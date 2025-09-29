from typing import List, Dict

from django.contrib.auth import authenticate
from django.db import transaction
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import status, permissions
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Conversation, Message
from .serializers import (
    SignupSerializer,
    UserSerializer,
    ConversationSerializer,
    CreateConversationSerializer,
    MessageSerializer,
)
from .services import get_chat_response, ChatServiceError


@api_view(['GET'])
def health(request):
    """Simple health check endpoint."""
    return Response({"message": "Server is up!"})


class SignupView(APIView):
    """User registration."""

    # PUBLIC_INTERFACE
    @swagger_auto_schema(
        operation_id="auth_signup",
        operation_summary="Sign up",
        operation_description="Create a new user account.",
        request_body=SignupSerializer,
        responses={201: UserSerializer, 400: "Bad Request"},
        tags=["auth"],
    )
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Auto-create a default conversation? We'll skip; frontend can create.
            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """Obtain JWT tokens via username/password."""

    # PUBLIC_INTERFACE
    @swagger_auto_schema(
        operation_id="auth_login",
        operation_summary="Login",
        operation_description="Authenticate and retrieve JWT tokens.",
        manual_parameters=[],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING, description='Username'),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='Password'),
            },
            required=['username', 'password'],
        ),
        responses={200: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'access': openapi.Schema(type=openapi.TYPE_STRING),
                'refresh': openapi.Schema(type=openapi.TYPE_STRING),
                'user': openapi.Schema(type=openapi.TYPE_OBJECT),
            }
        ), 400: "Invalid credentials"},
        tags=["auth"],
    )
    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(username=username, password=password)
        if not user:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)
        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        })


class ConversationListCreateView(APIView):
    """List conversations or create a new one for the authenticated user."""
    permission_classes = [permissions.IsAuthenticated]

    # PUBLIC_INTERFACE
    @swagger_auto_schema(
        operation_id="conversations_list",
        operation_summary="List conversations",
        operation_description="Returns all conversations for the authenticated user.",
        responses={200: ConversationSerializer(many=True)},
        tags=["conversations"],
    )
    def get(self, request):
        convs = Conversation.objects.filter(user=request.user).order_by("-updated_at")
        return Response(ConversationSerializer(convs, many=True).data)

    # PUBLIC_INTERFACE
    @swagger_auto_schema(
        operation_id="conversations_create",
        operation_summary="Create conversation",
        operation_description="Creates a new conversation for the authenticated user.",
        request_body=CreateConversationSerializer,
        responses={201: ConversationSerializer},
        tags=["conversations"],
    )
    def post(self, request):
        serializer = CreateConversationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conv = Conversation.objects.create(user=request.user, title=serializer.validated_data.get("title", "New Conversation"))
        return Response(ConversationSerializer(conv).data, status=status.HTTP_201_CREATED)


class ConversationDetailView(APIView):
    """Retrieve or delete a conversation."""
    permission_classes = [permissions.IsAuthenticated]

    # PUBLIC_INTERFACE
    @swagger_auto_schema(
        operation_id="conversations_retrieve",
        operation_summary="Retrieve conversation",
        operation_description="Get a single conversation with its messages.",
        responses={200: ConversationSerializer, 404: "Not found"},
        tags=["conversations"],
    )
    def get(self, request, conversation_id: int):
        conv = Conversation.objects.filter(id=conversation_id, user=request.user).first()
        if not conv:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(ConversationSerializer(conv).data)

    # PUBLIC_INTERFACE
    @swagger_auto_schema(
        operation_id="conversations_delete",
        operation_summary="Delete conversation",
        operation_description="Delete a conversation and all its messages.",
        responses={204: "Deleted", 404: "Not found"},
        tags=["conversations"],
    )
    def delete(self, request, conversation_id: int):
        conv = Conversation.objects.filter(id=conversation_id, user=request.user).first()
        if not conv:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        conv.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChatView(APIView):
    """Chat endpoint to send user prompt and receive AI response."""
    permission_classes = [permissions.IsAuthenticated]

    # PUBLIC_INTERFACE
    @swagger_auto_schema(
        operation_id="chat_send",
        operation_summary="Send chat message",
        operation_description="Sends a user message to the AI and returns the assistant response. "
                              "If conversation_id is provided, the message is appended; otherwise a new conversation is created.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'message': openapi.Schema(type=openapi.TYPE_STRING, description='User message'),
                'conversation_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Existing conversation ID'),
                'system_prompt': openapi.Schema(type=openapi.TYPE_STRING, description='Optional system prompt'),
            },
            required=['message']
        ),
        responses={200: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'conversation_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'assistant': openapi.Schema(type=openapi.TYPE_STRING),
                'messages': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_OBJECT)),
            }
        ), 400: "Bad Request"},
        tags=["chat"],
    )
    @transaction.atomic
    def post(self, request):
        user = request.user
        message_text = request.data.get("message", "").strip()
        if not message_text:
            return Response({"detail": "Message is required"}, status=status.HTTP_400_BAD_REQUEST)

        conversation_id = request.data.get("conversation_id")
        system_prompt = request.data.get("system_prompt")

        if conversation_id:
            conv = Conversation.objects.filter(id=conversation_id, user=user).first()
            if not conv:
                return Response({"detail": "Conversation not found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            conv = Conversation.objects.create(user=user, title=message_text[:60] or "New Conversation")

        # Build prior messages for context
        prior_msgs_qs = conv.messages.order_by("created_at")
        history: List[Dict[str, str]] = []
        if system_prompt:
            history.append({"role": "system", "content": system_prompt})
        for m in prior_msgs_qs:
            history.append({"role": m.role, "content": m.content})
        # Append current user message
        history.append({"role": "user", "content": message_text})

        # Persist user message immediately
        Message.objects.create(conversation=conv, role=Message.ROLE_USER, content=message_text)

        try:
            ai_text = get_chat_response(history)
        except ChatServiceError as e:
            transaction.set_rollback(True)
            return Response({"detail": f"Chat service error: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

        # Save assistant reply
        Message.objects.create(conversation=conv, role=Message.ROLE_ASSISTANT, content=ai_text)

        conv.refresh_from_db()
        return Response({
            "conversation_id": conv.id,
            "assistant": ai_text,
            "messages": MessageSerializer(conv.messages.order_by("created_at"), many=True).data
        }, status=status.HTTP_200_OK)

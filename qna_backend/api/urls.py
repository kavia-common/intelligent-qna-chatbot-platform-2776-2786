from django.urls import path
from .views import (
    health,
    SignupView,
    LoginView,
    ConversationListCreateView,
    ConversationDetailView,
    ChatView,
)

urlpatterns = [
    path('health/', health, name='Health'),
    path('auth/signup/', SignupView.as_view(), name='Signup'),
    path('auth/login/', LoginView.as_view(), name='Login'),
    path('conversations/', ConversationListCreateView.as_view(), name='Conversations'),
    path('conversations/<int:conversation_id>/', ConversationDetailView.as_view(), name='ConversationDetail'),
    path('chat/', ChatView.as_view(), name='Chat'),
]

from django.conf import settings
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """Abstract base that adds created_at and updated_at."""
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserProfile(TimeStampedModel):
    """Optional profile extension for auth.User to store chatbot-specific settings."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=150, blank=True, default="")
    # Future: add preferences (e.g., model selection, temperature, etc.)

    def __str__(self) -> str:
        return f"Profile<{self.user.username}>"


class Conversation(TimeStampedModel):
    """A conversation session belonging to a user."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations")
    title = models.CharField(max_length=255, default="New Conversation")

    def __str__(self) -> str:
        return f"Conversation<{self.id}>:{self.title}"


class Message(TimeStampedModel):
    """A message within a conversation."""
    ROLE_USER = "user"
    ROLE_ASSISTANT = "assistant"
    ROLE_SYSTEM = "system"
    ROLE_CHOICES = [
        (ROLE_USER, "User"),
        (ROLE_ASSISTANT, "Assistant"),
        (ROLE_SYSTEM, "System"),
    ]

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    content = models.TextField()

    def __str__(self) -> str:
        return f"Message<{self.role}> in Conv<{self.conversation_id}>"

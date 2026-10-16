from django.db import models
from django.contrib.auth.models import User
from tools.generate_nums import generate_uuid7
from .tool_config import default_tools


class ChatPersona(models.Model):
    id = models.CharField(max_length=32, primary_key=True, default=generate_uuid7)
    name = models.CharField(max_length=80, unique=True)
    description = models.CharField(max_length=500, blank=True)
    system_prompt = models.TextField()
    greeting = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    tools = models.JSONField(default=default_tools, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chat_personas'
        ordering = ['sort_order', 'created_at', 'id']


class ChatConversation(models.Model):
    id = models.CharField(max_length=32, primary_key=True, default=generate_uuid7)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_conversations')
    persona = models.ForeignKey(ChatPersona, null=True, on_delete=models.SET_NULL)
    title = models.CharField(max_length=100, default='新聊天')
    # Snapshot preserves existing chats when a persona is edited or removed.
    persona_name = models.CharField(max_length=80)
    system_prompt = models.TextField()
    greeting = models.TextField(blank=True)
    agent_messages = models.JSONField(default=list, blank=True)
    persona_tools = models.JSONField(default=default_tools, blank=True)
    generation_id = models.CharField(max_length=32, blank=True, default='')
    generation_started_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chat_conversations'
        ordering = ['-updated_at', '-id']
        indexes = [models.Index(fields=['user', '-updated_at'])]


class ChatMessage(models.Model):
    id = models.CharField(max_length=32, primary_key=True, default=generate_uuid7)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_messages')
    conversation = models.ForeignKey(ChatConversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10)  # 'user' or 'ai'
    content = models.TextField()
    token_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_messages'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f'[{self.role}] {self.user.username} @ {self.created_at}'

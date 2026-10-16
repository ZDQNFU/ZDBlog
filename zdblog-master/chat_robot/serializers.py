from rest_framework import serializers

from .models import ChatConversation, ChatMessage, ChatPersona
from .tool_config import TOOL_CHOICES


class PersonaSerializer(serializers.ModelSerializer):
    tools = serializers.ListField(child=serializers.ChoiceField(choices=TOOL_CHOICES),
                                  max_length=len(TOOL_CHOICES), required=False, allow_empty=True)

    def validate_tools(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError('工具名称不能重复')
        return value
    system_prompt = serializers.CharField(max_length=20000)
    greeting = serializers.CharField(max_length=2000, allow_blank=True, required=False)

    class Meta:
        model = ChatPersona
        fields = ['id', 'name', 'description', 'system_prompt', 'greeting',
                  'is_active', 'sort_order', 'tools', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class PublicPersonaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatPersona
        fields = ['id', 'name', 'description', 'greeting']


class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatConversation
        fields = ['id', 'title', 'persona', 'persona_name', 'greeting', 'created_at', 'updated_at']
        read_only_fields = ['id', 'persona', 'persona_name', 'greeting', 'created_at', 'updated_at']


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'role', 'content', 'created_at', 'conversation_id']

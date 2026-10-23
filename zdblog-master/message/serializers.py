from rest_framework import serializers
from django.db import transaction
from django.utils import timezone
from .models import Message, MessageLike
from .moderation import moderate_message


class MessageSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_has_liked = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'user_name', 'content', 'like_count',
                  'is_hidden', 'created_at', 'user_has_liked']

    def get_user_name(self, obj):
        if obj.user:
            return obj.user.username
        return '游客'

    def get_user_has_liked(self, obj):
        if hasattr(obj, 'viewer_has_liked'):
            return obj.viewer_has_liked
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return MessageLike.objects.filter(
                message=obj, user=request.user
            ).exists()
        return False


class MessageWriteSerializer(serializers.ModelSerializer):
    content = serializers.CharField(max_length=100, trim_whitespace=True)
    message = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'content', 'status', 'message', 'created_at']
        read_only_fields = ['id', 'status', 'message', 'created_at']

    @transaction.atomic
    def create(self, validated_data):
        result, reason = moderate_message(validated_data['content'], user=validated_data.get('user'))
        validated_data.update(status=result, moderation_reason=reason)
        return super().create(validated_data)

    def get_message(self, obj):
        return {
            Message.STATUS_APPROVED: '留言发送成功',
            Message.STATUS_PENDING: '留言已提交，审核通过后显示',
            Message.STATUS_REJECTED: '留言未通过审核，请文明交流并避免广告、辱骂等内容',
        }[obj.status]


class MessageAdminSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    content = serializers.CharField(max_length=100, trim_whitespace=True)
    is_hidden = serializers.ChoiceField(choices=[0, 1], required=False)
    reviewed_by_name = serializers.CharField(source='reviewed_by.username', read_only=True, default=None)

    class Meta:
        model = Message
        fields = ['id', 'user', 'user_name', 'content', 'like_count',
                  'is_hidden', 'status', 'moderation_reason', 'reviewed_by',
                  'reviewed_by_name', 'reviewed_at', 'created_at']
        read_only_fields = ['id', 'user', 'created_at', 'like_count', 'moderation_reason',
                            'reviewed_by', 'reviewed_by_name', 'reviewed_at']

    def _apply_moderation(self, validated_data, user):
        result, reason = moderate_message(validated_data['content'], user=user)
        validated_data.update(status=result, moderation_reason=reason, reviewed_by=None, reviewed_at=None)

    def _apply_review(self, validated_data, status):
        if status is not None:
            validated_data.update(status=status, reviewed_at=timezone.now(),
                                  reviewed_by=self.context['request'].user)

    @transaction.atomic
    def create(self, validated_data):
        manual_status = validated_data.get('status')
        self._apply_moderation(validated_data, validated_data.get('user'))
        self._apply_review(validated_data, manual_status)
        return super().create(validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        manual_status = validated_data.get('status')
        if 'content' in validated_data and validated_data['content'] != instance.content:
            self._apply_moderation(validated_data, instance.user)
        self._apply_review(validated_data, manual_status)
        return super().update(instance, validated_data)

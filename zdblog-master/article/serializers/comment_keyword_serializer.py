from django.db import IntegrityError, transaction
from rest_framework import serializers

from article.models import CommentModerationKeyword
from article.services.comment_text import normalize


class CommentKeywordSerializer(serializers.ModelSerializer):
    enabled = serializers.BooleanField(default=True)

    class Meta:
        model = CommentModerationKeyword
        fields = ['id', 'word', 'action', 'enabled', 'description', 'source',
                  'created_by', 'updated_by', 'created_at', 'updated_at']
        read_only_fields = ['id', 'source', 'created_by', 'updated_by', 'created_at', 'updated_at']

    def validate_word(self, value):
        normalized = normalize(value)
        if not normalized:
            raise serializers.ValidationError('关键词须包含汉字、字母或数字，不能只填写符号')
        queryset = CommentModerationKeyword.objects.filter(normalized_word=normalized)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError('该关键词已存在（匹配时忽略大小写、全半角和分隔符）')
        return value

    def create(self, validated_data):
        try:
            with transaction.atomic():
                return super().create(validated_data)
        except IntegrityError as exc:
            raise serializers.ValidationError({'word': '该关键词已存在，请刷新列表'}) from exc

    def update(self, instance, validated_data):
        try:
            with transaction.atomic():
                return super().update(instance, validated_data)
        except IntegrityError as exc:
            raise serializers.ValidationError({'word': '该关键词已存在，请刷新列表'}) from exc

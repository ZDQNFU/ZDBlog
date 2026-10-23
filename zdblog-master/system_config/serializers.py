from rest_framework import serializers
from django.core.signing import dumps, loads
from .models import SystemConfig


class SystemConfigListSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemConfig
        fields = ['id', 'key', 'value_type', 'description', 'is_encrypted', 'created_at', 'updated_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.is_encrypted:
            data['value'] = '***'
        else:
            data['value'] = instance.value
        return data


class SystemConfigDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemConfig
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.is_encrypted:
            try:
                data['value'] = loads(instance.value)
            except Exception:
                data['value'] = instance.value
        return data


class SystemConfigWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemConfig
        fields = ['key', 'value', 'value_type', 'description', 'is_encrypted']

    def validate(self, attrs):
        key = attrs.get('key', self.instance.key if self.instance else '')
        if key in ('COMMENT_BLOCK_WORDS', 'COMMENT_REVIEW_WORDS'):
            raise serializers.ValidationError({'key': '评论关键词已迁移，请在“评论管理 → 审核关键词”中维护'})
        return attrs

    def create(self, validated_data):
        if validated_data.get('is_encrypted'):
            validated_data['value'] = dumps(validated_data['value'])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.get('is_encrypted', instance.is_encrypted):
            if 'value' in validated_data:
                validated_data['value'] = dumps(validated_data['value'])
            elif 'is_encrypted' in validated_data and not instance.is_encrypted:
                instance.value = dumps(instance.value)
        elif not validated_data.get('is_encrypted', True) and instance.is_encrypted:
            if 'value' in validated_data:
                pass
            else:
                try:
                    instance.value = loads(instance.value)
                except Exception:
                    pass
        return super().update(instance, validated_data)

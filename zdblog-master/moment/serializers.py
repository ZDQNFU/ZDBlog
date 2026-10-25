from rest_framework import serializers
from .models import Moment


class MomentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.username', read_only=True, default='站主')
    like_count = serializers.IntegerField(read_only=True, default=0)
    user_has_liked = serializers.BooleanField(source='viewer_has_liked', read_only=True, default=False)

    class Meta:
        model = Moment
        fields = ['id', 'content', 'author_name', 'created_at', 'updated_at', 'like_count', 'user_has_liked']


class MomentAdminSerializer(MomentSerializer):
    content = serializers.CharField(max_length=500, trim_whitespace=True, allow_blank=False)

    class Meta(MomentSerializer.Meta):
        fields = MomentSerializer.Meta.fields + ['is_published']
        read_only_fields = ['id', 'created_at', 'updated_at']

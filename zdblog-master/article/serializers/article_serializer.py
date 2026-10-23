from rest_framework import serializers
from django.db import transaction
from django.utils import timezone

from article.services.comment_moderation import moderate_comment
from article.services.comment_service import public_comment_tree

from article.models import (
    Article,
    Category,
    Tag,
    Comment,
    Like
)


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'color', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.username', read_only=True)
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'author_name', 'content', 'created_at', 'replies']

    def get_replies(self, obj):
        if hasattr(obj, 'prefetched_replies'):
            replies = obj.prefetched_replies
        else:
            replies = obj.replies.filter(status=Comment.STATUS_APPROVED)
        return CommentSerializer(replies, many=True).data


class ArticleListSerializer(serializers.ModelSerializer):
    """C端文章列表卡片序列化器"""
    tags = TagSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    author_name = serializers.CharField(source='author.username', read_only=True)

    class Meta:
        model = Article
        fields = [
            'id', 'title', 'slug', 'summary', 'cover',
            'tags', 'category',
            'like_count', 'comment_count', 'view_count',
            'author_name', 'status', 'published_at', 'updated_at'
        ]


class ArticleDetailSerializer(serializers.ModelSerializer):
    """C端文章详情序列化器"""
    tags = TagSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    author_name = serializers.CharField(source='author.username', read_only=True)
    comments = serializers.SerializerMethodField()
    user_has_liked = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = [
            'id', 'title', 'slug', 'summary', 'cover',
            'content_html', 'content_md',
            'tags', 'category',
            'like_count', 'comment_count', 'view_count',
            'author_name', 'status',
            'published_at', 'created_at', 'updated_at',
            'comments', 'user_has_liked'
        ]

    def get_comments(self, obj):
        top_comments = public_comment_tree(obj.pk)
        return CommentSerializer(top_comments, many=True).data

    def get_user_has_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Like.objects.filter(article=obj, user=request.user).exists()
        return False


class CommentAdminSerializer(serializers.ModelSerializer):
    """S端评论管理序列化器"""
    author_name = serializers.CharField(source='author.username', read_only=True)
    article_title = serializers.CharField(source='article.title', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.username', read_only=True, default=None)
    content = serializers.CharField(max_length=2000, trim_whitespace=True)

    class Meta:
        model = Comment
        fields = ['id', 'article', 'article_title', 'author', 'author_name',
                  'parent', 'content', 'status', 'moderation_reason', 'reviewed_by',
                  'reviewed_by_name', 'reviewed_at', 'created_at', 'updated_at']
        read_only_fields = ['id', 'article', 'author', 'parent', 'moderation_reason',
                            'reviewed_by', 'reviewed_by_name', 'reviewed_at', 'created_at', 'updated_at']

    @transaction.atomic
    def update(self, instance, validated_data):
        manual_status = validated_data.get('status')
        if 'content' in validated_data and validated_data['content'] != instance.content:
            result, reason = moderate_comment(validated_data['content'], author=instance.author)
            validated_data.update(status=result, moderation_reason=reason,
                                  reviewed_by=None, reviewed_at=None)
        if manual_status is not None:
            validated_data.update(status=manual_status, reviewed_at=timezone.now(),
                                  reviewed_by=self.context['request'].user)
        return super().update(instance, validated_data)


class ArticleWriteSerializer(serializers.ModelSerializer):
    """S端文章写入序列化器（创建/更新）"""
    content_html = serializers.CharField(required=False, allow_blank=True, default='')

    class Meta:
        model = Article
        fields = [
            'title', 'content_md', 'content_html',
            'summary', 'cover', 'status',
            'category', 'tags',
        ]

    def _make_slug(self, title):
        from django.utils.text import slugify
        from tools.generate_nums import generate_uuid7
        return slugify(title) or generate_uuid7()

    def _set_published_at(self, validated_data):
        from django.utils import timezone
        if validated_data.get('status') == 'published':
            validated_data['published_at'] = timezone.now()

    def create(self, validated_data):
        validated_data['slug'] = self._make_slug(validated_data['title'])
        self._set_published_at(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'title' in validated_data:
            validated_data['slug'] = self._make_slug(validated_data['title'])
        self._set_published_at(validated_data)
        return super().update(instance, validated_data)


class CommentCreateSerializer(serializers.ModelSerializer):
    """C端评论创建序列化器"""
    content = serializers.CharField(max_length=2000, trim_whitespace=True)
    message = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'article', 'parent', 'content', 'status', 'message', 'created_at']
        read_only_fields = ['id', 'status', 'message', 'created_at']

    def validate(self, attrs):
        article = attrs['article']
        if article.status not in (Article.STATUS_PUBLISHED, Article.STATUS_PRIVATE):
            raise serializers.ValidationError({'article': '该文章暂不接受评论'})
        parent = attrs.get('parent')
        depth = 0
        seen = set()
        while parent is not None:
            if parent.pk in seen or depth >= 5:
                raise serializers.ValidationError({'parent': '回复层级过多，请回复上层评论'})
            if parent.article_id != article.pk or parent.status != Comment.STATUS_APPROVED:
                raise serializers.ValidationError({'parent': '只能回复当前文章中已公开的评论'})
            seen.add(parent.pk)
            parent = parent.parent
            depth += 1
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        result, reason = moderate_comment(validated_data['content'], author=validated_data['author'])
        validated_data.update(status=result, moderation_reason=reason)
        return super().create(validated_data)

    def get_message(self, obj):
        return {
            Comment.STATUS_APPROVED: '评论发表成功',
            Comment.STATUS_PENDING: '评论已提交，审核通过后显示',
            Comment.STATUS_REJECTED: '评论未通过审核，请文明交流并避免广告、辱骂等内容',
        }[obj.status]

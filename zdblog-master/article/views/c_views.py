from django.contrib.auth.hashers import check_password
from django.db import IntegrityError
from django.db.models import F
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import UserRateThrottle

from tools.cache_utils import cache_result
from article.models import Article, Comment, Like, Tag
from article.serializers.article_serializer import (
    ArticleListSerializer,
    ArticleDetailSerializer,
    CommentCreateSerializer,
    TagSerializer,
)


class ArticleListPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


class ArticleListView(generics.ListAPIView):
    """C端：已发布+私密文章列表（带分页）"""
    serializer_class = ArticleListSerializer
    pagination_class = ArticleListPagination
    search_fields = ['title', 'summary', 'content_md']

    def get_queryset(self):
        return (
            Article.objects
            .filter(status__in=[Article.STATUS_PUBLISHED, Article.STATUS_PRIVATE])
            .select_related('author', 'category')
            .prefetch_related('tags')
            .order_by('-published_at')
        )


class ArticleDetailView(generics.RetrieveAPIView):
    """C端：文章详情（私密文章需验证密码）"""
    serializer_class = ArticleDetailSerializer
    lookup_field = 'pk'

    def get_queryset(self):
        return (
            Article.objects
            .filter(status__in=[Article.STATUS_PUBLISHED, Article.STATUS_PRIVATE])
            .select_related('author', 'category')
            .prefetch_related('tags')
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.status == Article.STATUS_PRIVATE:
            data = self.get_serializer(instance).data
            data['locked'] = True
            data['content_html'] = ''
            data['content_md'] = ''
            data['comments'] = []
            return Response(data)

        Article.objects.filter(pk=kwargs['pk']).update(view_count=F('view_count') + 1)
        instance.refresh_from_db()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class ArticleVerifyView(APIView):
    """C端：验证私密文章密码，返回完整内容"""

    def post(self, request, pk):
        try:
            article = Article.objects.get(pk=pk, status=Article.STATUS_PRIVATE)
        except Article.DoesNotExist:
            return Response({'detail': '文章不存在'}, status=status.HTTP_404_NOT_FOUND)

        password = request.data.get('password', '')
        if not password:
            return Response({'detail': '请输入密码'}, status=status.HTTP_400_BAD_REQUEST)

        if not check_password(password, article.author.password):
            return Response({'detail': '密码错误'}, status=status.HTTP_400_BAD_REQUEST)

        Article.objects.filter(pk=pk).update(view_count=F('view_count') + 1)
        article.refresh_from_db()

        serializer = ArticleDetailSerializer(article, context={'request': request})
        return Response(serializer.data)


class CommentRateThrottle(UserRateThrottle):
    scope = 'comment'
    rate = '5/min'


class CommentCreateView(generics.CreateAPIView):
    """C端：创建评论（需登录）"""
    permission_classes = [IsAuthenticated]
    serializer_class = CommentCreateSerializer
    throttle_classes = [CommentRateThrottle]

    def throttled(self, request, wait):
        from rest_framework.exceptions import Throttled
        raise Throttled(wait=wait, detail='评论提交过于频繁，请稍后再试')

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class LikeToggleView(APIView):
    """C端：点赞/取消点赞（需登录，幂等）"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            article = Article.objects.get(pk=pk, status__in=[Article.STATUS_PUBLISHED, Article.STATUS_PRIVATE])
        except Article.DoesNotExist:
            return Response({'detail': '文章不存在'}, status=status.HTTP_404_NOT_FOUND)
        try:
            Like.objects.create(article=article, user=request.user)
            article.like_count = article.likes.count()
            article.save(update_fields=['like_count'])
            return Response({'liked': True, 'like_count': article.like_count})
        except IntegrityError:
            return Response({'detail': '已经点过赞了'}, status=status.HTTP_409_CONFLICT)

    def delete(self, request, pk):
        try:
            article = Article.objects.get(pk=pk, status__in=[Article.STATUS_PUBLISHED, Article.STATUS_PRIVATE])
        except Article.DoesNotExist:
            return Response({'detail': '文章不存在'}, status=status.HTTP_404_NOT_FOUND)
        deleted, _ = Like.objects.filter(article=article, user=request.user).delete()
        if deleted:
            article.like_count = article.likes.count()
            article.save(update_fields=['like_count'])
            return Response({'liked': False, 'like_count': article.like_count})
        return Response({'detail': '尚未点赞'}, status=status.HTTP_404_NOT_FOUND)


class TagListView(generics.ListAPIView):
    """C端：所有标签列表"""
    serializer_class = TagSerializer
    pagination_class = None

    def get_queryset(self):
        return Tag.objects.all()

    @cache_result('c:tags', timeout=3600)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class RandomArticleView(generics.ListAPIView):
    """C端：随机推荐3篇文章"""
    serializer_class = ArticleListSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            Article.objects
            .filter(status=Article.STATUS_PUBLISHED)
            .select_related('author', 'category')
            .prefetch_related('tags')
            .order_by('?')[:3]
        )

    @cache_result('c:random_articles', timeout=300)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

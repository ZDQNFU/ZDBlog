from django.urls import path
from article.views.keyword_views import CommentKeywordListCreateView, CommentKeywordDetailView

from article.views.c_views import ArticleListView, ArticleDetailView, ArticleVerifyView, CommentCreateView, LikeToggleView, TagListView, RandomArticleView
from article.views.s_views import (
    SArticleListCreateView,
    SArticleRetrieveUpdateDestroyView,
    SArticleSummaryGenerateView,
    STagListCreateView,
    STagRetrieveUpdateDestroyView,
    SCategoryListCreateView,
    SCategoryRetrieveUpdateDestroyView,
    SCommentListCreateView,
    SCommentRetrieveUpdateDestroyView,
)

urlpatterns = [
    # ================= C端（公开接口） =================
    # 已发布文章列表（分页）
    path('c/list/', ArticleListView.as_view(), name='c_article_list'),
    # 评论创建（需登录）
    path('c/comments/', CommentCreateView.as_view(), name='c_comment_create'),
    # 标签列表
    path('c/tags/', TagListView.as_view(), name='c_tag_list'),
    # 随机推荐文章
    path('c/random/', RandomArticleView.as_view(), name='c_random_articles'),
    # 点赞/取消点赞（需登录）
    path('c/<str:pk>/like/', LikeToggleView.as_view(), name='c_article_like'),
    # 私密文章密码验证
    path('c/<str:pk>/verify/', ArticleVerifyView.as_view(), name='c_article_verify'),
    # 已发布/私密文章详情
    path('c/<str:pk>/', ArticleDetailView.as_view(), name='c_article_detail'),

    # ================= S端（管理接口） =================
    # 文章 CRUD
    path('s/articles/', SArticleListCreateView.as_view(), name='s_article_list_create'),
    path('s/articles/generate-summary/', SArticleSummaryGenerateView.as_view(), name='s_article_generate_summary'),
    path('s/articles/<str:pk>/', SArticleRetrieveUpdateDestroyView.as_view(), name='s_article_detail'),

    # 标签 CRUD
    path('s/tags/', STagListCreateView.as_view(), name='s_tag_list_create'),
    path('s/tags/<str:pk>/', STagRetrieveUpdateDestroyView.as_view(), name='s_tag_detail'),

    # 分类 CRUD
    path('s/categories/', SCategoryListCreateView.as_view(), name='s_category_list_create'),
    path('s/categories/<str:pk>/', SCategoryRetrieveUpdateDestroyView.as_view(), name='s_category_detail'),

    # 评论 CRUD
    path('s/comment-keywords/', CommentKeywordListCreateView.as_view(), name='s_comment_keywords'),
    path('s/comment-keywords/<int:pk>/', CommentKeywordDetailView.as_view(), name='s_comment_keyword_detail'),
    path('s/comments/', SCommentListCreateView.as_view(), name='s_comment_list_create'),
    path('s/comments/<str:pk>/', SCommentRetrieveUpdateDestroyView.as_view(), name='s_comment_detail'),
]

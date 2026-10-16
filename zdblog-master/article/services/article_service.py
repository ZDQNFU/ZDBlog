from django.db.models import F
from django.utils.text import slugify
from django.utils import timezone

from article.models import Article


class ArticleAdmin:
    """
    文章管理服务类，提供文章的创建、更新、删除、发布及查询等核心业务逻辑。
    """

    @staticmethod
    def create_article(
            *,
            title,
            content_md,
            author,
            category=None,
            tags=None,
            status='draft'
    ):
        """
        创建新文章。

        :param title: 文章标题
        :param content_md: 文章 Markdown 内容
        :param author: 文章作者对象
        :param category: 文章分类对象，可选
        :param tags: 文章标签列表或查询集，可选
        :param status: 文章状态，默认为 'draft' (草稿)
        :return: 创建的 Article 实例
        """
        # 根据标题生成唯一的 slug，当英文重复时，会出现冲突的情况
        # slug = slugify(title)

        # 生成基础 slug（保留中文）
        base_slug = slugify(title, allow_unicode=True)
        slug = base_slug

        # 处理冲突：如果 slug 已存在，添加计数器
        # __iexact：迁移前 MySQL 是 ci 排序规则，'Git' 与 'git' 算同一个 slug；
        # 不忽略大小写就会产生两个只差大小写的 slug，URL 上没法区分
        counter = 1
        while Article.objects.filter(slug__iexact=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        # 创建文章实例
        article = Article.objects.create(
            title=title,
            slug=slug,
            content_md=content_md,
            author=author,
            category=category,
            status=status
        )

        # 如果提供了标签，则设置关联
        if tags:
            article.tags.set(tags)

        return article

    @staticmethod
    def update_article(article, **kwargs):
        """
        更新现有文章的信息。

        :param article: 要更新的 Article 实例
        :param kwargs: 需要更新的字段及其新值的键值对
        :return: 更新后的 Article 实例
        """
        # 遍历传入的 kwargs，动态设置属性
        for key, value in kwargs.items():
            setattr(article, key, value)

        # 保存更改到数据库
        article.save()

        return article

    @staticmethod
    def delete_article(article):
        """
        删除指定文章。

        :param article: 要删除的 Article 实例
        """
        article.delete()

    @staticmethod
    def publish_article(article):
        """
        发布文章，将状态设置为已发布，并记录发布时间。

        :param article: 要发布的 Article 实例
        :return: 发布后的 Article 实例
        """
        # 设置状态为已发布
        article.status = Article.STATUS_PUBLISHED
        # 设置发布时间为当前时间
        article.published_at = timezone.now()
        # 保存更改
        article.save()

        return article

    @staticmethod
    def get_article_detail(article_id):
        """
        获取单篇文章的详细信息，优化查询以减少数据库访问次数。

        :param article_id: 文章 ID
        :return: Article 实例
        :raises Article.DoesNotExist: 如果文章不存在
        """
        return (
            Article.objects
            .select_related('author', 'category')  # 优化外键查询
            .prefetch_related('tags')              # 优化多对多关系查询
            .get(id=article_id)
        )

    @staticmethod
    def get_article_list():
        """
        获取已发布文章的列表，按创建时间倒序排列，并优化关联查询。

        :return: Article 查询集
        """
        return (
            Article.objects
            .filter(status=Article.STATUS_PUBLISHED)  # 仅筛选已发布文章
            .select_related('author', 'category')     # 优化外键查询
            .prefetch_related('tags')                 # 优化多对多关系查询
            .order_by('-created_at')                  # 按创建时间倒序
        )

    @staticmethod
    def increase_view_count(article_id):
        """
        原子性地增加文章的浏览次数。

        :param article_id: 文章 ID
        """
        Article.objects.filter(
            id=article_id
        ).update(
            view_count=F('view_count') + 1  # 使用 F 表达式进行原子更新，避免竞态条件
        )
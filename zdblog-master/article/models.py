from django.db import models
from django.contrib.auth import get_user_model
from tools.generate_nums import generate_uuid7

User = get_user_model()


class Category(models.Model):
    # ID
    id = models.CharField(
        primary_key=True,
        max_length=32,
        default=generate_uuid7,
        editable=False,
        verbose_name='ID'
    )
    # 分类名
    name = models.CharField('分类名', max_length=50, unique=True)

    # 创建与修改人
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_categories',
        verbose_name='创建人'
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_categories',
        verbose_name='最后修改人'
    )

    # 时间戳
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('最后修改时间', auto_now=True)

    class Meta:
        db_table = 'article_category'
        verbose_name = '分类'
        verbose_name_plural = '分类'
        ordering = ['-created_at']  # 按创建时间倒序

    def __str__(self):
        return self.name


class Tag(models.Model):
    id = models.CharField(
        primary_key=True,
        max_length=32,
        default=generate_uuid7,
        editable=False,
        verbose_name='ID'
    )
    name = models.CharField('标签名', max_length=50, unique=True)
    color = models.CharField(
        '标签颜色',
        max_length=7,
        default='#3b82f6',          # 默认蓝色
        help_text='十六进制颜色码，如 #ff0000'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_tags',
        verbose_name='创建人'
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_tags',
        verbose_name='最后修改人'
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('最后修改时间', auto_now=True)

    class Meta:
        # db_table: 指定数据库中的表名
        db_table = 'article_tag'
        # verbose_name: 在 Django Admin 或表单中显示的单数名称
        verbose_name = '标签'
        # verbose_name_plural: 在 Django Admin 或表单中显示的复数名称
        verbose_name_plural = '标签'
        # ordering: 默认查询排序规则
        ordering = ['-created_at']

    def __str__(self):
        """
        定义对象的字符串表示形式。
        当打印 Tag 实例或在 Django Admin 列表中显示时，将返回标签的名称。
        """
        return self.name


class Article(models.Model):

    STATUS_DRAFT = 'draft'
    STATUS_PUBLISHED = 'published'
    STATUS_PRIVATE = 'private'

    STATUS_CHOICES = [
        (STATUS_DRAFT, '草稿'),
        (STATUS_PUBLISHED, '已发布'),
        (STATUS_PRIVATE, '私密'),
    ]

    id = models.CharField(
        primary_key=True,
        max_length=32,
        default=generate_uuid7,
        editable=False,
        verbose_name='ID'
    )

    title = models.CharField(max_length=200)

    slug = models.SlugField(unique=True)

    summary = models.CharField(max_length=300, blank=True)

    content_md = models.TextField()

    content_html = models.TextField(blank=True)

    cover = models.URLField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT
    )

    view_count = models.IntegerField(default=0)

    like_count = models.IntegerField(default=0)

    comment_count = models.IntegerField(default=0)

    author = models.ForeignKey(
        User,
        null=True,
        on_delete=models.SET_NULL
    )

    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    tags = models.ManyToManyField(Tag, blank=True)

    published_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # db_table: 指定数据库中的表名
        db_table = 'article'
        # verbose_name: 在 Django Admin 或表单中显示的单数名称
        verbose_name = '文章'
        # verbose_name_plural: 在 Django Admin 或表单中显示的复数名称
        verbose_name_plural = '文章'
        # ordering: 默认查询排序规则
        ordering = ['-created_at']

    def __str__(self):
        """
        定义对象的字符串表示形式。
        当打印 Article 模型实例时，将返回文章的标题。
        """
        return self.title


class Comment(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, '待审核'),
        (STATUS_APPROVED, '已通过'),
        (STATUS_REJECTED, '已拒绝'),
    ]

    id = models.CharField(
        primary_key=True,
        max_length=32,
        default=generate_uuid7,
        editable=False,
        verbose_name='ID'
    )
    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='所属文章'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='comments',
        verbose_name='评论者'
    )
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='replies',
        verbose_name='父评论'
    )
    content = models.TextField('评论内容')
    content_fingerprint = models.CharField('内容指纹', max_length=64, db_index=True,
                                          blank=True, editable=False)
    status = models.CharField('审核状态', max_length=20, choices=STATUS_CHOICES,
                              default=STATUS_PENDING, db_index=True)
    moderation_reason = models.CharField('审核原因', max_length=255, blank=True)
    reviewed_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='reviewed_comments', verbose_name='审核人',
    )
    reviewed_at = models.DateTimeField('人工审核时间', null=True, blank=True)
    created_at = models.DateTimeField('评论时间', auto_now_add=True)
    updated_at = models.DateTimeField('最后修改时间', auto_now=True)

    class Meta:
        db_table = 'article_comment'
        verbose_name = '评论'
        verbose_name_plural = '评论'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.author} 评论了 {self.article}'

    def save(self, *args, **kwargs):
        from article.services.comment_text import content_fingerprint

        update_fields = kwargs.get('update_fields')
        if update_fields is None or 'content' in update_fields:
            self.content_fingerprint = content_fingerprint(self.content)
            if update_fields is not None:
                kwargs['update_fields'] = {*update_fields, 'content_fingerprint'}
        super().save(*args, **kwargs)


class CommentModerationKeyword(models.Model):
    ACTION_REJECT = 'reject'
    ACTION_REVIEW = 'review'
    ACTION_CHOICES = [(ACTION_REJECT, '直接拒绝'), (ACTION_REVIEW, '进入待审')]
    SOURCE_BUILTIN = 'builtin'
    SOURCE_CUSTOM = 'custom'

    word = models.CharField('关键词', max_length=100)
    normalized_word = models.CharField('匹配词', max_length=200, unique=True, editable=False)
    action = models.CharField('处理方式', max_length=10, choices=ACTION_CHOICES, default=ACTION_REJECT)
    enabled = models.BooleanField('启用', default=True)
    description = models.CharField('分类或备注', max_length=200, blank=True)
    source = models.CharField('来源', max_length=10, default=SOURCE_CUSTOM,
                              choices=[(SOURCE_BUILTIN, '内置'), (SOURCE_CUSTOM, '自定义')])
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name='created_comment_keywords', verbose_name='创建人')
    updated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name='updated_comment_keywords', verbose_name='修改人')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('修改时间', auto_now=True)

    class Meta:
        db_table = 'article_comment_keyword'
        verbose_name = '评论审核关键词'
        verbose_name_plural = verbose_name
        ordering = ['-created_at', '-pk']

    def save(self, *args, **kwargs):
        from article.services.comment_text import normalize

        self.normalized_word = normalize(self.word)
        if kwargs.get('update_fields') is not None:
            kwargs['update_fields'] = {*kwargs['update_fields'], 'normalized_word'}
        super().save(*args, **kwargs)

    def clean(self):
        from django.core.exceptions import ValidationError
        from article.services.comment_text import normalize

        normalized = normalize(self.word)
        if not normalized:
            raise ValidationError({'word': '关键词须包含汉字、字母或数字'})
        if type(self).objects.filter(normalized_word=normalized).exclude(pk=self.pk).exists():
            raise ValidationError({'word': '该关键词已存在（忽略大小写、全半角和分隔符）'})

    def __str__(self):
        return self.word


class Like(models.Model):
    """文章点赞（用户+文章唯一，可取消）"""
    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name='likes',
        verbose_name='文章'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='likes',
        verbose_name='用户'
    )
    created_at = models.DateTimeField('点赞时间', auto_now_add=True)

    class Meta:
        db_table = 'article_like'
        verbose_name = '点赞'
        verbose_name_plural = '点赞'
        constraints = [
            models.UniqueConstraint(
                fields=['article', 'user'],
                name='unique_article_user_like'
            )
        ]

    def __str__(self):
        return f'{self.user} 点赞了 {self.article}'

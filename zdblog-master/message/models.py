from django.db import models
from django.contrib.auth import get_user_model
from tools.generate_nums import generate_uuid7

User = get_user_model()


class Message(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, '待审核'), (STATUS_APPROVED, '已通过'), (STATUS_REJECTED, '已拒绝'),
    ]

    id = models.CharField(
        primary_key=True,
        max_length=32,
        default=generate_uuid7,
        editable=False,
        verbose_name='ID'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='messages',
        verbose_name='用户'
    )
    content = models.CharField('留言内容', max_length=100)
    content_fingerprint = models.CharField('内容指纹', max_length=64, db_index=True,
                                          blank=True, editable=False)
    status = models.CharField('审核状态', max_length=20, choices=STATUS_CHOICES,
                              default=STATUS_PENDING, db_index=True)
    moderation_reason = models.CharField('审核原因', max_length=255, blank=True)
    reviewed_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='reviewed_messages', verbose_name='审核人',
    )
    reviewed_at = models.DateTimeField('人工审核时间', null=True, blank=True)
    like_count = models.IntegerField('点赞数', default=0)
    is_hidden = models.IntegerField('是否隐藏', default=0)  # 1隐藏 0不隐藏
    created_at = models.DateTimeField('留言时间', auto_now_add=True)

    class Meta:
        db_table = 'message'
        verbose_name = '留言'
        verbose_name_plural = '留言'
        ordering = ['-created_at']

    def __str__(self):
        preview = self.content[:20] + '...' if len(self.content) > 20 else self.content
        return f'{preview}'

    def save(self, *args, **kwargs):
        from article.services.comment_text import content_fingerprint

        update_fields = kwargs.get('update_fields')
        if update_fields is None or 'content' in update_fields:
            self.content_fingerprint = content_fingerprint(self.content)
            if update_fields is not None:
                kwargs['update_fields'] = {*update_fields, 'content_fingerprint'}
        super().save(*args, **kwargs)


class MessageLike(models.Model):
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='likes',
        verbose_name='留言'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='message_likes',
        verbose_name='用户'
    )
    created_at = models.DateTimeField('点赞时间', auto_now_add=True)

    class Meta:
        db_table = 'message_like'
        verbose_name = '留言点赞'
        verbose_name_plural = '留言点赞'
        constraints = [
            models.UniqueConstraint(
                fields=['message', 'user'],
                name='unique_message_user_like'
            )
        ]

    def __str__(self):
        return f'{self.user.username} 点赞了 {self.message}'

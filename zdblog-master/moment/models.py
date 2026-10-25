from django.conf import settings
from django.db import models
from tools.generate_nums import generate_uuid7


class Moment(models.Model):
    id = models.CharField(primary_key=True, max_length=32, default=generate_uuid7, editable=False)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
                               related_name='moments', verbose_name='发布人')
    content = models.CharField('动态内容', max_length=500)
    is_published = models.BooleanField('公开显示', default=True)
    created_at = models.DateTimeField('发布时间', auto_now_add=True)
    updated_at = models.DateTimeField('修改时间', auto_now=True)

    class Meta:
        db_table = 'moment'
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['is_published', '-created_at', '-id'], name='moment_public_time_idx')]
        verbose_name = '动态'
        verbose_name_plural = '动态'

    def __str__(self):
        return self.content[:40]


class MomentLike(models.Model):
    moment = models.ForeignKey(Moment, on_delete=models.CASCADE, related_name='likes')
    visitor_key = models.CharField('访客标识摘要', max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'moment_like'
        constraints = [models.UniqueConstraint(fields=['moment', 'visitor_key'], name='unique_moment_visitor_like')]

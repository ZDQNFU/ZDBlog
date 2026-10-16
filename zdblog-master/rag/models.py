from django.contrib.postgres.indexes import GinIndex
from django.db import models
from pgvector.django import VectorField
from tools.generate_nums import generate_uuid7
from .config import VECTOR_DIMENSIONS


class ArticleChunk(models.Model):
    id = models.CharField(primary_key=True, max_length=32, default=generate_uuid7, editable=False)
    article = models.ForeignKey('article.Article', on_delete=models.CASCADE, related_name='chunks')
    ordinal = models.PositiveIntegerField()
    heading = models.TextField(blank=True)
    content = models.TextField()
    char_count = models.PositiveIntegerField(default=0)
    content_hash = models.CharField(max_length=64)
    source_hash = models.CharField(max_length=64)
    embed_fingerprint = models.CharField(max_length=64, blank=True)
    embedding = VectorField(dimensions=VECTOR_DIMENSIONS, null=True, blank=True)
    embedded_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'article_chunk'
        ordering = ['article_id', 'ordinal']
        constraints = [models.UniqueConstraint(fields=['article', 'ordinal'], name='uniq_chunk_article_ordinal')]
        indexes = [models.Index(fields=['content_hash']),
                   GinIndex(name='idx_chunk_content_trgm', fields=['content'], opclasses=['gin_trgm_ops'])]


class ArticleIndexState(models.Model):
    article = models.OneToOneField('article.Article', primary_key=True, on_delete=models.CASCADE, related_name='rag_state')
    source_hash = models.CharField(max_length=64, blank=True)
    embed_fingerprint = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=12, default='pending')
    indexed_at = models.DateTimeField(null=True, blank=True)
    # Generic failure code only: provider errors may contain API credentials.
    last_error = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = 'article_rag_state'

import logging
from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from article.models import Article

logger = logging.getLogger(__name__)
IGNORED_FIELDS = {'view_count', 'like_count', 'comment_count', 'updated_at'}


def sync_article(article_id):
    from .indexer import reindex_article
    from .models import ArticleIndexState
    article = Article.objects.filter(pk=article_id).first()
    if article is None:
        return
    try:
        reindex_article(article)
    except Exception as exc:
        # Article save has already committed; indexing must not turn that success into HTTP 500.
        logger.warning('RAG indexing failed for article %s (%s)', article_id, type(exc).__name__)
        if Article.objects.filter(pk=article_id).exists():
            ArticleIndexState.objects.update_or_create(article_id=article_id,
                defaults={'status': 'error', 'last_error': type(exc).__name__[:100]})


@receiver(post_save, sender=Article)
def article_saved(sender, instance, raw=False, update_fields=None, using='default', **kwargs):
    if raw or using != 'default' or not settings.RAG_ENABLED:
        return
    if update_fields is not None and IGNORED_FIELDS.issuperset(update_fields):
        return
    transaction.on_commit(lambda: sync_article(instance.pk), using=using, robust=True)

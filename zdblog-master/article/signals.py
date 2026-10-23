from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from article.models import Article, Comment
from article.services.comment_service import visible_comment_ids
from tools.cache_utils import invalidate


@receiver(post_save, sender=Comment)
@receiver(post_delete, sender=Comment)
def refresh_comment_count(sender, instance, **kwargs):
    # Serialize counter refreshes without conflicting with foreign-key inserts.
    with transaction.atomic():
        article = Article.objects.select_for_update(no_key=True).filter(
            pk=instance.article_id,
        ).first()
        if article is not None:
            Article.objects.filter(pk=article.pk).update(
                comment_count=len(visible_comment_ids(article.pk)),
            )
    transaction.on_commit(lambda: invalidate('dashboard:stats', 'c:random_articles'))

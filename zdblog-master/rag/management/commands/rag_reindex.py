from django.core.management.base import BaseCommand, CommandError
from article.models import Article
from rag.indexer import reindex_article
from rag.models import ArticleIndexState


class Command(BaseCommand):
    help = 'Incrementally rebuild public blog chunks; missing embedding credentials leave lexical-only chunks'

    def add_arguments(self, parser):
        parser.add_argument('--article-id')
        parser.add_argument('--force', action='store_true')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--prune', action='store_true')

    def handle(self, *args, **options):
        articles = Article.objects.order_by('id')
        if options['article_id']:
            articles = articles.filter(pk=options['article_id'])
            if not articles.exists():
                raise CommandError('Article does not exist')
        elif not options['prune']:
            articles = articles.filter(status=Article.STATUS_PUBLISHED)
        totals = dict(embedded=0, reused=0, deleted=0, total=0, pending=0)
        failures = 0
        for article in articles.iterator():
            try:
                stats = reindex_article(article, dry_run=options['dry_run'], force=options['force'])
                for key in totals:
                    totals[key] += stats.get(key, 0)
                self.stdout.write(f'{article.pk}: {stats}')
            except Exception as exc:
                failures += 1
                if not options['dry_run'] and Article.objects.filter(pk=article.pk).exists():
                    ArticleIndexState.objects.update_or_create(article=article,
                        defaults={'status': 'error', 'last_error': type(exc).__name__[:100]})
                self.stderr.write(f'{article.pk}: indexing failed ({type(exc).__name__})')
        self.stdout.write(f'Totals: {totals}; failures={failures}')
        if failures:
            raise CommandError('Some articles failed; existing committed indexes were preserved')

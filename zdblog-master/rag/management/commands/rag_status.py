import json
from django.core.management.base import BaseCommand
from article.models import Article
from rag.models import ArticleChunk, ArticleIndexState
from rag.indexer import source_hash
from rag.embeddings import fingerprint, embedding_configured
from rag.config import VECTOR_DIMENSIONS


class Command(BaseCommand):
    help = 'Show current public corpus, pending vectors, model mismatch and stale indexes'

    def handle(self, *args, **options):
        articles = list(Article.objects.filter(status=Article.STATUS_PUBLISHED))
        states = {s.article_id: s for s in ArticleIndexState.objects.all()}
        chunks = ArticleChunk.objects.filter(article__status=Article.STATUS_PUBLISHED)
        embedded = chunks.filter(embedding__isnull=False, embed_fingerprint=fingerprint()).count()
        data = {'published_articles': len(articles), 'chunks': chunks.count(), 'embedded': embedded,
                'pending': chunks.count() - embedded, 'embedding_configured': embedding_configured(),
                'vector_payload_bytes': embedded * VECTOR_DIMENSIONS * 4,
                'stale_articles': [a.pk for a in articles if a.pk not in states or states[a.pk].source_hash != source_hash(a)],
                'error_articles': [s.article_id for s in states.values() if s.status == 'error'],
                'model_mismatch_articles': [s.article_id for s in states.values() if s.embed_fingerprint != fingerprint()]}
        self.stdout.write(json.dumps(data, ensure_ascii=False, indent=2))

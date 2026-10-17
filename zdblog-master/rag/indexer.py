import hashlib
import json
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from article.models import Article
from .embeddings import embed_documents, embedding_configured, fingerprint, validate_vector
from .models import ArticleChunk, ArticleIndexState


def source_hash(article):
    # Counters and updated_at are deliberately excluded; queryset content updates are detected.
    payload = [article.title, article.summary, article.content_md, article.status]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()


def split_article(article):
    size, overlap = settings.RAG_CHUNK_SIZE, settings.RAG_CHUNK_OVERLAP
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError('RAG_CHUNK_OVERLAP must be nonnegative and smaller than RAG_CHUNK_SIZE')
    splitter = RecursiveCharacterTextSplitter(chunk_size=size, chunk_overlap=overlap,
        separators=['\n\n', '\n', '。', '！', '？', '；', '，', ' ', ''])
    sections = MarkdownHeaderTextSplitter(headers_to_split_on=[('#', 'h1'), ('##', 'h2'), ('###', 'h3'), ('####', 'h4')],
                                         strip_headers=False).split_text(article.content_md or '')
    pieces = []
    for section in sections:
        path = ' > '.join(section.metadata[k] for k in ['h1', 'h2', 'h3', 'h4'] if k in section.metadata)
        # Keep long heading paths from dominating the embedding input.
        prefix = f'《{article.title[:40]}》' + (f' > {path[:40]}' if path else '')
        bodies = splitter.split_text(section.page_content)
        # Do not discard short sections: they can contain critical facts or code.
        if len(bodies) > 1 and len(bodies[-1]) < settings.RAG_MIN_CHUNK_CHARS:
            bodies[-2:] = [bodies[-2] + '\n' + bodies[-1]]
        for raw in bodies:
            if not raw.strip():
                continue
            content = f'{prefix}\n{raw.strip()}'
            pieces.append({'heading': path, 'content': content, 'char_count': len(content),
                           'content_hash': hashlib.sha256(content.encode()).hexdigest()})
    return pieces


def reindex_article(article, dry_run=False, force=False):
    # Reload instead of trusting a stale post_save instance.
    article = Article.objects.filter(pk=article.pk).first()
    if article is None:
        return {'embedded': 0, 'reused': 0, 'deleted': 0, 'total': 0, 'superseded': True}
    version = source_hash(article)
    pieces = split_article(article) if article.status == Article.STATUS_PUBLISHED else []
    model_id = fingerprint()
    old = {c.content_hash: c for c in article.chunks.filter(embed_fingerprint=model_id, embedding__isnull=False)}
    todo = {p['content_hash']: p for p in pieces if force or p['content_hash'] not in old}
    configured = settings.RAG_ENABLED and embedding_configured()
    stats = {'embedded': len(todo) if configured else 0,
             'reused': sum(p['content_hash'] in old and not force for p in pieces),
             'deleted': article.chunks.count(), 'total': len(pieces),
             'pending': sum(p['content_hash'] in todo for p in pieces) if not configured else 0}
    if dry_run:
        return stats
    vectors = {key: (list(c.embedding), c.embedded_at) for key, c in old.items()}
    if todo and configured:
        values = embed_documents([p['content'] for p in todo.values()])
        if len(values) != len(todo):
            raise ValueError('Embedding response count mismatch')
        vectors.update({key: (validate_vector(v), timezone.now()) for key, v in zip(todo, values)})
    with transaction.atomic():
        current = Article.objects.select_for_update().filter(pk=article.pk).first()
        if current is None or source_hash(current) != version:
            return {**stats, 'superseded': True}
        article.chunks.all().delete()
        rows = []
        for ordinal, piece in enumerate(pieces):
            vector, timestamp = vectors.get(piece['content_hash'], (None, None))
            rows.append(ArticleChunk(article=current, ordinal=ordinal, **piece, source_hash=version,
                        embedding=vector, embedded_at=timestamp, embed_fingerprint=model_id if vector is not None else ''))
        ArticleChunk.objects.bulk_create(rows)
        ArticleIndexState.objects.update_or_create(article=current, defaults={
            'source_hash': version, 'embed_fingerprint': model_id,
            'status': 'ready' if not stats['pending'] else 'pending',
            'indexed_at': timezone.now(), 'last_error': '',
        })
    return stats

import logging
from django.conf import settings
from django.db.models import Q
from article.models import Article
from .embeddings import embedding_configured, embed_query
from .indexer import source_hash
from .models import ArticleChunk
from .store import search_dense, search_lexical, query_terms

logger = logging.getLogger(__name__)
RRF_K = 60


def rrf(rank_lists):
    scores = {}
    for ids in rank_lists:
        for rank, key in enumerate(dict.fromkeys(ids), 1):
            scores[key] = scores.get(key, 0) + 1 / (RRF_K + rank)
    return sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))


def hit(article, content, heading='', chunk_id=None, score=0.0, query=''):
    limit = settings.RAG_SNIPPET_CHARS
    # Center the snippet around the first matching term instead of always returning the intro.
    offsets = [content.lower().find(t.lower()) for t in query_terms(query)]
    offsets = [offset for offset in offsets if offset >= 0]
    start = max(0, min(offsets) - 60) if offsets else 0
    snippet = ('…' if start else '') + content[start:start + limit]
    if len(content) > start + limit:
        snippet += '…'
    return {'chunk_id': chunk_id, 'article_id': article.pk, 'title': article.title,
            'heading': heading, 'snippet': snippet, 'url': f'/article/{article.pk}', 'score': round(score, 6)}


def keyword_articles(query, top_k):
    """Live article fallback also covers not-yet-indexed or stale content."""
    terms = query_terms(query) or [query]
    filters = Q()
    for term in terms:
        filters |= Q(title__icontains=term) | Q(summary__icontains=term) | Q(content_md__icontains=term)
    articles = Article.objects.filter(status=Article.STATUS_PUBLISHED).filter(filters).order_by('-published_at', 'id')[:100]
    ranked = sorted(articles, key=lambda a: -sum(t.lower() in f'{a.title}\n{a.summary}\n{a.content_md}'.lower() for t in terms))
    return [hit(a, a.content_md or a.summary, query=query) for a in ranked[:top_k]]


def retrieve(query, top_k=None, candidate_k=None):
    query = str(query).strip()[:1000]
    if not query or not settings.RAG_ENABLED:
        return []
    top_k = min(20, max(1, top_k or settings.RAG_TOP_K))
    candidate_k = min(100, max(top_k, candidate_k or settings.RAG_CANDIDATE_K))
    dense, lexical = [], []
    if embedding_configured():
        try:
            dense = [key for key, _, score in search_dense(embed_query(query), candidate_k)
                     if score >= settings.RAG_MIN_DENSE_SCORE]
        except Exception as exc:
            logger.warning('RAG dense retrieval unavailable (%s)', type(exc).__name__)
    try:
        lexical = [key for key, score in search_lexical(query, candidate_k)
                   if score >= settings.RAG_MIN_LEXICAL_SCORE]
    except Exception as exc:
        logger.warning('RAG lexical chunk retrieval unavailable (%s)', type(exc).__name__)
    fused = rrf([dense, lexical])
    chunks = {c.pk: c for c in ArticleChunk.objects.select_related('article').filter(
        pk__in=[key for key, _ in fused], article__status=Article.STATUS_PUBLISHED)} if fused else {}
    results, seen = [], set()
    versions = {}
    for key, score in fused:
        chunk = chunks.get(key)
        if chunk is None or chunk.article_id in seen:
            continue
        version = versions.setdefault(chunk.article_id, source_hash(chunk.article))
        if chunk.source_hash != version:
            continue  # Never return stale text after queryset edits or failed reindexing.
        results.append(hit(chunk.article, chunk.content, chunk.heading, chunk.pk, score, query))
        seen.add(chunk.article_id)
        if len(results) >= top_k:
            break
    for result in keyword_articles(query, top_k):
        if len(results) >= top_k:
            break
        if result['article_id'] not in seen:
            seen.add(result['article_id'])
            results.append(result)
    return results


def format_tool_result(hits):
    """Bound output by whole citations; never cut a URL in half."""
    if not hits:
        return '站内未找到相关文章。'
    blocks = []
    remaining = settings.RAG_TOOL_MAX_CHARS
    for result in hits:
        title = result['title'].replace('[', '［').replace(']', '］').replace('\n', ' ')
        header = f'来源：[《{title}》]({result["url"]})\n'
        available = remaining - len(header) - 2
        if available < 40:
            break
        snippet = result['snippet'][:available]
        block = header + snippet
        blocks.append(block)
        remaining -= len(block) + 2
    return '\n\n'.join(blocks)

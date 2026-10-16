"""Stateless PostgreSQL dense and lexical candidate retrieval."""
import re
from django.conf import settings
from django.db import connection, transaction
from .embeddings import fingerprint, validate_vector


def search_dense(query_vector, top_k=20):
    literal = '[' + ','.join(str(v) for v in validate_vector(query_vector)) + ']'
    with connection.cursor() as cursor:
        cursor.execute(
            'SELECT c.id, c.article_id, 1 - (c.embedding <=> %s::vector) AS score '
            'FROM article_chunk c JOIN article a ON a.id = c.article_id '
            "WHERE a.status = 'published' AND c.embedding IS NOT NULL AND c.embed_fingerprint = %s "
            'ORDER BY c.embedding <=> %s::vector LIMIT %s', [literal, fingerprint(), literal, top_k])
        return [(row[0], row[1], float(row[2])) for row in cursor.fetchall()]


def query_terms(query):
    terms = re.findall(r'[A-Za-z0-9_][A-Za-z0-9_+.#-]*', query)
    chinese = re.findall(r'[\u4e00-\u9fff]+', query)
    noise = r'有没有|写过|本站|站内|博客|文章|哪篇|那篇|关于|如何|怎么|什么|介绍|解释|说了|讲了|内容|能否|请问|请|里的|的|吗|呢|我|了|哪|篇|讲'
    for part in chinese:
        terms.extend(t for t in re.split(noise, part) if len(t) >= 2)
    return list(dict.fromkeys([t for t in terms if len(t) >= 2]))[:12]


def search_lexical(query, top_k=20):
    terms = query_terms(query) or [query]
    terms = list(dict.fromkeys([query, *terms]))[:13]
    scores = ', '.join('word_similarity(%s, c.content)' for _ in terms)
    filters, params = [], list(terms)
    for term in terms:
        filters.append('(c.content ILIKE %s OR c.content %%> %s)')
        escaped = term.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        params.extend([f'%{escaped}%', term])
    sql = (f'SELECT c.id, GREATEST({scores}) AS score FROM article_chunk c '
           'JOIN article a ON a.id = c.article_id '
           "WHERE a.status = 'published' AND (" + ' OR '.join(filters) + ') '
           'ORDER BY score DESC, c.article_id, c.ordinal LIMIT %s')
    params.append(top_k)
    # Savepoint keeps a lexical SQL failure from poisoning an outer transaction.
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('pg_trgm.word_similarity_threshold', %s, true)",
                           [str(settings.RAG_MIN_LEXICAL_SCORE)])
            cursor.execute(sql, params)
            return [(row[0], float(row[1])) for row in cursor.fetchall()]

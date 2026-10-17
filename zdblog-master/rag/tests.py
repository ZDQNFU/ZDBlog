from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch
from django.core.management import call_command
from django.db import transaction, connection
from django.test import TestCase, SimpleTestCase, override_settings
from article.models import Article
from chat_robot.models import ChatPersona, ChatConversation
from chat_robot.serializers import PersonaSerializer
from .embeddings import validate_vector
from .indexer import reindex_article, split_article, source_hash
from .models import ArticleChunk, ArticleIndexState
from .retriever import retrieve, format_tool_result, rrf
from .store import search_dense, search_lexical
from .evaluation import evaluate_cases


def vector(axis=0):
    result = [0.0] * 1024
    result[axis] = 1.0
    return result


class PureTests(SimpleTestCase):
    def test_short_sections_and_heading_paths_survive(self):
        article = SimpleNamespace(title='标题', content_md='# 第一节\n关键事实\n## 二级\n只有七字\n')
        pieces = split_article(article)
        self.assertEqual(len(pieces), 2)
        self.assertIn('第一节 > 二级', pieces[1]['heading'])
        self.assertIn('只有七字', pieces[1]['content'])

    def test_rrf_deduplicates_each_leg(self):
        self.assertEqual(rrf([['a', 'a'], ['b', 'a']])[0][0], 'a')

    def test_vector_validation(self):
        self.assertEqual(len(validate_vector(vector())), 1024)
        for value in [[1] * 512, [0] * 1024, [float('nan')] * 1024, [float('inf')] * 1024]:
            with self.assertRaises(ValueError):
                validate_vector(value)

    def test_tool_budget_preserves_complete_links(self):
        hits = [{'title': '很长的标题' * 30, 'url': '/article/' + str(i) * 32, 'snippet': '正文' * 1000} for i in range(5)]
        output = format_tool_result(hits)
        self.assertLessEqual(len(output), 1500)
        self.assertIn('](/article/' + '0' * 32 + ')', output)
        self.assertEqual(format_tool_result([]), '站内未找到相关文章。')

    def test_recall_differs_from_hit_rate_for_multi_article_cases(self):
        scores = evaluate_cases([{'q': 'q', 'expect': ['a', 'b']}, {'q': 'absent', 'expect': []}],
                                lambda query, top_k: [{'article_id': 'a'}] if query == 'q' else [], 5)
        self.assertEqual(scores['recall'], 0.5)
        self.assertEqual(scores['hit_rate'], 1)
        self.assertEqual(scores['negative_accuracy'], 1)


class PostgresTests(TestCase):
    def article(self, title='MySQL 索引', content='B+Tree 索引通过树结构提高 MySQL 查询效率。', status='published'):
        return Article.objects.create(title=title, slug='s-' + str(Article.objects.count()), content_md=content, status=status)

    def test_schema_really_uses_pgvector_and_trigrams(self):
        self.assertEqual(connection.vendor, 'postgresql')
        with connection.cursor() as cursor:
            cursor.execute("SELECT format_type(atttypid, atttypmod) FROM pg_attribute WHERE attrelid='article_chunk'::regclass AND attname='embedding'")
            self.assertEqual(cursor.fetchone()[0], 'vector(1024)')
            cursor.execute("SELECT extname FROM pg_extension WHERE extname IN ('vector', 'pg_trgm')")
            self.assertEqual({row[0] for row in cursor.fetchall()}, {'vector', 'pg_trgm'})

    def test_lexical_pending_index_and_live_fallback(self):
        article = self.article()
        stats = reindex_article(article)
        self.assertEqual(stats['pending'], 1)
        self.assertEqual(ArticleIndexState.objects.get(article=article).status, 'pending')
        self.assertTrue(search_lexical('B+Tree'))
        self.assertEqual(retrieve('MySQL 索引')[0]['article_id'], article.pk)
        article.chunks.all().delete()
        self.assertEqual(retrieve('MySQL 索引')[0]['article_id'], article.pk)
        self.assertEqual(retrieve('k8s operator'), [])

    @override_settings(RAG_EMBED_BASE_URL='http://test', RAG_EMBED_API_KEY='test')
    def test_real_sql_dense_reuse_and_model_space_isolation(self):
        article = self.article()
        with patch('rag.indexer.embed_documents', return_value=[vector()]) as embed:
            reindex_article(article)
            reindex_article(article)
            self.assertEqual(embed.call_count, 1)
        self.assertEqual(search_dense(vector())[0][1], article.pk)
        with override_settings(RAG_EMBED_MODEL='different-model'):
            self.assertEqual(search_dense(vector()), [])
        with patch('rag.retriever.embed_query', return_value=vector(1)):
            self.assertEqual(retrieve('Rust ownership'), [])

    def test_nonpublic_never_returns_even_with_leftover_chunks(self):
        article = self.article()
        reindex_article(article)
        Article.objects.filter(pk=article.pk).update(status='private')
        self.assertEqual(retrieve('MySQL'), [])
        self.assertEqual(search_lexical('MySQL'), [])
        article.refresh_from_db()
        reindex_article(article)
        self.assertEqual(article.chunks.count(), 0)
        article.delete()
        self.assertEqual(ArticleIndexState.objects.count(), 0)

    def test_queryset_edit_never_returns_stale_snippets(self):
        article = self.article()
        reindex_article(article)
        Article.objects.filter(pk=article.pk).update(content_md='MySQL 全新正文，只使用最新版本的索引说明。')
        hits = retrieve('MySQL')
        self.assertEqual(len(hits), 1)
        self.assertIn('全新正文', hits[0]['snippet'])
        self.assertNotIn('B+Tree', hits[0]['snippet'])

    @override_settings(RAG_EMBED_BASE_URL='http://test', RAG_EMBED_API_KEY='test')
    def test_concurrent_content_change_does_not_commit_old_index(self):
        article = self.article()
        def embedding(texts):
            Article.objects.filter(pk=article.pk).update(content_md='并发更新后的正文')
            return [vector() for _ in texts]
        with patch('rag.indexer.embed_documents', side_effect=embedding):
            stats = reindex_article(article)
        self.assertTrue(stats['superseded'])
        self.assertEqual(article.chunks.count(), 0)

    @override_settings(RAG_EMBED_BASE_URL='http://test', RAG_EMBED_API_KEY='test')
    def test_embedding_failure_preserves_old_index_and_save_success(self):
        article = self.article()
        with patch('rag.indexer.embed_documents', return_value=[vector()]):
            reindex_article(article)
        before = list(article.chunks.values_list('pk', flat=True))
        with patch('rag.indexer.embed_documents', side_effect=RuntimeError('secret-api-error')):
            with self.assertLogs('rag.signals', level='WARNING') as logs, self.captureOnCommitCallbacks(execute=True):
                article.content_md = '新版本 MySQL 正文'
                article.save()
            self.assertNotIn('secret-api-error', ''.join(logs.output))
        article.refresh_from_db()
        self.assertEqual(article.content_md, '新版本 MySQL 正文')
        self.assertEqual(list(article.chunks.values_list('pk', flat=True)), before)
        self.assertEqual(ArticleIndexState.objects.get(article=article).status, 'error')

    def test_save_sync_and_counter_changes_ignored(self):
        with self.captureOnCommitCallbacks(execute=True):
            article = self.article()
        self.assertEqual(article.chunks.count(), 1)
        with self.captureOnCommitCallbacks(execute=True), patch('rag.signals.sync_article') as sync:
            article.like_count = 1
            article.save(update_fields=['like_count'])
            self.assertFalse(sync.called)
        with self.captureOnCommitCallbacks(execute=True):
            article.status = 'draft'
            article.save(update_fields=['status'])
        self.assertEqual(article.chunks.count(), 0)

    def test_lexical_sql_failure_uses_savepoint(self):
        article = self.article()
        reindex_article(article)
        # Missing lexical operator or extension should be recoverable by the caller.
        with patch('rag.retriever.search_lexical', side_effect=RuntimeError('failed')), self.assertLogs('rag.retriever'):
            self.assertEqual(retrieve('MySQL')[0]['article_id'], article.pk)
        self.assertTrue(Article.objects.exists())

    def test_dry_run_and_status_commands(self):
        article = self.article()
        output = StringIO()
        call_command('rag_reindex', dry_run=True, stdout=output)
        self.assertEqual(article.chunks.count(), 0)
        reindex_article(article)
        output = StringIO()
        call_command('rag_status', stdout=output)
        self.assertIn('"pending": 1', output.getvalue())

    def test_tools_validation_empty_list_and_snapshot(self):
        serializer = PersonaSerializer(data={'name': '工具配置', 'system_prompt': 'prompt', 'tools': []})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        persona = serializer.save()
        self.assertEqual(persona.tools, [])
        for tools in [['bad'], ['search_blog', 'search_blog']]:
            self.assertFalse(PersonaSerializer(data={'name': 'x', 'system_prompt': 'p', 'tools': tools}).is_valid())

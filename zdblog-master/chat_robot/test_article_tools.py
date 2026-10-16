import importlib
import json
import runpy
from datetime import datetime, timezone as dt_timezone
from types import SimpleNamespace
from unittest import skipUnless
from unittest.mock import Mock, patch
from django.apps import apps
from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase, TransactionTestCase, SimpleTestCase, override_settings
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from .article_tools import list_articles, count_articles, get_article
from .models import ChatPersona, ChatConversation
from .tool_config import ARTICLE_TOOLS, BLOG_RULES


@skipUnless(apps.is_installed('article'), 'Requires the PostgreSQL rag.test_settings suite')
@override_settings(RAG_ENABLED=False)
class ArticleToolsTests(TestCase):
    def article(self, title, published=None, updated=None, status='published', content='正文'):
        from article.models import Article
        article = Article.objects.create(title=title, slug='s-' + str(Article.objects.count()),
                                         content_md=content, summary='文章简介', status=status,
                                         published_at=published)
        if updated:
            Article.objects.filter(pk=article.pk).update(updated_at=updated)
        return article

    def utc(self, day, hour=0):
        return datetime(2026, 10, day, hour, tzinfo=dt_timezone.utc)

    def test_latest_means_publication_date_and_private_never_appears(self):
        older = self.article('旧文章', self.utc(1), self.utc(5))
        latest = self.article('新文章', self.utc(3), self.utc(3))
        unknown = self.article('未记录发布时间', updated=self.utc(2))
        self.article('私密文章', self.utc(6), status='private')
        self.article('草稿', self.utc(7), status='draft')
        data = json.loads(list_articles.invoke({}))
        self.assertEqual([a['article_id'] for a in data['articles']], [latest.pk, older.pk, unknown.pk])
        self.assertEqual(data['total'], 3)
        self.assertEqual(data['articles'][-1]['published_at'], None)
        self.assertIn('+08:00', data['articles'][0]['published_at'])
        updated = json.loads(list_articles.invoke({'sort': 'updated_at', 'limit': 1}))
        self.assertEqual(updated['articles'][0]['article_id'], older.pk)
        self.assertTrue(updated['has_more'])
        page = json.loads(list_articles.invoke({'limit': 1, 'offset': 1}))
        self.assertEqual(page['articles'][0]['article_id'], older.pk)

    def test_date_filters_are_inclusive_and_use_china_timezone(self):
        self.article('范围前', self.utc(2, 15))
        first = self.article('当地零点', self.utc(2, 16))
        last = self.article('当地末尾', self.utc(3, 15))
        self.article('范围后', self.utc(3, 16))
        self.article('未知日期')
        params = {'start_date': '2026-10-03', 'end_date': '2026-10-03'}
        data = json.loads(list_articles.invoke(params))
        self.assertEqual({a['article_id'] for a in data['articles']}, {first.pk, last.pk})
        self.assertEqual(json.loads(count_articles.invoke(params))['total'], 2)
        self.assertEqual(json.loads(count_articles.invoke({}))['total'], 5)
        self.assertEqual(data['timezone'], 'Asia/Shanghai')

    def test_count_is_exact_and_keyword_filter_is_structured(self):
        for i in range(12):
            self.article(f'Django 文章 {i}', self.utc(1))
        self.article('其他文章', self.utc(2))
        listing = json.loads(list_articles.invoke({'keyword': 'Django'}))
        self.assertEqual(len(listing['articles']), 5)
        self.assertEqual(listing['total'], 12)
        self.assertEqual(json.loads(count_articles.invoke({'keyword': 'Django'}))['total'], 12)

    def test_full_read_is_paged_and_private_ids_do_not_leak(self):
        body = '文章中的重要正文\n' * 100
        article = self.article('公开文章', content=body)
        private = self.article('私密标题', status='private', content='私密正文')
        first = json.loads(get_article.invoke({'article_id': article.pk, 'max_chars': 500}))
        second = json.loads(get_article.invoke({'article_id': article.pk, 'offset': first['next_offset']}))
        self.assertTrue(first['has_more'])
        self.assertFalse(second['has_more'])
        self.assertEqual(first['content'] + second['content'], body)
        self.assertEqual(first['url'], f'/article/{article.pk}')
        output = get_article.invoke({'article_id': private.pk})
        self.assertFalse(json.loads(output)['found'])
        self.assertNotIn('私密标题', output)
        self.assertNotIn('私密正文', output)

    def test_invalid_ranges_and_ids_return_clear_errors(self):
        for params in [{'start_date': '2026-02-30'}, {'start_date': '2026-10-03', 'end_date': '2026-10-01'},
                       {'limit': 20}, {'offset': -1}, {'keyword': '长' * 201}]:
            self.assertIn('error', json.loads(list_articles.invoke(params)))
        self.assertIn('error', json.loads(get_article.invoke({'article_id': 'bad'})))
        self.assertEqual(json.loads(list_articles.invoke({}))['articles'], [])

    def test_upgrade_preserves_custom_prompts_and_disabled_tools(self):
        migration = importlib.import_module('chat_robot.migrations.0007_article_query_tools')
        persona = ChatPersona.objects.create(name='自定义知识助手', tools=['search_blog'],
                                            system_prompt='自定义语气' + migration.OLD_RULES)
        disabled = ChatPersona.objects.create(name='关闭工具', tools=[], system_prompt='不启用工具')
        user = User.objects.create_user(username='upgrade-user')
        conversation = ChatConversation.objects.create(user=user, persona_name=persona.name,
            system_prompt='快照角色' + migration.OLD_RULES, persona_tools=['search_blog'],
            agent_messages=[{'old': 'history'}])
        migration.forwards(apps, SimpleNamespace(connection=connection))
        migration.forwards(apps, SimpleNamespace(connection=connection))
        persona.refresh_from_db()
        disabled.refresh_from_db()
        conversation.refresh_from_db()
        self.assertEqual(persona.tools, ['search_blog', *ARTICLE_TOOLS])
        self.assertEqual(persona.system_prompt, '自定义语气')
        self.assertEqual(conversation.system_prompt, '快照角色')
        self.assertEqual(conversation.persona_tools, persona.tools)
        self.assertEqual(conversation.agent_messages, [{'old': 'history'}])
        self.assertEqual(disabled.tools, [])

@skipUnless(apps.is_installed('article'), 'Requires the PostgreSQL rag.test_settings suite')
@override_settings(RAG_ENABLED=False)
class ArticleToolLoopTests(TransactionTestCase):
    def test_real_agent_executes_structured_tool_instead_of_rag(self):
        from article.models import Article
        Article.objects.create(title='最新文章', slug='agent-list', status='published', content_md='正文',
                               published_at=datetime(2026, 10, 3, tzinfo=dt_timezone.utc))

        class Model(FakeMessagesListChatModel):
            def bind_tools(self, tools, **kwargs):
                return self

        model = Model(responses=[AIMessage(content='', tool_calls=[{
            'name': 'list_articles', 'args': {'sort': 'published_at', 'limit': 5},
            'id': 'list1', 'type': 'tool_call'}]), AIMessage(content='最新发布的是最新文章。')])
        with patch('chat_robot.utils.get_llm_model', return_value=model):
            factory = runpy.run_module('chat_robot.agent')['build_agent']
        state = factory('博客助手', ['list_articles']).invoke(
            {'messages': [HumanMessage(content='最近有什么新文章？')]})
        evidence = next(m for m in state['messages'] if isinstance(m, ToolMessage))
        self.assertEqual(json.loads(evidence.content)['articles'][0]['title'], '最新文章')


class ArticleRoutingTests(SimpleTestCase):
    def test_routing_rules_reach_graph_without_extra_model_or_disabled_tools(self):
        with patch('chat_robot.utils.get_llm_model', return_value=Mock()):
            factory = runpy.run_module('chat_robot.agent')['build_agent']
        with patch.dict(factory.__globals__, {'create_agent': Mock()}):
            factory('人物快照', ['list_articles'])
            args = factory.__globals__['create_agent'].call_args.kwargs
            self.assertIn(BLOG_RULES, args['system_prompt'])
            self.assertIn('Asia/Shanghai', args['system_prompt'])
            self.assertEqual([t.name for t in args['tools']], ['list_articles'])
            factory('人物快照', [])
            self.assertEqual(factory.__globals__['create_agent'].call_args.kwargs['system_prompt'], '人物快照')

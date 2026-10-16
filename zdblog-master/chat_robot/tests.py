import json
import logging
import sys
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import connections
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, SimpleTestCase
from django.utils import timezone
from rest_framework.test import APIClient
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage, messages_from_dict

from .models import ChatConversation, ChatMessage, ChatPersona
from .utils import stream_chat_with_agent


class FakeGraph:
    def __init__(self, fail=False):
        self.inputs = []
        self.fail = fail

    def stream(self, inputs, **kwargs):
        self.inputs.append(inputs['messages'])
        yield 'messages', (AIMessageChunk(content='你好'), {'langgraph_node': 'model'})
        if self.fail:
            raise RuntimeError('private-provider-details')
        yield 'messages', (AIMessageChunk(content='\n\n世界'), {'langgraph_node': 'model'})
        yield 'values', {'messages': [*inputs['messages'], AIMessage(
            content='你好\n\n世界', additional_kwargs={'reasoning_content': 'private-reasoning'},
        )]}


class ChatAPITests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user('staff', is_staff=True)
        self.other = User.objects.create_user('other', is_staff=True)
        self.reader = User.objects.create_user('reader')
        self.client = APIClient()
        self.client.force_authenticate(self.staff)
        self.persona = ChatPersona.objects.create(name='测试人物', system_prompt='测试设定', greeting='你好')

    def create_conversation(self, user=None):
        return ChatConversation.objects.create(user=user or self.staff, persona=self.persona,
            persona_name=self.persona.name, system_prompt=self.persona.system_prompt, greeting=self.persona.greeting)

    def consume(self, response):
        self.assertEqual(response.status_code, 200)
        return ''.join(c.decode() if isinstance(c, bytes) else c for c in response.streaming_content)

    def send(self, conversation, graph, text='第一句话'):
        with patch.dict(sys.modules, {'chat_robot.agent': SimpleNamespace(build_agent=lambda prompt, tool_names=None: graph)}):
            return self.consume(self.client.post('/stream/', {'conversation_id': conversation.pk, 'message': text}, format='json'))

    def test_persona_crud_and_validation(self):
        response = self.client.post('/manage/personas/', {'name': '新人物', 'system_prompt': '新的设定'}, format='json')
        self.assertEqual(response.status_code, 201)
        pk = response.data['id']
        self.assertEqual(self.client.get(f'/manage/personas/{pk}/').data['system_prompt'], '新的设定')
        self.assertEqual(self.client.patch(f'/manage/personas/{pk}/', {'greeting': '欢迎', 'is_active': False}, format='json').status_code, 200)
        self.assertEqual(self.client.post('/manage/personas/', {'name': '新人物', 'system_prompt': '重复'}, format='json').status_code, 400)
        self.assertEqual(self.client.post('/manage/personas/', {'name': '空设定', 'system_prompt': '  '}, format='json').status_code, 400)
        self.assertEqual(self.client.delete(f'/manage/personas/{pk}/').status_code, 204)

    def test_persona_visibility_and_staff_permissions(self):
        ChatPersona.objects.create(name='隐藏', system_prompt='秘密', is_active=False)
        self.client.force_authenticate(self.reader)
        public = self.client.get('/personas/').data
        self.assertNotIn('隐藏', [p['name'] for p in public])
        self.assertTrue(all('system_prompt' not in p for p in public))
        self.assertEqual(self.client.get('/manage/personas/').status_code, 403)
        self.assertEqual(self.client.post('/stream/', {}, format='json').status_code, 403)
        self.assertEqual(APIClient().get('/conversations/').status_code, 403)

    def test_conversation_snapshot_and_persona_deletion(self):
        response = self.client.post('/conversations/', {'persona_id': self.persona.pk}, format='json')
        self.assertEqual(response.status_code, 201)
        conversation = ChatConversation.objects.get(pk=response.data['id'])
        self.persona.system_prompt = '新设定'
        self.persona.save()
        self.persona.delete()
        conversation.refresh_from_db()
        self.assertIsNone(conversation.persona_id)
        self.assertEqual(conversation.system_prompt, '测试设定')
        self.assertEqual(conversation.persona_tools, ['get_weather', 'search_func'])
        self.assertNotIn('system_prompt', response.data)

    def test_inactive_and_missing_persona(self):
        self.persona.is_active = False
        self.persona.save()
        for pk in [self.persona.pk, 'missing']:
            self.assertEqual(self.client.post('/conversations/', {'persona_id': pk}, format='json').status_code, 400)

    def test_owner_isolation(self):
        c = self.create_conversation(self.other)
        self.assertEqual(self.client.get('/conversations/').data['conversations'], [])
        self.assertEqual(self.client.get(f'/conversations/{c.pk}/').status_code, 404)
        self.assertEqual(self.client.patch(f'/conversations/{c.pk}/', {'title': '篡改'}, format='json').status_code, 404)
        self.assertEqual(self.client.delete(f'/conversations/{c.pk}/').status_code, 404)
        self.assertEqual(self.client.get(f'/history/?conversation_id={c.pk}').status_code, 404)
        self.assertEqual(self.client.post('/stream/', {'conversation_id': c.pk, 'message': '篡改'}, format='json').status_code, 404)

    def test_rename_and_cascade_delete(self):
        c = self.create_conversation()
        ChatMessage.objects.create(conversation=c, user=self.staff, role='user', content='旧消息')
        self.assertEqual(self.client.patch(f'/conversations/{c.pk}/', {'title': '新标题'}, format='json').status_code, 200)
        self.assertEqual(self.client.patch(f'/conversations/{c.pk}/', {'title': ''}, format='json').status_code, 400)
        self.assertEqual(self.client.delete(f'/conversations/{c.pk}/').status_code, 204)
        self.assertFalse(ChatMessage.objects.filter(conversation_id=c.pk).exists())

    def test_stream_persistence_and_independent_context(self):
        first, second = self.create_conversation(), self.create_conversation()
        graph = FakeGraph()
        self.assertIn('"done": true', self.send(first, graph))
        first.refresh_from_db()
        self.assertEqual(first.title, '第一句话')
        self.assertEqual(first.messages.count(), 2)
        restored = messages_from_dict(first.agent_messages)
        self.assertEqual(restored[-1].additional_kwargs['reasoning_content'], 'private-reasoning')
        self.send(second, graph, '另外的话')
        self.assertEqual(len(graph.inputs[-1]), 1)
        # A fresh graph simulates a worker restart and still receives prior state.
        restarted = FakeGraph()
        self.send(first, restarted, '第二句话')
        self.assertEqual(len(restarted.inputs[-1]), 3)
        self.assertEqual(restarted.inputs[-1][0].content, '第一句话')
        self.assertEqual(first.messages.count(), 4)
        self.assertEqual(second.messages.count(), 2)

    def test_failed_stream_releases_lease_and_preserves_partial_response(self):
        c = self.create_conversation()
        with self.assertLogs('chat_robot.views', level=logging.ERROR):
            payload = self.send(c, FakeGraph(fail=True))
        self.assertIn('"error"', payload)
        self.assertNotIn('private-provider-details', payload)
        self.assertNotIn('"done"', payload)
        c.refresh_from_db()
        self.assertEqual(c.generation_id, '')
        self.assertEqual(c.agent_messages, [])
        self.assertEqual(c.messages.last().content, '你好')
        graph = FakeGraph()
        self.send(c, graph, '重试')
        self.assertEqual(len(graph.inputs[-1]), 3)

    def test_busy_conversation_and_expired_lease(self):
        c = self.create_conversation()
        response = self.client.post('/stream/', {'conversation_id': c.pk, 'message': '等待'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.post('/stream/', {'conversation_id': c.pk, 'message': '并发'}, format='json').status_code, 409)
        self.assertEqual(self.client.delete(f'/conversations/{c.pk}/').status_code, 409)
        self.assertEqual(self.client.post(f'/users/{self.staff.pk}/clear/').status_code, 409)
        self.assertEqual(self.client.post(f'/users/{self.staff.pk}/trim/', {'days': 30}, format='json').status_code, 409)
        # Worker crash: lease is abandoned before the generator starts.
        ChatConversation.objects.filter(pk=c.pk).update(generation_started_at=timezone.now() - timedelta(minutes=16))
        self.assertIn('"done": true', self.send(c, FakeGraph(), '恢复'))
        # The abandoned generator never started; closing an HTTP response here would
        # emit request_finished and close PostgreSQL's TestCase transaction.

    def test_admin_clear_and_trim_reset_agent_memory(self):
        c = self.create_conversation()
        self.send(c, FakeGraph())
        message = c.messages.first()
        ChatMessage.objects.filter(pk=message.pk).update(created_at=timezone.now() - timedelta(days=40))
        self.assertEqual(self.client.post(f'/users/{self.staff.pk}/trim/', {'days': 'bad'}, format='json').status_code, 400)
        self.assertEqual(self.client.post(f'/users/{self.staff.pk}/trim/', {'days': 30}, format='json').status_code, 200)
        c.refresh_from_db()
        self.assertEqual(c.agent_messages, [])
        self.assertEqual(c.messages.count(), 1)
        self.assertEqual(self.client.post(f'/users/{self.staff.pk}/clear/').status_code, 200)
        self.assertEqual(c.messages.count(), 0)
        self.assertEqual(self.client.get('/users/?page=bad').status_code, 400)

    def test_validation_and_conversation_grouping(self):
        c = self.create_conversation()
        for value in ['', ' ', None, {}, 'x' * 10001]:
            self.assertEqual(self.client.post('/stream/', {'conversation_id': c.pk, 'message': value}, format='json').status_code, 400)
        self.send(c, FakeGraph())
        detail = self.client.get(f'/users/{self.staff.pk}/').data
        self.assertEqual(detail['conversations'][0]['id'], c.pk)
        self.assertTrue(all(m['conversation_id'] == c.pk for m in detail['messages']))
        self.assertEqual(self.client.get('/users/').data['results'][0]['message_count'], 2)


class StreamingProjectionTests(SimpleTestCase):
    def test_real_agent_tool_loop_and_state_restore(self):
        import runpy
        from langchain.agents.middleware import wrap_tool_call
        from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
        from langchain_core.outputs import ChatGenerationChunk
        from langchain_core.tools import tool

        class Model(FakeMessagesListChatModel):
            def bind_tools(self, tools, **kwargs):
                return self

            def _stream(self, messages, stop=None, run_manager=None, **kwargs):
                result = self._generate(messages).generations[0].message
                yield ChatGenerationChunk(message=AIMessageChunk(
                    content=result.content, tool_calls=result.tool_calls,
                    additional_kwargs=result.additional_kwargs,
                ))

        @tool
        def weather():
            """Return deterministic test weather."""
            return '晴天'

        @wrap_tool_call
        def errors(request, handler):
            return handler(request)

        model = Model(responses=[AIMessage(content='', tool_calls=[{'name': 'weather', 'args': {}, 'id': 't1', 'type': 'tool_call'}]), AIMessage(content='今天天气晴朗')])
        fake_tools = SimpleNamespace(get_weather=weather, search_func=weather, search_blog=weather,
                                     analyze_sentiment=weather, handle_tool_errors=errors)
        with patch.dict(sys.modules, {'chat_robot.tools': fake_tools}), patch('chat_robot.utils.get_llm_model', return_value=model):
            factory = runpy.run_module('chat_robot.agent')['build_agent']
            graph = factory('你是一位测试助手')
            empty_tools_node = factory('关闭工具', tool_names=[]).get_graph().nodes['tools'].data
            self.assertFalse(empty_tools_node.tools_by_name)
            with self.assertRaises(ValueError):
                factory('无效配置', tool_names=['arbitrary-tool'])
        states = []
        output = ''.join(stream_chat_with_agent(graph, '今天天气？', on_state=states.append))
        self.assertEqual(output, '今天天气晴朗')
        self.assertTrue(any(isinstance(m, ToolMessage) for m in states[-1]))
        self.assertEqual(states[-1][-1].content, output)

    def test_filters_tools_and_summaries_and_preserves_whitespace(self):
        class Graph:
            def stream(self, *args, **kwargs):
                yield 'messages', (AIMessageChunk(content='内部总结'), {'langgraph_node': 'model', 'lc_source': 'summarization'})
                yield 'messages', (ToolMessage(content='内部数据', tool_call_id='t'), {'langgraph_node': 'tools'})
                yield 'messages', (AIMessageChunk(content='## SUMMARY 正常回答'), {'langgraph_node': 'model'})
                yield 'messages', (AIMessageChunk(content='\n\n'), {'langgraph_node': 'model'})
                yield 'messages', (AIMessageChunk(content='结尾'), {'langgraph_node': 'model'})
                yield 'values', {'messages': [HumanMessage(content='问题'), AIMessage(content='回答')]}
        states = []
        output = ''.join(stream_chat_with_agent(Graph(), '问题', on_state=states.append))
        self.assertEqual(output, '## SUMMARY 正常回答\n\n结尾')
        self.assertEqual(states[-1][-1].content, '回答')


class LegacyMigrationTests(SimpleTestCase):
    databases = {'default', 'migration'}

    def test_legacy_history_is_preserved(self):
        from django.db.backends.sqlite3.base import DatabaseWrapper
        original = connections['migration']
        connection = DatabaseWrapper({**original.settings_dict, 'NAME': ':memory:'}, alias='migration')
        connections['migration'] = connection
        self.addCleanup(lambda: setattr(connections, 'migration', original))
        self.addCleanup(connection.close)
        executor = MigrationExecutor(connection)
        old_target = [('chat_robot', '0002_rename_human_to_user')]
        executor.migrate(old_target)
        old_apps = executor.loader.project_state(old_target).apps
        user = old_apps.get_model('auth', 'User').objects.using('migration').create(username='legacy')
        Message = old_apps.get_model('chat_robot', 'ChatMessage')
        Message.objects.using('migration').create(user_id=user.pk, role='user', content='迁移前的消息')
        new_target = [('chat_robot', '0004_seed_personas_and_migrate_history')]
        executor = MigrationExecutor(connection)
        executor.migrate(new_target)
        apps = executor.loader.project_state(new_target).apps
        message = apps.get_model('chat_robot', 'ChatMessage').objects.using('migration').get()
        conversation = apps.get_model('chat_robot', 'ChatConversation').objects.using('migration').get()
        self.assertEqual(message.content, '迁移前的消息')
        self.assertEqual(message.conversation_id, conversation.pk)
        self.assertEqual(conversation.title, '历史聊天')
        self.assertEqual(conversation.persona_name, '明日香')
        self.assertEqual(apps.get_model('chat_robot', 'ChatPersona').objects.using('migration').count(), 2)

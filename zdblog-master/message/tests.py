from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from article.models import Article
from article.services.comment_text import content_fingerprint
from message.models import Message, MessageLike

User = get_user_model()


class MessageModerationTests(TestCase):
    create_url = '/api/messages/c/create/'
    list_url = '/api/messages/c/list/'
    admin_url = '/api/messages/s/messages/'

    def setUp(self):
        cache.clear()
        self.reader = User.objects.create_user(username='message-reader')
        self.admin = User.objects.create_user(username='message-moderator', is_staff=True)
        self.client = APIClient()
        self.staff_client = APIClient()
        self.staff_client.force_authenticate(self.admin)

    def submit(self, content='祝博客越来越好！', **extra):
        return self.client.post(self.create_url, {'content': content, **extra}, format='json')

    def review(self, message_id, status):
        return self.staff_client.patch(f'{self.admin_url}{message_id}/', {'status': status}, format='json')

    def test_friendly_anonymous_messages_publish_without_exposing_audit_fields(self):
        response = self.submit()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], 'approved')
        self.assertIn('发送成功', response.data['message'])
        row = self.client.get(self.list_url).data[0]
        self.assertEqual(row['user_name'], '游客')
        self.assertNotIn('moderation_reason', row)
        self.assertNotIn('reviewed_by', row)

    def test_anonymous_people_are_not_treated_as_one_duplicate_author(self):
        self.assertEqual(self.submit().data['status'], 'approved')
        response = self.client.post(self.create_url, {'content': '祝博客越来越好！'},
                                    format='json', REMOTE_ADDR='192.0.2.2')
        self.assertEqual(response.data['status'], 'approved')

    def test_authenticated_author_is_bound_by_server_and_duplicates_wait(self):
        self.client.force_authenticate(self.reader)
        first = self.submit(user=self.admin.pk)
        self.assertEqual(Message.objects.get(pk=first.data['id']).user, self.reader)
        self.assertEqual(self.submit().data['status'], 'pending')

    def test_obfuscated_blocked_content_cannot_forge_approval(self):
        response = self.submit('你这个傻\u200b Ｂ', status='approved', moderation_reason='已通过',
                               reviewed_by=self.admin.pk, user=self.admin.pk, is_hidden=0)
        self.assertEqual(response.data['status'], 'rejected')
        message = Message.objects.get(pk=response.data['id'])
        self.assertIsNone(message.user)
        self.assertIsNone(message.reviewed_by)
        self.assertTrue(message.moderation_reason)
        self.assertEqual(self.client.get(self.list_url).data, [])

    def test_keyword_changes_are_shared_between_comments_and_messages(self):
        keyword_url = '/api/articles/s/comment-keywords/'
        keyword = self.staff_client.post(keyword_url, {'word': '统一过滤词', 'action': 'reject'}, format='json')
        self.assertEqual(keyword.status_code, 201)
        detail_url = f'{keyword_url}{keyword.data["id"]}/'
        article = Article.objects.create(title='共用词库', slug='shared-keywords', status='published')
        comment_client = APIClient()
        comment_client.force_authenticate(self.reader)

        def comment(content):
            return comment_client.post('/api/articles/c/comments/',
                                       {'article': article.pk, 'content': content}, format='json')

        self.assertEqual(self.submit('第一条统一过滤词').data['status'], 'rejected')
        self.assertEqual(comment('第一条统一过滤词').data['status'], 'rejected')
        self.staff_client.patch(detail_url, {'action': 'review'}, format='json')
        self.assertEqual(self.submit('第二条统一过滤词').data['status'], 'pending')
        self.assertEqual(comment('第二条统一过滤词').data['status'], 'pending')
        self.staff_client.patch(detail_url, {'enabled': False}, format='json')
        self.assertEqual(self.submit('第三条统一过滤词').data['status'], 'approved')
        self.assertEqual(comment('第三条统一过滤词').data['status'], 'approved')

    def test_promotions_links_and_flooding_wait_for_review(self):
        for content in ('加微信领取资料', 'https://a.test https://b.test https://c.test', '😂' * 20):
            with self.subTest(content=content):
                self.assertEqual(self.submit(content).data['status'], 'pending')
        self.assertEqual(self.client.get(self.list_url).data, [])

    def test_public_visibility_and_likes_require_both_approval_and_not_hidden(self):
        visible = Message.objects.create(content='已公开', status='approved')
        pending = Message.objects.create(content='待审核')
        rejected = Message.objects.create(content='拒绝', status='rejected')
        hidden = Message.objects.create(content='隐藏', status='approved', is_hidden=1)
        self.client.force_authenticate(self.reader)
        self.assertEqual([row['id'] for row in self.client.get(self.list_url).data], [visible.pk])
        for message in (pending, rejected, hidden):
            url = f'/api/messages/c/{message.pk}/like/'
            self.assertEqual(self.client.post(url).status_code, 404)
            self.assertEqual(self.client.delete(url).status_code, 404)
        self.assertEqual(self.client.post(f'/api/messages/c/{visible.pk}/like/').status_code, 200)

    def test_public_list_ignores_stale_global_cache_and_updates_after_rejection(self):
        response = self.submit('一条即将被人工拒绝的留言')
        cache.set('c:messages', {'data': [{'content': '旧缓存不应再公开'}], 'status': 200})
        self.assertEqual(len(self.client.get(self.list_url).data), 1)
        self.review(response.data['id'], 'rejected')
        self.assertEqual(self.client.get(self.list_url).data, [])

    def test_liked_flags_are_isolated_between_viewers(self):
        message = Message.objects.create(content='点赞状态', status='approved')
        MessageLike.objects.create(message=message, user=self.reader)
        self.client.force_authenticate(self.reader)
        self.assertTrue(self.client.get(self.list_url).data[0]['user_has_liked'])
        self.client.force_authenticate(self.admin)
        self.assertFalse(self.client.get(self.list_url).data[0]['user_has_liked'])
        self.assertFalse(APIClient().get(self.list_url).data[0]['user_has_liked'])

    def test_rejected_messages_stay_rejected_across_users_and_time(self):
        original = self.submit('ＡＢＣ 此留言被人工拒绝')
        self.review(original.data['id'], 'rejected')
        Message.objects.filter(pk=original.data['id']).update(created_at=timezone.now() - timedelta(days=30))
        self.client.force_authenticate(self.reader)
        repeated = self.submit('abc，此留言被人工拒绝！')
        self.assertEqual(repeated.data['status'], 'rejected')
        self.assertIn('与已拒绝的留言', Message.objects.get(pk=repeated.data['id']).moderation_reason)

    def test_manual_approval_records_reviewer_and_respects_hidden_flag(self):
        response = self.submit('加微信领取资料')
        message_id = response.data['id']
        self.staff_client.patch(f'{self.admin_url}{message_id}/', {'is_hidden': 1}, format='json')
        approved = self.review(message_id, 'approved')
        self.assertEqual(approved.data['reviewed_by_name'], self.admin.username)
        self.assertIsNotNone(approved.data['reviewed_at'])
        self.assertEqual(self.client.get(self.list_url).data, [])
        self.staff_client.patch(f'{self.admin_url}{message_id}/', {'is_hidden': 0}, format='json')
        self.assertEqual(len(self.client.get(self.list_url).data), 1)

    def test_hiding_does_not_approve_pending_messages(self):
        response = self.submit('加微信领取资料')
        url = f'{self.admin_url}{response.data["id"]}/'
        for hidden in (1, 0):
            result = self.staff_client.patch(url, {'is_hidden': hidden}, format='json')
            self.assertEqual(result.data['status'], 'pending')
        self.assertEqual(self.client.get(self.list_url).data, [])

    def test_edits_are_rechecked_and_reset_manual_audit(self):
        response = self.submit()
        self.review(response.data['id'], 'approved')
        changed = self.staff_client.patch(f'{self.admin_url}{response.data["id"]}/',
                                          {'content': '操你妈'}, format='json')
        self.assertEqual(changed.data['status'], 'rejected')
        self.assertIsNone(changed.data['reviewed_at'])
        self.assertIsNone(changed.data['reviewed_by'])
        self.assertEqual(self.client.get(self.list_url).data, [])

    def test_admin_created_messages_also_use_moderation(self):
        response = self.staff_client.post(self.admin_url, {'content': '操你妈', 'is_hidden': 1}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], 'rejected')
        self.assertEqual(response.data['is_hidden'], 1)
        self.assertEqual(response.data['user'], self.admin.pk)

    def test_status_filter_combines_with_existing_search(self):
        self.submit('加微信领取资料')
        self.submit()
        response = self.staff_client.get(self.admin_url, {'status': 'pending', 'search': '领取'})
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['status'], 'pending')

    def test_readers_cannot_use_admin_endpoints_to_bypass_moderation(self):
        message = Message.objects.create(content='需要审核')
        url = f'{self.admin_url}{message.pk}/'
        self.client.force_authenticate(self.reader)
        for response in (self.client.get(self.admin_url), self.client.get(url),
                         self.client.post(self.admin_url, {'content': '绕过审核', 'status': 'approved'}),
                         self.client.patch(url, {'status': 'approved'}), self.client.delete(url)):
            self.assertEqual(response.status_code, 403)

    def test_anonymous_rate_limit_is_by_ip_and_length_limit_is_kept(self):
        for content in ('  ', '字' * 101):
            self.assertEqual(self.submit(content).status_code, 400)
        cache.clear()
        for i in range(5):
            self.assertEqual(self.submit(f'第{i}条留言').status_code, 201)
        response = self.submit('第六条留言')
        self.assertEqual(response.status_code, 429)
        self.assertIn('过于频繁', str(response.data['detail']))
        response = self.client.post(self.create_url, {'content': '另一个访客'},
                                    format='json', REMOTE_ADDR='192.0.2.3')
        self.assertEqual(response.status_code, 201)


class MessageMigrationTests(TransactionTestCase):
    def test_upgrade_keeps_historical_visibility_and_backfills_fingerprints(self):
        executor = MigrationExecutor(connection)
        old_target = [('message', '0001_initial')]
        new_target = executor.loader.graph.leaf_nodes()
        executor.migrate(old_target)
        try:
            OldMessage = executor.loader.project_state(old_target).apps.get_model('message', 'Message')
            visible = OldMessage.objects.create(content='原来的公开留言 👍！')
            hidden = OldMessage.objects.create(content='原来的隐藏留言', is_hidden=1)
        finally:
            MigrationExecutor(connection).migrate(new_target)
        visible = Message.objects.get(pk=visible.pk)
        hidden = Message.objects.get(pk=hidden.pk)
        self.assertEqual(visible.status, 'approved')
        self.assertEqual(visible.is_hidden, 0)
        self.assertEqual(hidden.status, 'approved')
        self.assertEqual(hidden.is_hidden, 1)
        self.assertEqual(visible.content_fingerprint, content_fingerprint(visible.content))
        self.assertEqual(Message.objects.create(content='未审核的新留言').status, 'pending')

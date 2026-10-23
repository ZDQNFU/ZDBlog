import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from article.models import Article, Comment, CommentModerationKeyword
from article.services.comment_text import content_fingerprint
from system_config.models import SystemConfig

User = get_user_model()


class CommentModerationTests(TestCase):
    create_url = '/api/articles/c/comments/'
    admin_url = '/api/articles/s/comments/'

    def setUp(self):
        cache.clear()
        self.reader = User.objects.create_user(username='reader')
        self.admin = User.objects.create_user(username='moderator', is_staff=True)
        self.article = Article.objects.create(title='测试文章', slug='test', status='published')
        self.client = APIClient()
        self.client.force_authenticate(self.reader)

    def submit(self, content='谢谢分享，讲得很清楚！', **extra):
        return self.client.post(self.create_url, {
            'article': self.article.pk, 'content': content, **extra,
        }, format='json')

    def public_detail(self):
        client = APIClient()
        return client.get(f'/api/articles/c/{self.article.pk}/').data

    def test_useful_criticism_and_a_technical_link_publish_immediately(self):
        response = self.submit('这个 class 的设计有问题，可以参考 https://docs.python.org/ 改进。')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], 'approved')
        data = self.public_detail()
        self.assertEqual(data['comment_count'], 1)
        self.assertEqual(data['comments'][0]['content'], response.data['content'])
        self.assertNotIn('moderation_reason', data['comments'][0])

    def test_obfuscated_abuse_is_saved_for_admin_but_never_published(self):
        response = self.submit('你这个傻\u200b · Ｂ')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], 'rejected')
        self.assertIn('未通过审核', response.data['message'])
        self.assertTrue(Comment.objects.get(pk=response.data['id']).moderation_reason)
        self.assertEqual(self.public_detail()['comments'], [])
        self.assertEqual(self.public_detail()['comment_count'], 0)

    def test_promotional_content_waits_for_review(self):
        response = self.submit('加微信领取学习资料')
        self.assertEqual(response.data['status'], 'pending')
        self.assertIn('审核通过后显示', response.data['message'])
        self.assertEqual(self.public_detail()['comments'], [])

    def test_many_links_and_emoji_flood_are_queued(self):
        for content in ('https://a.example https://b.example https://c.example', '😂' * 20):
            with self.subTest(content=content):
                self.assertEqual(self.submit(content).data['status'], 'pending')

    def test_short_time_duplicates_are_queued(self):
        first = self.submit()
        second = self.submit()
        self.assertEqual(first.data['status'], 'approved')
        self.assertEqual(second.data['status'], 'pending')
        self.assertEqual(self.public_detail()['comment_count'], 1)

    def test_different_emoji_reactions_are_not_duplicates(self):
        self.assertEqual(self.submit('👍').data['status'], 'approved')
        self.assertEqual(self.submit('❤️').data['status'], 'approved')

    def test_custom_word_lists_extend_built_in_rules(self):
        CommentModerationKeyword.objects.create(word='私设拦截词', action='reject')
        CommentModerationKeyword.objects.create(word='私设复核词', action='review')
        self.assertEqual(self.submit('私设拦截词').data['status'], 'rejected')
        self.assertEqual(self.submit('私设复核词').data['status'], 'pending')
        self.assertEqual(self.submit('操你妈').data['status'], 'rejected')

    def test_disabled_keyword_does_not_filter_new_content(self):
        CommentModerationKeyword.objects.create(word='暂停使用的词', enabled=False)
        self.assertEqual(self.submit('这里有暂停使用的词').data['status'], 'approved')

    def test_rejected_content_is_blocked_across_users_articles_and_time(self):
        content = 'AbC 这是管理员拒绝的整条评论'
        original = self.submit(content)
        self.client.force_authenticate(self.admin)
        self.client.patch(f'{self.admin_url}{original.data["id"]}/', {'status': 'rejected'})
        Comment.objects.filter(pk=original.data['id']).update(created_at=timezone.now() - timedelta(days=30))
        other_article = Article.objects.create(title='别处', slug='elsewhere', status='published')
        other_reader = User.objects.create_user(username='other-reader')
        self.client.force_authenticate(other_reader)
        repeated = self.submit('ＡＢＣ， 这是管理员拒绝的整条评论！', article=other_article.pk)
        self.assertEqual(repeated.data['status'], 'rejected')
        self.assertIn('与已拒绝', Comment.objects.get(pk=repeated.data['id']).moderation_reason)
        self.assertEqual(self.submit(content + '补充了不同内容').data['status'], 'approved')

    def test_rejected_promotional_comment_does_not_return_to_pending(self):
        original = self.submit('加微信领取资料')
        self.assertEqual(original.data['status'], 'pending')
        self.client.force_authenticate(self.admin)
        self.client.patch(f'{self.admin_url}{original.data["id"]}/', {'status': 'rejected'})
        self.client.force_authenticate(self.reader)
        self.assertEqual(self.submit('加微信领取资料').data['status'], 'rejected')

    def test_latest_manual_release_overrides_older_duplicate_rejections(self):
        original = self.submit('这句评论可以通过复核放行')
        url = f'{self.admin_url}{original.data["id"]}/'
        self.client.force_authenticate(self.admin)
        self.client.patch(url, {'status': 'rejected'})
        self.client.force_authenticate(self.reader)
        self.assertEqual(self.submit('这句评论可以通过复核放行').data['status'], 'rejected')
        self.client.force_authenticate(self.admin)
        self.client.patch(url, {'status': 'approved'})
        fresh = User.objects.create_user(username='fresh-reader')
        self.client.force_authenticate(fresh)
        self.assertEqual(self.submit('这句评论可以通过复核放行').data['status'], 'approved')

    def test_rejecting_one_emoji_does_not_reject_different_reactions(self):
        original = self.submit('👍')
        self.client.force_authenticate(self.admin)
        self.client.patch(f'{self.admin_url}{original.data["id"]}/', {'status': 'rejected'})
        self.client.force_authenticate(self.reader)
        self.assertEqual(self.submit('❤️').data['status'], 'approved')
        self.assertEqual(self.submit('👍').data['status'], 'rejected')

    def test_client_cannot_supply_approval_author_or_audit_fields(self):
        response = self.submit('傻逼', status='approved', author=self.admin.pk,
                               moderation_reason='已通过', reviewed_by=self.admin.pk)
        comment = Comment.objects.get(pk=response.data['id'])
        self.assertEqual(comment.status, 'rejected')
        self.assertEqual(comment.author, self.reader)
        self.assertIsNone(comment.reviewed_by)

    def test_empty_oversized_and_draft_comments_are_rejected(self):
        for content in ('   ', '字' * 2001):
            self.assertEqual(self.submit(content).status_code, 400)
        self.article.status = 'draft'
        self.article.save()
        self.assertEqual(self.submit().status_code, 400)
        self.assertEqual(Comment.objects.count(), 0)

    def test_cannot_reply_to_hidden_or_another_articles_comments(self):
        hidden = Comment.objects.create(article=self.article, content='待审')
        other_article = Article.objects.create(title='另一篇', slug='other', status='published')
        other = Comment.objects.create(article=other_article, content='别的文章', status='approved')
        for parent in (hidden, other):
            self.assertEqual(self.submit(parent=parent.pk).status_code, 400)

    def test_hidden_parent_also_hides_approved_descendants_and_counts(self):
        parent = Comment.objects.create(article=self.article, content='正常父评论', status='approved')
        child = Comment.objects.create(article=self.article, parent=parent, content='正常回复', status='approved')
        Comment.objects.create(article=self.article, parent=child, content='孙级回复', status='approved')
        self.assertEqual(self.public_detail()['comment_count'], 3)
        self.client.force_authenticate(self.admin)
        response = self.client.patch(f'{self.admin_url}{parent.pk}/', {'status': 'rejected'})
        self.assertEqual(response.status_code, 200)
        data = self.public_detail()
        self.assertEqual(data['comments'], [])
        self.assertEqual(data['comment_count'], 0)
        self.client.force_authenticate(self.reader)
        self.assertEqual(self.submit(parent=child.pk).status_code, 400)
        self.client.force_authenticate(self.admin)
        self.client.patch(f'{self.admin_url}{parent.pk}/', {'status': 'approved'})
        self.assertEqual(self.public_detail()['comment_count'], 3)

    def test_pending_reply_is_not_included_under_an_approved_parent(self):
        parent = Comment.objects.create(article=self.article, content='公开', status='approved')
        response = self.submit('加微信获取资源', parent=parent.pk)
        self.assertEqual(response.data['status'], 'pending')
        data = self.public_detail()
        self.assertEqual(data['comments'][0]['replies'], [])
        self.assertEqual(data['comment_count'], 1)

    def test_admin_can_release_a_false_positive_and_audit_is_recorded(self):
        response = self.submit('推广合作请联系站长')
        self.client.force_authenticate(self.admin)
        reviewed = self.client.patch(f'{self.admin_url}{response.data["id"]}/', {'status': 'approved'})
        self.assertEqual(reviewed.status_code, 200)
        self.assertEqual(reviewed.data['reviewed_by_name'], self.admin.username)
        self.assertIsNotNone(reviewed.data['reviewed_at'])
        self.assertEqual(self.public_detail()['comment_count'], 1)

    def test_admin_content_edits_run_moderation_again(self):
        response = self.submit()
        self.client.force_authenticate(self.admin)
        reviewed = self.client.patch(f'{self.admin_url}{response.data["id"]}/', {'content': '操你妈'})
        self.assertEqual(reviewed.data['status'], 'rejected')
        self.assertEqual(self.public_detail()['comment_count'], 0)

    def test_admin_filter_combines_with_search(self):
        self.submit('加微信领取资料')
        self.submit('谢谢，测试通过')
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.admin_url, {'status': 'pending', 'search': '领取'})
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['status'], 'pending')

    def test_ordinary_users_cannot_read_edit_delete_or_bypass_moderation(self):
        comment = Comment.objects.create(article=self.article, content='待审')
        url = f'{self.admin_url}{comment.pk}/'
        for response in (self.client.get(self.admin_url), self.client.get(url),
                         self.client.patch(url, {'status': 'approved'}), self.client.delete(url),
                         self.client.post(self.admin_url, {'article': self.article.pk, 'content': 'x'})):
            self.assertEqual(response.status_code, 403)
        self.assertEqual(Comment.objects.get(pk=comment.pk).status, 'pending')

    def test_ordinary_users_cannot_change_the_moderation_word_lists(self):
        url = '/api/system-config/s/configs/'
        config = SystemConfig.objects.create(key='TEST_CONFIG', value='[]')
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.patch(f'{url}{config.pk}/', {'value': '[]'}).status_code, 403)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.patch(f'{url}{config.pk}/', {'value': '["新增词"]'}).status_code, 200)

    def test_public_config_does_not_leak_moderation_words(self):
        SystemConfig.objects.create(key='COMMENT_BLOCK_WORDS', value='["私有词库"]')
        response = APIClient().get('/api/system-config/c/public/')
        self.assertNotIn('COMMENT_BLOCK_WORDS', response.data)
        self.assertNotIn('私有词库', json.dumps(response.data, ensure_ascii=False))

    def test_cascade_delete_updates_public_count(self):
        parent = Comment.objects.create(article=self.article, content='父评论', status='approved')
        Comment.objects.create(article=self.article, parent=parent, content='子评论', status='approved')
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.delete(f'{self.admin_url}{parent.pk}/').status_code, 204)
        self.assertEqual(self.public_detail()['comment_count'], 0)

    def test_submission_requires_login_and_is_rate_limited_per_user(self):
        self.assertEqual(APIClient().post(self.create_url, {}).status_code, 401)
        for i in range(5):
            self.assertEqual(self.submit(f'第{i}条正常评论').status_code, 201)
        response = self.submit('第六条')
        self.assertEqual(response.status_code, 429)
        self.assertIn('过于频繁', str(response.data['detail']))
        self.assertEqual(Comment.objects.count(), 5)


class CommentKeywordApiTests(TestCase):
    url = '/api/articles/s/comment-keywords/'

    def setUp(self):
        cache.clear()
        self.admin = User.objects.create_user(username='keyword-admin', is_staff=True)
        self.reader = User.objects.create_user(username='keyword-reader')
        self.article = Article.objects.create(title='关键词测试', slug='keyword-test', status='published')
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.reader_client = APIClient()
        self.reader_client.force_authenticate(self.reader)

    def submit(self, content):
        return self.reader_client.post('/api/articles/c/comments/', {
            'article': self.article.pk, 'content': content,
        }, format='json')

    def test_built_in_keywords_are_visible_and_editable(self):
        response = self.client.get(self.url, {'search': '加微信'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        keyword = response.data['results'][0]
        self.assertEqual(keyword['source'], 'builtin')
        self.assertEqual(keyword['action'], 'review')
        response = self.client.patch(f'{self.url}{keyword["id"]}/', {'action': 'reject'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.submit('加微信领取内容').data['status'], 'rejected')

    def test_add_edit_toggle_and_delete_immediately_change_new_comment_moderation(self):
        response = self.client.post(self.url, {'word': '自定义标记', 'action': 'reject',
                                              'source': 'builtin', 'created_by': self.reader.pk})
        self.assertEqual(response.status_code, 201)
        keyword = response.data
        self.assertEqual(keyword['source'], 'custom')
        self.assertEqual(keyword['created_by'], self.admin.pk)
        self.assertEqual(self.submit('这条自定义标记').data['status'], 'rejected')
        url = f'{self.url}{keyword["id"]}/'
        self.assertEqual(self.client.patch(url, {'enabled': False}).status_code, 200)
        self.assertEqual(self.submit('另一条自定义标记').data['status'], 'approved')
        self.assertEqual(self.client.patch(url, {'word': '新标记', 'action': 'review', 'enabled': True}).status_code, 200)
        self.assertEqual(self.submit('这里是新标记').data['status'], 'pending')
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.submit('最后一条新标记').data['status'], 'approved')

    def test_invalid_and_equivalent_duplicate_keywords_are_rejected(self):
        first = self.client.post(self.url, {'word': 'AbC 测试词', 'action': 'reject'})
        self.assertEqual(first.status_code, 201)
        for data in ({'word': 'ＡＢＣ·测试词'}, {'word': '---'}, {'word': '😂'},
                     {'word': '字' * 101}, {'word': '正常词', 'action': 'unknown'}):
            with self.subTest(data=data):
                self.assertEqual(self.client.post(self.url, data).status_code, 400)

    def test_only_admins_can_read_or_change_keywords(self):
        keyword = CommentModerationKeyword.objects.first()
        url = f'{self.url}{keyword.pk}/'
        self.assertEqual(APIClient().get(self.url).status_code, 401)
        self.client.force_authenticate(self.reader)
        for response in (self.client.get(self.url), self.client.get(url),
                         self.client.post(self.url, {'word': '越权添加'}),
                         self.client.patch(url, {'enabled': False}), self.client.delete(url)):
            self.assertEqual(response.status_code, 403)

    def test_legacy_system_settings_point_admins_to_the_keyword_manager(self):
        response = self.client.post('/api/system-config/s/configs/', {
            'key': 'COMMENT_BLOCK_WORDS', 'value': '["旧入口"]',
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('审核关键词', str(response.data))


class CommentMigrationTests(TransactionTestCase):
    def test_upgrade_keeps_historical_comments_public_and_new_defaults_pending(self):
        executor = MigrationExecutor(connection)
        old_target = [('article', '0004_like')]
        new_target = [('article', '0006_comment_keywords_and_fingerprint')]
        executor.migrate(old_target)
        try:
            old_apps = executor.loader.project_state(old_target).apps
            OldArticle = old_apps.get_model('article', 'Article')
            OldComment = old_apps.get_model('article', 'Comment')
            article = OldArticle.objects.create(title='历史文章', slug='historical', status='published')
            parent = OldComment.objects.create(article=article, content='旧评论')
            OldComment.objects.create(article=article, parent=parent, content='旧回复')
        finally:
            MigrationExecutor(connection).migrate(new_target)
        self.assertEqual(Comment.objects.filter(article_id=article.pk, status='approved').count(), 2)
        self.assertEqual(Article.objects.get(pk=article.pk).comment_count, 2)
        new = Comment.objects.create(article_id=article.pk, content='未经审核')
        self.assertEqual(new.status, 'pending')

    def test_existing_custom_keywords_and_rejections_are_migrated(self):
        old_target = [('article', '0005_comment_moderation'), ('system_config', '0001_initial')]
        new_target = [('article', '0006_comment_keywords_and_fingerprint')]
        executor = MigrationExecutor(connection)
        executor.migrate(old_target)
        try:
            old_apps = executor.loader.project_state(old_target).apps
            OldArticle = old_apps.get_model('article', 'Article')
            OldComment = old_apps.get_model('article', 'Comment')
            OldConfig = old_apps.get_model('system_config', 'SystemConfig')
            article = OldArticle.objects.create(title='待迁移', slug='migrate-words', status='published')
            comment = OldComment.objects.create(article=article, content='拒绝这条评论 👍！', status='rejected')
            OldConfig.objects.create(key='COMMENT_BLOCK_WORDS', value='["原有自定义词", "加微信"]')
            OldConfig.objects.create(key='COMMENT_REVIEW_WORDS', value='["待人工复核词", "原有自定义词"]')
        finally:
            MigrationExecutor(connection).migrate(new_target)
        self.assertEqual(Comment.objects.get(pk=comment.pk).content_fingerprint, content_fingerprint(comment.content))
        self.assertEqual(CommentModerationKeyword.objects.get(word='原有自定义词').action, 'reject')
        self.assertEqual(CommentModerationKeyword.objects.get(word='加微信').action, 'reject')
        self.assertEqual(CommentModerationKeyword.objects.get(word='待人工复核词').action, 'review')

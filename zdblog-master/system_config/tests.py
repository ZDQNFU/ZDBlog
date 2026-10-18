from django.test import TestCase
from rest_framework.test import APIClient

from system_config.models import SystemConfig


class PublicSystemConfigTests(TestCase):
    url = '/api/system-config/c/public/'

    def setUp(self):
        self.client = APIClient()
        SystemConfig.objects.create(key='ICP_BEIAN', value='皖ICP备测试号')
        SystemConfig.objects.create(key='GONGAN_BEIAN', value='皖公网安备测试号')
        SystemConfig.objects.create(key='GITHUB_TOKEN', value='should-never-leak', is_encrypted=True)

    def test_anonymous_can_read_whitelisted_keys(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {
            'ICP_BEIAN': '皖ICP备测试号',
            'GONGAN_BEIAN': '皖公网安备测试号',
        })

    def test_missing_keys_return_empty_strings(self):
        SystemConfig.objects.all().delete()
        response = self.client.get(self.url)
        self.assertEqual(response.data, {'ICP_BEIAN': '', 'GONGAN_BEIAN': ''})

    def test_non_whitelisted_keys_are_not_exposed(self):
        response = self.client.get(self.url)
        self.assertNotIn('GITHUB_TOKEN', response.data)
        self.assertEqual(sorted(response.data), ['GONGAN_BEIAN', 'ICP_BEIAN'])

    def test_encrypted_public_key_is_excluded(self):
        SystemConfig.objects.filter(key='ICP_BEIAN').update(value='signed-blob', is_encrypted=True)
        response = self.client.get(self.url)
        self.assertEqual(response.data['ICP_BEIAN'], '')

    def test_stale_authorization_header_is_ignored(self):
        response = self.client.get(self.url, HTTP_AUTHORIZATION='Bearer expired-token')
        self.assertEqual(response.status_code, 200)

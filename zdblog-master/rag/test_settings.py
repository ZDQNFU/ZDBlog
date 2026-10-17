"""Separate PostgreSQL test DB, production connection credentials loaded without printing."""
from config.settings import *  # noqa: F403

SECRET_KEY = 'isolated-rag-tests'
INSTALLED_APPS = ['django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.postgres',
                  'rest_framework', 'article', 'chat_robot', 'rag.apps.RagConfig']
MIDDLEWARE = []
ROOT_URLCONF = 'chat_robot.urls'
REST_FRAMEWORK = {'DEFAULT_AUTHENTICATION_CLASSES': [], 'UNAUTHENTICATED_USER': None}
DATABASES['default']['TEST'] = {'NAME': 'test_zdblog_rag'}
DATABASES['migration'] = {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:',
                        'TEST': {'MIRROR': 'default'}}
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
# Test fixtures must not call the configured embedding provider on save.
RAG_EMBED_PROVIDER = 'openai'
RAG_EMBED_BASE_URL = ''
RAG_EMBED_API_KEY = ''
RAG_EMBED_MODEL = 'test-1024'

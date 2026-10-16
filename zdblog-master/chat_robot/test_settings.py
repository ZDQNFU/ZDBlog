"""Isolated SQLite settings for chat tests; never loads production credentials."""
SECRET_KEY = 'chat-tests-only'
INSTALLED_APPS = ['django.contrib.auth', 'django.contrib.contenttypes', 'rest_framework', 'chat_robot']
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
# Mirror is intentionally not pre-migrated; the migration test builds its old schema.
DATABASES['migration'] = {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:',
                          'TEST': {'MIRROR': 'default'}}
ROOT_URLCONF = 'chat_robot.urls'
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
REST_FRAMEWORK = {'DEFAULT_AUTHENTICATION_CLASSES': [], 'UNAUTHENTICATED_USER': None}

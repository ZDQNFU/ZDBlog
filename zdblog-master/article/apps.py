from django.apps import AppConfig


class ArticleConfig(AppConfig):
    name = 'article'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        from . import signals  # noqa: F401

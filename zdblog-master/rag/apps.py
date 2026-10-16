from django.apps import AppConfig


class RagConfig(AppConfig):
    name = 'rag'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        from . import signals  # noqa: F401

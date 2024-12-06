from django.apps import AppConfig


class E91Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'e91'

    def ready(self):
        import e91.signals  # noqa%
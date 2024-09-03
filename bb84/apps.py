from django.apps import AppConfig


class Bb84Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bb84'

    def ready(self):
        import bb84.signals  # noqa%

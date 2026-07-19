from django.apps import AppConfig


class CampusConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.moderator'
    label = 'moderator'

    def ready(self):
        import apps.moderator.signals

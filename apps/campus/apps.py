from django.apps import AppConfig


class CampusConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.campus'
    label = 'campus'

    def ready(self):
        import apps.campus.signals

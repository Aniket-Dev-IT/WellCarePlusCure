from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.notifications'
    verbose_name = 'Notifications System'
    
    def ready(self):
        # Import signals to ensure they're loaded
        try:
            from . import signals
        except ImportError:
            pass

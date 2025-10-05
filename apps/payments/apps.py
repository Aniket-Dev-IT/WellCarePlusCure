from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.payments'
    verbose_name = 'Payment Management'
    
    def ready(self):
        """Import signals when app is ready."""
        try:
            import apps.payments.signals  # noqa F401
        except ImportError:
            pass

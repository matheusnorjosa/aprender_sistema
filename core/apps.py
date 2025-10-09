from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        """
        Inicialização quando a aplicação está pronta
        """
        # Importar signals
        try:
            import core.signals
        except ImportError:
            pass

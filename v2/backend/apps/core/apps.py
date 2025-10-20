from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Core"

    def ready(self):
        """
        Importa signals para registrar auto-invalidação de cache.

        Signals registrados:
        - post_save(Config): Invalida cache quando Config é salvo
        """
        import apps.core.signals  # noqa: F401

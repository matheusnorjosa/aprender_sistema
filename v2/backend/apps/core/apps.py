from __future__ import annotations

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Core"

    def ready(self) -> None:
        """
        Importa signals e admin para registrar auto-invalidação de cache e modelos.

        Signals registrados:
        - post_save(Config): Invalida cache quando Config é salvo
        - post_save/delete(Solicitacao): Invalida cache de availability (CP3)
        - post_save/delete(AvailabilityBlock): Invalida cache de availability (CP3)
        - post_save/delete(Municipio): Invalida cache de endpoints estáticos (CP3)
        - post_save/delete(Projeto): Invalida cache de endpoints estáticos (CP3)
        - post_save/delete(TipoEvento): Invalida cache de endpoints estáticos (CP3)

        Admin registrado:
        - Registro explícito de modelos essenciais (Usuario, Projeto, Municipio, etc.)
        """
        import apps.core.admin  # noqa: F401
        import apps.core.rbac_signals  # noqa: F401  # pyright: ignore[reportUnusedImport]
        import apps.core.signals  # noqa: F401  # pyright: ignore[reportUnusedImport]

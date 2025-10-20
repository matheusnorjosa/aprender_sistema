"""
Core Signals — Auto-invalidação de cache

Signals:
- post_save(Config): Invalida cache quando Config é salvo

Uso:
    # Automático! Nenhuma ação necessária, basta salvar o Config:
    Config.objects.create(key="availability", value={"TRAVEL_BUFFER_MINUTES": 90})
    # → Cache cfg:v1:availability invalidado automaticamente

Registro:
    - Registrado em apps/core/apps.py no método ready()
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.core.models import Config
from apps.core.services.config_service import bust_cfg


@receiver(post_save, sender=Config)
def _cfg_invalidate(sender, instance, **kwargs):
    """
    Invalida cache quando Config é salvo.

    Args:
        sender: Model class (Config)
        instance: Instância do Config salvo
        **kwargs: Argumentos extras do signal

    Side effects:
        - Chama bust_cfg(instance.key) para invalidar cache
    """
    bust_cfg(instance.key)

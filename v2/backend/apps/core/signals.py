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

from __future__ import annotations

from typing import Any

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.core.models import AvailabilityBlock, Config, Municipio, Projeto, Solicitacao, TipoEvento
from apps.core.services.config_service import bust_cfg
from apps.core.utils.cache_utils import invalidate_availability_cache, invalidate_static_cache


@receiver(post_save, sender=Config)
def _cfg_invalidate(sender: type[Config], instance: Config, **kwargs: Any) -> None:  # pyright: ignore[reportUnusedFunction]
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


# ================================================================
# CP3: Cache Invalidation for Availability Checks
# ================================================================


@receiver([post_save, post_delete], sender=Solicitacao)
def _invalidate_cache_on_solicitacao_change(sender: type[Solicitacao], instance: Solicitacao, **kwargs: Any) -> None:  # pyright: ignore[reportUnusedFunction]
    """
    Invalida cache de availability ao modificar Solicitacao.

    Quando uma solicitação é criada/atualizada/deletada, o resultado de
    check_conflicts() pode mudar, então invalidamos o cache.

    Args:
        sender: Model class (Solicitacao)
        instance: Instância da Solicitacao modificada
        **kwargs: Argumentos extras do signal

    Side effects:
        - Invalida cache de availability checks
    """
    invalidate_availability_cache()


@receiver([post_save, post_delete], sender=AvailabilityBlock)
def _invalidate_cache_on_block_change(sender: type[AvailabilityBlock], instance: AvailabilityBlock, **kwargs: Any) -> None:  # pyright: ignore[reportUnusedFunction]
    """
    Invalida cache de availability ao modificar AvailabilityBlock (bloqueio de agenda).

    Quando um bloqueio é criado/atualizado/deletado, o resultado de
    check_conflicts() pode mudar, então invalidamos o cache.

    Args:
        sender: Model class (AvailabilityBlock)
        instance: Instância do AvailabilityBlock modificado
        **kwargs: Argumentos extras do signal

    Side effects:
        - Invalida cache de availability checks
    """
    invalidate_availability_cache()


# ================================================================
# CP3: Cache Invalidation for Static Endpoints
# ================================================================


@receiver([post_save, post_delete], sender=Municipio)
def _invalidate_cache_on_municipio_change(sender: type[Municipio], instance: Municipio, **kwargs: Any) -> None:  # pyright: ignore[reportUnusedFunction]
    """
    Invalida cache de endpoints estáticos ao modificar Municipio.

    Args:
        sender: Model class (Municipio)
        instance: Instância do Municipio modificado
        **kwargs: Argumentos extras do signal

    Side effects:
        - Invalida cache de endpoints estáticos
    """
    invalidate_static_cache("Municipio")


@receiver([post_save, post_delete], sender=Projeto)
def _invalidate_cache_on_projeto_change(sender: type[Projeto], instance: Projeto, **kwargs: Any) -> None:  # pyright: ignore[reportUnusedFunction]
    """
    Invalida cache de endpoints estáticos ao modificar Projeto.

    Args:
        sender: Model class (Projeto)
        instance: Instância do Projeto modificado
        **kwargs: Argumentos extras do signal

    Side effects:
        - Invalida cache de endpoints estáticos
    """
    invalidate_static_cache("Projeto")


@receiver([post_save, post_delete], sender=TipoEvento)
def _invalidate_cache_on_tipo_evento_change(sender: type[TipoEvento], instance: TipoEvento, **kwargs: Any) -> None:  # pyright: ignore[reportUnusedFunction]
    """
    Invalida cache de endpoints estáticos ao modificar TipoEvento.

    Args:
        sender: Model class (TipoEvento)
        instance: Instância do TipoEvento modificado
        **kwargs: Argumentos extras do signal

    Side effects:
        - Invalida cache de endpoints estáticos
    """
    invalidate_static_cache("TipoEvento")

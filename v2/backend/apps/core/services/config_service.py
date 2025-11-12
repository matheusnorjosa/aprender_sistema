"""
Config Service — Cache layer para Config model (5min TTL)

Funções:
- get_cfg(key, default): Busca config com cache (5min TTL)
- bust_cfg(key): Invalida cache para key específica

Uso:
    from apps.core.services.config_service import get_cfg

    # Obter buffer de deslocamento (RD-04)
    cfg = get_cfg("availability", {})
    buffer_min = cfg.get("TRAVEL_BUFFER_MINUTES", 120)

    # Obter limite diário (RD-05)
    daily_limit_h = cfg.get("AVAILABILITY_DAILY_LIMIT_HOURS", 8)

Invalidação automática:
    - Via signal post_save em apps/core/signals.py
    - Chama bust_cfg(key) automaticamente quando Config é salvo
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false

from __future__ import annotations

from typing import Any

from django.core.cache import cache

_PREFIX: str = "cfg:v1:"
_TTL: int = 300  # 5 minutos


def get_cfg(key: str, default: Any = None) -> Any:
    """
    Busca config com cache (5min TTL).

    Args:
        key: Chave da configuração (ex: "availability", "gcal_sync")
        default: Valor padrão se key não existir (default: None)

    Returns:
        Valor da configuração ou default

    Exemplos:
        >>> cfg = get_cfg("availability", {})
        >>> buffer_min = cfg.get("TRAVEL_BUFFER_MINUTES", 120)
        120

        >>> cfg = get_cfg("gcal_sync", {})
        >>> batch_size = cfg.get("BATCH_SIZE", 200)
        200
    """
    ck: str = f"{_PREFIX}{key}"
    val: Any = cache.get(ck)

    if val is not None:
        return val

    # Import local para evitar circular import
    from apps.core.models import Config

    # Buscar no DB (ordem: effective_at DESC, updated_at DESC)
    row = (
        Config.objects.filter(key=key).order_by("-effective_at", "-updated_at").first()
    )

    val = row.value if row else default

    # Armazenar em cache
    cache.set(ck, val, _TTL)

    return val


def bust_cfg(key: str) -> None:
    """
    Invalida cache para key específica.

    Args:
        key: Chave da configuração a invalidar

    Uso:
        # Manual (normalmente via signal)
        bust_cfg("availability")

    Note:
        - Chamado automaticamente pelo signal post_save em signals.py
        - Não precisa ser chamado manualmente na maioria dos casos
    """
    ck: str = f"{_PREFIX}{key}"
    cache.delete(ck)

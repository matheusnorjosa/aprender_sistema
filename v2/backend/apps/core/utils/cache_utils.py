"""
Cache utilities for AS v2 (CP3 - Cache Availability Checks).

ASQ-007 (#780): Granular invalidation via versioned keys.
Instead of pattern-deleting all keys (cache.keys("availability_check:*")),
we use a version counter per user. Incrementing the version makes all
old cache entries miss without scanning Redis.
"""

import hashlib
import json
import random
from functools import wraps
from typing import Any, Callable, TypeVar, cast

from django.core.cache import cache

from apps.core.services.config_service import parametros_disponibilidade

F = TypeVar("F", bound=Callable[..., Any])

# Base TTL with jitter to prevent cache stampede
_BASE_TTL = 300  # 5 minutes
_JITTER_MAX = 30  # up to 30s random jitter


def _ttl_with_jitter() -> int:
    """Return TTL with random jitter to avoid simultaneous expiration."""
    return _BASE_TTL + random.randint(0, _JITTER_MAX)


def _get_cache_version(usuario_id: int) -> int:
    """Get current cache version for a user. Returns 0 if not set."""
    ver = cache.get(f"avail_ver:{usuario_id}")
    return int(ver) if ver is not None else 0


def cache_availability_check(timeout: int | None = None) -> Callable[[F], F]:
    """
    Decorator to cache check_conflicts results.

    Cache key includes a per-user version counter. When user's data changes,
    the version increments and all old entries become cache misses naturally.

    A chave é montada a partir destes 4 argumentos e dos parâmetros vigentes de disponibilidade
    (`parametros_disponibilidade`: o Buffer de deslocamento, que o motor aplica, e o teto de horas
    por evento, que o motor não usa desde 05/10/2026), e mais nada. Salvar esses
    parâmetros em Configurações muda a chave: a consulta seguinte já usa o valor novo, sem
    esperar o cache vencer (auditoria UX 30/09, rodada 4). Por isso também o wrapper aceita
    SÓ os 4 argumentos: um kwarg extra mudaria o resultado sem mudar a chave, e a próxima
    chamada com a chave antiga receberia a resposta errada. Quem precisa de argumentos
    extras (ex.: `exclude_solicitacao_id`) chama a versão sem cache.

    Args:
        timeout: TTL in seconds (default: 300 + jitter)
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*, usuario: Any, inicio: Any, fim: Any, municipio: Any = None) -> Any:
            usuario_id = usuario.id
            version = _get_cache_version(usuario_id)

            key_data = {
                "v": version,
                "usuario_id": usuario_id,
                "inicio": inicio.isoformat(),
                "fim": fim.isoformat(),
                "municipio_id": municipio.id if municipio else None,
                "parametros": parametros_disponibilidade(),
            }
            key_str = json.dumps(key_data, sort_keys=True)
            key_hash = hashlib.md5(key_str.encode(), usedforsecurity=False).hexdigest()
            # v2: o resultado ganhou `warnings` (limite diário como aviso, 02/10/2026). A
            # versão no prefixo impede servir objeto guardado antes do deploy, sem o campo.
            cache_key = f"availability_check:v2:{key_hash}"

            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            result = func(usuario=usuario, inicio=inicio, fim=fim, municipio=municipio)

            ttl = timeout if timeout is not None else _ttl_with_jitter()
            cache.set(cache_key, result, timeout=ttl)

            return result

        return cast(F, wrapper)

    return decorator


# Versão única da grade mensal (item 38): sobe a cada mudança de bloqueio/evento/participação.
_MONTHLY_VER_KEY = "monthly_ver:__global__"


def invalidate_availability_cache(usuario_id: int | None = None) -> None:
    """
    Invalidate availability cache for a specific user or globally.

    ASQ-007: Uses version counter instead of pattern delete.
    Incrementing the version makes all old cache entries miss
    without scanning Redis keys.

    Also invalidates the monthly grid cache for every viewer (item 38).

    Args:
        usuario_id: Specific user to invalidate. If None, bumps global version.
    """
    if usuario_id is not None:
        # Surgical: bump only this user's version
        ver_key = f"avail_ver:{usuario_id}"
        try:
            cache.incr(ver_key)
        except ValueError:
            # Key doesn't exist yet — set to 1
            cache.set(ver_key, 1, timeout=3600)
    else:
        # Global: bump a global version (used as fallback)
        try:
            cache.incr("avail_ver:__global__")
        except ValueError:
            cache.set("avail_ver:__global__", 1, timeout=3600)

    # A grade mensal mostra várias pessoas: a mudança de uma invalida a grade de todos (item 38).
    _invalidate_monthly_cache()


def _invalidate_monthly_cache() -> None:
    """
    Invalidate monthly availability grid cache — for EVERY viewer.

    Uses the same version-counter approach: bump the global `monthly_ver` that enters every grid
    cache key. Item 38 (ensaio r2): the key used the VIEWER's version while a change bumped only
    the owner's, so whoever looked at someone else's agenda saw a stale grid for ~5 min.
    """
    try:
        cache.incr(_MONTHLY_VER_KEY)
    except ValueError:
        cache.set(_MONTHLY_VER_KEY, 1, timeout=3600)


def get_monthly_cache_version() -> int:
    """Get current monthly cache version for cache key composition."""
    ver = cache.get(_MONTHLY_VER_KEY)
    return int(ver) if ver is not None else 0


def cache_static_endpoint(timeout: int = 300) -> Callable[[F], F]:
    """
    Decorator to cache static endpoints (municípios, projetos, tipos).

    TTL: 5 minutes — data rarely changes.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            from rest_framework.response import Response

            _request = args[0] if args else None  # noqa: F841
            cache_key = f"static_endpoint:{func.__module__}.{func.__name__}"

            cached_data = cache.get(cache_key)
            if cached_data is not None:
                return Response(cached_data)

            result = func(*args, **kwargs)

            if isinstance(result, Response):
                _ = result.data  # type: ignore[assignment]
                cache.set(cache_key, result.data, timeout=timeout)  # type: ignore[arg-type]
            else:
                cache.set(cache_key, result, timeout=timeout)

            return result

        return cast(F, wrapper)

    return decorator


def invalidate_static_cache(model_name: str) -> None:
    """
    Invalidate cache for static endpoints.

    Called on Municipio, Projeto, TipoEvento changes via signals.
    """
    pattern = "static_endpoint:*"

    try:
        keys = cache.keys(pattern) if hasattr(cache, "keys") else []  # type: ignore[attr-defined]
        if keys:
            cache.delete_many(keys)  # type: ignore[arg-type]
    except Exception:
        pass

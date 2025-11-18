"""
Cache utilities for AS v2 (CP3 - Cache Availability Checks).

Provides caching decorator for availability checks and invalidation utilities.
"""
import hashlib
import json
from functools import wraps
from typing import Any, Callable, TypeVar, cast

from django.core.cache import cache

F = TypeVar("F", bound=Callable[..., Any])


def cache_availability_check(timeout: int = 300) -> Callable[[F], F]:
    """
    Decorator para cachear check_conflicts.

    TTL: 5 minutos (300s) - dados mudam frequentemente, mas não a cada segundo
    Cache key: hash(usuario_id, inicio, fim, municipio_id)

    Args:
        timeout: TTL do cache em segundos (default: 300 = 5 minutos)

    Returns:
        Decorator function

    Example:
        @cache_availability_check(timeout=300)
        def check_conflicts(*, usuario, inicio, fim, municipio=None):
            # Código de verificação...
            return result
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*, usuario: Any, inicio: Any, fim: Any, municipio: Any = None, **kwargs: Any) -> Any:
            # Gerar cache key baseado nos parâmetros
            key_data = {
                "usuario_id": usuario.id,
                "inicio": inicio.isoformat(),
                "fim": fim.isoformat(),
                "municipio_id": municipio.id if municipio else None,
            }
            key_str = json.dumps(key_data, sort_keys=True)
            key_hash = hashlib.md5(key_str.encode()).hexdigest()
            cache_key = f"availability_check:{key_hash}"

            # Tentar buscar do cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Cache miss: executar função
            result = func(
                usuario=usuario, inicio=inicio, fim=fim, municipio=municipio, **kwargs
            )

            # Salvar no cache
            cache.set(cache_key, result, timeout=timeout)

            return result

        return cast(F, wrapper)

    return decorator


def invalidate_availability_cache(usuario_id: int | None = None) -> None:
    """
    Invalida cache de availability para um ou todos os usuários.

    Chamado ao criar/atualizar/deletar Solicitacao ou AvailabilityBlock via signals.

    Args:
        usuario_id: ID do usuário para invalidar cache específico.
                   Se None, invalida todo o cache de availability.

    Note:
        Usa abordagem simples de deletar todas as keys de availability.
        TTL curto (5 min) garante que cache não fica muito desatualizado.
        Para otimização futura, poderia usar Redis SCAN para deletar apenas
        keys específicas do usuário.
    """
    pattern = "availability_check:*"

    # django-redis suporta keys() e delete_many()
    # Abordagem simples: deletar todas as keys de availability
    try:
        keys = cache.keys(pattern) if hasattr(cache, "keys") else []  # type: ignore[attr-defined]
        if keys:
            cache.delete_many(keys)  # type: ignore[arg-type]
    except Exception:
        # Fallback: se keys() não funcionar, ignorar
        # TTL de 5 min garante que cache expira automaticamente
        pass


def cache_static_endpoint(timeout: int = 300) -> Callable[[F], F]:
    """
    Decorator para cachear endpoints estáticos (municípios, projetos, tipos).

    TTL: 5 minutos (300s) - dados raramente mudam

    IMPORTANTE: Cacheia apenas os dados (.data), não o objeto Response completo,
    pois Response não pode ser serializado (pickle).

    Args:
        timeout: TTL do cache em segundos (default: 300 = 5 minutos)

    Returns:
        Decorator function

    Example:
        @cache_static_endpoint(timeout=300)
        def list_municipios(request):
            # Código de listagem...
            return Response(data)
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            from rest_framework.response import Response

            # Gerar cache key baseado no nome da função (incluir query params se presente)
            # args[0] é self ou request (dependendo se é method ou function-based view)
            request = args[0] if args else None

            # Para function-based views DRF, args[0] é o Request
            cache_key = f"static_endpoint:{func.__module__}.{func.__name__}"

            # Tentar buscar do cache
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                # Retornar Response com dados do cache
                # Não tentar definir renderer, deixar DRF processar naturalmente
                return Response(cached_data)

            # Cache miss: executar função
            result = func(*args, **kwargs)

            # Salvar apenas os dados no cache (não o Response completo)
            if isinstance(result, Response):
                # Renderizar response para garantir que data está disponível
                # Isso força o processamento antes de cachear
                _ = result.data  # Force rendering
                cache.set(cache_key, result.data, timeout=timeout)
            else:
                # Fallback: cachear resultado completo se não for Response
                cache.set(cache_key, result, timeout=timeout)

            return result

        return cast(F, wrapper)

    return decorator


def invalidate_static_cache(model_name: str) -> None:
    """
    Invalida cache de endpoints estáticos para um modelo específico.

    Chamado ao criar/atualizar/deletar Municipio, Projeto ou TipoEvento via signals.

    Args:
        model_name: Nome do modelo ('Municipio', 'Projeto', 'TipoEvento')

    Note:
        Invalida todas as keys de static_endpoint, incluindo variações com query params.
        Exemplo: static_endpoint:projetos_options:include_test=True/False
    """
    pattern = "static_endpoint:*"

    try:
        keys = cache.keys(pattern) if hasattr(cache, "keys") else []  # type: ignore[attr-defined]
        if keys:
            cache.delete_many(keys)  # type: ignore[arg-type]
    except Exception:
        # Fallback: se keys() não funcionar, ignorar
        # TTL de 5 min garante que cache expira automaticamente
        pass

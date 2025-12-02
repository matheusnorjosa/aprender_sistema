"""
AS v2 — GCal Sync Utilities

Utility functions for retry, hashing, etc.
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections.abc import Callable
from typing import TypeVar

from apps.core.types import JsonDict, PayloadHash

logger = logging.getLogger(__name__)

# Type variable para retry genérico
T = TypeVar('T')


def _retry_with_backoff(
    func: Callable[[], T],
    *,
    operation_name: str = "operation",
    max_retries: int = 3,
    initial_delay: float = 1.0,
) -> T:
    """
    Executa função com retry e backoff exponencial (RF05 - PR19).

    Estratégia:
    - 1 tentativa inicial + até 3 retries (total: 4 tentativas)
    - Backoff: 1s, 2s, 4s
    - Retry apenas em: 429 (rate limit), 5xx (server errors)
    - Não retry em: 4xx (exceto 429)
    - Respeita Retry-After header se presente
    - Trata 409/412 como sucesso (idempotência)

    Args:
        func: Função a executar (sem argumentos, use lambda se necessário)
        operation_name: Nome da operação (para logs)
        max_retries: Número máximo de retries (default: 3)
        initial_delay: Delay inicial em segundos (default: 1.0)

    Returns:
        Resultado da função

    Raises:
        Exception: Última exceção após esgotar retries
    """
    attempt = 0
    last_exception = None

    while attempt <= max_retries:
        try:
            result = func()

            # Sucesso na tentativa
            if attempt > 0:
                logger.info(
                    f"{operation_name} succeeded after {attempt} retries"
                )
            return result

        except Exception as e:
            last_exception = e
            error_str = str(e).lower()

            # Extrair código de status HTTP se disponível
            status_code = None
            retry_after = None

            # Tentar extrair status code de exceções comuns
            if hasattr(e, 'resp') and hasattr(e.resp, 'status'):
                # googleapiclient.errors.HttpError
                status_code = e.resp.status

                # Extrair Retry-After header
                if hasattr(e.resp, 'get'):
                    retry_after = e.resp.get('Retry-After')
            elif '429' in error_str:
                status_code = 429
            elif '500' in error_str or '502' in error_str or '503' in error_str or '504' in error_str:
                status_code = 500  # Genérico para 5xx
            elif '409' in error_str:
                status_code = 409
            elif '412' in error_str:
                status_code = 412

            # VERIFICAR IDEMPOTÊNCIA PRIMEIRO (409/412 = sucesso)
            if status_code in (409, 412):
                logger.info(
                    f"{operation_name}: {status_code} treated as success (idempotency)"
                )
                return None  # type: ignore[return-value]

            # Decidir se deve retentar
            should_retry = False

            if status_code == 429:
                # Rate limit → sempre retry
                should_retry = True
                logger.warning(
                    f"{operation_name}: Rate limit (429), attempt {attempt + 1}/{max_retries + 1}"
                )
            elif status_code and status_code >= 500:
                # Server error → retry
                should_retry = True
                logger.warning(
                    f"{operation_name}: Server error ({status_code}), attempt {attempt + 1}/{max_retries + 1}"
                )
            elif status_code and 400 <= status_code < 500:
                # Client error (exceto 429) → não retry
                logger.error(
                    f"{operation_name}: Client error ({status_code}), aborting without retry"
                )
                raise
            else:
                # Erro desconhecido → retry conservador
                should_retry = True
                logger.warning(
                    f"{operation_name}: Unknown error, attempt {attempt + 1}/{max_retries + 1}: {error_str[:100]}"
                )

            # Se não deve retentar ou esgotou tentativas, lança exceção
            if not should_retry or attempt >= max_retries:
                logger.error(
                    f"{operation_name}: Failed after {attempt + 1} attempts. Last error: {error_str[:200]}"
                )
                raise

            # Calcular delay
            if retry_after:
                try:
                    delay = float(retry_after)
                except (ValueError, TypeError):
                    delay = initial_delay * (2 ** attempt)
            else:
                delay = initial_delay * (2 ** attempt)

            logger.info(f"{operation_name}: Retrying in {delay:.1f}s...")
            time.sleep(delay)
            attempt += 1

    # Nunca deve chegar aqui, mas por segurança
    raise last_exception or Exception(f"{operation_name}: Unexpected retry loop exit")


def _payload_hash(payload: JsonDict) -> PayloadHash:
    """
    Calcula SHA1 hash determinístico do payload (PR14).

    Args:
        payload: Dicionário com dados do evento

    Returns:
        str: Hash SHA1 hex (40 chars)
    """
    serialized: str = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(serialized.encode("utf-8")).hexdigest()

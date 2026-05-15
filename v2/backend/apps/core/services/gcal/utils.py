"""
AS v2 — GCal Sync Utilities

Utility functions for retry, hashing, circuit breaker integration.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections.abc import Callable
from typing import TypeVar, cast

from apps.core.types import JsonDict, PayloadHash

logger = logging.getLogger(__name__)

# Type variable para retry genérico
T = TypeVar("T")


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
                logger.info(f"{operation_name} succeeded after {attempt} retries")
            return result

        except Exception as e:
            last_exception = e
            error_str = str(e).lower()

            # Extrair código de status HTTP se disponível
            status_code = None
            retry_after = None

            # Tentar extrair status code de exceções comuns
            if hasattr(e, "resp") and hasattr(e.resp, "status"):
                # googleapiclient.errors.HttpError
                status_code = e.resp.status

                # Extrair Retry-After header
                if hasattr(e.resp, "get"):
                    retry_after = e.resp.get("Retry-After")
            elif "429" in error_str:
                status_code = 429
            elif "500" in error_str or "502" in error_str or "503" in error_str or "504" in error_str:
                status_code = 500  # Genérico para 5xx
            elif "409" in error_str:
                status_code = 409
            elif "412" in error_str:
                status_code = 412

            # VERIFICAR IDEMPOTÊNCIA PRIMEIRO (409/412 = sucesso)
            if status_code in (409, 412):
                logger.info(f"{operation_name}: {status_code} treated as success (idempotency)")
                return None  # type: ignore[return-value]

            # Decidir se deve retentar
            should_retry = False

            if status_code == 429:
                # Rate limit → sempre retry
                should_retry = True
                logger.warning(f"{operation_name}: Rate limit (429), attempt {attempt + 1}/{max_retries + 1}")
            elif status_code and status_code >= 500:
                # Server error → retry
                should_retry = True
                logger.warning(
                    f"{operation_name}: Server error ({status_code}), attempt {attempt + 1}/{max_retries + 1}"
                )
            elif status_code and 400 <= status_code < 500:
                # Client error (exceto 429) → não retry
                logger.error(f"{operation_name}: Client error ({status_code}), aborting without retry")
                raise
            else:
                # Erro desconhecido → retry conservador
                should_retry = True
                logger.warning(
                    f"{operation_name}: Unknown error, attempt {attempt + 1}/{max_retries + 1}: {error_str[:100]}"
                )

            # Se não deve retentar ou esgotou tentativas, lança exceção
            if not should_retry or attempt >= max_retries:
                logger.error(f"{operation_name}: Failed after {attempt + 1} attempts. Last error: {error_str[:200]}")
                raise

            # Calcular delay
            if retry_after:
                try:
                    delay = float(retry_after)
                except (ValueError, TypeError):
                    delay = initial_delay * (2**attempt)
            else:
                delay = initial_delay * (2**attempt)

            logger.info(f"{operation_name}: Retrying in {delay:.1f}s...")
            time.sleep(delay)
            attempt += 1

    # Nunca deve chegar aqui, mas por segurança
    raise last_exception or Exception(f"{operation_name}: Unexpected retry loop exit")


def _payload_hash(payload: JsonDict) -> PayloadHash:
    """
    Calcula SHA1 hash determinístico do payload (PR14).

    Used for deterministic idempotency key generation
    (``Solicitacao.gcal_payload_hash`` — drift detection for GCal events),
    not for cryptographic security. The ``usedforsecurity=False`` flag is set
    per PEP 644 to silence general weak-crypto linters; CodeQL
    ``py/weak-sensitive-data-hashing`` is also dismissed as false-positive in
    this context (the input is a normalized event payload, not a credential).
    Trocar para SHA-256 invalidaria todos os ``gcal_payload_hash`` históricos
    e forçaria re-sync do GCal — manter SHA-1 preserva o contrato de drift.

    Exclui ``conferenceData`` do cálculo porque contém metadata
    da API Google (requestId) que não representa dados do evento.
    Fix #573: evita falsos positivos de drift em eventos online.

    Args:
        payload: Dicionário com dados do evento

    Returns:
        str: Hash SHA1 hex (40 chars)
    """
    # Excluir conferenceData do hash (fix #573)
    hashable = {k: v for k, v in payload.items() if k != "conferenceData"}
    serialized: str = json.dumps(hashable, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(serialized.encode("utf-8"), usedforsecurity=False).hexdigest()


def _retry_with_circuit_breaker(
    func: Callable[[], T],
    *,
    operation_name: str = "operation",
    max_retries: int = 3,
    initial_delay: float = 1.0,
) -> T:
    """
    Execute function with retry, backoff, AND circuit breaker protection.

    Combines _retry_with_backoff with circuit breaker pattern.
    If circuit is open, raises CircuitBreakerError immediately.
    Failed operations count toward circuit breaker failure threshold.

    Args:
        func: Function to execute (no arguments, use lambda if needed)
        operation_name: Operation name for logs
        max_retries: Maximum retry attempts (default: 3)
        initial_delay: Initial delay in seconds (default: 1.0)

    Returns:
        Result of the function

    Raises:
        CircuitBreakerError: If circuit is open
        Exception: Last exception after exhausting retries
    """
    from .circuit_breaker import CircuitBreakerError, gcal_breaker

    # Check circuit state first
    if str(gcal_breaker.current_state) == "open":
        logger.warning(f"{operation_name}: Circuit breaker is OPEN, failing fast")
        raise CircuitBreakerError(gcal_breaker)

    try:
        # Use circuit breaker to track success/failure
        result = gcal_breaker.call(
            _retry_with_backoff,
            func,
            operation_name=operation_name,
            max_retries=max_retries,
            initial_delay=initial_delay,
        )
        return cast(T, result)
    except CircuitBreakerError:
        logger.warning(f"{operation_name}: Circuit breaker opened due to repeated failures")
        raise

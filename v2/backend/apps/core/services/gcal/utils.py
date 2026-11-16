"""
AS v2 — GCal Sync Utilities

Utility functions for idempotent execution, hashing, circuit breaker integration.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Callable
from typing import TypeVar, cast

from celery.exceptions import SoftTimeLimitExceeded

from apps.core.types import JsonDict, PayloadHash

logger = logging.getLogger(__name__)

# Type variable do retorno da chamada ao Google
T = TypeVar("T")


# Repetições por chamada ao Google nas escritas e no `get` (FER-60). A única camada de repetição é a da
# própria biblioteca do Google: `request.execute(num_retries=NUM_RETRIES_GOOGLE)` nos clientes, que repete
# 5xx, 429, 403 de limite de velocidade (não a cota diária), timeout e queda de conexão com espera crescente e aleatória. As leituras do
# caminho da tela usam `settings.GCAL_REQUEST_MAX_RETRIES`. Nada aqui repete de novo por cima.
NUM_RETRIES_GOOGLE = 3


def _status_http(e: Exception) -> int | None:
    """Status HTTP do erro do Google; sem `resp`, procura 409/412 no texto (clientes que só levantam texto)."""
    resp = getattr(e, "resp", None)
    status = getattr(resp, "status", None)
    if status is not None:
        return int(status)
    texto = str(e)
    for codigo in (409, 412):
        if str(codigo) in texto:
            return codigo
    return None


def _executar_uma_vez(func: Callable[[], T], *, operation_name: str = "operation") -> T:
    """
    Executa a chamada ao Google uma vez só, tratando 409/412 como sucesso (idempotência, RF05).

    A repetição mora no cliente (`execute(num_retries=...)`); aqui não há laço. 409/412 voltam `None`:
    o id determinístico já existe no Google (`sync.py` depende disso). Os outros erros sobem na hora.
    """
    try:
        return func()
    except SoftTimeLimitExceeded:
        # #1968: tempo esgotado sobe na hora, para a task registrar a falha antes do limite duro.
        raise
    except Exception as e:
        status = _status_http(e)
        if status in (409, 412):
            logger.info(f"{operation_name}: {status} treated as success (idempotency)")
            return None  # type: ignore[return-value]
        logger.error(f"{operation_name}: falhou (status {status}): {str(e)[:200]}")
        raise


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
) -> T:
    """
    Executa a escrita no Google dentro do disjuntor (circuit breaker), com 409/412 como sucesso.

    O nome ficou do tempo em que havia um laço de repetição aqui. Desde o FER-60 a repetição é só a da
    biblioteca do Google, dentro do cliente (`execute(num_retries=...)`); esta função não repete de novo.
    Se o disjuntor está aberto, levanta CircuitBreakerError na hora; cada operação lógica que falha
    conta 1 falha para o disjuntor.

    Raises:
        CircuitBreakerError: Se o disjuntor está aberto
        Exception: O erro da chamada (depois das repetições do cliente)
    """
    from .circuit_breaker import CircuitBreakerError, gcal_breaker

    # Check circuit state first
    if str(gcal_breaker.current_state) == "open":
        logger.warning(f"{operation_name}: Circuit breaker is OPEN, failing fast")
        raise CircuitBreakerError(gcal_breaker)

    try:
        # Use circuit breaker to track success/failure
        result = gcal_breaker.call(_executar_uma_vez, func, operation_name=operation_name)
        return cast(T, result)
    except CircuitBreakerError:
        logger.warning(f"{operation_name}: Circuit breaker opened due to repeated failures")
        raise

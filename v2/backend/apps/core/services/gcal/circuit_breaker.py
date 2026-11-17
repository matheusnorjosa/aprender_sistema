"""
AS v2 — GCal Circuit Breaker (Gap 6 - PLAN_maturity_gaps.md)

Implements circuit breaker pattern for Google Calendar API calls.

Circuit breaker states:
- CLOSED: Normal operation, requests go through
- OPEN: Failure threshold reached, requests fail fast
- HALF-OPEN: Testing if service recovered

Configuration:
- fail_max=5: Opens after 5 consecutive failures
- reset_timeout=60: Tries to close after 60 seconds

Usage:
    from apps.core.services.gcal.circuit_breaker import gcal_breaker, CircuitBreakerError

    try:
        result = gcal_breaker.call(client.insert, calendar_id, event_id, payload)
    except CircuitBreakerError:
        # Circuit is open, queue for later retry
        pass
"""

# pyright: reportIncompatibleMethodOverride=false

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, TypeVar

from django.conf import settings

import pybreaker
from google.auth.exceptions import RefreshError

if TYPE_CHECKING:
    from typing import ParamSpec

    P = ParamSpec("P")
    T = TypeVar("T")

logger = logging.getLogger("gcal.circuit_breaker")

# Re-export CircuitBreakerError for convenience
CircuitBreakerError = pybreaker.CircuitBreakerError


class GCalCircuitBreakerListener(pybreaker.CircuitBreakerListener):
    """Log circuit breaker state changes for monitoring."""

    def state_change(
        self,
        cb: pybreaker.CircuitBreaker,
        old_state: pybreaker.CircuitBreakerState,
        new_state: pybreaker.CircuitBreakerState,
    ) -> None:
        """Log state transitions."""
        logger.warning(
            "GCal circuit breaker state change",
            extra={
                "old_state": str(old_state),
                "new_state": str(new_state),
                "fail_counter": cb.fail_counter,
            },
        )

    def failure(
        self,
        cb: pybreaker.CircuitBreaker,
        exc: Exception,
    ) -> None:
        """Log failures."""
        logger.warning(
            "GCal circuit breaker recorded failure",
            extra={
                "exception": str(exc),
                "fail_counter": cb.fail_counter,
                "state": str(cb.current_state),
            },
        )

    def success(self, cb: pybreaker.CircuitBreaker) -> None:
        """Log successful calls (only in half-open state)."""
        if str(cb.current_state) == "half-open":
            logger.info(
                "GCal circuit breaker success in half-open state",
                extra={"state": str(cb.current_state)},
            )


# DEF-31 (ART-21): o disjuntor mede a saúde do Google. Erro do próprio pedido, falta de acesso ao calendário e
# credencial recusada (401, refresh recusado) não são o Google fora do ar e não contam. O 403 de cota conta: é o Google pedindo para parar. A lista é a dos
# motivos de acesso conhecidos, não a de cota: motivo de cota novo ou fora da lista (ex.: dailyLimitExceeded) conta.
_MOTIVOS_SEM_ACESSO = frozenset(
    {"forbidden", "requiredAccessLevel", "insufficientPermissions", "forbiddenForNonOrganizer"}
)
_ERROS_DO_PEDIDO = frozenset({400, 404, 409, 410, 412})


def _motivo_do_403(exc: BaseException) -> str | None:
    """`error.errors[0].reason` do corpo, a mesma leitura do googleapiclient (`_should_retry_response`)."""
    try:
        conteudo: Any = getattr(exc, "content", None)
        corpo = json.loads(conteudo)
        motivo = corpo["error"]["errors"][0]["reason"]
    except Exception:
        return None
    return motivo if isinstance(motivo, str) else None


def _nao_conta_como_falha(exc: BaseException) -> bool:
    """`exclude` do pybreaker: True tira o erro da contagem. Na dúvida (sem status, motivo ilegível ou
    desconhecido), conta."""
    if isinstance(exc, RefreshError):
        # Credencial de uma pessoa (ex.: acesso revogado, invalid_grant) não conta; `retryable` é o google-auth
        # dizendo que o token endpoint falhou (5xx, 429): isso é o Google e conta.
        retryable: Any = getattr(exc, "retryable", False)
        return not retryable
    try:
        status_bruto: Any = getattr(getattr(exc, "resp", None), "status", None)
        status = int(status_bruto)
    except (TypeError, ValueError):
        return False  # timeout, queda de conexão, erro sem resposta HTTP
    if status in _ERROS_DO_PEDIDO or status == 401:  # 401: o Google recusou a credencial de uma pessoa
        return True
    if status == 403:
        return _motivo_do_403(exc) in _MOTIVOS_SEM_ACESSO
    return False  # 429, 5xx e o resto


# Global circuit breaker instance for GCal operations
# Issue #443: Use settings for fail_max and reset_timeout
gcal_breaker = pybreaker.CircuitBreaker(
    fail_max=getattr(settings, "GCAL_CIRCUIT_BREAKER_FAIL_MAX", 5),
    reset_timeout=getattr(settings, "GCAL_CIRCUIT_BREAKER_RESET_TIMEOUT", 60),
    exclude=[_nao_conta_como_falha],
    state_storage=pybreaker.CircuitMemoryStorage(pybreaker.STATE_CLOSED),
    listeners=[GCalCircuitBreakerListener()],
    name="gcal_api",
)


def with_circuit_breaker(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator to wrap a function with circuit breaker protection.

    Usage:
        @with_circuit_breaker
        def call_gcal_api(...):
            ...

    Raises:
        CircuitBreakerError: If circuit is open
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return gcal_breaker.call(func, *args, **kwargs)

    return wrapper


def is_circuit_open() -> bool:
    """Check if circuit breaker is currently open."""
    return str(gcal_breaker.current_state) == "open"


def bloqueado_agora() -> bool:
    """True se o disjuntor está aberto e a pausa (`reset_timeout`) ainda não venceu.

    Para quem precisa decidir antes de chamar o `gcal_breaker.call` (a nova tentativa, que trava a linha e lê o
    Google antes da escrita). `current_state` sozinho não serve: só o `call` passa de open a half-open, então ler
    o estado e desistir deixava o disjuntor aberto para sempre naquele processo (ART-21). Mesma conta e mesmo
    relógio do pybreaker 1.2.0 (`CircuitOpenState.before_call`: `datetime.utcnow()`, UTC sem fuso).
    """
    if str(gcal_breaker.current_state) != "open":
        return False
    # Atributo privado do pybreaker; test_gcal_circuit_breaker quebra se ele sumir numa troca de versão.
    opened_at = gcal_breaker._state_storage.opened_at  # pyright: ignore[reportPrivateUsage]
    if not opened_at:
        return False  # o pybreaker também deixa passar sem a hora da abertura
    agora = datetime.now(UTC).replace(tzinfo=None)
    return agora < opened_at + timedelta(seconds=gcal_breaker.reset_timeout)


def get_circuit_state() -> str:
    """Get current circuit breaker state as string."""
    return str(gcal_breaker.current_state)


def reset_circuit() -> None:
    """Manually reset circuit breaker to closed state (for testing/admin)."""
    gcal_breaker.close()
    logger.info("GCal circuit breaker manually reset to closed")

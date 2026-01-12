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

import logging
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, TypeVar

import pybreaker

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


# Global circuit breaker instance for GCal operations
# Opens after 5 failures, tests recovery after 60 seconds
gcal_breaker = pybreaker.CircuitBreaker(
    fail_max=5,
    reset_timeout=60,
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


def get_circuit_state() -> str:
    """Get current circuit breaker state as string."""
    return str(gcal_breaker.current_state)


def reset_circuit() -> None:
    """Manually reset circuit breaker to closed state (for testing/admin)."""
    gcal_breaker.close()
    logger.info("GCal circuit breaker manually reset to closed")

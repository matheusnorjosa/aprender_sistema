"""
AS v2 — Database Retry Helper (ASQ-016, issue #866)

Centralized policy for surviving transient PostgreSQL errors — primarily
serialization failures and deadlocks — in wrapped transactional sections.

Usage (decorator on a function that itself opens a transaction):

    from apps.core.services.db_retry import retry_on_deadlock

    @retry_on_deadlock()
    def approve_solicitacao(solicitacao, user, request, justificativa=""):
        with transaction.atomic():
            ...

The retry loop is safe *only* when the decorated callable opens its own
`transaction.atomic()` block on every call. That way the rolled-back state
from a failed attempt is cleanly discarded before the next attempt runs.

Covered PostgreSQL error classes:
- `40001` serialization_failure
- `40P01` deadlock_detected

Anything else (IntegrityError, ProgrammingError, etc.) propagates immediately.
"""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING, Any, TypeVar, cast

from django.db import OperationalError

try:
    from django_prometheus.exports import Counter  # type: ignore[import-untyped]
except Exception:  # pragma: no cover - prometheus is optional in tests
    Counter = None  # type: ignore[assignment,misc]

if TYPE_CHECKING:
    from typing import ParamSpec

    P = ParamSpec("P")

T = TypeVar("T")

logger = logging.getLogger(__name__)

# PostgreSQL SQLSTATE codes we retry on. See
# https://www.postgresql.org/docs/current/errcodes-appendix.html
_RETRYABLE_PGCODES = frozenset(
    {
        "40001",  # serialization_failure
        "40P01",  # deadlock_detected
    }
)

_retry_counter: Any
if Counter is not None:  # pragma: no branch
    _retry_counter = Counter(
        "as_db_transaction_retries_total",
        "Number of transactional retries triggered by deadlock/serialization errors.",
        ["operation", "pgcode", "attempt"],
    )
else:  # pragma: no cover
    _retry_counter = None


def _extract_pgcode(exc: OperationalError) -> str | None:
    """Best-effort extraction of the 5-char SQLSTATE from a django OperationalError.

    Different psycopg versions expose this through slightly different paths,
    so we try each one and fall back to string matching for the deadlock
    keyword (psycopg sometimes wraps the code into `__cause__`).
    """
    cause = exc.__cause__ or exc
    # psycopg3: cause.sqlstate, cause.diag.sqlstate
    code = getattr(cause, "sqlstate", None)
    if code:
        return str(code)
    diag = getattr(cause, "diag", None)
    if diag is not None:
        code = getattr(diag, "sqlstate", None)
        if code:
            return str(code)
    # psycopg2: cause.pgcode
    code = getattr(cause, "pgcode", None)
    if code:
        return str(code)
    return None


def _is_retryable(exc: OperationalError) -> tuple[bool, str]:
    """Return (retryable, pgcode_or_label) for an OperationalError."""
    code = _extract_pgcode(exc)
    if code in _RETRYABLE_PGCODES:
        return True, code
    # Fallback: some configs swallow the SQLSTATE but leave the message intact.
    msg = str(exc).lower()
    if "deadlock detected" in msg:
        return True, "40P01"
    if "could not serialize" in msg:
        return True, "40001"
    return False, code or "unknown"


def retry_on_deadlock(
    *,
    max_attempts: int = 3,
    base_delay: float = 0.1,
    max_delay: float = 1.0,
    operation: str | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Wrap a function that opens its own transaction so that it is retried
    up to `max_attempts` times on transient PostgreSQL concurrency errors.

    - `base_delay` and `max_delay` are in seconds; jittered exponential
      backoff of the form `rand(0, min(max_delay, base_delay * 2**n))`
      is used between attempts.
    - `operation` names the retry counter label; defaults to the wrapped
      function's qualified name.

    IMPORTANT: The decorated callable MUST own its transaction boundary.
    Retrying inside an already-open transaction is a bug — the outer
    transaction is still marked broken by the first failure.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        op_label = operation or f"{func.__module__}.{func.__qualname__}"

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exc: OperationalError | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except OperationalError as exc:
                    retryable, code = _is_retryable(exc)
                    if not retryable:
                        raise
                    last_exc = exc
                    if _retry_counter is not None:
                        try:
                            _retry_counter.labels(
                                operation=op_label,
                                pgcode=code,
                                attempt=str(attempt),
                            ).inc()
                        except Exception:  # pragma: no cover - never kill a retry on telemetry
                            pass
                    if attempt >= max_attempts:
                        logger.warning(
                            "db_retry exhausted",
                            extra={
                                "event": "db_retry_exhausted",
                                "operation": op_label,
                                "pgcode": code,
                                "attempt": attempt,
                                "max_attempts": max_attempts,
                            },
                        )
                        raise
                    delay = random.uniform(0.0, min(max_delay, base_delay * (2 ** (attempt - 1))))
                    logger.info(
                        "db_retry scheduled",
                        extra={
                            "event": "db_retry_scheduled",
                            "operation": op_label,
                            "pgcode": code,
                            "attempt": attempt,
                            "next_delay_seconds": round(delay, 3),
                        },
                    )
                    time.sleep(delay)
            # Defensive; the loop either returns or raises above.
            assert last_exc is not None  # pragma: no cover
            raise last_exc  # pragma: no cover

        return cast(Callable[..., T], wrapper)

    return decorator

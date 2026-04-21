"""
Unit tests for the deadlock-retry helper (ASQ-016, #866).

Verifies that `retry_on_deadlock`:
- retries on SQLSTATE 40001 / 40P01 and on messages containing the
  deadlock/serialization keywords
- surfaces non-retryable OperationalErrors unchanged
- respects max_attempts and re-raises the last exception
- does not introduce retries for non-OperationalError exceptions
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportUnknownLambdaType=false

from __future__ import annotations

from django.db import OperationalError

import pytest

from apps.core.services.db_retry import retry_on_deadlock


class _FakePgError(Exception):
    """Stand-in for psycopg's DatabaseError — exposes `sqlstate`."""

    def __init__(self, sqlstate: str, message: str = "db error") -> None:
        super().__init__(message)
        self.sqlstate = sqlstate


def _opex_with_sqlstate(code: str, message: str = "db error") -> OperationalError:
    """Build an OperationalError whose __cause__ mimics a psycopg error."""
    cause = _FakePgError(code, message)
    exc = OperationalError(message)
    exc.__cause__ = cause
    return exc


class TestRetryOnDeadlock:
    def test_returns_immediately_on_success(self):
        calls = {"n": 0}

        @retry_on_deadlock(max_attempts=3, base_delay=0, max_delay=0)
        def fn():
            calls["n"] += 1
            return "ok"

        assert fn() == "ok"
        assert calls["n"] == 1

    def test_retries_on_deadlock_sqlstate(self):
        calls = {"n": 0}

        @retry_on_deadlock(max_attempts=3, base_delay=0, max_delay=0)
        def fn():
            calls["n"] += 1
            if calls["n"] < 2:
                raise _opex_with_sqlstate("40P01", "deadlock detected")
            return "recovered"

        assert fn() == "recovered"
        assert calls["n"] == 2

    def test_retries_on_serialization_sqlstate(self):
        calls = {"n": 0}

        @retry_on_deadlock(max_attempts=3, base_delay=0, max_delay=0)
        def fn():
            calls["n"] += 1
            if calls["n"] < 3:
                raise _opex_with_sqlstate("40001", "could not serialize")
            return "ok"

        assert fn() == "ok"
        assert calls["n"] == 3

    def test_retries_on_deadlock_message_without_sqlstate(self):
        # Some psycopg setups don't expose sqlstate; the helper falls back to
        # scanning the message body for the deadlock keyword.
        calls = {"n": 0}

        @retry_on_deadlock(max_attempts=2, base_delay=0, max_delay=0)
        def fn():
            calls["n"] += 1
            if calls["n"] < 2:
                raise OperationalError("ERROR: deadlock detected on relation ...")
            return "ok"

        assert fn() == "ok"
        assert calls["n"] == 2

    def test_reraises_after_max_attempts(self):
        @retry_on_deadlock(max_attempts=3, base_delay=0, max_delay=0)
        def fn():
            raise _opex_with_sqlstate("40P01")

        with pytest.raises(OperationalError):
            fn()

    def test_does_not_retry_on_unknown_sqlstate(self):
        calls = {"n": 0}

        @retry_on_deadlock(max_attempts=3, base_delay=0, max_delay=0)
        def fn():
            calls["n"] += 1
            raise _opex_with_sqlstate("23505", "unique_violation")  # IntegrityError-ish

        with pytest.raises(OperationalError):
            fn()
        assert calls["n"] == 1  # no retries

    def test_does_not_retry_on_non_operational_error(self):
        calls = {"n": 0}

        @retry_on_deadlock(max_attempts=3, base_delay=0, max_delay=0)
        def fn():
            calls["n"] += 1
            raise ValueError("nope")

        with pytest.raises(ValueError):
            fn()
        assert calls["n"] == 1

    def test_passes_through_args_and_kwargs(self):
        @retry_on_deadlock(max_attempts=2, base_delay=0, max_delay=0)
        def fn(a, b, *, c):
            return a + b + c

        assert fn(1, 2, c=3) == 6

    def test_max_attempts_must_be_positive(self):
        with pytest.raises(ValueError):
            retry_on_deadlock(max_attempts=0)

    def test_exhaustion_logs_warning(self):
        # Attach a capturing handler directly to the module logger; Django's
        # LOGGING config may set propagate=False on child loggers, so caplog
        # (which listens on the root) doesn't always see our events.
        import logging

        from apps.core.services import db_retry as db_retry_module

        captured: list[logging.LogRecord] = []

        class _Capture(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                captured.append(record)

        handler = _Capture(level=logging.WARNING)
        db_retry_module.logger.addHandler(handler)
        try:

            @retry_on_deadlock(max_attempts=2, base_delay=0, max_delay=0)
            def fn():
                raise _opex_with_sqlstate("40P01")

            with pytest.raises(OperationalError):
                fn()
        finally:
            db_retry_module.logger.removeHandler(handler)

        exhausted = [r for r in captured if getattr(r, "event", None) == "db_retry_exhausted"]
        assert exhausted, f"expected a db_retry_exhausted warning; got {[r.message for r in captured]}"
        rec = exhausted[0]
        assert rec.operation.endswith("fn")
        assert rec.pgcode == "40P01"
        assert rec.max_attempts == 2

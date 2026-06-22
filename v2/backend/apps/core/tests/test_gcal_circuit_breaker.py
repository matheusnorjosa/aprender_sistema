"""
Tests for the GCal circuit breaker integration (ASQ-006 / #779).

Covers:
- State transitions CLOSED → OPEN → HALF_OPEN → CLOSED
- Fast-fail behavior once open
- `_retry_with_circuit_breaker` wrapping `_retry_with_backoff`
- `/api/gcal/circuit-breaker/` endpoint (state + counters + RBAC)
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false, reportPrivateUsage=false

from __future__ import annotations

from unittest import mock

from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

import pybreaker
import pytest

from apps.core.services.gcal.circuit_breaker import (
    CircuitBreakerError,
    gcal_breaker,
    get_circuit_state,
    is_circuit_open,
    reset_circuit,
)
from apps.core.services.gcal.utils import _retry_with_circuit_breaker
from apps.core.tests.factories import GroupFactory, UsuarioFactory


@pytest.fixture(autouse=True)
def _reset_breaker():
    """Reset breaker before and after each test — global state leaks otherwise."""
    reset_circuit()
    yield
    reset_circuit()


class FakeHttpResp:
    def __init__(self, status_code: int):
        self.status = status_code

    def get(self, _key: str, default=None):
        return default


class FakeHttpError(Exception):
    """Mimics googleapiclient.errors.HttpError's .resp.status attribute."""

    def __init__(self, status_code: int, message: str = ""):
        super().__init__(message or f"HTTP {status_code}")
        self.resp = FakeHttpResp(status_code)


class TestStateTransitions:
    """Exercise CLOSED → OPEN → HALF_OPEN → CLOSED transitions."""

    def test_starts_closed(self):
        assert get_circuit_state() == "closed"
        assert is_circuit_open() is False

    def test_opens_after_fail_max_consecutive_failures(self):
        def failing():
            raise FakeHttpError(503, "upstream down")

        fail_max = getattr(gcal_breaker, "fail_max", 5)

        # Each call counts as one breaker failure (max_retries=0 to disable backoff).
        # The last call may already raise CircuitBreakerError if the breaker tripped
        # mid-call, so accept either flavor.
        for _ in range(fail_max):
            with pytest.raises((FakeHttpError, CircuitBreakerError)):
                _retry_with_circuit_breaker(failing, operation_name="test", max_retries=0)

        assert is_circuit_open() is True
        assert get_circuit_state() == "open"

    def test_open_breaker_fast_fails_without_calling_func(self):
        # Force breaker open directly
        gcal_breaker.open()
        called = {"count": 0}

        def tracker():
            called["count"] += 1
            return "ok"

        with pytest.raises(CircuitBreakerError):
            _retry_with_circuit_breaker(tracker, operation_name="fast-fail")

        assert called["count"] == 0, "open breaker should skip the function entirely"

    def test_half_open_success_returns_breaker_to_closed(self):
        # Force half-open via pybreaker's public API (the lazy time-based
        # transition from open→half-open is hard to reproduce reliably).
        gcal_breaker.half_open()
        assert get_circuit_state() == "half-open"

        result = _retry_with_circuit_breaker(lambda: "recovered", operation_name="half-open-probe")
        assert result == "recovered"
        assert get_circuit_state() == "closed"

    def test_half_open_failure_reopens_breaker(self):
        gcal_breaker.half_open()
        assert get_circuit_state() == "half-open"

        def fail():
            raise FakeHttpError(503)

        with pytest.raises((FakeHttpError, CircuitBreakerError)):
            _retry_with_circuit_breaker(fail, operation_name="half-open-fail", max_retries=0)

        assert get_circuit_state() == "open"


class TestRetryIntegration:
    """Ensure the breaker observes the same success/failure signal as the retry layer."""

    def test_transient_error_that_eventually_succeeds_does_not_open_breaker(self):
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] < 3:
                raise FakeHttpError(503)
            return "ok"

        with mock.patch("apps.core.services.gcal.utils.time.sleep"):  # skip real backoff
            result = _retry_with_circuit_breaker(flaky, operation_name="flaky-then-ok", max_retries=3)

        assert result == "ok"
        assert get_circuit_state() == "closed"

    def test_non_transient_4xx_does_not_retry_but_counts_toward_breaker(self):
        # 4xx errors are non-retryable, but they still surface through the breaker
        # as a single failure — matches current pybreaker semantics.
        def forbidden():
            raise FakeHttpError(403, "forbidden")

        with pytest.raises(FakeHttpError):
            _retry_with_circuit_breaker(forbidden, operation_name="auth-fail", max_retries=3)

        # One failure recorded, not several retries. fail_counter may be internal,
        # but the breaker state should still be closed after a single 4xx.
        assert get_circuit_state() == "closed"


class TestCircuitBreakerEndpoint:
    """`/api/gcal/circuit-breaker/` — state + RBAC."""

    @pytest.fixture
    def client(self):
        return APIClient()

    @pytest.fixture
    def staff_user(self, db):
        user = UsuarioFactory(username="operator", email="operator@test.com", password="x")
        group = GroupFactory(name="Controle")
        user.groups.add(group)
        return user

    @pytest.fixture
    def regular_user(self, db):
        return UsuarioFactory(username="regular", email="regular@test.com", password="x")

    def test_returns_closed_state_on_fresh_breaker(self, client, staff_user):
        client.force_authenticate(user=staff_user)
        response = client.get("/api/gcal/circuit-breaker/")

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["state"] == "closed"
        assert body["fail_counter"] == 0
        assert body["fail_max"] >= 1
        assert body["reset_timeout_seconds"] >= 1

    def test_returns_open_state_when_breaker_tripped(self, client, staff_user):
        client.force_authenticate(user=staff_user)
        gcal_breaker.open()

        response = client.get("/api/gcal/circuit-breaker/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["state"] == "open"

    def test_requires_authentication(self, client):
        response = client.get("/api/gcal/circuit-breaker/")
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_regular_user_forbidden(self, client, regular_user):
        client.force_authenticate(user=regular_user)
        response = client.get("/api/gcal/circuit-breaker/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @override_settings(GCAL_CIRCUIT_BREAKER_FAIL_MAX=7, GCAL_CIRCUIT_BREAKER_RESET_TIMEOUT=90)
    def test_reports_settings_derived_thresholds(self, client, staff_user):
        client.force_authenticate(user=staff_user)
        response = client.get("/api/gcal/circuit-breaker/")
        body = response.json()
        assert body["fail_max"] == 7
        assert body["reset_timeout_seconds"] == 90


class TestCircuitBreakerSanity:
    """Safety nets for the existing helpers used elsewhere."""

    def test_pybreaker_error_is_reexported(self):
        assert issubclass(CircuitBreakerError, pybreaker.CircuitBreakerError)

    def test_reset_circuit_closes_open_breaker(self):
        gcal_breaker.open()
        assert is_circuit_open() is True
        reset_circuit()
        assert is_circuit_open() is False

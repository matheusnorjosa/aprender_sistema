"""Tests for FreezeTimeMiddleware (E2E time-freeze).

Gate duplo:
- settings.INCLUDE_DEV_TOOLS=True
- settings.DEBUG_E2E=True

Sem ambos, o middleware recusa inicialização — proteção explícita contra
vazamento em produção.
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Callable, Generator

import pytest
from django.http import HttpRequest, HttpResponse
from django.test import override_settings
from django.utils import timezone


@pytest.fixture(autouse=True)
def _reset_freeze_time_state() -> Generator[None, None, None]:
    """Reseta monkey-patch entre testes para evitar poluição."""
    from apps.dev_tools.middleware.freeze_time import reset_for_tests

    reset_for_tests()
    yield
    reset_for_tests()


def _make_get_response() -> Callable[[HttpRequest], HttpResponse]:
    response = HttpResponse(b"ok")

    def _inner(request: HttpRequest) -> HttpResponse:
        # Captura snapshot de timezone.now() no momento do request
        response["X-Captured-Now"] = timezone.now().isoformat()
        return response

    return _inner


@override_settings(DEBUG_E2E=True, INCLUDE_DEV_TOOLS=True)
def test_middleware_initializes_when_both_flags_true() -> None:
    from apps.dev_tools.middleware.freeze_time import FreezeTimeMiddleware

    middleware = FreezeTimeMiddleware(_make_get_response())
    assert middleware is not None


@override_settings(DEBUG_E2E=False, INCLUDE_DEV_TOOLS=True)
def test_middleware_refuses_when_debug_e2e_false() -> None:
    from apps.dev_tools.middleware.freeze_time import FreezeTimeMiddleware

    with pytest.raises(RuntimeError, match="DEBUG_E2E"):
        FreezeTimeMiddleware(_make_get_response())


@override_settings(DEBUG_E2E=True, INCLUDE_DEV_TOOLS=False)
def test_middleware_refuses_when_include_dev_tools_false() -> None:
    from apps.dev_tools.middleware.freeze_time import FreezeTimeMiddleware

    with pytest.raises(RuntimeError, match="INCLUDE_DEV_TOOLS"):
        FreezeTimeMiddleware(_make_get_response())


@override_settings(DEBUG_E2E=True, INCLUDE_DEV_TOOLS=True)
def test_freezes_time_when_header_present() -> None:
    from apps.dev_tools.middleware.freeze_time import FreezeTimeMiddleware

    middleware = FreezeTimeMiddleware(_make_get_response())
    request = HttpRequest()
    request.META["HTTP_X_E2E_FROZEN_TIME"] = "2026-04-21T09:00:00-03:00"

    response = middleware(request)

    expected = datetime(2026, 4, 21, 9, 0, 0, tzinfo=dt_timezone(timedelta(hours=-3)))
    assert response["X-Captured-Now"] == expected.isoformat()


@override_settings(DEBUG_E2E=True, INCLUDE_DEV_TOOLS=True)
def test_does_not_freeze_when_header_absent() -> None:
    from apps.dev_tools.middleware.freeze_time import FreezeTimeMiddleware

    middleware = FreezeTimeMiddleware(_make_get_response())
    request = HttpRequest()

    response = middleware(request)

    # Sem header, deve ser "agora" real — não o valor fixo do teste acima
    captured = datetime.fromisoformat(response["X-Captured-Now"])
    real_now = timezone.now()
    delta_seconds = abs((real_now - captured).total_seconds())
    assert delta_seconds < 5, "Sem header, timezone.now() deve ser o agora real"


@override_settings(DEBUG_E2E=True, INCLUDE_DEV_TOOLS=True)
def test_invalid_iso_header_is_ignored() -> None:
    from apps.dev_tools.middleware.freeze_time import FreezeTimeMiddleware

    middleware = FreezeTimeMiddleware(_make_get_response())
    request = HttpRequest()
    request.META["HTTP_X_E2E_FROZEN_TIME"] = "not-a-date"

    # Não deve levantar; segue sem congelamento
    response = middleware(request)
    assert response.status_code == 200


@override_settings(DEBUG_E2E=True, INCLUDE_DEV_TOOLS=True)
def test_naive_datetime_header_is_rejected() -> None:
    """Header sem timezone é rejeitado (evita ambiguidade UTC vs local)."""
    from apps.dev_tools.middleware.freeze_time import FreezeTimeMiddleware

    middleware = FreezeTimeMiddleware(_make_get_response())
    request = HttpRequest()
    request.META["HTTP_X_E2E_FROZEN_TIME"] = "2026-04-21T09:00:00"  # sem tz

    response = middleware(request)

    # Sem tz → middleware ignora e usa "agora" real
    captured = datetime.fromisoformat(response["X-Captured-Now"])
    real_now = timezone.now()
    delta_seconds = abs((real_now - captured).total_seconds())
    assert delta_seconds < 5


@override_settings(DEBUG_E2E=True, INCLUDE_DEV_TOOLS=True)
def test_freeze_does_not_leak_between_requests() -> None:
    """Após request com header, próximo sem header volta ao tempo real."""
    from apps.dev_tools.middleware.freeze_time import FreezeTimeMiddleware

    middleware = FreezeTimeMiddleware(_make_get_response())

    # Request 1 com congelamento
    req1 = HttpRequest()
    req1.META["HTTP_X_E2E_FROZEN_TIME"] = "2020-01-01T00:00:00+00:00"
    resp1 = middleware(req1)
    assert resp1["X-Captured-Now"].startswith("2020-01-01")

    # Request 2 sem congelamento — deve voltar ao real
    req2 = HttpRequest()
    resp2 = middleware(req2)
    assert not resp2["X-Captured-Now"].startswith("2020-01-01")

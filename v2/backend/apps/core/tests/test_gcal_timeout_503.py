"""GCal request-path: timeout do Google vira 503 (ServiceUnavailableError), nao 500.

Onda 4c (pos-incidente 2026-07-06): `socket.timeout` IS `TimeoutError` no py3.12 e propaga
cru (o retry client-level so pega `HttpError`). Antes, as 3 views de LEITURA do GCal
(gcal_calendars, google_oauth_list_calendars, google_oauth_list_events) engoliam qualquer
erro com `except Exception` -> 500 (erro do servidor, alarme falso). Agora um timeout do
Google retorna 503 + code SERVICE_UNAVAILABLE — "servico externo indisponivel, tente de
novo" — como o gcal_health ja fazia. Erros NAO-timeout continuam 500 (handler estreito).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportMissingParameterType=false, reportUnknownParameterType=false, reportOptionalMemberAccess=false, reportArgumentType=false

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import GoogleOAuthCredential
from apps.core.tests.factories import GroupFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


def _controle_client() -> tuple[APIClient, object]:
    """APIClient autenticado com grupo Controle (satisfaz CanUseGcal)."""
    user = UsuarioFactory()
    user.groups.add(GroupFactory(name="Controle"))
    api = APIClient()
    api.force_authenticate(user=user)
    return api, user


class _TimeoutCalClient:
    """Stub de client GCal cujas LEITURAS estouram timeout (socket.timeout == TimeoutError)."""

    def __init__(self, *args: object, **kwargs: object) -> None: ...

    def list_calendars(self) -> object:
        raise TimeoutError("deadline exceeded")

    def list_events(self, *args: object, **kwargs: object) -> object:
        raise TimeoutError("deadline exceeded")


def _make_credential(user: object) -> None:
    GoogleOAuthCredential.objects.create(
        user=user,
        google_email="op@aprendereditora.com.br",
        access_token_encrypted=b"enc-access",
        refresh_token_encrypted=b"enc-refresh",
        token_expiry=timezone.now() + timedelta(hours=1),
        scope="https://www.googleapis.com/auth/calendar",
        default_calendar_id="primary",
    )


def _assert_503(resp: object) -> None:
    assert resp.status_code == 503, f"esperava 503, veio {resp.status_code}: {getattr(resp, 'data', None)}"
    assert resp.data.get("code") == "SERVICE_UNAVAILABLE", f"code inesperado: {resp.data}"


def test_gcal_calendars_timeout_vira_503(monkeypatch: pytest.MonkeyPatch) -> None:
    api, _ = _controle_client()
    monkeypatch.setattr(
        "apps.core.views_gcal.gcal.get_gcal_client_and_calendar_id",
        lambda: (_TimeoutCalClient(), "cal"),
    )
    _assert_503(api.get("/api/gcal/calendars/"))


def test_oauth_list_calendars_timeout_vira_503(monkeypatch: pytest.MonkeyPatch) -> None:
    api, user = _controle_client()
    _make_credential(user)
    monkeypatch.setattr("apps.core.services.gcal_oauth_client.OAuthCalendarClient", _TimeoutCalClient)
    _assert_503(api.get("/api/integrations/google/calendars/"))


def test_oauth_list_events_timeout_vira_503(monkeypatch: pytest.MonkeyPatch) -> None:
    api, user = _controle_client()
    _make_credential(user)
    monkeypatch.setattr("apps.core.services.gcal_oauth_client.OAuthCalendarClient", _TimeoutCalClient)
    _assert_503(api.get("/api/integrations/google/events/"))


def test_gcal_calendars_erro_generico_continua_500(monkeypatch: pytest.MonkeyPatch) -> None:
    """Handler estreito: so TimeoutError vira 503; qualquer outro erro segue 500."""

    class _BrokenClient:
        def list_calendars(self) -> object:
            raise ValueError("boom")

    api, _ = _controle_client()
    monkeypatch.setattr(
        "apps.core.views_gcal.gcal.get_gcal_client_and_calendar_id",
        lambda: (_BrokenClient(), "cal"),
    )
    resp = api.get("/api/gcal/calendars/")
    assert resp.status_code == 500, f"erro generico deveria seguir 500, veio {resp.status_code}"

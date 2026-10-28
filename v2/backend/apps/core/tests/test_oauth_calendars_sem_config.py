"""
`GET /api/integrations/google/calendars/` sem a configuração OAuth do servidor (ensaio r3, 28/10/2026).

Sem `GCAL_OAUTH_CLIENT_ID`/`GCAL_OAUTH_CLIENT_SECRET`, o cliente do Google não monta e a view caía
no `except Exception` -> 500 ("erro do servidor", alarme falso). Agora devolve 409 com
`code=google_calendar_not_configured` e uma mensagem em pt-BR que o card da tela mostra, sem
detalhe interno (nome de variável, stack). Vale também com o token vencido: a renovação pede a
mesma configuração.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportMissingParameterType=false, reportUnknownParameterType=false, reportOptionalMemberAccess=false, reportArgumentType=false

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import GoogleOAuthCredential
from apps.core.tests.factories import GroupFactory, UsuarioFactory, com_pacote_do_controle

pytestmark = pytest.mark.django_db

MENSAGEM = "A conexão com o Google Agenda ainda não foi configurada no sistema. Avise a administração do sistema."


def _controle_com_credencial(expira_em: timedelta) -> APIClient:
    user = UsuarioFactory()
    user.groups.add(GroupFactory(name="Controle"))
    com_pacote_do_controle(user)
    GoogleOAuthCredential.objects.create(
        user=user,
        google_email="op@aprendereditora.com.br",
        access_token_encrypted=b"enc-access",
        refresh_token_encrypted=b"enc-refresh",
        token_expiry=timezone.now() + expira_em,
        scope="https://www.googleapis.com/auth/calendar",
        default_calendar_id="primary",
    )
    api = APIClient()
    api.force_authenticate(user=user)
    return api


@pytest.mark.parametrize("expira_em", [timedelta(hours=1), timedelta(hours=-1)], ids=["token valido", "token vencido"])
def test_sem_config_oauth_devolve_409_tratado(monkeypatch: pytest.MonkeyPatch, expira_em: timedelta) -> None:
    monkeypatch.delenv("GCAL_OAUTH_CLIENT_ID", raising=False)
    monkeypatch.delenv("GCAL_OAUTH_CLIENT_SECRET", raising=False)
    api = _controle_com_credencial(expira_em)

    resp = api.get("/api/integrations/google/calendars/")

    assert resp.status_code == 409, f"esperava 409, veio {resp.status_code}: {getattr(resp, 'data', None)}"
    assert resp.data["code"] == "google_calendar_not_configured"
    assert resp.data["detail"] == MENSAGEM
    corpo = resp.content.decode()
    assert "GCAL_OAUTH" not in corpo
    assert "Traceback" not in corpo


def test_falta_so_o_secret_tambem_e_409(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GCAL_OAUTH_CLIENT_ID", "client-id-de-teste")
    monkeypatch.delenv("GCAL_OAUTH_CLIENT_SECRET", raising=False)
    api = _controle_com_credencial(timedelta(hours=1))

    resp = api.get("/api/integrations/google/calendars/")

    assert resp.status_code == 409
    assert resp.data["code"] == "google_calendar_not_configured"

"""
Item 22 da lista de liberação (19/10/2026), parte 1: o CPF sai dos logs que ainda o levavam (#1964).

Desde 29/09 o login (`username`) de toda conta é o CPF. Então:
- as rotas do Google (`views_oauth.py`) logam `user_id=<pk>`, não o login;
- o importador de usuários loga o pk da conta, não o login `user_<cpf>` (que o filtro de log não
  reconhece: o `_` cola no CPF e tira a fronteira de palavra);
- o `target_username` que a tela de Usuários grava no AuditLog passa por `redact_username`, que
  também tira o CPF do login `user_<cpf>`;
- o filtro de log (`PIIRedactionFilter`) também redige o CPF formatado `000.000.000-00`, com a
  mesma regra de `apps/core/pii.py` (#1964: os dois módulos tinham divergido).

O CPF aqui é sintético.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportIndexIssue=false, reportPrivateUsage=false

from __future__ import annotations

import logging
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import Group
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.logging_filters import PIIRedactionFilter
from apps.core.models import AuditLog, GoogleOAuthCredential
from apps.core.pii import redact_cpf, redact_username
from apps.core.services.audit import (
    auditar_assign_groups,
    auditar_privilege_flags,
    auditar_reset_senha,
    auditar_user_delete,
)
from apps.core.services.usuarios_import import _assign_groups
from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

CPF = "11144477735"
CPF_FORMATADO = "111.444.777-35"


@pytest.fixture(autouse=True)
def _cache_limpo():
    cache.clear()
    yield
    cache.clear()


def _sem_cpf(texto: str) -> bool:
    return CPF not in texto and CPF_FORMATADO not in texto


def _log_sem_cpf(mensagem: str) -> bool:
    """Nem o CPF nem o `<cpf>` do filtro: o filtro de log redige o registro no lugar, antes do caplog."""
    return _sem_cpf(mensagem) and "<cpf>" not in mensagem


def _client(user) -> APIClient:
    c = APIClient()
    c.force_authenticate(user)
    return c


# =============================================================================
# Filtro de log: a mesma regra de CPF de `pii.py` (#1964)
# =============================================================================


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        (f"cpf {CPF} ok", "cpf <cpf> ok"),
        (f"cpf {CPF_FORMATADO} ok", "cpf <cpf> ok"),
        (f"celula '{CPF_FORMATADO}' invalida", "celula '<cpf>' invalida"),
        ("login user_ab12cd34ef56 ok", "login user_ab12cd34ef56 ok"),
        ("doze 111444777351 digitos", "doze 111444777351 digitos"),
    ],
)
def test_filtro_de_log_e_pii_redigem_igual(entrada, esperado):
    rec = logging.LogRecord("t", logging.INFO, __file__, 1, entrada, (), None)
    PIIRedactionFilter().filter(rec)
    assert rec.getMessage() == esperado
    assert redact_cpf(entrada) == esperado


# =============================================================================
# Rotas do Google: o log leva o pk, não o login
# =============================================================================


@pytest.fixture
def conta_cpf():
    return UsuarioFactory(superuser=True, username=CPF, cpf=CPF, email="pessoa@example.invalid")


@pytest.fixture
def credencial(conta_cpf):
    return GoogleOAuthCredential.objects.create(
        user=conta_cpf,
        google_email="operacao@example.invalid",
        access_token_encrypted=b"x",
        refresh_token_encrypted=b"x",
        token_expiry=timezone.now() + timedelta(hours=1),
        scope="https://www.googleapis.com/auth/calendar",
        default_calendar_id="primary",
    )


def _start(client):
    with patch(
        "apps.core.views_oauth.build_authorization_url",
        return_value="https://accounts.google.com/o/oauth2/v2/auth?state=s",
    ):
        return client.get("/api/oauth/google/start/")


def _callback(client):
    tokens = {
        "email": "operacao@example.invalid",
        "access_token": "a",
        "refresh_token": "r",
        "expires_in": 3600,
        "scope": "https://www.googleapis.com/auth/calendar",
    }
    with (
        patch(
            "apps.core.services.google_oauth.validate_oauth_state",
            return_value={"valid": True, "return_to": "/pre-agenda"},
        ),
        patch("apps.core.views_oauth.exchange_code_for_tokens", return_value=tokens),
        patch("apps.core.views_oauth.encrypt_token", return_value=b"x"),
    ):
        return client.get("/api/oauth/google/callback/", {"code": "c", "state": "s"})


def _disconnect(client):
    with patch("apps.core.views_oauth.revoke_token", return_value=True):
        return client.post("/api/integrations/google/disconnect/")


def _eventos(client):
    cliente_google = MagicMock()
    cliente_google.list_events.return_value = [{"id": "e1"}]
    with patch("apps.core.services.gcal_oauth_client.OAuthCalendarClient", return_value=cliente_google):
        return client.get("/api/integrations/google/events/")


def _calendarios(client):
    cliente_google = MagicMock()
    cliente_google.list_calendars.return_value = [{"id": "primary", "summary": "Agenda"}]
    with patch("apps.core.services.gcal_oauth_client.OAuthCalendarClient", return_value=cliente_google):
        return client.get("/api/integrations/google/calendars/")


def _seleciona(client):
    return client.post("/api/integrations/google/select-calendar/", {"calendar_id": "primary"}, format="json")


@pytest.mark.parametrize(
    "rota",
    [_start, _callback, _disconnect, _eventos, _calendarios, _seleciona],
    ids=["start", "callback", "disconnect", "eventos", "calendarios", "seleciona"],
)
@pytest.mark.usefixtures("credencial")
def test_rotas_do_google_logam_o_pk_e_nao_o_cpf(caplog, conta_cpf, rota):
    with (
        patch("apps.core.views_oauth.has_publish_scope", return_value=True),
        caplog.at_level(logging.DEBUG),
    ):
        resp = rota(_client(conta_cpf))
    assert resp.status_code in (200, 302), getattr(resp, "content", resp)
    mensagens = [r.getMessage() for r in caplog.records]
    assert any(f"user_id={conta_cpf.pk}" in m for m in mensagens), mensagens
    for m in mensagens:
        assert _log_sem_cpf(m), m


# =============================================================================
# Importador de usuários: o log de grupo recusado leva o pk
# =============================================================================


def test_import_loga_o_pk_e_nao_o_login_user_cpf(caplog):
    superuser = UsuarioFactory(superuser=True)
    alvo = UsuarioFactory(username=f"user_{CPF}", cpf=CPF)
    admin, _ = Group.objects.get_or_create(name="AdminSistema")  # fora da allowlist: gera o aviso
    with caplog.at_level(logging.WARNING, logger="apps.core.services.usuarios_import"):
        _assign_groups(alvo, [admin], actor=superuser)
    mensagens = [r.getMessage() for r in caplog.records]
    assert any(f"user_id={alvo.pk}" in m for m in mensagens), mensagens
    for m in mensagens:
        assert _log_sem_cpf(m), m


# =============================================================================
# Tela de Usuários: o AuditLog não guarda o login (CPF)
# =============================================================================


def test_auditoria_de_criar_e_alterar_conta_nao_guarda_o_cpf():
    root = UsuarioFactory(superuser=True)
    client = _client(root)
    resp = client.post(
        "/api/usuarios-admin/",
        {"username": CPF, "cpf": CPF, "email": "nova@example.invalid", "first_name": "Ana"},
        format="json",
    )
    assert resp.status_code == 201, resp.content
    alvo_id = resp.data["id"]
    resp = client.patch(f"/api/usuarios-admin/{alvo_id}/", {"first_name": "Bia"}, format="json")
    assert resp.status_code == 200, resp.content

    logs = AuditLog.objects.filter(model_name="Usuario", details__target_user_id=alvo_id)
    acoes = {log.action for log in logs}
    assert {AuditLog.Action.CREATE, AuditLog.Action.UPDATE} <= acoes
    for log in logs:
        assert _sem_cpf(str(log.details)), log.details


# =============================================================================
# Login `user_<cpf>` do importador: o `target_username` do AuditLog também sai sem CPF
# =============================================================================


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        (f"user_{CPF}", "user_<cpf>"),
        (f"user_{CPF}_2", "user_<cpf>_2"),
        (CPF, "<cpf>"),
        ("novo_m0703", "novo_m0703"),
        ("user_ab12cd34ef56", "user_ab12cd34ef56"),
        (None, None),
    ],
)
def test_redact_username_tira_o_cpf_do_login_user_cpf(entrada, esperado):
    assert redact_username(entrada) == esperado


def test_auditoria_de_alterar_conta_user_cpf_nao_guarda_o_cpf():
    root = UsuarioFactory(superuser=True)
    alvo = UsuarioFactory(username=f"user_{CPF}", cpf=CPF)
    resp = _client(root).patch(f"/api/usuarios-admin/{alvo.pk}/", {"first_name": "Bia"}, format="json")
    assert resp.status_code == 200, resp.content

    log = AuditLog.objects.get(action=AuditLog.Action.UPDATE, details__target_user_id=alvo.pk)
    assert log.details["target_username"] == "user_<cpf>"


def test_registradores_de_audit_nao_guardam_o_login_user_cpf():
    root = UsuarioFactory(superuser=True)
    alvo = UsuarioFactory(username=f"user_{CPF}_1", cpf=CPF)
    grupo, _ = Group.objects.get_or_create(name="Formador")
    auditar_assign_groups(actor=root, target_user=alvo, before_group_ids=[], after_group_ids=[grupo.pk], imediato=True)
    auditar_reset_senha(actor=root, target_user=alvo, imediato=True)
    alvo.is_staff = True
    auditar_privilege_flags(
        actor=root,
        target_user=alvo,
        before={"is_superuser": False, "is_staff": False, "is_active": True},
        via="teste",
        imediato=True,
    )
    auditar_user_delete(actor=root, target_user=alvo, imediato=True)

    logs = AuditLog.objects.filter(details__target_user_id=alvo.pk)
    assert logs.count() == 4
    for log in logs:
        assert log.details["target_username"] == "user_<cpf>_1", log.details
        assert _sem_cpf(str(log.details)), log.details

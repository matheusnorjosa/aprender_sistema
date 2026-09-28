"""Falha de credencial ou de cancelamento marca ERROR — nunca PENDING eterno (#2039, #1656).

publish/resync/cancel marcam a linha PENDING ANTES de enfileirar (services/solicitacao_publish.py).
Se a task saía cedo (sem credencial, operador inexistente, token revogado, rede no refresh) ou o
cancel estourava, a linha ficava PENDING para sempre: o botão de publicar some na UI e a edição fica
bloqueada. Agora a task marca ERROR com uma mensagem que diz como resolver, o erro cru vai para o
AuditLog e o `external_event_id` é mantido (a linha continua re-tentável).

Cada teste liga o modo OAuth explicitamente: o fixture autouse de conftest.py força service_account.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import timedelta
from unittest.mock import Mock, patch

from django.test import override_settings
from django.utils import timezone

import pytest
import requests
from googleapiclient.errors import HttpError

from apps.core.models import AuditLog, GoogleOAuthCredential, Solicitacao
from apps.core.services.oauth.token_manager import encrypt_token
from apps.core.tasks import task_cancel_solicitacao_from_gcal, task_publish_solicitacao_to_gcal
from apps.core.tests.factories import SolicitacaoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

OAUTH = override_settings(GCAL_CLIENT="google", GCAL_AUTH_MODE="oauth")
CLIENT_FACTORY = "apps.core.services.gcal_client_factory.get_oauth_client_for_user"


def _pendente_gcal(**extra) -> Solicitacao:
    """Aprovada e já PENDING — o estado em que o request deixa a linha antes da task rodar."""
    sol = SolicitacaoFactory(status="aprovado", **extra)
    sol.gcal_status = Solicitacao.GCalStatus.PENDING
    sol.save(update_fields=["gcal_status"])
    return sol


def _ultimo_erro(sol: Solicitacao) -> AuditLog:
    return AuditLog.objects.filter(action=AuditLog.Action.PUBLISH_GCAL_ERROR, details__solicitacao_id=sol.id).latest(
        "created_at"
    )


def _cliente_fake():
    client = Mock()
    client.credential.google_email = "operador@aprendereditora.com.br"
    return client, "cal-org"


@OAUTH
def test_publish_sem_credencial_marca_error_e_nao_fica_pending():
    operador = UsuarioFactory()  # sem GoogleOAuthCredential
    sol = _pendente_gcal()

    resultado = task_publish_solicitacao_to_gcal(sol.id, operator_user_id=operador.pk)

    assert resultado["action"] == "ERROR"
    sol.refresh_from_db()
    assert sol.gcal_status == Solicitacao.GCalStatus.ERROR
    assert "conecte sua conta Google" in sol.gcal_last_error
    assert _ultimo_erro(sol).usuario_id == operador.pk


@OAUTH
def test_publish_invalid_grant_marca_error_com_mensagem_de_reconexao():
    operador = UsuarioFactory()
    sol = _pendente_gcal()

    with patch(CLIENT_FACTORY, side_effect=ValueError("refresh token revogado (invalid_grant)")):
        task_publish_solicitacao_to_gcal(sol.id, operator_user_id=operador.pk)

    sol.refresh_from_db()
    assert sol.gcal_status == Solicitacao.GCalStatus.ERROR
    assert "conecte sua conta Google" in sol.gcal_last_error
    assert "invalid_grant" in _ultimo_erro(sol).details["error"]  # erro cru preservado


@OAUTH
def test_publish_falha_de_rede_no_refresh_marca_error():
    """O refresh levanta Exception genérica em erro de rede (token_manager) — não pode escapar da task."""
    operador = UsuarioFactory()
    sol = _pendente_gcal()

    with patch(CLIENT_FACTORY, side_effect=Exception("Falha ao atualizar token Google: timeout")):
        resultado = task_publish_solicitacao_to_gcal(sol.id, operator_user_id=operador.pk)

    assert resultado["action"] == "ERROR"
    sol.refresh_from_db()
    assert sol.gcal_status == Solicitacao.GCalStatus.ERROR
    assert "Falha ao atualizar token Google" in sol.gcal_last_error


@OAUTH
def test_publish_operador_inexistente_marca_error():
    sol = _pendente_gcal()

    resultado = task_publish_solicitacao_to_gcal(sol.id, operator_user_id=999_999)

    assert resultado["error"] == "operator_not_found"
    sol.refresh_from_db()
    assert sol.gcal_status == Solicitacao.GCalStatus.ERROR


@OAUTH
def test_publish_http_403_grava_mensagem_acionavel_e_audit_com_erro_cru():
    operador = UsuarioFactory()
    sol = _pendente_gcal()
    recusado = HttpError(resp=Mock(status=403, reason="Forbidden"), content=b'{"error": {"message": "Forbidden"}}')

    with (
        patch(CLIENT_FACTORY, return_value=_cliente_fake()),
        patch("apps.core.services.gcal_sync_service.apply_one_solicitacao", side_effect=recusado),
    ):
        task_publish_solicitacao_to_gcal(sol.id, operator_user_id=operador.pk)

    sol.refresh_from_db()
    assert sol.gcal_status == Solicitacao.GCalStatus.ERROR
    assert "calendário da organização" in sol.gcal_last_error
    audit = _ultimo_erro(sol)
    assert "403" in audit.details["error"]
    assert audit.usuario_id == operador.pk


@OAUTH
def test_cancel_sem_credencial_marca_error_e_mantem_external_event_id():
    operador = UsuarioFactory()
    sol = _pendente_gcal(external_event_id="asv2x1")

    resultado = task_cancel_solicitacao_from_gcal(sol.id, operator_user_id=operador.pk)

    assert resultado["action"] == "ERROR"
    sol.refresh_from_db()
    assert sol.gcal_status == Solicitacao.GCalStatus.ERROR
    assert sol.external_event_id == "asv2x1"
    assert "conecte sua conta Google" in sol.gcal_last_error


@OAUTH
def test_cancel_excecao_marca_error_e_mantem_external_event_id():
    operador = UsuarioFactory()
    sol = _pendente_gcal(external_event_id="asv2x2")

    with (
        patch(CLIENT_FACTORY, return_value=_cliente_fake()),
        patch("apps.core.services.gcal_sync_service.cancel_solicitacao", side_effect=RuntimeError("boom no delete")),
    ):
        resultado = task_cancel_solicitacao_from_gcal(sol.id, operator_user_id=operador.pk)

    assert resultado["action"] == "ERROR"
    sol.refresh_from_db()
    assert sol.gcal_status == Solicitacao.GCalStatus.ERROR
    assert sol.external_event_id == "asv2x2"
    assert _ultimo_erro(sol).details["operation"] == "cancel"


def test_mensagem_invalid_grant_nao_cita_pre_agenda():
    """A Apoio não abre a Pré-agenda: a mensagem de token revogado não pode mandá-la para lá."""
    from apps.core.services.oauth import token_manager

    usuario = UsuarioFactory()
    cred = GoogleOAuthCredential.objects.create(
        user=usuario,
        google_email="apoio@aprendereditora.com.br",
        access_token_encrypted=encrypt_token("velho"),
        refresh_token_encrypted=encrypt_token("revogado"),
        token_expiry=timezone.now() - timedelta(hours=2),
        scope="https://www.googleapis.com/auth/calendar",
    )
    resposta = Mock(status_code=400)
    resposta.json.return_value = {"error": "invalid_grant"}

    with (
        patch.dict("os.environ", {"GCAL_OAUTH_CLIENT_ID": "id", "GCAL_OAUTH_CLIENT_SECRET": "segredo"}),
        patch.object(token_manager.requests, "post") as post,
    ):
        post.return_value.raise_for_status.side_effect = requests.exceptions.HTTPError(response=resposta)
        with pytest.raises(ValueError) as erro:
            token_manager.refresh_access_token_safe(cred)

    assert "Pré-agenda" not in str(erro.value)
    assert "conecte sua conta Google" in str(erro.value)

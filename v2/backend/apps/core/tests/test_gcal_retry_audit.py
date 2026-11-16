"""
Testes Sprint 4 - Audit Log + Error Handling + Retry Policy

Cobertura:
- Retry/backoff exponencial em 429/5xx (cliente real sobre respostas HTTP prontas; desde o FER-60
  o retry e o da biblioteca do Google, `execute(num_retries=...)`)
- Persistência de gcal_last_error/gcal_last_sync_at
- AuditLog com PUBLISH_GCAL_ERROR/PUBLISH_GCAL_SUCCESS
- Endpoint de status (opcional)

100% fake/mocked, sem rede real.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

import json
from datetime import timedelta
from unittest.mock import MagicMock, Mock, patch

from django.utils import timezone
from rest_framework import status as http_status
from rest_framework.test import APIClient

import pytest
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import HttpMockSequence

from apps.core.models import AuditLog, Solicitacao
from apps.core.services.gcal_google_client import GoogleCalendarClient
from apps.core.tests.factories import (
    GroupFactory,
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
    com_pacote_do_controle,
)


@pytest.fixture
def usuario_controle():
    """Usuário do grupo Controle"""
    user = UsuarioFactory(
        username="controle_sprint4",
        email="controle_sprint4@test.com",
        password="testpass",
        cpf="88888888888",
    )
    grupo = GroupFactory(name="Controle")
    user.groups.add(grupo)
    com_pacote_do_controle(user)
    return user


@pytest.fixture
def solicitacao_aprovada(usuario_controle):
    """Solicitação aprovada para testes"""
    municipio = MunicipioFactory(nome="Fortaleza", uf="CE", ativo=True)
    projeto = ProjetoFactory(nome="Projeto Sprint4", codigo="SP4", fluxo="SUPER", ativo=True)
    tipo_evento = TipoEventoFactory(nome="Formação Sprint4")

    now = timezone.now()
    return SolicitacaoFactory(
        usuario=usuario_controle,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo_evento,
        tipo="evento",
        inicio=now + timedelta(days=1),
        fim=now + timedelta(days=1, hours=3),
        status="aprovado",
        gcal_status=Solicitacao.GCalStatus.NONE,
    )


def create_http_error(status_code, reason="Test error"):
    """Helper para criar HttpError mock"""
    resp = MagicMock()
    resp.status = status_code
    resp.reason = reason
    return HttpError(resp, b"Error content")


class _HttpQueConta(HttpMockSequence):
    """HttpMockSequence que conta as requisicoes que sairam."""

    def __init__(self, respostas):
        super().__init__(respostas)
        self.chamadas = 0

    def request(self, *args, **kwargs):
        self.chamadas += 1
        return super().request(*args, **kwargs)


def _resposta(status_code, corpo):
    return ({"status": str(status_code)}, json.dumps(corpo).encode())


def _cliente_google_sobre(respostas):
    """GoogleCalendarClient de verdade sobre respostas HTTP prontas (sem rede)."""
    http = _HttpQueConta(list(respostas))
    cliente = GoogleCalendarClient.__new__(GoogleCalendarClient)
    cliente.service = build("calendar", "v3", http=http, static_discovery=True, cache_discovery=False)
    return cliente, http


@pytest.mark.django_db
class TestRetryBackoff:
    """Testes de retry com backoff exponencial"""

    @pytest.mark.parametrize(
        "status_code, falhas",
        [(429, 2), (503, 1)],
        ids=["429-rate-limit", "5xx-server-error"],
    )
    @patch("apps.core.services.gcal_client_factory.get_gcal_client_and_calendar_id")
    def test_retry_on_429_and_5xx(self, mock_factory, monkeypatch, solicitacao_aprovada, status_code, falhas):
        """
        Casos 1 e 2: o client faz retry em 429 (rate limit) e 5xx (server error) ate dar certo.

        Desde o FER-60 o retry e o da biblioteca do Google, dentro do client: a publicacao
        ve uma operacao so, que deu certo.
        """
        from apps.core.services.gcal_sync_service import apply_one_solicitacao

        monkeypatch.setattr("time.sleep", lambda _s: None)  # backoff da biblioteca sem esperar
        event_id = f"asv2{solicitacao_aprovada.id}"
        erro = _resposta(status_code, {"error": {"code": status_code, "message": "x"}})
        cliente, http = _cliente_google_sobre(
            [
                _resposta(404, {"error": {"code": 404, "message": "Not Found"}}),  # get: evento nao existe
                *[erro] * falhas,
                _resposta(200, {"id": event_id, "summary": "Test"}),
            ]
        )
        mock_factory.return_value = (cliente, "test-calendar-id")

        outcome = apply_one_solicitacao(solicitacao_aprovada, dry_run=False, apply_blocked=True)

        # 1 get + insert com as falhas e o sucesso
        assert http.chamadas == 1 + falhas + 1
        assert outcome.action == "CREATE"
        assert outcome.external_event_id == event_id

    @patch("apps.core.services.gcal_client_factory.get_gcal_client_and_calendar_id")
    def test_no_retry_on_404_not_found(self, mock_factory, solicitacao_aprovada):
        """
        Caso 3: Client NÃO deve fazer retry em 404 (esperado em alguns casos)
        """
        from apps.core.services.gcal_sync_service import apply_one_solicitacao

        mock_client = MagicMock()
        mock_calendar_id = "test-calendar-id"
        mock_factory.return_value = (mock_client, mock_calendar_id)

        # get() retorna None (404)
        mock_client.get.return_value = None
        # insert() sucede normalmente
        mock_client.insert.return_value = {"id": f"asv2{solicitacao_aprovada.id}", "summary": "Test"}

        outcome = apply_one_solicitacao(solicitacao_aprovada, dry_run=False, apply_blocked=True)

        # Deve ter chamado apenas 1x (sem retry)
        assert mock_client.insert.call_count == 1
        assert outcome.action == "CREATE"


@pytest.mark.django_db
class TestErrorPersistence:
    """Testes de persistência de erros em gcal_last_error"""

    @patch("apps.core.services.gcal_client_factory.get_gcal_client_and_calendar_id")
    def test_persist_error_on_failure(self, mock_factory, solicitacao_aprovada):
        """
        Caso 4: Erros devem ser persistidos em gcal_last_error
        """
        from apps.core.services.gcal_sync_service import apply_one_solicitacao

        mock_client = MagicMock()
        mock_factory.return_value = (mock_client, "test-calendar-id")

        # Simular erro permanente (max retries exceeded)
        mock_client.get.return_value = None
        mock_client.insert.side_effect = create_http_error(500, "Internal Server Error")

        # Deve falhar após retries
        with pytest.raises(HttpError):
            apply_one_solicitacao(solicitacao_aprovada, dry_run=False, apply_blocked=True)

        # Verificar que erro foi persistido
        solicitacao_aprovada.refresh_from_db()
        assert solicitacao_aprovada.gcal_status == Solicitacao.GCalStatus.ERROR
        assert (
            "500" in solicitacao_aprovada.gcal_last_error
            or "Internal Server Error" in solicitacao_aprovada.gcal_last_error
        )

    @patch("apps.core.services.gcal_client_factory.get_gcal_client_and_calendar_id")
    def test_clear_error_on_success(self, mock_factory, solicitacao_aprovada):
        """
        Caso 5: gcal_last_error deve ser limpo em caso de sucesso
        """
        from apps.core.services.gcal_sync_service import apply_one_solicitacao

        # Marcar erro anterior
        solicitacao_aprovada.mark_gcal(status=Solicitacao.GCalStatus.ERROR, payload_hash=None, error="Previous error")
        solicitacao_aprovada.save()

        mock_client = MagicMock()
        mock_factory.return_value = (mock_client, "test-calendar-id")
        mock_client.get.return_value = None
        mock_client.insert.return_value = {"id": f"asv2{solicitacao_aprovada.id}", "summary": "Test"}

        # Aplicar com sucesso
        outcome = apply_one_solicitacao(solicitacao_aprovada, dry_run=False, apply_blocked=True)

        # Verificar que erro foi limpo
        solicitacao_aprovada.refresh_from_db()
        assert outcome.action == "CREATE"
        assert solicitacao_aprovada.gcal_status == Solicitacao.GCalStatus.PUBLISHED
        assert solicitacao_aprovada.gcal_last_error == ""


@pytest.mark.django_db
class TestAuditLog:
    """Testes de AuditLog para erros e sucessos"""

    @patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay")
    @patch("django.conf.settings.GCAL_CLIENT", "fake")
    @patch("rest_framework.throttling.AnonRateThrottle.allow_request", return_value=True)
    @patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True)
    def test_audit_log_on_publish_request(
        self, mock_throttle1, mock_throttle2, mock_task, solicitacao_aprovada, usuario_controle
    ):
        """
        Caso 6: AuditLog deve registrar PUBLISH_GCAL_REQUESTED ao enfileirar task
        """
        mock_task.return_value = Mock(id="test-task-id")

        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        response = client.post(
            f"/api/solicitacoes/{solicitacao_aprovada.id}/publish/",
            {"dry_run": False, "apply_blocked": True},
            format="json",
        )

        assert response.status_code == http_status.HTTP_202_ACCEPTED

        # Verificar AuditLog
        audit_log = AuditLog.objects.filter(
            action="PUBLISH_GCAL_REQUESTED",
            usuario=usuario_controle,
        ).latest("created_at")

        assert audit_log is not None
        assert audit_log.model_name == "Solicitacao"
        assert audit_log.details["solicitacao_id"] == solicitacao_aprovada.id
        assert audit_log.details["task_id"] == "test-task-id"

    @patch("apps.core.services.gcal_client_factory.get_gcal_client_and_calendar_id")
    def test_task_logs_success_in_audit(self, mock_factory, solicitacao_aprovada):
        """
        Caso 7: Task deve registrar sucesso em AuditLog
        """
        from apps.core.tasks import task_publish_solicitacao_to_gcal

        mock_client = MagicMock()
        mock_factory.return_value = (mock_client, "test-calendar-id")
        mock_client.get.return_value = None
        mock_client.insert.return_value = {"id": f"asv2{solicitacao_aprovada.id}", "summary": "Test"}

        # Executar task (síncrona para teste)
        result = task_publish_solicitacao_to_gcal(solicitacao_aprovada.id, dry_run=False, apply_blocked=True)

        assert result["action"] == "CREATE"
        assert result["error"] is None

        # Verificar AuditLog
        audit_log = AuditLog.objects.filter(
            action="PUBLISH_GCAL",
            model_name="Solicitacao",
        ).latest("created_at")

        assert audit_log is not None
        assert audit_log.details["solicitacao_id"] == solicitacao_aprovada.id
        assert audit_log.details["action"] == "CREATE"

    @patch("apps.core.services.gcal_client_factory.get_gcal_client_and_calendar_id")
    def test_task_logs_error_in_audit(self, mock_factory, solicitacao_aprovada):
        """
        Caso 8: Task deve registrar erro em AuditLog
        """
        from apps.core.tasks import task_publish_solicitacao_to_gcal

        mock_client = MagicMock()
        mock_factory.return_value = (mock_client, "test-calendar-id")
        mock_client.get.return_value = None
        mock_client.insert.side_effect = create_http_error(500, "Server Error")

        # Executar task (deve tratar erro)
        result = task_publish_solicitacao_to_gcal(solicitacao_aprovada.id, dry_run=False, apply_blocked=True)

        assert result["action"] == "ERROR"
        assert result["error"] is not None

        # Verificar AuditLog
        audit_log = AuditLog.objects.filter(
            action="PUBLISH_GCAL_ERROR",
            model_name="Solicitacao",
        ).latest("created_at")

        assert audit_log is not None
        assert audit_log.details["solicitacao_id"] == solicitacao_aprovada.id
        assert "error" in audit_log.details
        assert audit_log.details["dry_run"] is False
        assert audit_log.details["apply_blocked"] is True

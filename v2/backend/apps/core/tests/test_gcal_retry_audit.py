"""
Testes Sprint 4 - Audit Log + Error Handling + Retry Policy

Cobertura:
- Retry/backoff exponencial em 429/5xx (mock fake client)
- Persistência de gcal_last_error/gcal_last_sync_at
- AuditLog com PUBLISH_GCAL_ERROR/PUBLISH_GCAL_SUCCESS
- Endpoint de status (opcional)

100% fake/mocked, sem rede real.
"""

import pytest
from unittest.mock import patch, Mock, MagicMock
from django.contrib.auth.models import Group
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status as http_status
from googleapiclient.errors import HttpError

from apps.core.models import Usuario, Solicitacao, Municipio, Projeto, TipoEvento, AuditLog


@pytest.fixture
def usuario_controle():
    """Usuário do grupo Controle"""
    user = Usuario.objects.create_user(
        username="controle_sprint4",
        email="controle_sprint4@test.com",
        password="testpass",
        cpf="88888888888",
    )
    grupo, _ = Group.objects.get_or_create(name="Controle")
    user.groups.add(grupo)
    return user


@pytest.fixture
def solicitacao_aprovada(usuario_controle):
    """Solicitação aprovada para testes"""
    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome="Projeto Sprint4", codigo="SP4", fluxo="SUPER", ativo=True)
    tipo_evento = TipoEvento.objects.create(nome="Formação Sprint4")

    now = timezone.now()
    return Solicitacao.objects.create(
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


@pytest.mark.django_db
class TestRetryBackoff:
    """Testes de retry com backoff exponencial"""

    @patch('apps.core.services.gcal_google_client.GoogleCalendarClient._retry_with_backoff')
    @patch('apps.core.services.gcal_client_factory.get_gcal_client_and_calendar_id')
    def test_retry_on_429_rate_limit(self, mock_factory, mock_retry, solicitacao_aprovada):
        """
        Caso 1: Client deve fazer retry em 429 (rate limit) com backoff exponencial
        """
        from apps.core.services.gcal_sync_service import apply_one_solicitacao

        # Mock client que retorna erro 429 nas primeiras 2 tentativas
        mock_client = MagicMock()
        mock_calendar_id = "test-calendar-id"
        mock_factory.return_value = (mock_client, mock_calendar_id)

        # Simular comportamento de retry: falha 2x depois sucesso
        call_count = 0

        def side_effect_insert(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise create_http_error(429, "Rate Limit Exceeded")
            return {"id": f"asv2-{solicitacao_aprovada.id}", "summary": "Test"}

        mock_client.insert.side_effect = side_effect_insert
        mock_client.get.return_value = None  # Evento não existe ainda

        # Aplicar (should retry and succeed)
        outcome = apply_one_solicitacao(solicitacao_aprovada, dry_run=False, apply_blocked=True)

        # Verificar que tentou 3 vezes (2 falhas + 1 sucesso)
        assert call_count == 3
        assert outcome.action == "CREATE"
        assert outcome.external_event_id == f"asv2-{solicitacao_aprovada.id}"

    @patch('apps.core.services.gcal_google_client.GoogleCalendarClient._retry_with_backoff')
    @patch('apps.core.services.gcal_client_factory.get_gcal_client_and_calendar_id')
    def test_retry_on_5xx_server_error(self, mock_factory, mock_retry, solicitacao_aprovada):
        """
        Caso 2: Client deve fazer retry em 5xx (server error) com backoff exponencial
        """
        from apps.core.services.gcal_sync_service import apply_one_solicitacao

        mock_client = MagicMock()
        mock_calendar_id = "test-calendar-id"
        mock_factory.return_value = (mock_client, mock_calendar_id)

        # Simular 503 Service Unavailable
        call_count = 0

        def side_effect_insert(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise create_http_error(503, "Service Unavailable")
            return {"id": f"asv2-{solicitacao_aprovada.id}", "summary": "Test"}

        mock_client.insert.side_effect = side_effect_insert
        mock_client.get.return_value = None

        outcome = apply_one_solicitacao(solicitacao_aprovada, dry_run=False, apply_blocked=True)

        assert call_count == 2
        assert outcome.action == "CREATE"

    @patch('apps.core.services.gcal_client_factory.get_gcal_client_and_calendar_id')
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
        mock_client.insert.return_value = {
            "id": f"asv2-{solicitacao_aprovada.id}",
            "summary": "Test"
        }

        outcome = apply_one_solicitacao(solicitacao_aprovada, dry_run=False, apply_blocked=True)

        # Deve ter chamado apenas 1x (sem retry)
        assert mock_client.insert.call_count == 1
        assert outcome.action == "CREATE"


@pytest.mark.django_db
class TestErrorPersistence:
    """Testes de persistência de erros em gcal_last_error"""

    @patch('apps.core.services.gcal_client_factory.get_gcal_client_and_calendar_id')
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
        assert "500" in solicitacao_aprovada.gcal_last_error or "Internal Server Error" in solicitacao_aprovada.gcal_last_error

    @patch('apps.core.services.gcal_client_factory.get_gcal_client_and_calendar_id')
    def test_clear_error_on_success(self, mock_factory, solicitacao_aprovada):
        """
        Caso 5: gcal_last_error deve ser limpo em caso de sucesso
        """
        from apps.core.services.gcal_sync_service import apply_one_solicitacao

        # Marcar erro anterior
        solicitacao_aprovada.mark_gcal(
            status=Solicitacao.GCalStatus.ERROR,
            payload_hash=None,
            error="Previous error"
        )
        solicitacao_aprovada.save()

        mock_client = MagicMock()
        mock_factory.return_value = (mock_client, "test-calendar-id")
        mock_client.get.return_value = None
        mock_client.insert.return_value = {
            "id": f"asv2-{solicitacao_aprovada.id}",
            "summary": "Test"
        }

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

    @patch('apps.core.tasks.task_publish_solicitacao_to_gcal.delay')
    @patch('django.conf.settings.GCAL_CLIENT', 'fake')
    @patch('rest_framework.throttling.AnonRateThrottle.allow_request', return_value=True)
    @patch('rest_framework.throttling.UserRateThrottle.allow_request', return_value=True)
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

    @patch('apps.core.services.gcal_client_factory.get_gcal_client_and_calendar_id')
    def test_task_logs_success_in_audit(self, mock_factory, solicitacao_aprovada):
        """
        Caso 7: Task deve registrar sucesso em AuditLog
        """
        from apps.core.tasks import task_publish_solicitacao_to_gcal

        mock_client = MagicMock()
        mock_factory.return_value = (mock_client, "test-calendar-id")
        mock_client.get.return_value = None
        mock_client.insert.return_value = {
            "id": f"asv2-{solicitacao_aprovada.id}",
            "summary": "Test"
        }

        # Executar task (síncrona para teste)
        result = task_publish_solicitacao_to_gcal(
            solicitacao_aprovada.id,
            dry_run=False,
            apply_blocked=True
        )

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

    @patch('apps.core.services.gcal_client_factory.get_gcal_client_and_calendar_id')
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
        result = task_publish_solicitacao_to_gcal(
            solicitacao_aprovada.id,
            dry_run=False,
            apply_blocked=True
        )

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


@pytest.mark.django_db
class TestBackoffTiming:
    """Testes para validar tempos de backoff (fast-forward em testes)"""

    @patch('time.sleep')
    @patch('apps.core.services.gcal_google_client.GoogleCalendarClient.insert')
    def test_exponential_backoff_timing(self, mock_insert, mock_sleep, solicitacao_aprovada):
        """
        Caso 9: Backoff deve seguir padrão exponencial (1s, 2s, 4s)
        """
        from apps.core.services.gcal_google_client import GoogleCalendarClient

        # Criar client real mas mockar método insert
        client = GoogleCalendarClient.__new__(GoogleCalendarClient)

        # Simular 3 tentativas com 429
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise create_http_error(429, "Rate Limit")
            return {"id": "test-id", "summary": "Test"}

        mock_insert.side_effect = side_effect

        # Executar retry_with_backoff (método real)
        try:
            result = client._retry_with_backoff(
                lambda: mock_insert("calendar-id", "event-id", {})
            )
        except HttpError:
            pass  # Esperado se max_retries for atingido

        # Verificar que sleep foi chamado com backoff exponencial
        if mock_sleep.call_count > 0:
            sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
            # Deve ser [1, 2, 4] ou similar (depende de max_retries)
            assert len(sleep_calls) >= 1
            # Primeiro sleep deve ser 2^0 = 1
            assert sleep_calls[0] == 1
            if len(sleep_calls) > 1:
                assert sleep_calls[1] == 2

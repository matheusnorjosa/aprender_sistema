"""
Testes para Fase 4: Resync/Cancel Google Calendar

Cobertura:
- Helpers: resync_solicitacao() e cancel_solicitacao()
- Task: task_cancel_solicitacao_from_gcal
- Endpoints: /api/solicitacoes/{id}/resync-gcal/ e /api/solicitacoes/{id}/cancel-gcal/

Total: 12 testes
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, Municipio, Projeto, Solicitacao, TipoEvento, Usuario
from apps.core.services.gcal_sync_service import SyncOutcome, cancel_solicitacao, resync_solicitacao
from apps.core.tasks import task_cancel_solicitacao_from_gcal

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def api_client():
    """DRF API client."""
    return APIClient()


@pytest.fixture
def grupo_super(db):
    """Grupo Superintendência."""
    grupo, _ = Group.objects.get_or_create(name="Superintendência")
    return grupo


@pytest.fixture
def grupo_controle(db):
    """Grupo Controle."""
    grupo, _ = Group.objects.get_or_create(name="Controle")
    return grupo


@pytest.fixture
def usuario_super(db, grupo_super):
    """Usuário com perfil Superintendência."""
    usuario = Usuario.objects.create_user(
        username="superintendente", email="super@example.com", password="testpass123", cpf="11111111111"
    )
    usuario.groups.add(grupo_super)
    return usuario


@pytest.fixture
def usuario_controle(db, grupo_controle):
    """Usuário com perfil Controle."""
    usuario = Usuario.objects.create_user(
        username="controle", email="controle@example.com", password="testpass123", cpf="22222222222"
    )
    usuario.groups.add(grupo_controle)
    return usuario


@pytest.fixture
def usuario_coordenador(db):
    """Usuário coordenador (sem permissões especiais)."""
    return Usuario.objects.create_user(
        username="coordenador", email="coord@example.com", password="testpass123", cpf="33333333333"
    )


@pytest.fixture
def municipio(db):
    """Município de teste."""
    return Municipio.objects.create(nome="Fortaleza", uf="CE", ibge_code="2304400")


@pytest.fixture
def tipo_evento(db):
    """Tipo de evento de teste."""
    return TipoEvento.objects.create(nome="Formação", cor="#0000FF")


@pytest.fixture
def projeto(db):
    """Projeto de teste."""
    return Projeto.objects.create(nome="Projeto Teste", fluxo="SUPER")


@pytest.fixture
def solicitacao_aprovada(db, usuario_coordenador, municipio, tipo_evento, projeto):
    """Solicitação aprovada (pronta para publicação)."""
    return Solicitacao.objects.create(
        usuario=usuario_coordenador,
        municipio=municipio,
        tipo_evento=tipo_evento,
        projeto=projeto,
        inicio=timezone.now() + timezone.timedelta(days=1),
        fim=timezone.now() + timezone.timedelta(days=1, hours=2),
        status="aprovado",
        observacoes="Teste resync/cancel",
    )


@pytest.fixture
def solicitacao_publicada(db, solicitacao_aprovada):
    """Solicitação publicada no Google Calendar."""
    solicitacao_aprovada.external_event_id = "test-event-123"
    solicitacao_aprovada.meet_link = "https://meet.google.com/abc-defg-hij"
    solicitacao_aprovada.gcal_payload_hash = "abc123"
    solicitacao_aprovada.gcal_status = Solicitacao.GCalStatus.PUBLISHED
    solicitacao_aprovada.last_synced_at = timezone.now()
    solicitacao_aprovada.last_sync_action = "CREATE"
    solicitacao_aprovada.save()
    return solicitacao_aprovada


# ============================================================================
# TESTES: HELPERS (3 testes)
# ============================================================================


@pytest.mark.django_db
class TestResyncHelper:
    """Testes para helper resync_solicitacao()."""

    def test_resync_requires_approved_status(self, solicitacao_aprovada):
        """Resync requer status='aprovado' (ValueError caso contrário)."""
        solicitacao_aprovada.status = "pendente"
        solicitacao_aprovada.save()

        with pytest.raises(ValueError, match="Apenas solicitações aprovadas"):
            resync_solicitacao(solicitacao_aprovada)

    @patch("apps.core.services.gcal.sync.apply_one_solicitacao")
    def test_resync_resets_hash_and_calls_apply(self, mock_apply, solicitacao_publicada):
        """Resync reseta hash e chama apply_one_solicitacao."""
        # Configurar mock
        mock_apply.return_value = SyncOutcome(
            action="UPDATE",
            solicitation_id=solicitacao_publicada.id,
            external_event_id="test-event-123",
            summary="Updated event",
        )

        # Validar hash inicial
        assert solicitacao_publicada.gcal_payload_hash == "abc123"

        # Executar resync
        outcome = resync_solicitacao(solicitacao_publicada, apply_blocked=False)

        # Validar que hash foi resetado
        solicitacao_publicada.refresh_from_db()
        assert solicitacao_publicada.gcal_payload_hash is None

        # Validar que apply foi chamado
        mock_apply.assert_called_once_with(solicitacao_publicada, dry_run=False, apply_blocked=False)

        # Validar outcome
        assert outcome.action == "UPDATE"
        assert outcome.solicitation_id == solicitacao_publicada.id


@pytest.mark.django_db
class TestCancelHelper:
    """Testes para helper cancel_solicitacao()."""

    def test_cancel_validates_published(self, solicitacao_aprovada):
        """Cancel requer evento publicado (ValueError caso contrário)."""
        # Solicitação aprovada mas não publicada
        assert solicitacao_aprovada.external_event_id is None
        assert solicitacao_aprovada.gcal_status != Solicitacao.GCalStatus.PUBLISHED

        with pytest.raises(ValueError, match="não possui evento publicado"):
            cancel_solicitacao(solicitacao_aprovada)

    @patch("apps.core.services.gcal_client_factory.get_gcal_client_and_calendar_id")
    @patch("apps.core.services.gcal.sync._retry_with_circuit_breaker")
    def test_cancel_deletes_and_clears_fields(self, mock_retry, mock_get_client, solicitacao_publicada):
        """Cancel deleta evento e limpa campos."""
        # Configurar mocks
        mock_client = MagicMock()
        mock_get_client.return_value = (mock_client, "test-calendar@group.calendar.google.com")
        mock_retry.return_value = None  # Sucesso (sem retorno)

        # Executar cancel
        outcome = cancel_solicitacao(solicitacao_publicada)

        # Validar que retry foi chamado com função de delete
        mock_retry.assert_called_once()
        assert "GCal CANCEL" in mock_retry.call_args[1]["operation_name"]

        # Validar campos limpos
        solicitacao_publicada.refresh_from_db()
        assert solicitacao_publicada.external_event_id is None
        assert solicitacao_publicada.meet_link is None
        assert solicitacao_publicada.gcal_payload_hash is None
        assert solicitacao_publicada.gcal_status == Solicitacao.GCalStatus.NONE
        assert solicitacao_publicada.last_sync_action == "DELETE"
        assert solicitacao_publicada.last_sync_error is None

        # Validar outcome
        assert outcome.action == "DELETE"
        assert outcome.solicitation_id == solicitacao_publicada.id
        assert outcome.external_event_id is None


# ============================================================================
# TESTES: TASK CELERY (2 testes)
# ============================================================================


@pytest.mark.django_db
class TestCancelTask:
    """Testes para task_cancel_solicitacao_from_gcal."""

    @patch("apps.core.services.gcal_sync_service.cancel_solicitacao")
    def test_task_cancel_success(self, mock_cancel, solicitacao_publicada):
        """Task executa cancel e cria AuditLog."""
        # Configurar mock
        mock_cancel.return_value = SyncOutcome(
            action="DELETE",
            solicitation_id=solicitacao_publicada.id,
            external_event_id=None,
            summary=f"Solicitação #{solicitacao_publicada.id} (cancelada)",
        )

        # Executar task
        result = task_cancel_solicitacao_from_gcal(solicitacao_publicada.id)

        # Validar resultado
        assert result["action"] == "DELETE"
        assert result["solicitation_id"] == solicitacao_publicada.id
        assert result["error"] is None

        # Validar AuditLog criado
        audit = AuditLog.objects.filter(action="CANCEL_GCAL", model_name="Solicitacao").last()
        assert audit is not None
        assert audit.details["solicitacao_id"] == solicitacao_publicada.id
        assert audit.details["action"] == "DELETE"

    def test_task_cancel_not_found(self):
        """Task trata DoesNotExist (solicitação não encontrada)."""
        result = task_cancel_solicitacao_from_gcal(solicitation_id=99999)

        assert result["action"] == "ERROR"
        assert result["error"] == "DoesNotExist"
        assert "não encontrada" in result["summary"]


# ============================================================================
# TESTES: ENDPOINTS (7 testes)
# ============================================================================


@pytest.mark.django_db
class TestResyncEndpoint:
    """Testes para POST /api/solicitacoes/{id}/resync-gcal/."""

    def test_resync_endpoint_requires_approved(self, api_client, usuario_controle, solicitacao_aprovada):
        """Endpoint retorna 400 se solicitação não aprovada."""
        api_client.force_authenticate(user=usuario_controle)

        # Mudar status para pendente
        solicitacao_aprovada.status = "pendente"
        solicitacao_aprovada.save()

        response = api_client.post(f"/api/solicitacoes/{solicitacao_aprovada.id}/resync-gcal/")

        assert response.status_code == 400
        assert "aprovadas" in response.data["detail"]

    @patch("apps.core.tasks.task_publish_solicitacao_to_gcal")
    def test_resync_endpoint_success(self, mock_task, api_client, usuario_controle, solicitacao_aprovada):
        """Endpoint retorna 202 + task_id + cria AuditLog."""
        api_client.force_authenticate(user=usuario_controle)

        # Configurar mock task
        mock_task.delay.return_value = MagicMock(id="task-123")

        response = api_client.post(f"/api/solicitacoes/{solicitacao_aprovada.id}/resync-gcal/")

        assert response.status_code == 202
        assert response.data["task_id"] == "task-123"
        assert "Resincronização solicitada" in response.data["detail"]

        # Validar AuditLog
        audit = AuditLog.objects.filter(action="RESYNC_GCAL_REQUESTED", model_name="Solicitacao").last()
        assert audit is not None
        assert audit.usuario == usuario_controle
        assert audit.details["solicitacao_id"] == solicitacao_aprovada.id

        # Validar solicitação marcada como PENDING
        solicitacao_aprovada.refresh_from_db()
        assert solicitacao_aprovada.gcal_status == Solicitacao.GCalStatus.PENDING

    def test_resync_endpoint_requires_permission(self, api_client, usuario_coordenador, solicitacao_aprovada):
        """Endpoint retorna 403 para usuários sem permissão (IsControleOrSuper)."""
        api_client.force_authenticate(user=usuario_coordenador)

        response = api_client.post(f"/api/solicitacoes/{solicitacao_aprovada.id}/resync-gcal/")

        assert response.status_code == 403


@pytest.mark.django_db
class TestCancelEndpoint:
    """Testes para POST /api/solicitacoes/{id}/cancel-gcal/."""

    def test_cancel_endpoint_requires_published(self, api_client, usuario_controle, solicitacao_aprovada):
        """Endpoint retorna 409 se evento não publicado."""
        api_client.force_authenticate(user=usuario_controle)

        # Solicitação aprovada mas não publicada
        assert solicitacao_aprovada.external_event_id is None

        response = api_client.post(f"/api/solicitacoes/{solicitacao_aprovada.id}/cancel-gcal/")

        assert response.status_code == 409
        assert "não possui evento publicado" in response.data["detail"]

    @patch("apps.core.tasks.task_cancel_solicitacao_from_gcal")
    def test_cancel_endpoint_success(self, mock_task, api_client, usuario_controle, solicitacao_publicada):
        """Endpoint retorna 202 + task_id + cria AuditLog."""
        api_client.force_authenticate(user=usuario_controle)

        # Configurar mock task
        mock_task.delay.return_value = MagicMock(id="task-456")

        response = api_client.post(f"/api/solicitacoes/{solicitacao_publicada.id}/cancel-gcal/")

        assert response.status_code == 202
        assert response.data["task_id"] == "task-456"
        assert "Cancelamento solicitado" in response.data["detail"]

        # Validar AuditLog
        audit = AuditLog.objects.filter(action="CANCEL_GCAL_REQUESTED", model_name="Solicitacao").last()
        assert audit is not None
        assert audit.usuario == usuario_controle
        assert audit.details["solicitacao_id"] == solicitacao_publicada.id
        assert audit.details["external_event_id"] == "test-event-123"

        # Validar solicitação marcada como PENDING temporariamente
        solicitacao_publicada.refresh_from_db()
        assert solicitacao_publicada.gcal_status == Solicitacao.GCalStatus.PENDING

    def test_cancel_endpoint_requires_permission(self, api_client, usuario_coordenador, solicitacao_publicada):
        """Endpoint retorna 403 para usuários sem permissão (IsControleOrSuper)."""
        api_client.force_authenticate(user=usuario_coordenador)

        response = api_client.post(f"/api/solicitacoes/{solicitacao_publicada.id}/cancel-gcal/")

        assert response.status_code == 403

    @patch("apps.core.services.gcal_client_factory.get_gcal_client_and_calendar_id")
    @patch("apps.core.services.gcal.sync._retry_with_circuit_breaker")
    def test_cancel_endpoint_idempotent_404(
        self, mock_retry, mock_get_client, api_client, usuario_controle, solicitacao_publicada
    ):
        """Cancel trata 404 como sucesso (idempotência) - testado via helper."""
        # Este teste valida que o helper trata 404 corretamente
        # Configurar mocks
        mock_client = MagicMock()
        mock_get_client.return_value = (mock_client, "test-calendar@group.calendar.google.com")

        # Simular 404 no retry
        def raise_404(*args, **kwargs):
            raise Exception("404 Not Found")

        mock_retry.side_effect = raise_404

        # Executar cancel via helper (não endpoint, pois endpoint é assíncrono)
        # Validar que não levanta exceção
        outcome = cancel_solicitacao(solicitacao_publicada)

        # Validar que campos foram limpos mesmo com 404
        solicitacao_publicada.refresh_from_db()
        assert solicitacao_publicada.external_event_id is None
        assert solicitacao_publicada.gcal_status == Solicitacao.GCalStatus.NONE
        assert outcome.action == "DELETE"

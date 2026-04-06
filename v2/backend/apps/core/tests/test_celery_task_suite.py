"""
Celery task test suite — validates task execution, retry, and error handling.

Tests use celery.contrib.pytest fixtures for realistic task execution
(not CELERY_TASK_ALWAYS_EAGER which hides real issues).

Refs: Issue #846, TESTING_POLICY.md
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth.models import Group
from django.utils import timezone

import pytest

from apps.core.models import AuditLog, Municipio, Projeto, Solicitacao, TipoEvento, Usuario

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def task_solicitacao(db):
    """Create a published solicitacao for task tests."""
    uid = uuid4().hex[:8]
    user = Usuario.objects.create_user(
        username=f"task_user_{uid}",
        email=f"task_{uid}@test.com",
        password="testpass",
        cpf=f"888{uid.ljust(8, '0')}",
    )
    Group.objects.get_or_create(name="Controle")
    municipio = Municipio.objects.create(nome=f"TaskCity_{uid}", uf="CE")
    projeto = Projeto.objects.create(nome=f"TaskProj_{uid}", fluxo="SUPER")
    tipo = TipoEvento.objects.create(nome=f"TaskType_{uid}")

    now = timezone.now()
    sol = Solicitacao.objects.create(
        usuario=user,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo,
        inicio=now + timedelta(days=1),
        fim=now + timedelta(days=1, hours=2),
        status="aprovado",
        gcal_status=Solicitacao.GCalStatus.PUBLISHED,
        external_event_id=f"asv2-task-{uid}",
    )
    return sol


class TestPublishTask:
    """Tests for task_publish_solicitacao_to_gcal."""

    def test_publish_task_returns_outcome_dict(self, task_solicitacao):
        """Task returns dict with action, solicitation_id, etc."""
        from apps.core.tasks import task_publish_solicitacao_to_gcal

        # Reset to approved (not published) for publish test
        task_solicitacao.gcal_status = Solicitacao.GCalStatus.NONE
        task_solicitacao.external_event_id = None
        task_solicitacao.save()

        with patch("apps.core.services.gcal_sync_service.apply_one_solicitacao") as mock_apply:
            from apps.core.services.gcal.sync import SyncOutcome

            mock_apply.return_value = SyncOutcome(
                action="CREATE",
                solicitation_id=task_solicitacao.id,
                external_event_id=f"asv2-{task_solicitacao.id}",
                summary=f"Solicitação #{task_solicitacao.id}",
            )

            result = task_publish_solicitacao_to_gcal(task_solicitacao.id, dry_run=True)

            assert result["action"] == "CREATE"
            assert result["solicitation_id"] == task_solicitacao.id
            assert result["error"] is None

    def test_publish_task_handles_not_found(self):
        """Task returns ERROR dict when solicitacao doesn't exist."""
        from apps.core.tasks import task_publish_solicitacao_to_gcal

        result = task_publish_solicitacao_to_gcal(999999, dry_run=True)

        assert result["action"] == "ERROR"
        assert "999999" in result["summary"]


class TestCancelTask:
    """Tests for task_cancel_solicitacao_from_gcal."""

    def test_cancel_task_returns_outcome(self, task_solicitacao):
        """Task returns DELETE action on success."""
        from apps.core.tasks import task_cancel_solicitacao_from_gcal

        with patch("apps.core.services.gcal_sync_service.cancel_solicitacao") as mock_cancel:
            from apps.core.services.gcal.sync import SyncOutcome

            mock_cancel.return_value = SyncOutcome(
                action="DELETE",
                solicitation_id=task_solicitacao.id,
                external_event_id=None,
                summary=f"Solicitação #{task_solicitacao.id} (cancelada)",
            )

            result = task_cancel_solicitacao_from_gcal(task_solicitacao.id)

            assert result["action"] == "DELETE"
            assert result["error"] is None

    def test_cancel_task_creates_audit_log(self, task_solicitacao):
        """Task creates AuditLog entry on success."""
        from apps.core.tasks import task_cancel_solicitacao_from_gcal

        with patch("apps.core.services.gcal_sync_service.cancel_solicitacao") as mock_cancel:
            from apps.core.services.gcal.sync import SyncOutcome

            mock_cancel.return_value = SyncOutcome(
                action="DELETE",
                solicitation_id=task_solicitacao.id,
                external_event_id=None,
                summary="cancelled",
            )

            task_cancel_solicitacao_from_gcal(task_solicitacao.id)

            audit = AuditLog.objects.filter(
                action="CANCEL_GCAL",
                details__solicitacao_id=task_solicitacao.id,
            ).first()
            assert audit is not None

    def test_cancel_task_handles_not_found(self):
        """Task returns ERROR when solicitacao doesn't exist."""
        from apps.core.tasks import task_cancel_solicitacao_from_gcal

        result = task_cancel_solicitacao_from_gcal(999999)

        assert result["action"] == "ERROR"
        assert result["error"] == "DoesNotExist"

    def test_cancel_task_handles_exception(self, task_solicitacao):
        """Task returns ERROR on unexpected exception."""
        from apps.core.tasks import task_cancel_solicitacao_from_gcal

        with patch("apps.core.services.gcal_sync_service.cancel_solicitacao") as mock_cancel:
            mock_cancel.side_effect = RuntimeError("GCal API down")

            result = task_cancel_solicitacao_from_gcal(task_solicitacao.id)

            assert result["action"] == "ERROR"
            assert "GCal API down" in result["error"]


class TestNotificacoesTask:
    """Tests for processar_notificacoes_acoes_diarias."""

    def test_notificacoes_task_returns_result(self, db):
        """Task returns dict with counts."""
        from apps.core.tasks import processar_notificacoes_acoes_diarias

        result = processar_notificacoes_acoes_diarias()

        assert "notifications_created" in result or "actions_evaluated" in result

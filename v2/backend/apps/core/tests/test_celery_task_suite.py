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

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

import pytest

from apps.core.models import AuditLog, Solicitacao
from apps.core.tests.factories import (
    GroupFactory,
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def task_solicitacao(db):
    """Create a published solicitacao for task tests."""
    uid = uuid4().hex[:8]
    user = UsuarioFactory(
        username=f"task_user_{uid}",
        email=f"task_{uid}@test.com",
        password="testpass",
        cpf=f"888{uid.ljust(8, '0')}",
    )
    GroupFactory(name="Controle")
    municipio = MunicipioFactory(nome=f"TaskCity_{uid}", uf="CE")
    projeto = ProjetoFactory(nome=f"TaskProj_{uid}", fluxo="SUPER")
    tipo = TipoEventoFactory(nome=f"TaskType_{uid}")

    now = timezone.now()
    sol = SolicitacaoFactory(
        usuario=user,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo,
        inicio=now + timedelta(days=1),
        fim=now + timedelta(days=1, hours=2),
        status="aprovado",
        gcal_status=Solicitacao.GCalStatus.PUBLISHED,
        external_event_id=f"asv2task{uid}",
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
                external_event_id=f"asv2{task_solicitacao.id}",
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

    def test_publish_task_usa_select_for_update(self, task_solicitacao):
        """#1726: a task deve reler a Solicitacao com select_for_update() (dentro de atomic())
        antes de mutar/persistir — evita lost-update entre publish/cancel concorrentes do
        mesmo evento.

        RED: hoje a task faz `Solicitacao.objects.get(id=...)` puro (sem lock).
        """
        from apps.core.services.gcal.sync import SyncOutcome
        from apps.core.tasks import task_publish_solicitacao_to_gcal

        task_solicitacao.gcal_status = Solicitacao.GCalStatus.NONE
        task_solicitacao.external_event_id = None
        task_solicitacao.save()

        with (
            patch("apps.core.services.gcal_sync_service.apply_one_solicitacao") as mock_apply,
            patch.object(
                Solicitacao.objects, "select_for_update", wraps=Solicitacao.objects.select_for_update
            ) as spy_lock,
        ):
            mock_apply.return_value = SyncOutcome(
                action="CREATE",
                solicitation_id=task_solicitacao.id,
                external_event_id=f"asv2{task_solicitacao.id}",
                summary=f"Solicitação #{task_solicitacao.id}",
            )
            # Publicação real: é ela que persiste. A prévia não trava a linha (#2068,
            # test_so_a_publicacao_real_trava_a_linha_da_solicitacao cobre os dois lados).
            result = task_publish_solicitacao_to_gcal(task_solicitacao.id, dry_run=False)

        assert result["error"] is None
        spy_lock.assert_called()  # a task travou a linha antes de operar


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

    def test_cancel_task_usa_select_for_update(self, task_solicitacao):
        """#1726: idem publish — a task de cancel deve travar a linha (select_for_update
        dentro de atomic()) antes de deletar o evento e limpar os campos de sync.

        RED: hoje faz `Solicitacao.objects.get(id=...)` puro (sem lock).
        """
        from apps.core.services.gcal.sync import SyncOutcome
        from apps.core.tasks import task_cancel_solicitacao_from_gcal

        with (
            patch("apps.core.services.gcal_sync_service.cancel_solicitacao") as mock_cancel,
            patch.object(
                Solicitacao.objects, "select_for_update", wraps=Solicitacao.objects.select_for_update
            ) as spy_lock,
        ):
            mock_cancel.return_value = SyncOutcome(
                action="DELETE",
                solicitation_id=task_solicitacao.id,
                external_event_id=None,
                summary=f"Solicitação #{task_solicitacao.id} (cancelada)",
            )
            result = task_cancel_solicitacao_from_gcal(task_solicitacao.id)

        assert result["error"] is None
        spy_lock.assert_called()

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


_APPLY = "apps.core.services.gcal_sync_service.apply_one_solicitacao"
_CAMPOS_GCAL = ("gcal_status", "gcal_payload_hash", "gcal_last_error", "gcal_last_sync_at")


def _estado_gcal(sol):
    return Solicitacao.objects.filter(pk=sol.pk).values(*_CAMPOS_GCAL).get()


def _travou_a_solicitacao(consultas) -> bool:
    return any("FOR UPDATE" in q["sql"] and 'FROM "core_solicitacao"' in q["sql"] for q in consultas)


def _sincronizou(sol):
    from apps.core.services.gcal.sync import SyncOutcome

    return SyncOutcome(
        action="UPDATE",
        solicitation_id=sol.id,
        external_event_id=sol.external_event_id,
        summary=f"Solicitação #{sol.id}",
    )


def _grava_e_levanta(erro):
    """Imita o apply_one_solicitacao que falha: marca ERROR na linha e relança."""

    def aplicar(s, **_kwargs):
        s.mark_gcal(status=Solicitacao.GCalStatus.ERROR, error="gravação parcial")
        raise erro

    return aplicar


class TestGcalSyncRetryTask:
    """ART-01: a nova tentativa depois do circuit breaker aberto (queue_gcal_sync_retry) grava como o
    publish e o cancel do #1726: linha travada dentro de atomic(), com o except fora do bloco."""

    @pytest.mark.parametrize("dry_run", [True, False], ids=["previa", "publicacao"])
    def test_retry_trava_a_linha_so_fora_do_dry_run(self, task_solicitacao, dry_run):
        """Sem a trava, a nova tentativa desfazia um publish ou cancel feito ao mesmo tempo (lost update).
        A prévia não escreve na linha e não trava, como no publish.

        RED (publicacao): hoje a task faz `Solicitacao.objects.get(id=...)` puro, fora de atomic().
        """
        from apps.core.tasks import queue_gcal_sync_retry

        with (
            patch(_APPLY, return_value=_sincronizou(task_solicitacao)),
            CaptureQueriesContext(connection) as consultas,
        ):
            resultado = queue_gcal_sync_retry(task_solicitacao.id, dry_run=dry_run)

        assert resultado["error"] is None
        assert _travou_a_solicitacao(consultas.captured_queries) is not dry_run

    def test_retry_que_da_certo_grava_o_audit_log(self, task_solicitacao):
        from apps.core.tasks import queue_gcal_sync_retry

        with patch(_APPLY, return_value=_sincronizou(task_solicitacao)):
            resultado = queue_gcal_sync_retry(task_solicitacao.id)

        assert resultado == {
            "action": "UPDATE",
            "solicitation_id": task_solicitacao.id,
            "external_event_id": task_solicitacao.external_event_id,
            "summary": f"Solicitação #{task_solicitacao.id}",
            "retry_attempt": 1,
            "error": None,
        }
        audit = AuditLog.objects.get(
            action=AuditLog.Action.GCAL_RETRY_SUCCESS, details__solicitacao_id=task_solicitacao.id
        )
        assert audit.details == {
            "solicitacao_id": task_solicitacao.id,
            "action": "UPDATE",
            "external_event_id": task_solicitacao.external_event_id,
            "retry_attempt": 1,
        }

    def test_retry_de_solicitacao_que_sumiu_devolve_does_not_exist(self):
        from apps.core.tasks import queue_gcal_sync_retry

        assert queue_gcal_sync_retry(999_999_999) == {
            "action": "ERROR",
            "solicitation_id": 999_999_999,
            "external_event_id": None,
            "summary": "Solicitação #999999999 não encontrada",
            "error": "DoesNotExist",
        }

    def test_retry_que_falha_desfaz_a_gravacao_parcial_e_devolve_error(self, task_solicitacao):
        """O except roda fora do bloco e devolve o mesmo ERROR de hoje; o rollback desfaz o que o
        apply_one_solicitacao gravou antes de levantar.

        RED: hoje a task roda fora de atomic() e a gravação parcial fica.
        """
        from apps.core.tasks import queue_gcal_sync_retry

        antes = _estado_gcal(task_solicitacao)
        with patch(_APPLY, side_effect=_grava_e_levanta(RuntimeError("Google fora do ar"))):
            resultado = queue_gcal_sync_retry(task_solicitacao.id)

        assert resultado == {
            "action": "ERROR",
            "solicitation_id": task_solicitacao.id,
            "external_event_id": None,
            "summary": "Erro ao sincronizar: Google fora do ar",
            "error": "Google fora do ar",
        }
        assert _estado_gcal(task_solicitacao) == antes

    def test_retry_com_breaker_aberto_desfaz_a_gravacao_parcial_e_pede_nova_tentativa(self, task_solicitacao):
        """CircuitBreakerError segue pedindo nova tentativa em 60 s, agora sem deixar gravação parcial.

        RED: hoje a task roda fora de atomic() e a gravação parcial fica.
        """
        from celery.exceptions import Retry

        from apps.core.services.gcal.circuit_breaker import CircuitBreakerError, gcal_breaker
        from apps.core.tasks import queue_gcal_sync_retry

        erro = CircuitBreakerError(gcal_breaker)
        antes = _estado_gcal(task_solicitacao)
        with (
            patch(_APPLY, side_effect=_grava_e_levanta(erro)),
            patch.object(queue_gcal_sync_retry, "retry", side_effect=Retry()) as nova_tentativa,
            pytest.raises(Retry),
        ):
            queue_gcal_sync_retry(task_solicitacao.id)

        nova_tentativa.assert_called_once_with(countdown=60, exc=erro)
        assert _estado_gcal(task_solicitacao) == antes


class TestNotificacoesTask:
    """Tests for processar_notificacoes_acoes_diarias."""

    def test_notificacoes_task_returns_result(self, db):
        """Task returns dict with counts."""
        from apps.core.tasks import processar_notificacoes_acoes_diarias

        result = processar_notificacoes_acoes_diarias()

        assert "notifications_created" in result or "actions_evaluated" in result


def test_limite_brando_global_abaixo_do_duro():
    """#1968: aos 25 min a task recebe SoftTimeLimitExceeded e registra a falha; aos 30 min o SIGKILL não limpa nada."""
    from django.conf import settings

    from config.celery import app

    brando = getattr(settings, "CELERY_TASK_SOFT_TIME_LIMIT", None)
    assert brando is not None
    assert brando < settings.CELERY_TASK_TIME_LIMIT
    assert app.conf.task_soft_time_limit == brando

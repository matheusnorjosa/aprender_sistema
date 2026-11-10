"""
Testes da task Celery task_run_import_job (ASQ-005 fase 1 — #778).

Invoca a task sincronamente via .run() com o service mockado. Nao depende de
worker Celery rodando.

Cobertura:
- Happy path: status=SUCCESS, stats mirrored, AuditLog criado
- Falha: status=FAILED, error_message/error_traceback populados, AuditLog com FAILED
- Idempotencia: segundo run retorna SKIPPED sem re-invocar service
- Job inexistente: retorna NOT_FOUND sem raise
- import_type nao suportado: vai pra FAILED com NotImplementedError
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportUnknownParameterType=false, reportMissingParameterType=false
# pyright: reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportArgumentType=false, reportOptionalMemberAccess=false, reportFunctionMemberAccess=false

from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

import pytest
from celery.exceptions import SoftTimeLimitExceeded

from apps.core.models import AuditLog, AvailabilityBlock, ImportJob
from apps.core.services import bloqueios_import
from apps.core.tasks import task_run_import_job

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="task_user",
        email="task_user@test.com",
        password="testpass123",
        cpf="22222222222",
        first_name="Task",
        last_name="User",
    )


def _job(user, *, dry_run: bool = True, import_type: str | None = None) -> ImportJob:
    return ImportJob.objects.create(
        user=user,
        import_type=import_type or ImportJob.ImportType.BLOQUEIOS,
        dry_run=dry_run,
        file=SimpleUploadedFile("sample.csv", b"usuario,inicio,fim,tipo,motivo\n", content_type="text/csv"),
    )


@pytest.mark.django_db(transaction=True)
class TestTaskHappyPath:
    def test_success_transitions_and_auditlog(self, user):
        job = _job(user, dry_run=True)

        fake_report = {
            "stats": {"created": 4, "updated": 1, "unchanged": 0, "skipped": {"usuario": 0}},
            "pendencias": {"usuarios": [], "dates": [], "outros": []},
            "dry_run": True,
            "file": "ignored-by-mock",
        }
        with patch(
            "apps.core.services.bloqueios_import.import_bloqueios_from_file", return_value=fake_report
        ) as mocked:
            result = task_run_import_job.run(import_job_id=job.id)

        assert result["action"] == "SUCCESS"
        assert result["stats"]["created"] == 4
        mocked.assert_called_once()
        # dry_run e caminho do arquivo devem ser passados
        kwargs = mocked.call_args.kwargs
        assert kwargs["dry_run"] is True
        assert kwargs["path"].endswith(".csv")

        job.refresh_from_db()
        assert job.status == ImportJob.Status.SUCCESS
        assert job.stats["created"] == 4
        assert job.finished_at is not None
        assert job.duration_ms is not None

        # AuditLog criado
        audits = AuditLog.objects.filter(action="IMPORT_JOB_COMPLETED")
        assert audits.count() == 1
        details = audits.first().details
        assert details["import_job_id"] == job.id
        assert details["import_type"] == ImportJob.ImportType.BLOQUEIOS
        assert details["dry_run"] is True
        assert details["stats"]["created"] == 4

    def test_apply_mode_passes_dry_run_false(self, user):
        job = _job(user, dry_run=False)
        fake_report = {"stats": {"created": 1}, "pendencias": {}, "dry_run": False, "file": "x"}
        with patch(
            "apps.core.services.bloqueios_import.import_bloqueios_from_file", return_value=fake_report
        ) as mocked:
            task_run_import_job.run(import_job_id=job.id)
        assert mocked.call_args.kwargs["dry_run"] is False


@pytest.mark.django_db(transaction=True)
class TestTaskFailurePath:
    def test_service_exception_transitions_to_failed(self, user):
        job = _job(user, dry_run=True)

        with patch(
            "apps.core.services.bloqueios_import.import_bloqueios_from_file",
            side_effect=ValueError("arquivo corrompido"),
        ):
            result = task_run_import_job.run(import_job_id=job.id)

        assert result["action"] == "FAILED"
        assert "arquivo corrompido" in result["error"]

        job.refresh_from_db()
        assert job.status == ImportJob.Status.FAILED
        assert "arquivo corrompido" in job.error_message
        assert "ValueError" in job.error_traceback
        assert job.finished_at is not None

        audits = AuditLog.objects.filter(action="IMPORT_JOB_FAILED")
        assert audits.count() == 1
        assert audits.first().details["import_job_id"] == job.id

    def test_long_error_message_is_truncated_to_500(self, user):
        job = _job(user, dry_run=True)
        big_msg = "E" * 1000

        with patch(
            "apps.core.services.bloqueios_import.import_bloqueios_from_file",
            side_effect=RuntimeError(big_msg),
        ):
            task_run_import_job.run(import_job_id=job.id)

        job.refresh_from_db()
        assert len(job.error_message) == 500

    def test_unsupported_import_type_fails(self, user):
        job = ImportJob.objects.create(
            user=user,
            import_type="usuarios",  # ainda nao suportado (fase 2)
            file=SimpleUploadedFile("x.csv", b"a,b\n", content_type="text/csv"),
        )
        result = task_run_import_job.run(import_job_id=job.id)

        assert result["action"] == "FAILED"
        job.refresh_from_db()
        assert job.status == ImportJob.Status.FAILED
        assert "nao suportado" in job.error_message or "NotImplementedError" in job.error_traceback


@pytest.mark.django_db(transaction=True)
class TestTaskIdempotence:
    def test_second_run_returns_skipped_without_reinvoking_service(self, user):
        job = _job(user, dry_run=True)
        fake_report = {"stats": {"created": 1}, "pendencias": {}, "dry_run": True, "file": "x"}

        with patch(
            "apps.core.services.bloqueios_import.import_bloqueios_from_file", return_value=fake_report
        ) as mocked:
            first = task_run_import_job.run(import_job_id=job.id)
            second = task_run_import_job.run(import_job_id=job.id)

        assert first["action"] == "SUCCESS"
        assert second["action"] == "SKIPPED"
        assert second["status"] == ImportJob.Status.SUCCESS
        # Service chamado apenas uma vez
        assert mocked.call_count == 1

    def test_running_job_is_skipped(self, user):
        job = _job(user, dry_run=True)
        # Simula um job que ja transicionou para RUNNING (por outro worker)
        job.mark_running(celery_task_id="prior-worker")

        result = task_run_import_job.run(import_job_id=job.id)
        assert result["action"] == "SKIPPED"


@pytest.mark.django_db(transaction=True)
class TestTaskNotFound:
    def test_nonexistent_job_returns_not_found(self, db):
        result = task_run_import_job.run(import_job_id=999_999_999)
        assert result["action"] == "NOT_FOUND"
        assert result["error"] == "DoesNotExist"


# Duas linhas válidas para o `user` acima ("Task User"), com data antes do corte do Formador.
_CSV_DUAS_LINHAS = (
    b"usuario,inicio,fim,tipo,motivo\n"
    b"Task User,2026-03-01 08:00,2026-03-01 12:00,P,Consulta\n"
    b"Task User,2026-03-02 08:00,2026-03-02 12:00,P,Consulta\n"
)


@pytest.mark.django_db(transaction=True)
class TestTaskSoftTimeLimit:
    """#1968: o limite brando no meio do import vira FAILED com motivo, e o arquivo é desfeito por inteiro."""

    def test_soft_time_limit_no_meio_do_arquivo_falha_sem_gravar(self, user, monkeypatch):
        job = ImportJob.objects.create(
            user=user,
            import_type=ImportJob.ImportType.BLOQUEIOS,
            dry_run=False,
            file=SimpleUploadedFile("duas.csv", _CSV_DUAS_LINHAS, content_type="text/csv"),
        )
        linha_real = bloqueios_import._process_row

        def _estoura_na_linha_2(row, idx, *args):
            if idx == 2:
                raise SoftTimeLimitExceeded()
            return linha_real(row, idx, *args)

        monkeypatch.setattr(bloqueios_import, "_process_row", _estoura_na_linha_2)

        result = task_run_import_job.run(import_job_id=job.id)

        assert result["action"] == "FAILED"
        job.refresh_from_db()
        assert job.status == ImportJob.Status.FAILED
        assert AvailabilityBlock.objects.count() == 0  # a linha 1 também foi desfeita
        assert AuditLog.objects.filter(action="IMPORT_JOB_FAILED", details__import_job_id=job.id).count() == 1

    def test_soft_time_limit_motivo_explicito(self, user):
        job = _job(user, dry_run=True)

        with patch(
            "apps.core.services.bloqueios_import.import_bloqueios_from_file",
            side_effect=SoftTimeLimitExceeded(),
        ):
            result = task_run_import_job.run(import_job_id=job.id)

        assert result["action"] == "FAILED"
        job.refresh_from_db()
        assert job.status == ImportJob.Status.FAILED
        assert "tempo esgotado" in job.error_message.lower()
        audit = AuditLog.objects.get(action="IMPORT_JOB_FAILED", details__import_job_id=job.id)
        assert "tempo esgotado" in audit.details["error"].lower()

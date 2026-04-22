"""
Testes do model ImportJob (ASQ-005 fase 1 — #778).

Cobertura:
- Defaults (status=QUEUED, dry_run=True, stats/pendencias vazios)
- __str__ format
- Ordering (-created_at)
- Transicoes: mark_running, mark_success, mark_failed
- duration_ms e calculado apenas quando started_at existe
- error_message e truncado em 500 chars
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportUnknownParameterType=false, reportMissingParameterType=false
# pyright: reportCallIssue=false, reportOperatorIssue=false, reportArgumentType=false

from __future__ import annotations

import time
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

import pytest

from apps.core.models import ImportJob

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="user_importjob",
        email="user_importjob@test.com",
        password="testpass123",
        cpf="11111111111",
        first_name="Import",
        last_name="User",
    )


def _minimal_file() -> SimpleUploadedFile:
    return SimpleUploadedFile("sample.csv", b"usuario,inicio,fim,tipo,motivo\n", content_type="text/csv")


@pytest.mark.django_db
class TestImportJobDefaults:
    """Campos default ao criar um job."""

    def test_defaults_queued_and_empty(self, user):
        job = ImportJob.objects.create(
            user=user,
            import_type=ImportJob.ImportType.BLOQUEIOS,
            file=_minimal_file(),
        )
        assert job.status == ImportJob.Status.QUEUED
        assert job.dry_run is True
        assert job.stats == {}
        assert job.pendencias == {}
        assert job.error_message == ""
        assert job.error_traceback == ""
        assert job.celery_task_id == ""
        assert job.duration_ms is None
        assert job.started_at is None
        assert job.finished_at is None
        assert job.created_at is not None
        assert job.updated_at is not None

    def test_str_format(self, user):
        job = ImportJob.objects.create(
            user=user,
            import_type=ImportJob.ImportType.BLOQUEIOS,
            file=_minimal_file(),
        )
        rendered = str(job)
        assert job.import_type in rendered
        assert str(job.pk) in rendered
        assert job.status in rendered

    def test_original_filename_persisted(self, user):
        job = ImportJob.objects.create(
            user=user,
            import_type=ImportJob.ImportType.BLOQUEIOS,
            original_filename="planilha-bloqueios.xlsx",
            file=_minimal_file(),
        )
        assert job.original_filename == "planilha-bloqueios.xlsx"


@pytest.mark.django_db
class TestImportJobOrdering:
    """ordering = ['-created_at']."""

    def test_most_recent_first(self, user):
        j1 = ImportJob.objects.create(user=user, import_type=ImportJob.ImportType.BLOQUEIOS, file=_minimal_file())
        # Garante created_at distinto mesmo em bancos com resolucao grosseira
        ImportJob.objects.filter(pk=j1.pk).update(created_at=timezone.now() - timedelta(hours=1))
        j2 = ImportJob.objects.create(user=user, import_type=ImportJob.ImportType.BLOQUEIOS, file=_minimal_file())
        ordered = list(ImportJob.objects.values_list("pk", flat=True))
        assert ordered[0] == j2.pk
        assert ordered[-1] == j1.pk


@pytest.mark.django_db
class TestImportJobTransitions:
    """mark_running / mark_success / mark_failed."""

    def test_mark_running_sets_status_and_timestamps(self, user):
        job = ImportJob.objects.create(user=user, import_type=ImportJob.ImportType.BLOQUEIOS, file=_minimal_file())
        job.mark_running(celery_task_id="celery-task-abc-123")

        job.refresh_from_db()
        assert job.status == ImportJob.Status.RUNNING
        assert job.celery_task_id == "celery-task-abc-123"
        assert job.started_at is not None
        assert job.finished_at is None

    def test_mark_success_populates_payload(self, user):
        job = ImportJob.objects.create(user=user, import_type=ImportJob.ImportType.BLOQUEIOS, file=_minimal_file())
        job.mark_running(celery_task_id="t-1")
        # Pequeno sleep garante duration_ms >= 0
        time.sleep(0.01)
        job.mark_success(
            stats={"created": 3, "updated": 1, "unchanged": 0, "skipped": {"usuario": 0}},
            pendencias={"usuarios": [], "dates": [], "outros": []},
        )

        job.refresh_from_db()
        assert job.status == ImportJob.Status.SUCCESS
        assert job.stats["created"] == 3
        assert job.pendencias["usuarios"] == []
        assert job.finished_at is not None
        assert job.duration_ms is not None
        assert job.duration_ms >= 0

    def test_mark_failed_truncates_message_and_keeps_traceback(self, user):
        job = ImportJob.objects.create(user=user, import_type=ImportJob.ImportType.BLOQUEIOS, file=_minimal_file())
        job.mark_running(celery_task_id="t-2")

        long_msg = "x" * 800  # > 500
        # Traceback sintetico > 500 chars para validar que NAO e truncado
        full_tb = "Traceback (most recent call last):\n  File ...\nRuntimeError: boom\n" * 20

        job.mark_failed(error_message=long_msg, error_traceback=full_tb)

        job.refresh_from_db()
        assert job.status == ImportJob.Status.FAILED
        assert len(job.error_message) == 500  # truncated
        assert "Traceback" in job.error_traceback
        # Traceback nao deve ser truncado (vai para logs/debug interno)
        assert len(job.error_traceback) > 500
        assert job.finished_at is not None
        assert job.duration_ms is not None

    def test_mark_failed_without_started_at_skips_duration(self, user):
        job = ImportJob.objects.create(user=user, import_type=ImportJob.ImportType.BLOQUEIOS, file=_minimal_file())
        # Sem mark_running: started_at permanece None
        job.mark_failed(error_message="erro antes de rodar", error_traceback="")

        job.refresh_from_db()
        assert job.status == ImportJob.Status.FAILED
        assert job.duration_ms is None
        assert job.finished_at is not None

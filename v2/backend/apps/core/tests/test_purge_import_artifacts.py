"""LGPD retencao/minimizacao (arts. 6/16) — testes da task purge_import_job_artifacts.

Verifica que, apos a janela de retencao, os artefatos de PII do ImportJob (arquivo
submetido + pendencias + traceback) sao expurgados, MANTENDO a linha operacional,
de forma idempotente e auditada.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false, reportArgumentType=false, reportCallIssue=false, reportIndexIssue=false

from __future__ import annotations

import os
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

import pytest

from apps.core.models import AuditLog, ImportJob
from apps.core.tasks import purge_import_job_artifacts
from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

_PII_CSV = b"cpf,nome,email\n11144477735,Maria,maria@example.com\n"


def _import_job(*, dias_atras: int):
    job = ImportJob.objects.create(
        user=UsuarioFactory(),
        import_type=ImportJob.ImportType.BLOQUEIOS,
        file=SimpleUploadedFile("planilha.csv", _PII_CSV),
        pendencias={"usuarios": [{"cpf": "11144477735"}]},
        error_traceback="Traceback: valor invalido na linha do CPF 11144477735",
    )
    # created_at tem default=now; backdate via update p/ nao brigar com o default.
    ImportJob.objects.filter(pk=job.pk).update(created_at=timezone.now() - timedelta(days=dias_atras))
    job.refresh_from_db()
    return job


def test_purga_artefatos_de_job_antigo(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    job = _import_job(dias_atras=200)
    file_path = job.file.path
    assert os.path.exists(file_path)

    result = purge_import_job_artifacts()

    assert result["purged"] == 1
    job.refresh_from_db()
    assert ImportJob.objects.filter(pk=job.pk).exists()  # linha preservada (metadata)
    assert not job.file
    assert job.pendencias == {}
    assert job.error_traceback == ""
    assert not os.path.exists(file_path)  # arquivo removido do storage
    assert job.import_type == ImportJob.ImportType.BLOQUEIOS  # metadata operacional intacta


def test_nao_toca_job_dentro_da_retencao(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    job = _import_job(dias_atras=10)  # < 90 dias

    purge_import_job_artifacts()

    job.refresh_from_db()
    assert bool(job.file) is True
    assert job.pendencias != {}


def test_idempotente(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    _import_job(dias_atras=200)

    assert purge_import_job_artifacts()["purged"] == 1
    assert purge_import_job_artifacts()["purged"] == 0  # nada mais a expurgar


def test_audita_o_purge(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    _import_job(dias_atras=200)

    purge_import_job_artifacts()

    log = AuditLog.objects.filter(action=AuditLog.Action.IMPORT_ARTIFACT_PURGE).latest("created_at")
    assert log.details["purged"] == 1
    assert log.details["retention_days"] == 90

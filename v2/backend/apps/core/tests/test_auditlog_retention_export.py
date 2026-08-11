"""LGPD arts. 6/16/37 — retenção do AuditLog (#1) + trilha de exportação (#7).

- Retencao: `purge_old_audit_logs` expurga entradas alem de AUDITLOG_RETENTION_DAYS.
- Export audit: `lgpd_export` grava um AuditLog EXPORT do FATO, sem valores de PII.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false, reportArgumentType=false, reportCallIssue=false, reportIndexIssue=false

from __future__ import annotations

from datetime import timedelta

from django.core.management import call_command
from django.utils import timezone

import pytest

from apps.core.models import AuditLog
from apps.core.tasks import purge_old_audit_logs
from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db


def _audit(*, dias_atras: int, action: str = "LOGIN"):
    log = AuditLog.objects.create(action=action, details={"ip_address": "1.2.3.4"})
    AuditLog.objects.filter(pk=log.pk).update(created_at=timezone.now() - timedelta(days=dias_atras))
    return log


# ------------------------- retenção (#1) -------------------------


def test_purge_expurga_logs_antigos(settings):
    settings.AUDITLOG_RETENTION_DAYS = 1825
    old = _audit(dias_atras=2000)  # > 5 anos
    recent = _audit(dias_atras=30)  # dentro da janela

    result = purge_old_audit_logs()

    assert result["deleted"] == 1
    assert not AuditLog.objects.filter(pk=old.pk).exists()
    assert AuditLog.objects.filter(pk=recent.pk).exists()


def test_purge_idempotente(settings):
    settings.AUDITLOG_RETENTION_DAYS = 1825
    _audit(dias_atras=2000)
    assert purge_old_audit_logs()["deleted"] == 1
    assert purge_old_audit_logs()["deleted"] == 0


def test_purge_respeita_retention_configuravel(settings):
    settings.AUDITLOG_RETENTION_DAYS = 10
    _audit(dias_atras=20)  # fora
    _audit(dias_atras=5)  # dentro
    assert purge_old_audit_logs()["deleted"] == 1


# ------------------------- trilha de export (#7) -------------------------


def test_lgpd_export_registra_trilha_sem_pii(tmp_path):
    user = UsuarioFactory(cpf="11144477735", email="maria@example.com")
    out = tmp_path / "export.json"

    call_command("lgpd_export", cpf="11144477735", output=str(out))

    log = AuditLog.objects.filter(action=AuditLog.Action.EXPORT).latest("created_at")
    assert log.details["target_user_id"] == user.pk
    assert "counts" in log.details
    # o FATO e' auditado, mas os valores de PII do titular NAO entram na trilha
    blob = str(log.details)
    assert "11144477735" not in blob
    assert "maria@example.com" not in blob
    assert out.exists()

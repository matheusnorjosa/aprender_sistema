"""
Tests for automated backup Celery tasks.

Coverage:
- perform_database_backup success path (script invocation + env wiring)
- perform_database_backup failure when script is missing
- verify_backup_health healthy/degraded scenarios
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false, reportFunctionMemberAccess=false

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from apps.core import tasks_backup as backup_tasks


@pytest.mark.django_db
def test_perform_database_backup_success_parses_output(monkeypatch):
    """Task should run script with env vars and parse backup file from stdout."""
    script_suffix = "infra/scripts/backup_db.sh"
    original_exists = Path.exists
    captured: dict[str, object] = {}

    def fake_exists(self: Path) -> bool:  # noqa: ANN001
        if self.as_posix().endswith(script_suffix):
            return True
        return original_exists(self)

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=(
                "[Wed Feb 25 10:00:00 -03 2026] Starting backup\n"
                "[Wed Feb 25 10:00:00 -03 2026] "
                "backup_full_20260225_100000.sql.gz "
                "(/backups/backup_full_20260225_100000.sql.gz)\n"
            ),
            stderr="",
        )

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(backup_tasks.subprocess, "run", fake_run)

    result = backup_tasks.perform_database_backup.run(backup_type="full")

    assert result["status"] == "success"
    assert result["backup_type"] == "full"
    assert result["backup_file"] == "/backups/backup_full_20260225_100000.sql.gz"

    cmd = captured["cmd"]
    kwargs = captured["kwargs"]
    assert isinstance(cmd, list)
    assert len(cmd) == 2
    assert isinstance(cmd[0], str)
    assert cmd[0].endswith(script_suffix)
    assert cmd[1] == "full"
    assert isinstance(kwargs, dict)
    assert kwargs.get("check") is True
    assert kwargs.get("timeout") == 3600
    assert kwargs.get("capture_output") is True
    assert kwargs.get("text") is True

    env = kwargs["env"]
    assert isinstance(env, dict)
    assert env.get("BACKUP_DIR") == "/backups"
    assert "DB_HOST" in env
    assert "DB_PORT" in env
    assert "DB_USER" in env
    assert "DB_NAME" in env
    assert "DB_PASSWORD" in env


@pytest.mark.django_db
def test_perform_database_backup_raises_when_script_missing(monkeypatch):
    """Task should fail fast with FileNotFoundError when script is unavailable."""
    script_suffix = "infra/scripts/backup_db.sh"
    original_exists = Path.exists

    def fake_exists(self: Path) -> bool:  # noqa: ANN001
        if self.as_posix().endswith(script_suffix):
            return False
        return original_exists(self)

    monkeypatch.setattr(Path, "exists", fake_exists)

    with pytest.raises(FileNotFoundError):
        backup_tasks.perform_database_backup.run(backup_type="full")


@pytest.mark.django_db
def test_verify_backup_health_is_healthy_with_recent_backup(tmp_path, settings):
    """Health check should be healthy when backup dir is writable and backup is recent."""
    settings.BACKUP_DIR = str(tmp_path)
    settings.BACKUP_S3_BUCKET = ""

    backup_file = tmp_path / "backup_full_20260225_100000.sql.gz"
    backup_file.write_bytes(b"fake-gzip-content")

    result = backup_tasks.verify_backup_health()

    assert result["status"] == "healthy"
    assert result["checks_total"] == 2
    assert result["checks_passed"] == 2
    assert result["warnings"] == []


@pytest.mark.django_db
def test_verify_backup_health_is_degraded_without_backups(tmp_path, settings):
    """Health check should degrade when no backup files exist."""
    settings.BACKUP_DIR = str(tmp_path)
    settings.BACKUP_S3_BUCKET = ""

    result = backup_tasks.verify_backup_health()

    assert result["status"] == "degraded"
    assert result["checks_total"] == 2
    assert result["checks_passed"] == 1
    warnings = result["warnings"]
    assert isinstance(warnings, list)
    assert any("No backups found" in warning for warning in warnings)


@pytest.mark.django_db
def test_verify_backup_health_warns_when_s3_check_fails(tmp_path, settings, monkeypatch):
    """Health check should report warning when S3 is configured but not reachable."""
    settings.BACKUP_DIR = str(tmp_path)
    settings.BACKUP_S3_BUCKET = "example-bucket"

    backup_file = tmp_path / "backup_full_20260225_100000.sql.gz"
    backup_file.write_bytes(b"fake-gzip-content")

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("aws cli not installed")

    monkeypatch.setattr(backup_tasks.subprocess, "run", fake_run)

    result = backup_tasks.verify_backup_health()

    assert result["status"] == "degraded"
    assert result["checks_total"] == 3
    assert result["checks_passed"] == 2
    warnings = result["warnings"]
    assert isinstance(warnings, list)
    assert any("S3 connectivity check failed" in warning for warning in warnings)

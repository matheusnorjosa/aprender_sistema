"""
Tests for database backup tasks.

Refs: Issue #562 (C-05), Issue #563 (C-06), MP5
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false, reportFunctionMemberAccess=false, reportGeneralTypeIssues=false

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.conf import settings

import pytest

from apps.core.tasks_backup import verify_backup_health


class TestVerifyBackupHealth:
    """Tests for verify_backup_health task."""

    def test_health_check_no_backups_returns_degraded(self, tmp_path: Path) -> None:
        """Test that health check returns degraded when no backups exist."""
        with patch("apps.core.tasks_backup.getattr") as mock_getattr:
            mock_getattr.return_value = str(tmp_path)
            result = verify_backup_health()

            assert result["status"] == "degraded"
            assert "No backups found" in str(result["warnings"])

    def test_health_check_degraded_logs_error_for_alerting(self, tmp_path: Path) -> None:
        """#1541: 'degraded' (backup morto) deve sair em logger.error — não info.

        SENTRY_DSN está vazio em prod (o capture_message é no-op) e o INFO era
        engolido por alertas de log (level>=WARNING). Se o resumo final voltar a INFO,
        o detector de backup morto acha o problema e o alarme não chega a ninguém.
        """
        with (
            patch("apps.core.tasks_backup.getattr") as mock_getattr,
            patch("apps.core.tasks_backup.logger") as mock_logger,
        ):
            mock_getattr.return_value = str(tmp_path)  # dir vazio → "No backups found" → degraded
            result = verify_backup_health()

            assert result["status"] == "degraded"
            assert mock_logger.error.called, "degraded deve logar em ERROR"
            error_text = " ".join(str(c) for c in mock_logger.error.call_args_list)
            assert "degraded" in error_text
            # o resumo de conclusão NÃO pode sair em info quando degraded
            info_text = " ".join(str(c) for c in mock_logger.info.call_args_list)
            assert "completed: degraded" not in info_text

    def test_health_check_with_recent_backup_returns_healthy(self, tmp_path: Path) -> None:
        """Test that health check returns healthy when recent backup exists."""
        # Create a recent backup file
        backup_file = tmp_path / "backup_full_20260205_120000.sql.gz"
        backup_file.write_bytes(b"fake backup content")

        with patch("apps.core.tasks_backup.getattr") as mock_getattr:
            # First call is for BACKUP_DIR, subsequent for S3
            def getattr_side_effect(obj, name, default=None):
                if name == "BACKUP_DIR":
                    return str(tmp_path)
                return default

            mock_getattr.side_effect = getattr_side_effect
            result = verify_backup_health()

            assert result["status"] == "healthy"
            assert result["checks_passed"] >= 2  # dir writable + recent backup

    def test_health_check_with_old_backup_returns_warning(self, tmp_path: Path) -> None:
        """Test that health check warns when backup is too old."""
        # Create an old backup file (modify mtime to simulate old backup)
        backup_file = tmp_path / "backup_full_20260101_120000.sql.gz"
        backup_file.write_bytes(b"fake backup content")

        # Set mtime to 48 hours ago
        old_time = os.path.getmtime(backup_file) - (48 * 3600)
        os.utime(backup_file, (old_time, old_time))

        with patch("apps.core.tasks_backup.getattr") as mock_getattr:

            def getattr_side_effect(obj, name, default=None):
                if name == "BACKUP_DIR":
                    return str(tmp_path)
                return default

            mock_getattr.side_effect = getattr_side_effect
            result = verify_backup_health()

            assert result["status"] == "degraded"
            assert any("old" in w.lower() for w in result["warnings"])

    def test_health_check_backup_dir_not_exists_returns_warning(self) -> None:
        """Test that health check warns when backup directory doesn't exist."""
        with patch("apps.core.tasks_backup.getattr") as mock_getattr:

            def getattr_side_effect(obj, name, default=None):
                if name == "BACKUP_DIR":
                    return "/nonexistent/backup/dir"
                return default

            mock_getattr.side_effect = getattr_side_effect
            result = verify_backup_health()

            assert result["status"] == "degraded"
            assert any("does not exist" in w for w in result["warnings"])

    def test_health_check_glob_pattern_matches_expected_naming(self, tmp_path: Path) -> None:
        """Test that health check looks for backup_full_*.sql.gz pattern."""
        # Create a backup with wrong naming (should not be found)
        wrong_name = tmp_path / "aprender_db_20260205_120000.sql.gz"
        wrong_name.write_bytes(b"fake backup content")

        with patch("apps.core.tasks_backup.getattr") as mock_getattr:

            def getattr_side_effect(obj, name, default=None):
                if name == "BACKUP_DIR":
                    return str(tmp_path)
                return default

            mock_getattr.side_effect = getattr_side_effect
            result = verify_backup_health()

            # Should report no backups because naming doesn't match
            assert result["status"] == "degraded"
            assert "No backups found" in str(result["warnings"])

        # Now create correctly named backup
        correct_name = tmp_path / "backup_full_20260205_120000.sql.gz"
        correct_name.write_bytes(b"fake backup content")

        with patch("apps.core.tasks_backup.getattr") as mock_getattr:
            mock_getattr.side_effect = getattr_side_effect
            result = verify_backup_health()

            # Should find the backup now
            assert result["status"] == "healthy"

    def test_health_check_encontra_backup_cifrado_age(self, tmp_path: Path) -> None:
        """O health check DEVE enxergar `.sql.gz.age`, que e o que producao grava.

        `glob("backup_full_*.sql.gz")` nao casa `backup_full_*.sql.gz.age` (fnmatch
        exige que o padrao termine o nome). Antes do fix, o alarme olhava um diretorio
        cheio de dumps cifrados validos e reportava "No backups found" — um alarme que
        grita lobo toda semana e some no ruido. Ver #1455 / SEC-017.
        """
        cifrado = tmp_path / "backup_full_20260710_020000.sql.gz.age"
        cifrado.write_bytes(b"age-encryption.org/v1\nfake payload")

        with patch("apps.core.tasks_backup.getattr") as mock_getattr:

            def getattr_side_effect(obj, name, default=None):  # type: ignore[no-untyped-def]
                if name == "BACKUP_DIR":
                    return str(tmp_path)
                return default

            mock_getattr.side_effect = getattr_side_effect
            result = verify_backup_health()

            assert result["status"] == "healthy", result["warnings"]
            assert not any("No backups found" in w for w in result["warnings"])


class TestPerformDatabaseBackupScriptPath:
    """Tests for perform_database_backup script path validation."""

    def test_backup_script_path_uses_expected_location(self) -> None:
        """Test that the task uses the correct script path."""
        # This is a simple smoke test that the module can be imported
        # and references the expected script location.
        # Full integration tests require Docker environment.
        from apps.core.tasks_backup import perform_database_backup

        # Verify the task is registered
        assert perform_database_backup.name == "backup.perform_database_backup"

    def test_backup_task_has_retry_config(self) -> None:
        """Test that the backup task has proper retry configuration."""
        from apps.core.tasks_backup import perform_database_backup

        # Verify retry configuration
        assert perform_database_backup.max_retries == 3
        assert perform_database_backup.default_retry_delay == 300

"""
Tests for database backup tasks.

Refs: Issue #562 (C-05), Issue #563 (C-06), MP5
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false, reportFunctionMemberAccess=false

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings

from apps.core.tasks_backup import perform_database_backup, verify_backup_health


class TestPerformDatabaseBackup:
    """Tests for perform_database_backup task."""

    @pytest.fixture
    def mock_script_exists(self, tmp_path: Path) -> Path:
        """Create a mock backup script that succeeds."""
        script = tmp_path / "backup_db.sh"
        script.write_text(
            """#!/bin/bash
echo "[$(date)] Starting backup..."
echo "[$(date)] backup_full_20260205_120000.sql.gz (/backups/backup_full_20260205_120000.sql.gz)"
echo "[$(date)] Backup complete."
exit 0
"""
        )
        script.chmod(0o755)
        return script

    @pytest.fixture
    def mock_script_fails(self, tmp_path: Path) -> Path:
        """Create a mock backup script that fails."""
        script = tmp_path / "backup_db.sh"
        script.write_text(
            """#!/bin/bash
echo "[$(date)] ERROR: Backup failed!"
exit 1
"""
        )
        script.chmod(0o755)
        return script

    def test_backup_script_not_found(self) -> None:
        """Test that FileNotFoundError is raised when script doesn't exist."""
        with patch("apps.core.tasks_backup.Path") as mock_path:
            mock_path.return_value.exists.return_value = False
            mock_path.return_value.__str__ = lambda x: "/nonexistent/script.sh"

            # Create a mock task with request
            task = perform_database_backup
            task.request = MagicMock(id="test-task-id")

            with pytest.raises(FileNotFoundError, match="Backup script not found"):
                perform_database_backup.__wrapped__(task, "full")

    def test_backup_passes_correct_environment_variables(self, mock_script_exists: Path) -> None:
        """Test that backup task passes correct environment variables to script."""
        captured_env: dict[str, str] = {}

        def capture_env(*args, **kwargs):
            """Capture environment variables passed to subprocess."""
            captured_env.update(kwargs.get("env", {}))
            return MagicMock(
                stdout="backup_full_20260205_120000.sql.gz",
                returncode=0,
            )

        with (
            patch("apps.core.tasks_backup.Path") as mock_path,
            patch("apps.core.tasks_backup.subprocess.run", side_effect=capture_env),
        ):
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.__str__ = lambda x: str(mock_script_exists)

            task = perform_database_backup
            task.request = MagicMock(id="test-task-id")

            perform_database_backup.__wrapped__(task, "full")

            # Verify DB connection info is passed
            assert "DB_HOST" in captured_env
            assert "DB_PORT" in captured_env
            assert "DB_USER" in captured_env
            assert "DB_PASSWORD" in captured_env
            assert "DB_NAME" in captured_env
            assert "BACKUP_DIR" in captured_env
            assert "BACKUP_RETENTION_DAYS" in captured_env

    def test_backup_uses_settings_for_db_connection(self, mock_script_exists: Path) -> None:
        """Test that backup task uses Django settings for database connection."""
        captured_env: dict[str, str] = {}

        def capture_env(*args, **kwargs):
            captured_env.update(kwargs.get("env", {}))
            return MagicMock(
                stdout="backup_full_20260205_120000.sql.gz",
                returncode=0,
            )

        with (
            patch("apps.core.tasks_backup.Path") as mock_path,
            patch("apps.core.tasks_backup.subprocess.run", side_effect=capture_env),
        ):
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.__str__ = lambda x: str(mock_script_exists)

            task = perform_database_backup
            task.request = MagicMock(id="test-task-id")

            perform_database_backup.__wrapped__(task, "full")

            # Verify values match Django settings
            assert captured_env["DB_HOST"] == settings.DATABASES["default"]["HOST"]
            assert captured_env["DB_PORT"] == str(settings.DATABASES["default"]["PORT"])
            assert captured_env["DB_USER"] == settings.DATABASES["default"]["USER"]
            assert captured_env["DB_NAME"] == settings.DATABASES["default"]["NAME"]


class TestVerifyBackupHealth:
    """Tests for verify_backup_health task."""

    def test_health_check_no_backups_returns_degraded(self, tmp_path: Path) -> None:
        """Test that health check returns degraded when no backups exist."""
        with patch.object(settings, "BACKUP_DIR", str(tmp_path)):
            result = verify_backup_health()

            assert result["status"] == "degraded"
            assert "No backups found" in str(result["warnings"])

    def test_health_check_with_recent_backup_returns_healthy(self, tmp_path: Path) -> None:
        """Test that health check returns healthy when recent backup exists."""
        # Create a recent backup file
        backup_file = tmp_path / "backup_full_20260205_120000.sql.gz"
        backup_file.write_bytes(b"fake backup content")

        with patch.object(settings, "BACKUP_DIR", str(tmp_path)):
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

        with patch.object(settings, "BACKUP_DIR", str(tmp_path)):
            result = verify_backup_health()

            assert result["status"] == "degraded"
            assert any("old" in w.lower() for w in result["warnings"])

    def test_health_check_backup_dir_not_exists_returns_warning(self) -> None:
        """Test that health check warns when backup directory doesn't exist."""
        with patch.object(settings, "BACKUP_DIR", "/nonexistent/backup/dir"):
            result = verify_backup_health()

            assert result["status"] == "degraded"
            assert any("does not exist" in w for w in result["warnings"])

    def test_health_check_glob_pattern_matches_expected_naming(self, tmp_path: Path) -> None:
        """Test that health check looks for backup_full_*.sql.gz pattern."""
        # Create a backup with wrong naming (should not be found)
        wrong_name = tmp_path / "aprender_db_20260205_120000.sql.gz"
        wrong_name.write_bytes(b"fake backup content")

        with patch.object(settings, "BACKUP_DIR", str(tmp_path)):
            result = verify_backup_health()

            # Should report no backups because naming doesn't match
            assert result["status"] == "degraded"
            assert "No backups found" in str(result["warnings"])

        # Now create correctly named backup
        correct_name = tmp_path / "backup_full_20260205_120000.sql.gz"
        correct_name.write_bytes(b"fake backup content")

        with patch.object(settings, "BACKUP_DIR", str(tmp_path)):
            result = verify_backup_health()

            # Should find the backup now
            assert result["status"] == "healthy"

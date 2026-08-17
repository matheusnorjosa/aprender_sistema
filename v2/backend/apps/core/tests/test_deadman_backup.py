"""Dead-man switch do backup: alerta quando o backup mais recente fica velho demais.

Motivacao (2026-08): o backup diario morreu em silencio por ~10 dias (08-03 -> 08-17)
e so foi descoberto quando o gate de backup fresco do deploy travou. O health check
`verify_backup_health` existe, mas so roda aos domingos — janela larga demais. Esta
task roda DIARIAMENTE e grita (ERROR + Sentry) assim que o frescor passa do limite.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportIndexIssue=false, reportOperatorIssue=false, reportFunctionMemberAccess=false

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from django.test import override_settings

from apps.core.tasks_backup import check_backup_freshness


def _write_backup(tmp_path: Path, name: str, *, age_hours: float) -> Path:
    """Cria um artefato de backup com mtime `age_hours` no passado."""
    f = tmp_path / name
    f.write_bytes(b"age-encryption.org/v1\nfake payload")
    ts = os.path.getmtime(f) - age_hours * 3600
    os.utime(f, (ts, ts))
    return f


class TestCheckBackupFreshness:
    """Contrato do dead-man: fresh=silencio, stale/missing=ERROR."""

    def test_fresh_backup_returns_fresh_and_does_not_alert(self, tmp_path: Path) -> None:
        # backup de 4h atras, limite 24h → saudavel, sem alarme
        _write_backup(tmp_path, "backup_full_20260817_020000.sql.gz.age", age_hours=4)
        with (
            override_settings(BACKUP_DIR=str(tmp_path), SENTRY_DSN="", BACKUP_DEADMAN_MAX_AGE_HOURS=24),
            patch("apps.core.tasks_backup.logger") as mock_logger,
        ):
            result = check_backup_freshness()

        assert result["status"] == "fresh"
        assert result["latest_backup"] == "backup_full_20260817_020000.sql.gz.age"
        assert not mock_logger.error.called, "backup fresco NAO deve disparar alarme"

    def test_stale_backup_alerts_in_error_and_returns_stale(self, tmp_path: Path) -> None:
        # o backup mais novo tem 30h → passou do limite de 24h → dead-man dispara
        _write_backup(tmp_path, "backup_full_20260810_020000.sql.gz.age", age_hours=30)
        with (
            override_settings(BACKUP_DIR=str(tmp_path), SENTRY_DSN="", BACKUP_DEADMAN_MAX_AGE_HOURS=24),
            patch("apps.core.tasks_backup.logger") as mock_logger,
        ):
            result = check_backup_freshness()

        assert result["status"] == "stale"
        assert mock_logger.error.called, "backup velho DEVE sair em logger.error (alarme em prod)"
        error_text = " ".join(str(c) for c in mock_logger.error.call_args_list)
        assert "DEAD-MAN" in error_text

    def test_no_backup_alerts_and_returns_missing(self, tmp_path: Path) -> None:
        # diretorio vazio → nenhum backup → dead-man dispara com status 'missing'
        with (
            override_settings(BACKUP_DIR=str(tmp_path), SENTRY_DSN="", BACKUP_DEADMAN_MAX_AGE_HOURS=24),
            patch("apps.core.tasks_backup.logger") as mock_logger,
        ):
            result = check_backup_freshness()

        assert result["status"] == "missing"
        assert result["latest_backup"] is None
        assert mock_logger.error.called

    def test_encontra_backup_cifrado_age(self, tmp_path: Path) -> None:
        """Producao grava `.sql.gz.age` — o dead-man DEVE enxerga-lo (nao so `.sql.gz`)."""
        _write_backup(tmp_path, "backup_full_20260817_020000.sql.gz.age", age_hours=1)
        with (
            override_settings(BACKUP_DIR=str(tmp_path), SENTRY_DSN="", BACKUP_DEADMAN_MAX_AGE_HOURS=24),
            patch("apps.core.tasks_backup.logger") as mock_logger,
        ):
            result = check_backup_freshness()

        assert result["status"] == "fresh"
        assert not mock_logger.error.called

    def test_respects_custom_threshold(self, tmp_path: Path) -> None:
        # 2h de idade com limite de 1h → stale
        _write_backup(tmp_path, "backup_full_20260817_000000.sql.gz.age", age_hours=2)
        with (
            override_settings(BACKUP_DIR=str(tmp_path), SENTRY_DSN="", BACKUP_DEADMAN_MAX_AGE_HOURS=1),
            patch("apps.core.tasks_backup.logger") as mock_logger,
        ):
            result = check_backup_freshness()

        assert result["status"] == "stale"
        assert mock_logger.error.called

    def test_task_is_registered_with_expected_name(self) -> None:
        assert check_backup_freshness.name == "backup.check_backup_freshness"

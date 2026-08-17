"""
Celery tasks for automated database backups.

Implements MP5: Automated Backup System with:
- Scheduled full backups (daily at 2am)
- Retention policies (7 days default)
- S3/MinIO upload support
- Sentry integration for failure alerts

Refs: Issue #169
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportUnknownArgumentType=false

from __future__ import annotations

import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from django.conf import settings

from celery import shared_task

if TYPE_CHECKING:
    from typing import Literal

logger = logging.getLogger(__name__)


@shared_task(
    name="backup.perform_database_backup",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
)
def perform_database_backup(
    self,
    backup_type: Literal["full", "incremental"] = "full",
) -> dict[str, str | int]:
    """
    Execute database backup using backup_db.sh script.

    Args:
        backup_type: Type of backup ('full' or 'incremental')

    Returns:
        dict with backup status, file path, and metrics

    Raises:
        Exception: If backup fails after retries
    """
    start_time = datetime.now()
    script_path = Path("/app/infra/scripts/backup_db.sh")

    logger.info(f"Starting {backup_type} database backup (task_id={self.request.id})")

    # Validate script exists
    if not script_path.exists():
        error_msg = f"Backup script not found: {script_path}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    # Prepare environment variables
    env = os.environ.copy()
    env.update(
        {
            "DB_HOST": settings.DATABASES["default"]["HOST"],
            "DB_PORT": str(settings.DATABASES["default"]["PORT"]),
            "DB_USER": settings.DATABASES["default"]["USER"],
            "DB_PASSWORD": settings.DATABASES["default"]["PASSWORD"],
            "DB_NAME": settings.DATABASES["default"]["NAME"],
            "BACKUP_DIR": getattr(settings, "BACKUP_DIR", "/backups"),
            "BACKUP_RETENTION_DAYS": str(getattr(settings, "BACKUP_RETENTION_DAYS", 7)),
            "S3_BUCKET": getattr(settings, "BACKUP_S3_BUCKET", ""),
            "SENTRY_DSN": getattr(settings, "SENTRY_DSN", ""),
        }
    )

    try:
        # Execute backup script
        result = subprocess.run(
            [str(script_path), backup_type],
            env=env,
            capture_output=True,
            text=True,
            timeout=3600,  # 1 hour timeout
            check=True,
        )

        duration = (datetime.now() - start_time).total_seconds()

        # Parse backup file path from output
        backup_file = None
        for line in result.stdout.splitlines():
            if "backup_full_" in line and ".sql.gz" in line:
                backup_file = line.split()[-1].strip("()")
                break

        logger.info(
            f"Backup completed successfully in {duration:.2f}s",
            extra={
                "backup_type": backup_type,
                "backup_file": backup_file,
                "duration_seconds": duration,
            },
        )

        return {
            "status": "success",
            "backup_type": backup_type,
            "backup_file": backup_file or "unknown",
            "duration_seconds": int(duration),
            "stdout": result.stdout[-500:],  # Last 500 chars
        }

    except subprocess.TimeoutExpired:
        error_msg = f"{backup_type} backup timed out after 1 hour"
        logger.error(error_msg)

        # Retry with exponential backoff
        raise self.retry(exc=Exception(error_msg), countdown=300)

    except subprocess.CalledProcessError as exc:
        duration = (datetime.now() - start_time).total_seconds()
        error_msg = f"{backup_type} backup failed (exit code {exc.returncode})"

        logger.error(
            error_msg,
            extra={
                "backup_type": backup_type,
                "duration_seconds": duration,
                "stdout": exc.stdout[-500:] if exc.stdout else "",
                "stderr": exc.stderr[-500:] if exc.stderr else "",
                "exit_code": exc.returncode,
            },
        )

        # Send to Sentry if configured
        if hasattr(settings, "SENTRY_DSN") and settings.SENTRY_DSN:
            try:
                import sentry_sdk

                sentry_sdk.capture_exception(exc)
            except ImportError:
                pass

        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=self.default_retry_delay * (2**self.request.retries))

    except Exception as exc:
        logger.exception(f"Unexpected error during {backup_type} backup")

        # Send to Sentry
        if hasattr(settings, "SENTRY_DSN") and settings.SENTRY_DSN:
            try:
                import sentry_sdk

                sentry_sdk.capture_exception(exc)
            except ImportError:
                pass

        raise


def _latest_backup_age_hours(backup_dir: Path) -> tuple[Path | None, float]:
    """Retorna (backup mais recente, idade em horas) ou (None, 0.0) se nao houver.

    Cobre os DOIS sufixos: `.sql.gz` (sem cifra) e `.sql.gz.age` (SEC-017 — o que
    producao realmente grava). `glob("backup_full_*.sql.gz")` NAO casa
    `backup_full_*.sql.gz.age` (fnmatch exige que o padrao termine o nome): sem os
    dois globs, um diretorio cheio de dumps cifrados validos seria lido como vazio e
    o alarme gritaria "sem backup" toda vez (#1455). Diretorio inexistente → `glob`
    devolve vazio → (None, 0.0). SSOT do frescor: usado pelo health check semanal e
    pelo dead-man diario.
    """
    backups = [
        *backup_dir.glob("backup_full_*.sql.gz"),
        *backup_dir.glob("backup_full_*.sql.gz.age"),
    ]
    if not backups:
        return None, 0.0
    latest = max(backups, key=lambda p: p.stat().st_mtime)
    age_hours = (datetime.now().timestamp() - latest.stat().st_mtime) / 3600
    return latest, age_hours


def _alert_backup_deadman(message: str) -> None:
    """Dispara o alarme do dead-man: ERROR no log (chega a alguem mesmo sem Sentry,
    ja que SENTRY_DSN e vazio em prod) + evento de erro no Sentry quando configurado."""
    logger.error(message)
    if getattr(settings, "SENTRY_DSN", ""):
        try:
            import sentry_sdk

            sentry_sdk.capture_message(message, level="error")
        except ImportError:
            pass


@shared_task(name="backup.verify_backup_health")
def verify_backup_health() -> dict[str, str | int | list[str]]:
    """
    Verify backup system health (run weekly).

    Checks:
    - Recent backup exists (within last 25 hours for daily backups)
    - Backup directory is writable
    - S3 connectivity (if configured)

    Returns:
        dict with health status and warnings
    """
    backup_dir = Path(getattr(settings, "BACKUP_DIR", "/backups"))
    warnings = []
    checks_passed = 0
    checks_total = 3

    logger.info("Running backup health verification")

    # Check 1: Backup directory exists and is writable
    if not backup_dir.exists():
        warnings.append(f"Backup directory does not exist: {backup_dir}")
    elif not os.access(backup_dir, os.W_OK):
        warnings.append(f"Backup directory is not writable: {backup_dir}")
    else:
        checks_passed += 1

    # Check 2: Recent backup exists (within last 25 hours). O glob dos dois sufixos
    # (`.sql.gz` + `.sql.gz.age`, SEC-017/#1455) vive em `_latest_backup_age_hours` —
    # mesma fonte de frescor que o dead-man diario (`check_backup_freshness`) usa.
    latest_backup, age_hours = _latest_backup_age_hours(backup_dir)
    if latest_backup is not None:
        if age_hours > 25:
            warnings.append(f"Latest backup is {age_hours:.1f}h old (expected < 25h)")
        else:
            checks_passed += 1
            logger.info(f"Latest backup: {latest_backup.name} ({age_hours:.1f}h old)")
    else:
        warnings.append("No backups found in backup directory")

    # Check 3: S3 connectivity (if configured)
    s3_bucket = getattr(settings, "BACKUP_S3_BUCKET", "")
    if s3_bucket:
        try:
            _result = subprocess.run(  # noqa: F841 - used for side effects only
                ["aws", "s3", "ls", f"s3://{s3_bucket}/backups/"],
                capture_output=True,
                timeout=30,
                check=True,
            )
            checks_passed += 1
            logger.info("S3 connectivity check passed")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            warnings.append("S3 connectivity check failed")
    else:
        # S3 not configured - skip check
        checks_total = 2

    # Send warnings to Sentry if critical
    if len(warnings) > 0 and hasattr(settings, "SENTRY_DSN") and settings.SENTRY_DSN:
        try:
            import sentry_sdk

            sentry_sdk.capture_message(
                f"Backup health check warnings: {'; '.join(warnings)}",
                level="warning",
            )
        except ImportError:
            pass

    health_status = "healthy" if checks_passed == checks_total else "degraded"

    _msg = f"Backup health check completed: {health_status} ({checks_passed}/{checks_total} passed)"
    if health_status == "healthy":
        logger.info(_msg, extra={"warnings": warnings})
    else:
        # #1541: 'degraded' e o sinal de backup morto — a razao de a task existir.
        # SENTRY_DSN esta VAZIO em prod (o capture_message acima e no-op) e o INFO era
        # engolido por alertas baseados em log (level>=WARNING). Logar em ERROR faz o
        # alarme chegar a alguem, independente do Sentry.
        logger.error(_msg, extra={"warnings": warnings})

    return {
        "status": health_status,
        "checks_passed": checks_passed,
        "checks_total": checks_total,
        "warnings": warnings,
    }


@shared_task(name="backup.check_backup_freshness")
def check_backup_freshness() -> dict[str, str | float | None]:
    """Dead-man switch DIARIO: alarme quando o backup mais recente fica velho demais.

    O backup roda diariamente as 2am (`backup.perform_database_backup`). Esta task
    roda de manha e, se o backup mais novo passar de `BACKUP_DEADMAN_MAX_AGE_HOURS`
    (default 24h) — ou se nao houver backup nenhum — dispara alarme via
    `_alert_backup_deadman` (ERROR no log + Sentry quando ha DSN).

    Foi a AUSENCIA deste alarme que deixou o backup diario morrer em silencio por
    ~10 dias (2026-08-03 -> 08-17), so descoberto quando o gate de backup fresco do
    deploy travou. O `verify_backup_health` e mais largo (dir/S3/frescor) mas so
    roda aos domingos; este e o dead-man de cadencia diaria, focado em frescor.

    Limitacao residual (honesta): se o proprio beat/worker estiver morto, esta task
    tambem nao roda — o backstop externo continua sendo o gate `check_backup.sh` do
    `aprender-applier`, que recusa deploy sem backup fresco.

    Returns:
        dict com `status` ('fresh' | 'stale' | 'missing'), nome do backup, idade em
        horas e o limite aplicado.
    """
    backup_dir = Path(getattr(settings, "BACKUP_DIR", "/backups"))
    max_age_hours = float(getattr(settings, "BACKUP_DEADMAN_MAX_AGE_HOURS", 24))

    latest_backup, age_hours = _latest_backup_age_hours(backup_dir)

    if latest_backup is None:
        _alert_backup_deadman(
            f"DEAD-MAN de backup: nenhum backup encontrado em {backup_dir} — o backup diario pode ter parado de rodar"
        )
        return {
            "status": "missing",
            "latest_backup": None,
            "age_hours": None,
            "max_age_hours": max_age_hours,
        }

    if age_hours > max_age_hours:
        _alert_backup_deadman(
            f"DEAD-MAN de backup: o backup mais recente ({latest_backup.name}) tem {age_hours:.1f}h (limite {max_age_hours:.0f}h) — o backup diario pode ter parado"
        )
        return {
            "status": "stale",
            "latest_backup": latest_backup.name,
            "age_hours": round(age_hours, 1),
            "max_age_hours": max_age_hours,
        }

    logger.info(f"Dead-man de backup OK: {latest_backup.name} ({age_hours:.1f}h, limite {max_age_hours:.0f}h)")
    return {
        "status": "fresh",
        "latest_backup": latest_backup.name,
        "age_hours": round(age_hours, 1),
        "max_age_hours": max_age_hours,
    }

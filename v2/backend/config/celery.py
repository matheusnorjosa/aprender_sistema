"""
AS v2 — Celery App Configuration

Configuração da aplicação Celery para tarefas assíncronas:
- Broker: Redis (CELERY_BROKER_URL)
- Backend: Redis (CELERY_RESULT_BACKEND)
- Autodiscovery: apps.core.tasks
- Timezone: America/Fortaleza

Comandos:
- Worker: celery -A config worker -l info
- Beat: celery -A config beat -l info
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportCallIssue=false, reportUntypedFunctionDecorator=false

from __future__ import annotations

import os

from celery import Celery
from celery.schedules import crontab

# Define Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Create Celery app
app = Celery("config")

# Load config from Django settings (namespace CELERY_*)
app.config_from_object("django.conf:settings", namespace="CELERY")

# Merge local schedules with settings.py schedules (no override).
existing_schedule = dict(app.conf.get("CELERY_BEAT_SCHEDULE", {}) or {})
existing_schedule.update(
    {
        # MP5: Daily full backup at 2am (America/Fortaleza)
        "daily-database-backup": {
            "task": "backup.perform_database_backup",
            "schedule": crontab(hour=2, minute=0),
            "args": ("full",),
            "options": {"expires": 3600},
        },
        # MP5: Weekly backup health check (Sundays at 3am)
        "weekly-backup-health-check": {
            "task": "backup.verify_backup_health",
            "schedule": crontab(hour=3, minute=0, day_of_week=0),
            "options": {"expires": 1800},
        },
        # #871: Daily notifications/escalation processing at 08:00 (America/Fortaleza)
        "acoes-notificacoes-diarias": {
            "task": "apps.core.tasks.processar_notificacoes_acoes_diarias",
            "schedule": crontab(hour=8, minute=0),
            "options": {"expires": 3600},
        },
    }
)
app.conf.update(CELERY_BEAT_SCHEDULE=existing_schedule)

# Auto-discover tasks in all installed apps (ex: apps.core.tasks)
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self) -> None:  # type: ignore[no-untyped-def]
    """
    Debug task for testing Celery setup.
    Usage: from config.celery import debug_task; debug_task.delay()
    """
    print(f"Request: {self.request!r}")

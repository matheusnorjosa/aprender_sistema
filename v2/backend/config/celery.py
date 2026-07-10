"""
AS v2 — Celery App Configuration

Configuração da aplicação Celery para tarefas assíncronas:
- Broker: Redis (CELERY_BROKER_URL)
- Backend: django-db (CELERY_RESULT_BACKEND)
- Autodiscovery: apps.core.tasks + apps.core.tasks_backup
- Timezone: America/Fortaleza

Comandos:
- Worker: celery -A config worker -l info
- Beat: celery -A config beat -l info
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportUnknownArgumentType=false, reportArgumentType=false

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

# Auto-discover tasks in all installed apps.
#
# ATENCAO: `autodiscover_tasks()` importa APENAS o modulo `tasks` de cada app
# instalada. As tasks de backup vivem em `apps/core/tasks_backup.py` e por isso
# NUNCA eram registradas no worker: o beat despachava
# `backup.perform_database_backup` todo dia as 02:00 e o worker respondia
# NotRegistered, em silencio, por meses (#1455). Os testes nao pegavam porque
# importam `tasks_backup` diretamente — o registro vazava para o processo de teste.
#
# A segunda chamada cobre qualquer app que tenha um `tasks_backup.py`.
# Sentinela contra regressao: apps/core/tests/test_celery_beat_registration.py
# (roda num interpretador novo; um `import` no pytest mascararia o defeito).
app.autodiscover_tasks()
app.autodiscover_tasks(related_name="tasks_backup")


@app.task(bind=True)
def debug_task(self) -> None:  # type: ignore[no-untyped-def]
    """
    Debug task for testing Celery setup.
    Usage: from config.celery import debug_task; debug_task.delay()
    """
    print(f"Request: {self.request!r}")

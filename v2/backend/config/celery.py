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

from __future__ import annotations

import os

from celery import Celery

# Define Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Create Celery app
app = Celery("config")

# Load config from Django settings (namespace CELERY_*)
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in all installed apps (ex: apps.core.tasks)
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    """
    Debug task for testing Celery setup.
    Usage: from config.celery import debug_task; debug_task.delay()
    """
    print(f"Request: {self.request!r}")

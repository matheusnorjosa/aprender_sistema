"""
Celery config para AS v2
VM01: 4 vCPU, 16GB RAM
Referência: PLAN_infrastructure_scaling.md

Este arquivo deve ser importado no celery.py do Django.
"""

import os

# Broker (Redis VM03)
broker_url = os.getenv(
    "CELERY_BROKER_URL",
    "redis://:PASSWORD@10.0.0.3:6379/0"
)
result_backend = os.getenv(
    "CELERY_RESULT_BACKEND",
    "redis://:PASSWORD@10.0.0.3:6379/1"
)

# Task settings
task_serializer = "json"
accept_content = ["json"]
result_serializer = "json"
timezone = "America/Fortaleza"
enable_utc = True

# Worker settings
worker_concurrency = 4
worker_prefetch_multiplier = 2
worker_max_tasks_per_child = 1000

# Task execution
task_acks_late = True
task_reject_on_worker_lost = True
task_time_limit = 300  # 5 minutos hard limit
task_soft_time_limit = 240  # 4 minutos soft limit

# Queues
task_default_queue = "default"
task_queues = {
    "high": {"exchange": "high", "routing_key": "high"},
    "default": {"exchange": "default", "routing_key": "default"},
    "low": {"exchange": "low", "routing_key": "low"},
}

# Routes
task_routes = {
    "apps.core.tasks.sync_solicitacao_gcal": {"queue": "high"},
    "apps.core.tasks.send_notification_email": {"queue": "default"},
    "apps.dat_ingest.tasks.*": {"queue": "low"},
}

# Beat schedule
beat_schedule = {
    "cleanup-expired-sessions": {
        "task": "apps.core.tasks.cleanup_expired_sessions",
        "schedule": 3600.0,  # A cada hora
    },
    "sync-pending-gcal": {
        "task": "apps.core.tasks.sync_pending_gcal_events",
        "schedule": 300.0,  # A cada 5 minutos
    },
}

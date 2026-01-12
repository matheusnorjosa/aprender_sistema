# Celery config para AS v2
# VM01: 4 vCPU, 16GB RAM
# Ref: PLAN_infrastructure_scaling.md
#
# Note: This file documents the Celery configuration.
# Actual config is in Django settings (config/settings.py)
# and the celery app (config/celery.py).

# ==============================================================================
# BROKER (Redis on VM03)
# ==============================================================================
# broker_url = "redis://:PASSWORD@10.0.0.3:6379/0"
# result_backend = "redis://:PASSWORD@10.0.0.3:6379/1"

# ==============================================================================
# TASK SETTINGS
# ==============================================================================
# task_serializer = "json"
# accept_content = ["json"]
# result_serializer = "json"
# timezone = "America/Fortaleza"
# enable_utc = True

# ==============================================================================
# WORKER SETTINGS
# ==============================================================================
# worker_concurrency = 4  # Match vCPU count
# worker_prefetch_multiplier = 2  # Prefetch 2 tasks per worker
# worker_max_tasks_per_child = 1000  # Recycle worker after 1000 tasks

# ==============================================================================
# TASK EXECUTION
# ==============================================================================
# task_acks_late = True  # Ack after task completion (not before)
# task_reject_on_worker_lost = True  # Requeue if worker dies
# task_time_limit = 300  # 5 minutes hard limit
# task_soft_time_limit = 240  # 4 minutes soft limit (raises exception)

# ==============================================================================
# QUEUES
# ==============================================================================
# task_default_queue = "default"
# task_queues = {
#     "high": {"exchange": "high", "routing_key": "high"},
#     "default": {"exchange": "default", "routing_key": "default"},
#     "low": {"exchange": "low", "routing_key": "low"},
# }

# ==============================================================================
# ROUTES
# ==============================================================================
# task_routes = {
#     "apps.core.tasks.sync_solicitacao_gcal": {"queue": "high"},
#     "apps.core.tasks.send_notification_email": {"queue": "default"},
#     "apps.dat_ingest.tasks.*": {"queue": "low"},
# }

# ==============================================================================
# BEAT SCHEDULE
# ==============================================================================
# beat_schedule = {
#     "cleanup-expired-sessions": {
#         "task": "apps.core.tasks.cleanup_expired_sessions",
#         "schedule": 3600.0,  # Every hour
#     },
#     "sync-pending-gcal": {
#         "task": "apps.core.tasks.sync_pending_gcal_events",
#         "schedule": 300.0,  # Every 5 minutes
#     },
# }

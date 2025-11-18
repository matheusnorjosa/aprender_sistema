"""
Gunicorn production configuration for AS v2.

Performance tuning for I/O-bound workload (Django + PostgreSQL).

References:
- https://docs.gunicorn.org/en/stable/settings.html
- PLANO_MELHORIAS_DETALHADO.md (CP1)
"""
import multiprocessing
import os

# ================================================================
# WORKERS & THREADS
# ================================================================
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count()))
threads = int(os.getenv("GUNICORN_THREADS", 2))
worker_class = "gthread"  # Gunicorn with threads (I/O-bound workload)

# ================================================================
# TIMEOUTS
# ================================================================
timeout = int(os.getenv("GUNICORN_TIMEOUT", 120))  # Suporta ETL e grade mensal
graceful_timeout = 30
keepalive = 5

# ================================================================
# RESOURCE MANAGEMENT
# ================================================================
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", 1000))
max_requests_jitter = 50  # Previne restart sincronizado de workers
worker_tmp_dir = "/dev/shm" if os.path.exists("/dev/shm") else None

# ================================================================
# LOGGING (MP2: Structured Logging)
# ================================================================
# Logs vão para stdout/stderr, Django LOGGING (settings.py) define formato JSON
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# ================================================================
# BIND
# ================================================================
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")

# ================================================================
# PRELOAD (production only)
# ================================================================
preload_app = os.getenv("ENVIRONMENT", "development") == "production"

# ================================================================
# HOOKS
# ================================================================
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info(f"Starting Gunicorn with {workers} workers, {threads} threads/worker")


def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Gunicorn ready. Spawning workers")


def worker_int(worker):
    """Called when a worker receives the SIGINT or SIGQUIT signal."""
    worker.log.info(f"Worker {worker.pid} received SIGINT/SIGQUIT")


def worker_abort(worker):
    """Called when a worker received the SIGABRT signal."""
    worker.log.warning(f"Worker {worker.pid} received SIGABRT (timeout exceeded)")

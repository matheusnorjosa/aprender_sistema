# Gunicorn config para AS v2
# VM01: 4 vCPU, 16GB RAM
# Ref: PLAN_infrastructure_scaling.md
# Copy to /etc/aprender/gunicorn.conf.py

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Workers
# Formula: 2 x vCPU for I/O bound applications
workers = 4
worker_class = "gthread"
threads = 2  # 2 threads per worker = 8 total threads
worker_connections = 1000
max_requests = 1000  # Recycle workers after N requests (memory leak protection)
max_requests_jitter = 100  # Randomize to prevent thundering herd

# Timeouts
timeout = 30  # Kill worker after 30s of silence
graceful_timeout = 30  # Wait 30s for graceful shutdown
keepalive = 5  # Keep connection alive for 5s

# Process naming
proc_name = "aprender-gunicorn"

# Logging
accesslog = "/var/log/aprender/gunicorn-access.log"
errorlog = "/var/log/aprender/gunicorn-error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Server mechanics
daemon = False  # Systemd handles daemonization
pidfile = "/run/aprender/gunicorn.pid"
user = "aprender"
group = "aprender"
tmp_upload_dir = None

# SSL (handled by Nginx, not Gunicorn)
# keyfile = None
# certfile = None

# Hooks (optional - for metrics/monitoring)
def on_starting(server):
    """Called before the master process is initialized."""
    pass

def on_reload(server):
    """Called before the master process is reloaded."""
    pass

def worker_int(worker):
    """Called when a worker receives SIGINT."""
    pass

def worker_abort(worker):
    """Called when a worker receives SIGABRT."""
    pass

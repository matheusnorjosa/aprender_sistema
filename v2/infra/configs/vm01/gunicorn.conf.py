"""
Gunicorn config para AS v2
VM01: 4 vCPU, 16GB RAM
Referência: PLAN_infrastructure_scaling.md
"""

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Workers
workers = 4  # 2 × vCPU (I/O bound)
worker_class = "gthread"
threads = 2  # 2 threads por worker
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100

# Timeouts
timeout = 30
graceful_timeout = 30
keepalive = 5

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
daemon = False
pidfile = "/run/aprender/gunicorn.pid"
user = "aprender"
group = "aprender"
tmp_upload_dir = None

# SSL (handled by Nginx)
# keyfile = None
# certfile = None

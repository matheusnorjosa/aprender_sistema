# Plano: Infraestrutura e Escalabilidade

**Data**: 2026-01-09
**Status**: ✅ CONCLUÍDO (PR #391)
**Meta**: Configurar infraestrutura de produção otimizada

---

## 1. Recursos Disponíveis

| Hostname | vCPU | Memória | Sistema | Disco |
|----------|------|---------|---------|-------|
| VM01_App + Workers | 4 | 16GB | Ubuntu Server | 60GB |
| VM02_Banco | 4 | 16GB | Ubuntu Server | 300GB |
| VM03_Redis | 2 | 4GB | Ubuntu Server | 20GB |

---

## 2. Arquitetura Target

```
                            ┌─────────────────┐
                            │    Internet     │
                            └────────┬────────┘
                                     │
                    ┌────────────────▼────────────────┐
                    │         VM01_App (4vCPU/16GB)   │
                    │  ┌──────────────────────────┐   │
                    │  │   Nginx (Reverse Proxy)  │   │
                    │  │   + SSL Termination      │   │
                    │  └────────────┬─────────────┘   │
                    │        ┌──────┴──────┐         │
                    │        │             │         │
                    │  ┌─────▼─────┐ ┌─────▼─────┐   │
                    │  │ Gunicorn  │ │ Gunicorn  │   │
                    │  │ (4 workers)│ │ (threads) │   │
                    │  └───────────┘ └───────────┘   │
                    │               │                │
                    │  ┌────────────▼────────────┐   │
                    │  │   Celery Workers (4)    │   │
                    │  │   + Celery Beat         │   │
                    │  └─────────────────────────┘   │
                    └───────────────┬────────────────┘
                                    │
                 ┌──────────────────┼──────────────────┐
                 │                  │                  │
    ┌────────────▼────────────┐    │    ┌────────────▼────────────┐
    │  VM02_Banco (4vCPU/16GB)│    │    │  VM03_Redis (2vCPU/4GB) │
    │  ┌──────────────────┐   │    │    │  ┌──────────────────┐   │
    │  │    PostgreSQL    │◄──┼────┼────┼──│      Redis       │   │
    │  │  - 300GB Storage │   │         │  │  - Cache         │   │
    │  └──────────────────┘   │         │  │  - Sessions      │   │
    └─────────────────────────┘         │  │  - Celery Broker │   │
                                        │  └──────────────────┘   │
                                        └─────────────────────────┘
```

---

## 3. Distribuição de Recursos

### VM01_App (16GB RAM)

| Componente | RAM | Descrição |
|------------|-----|-----------|
| Nginx | 512MB | Reverse proxy + static files |
| Gunicorn (4 workers) | 4GB | 4 workers × 1GB cada |
| Celery (4 workers) | 4GB | 4 workers × 1GB cada |
| Celery Beat | 256MB | Scheduler |
| Sistema/Buffer | ~7GB | OS + buffers |

### VM02_Banco (16GB RAM)

| Componente | RAM | Descrição |
|------------|-----|-----------|
| PostgreSQL | 12GB | shared_buffers + effective_cache |
| Sistema/Buffer | ~4GB | OS + file system cache |

### VM03_Redis (4GB RAM)

| Componente | RAM | Descrição |
|------------|-----|-----------|
| Redis | 3GB | maxmemory |
| Sistema/Buffer | ~1GB | OS + buffers |

---

## 4. Configurações Detalhadas

### 4.1 VM01 - Nginx

**Arquivo**: `/etc/nginx/nginx.conf`

```nginx
user www-data;
worker_processes 2;
pid /run/nginx.pid;

events {
    worker_connections 2048;
    use epoll;
    multi_accept on;
}

http {
    # Básico
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Gzip
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml application/json application/javascript
               application/xml application/rss+xml application/atom+xml image/svg+xml;

    # Logs
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;

    # Upstream Django
    upstream django {
        least_conn;
        server 127.0.0.1:8000 weight=1;
        keepalive 32;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_conn_zone $binary_remote_addr zone=conn:10m;

    server {
        listen 80;
        server_name aprender.com.br;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name aprender.com.br;

        # SSL
        ssl_certificate /etc/ssl/certs/aprender.crt;
        ssl_certificate_key /etc/ssl/private/aprender.key;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
        ssl_prefer_server_ciphers off;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 1d;

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

        # Static files
        location /static/ {
            alias /var/www/aprender/static/;
            expires 1y;
            add_header Cache-Control "public, immutable";
            access_log off;
        }

        # Media files
        location /media/ {
            alias /var/www/aprender/media/;
            expires 30d;
            add_header Cache-Control "public";
        }

        # Health check (sem rate limit)
        location /healthz/ {
            proxy_pass http://django;
            proxy_set_header Host $host;
            access_log off;
        }

        # API
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            limit_conn conn 10;

            proxy_pass http://django;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            proxy_connect_timeout 30s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;

            proxy_buffering on;
            proxy_buffer_size 4k;
            proxy_buffers 8 4k;
        }

        # Admin
        location /admin/ {
            proxy_pass http://django;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Frontend (React)
        location / {
            root /var/www/aprender/frontend/;
            try_files $uri $uri/ /index.html;
            expires 1h;
        }
    }
}
```

### 4.2 VM01 - Gunicorn

**Arquivo**: `/etc/aprender/gunicorn.conf.py`

```python
# Gunicorn config para AS v2
# VM01: 4 vCPU, 16GB RAM

import multiprocessing

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
```

**Systemd service**: `/etc/systemd/system/aprender-gunicorn.service`

```ini
[Unit]
Description=Aprender Sistema Gunicorn
After=network.target

[Service]
Type=notify
User=aprender
Group=aprender
RuntimeDirectory=aprender
WorkingDirectory=/var/www/aprender/backend
Environment="PATH=/var/www/aprender/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=config.settings"
ExecStart=/var/www/aprender/venv/bin/gunicorn config.wsgi:application -c /etc/aprender/gunicorn.conf.py
ExecReload=/bin/kill -s HUP $MAINPID
Restart=on-failure
RestartSec=5
KillMode=mixed
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

### 4.3 VM01 - Celery

**Arquivo**: `/etc/aprender/celery.conf`

```python
# Celery config para AS v2
# VM01: 4 vCPU, 16GB RAM

# Broker (Redis VM03)
broker_url = "redis://:PASSWORD@10.0.0.3:6379/0"
result_backend = "redis://:PASSWORD@10.0.0.3:6379/1"

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
```

**Systemd service - Worker**: `/etc/systemd/system/aprender-celery.service`

```ini
[Unit]
Description=Aprender Sistema Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=aprender
Group=aprender
WorkingDirectory=/var/www/aprender/backend
Environment="PATH=/var/www/aprender/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=config.settings"
ExecStart=/var/www/aprender/venv/bin/celery -A config multi start worker1 worker2 worker3 worker4 \
    --pidfile=/run/aprender/celery-%n.pid \
    --logfile=/var/log/aprender/celery-%n.log \
    --loglevel=INFO \
    -Q:worker1 high,default \
    -Q:worker2 high,default \
    -Q:worker3 default,low \
    -Q:worker4 low
ExecStop=/var/www/aprender/venv/bin/celery -A config multi stopwait worker1 worker2 worker3 worker4 \
    --pidfile=/run/aprender/celery-%n.pid
ExecReload=/var/www/aprender/venv/bin/celery -A config multi restart worker1 worker2 worker3 worker4 \
    --pidfile=/run/aprender/celery-%n.pid
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Systemd service - Beat**: `/etc/systemd/system/aprender-celerybeat.service`

```ini
[Unit]
Description=Aprender Sistema Celery Beat
After=network.target redis.service

[Service]
Type=simple
User=aprender
Group=aprender
WorkingDirectory=/var/www/aprender/backend
Environment="PATH=/var/www/aprender/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=config.settings"
ExecStart=/var/www/aprender/venv/bin/celery -A config beat \
    --pidfile=/run/aprender/celerybeat.pid \
    --logfile=/var/log/aprender/celerybeat.log \
    --loglevel=INFO \
    --scheduler=django_celery_beat.schedulers:DatabaseScheduler
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 4.4 VM02 - PostgreSQL

**Arquivo**: `/etc/postgresql/15/main/postgresql.conf`

```ini
# PostgreSQL config para AS v2
# VM02: 4 vCPU, 16GB RAM, 300GB SSD

#------------------------------------------------------------------------------
# CONNECTIONS
#------------------------------------------------------------------------------
listen_addresses = '10.0.0.2'
port = 5432
max_connections = 200
superuser_reserved_connections = 3

#------------------------------------------------------------------------------
# MEMORY
#------------------------------------------------------------------------------
# 25% da RAM para shared buffers
shared_buffers = 4GB

# 75% da RAM para cache estimado
effective_cache_size = 12GB

# Memória para operações de sort/hash
work_mem = 64MB

# Memória para VACUUM, CREATE INDEX
maintenance_work_mem = 1GB

# WAL buffers
wal_buffers = 64MB

#------------------------------------------------------------------------------
# QUERY TUNING
#------------------------------------------------------------------------------
# Para SSD
random_page_cost = 1.1
effective_io_concurrency = 200

# Parallel queries
max_parallel_workers_per_gather = 2
max_parallel_workers = 4
max_parallel_maintenance_workers = 2

# Estatísticas
default_statistics_target = 100

#------------------------------------------------------------------------------
# WAL / CHECKPOINTS
#------------------------------------------------------------------------------
wal_level = replica
max_wal_size = 4GB
min_wal_size = 1GB
checkpoint_completion_target = 0.9
checkpoint_timeout = 10min

# Archive (para backup incremental)
archive_mode = on
archive_command = 'gzip < %p > /var/lib/postgresql/wal_archive/%f.gz'
archive_timeout = 300

#------------------------------------------------------------------------------
# REPLICATION (preparado para futuro)
#------------------------------------------------------------------------------
max_wal_senders = 3
wal_keep_size = 1GB

#------------------------------------------------------------------------------
# LOGGING
#------------------------------------------------------------------------------
log_destination = 'stderr'
logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d.log'
log_rotation_age = 1d
log_rotation_size = 100MB

log_min_duration_statement = 500
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on
log_temp_files = 0

log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '

#------------------------------------------------------------------------------
# AUTOVACUUM
#------------------------------------------------------------------------------
autovacuum = on
autovacuum_max_workers = 3
autovacuum_naptime = 30s
autovacuum_vacuum_threshold = 50
autovacuum_vacuum_scale_factor = 0.1
autovacuum_analyze_threshold = 50
autovacuum_analyze_scale_factor = 0.05
autovacuum_vacuum_cost_delay = 2ms
autovacuum_vacuum_cost_limit = 1000

#------------------------------------------------------------------------------
# LOCALE
#------------------------------------------------------------------------------
lc_messages = 'en_US.UTF-8'
lc_monetary = 'pt_BR.UTF-8'
lc_numeric = 'pt_BR.UTF-8'
lc_time = 'pt_BR.UTF-8'
default_text_search_config = 'pg_catalog.portuguese'
```

**Arquivo**: `/etc/postgresql/15/main/pg_hba.conf`

```
# TYPE  DATABASE        USER            ADDRESS                 METHOD

# Local connections
local   all             postgres                                peer
local   all             all                                     peer

# VM01_App
host    aprender_db     aprender_user   10.0.0.1/32            scram-sha-256

# Replication (futuro)
host    replication     replicator      10.0.0.0/24            scram-sha-256

# Reject all others
host    all             all             0.0.0.0/0              reject
```

### 4.5 VM03 - Redis

**Arquivo**: `/etc/redis/redis.conf`

```ini
# Redis config para AS v2
# VM03: 2 vCPU, 4GB RAM

#------------------------------------------------------------------------------
# NETWORK
#------------------------------------------------------------------------------
bind 10.0.0.3
port 6379
protected-mode yes
tcp-backlog 511
timeout 300
tcp-keepalive 300

#------------------------------------------------------------------------------
# SECURITY
#------------------------------------------------------------------------------
requirepass SENHA_FORTE_AQUI

# Desabilitar comandos perigosos
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command DEBUG ""
rename-command CONFIG "CONFIG_b4ck3nd_s3cr3t"

#------------------------------------------------------------------------------
# MEMORY
#------------------------------------------------------------------------------
maxmemory 3gb
maxmemory-policy allkeys-lru
maxmemory-samples 5

#------------------------------------------------------------------------------
# PERSISTENCE - RDB
#------------------------------------------------------------------------------
save 900 1
save 300 10
save 60 10000

stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir /var/lib/redis

#------------------------------------------------------------------------------
# PERSISTENCE - AOF
#------------------------------------------------------------------------------
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb
aof-load-truncated yes
aof-use-rdb-preamble yes

#------------------------------------------------------------------------------
# CLIENTS
#------------------------------------------------------------------------------
maxclients 1000

#------------------------------------------------------------------------------
# LOGGING
#------------------------------------------------------------------------------
loglevel notice
logfile /var/log/redis/redis-server.log

#------------------------------------------------------------------------------
# SLOW LOG
#------------------------------------------------------------------------------
slowlog-log-slower-than 10000
slowlog-max-len 128
```

---

## 5. Django Settings para Produção

**Arquivo**: `config/settings.py` (adições para produção)

```python
# =============================================================================
# DATABASE - VM02
# =============================================================================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": os.getenv("DB_HOST", "10.0.0.2"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "NAME": os.getenv("DB_NAME", "aprender_db"),
        "USER": os.getenv("DB_USER", "aprender_user"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "CONN_MAX_AGE": 60,  # Reutiliza conexões por 60s
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "connect_timeout": 10,
            "options": "-c statement_timeout=30000",  # 30s query timeout
        },
    }
}

# =============================================================================
# CACHE - VM03
# =============================================================================
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"redis://:{os.getenv('REDIS_PASSWORD')}@10.0.0.3:6379/0",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "CONNECTION_POOL_KWARGS": {"max_connections": 50},
        },
        "KEY_PREFIX": "as2",
        "TIMEOUT": 300,  # 5 minutos default
    }
}

# Session via Redis
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_AGE = 86400  # 24 horas

# =============================================================================
# CELERY - VM03
# =============================================================================
CELERY_BROKER_URL = f"redis://:{os.getenv('REDIS_PASSWORD')}@10.0.0.3:6379/1"
CELERY_RESULT_BACKEND = f"redis://:{os.getenv('REDIS_PASSWORD')}@10.0.0.3:6379/2"

# =============================================================================
# STATIC/MEDIA
# =============================================================================
STATIC_ROOT = "/var/www/aprender/static/"
MEDIA_ROOT = "/var/www/aprender/media/"

# =============================================================================
# SECURITY
# =============================================================================
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
```

---

## 6. Scripts de Deploy

### 6.1 Script de Setup Inicial

**Arquivo**: `v2/infra/scripts/setup_vm01.sh`

```bash
#!/bin/bash
# Setup VM01_App
set -e

echo "=== Setup VM01_App ==="

# Criar usuário
sudo useradd -r -s /bin/false aprender

# Instalar dependências
sudo apt update
sudo apt install -y python3.12 python3.12-venv nginx

# Criar diretórios
sudo mkdir -p /var/www/aprender/{backend,frontend,static,media}
sudo mkdir -p /var/log/aprender
sudo mkdir -p /run/aprender
sudo mkdir -p /etc/aprender

# Setup virtualenv
sudo python3.12 -m venv /var/www/aprender/venv
sudo /var/www/aprender/venv/bin/pip install --upgrade pip wheel

# Permissões
sudo chown -R aprender:aprender /var/www/aprender
sudo chown -R aprender:aprender /var/log/aprender
sudo chown -R aprender:aprender /run/aprender

echo "=== VM01 Setup Complete ==="
```

### 6.2 Script de Deploy

**Arquivo**: `v2/infra/scripts/deploy.sh`

```bash
#!/bin/bash
# Deploy script para AS v2
set -e

DEPLOY_DIR="/var/www/aprender"
BACKEND_DIR="$DEPLOY_DIR/backend"
FRONTEND_DIR="$DEPLOY_DIR/frontend"
VENV="$DEPLOY_DIR/venv"

echo "=== Deploy AS v2 ==="

# 1. Pull latest code
cd $DEPLOY_DIR
git pull origin main

# 2. Backend
echo "--- Backend ---"
cd $BACKEND_DIR
source $VENV/bin/activate
pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# 3. Frontend
echo "--- Frontend ---"
cd $FRONTEND_DIR
npm ci
npm run build

# 4. Restart services
echo "--- Restarting services ---"
sudo systemctl restart aprender-gunicorn
sudo systemctl restart aprender-celery
sudo systemctl restart aprender-celerybeat
sudo systemctl reload nginx

# 5. Health check
echo "--- Health check ---"
sleep 5
curl -f http://localhost/healthz/ || exit 1

echo "=== Deploy Complete ==="
```

---

## 7. Backup Strategy

### 7.1 Backup Diário (VM02)

**Arquivo**: `/etc/cron.d/aprender-backup`

```cron
# Backup diário às 3h
0 3 * * * postgres /opt/scripts/backup_db.sh >> /var/log/aprender/backup.log 2>&1

# Limpeza de backups antigos (manter 7 dias)
0 4 * * * postgres find /var/backups/aprender -name "*.sql.gz" -mtime +7 -delete
```

### 7.2 Script de Backup

**Arquivo**: `v2/infra/scripts/backup_db.sh`

```bash
#!/bin/bash
set -e

BACKUP_DIR="/var/backups/aprender"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/aprender_db_$DATE.sql.gz"

mkdir -p $BACKUP_DIR

echo "[$(date)] Starting backup..."
pg_dump -U postgres -h localhost aprender_db | gzip > $BACKUP_FILE

echo "[$(date)] Backup complete: $BACKUP_FILE"
echo "[$(date)] Size: $(du -h $BACKUP_FILE | cut -f1)"
```

---

## 8. Capacidade Estimada

| Métrica | Valor |
|---------|-------|
| Requests/segundo | ~400-500 |
| Usuários simultâneos | ~500-1000 |
| Conexões DB | 200 max |
| Cache size | 3GB |
| Latência p95 | <300ms |

---

## 9. Checklist de Deploy

### Pré-Deploy

- [ ] Certificado SSL gerado/renovado
- [ ] Senhas fortes definidas (DB, Redis)
- [ ] Firewall configurado (apenas portas necessárias)
- [ ] Backup do banco atual

### VM01_App

- [ ] Nginx instalado e configurado
- [ ] Gunicorn instalado e configurado
- [ ] Celery workers configurados
- [ ] Celery beat configurado
- [ ] Logs configurados
- [ ] Systemd services habilitados

### VM02_Banco

- [ ] PostgreSQL instalado e tunado
- [ ] pg_hba.conf restritivo
- [ ] WAL archiving configurado
- [ ] Backup automático configurado
- [ ] Usuário aprender_user criado

### VM03_Redis

- [ ] Redis instalado e configurado
- [ ] Senha forte configurada
- [ ] AOF habilitado
- [ ] maxmemory configurado
- [ ] Comandos perigosos desabilitados

### Pós-Deploy

- [ ] Health check passing
- [ ] Logs sem erros
- [ ] SSL funcionando (https)
- [ ] Celery processando tasks
- [ ] Cache funcionando

---

## 10. Troubleshooting

### Problema: Conexões DB esgotadas

```bash
# Verificar conexões ativas
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity;"

# Solução: Aumentar max_connections ou verificar connection pooling
```

### Problema: Redis OOM

```bash
# Verificar uso de memória
redis-cli -a $REDIS_PASSWORD INFO memory

# Solução: Verificar maxmemory-policy ou aumentar RAM
```

### Problema: Gunicorn timeout

```bash
# Verificar logs
tail -f /var/log/aprender/gunicorn-error.log

# Solução: Verificar query lenta ou aumentar timeout
```

---

## Aprovação

- [ ] Configurações revisadas
- [ ] Senhas/secrets definidos
- [ ] VMs provisionadas
- [ ] Iniciar deploy

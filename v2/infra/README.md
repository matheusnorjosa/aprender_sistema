# Infrastructure Configuration

Configuration files and scripts for deploying Aprender Sistema v2 in production.

## Directory Structure

```
infra/
├── nginx/
│   ├── nginx.conf              # Main Nginx config
│   └── sites-available/
│       └── aprender            # Site config (copy to sites-enabled)
├── gunicorn/
│   └── gunicorn.conf.py        # Gunicorn worker config
├── celery/
│   └── celery.conf.py          # Celery config reference (actual config in Django)
├── postgresql/
│   ├── postgresql.conf         # PostgreSQL tuning (16GB RAM)
│   └── pg_hba.conf             # Access control
├── redis/
│   └── redis.conf              # Redis config (3GB, AOF)
├── systemd/
│   ├── aprender-gunicorn.service
│   ├── aprender-celery.service
│   └── aprender-celerybeat.service
├── cron/
│   └── aprender-backup         # Backup cron jobs
└── scripts/
    ├── setup_vm01.sh           # Initial VM setup
    ├── deploy.sh               # Deploy script
    ├── backup_db.sh            # Database backup
    ├── verify_backup.sh        # Backup verification
    └── restore_db.sh           # Database restore
```

## Quick Start

### 1. Initial Setup (VM01)

```bash
# Run as root
sudo ./scripts/setup_vm01.sh
```

### 2. Copy Configuration Files

```bash
# Nginx
sudo cp nginx/nginx.conf /etc/nginx/nginx.conf
sudo cp nginx/sites-available/aprender /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/aprender /etc/nginx/sites-enabled/

# Gunicorn
sudo cp gunicorn/gunicorn.conf.py /etc/aprender/

# Systemd
sudo cp systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
```

### 3. Enable Services

```bash
sudo systemctl enable aprender-gunicorn aprender-celery aprender-celerybeat nginx
```

### 4. Configure SSL

Generate or obtain SSL certificate and update paths in nginx config.

### 5. Deploy

```bash
./scripts/deploy.sh
```

## Environment Contracts (dev/staging/producao)

Use the operational matrix in `ENVIRONMENTS.md` to avoid context confusion between local dev, staging and production.

Quick commands (from `v2/infra`):

```bash
# DEV
make check-env-dev
make up-dev
make health-dev
make down-dev

# STAGING
make check-env-staging
make up-staging
make health-staging
make down-staging

# PROD (local controlled validation)
make check-env-prod
make up-prod
make health-prod
make down-prod
```

Default env templates are versioned as:

- `.env.dev`
- `.env.staging`
- `.env.production`

Important: keep placeholders only in these files. Real secrets must stay outside Git.

## Environment Variables

Create `/etc/aprender/env` with:

```bash
DJANGO_SETTINGS_MODULE=config.settings
SECRET_KEY=your-secret-key
DB_HOST=10.0.0.2
DB_PORT=5432
DB_NAME=aprender_db
DB_USER=aprender_user
DB_PASSWORD=your-db-password
REDIS_PASSWORD=your-redis-password
```

## VM Architecture

| VM | Role | IP | Ports |
|----|------|-----|-------|
| VM01_App | App + Workers | 10.0.0.1 | 80, 443 |
| VM02_Banco | PostgreSQL | 10.0.0.2 | 5432 |
| VM03_Redis | Redis | 10.0.0.3 | 6379 |

## Related Documentation

- [PLAN_infrastructure_scaling.md](../docs/PLAN_infrastructure_scaling.md)
- [DEPLOY_CHECKLIST.md](../docs/DEPLOY_CHECKLIST.md)
- [GUIDE_DR.md](../docs/GUIDE_DR.md) - Disaster Recovery & Backup

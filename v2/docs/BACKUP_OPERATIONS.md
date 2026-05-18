# Backup Operations Guide — AS v2

**Status**: ✅ Production-ready
**Refs**: Issue #169, PR #186, SEC-017 (criptografia opcional)
**Last Updated**: 2026-05-17

> **SSOT de operações de backup do AS v2.** Outros docs (`DISASTER_RECOVERY.md`,
> `GUIDE_DR.md`, `SLO_DEFINITIONS.md`, `docs/operations/backup.md`) devem apontar
> para este arquivo em vez de duplicar parâmetros.

## Parâmetros canônicos (RPO / RTO / Retenção / Frequência)

| Métrica | Valor | Nota |
|---|---|---|
| **RPO** (Recovery Point Objective) | **5 minutos** | WAL archiving contínuo (`archive_timeout=300`) |
| **RTO** (Recovery Time Objective) | **1 hora** | Inclui restore + migrations + smoke; restore puro é tipicamente 10-30 min em base atual |
| **Retenção padrão** | **7 dias** | Configurável via `BACKUP_RETENTION_DAYS`; S3 pode ter lifecycle policy mais longa |
| **Frequência** | **1×/dia** | 2:00 AM em Docker (Celery beat) / 3:00 AM em VM (cron) — janela noturna |
| **Verificação** | Semanal (domingos) | `verify_backup_health` (Docker) ou `verify_backup.sh` (VM) |

## Overview

The AS v2 backup system provides automated, reliable PostgreSQL backups with:

- **Daily full backups** (parâmetros acima)
- **S3/MinIO upload** support (optional)
- **Optional age encryption at rest** (SEC-017, set `BACKUP_AGE_RECIPIENT`)
- **Automated health checks** (weekly)
- **Failure alerting** via Sentry
- **Disaster recovery** with tested restore procedures

## Contextos suportados (mesmo script `backup_db.sh`)

| Contexto | Schedule | Storage | Doc complementar |
|---|---|---|---|
| **Docker Compose** (dev/staging/prod-like) | Celery Beat 2:00 AM (`tasks_backup.py`) | volume `backup_data` → `/backups` (+ S3 opcional) | `DISASTER_RECOVERY.md` (cenários de recovery) |
| **VM de produção** (systemd + PostgreSQL nativo) | Cron 3:00 AM (`/etc/cron.d/aprender-backup`) | `/var/backups/aprender` (+ S3 opcional) | `GUIDE_DR.md` (PITR via WAL) |

Em ambos os contextos, o script `v2/infra/scripts/backup_db.sh` é o **mesmo**;
muda apenas a chamada (Celery vs cron) e os defaults das env vars
(`DB_HOST=db` em Docker, `DB_HOST=localhost` em VM; `BACKUP_DIR=/backups` vs
`/var/backups/aprender`).

## Architecture

### Components

1. **Backup Script** (`v2/infra/scripts/backup_db.sh`)
   - PostgreSQL pg_dump execution
   - gzip compression
   - S3 upload (optional)
   - Retention policy enforcement
   - Comprehensive logging

2. **Restore Script** (`v2/infra/scripts/restore_db.sh`)
   - Interactive restoration with confirmation
   - Connection management
   - Post-restore verification

3. **Celery Tasks** (`v2/backend/apps/core/tasks_backup.py`)
   - `backup.perform_database_backup` - Main backup task
   - `backup.verify_backup_health` - Health monitoring

4. **Celery Beat Schedule** (`v2/backend/config/celery.py`)
   - Daily backup at 2:00 AM
   - Weekly health check on Sundays at 3:00 AM

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Celery Beat (2:00 AM daily)                                │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ Celery Worker: backup.perform_database_backup              │
│ - Validates environment                                     │
│ - Executes backup_db.sh                                     │
│ - Monitors execution (1h timeout)                           │
│ - Retries on failure (3x, exponential backoff)             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ backup_db.sh                                                │
│ 1. Test database connection                                │
│ 2. Execute pg_dump + gzip                                   │
│ 3. Upload to S3 (if configured)                             │
│ 4. Apply retention policy (delete old backups)             │
│ 5. Log results + send Sentry alerts on failure             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ Storage Destinations                                        │
│ - Local: /backups volume (Docker persistent)               │
│ - Remote: S3/MinIO bucket (optional)                        │
└─────────────────────────────────────────────────────────────┘
```

## Configuration

### Environment Variables

Add to `v2/infra/.env`:

```bash
# Automated Backups (MP5)
BACKUP_DIR=/backups
BACKUP_RETENTION_DAYS=7
BACKUP_S3_BUCKET=  # Optional: s3://your-bucket-name

# Sentry (for failure alerts)
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
```

### Docker Volumes

The `backup_data` volume is already configured in `v2/infra/docker-compose.yml`:

```yaml
services:
  web:
    volumes:
      - backup_data:/backups  # Persistent backup storage
      - ./scripts:/app/infra/scripts:ro  # Backup/restore scripts

volumes:
  backup_data:  # PostgreSQL backups storage
```

### S3/MinIO Setup (Optional)

If using S3/MinIO for remote backups:

1. **AWS Credentials** (for web/worker/beat containers):
   ```bash
   # In .env or container environment
   AWS_ACCESS_KEY_ID=your-access-key
   AWS_SECRET_ACCESS_KEY=your-secret-key
   AWS_DEFAULT_REGION=us-east-1  # Or your region
   ```

2. **Install AWS CLI** (already in Dockerfile):
   ```dockerfile
   RUN apt-get update && apt-get install -y awscli
   ```

3. **Configure Bucket**:
   ```bash
   BACKUP_S3_BUCKET=s3://aprender-backups/v2/
   ```

## Usage

### Manual Backup

Execute a manual backup from the web container:

```bash
# Full backup
cd v2/infra
docker compose exec web /app/infra/scripts/backup_db.sh full

# Check backup files
docker compose exec web ls -lh /backups/
```

### Manual Restore

Restore from a backup file:

```bash
# List available backups
docker compose exec web ls -lh /backups/

# Restore (DANGEROUS - will overwrite database!)
docker compose exec web /app/infra/scripts/restore_db.sh /backups/backup_full_20251118_020000.sql.gz
```

**Warning**: Restore will:
1. Drop all existing connections to the database
2. Overwrite all data with backup contents
3. Require interactive confirmation (unless in non-interactive mode)

### Trigger Backup Task via Celery

```bash
# Enter Django shell
docker compose exec web python manage.py shell

# Trigger backup task
from apps.core.tasks_backup import perform_database_backup
result = perform_database_backup.delay("full")
print(f"Task ID: {result.id}")
```

### Monitor Backup Status

```bash
# View Celery logs
docker compose logs -f worker

# View backup logs
docker compose exec web cat /backups/backup_*.log

# Check latest backup
docker compose exec web ls -lht /backups/ | head -5
```

## Scheduled Backups

### Celery Beat Schedule

Configured in `v2/backend/config/celery.py`:

| Task | Schedule | Description |
|------|----------|-------------|
| `daily-database-backup` | Daily at 2:00 AM | Full pg_dump backup |
| `weekly-backup-health-check` | Sundays at 3:00 AM | Verify backup system health |

### Verify Schedule

```bash
# Check Celery Beat schedule
docker compose exec beat celery -A config inspect scheduled

# View beat logs
docker compose logs -f beat
```

## Health Monitoring

### Weekly Health Check

The `backup.verify_backup_health` task runs every Sunday at 3:00 AM and checks:

1. **Backup directory exists and is writable**
2. **Recent backup exists** (within last 25 hours)
3. **S3 connectivity** (if configured)

Results are logged and sent to Sentry if warnings are detected.

### Manual Health Check

```bash
# Run health check manually
docker compose exec web python manage.py shell

from apps.core.tasks_backup import verify_backup_health
result = verify_backup_health()
print(result)
```

Expected output:
```python
{
    'status': 'healthy',  # or 'degraded'
    'checks_passed': 3,
    'checks_total': 3,
    'warnings': []  # List of issues if degraded
}
```

## Failure Handling

### Retry Policy

Backup tasks automatically retry on failure:
- **Max retries**: 3
- **Delay**: 5 minutes (300s) with exponential backoff
- **Timeout**: 1 hour per backup attempt

### Sentry Alerts

Failures are sent to Sentry when `SENTRY_DSN` is configured:
- Backup script failures (exit code != 0)
- Task timeouts
- Task retries exhausted
- Health check warnings

### Common Failures

| Issue | Cause | Solution |
|-------|-------|----------|
| `pg_dump: connection failed` | Database unreachable | Check `DB_HOST`, `DB_PORT`, ensure `db` service is running |
| `Permission denied: /backups` | Volume not writable | Check Docker volume permissions |
| `S3 upload failed` | AWS CLI not configured | Set `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, or leave `BACKUP_S3_BUCKET` empty |
| `Backup timed out` | Large database (>1h) | Increase timeout in `tasks_backup.py:89` |

## Disaster Recovery

### Restore Procedure

**Scenario**: Production database corrupted, need to restore from backup.

1. **Stop all services** (prevent writes during restore):
   ```bash
   cd v2/infra
   docker compose stop web worker beat
   ```

2. **List available backups**:
   ```bash
   docker compose exec db ls -lh /backups/
   # OR from S3
   aws s3 ls s3://aprender-backups/v2/backups/
   ```

3. **Download from S3** (if needed):
   ```bash
   docker compose exec web aws s3 cp \
     s3://aprender-backups/v2/backups/backup_full_20251118_020000.sql.gz \
     /backups/
   ```

4. **Restore database**:
   ```bash
   docker compose exec web /app/infra/scripts/restore_db.sh \
     /backups/backup_full_20251118_020000.sql.gz
   ```

5. **Verify restoration**:
   ```bash
   docker compose exec db psql -U aprender_user -d aprender_db -c \
     "SELECT COUNT(*) FROM core_solicitacao;"
   ```

6. **Restart services**:
   ```bash
   docker compose start web worker beat
   ```

### Recovery Time Objective (RTO)

- **Expected RTO**: 10-30 minutes (depending on database size)
- **Bottlenecks**:
  - S3 download speed (if remote backup)
  - Database size (gunzip + psql restore)
  - Connection dropping (minimal)

### Recovery Point Objective (RPO)

- **Expected RPO**: 5 minutes (WAL archiving + daily full dump)
- **Data loss**: Up to 5 minutes of transactions (WAL archive_timeout=300)
- **Daily dump**: Full pg_dump backup as baseline for PITR

## Testing

### Test Backup Script

```bash
# Dry-run backup (won't upload to S3)
docker compose exec web bash -c '
  BACKUP_S3_BUCKET="" \
  /app/infra/scripts/backup_db.sh full
'

# Verify backup file created
docker compose exec web ls -lh /backups/
```

### Test Restore Script

```bash
# Create test backup
docker compose exec web /app/infra/scripts/backup_db.sh full

# Restore in non-interactive mode
docker compose exec -T web /app/infra/scripts/restore_db.sh \
  /backups/backup_full_*.sql.gz

# Verify restoration
docker compose exec db psql -U aprender_user -d aprender_db -c \
  "SELECT version();"
```

### Test Celery Tasks

```bash
# Run pytest on backup tasks
docker compose exec web pytest apps/core/tests/test_tasks_backup.py -v
```

## Metrics and Monitoring

### Key Metrics

Track these metrics in production:

1. **Backup Success Rate**: % of successful backups (target: >99%)
2. **Backup Duration**: Time to complete backup (monitor for increases)
3. **Backup Size**: Disk usage trend (capacity planning)
4. **S3 Upload Duration**: Network performance
5. **Restore Test Success**: Monthly restore drills

### Prometheus Metrics (Future)

Potential metrics to export (MP1 integration):

```python
# Example Prometheus metrics
backup_duration_seconds = Histogram('backup_duration_seconds', 'Backup execution time')
backup_size_bytes = Gauge('backup_size_bytes', 'Latest backup file size')
backup_success_total = Counter('backup_success_total', 'Successful backups')
backup_failure_total = Counter('backup_failure_total', 'Failed backups')
```

## Security

### Access Control

- **Backup files**: Only accessible by web/worker/beat containers
- **S3 bucket**: Use IAM roles with minimal permissions (s3:PutObject, s3:GetObject)
- **Database credentials**: Never log `PGPASSWORD` in backup logs

### Data Encryption

- **At rest**: S3 bucket encryption (AES-256 or KMS)
- **In transit**: HTTPS for S3 uploads, TLS for database connections
- **Backup files**: gzip compression (not encryption)

**Recommendation**: Enable S3 server-side encryption (SSE-S3 or SSE-KMS):

```bash
aws s3api put-bucket-encryption \
  --bucket aprender-backups \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'
```

## Maintenance

### Retention Policy

Default: 7 days (configurable via `BACKUP_RETENTION_DAYS`)

**Policy logic** (in `backup_db.sh`):
```bash
find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete
```

**Manual cleanup**:
```bash
# List old backups (>30 days)
docker compose exec web find /backups -name "backup_*.sql.gz" -mtime +30

# Delete old backups (>30 days)
docker compose exec web find /backups -name "backup_*.sql.gz" -mtime +30 -delete
```

### Storage Capacity

Monitor disk usage:

```bash
# Check backup volume usage
docker compose exec web df -h /backups

# Check individual backup sizes
docker compose exec web du -h /backups/*.sql.gz | sort -h
```

**Capacity planning**:
- Estimate daily backup size: ~10-50 MB per GB of database
- With 7-day retention: `7 × daily_backup_size`
- Add 20% buffer for growth

### Rotate S3 Buckets

S3 lifecycle policy example (delete backups >30 days):

```json
{
  "Rules": [
    {
      "Id": "Delete old backups",
      "Status": "Enabled",
      "Prefix": "v2/backups/",
      "Expiration": {
        "Days": 30
      }
    }
  ]
}
```

Apply via AWS CLI:
```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket aprender-backups \
  --lifecycle-configuration file://lifecycle.json
```

## Troubleshooting

### Backup Not Running

**Symptoms**: No new backups in `/backups/` after 2:00 AM

**Diagnosis**:
```bash
# Check Celery Beat is running
docker compose ps beat

# Check Celery Beat logs
docker compose logs beat | grep "daily-database-backup"

# Check worker logs
docker compose logs worker | grep "backup.perform_database_backup"
```

**Common causes**:
- Beat container not running: `docker compose up -d beat`
- Wrong timezone: Verify `CELERY_TIMEZONE=America/Fortaleza` in settings
- Task queue full: `docker compose exec worker celery -A config purge`

### Backup Fails with "pg_dump: connection failed"

**Symptoms**: Backup script exits with error, logs show connection refused

**Diagnosis**:
```bash
# Test database connection from web container
docker compose exec web psql -h db -U aprender_user -d aprender_db -c "SELECT 1;"

# Check database is running
docker compose ps db
```

**Solutions**:
- Database not running: `docker compose up -d db`
- Wrong credentials: Verify `DB_USER`, `DB_PASSWORD` in `.env`
- Network issue: `docker compose restart db web`

### S3 Upload Fails

**Symptoms**: Backup succeeds locally but S3 upload fails

**Diagnosis**:
```bash
# Test AWS CLI from container
docker compose exec web aws s3 ls s3://aprender-backups/

# Check AWS credentials
docker compose exec web env | grep AWS
```

**Solutions**:
- Missing credentials: Set `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- Wrong bucket: Verify `BACKUP_S3_BUCKET` format (`s3://bucket-name/prefix/`)
- Permission denied: Check IAM policy allows `s3:PutObject`

### Restore Hangs or Times Out

**Symptoms**: Restore script runs for hours without completing

**Diagnosis**:
```bash
# Check database activity
docker compose exec db psql -U aprender_user -d postgres -c \
  "SELECT pid, state, query FROM pg_stat_activity WHERE datname = 'aprender_db';"
```

**Solutions**:
- Active connections blocking: Manually terminate connections before restore
- Large backup file: Expect ~5-10 minutes per GB
- Insufficient resources: Increase Docker memory/CPU limits

## Performance Optimization

### Parallel Compression

Modify `backup_db.sh` to use `pigz` (parallel gzip):

```bash
# Install pigz in Dockerfile
RUN apt-get update && apt-get install -y pigz

# Update backup_db.sh (line ~120)
pg_dump --format=custom "$PGDATABASE" | pigz -9 > "$BACKUP_FILE"
```

### Incremental Backups (Future Enhancement)

Not yet implemented. Potential approach:

1. **Base backup**: Full pg_dump daily
2. **Incremental**: WAL archiving every hour
3. **Restore**: Apply base + WAL segments

See: [PostgreSQL WAL Archiving](https://www.postgresql.org/docs/current/continuous-archiving.html)

## References

- **Issue**: #169 (MP5 - Automated Backups)
- **PR**: #186 (feat/mp5-automated-backups)
- **Scripts**:
  - `v2/infra/scripts/backup_db.sh`
  - `v2/infra/scripts/restore_db.sh`
- **Tasks**: `v2/backend/apps/core/tasks_backup.py`
- **Schedule**: `v2/backend/config/celery.py` (beat_schedule)

## Next Steps (Post-MP5)

1. **Monthly restore drills** (verify backups are restorable)
2. **Prometheus metrics** integration (MP1)
3. **Incremental backups** (WAL archiving)
4. **Cross-region replication** (S3 versioning + replication)
5. **Automated testing** (restore to ephemeral database, run tests)

---

**Document Owner**: DevOps/SRE Team
**Review Cycle**: Quarterly
**Last Reviewed**: 2025-11-18

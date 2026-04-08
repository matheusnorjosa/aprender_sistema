#!/bin/bash
# Database backup script for Docker and VM environments
#
# Docker: Called by Celery task (tasks_backup.py)
# VM: Run via cron: 0 3 * * * postgres /opt/scripts/backup_db.sh
#
# Environment variables (all have sensible defaults):
#   DB_HOST     - Database host (default: localhost for VM, should be 'db' in Docker)
#   DB_PORT     - Database port (default: 5432)
#   DB_USER     - Database user (default: postgres)
#   DB_NAME     - Database name (default: aprender_db)
#   DB_PASSWORD - Database password (used via PGPASSWORD)
#   BACKUP_DIR  - Backup directory (default: /backups for Docker, /var/backups/aprender for VM)
#   BACKUP_RETENTION_DAYS - Days to keep backups (default: 7)
#
# Refs: Issue #562 (C-05), MP5

set -e

# Configuration with environment variable support
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-aprender_db}"
DB_USER="${DB_USER:-postgres}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
DATE=$(date +%Y%m%d_%H%M%S)
S3_BUCKET="${S3_BUCKET:-}"
# Normalize bucket name if provided with scheme
S3_BUCKET="${S3_BUCKET#s3://}"

# SEC-017: Optional encryption via age (when BACKUP_AGE_RECIPIENT is set)
BACKUP_AGE_RECIPIENT="${BACKUP_AGE_RECIPIENT:-}"

# Naming convention: backup_full_YYYYMMDD_HHMMSS.sql.gz[.age]
if [ -n "$BACKUP_AGE_RECIPIENT" ]; then
    BACKUP_FILE="$BACKUP_DIR/backup_full_$DATE.sql.gz.age"
else
    BACKUP_FILE="$BACKUP_DIR/backup_full_$DATE.sql.gz"
fi

# Export password for pg_dump (if provided)
if [ -n "$DB_PASSWORD" ]; then
    export PGPASSWORD="$DB_PASSWORD"
fi

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup of $DB_NAME from $DB_HOST:$DB_PORT..."

# Create backup with compression (+ optional encryption)
# Using -h $DB_HOST and -p $DB_PORT for Docker compatibility
if [ -n "$BACKUP_AGE_RECIPIENT" ]; then
    echo "[$(date)] Encryption enabled (age recipient: ${BACKUP_AGE_RECIPIENT:0:20}...)"
    pg_dump -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" "$DB_NAME" \
        | gzip | age -r "$BACKUP_AGE_RECIPIENT" > "$BACKUP_FILE"
else
    pg_dump -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" "$DB_NAME" | gzip > "$BACKUP_FILE"
fi

# Verify backup
if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "[$(date)] Backup complete: $BACKUP_FILE"
    echo "[$(date)] Size: $SIZE"

    # Output the backup file path for Celery task parsing
    echo "[$(date)] backup_full_$DATE.sql.gz ($BACKUP_FILE)"

    # Optional: Copy to S3 (if S3_BUCKET is configured)
    if [ -n "$S3_BUCKET" ]; then
        echo "[$(date)] Uploading to S3: s3://$S3_BUCKET/backups/"
        aws s3 cp "$BACKUP_FILE" "s3://$S3_BUCKET/backups/" || echo "[$(date)] WARNING: S3 upload failed"
    fi
else
    echo "[$(date)] ERROR: Backup failed or file is empty!"
    exit 1
fi

# Cleanup old backups
echo "[$(date)] Cleaning up backups older than $BACKUP_RETENTION_DAYS days..."
find "$BACKUP_DIR" \( -name "backup_full_*.sql.gz" -o -name "backup_full_*.sql.gz.age" \) -mtime +"$BACKUP_RETENTION_DAYS" -delete 2>/dev/null || true

echo "[$(date)] Backup process complete."

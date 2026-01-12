#!/bin/bash
# Database backup script for VM02_Banco
# Run via cron: 0 3 * * * postgres /opt/scripts/backup_db.sh
#
# Backups are stored in /var/backups/aprender/
# Retention: 7 days (managed by separate cron job)

set -e

# Configuration
BACKUP_DIR="/var/backups/aprender"
DB_NAME="${DB_NAME:-aprender_db}"
DB_USER="${DB_USER:-postgres}"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_$DATE.sql.gz"

# Ensure backup directory exists
mkdir -p $BACKUP_DIR

echo "[$(date)] Starting backup of $DB_NAME..."

# Create backup with compression
pg_dump -U $DB_USER -h localhost $DB_NAME | gzip > $BACKUP_FILE

# Verify backup
if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
    SIZE=$(du -h $BACKUP_FILE | cut -f1)
    echo "[$(date)] Backup complete: $BACKUP_FILE"
    echo "[$(date)] Size: $SIZE"

    # Optional: Copy to remote storage (uncomment and configure)
    # aws s3 cp $BACKUP_FILE s3://your-bucket/backups/
    # OR
    # rclone copy $BACKUP_FILE remote:backups/

else
    echo "[$(date)] ERROR: Backup failed or file is empty!"
    exit 1
fi

# Cleanup old backups (keep last 7 days)
echo "[$(date)] Cleaning up old backups..."
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "[$(date)] Backup process complete."

#!/bin/bash
# Verify backup integrity for Aprender Sistema
# Run weekly via cron to ensure backups are valid
#
# Usage: ./verify_backup.sh

set -e

BACKUP_DIR="/var/backups/aprender"
TEMP_DIR="/tmp/backup_verify_$$"
DB_NAME="${DB_NAME:-aprender_db}"

echo "[$(date)] Starting backup verification..."

# Find the most recent backup
LATEST_BACKUP=$(ls -t $BACKUP_DIR/*.sql.gz 2>/dev/null | head -1)

if [ -z "$LATEST_BACKUP" ]; then
    echo "[$(date)] ERROR: No backup files found in $BACKUP_DIR"
    exit 1
fi

echo "[$(date)] Verifying: $LATEST_BACKUP"

# Create temp directory
mkdir -p $TEMP_DIR
trap "rm -rf $TEMP_DIR" EXIT

# Test gzip integrity
echo "[$(date)] Testing gzip integrity..."
if ! gzip -t "$LATEST_BACKUP"; then
    echo "[$(date)] ERROR: Backup file is corrupted!"
    exit 1
fi

# Decompress and check SQL structure
echo "[$(date)] Checking SQL structure..."
UNCOMPRESSED="$TEMP_DIR/backup.sql"
gunzip -c "$LATEST_BACKUP" > "$UNCOMPRESSED"

# Check for essential markers
if ! grep -q "PostgreSQL database dump" "$UNCOMPRESSED"; then
    echo "[$(date)] ERROR: Not a valid PostgreSQL dump!"
    exit 1
fi

if ! grep -q "CREATE TABLE" "$UNCOMPRESSED"; then
    echo "[$(date)] ERROR: No CREATE TABLE statements found!"
    exit 1
fi

# Count tables
TABLE_COUNT=$(grep -c "CREATE TABLE" "$UNCOMPRESSED" || echo "0")
echo "[$(date)] Found $TABLE_COUNT tables in backup"

# Check file size (should be reasonable)
SIZE=$(stat -f%z "$LATEST_BACKUP" 2>/dev/null || stat -c%s "$LATEST_BACKUP")
SIZE_MB=$((SIZE / 1024 / 1024))
echo "[$(date)] Backup size: ${SIZE_MB}MB"

if [ "$SIZE_MB" -lt 1 ]; then
    echo "[$(date)] WARNING: Backup seems too small (${SIZE_MB}MB)"
fi

# Check backup age
BACKUP_AGE=$(( ($(date +%s) - $(stat -f%m "$LATEST_BACKUP" 2>/dev/null || stat -c%Y "$LATEST_BACKUP")) / 86400 ))
echo "[$(date)] Backup age: ${BACKUP_AGE} days"

if [ "$BACKUP_AGE" -gt 1 ]; then
    echo "[$(date)] WARNING: Latest backup is ${BACKUP_AGE} days old!"
fi

echo "[$(date)] Backup verification completed successfully!"
echo "[$(date)] Latest backup: $LATEST_BACKUP"
echo "[$(date)] Size: ${SIZE_MB}MB, Tables: $TABLE_COUNT, Age: ${BACKUP_AGE} days"

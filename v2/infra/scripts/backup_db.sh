#!/bin/bash
#
# backup_db.sh - PostgreSQL backup script for AS v2
#
# Usage:
#   backup_db.sh [full|incremental]
#
# Environment variables required:
#   DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
#   BACKUP_DIR (default: /backups)
#   BACKUP_RETENTION_DAYS (default: 7)
#   S3_BUCKET (optional, for S3 upload)
#

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Configuration
BACKUP_TYPE="${1:-full}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$BACKUP_DIR/backup_${TIMESTAMP}.log"

# Database configuration from environment
export PGHOST="${DB_HOST:-db}"
export PGPORT="${DB_PORT:-5432}"
export PGUSER="${DB_USER:-aprender_user}"
export PGPASSWORD="${DB_PASSWORD}"
export PGDATABASE="${DB_NAME:-aprender_db}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" | tee -a "$LOG_FILE" >&2
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*" | tee -a "$LOG_FILE"
}

# Cleanup function for exit
cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        log_error "Backup failed with exit code $exit_code"
        # Optionally send alert (Sentry, Slack, email, etc.)
        if command -v python3 &> /dev/null && [ -n "${SENTRY_DSN:-}" ]; then
            python3 -c "import sentry_sdk; sentry_sdk.init('$SENTRY_DSN'); sentry_sdk.capture_message('Backup failed: exit code $exit_code', level='error')" 2>/dev/null || true
        fi
    fi
    exit $exit_code
}

trap cleanup EXIT

# Validate backup directory
if [ ! -d "$BACKUP_DIR" ]; then
    log "Creating backup directory: $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"
fi

# Perform backup
perform_backup() {
    local backup_file=""

    case "$BACKUP_TYPE" in
        full)
            backup_file="$BACKUP_DIR/backup_full_${TIMESTAMP}.sql.gz"
            log "Starting FULL backup..."
            log "Database: $PGDATABASE @ $PGHOST:$PGPORT"
            log "Output: $backup_file"

            # Full backup with pg_dump (schema + data)
            if pg_dump \
                --format=plain \
                --no-owner \
                --no-acl \
                --verbose \
                --file=- \
                2>>"$LOG_FILE" | gzip > "$backup_file"; then

                local size=$(du -h "$backup_file" | cut -f1)
                log_success "Full backup completed: $backup_file ($size)"
                echo "$backup_file"
                return 0
            else
                log_error "Full backup failed"
                return 1
            fi
            ;;

        incremental)
            # Incremental backup (WAL archiving would be ideal, but for simplicity we do full)
            # NOTE: True incremental requires WAL archiving setup in PostgreSQL
            log_warning "Incremental backup not yet implemented - performing full backup instead"
            BACKUP_TYPE="full"
            perform_backup
            return $?
            ;;

        *)
            log_error "Unknown backup type: $BACKUP_TYPE (use 'full' or 'incremental')"
            return 1
            ;;
    esac
}

# Upload to S3 (if configured)
upload_to_s3() {
    local file=$1

    if [ -z "${S3_BUCKET:-}" ]; then
        log "S3_BUCKET not configured - skipping upload"
        return 0
    fi

    if ! command -v aws &> /dev/null; then
        log_warning "AWS CLI not installed - skipping S3 upload"
        return 0
    fi

    log "Uploading to S3: s3://$S3_BUCKET/backups/$(basename "$file")"

    if aws s3 cp "$file" "s3://$S3_BUCKET/backups/" \
        --storage-class STANDARD_IA \
        --metadata "timestamp=$TIMESTAMP,type=$BACKUP_TYPE" 2>>"$LOG_FILE"; then
        log_success "S3 upload completed"
        return 0
    else
        log_error "S3 upload failed"
        return 1
    fi
}

# Apply retention policy
apply_retention() {
    log "Applying retention policy (keep last $RETENTION_DAYS days)..."

    local deleted_count=0

    # Find and delete old backups
    find "$BACKUP_DIR" \
        -name "backup_*.sql.gz" \
        -type f \
        -mtime +$RETENTION_DAYS \
        -print0 2>>"$LOG_FILE" | while IFS= read -r -d '' file; do

        log "Deleting old backup: $(basename "$file")"
        rm -f "$file"
        deleted_count=$((deleted_count + 1))
    done

    # Also delete old log files
    find "$BACKUP_DIR" \
        -name "backup_*.log" \
        -type f \
        -mtime +$RETENTION_DAYS \
        -delete 2>>"$LOG_FILE"

    log "Retention policy applied (deleted $deleted_count old backups)"
}

# Test database connection
test_connection() {
    log "Testing database connection..."

    if psql -c "SELECT version();" &>/dev/null; then
        log_success "Database connection OK"
        return 0
    else
        log_error "Cannot connect to database"
        return 1
    fi
}

# Main execution
main() {
    log "========================================="
    log "AS v2 - PostgreSQL Backup Script"
    log "Type: $BACKUP_TYPE"
    log "========================================="

    # Test connection
    test_connection || exit 1

    # Perform backup
    backup_file=$(perform_backup)
    if [ $? -ne 0 ]; then
        exit 1
    fi

    # Upload to S3 (if configured)
    upload_to_s3 "$backup_file" || log_warning "S3 upload failed, but backup file is available locally"

    # Apply retention policy
    apply_retention

    log_success "Backup process completed successfully"
    log "========================================="
}

# Run main function
main

#!/bin/bash
#
# restore_db.sh - PostgreSQL restore script for AS v2
#
# Usage:
#   restore_db.sh <backup_file.sql.gz>
#
# Environment variables required:
#   DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
#

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Configuration
BACKUP_FILE="${1:-}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"

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
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

# Validate input
validate_input() {
    if [ -z "$BACKUP_FILE" ]; then
        log_error "Usage: $0 <backup_file.sql.gz>"
        echo "Available backups in $BACKUP_DIR:"
        ls -lh "$BACKUP_DIR"/backup_*.sql.gz 2>/dev/null || echo "  (no backups found)"
        exit 1
    fi

    if [ ! -f "$BACKUP_FILE" ]; then
        log_error "Backup file not found: $BACKUP_FILE"
        exit 1
    fi

    if [[ ! "$BACKUP_FILE" =~ \.sql\.gz$ ]]; then
        log_error "Backup file must be a .sql.gz file"
        exit 1
    fi
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

# Confirm restore (interactive mode)
confirm_restore() {
    log_warning "========================================="
    log_warning "WARNING: This will OVERWRITE the database!"
    log_warning "Database: $PGDATABASE @ $PGHOST:$PGPORT"
    log_warning "Backup file: $(basename "$BACKUP_FILE")"
    log_warning "Size: $(du -h "$BACKUP_FILE" | cut -f1)"
    log_warning "========================================="

    # Skip confirmation if in non-interactive mode
    if [ ! -t 0 ]; then
        log "Running in non-interactive mode - skipping confirmation"
        return 0
    fi

    read -p "Are you sure you want to proceed? (yes/no): " -r
    echo

    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log "Restore cancelled by user"
        exit 0
    fi
}

# Drop existing connections
drop_connections() {
    log "Dropping existing connections to database..."

    psql -d postgres -c "
        SELECT pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = '$PGDATABASE'
          AND pid <> pg_backend_pid();
    " &>/dev/null || log_warning "Could not drop all connections"

    log_success "Connections dropped"
}

# Perform restore
perform_restore() {
    log "Starting database restore..."
    log "Backup file: $BACKUP_FILE"

    # Extract and restore
    if gunzip -c "$BACKUP_FILE" | psql 2>&1 | tee /tmp/restore.log; then
        log_success "Database restored successfully"
        return 0
    else
        log_error "Database restore failed"
        log_error "Check /tmp/restore.log for details"
        return 1
    fi
}

# Verify restore
verify_restore() {
    log "Verifying restore..."

    # Check if database has tables
    local table_count=$(psql -t -c "
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_schema = 'public';
    " | tr -d ' ')

    if [ "$table_count" -gt 0 ]; then
        log_success "Restore verification OK ($table_count tables found)"
        return 0
    else
        log_error "Restore verification FAILED (no tables found)"
        return 1
    fi
}

# Main execution
main() {
    log "========================================="
    log "AS v2 - PostgreSQL Restore Script"
    log "========================================="

    # Validate input
    validate_input

    # Test connection
    test_connection || exit 1

    # Confirm restore (interactive)
    confirm_restore

    # Drop existing connections
    drop_connections

    # Perform restore
    perform_restore || exit 1

    # Verify restore
    verify_restore || exit 1

    log_success "Restore process completed successfully"
    log "========================================="
}

# Run main function
main

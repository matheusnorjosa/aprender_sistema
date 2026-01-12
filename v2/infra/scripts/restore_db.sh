#!/bin/bash
# Database restore script for Aprender Sistema
# USE WITH CAUTION - This will overwrite the current database!
#
# Usage: 
#   ./restore_db.sh                     # Interactive mode (lists available backups)
#   ./restore_db.sh backup_file.sql.gz  # Restore specific backup
#   ./restore_db.sh --latest            # Restore most recent backup
#
# Prerequisites:
#   - PostgreSQL running
#   - Sufficient disk space
#   - Application stopped (recommended)

set -e

BACKUP_DIR="/var/backups/aprender"
DB_NAME="${DB_NAME:-aprender_db}"
DB_USER="${DB_USER:-aprender_user}"
DB_HOST="${DB_HOST:-localhost}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}  Aprender Sistema - Database Restore  ${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""

# Determine backup file
if [ "$1" == "--latest" ]; then
    BACKUP_FILE=$(ls -t $BACKUP_DIR/*.sql.gz 2>/dev/null | head -1)
    if [ -z "$BACKUP_FILE" ]; then
        echo -e "${RED}ERROR: No backup files found in $BACKUP_DIR${NC}"
        exit 1
    fi
    echo "Using latest backup: $BACKUP_FILE"
elif [ -n "$1" ]; then
    if [ -f "$1" ]; then
        BACKUP_FILE="$1"
    elif [ -f "$BACKUP_DIR/$1" ]; then
        BACKUP_FILE="$BACKUP_DIR/$1"
    else
        echo -e "${RED}ERROR: Backup file not found: $1${NC}"
        exit 1
    fi
else
    # Interactive mode - list available backups
    echo "Available backups:"
    echo ""
    ls -lh $BACKUP_DIR/*.sql.gz 2>/dev/null | awk '{print NR". "$9" ("$5")"}'
    echo ""
    read -p "Enter backup number or full path: " SELECTION
    
    if [[ "$SELECTION" =~ ^[0-9]+$ ]]; then
        BACKUP_FILE=$(ls -t $BACKUP_DIR/*.sql.gz | sed -n "${SELECTION}p")
    else
        BACKUP_FILE="$SELECTION"
    fi
    
    if [ ! -f "$BACKUP_FILE" ]; then
        echo -e "${RED}ERROR: Invalid selection${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${YELLOW}WARNING: This will OVERWRITE the database '$DB_NAME'!${NC}"
echo ""
echo "Backup file: $BACKUP_FILE"
echo "Database: $DB_NAME"
echo "Host: $DB_HOST"
echo ""

read -p "Are you sure you want to continue? (type 'yes' to confirm): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

echo ""
echo "[$(date)] Starting restore..."

# Step 1: Verify backup integrity
echo "[$(date)] Verifying backup integrity..."
if ! gzip -t "$BACKUP_FILE"; then
    echo -e "${RED}ERROR: Backup file is corrupted!${NC}"
    exit 1
fi
echo -e "${GREEN}Backup integrity OK${NC}"

# Step 2: Terminate existing connections
echo "[$(date)] Terminating existing connections..."
psql -h $DB_HOST -U postgres -c "
    SELECT pg_terminate_backend(pid) 
    FROM pg_stat_activity 
    WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();
" 2>/dev/null || true

# Step 3: Drop and recreate database
echo "[$(date)] Recreating database..."
psql -h $DB_HOST -U postgres -c "DROP DATABASE IF EXISTS $DB_NAME;"
psql -h $DB_HOST -U postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

# Step 4: Restore backup
echo "[$(date)] Restoring backup (this may take a while)..."
gunzip -c "$BACKUP_FILE" | psql -h $DB_HOST -U postgres -d $DB_NAME -q

# Step 5: Verify restore
echo "[$(date)] Verifying restore..."
TABLE_COUNT=$(psql -h $DB_HOST -U postgres -d $DB_NAME -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';")
echo "Tables restored: $TABLE_COUNT"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Restore completed successfully!      ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Start the application"
echo "2. Verify data integrity"
echo "3. Run migrations if needed: python manage.py migrate"

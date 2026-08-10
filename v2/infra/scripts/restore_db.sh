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

# NB: pipefail NAO e' global de proposito. As selecoes de backup usam `ls A B | head`,
# e com so `.age` em prod o glob `*.sql.gz` nao casa -> `ls` sai 2 e, sob pipefail+set -e,
# abortaria a selecao antes do guard de "nenhum backup". Onde a falha do pipe importa
# (os pipes do `age`), habilitamos pipefail LOCALMENTE via subshell.
set -e

# BACKUP_DIR respeita a env var (o mount do container aponta /backups). Antes estava
# hardcoded, entao `--latest` dentro do container nao achava os backups (#1611).
BACKUP_DIR="${BACKUP_DIR:-/var/backups/aprender}"
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
    # inclui os cifrados .sql.gz.age (o que prod grava, SEC-017) — audit #1541.
    BACKUP_FILE=$(ls -t $BACKUP_DIR/*.sql.gz $BACKUP_DIR/*.sql.gz.age 2>/dev/null | head -1)
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
    # -t nos DOIS (lista e selecao) p/ numeracao consistente por tempo; inclui .age.
    ls -lht $BACKUP_DIR/*.sql.gz $BACKUP_DIR/*.sql.gz.age 2>/dev/null | awk '{print NR". "$9" ("$5")"}'
    echo ""
    read -p "Enter backup number or full path: " SELECTION

    if [[ "$SELECTION" =~ ^[0-9]+$ ]]; then
        BACKUP_FILE=$(ls -t $BACKUP_DIR/*.sql.gz $BACKUP_DIR/*.sql.gz.age 2>/dev/null | sed -n "${SELECTION}p")
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
# SEC-017/#1611: a verificacao precisa ser CIENTE DO FORMATO. Producao grava so
# `.sql.gz.age`, cujo cabecalho e' texto ("age-encryption.org/v1"), nao gzip. Rodar
# `gzip -t` direto no .age falhava com "corrupted" (falso) e travava TODO restore de
# prod. Espelhamos aqui o branch que a Step 4 ja tinha: decifrar e SO ENTAO testar o gzip.
echo "[$(date)] Verifying backup integrity..."
if echo "$BACKUP_FILE" | grep -q '\.age$'; then
    BACKUP_AGE_KEY="${BACKUP_AGE_KEY:-/etc/backup-key.txt}"
    if ! command -v age > /dev/null 2>&1; then
        echo -e "${RED}ERROR: 'age' nao esta no PATH — necessario para verificar/restaurar backup .age${NC}"
        exit 1
    fi
    if [ ! -r "$BACKUP_AGE_KEY" ]; then
        echo -e "${RED}ERROR: chave age nao legivel: $BACKUP_AGE_KEY${NC}"
        exit 1
    fi
    # pipefail LOCAL (subshell): sem ele a falha do `age` seria mascarada pelo exit do gzip -t.
    if ! ( set -o pipefail; age -d -i "$BACKUP_AGE_KEY" "$BACKUP_FILE" | gzip -t ); then
        echo -e "${RED}ERROR: backup cifrado invalido (falha ao decifrar ou gzip corrompido)!${NC}"
        exit 1
    fi
else
    if ! gzip -t "$BACKUP_FILE"; then
        echo -e "${RED}ERROR: Backup file is corrupted!${NC}"
        exit 1
    fi
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
# SEC-017: Support encrypted backups (.age extension)
if echo "$BACKUP_FILE" | grep -q '\.age$'; then
    BACKUP_AGE_KEY="${BACKUP_AGE_KEY:-/etc/backup-key.txt}"
    echo "[$(date)] Decrypting encrypted backup with age..."
    # pipefail LOCAL: uma falha do `age` (chave errada, arquivo truncado) deve abortar o
    # restore — sem isso, o psql receberia stream vazio e "restauraria" um banco incompleto.
    ( set -o pipefail; age -d -i "$BACKUP_AGE_KEY" "$BACKUP_FILE" | gunzip | psql -h $DB_HOST -U postgres -d $DB_NAME -q )
else
    gunzip -c "$BACKUP_FILE" | psql -h $DB_HOST -U postgres -d $DB_NAME -q
fi

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

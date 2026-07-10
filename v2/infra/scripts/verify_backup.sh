#!/bin/bash
# Verify backup integrity for Aprender Sistema
# Run weekly via cron to ensure backups are valid
#
# Usage: ./verify_backup.sh

set -e

BACKUP_DIR="${BACKUP_DIR:-/var/backups/aprender}"
TEMP_DIR="/tmp/backup_verify_$$"
DB_NAME="${DB_NAME:-aprender_db}"
# Piso de bytes alinhado ao gate de deploy check_backup.sh (#1529).
BACKUP_MIN_SIZE="${BACKUP_MIN_SIZE:-1024}"

echo "[$(date)] Starting backup verification..."

# Backup mais recente — inclui os cifrados .sql.gz.age, que sao o que prod grava
# (SEC-017). O glob antigo (`*.sql.gz`) ficava CEGO aos backups reais e validava um
# .sql.gz legado, saindo "successfully" com falsa confianca (audit #1541 — mesma
# familia do bug de glob corrigido no health-check em #1455).
LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/backup_full_*.sql.gz "$BACKUP_DIR"/backup_full_*.sql.gz.age 2>/dev/null | head -1)

if [ -z "$LATEST_BACKUP" ]; then
    echo "[$(date)] ERROR: No backup files found in $BACKUP_DIR"
    exit 1
fi

echo "[$(date)] Verifying: $LATEST_BACKUP"

# Tamanho — piso HARD (exit != 0). Um dump truncado/vazio NAO pode sair "success":
# era WARNING-only, entao um backup minusculo passava verde (audit #1541).
SIZE=$(stat -c%s "$LATEST_BACKUP" 2>/dev/null || stat -f%z "$LATEST_BACKUP")
if [ "$SIZE" -lt "$BACKUP_MIN_SIZE" ]; then
    echo "[$(date)] ERROR: Backup too small (${SIZE}B < ${BACKUP_MIN_SIZE}B) — truncado/vazio?"
    exit 1
fi
SIZE_MB=$((SIZE / 1024 / 1024))
echo "[$(date)] Backup size: ${SIZE}B (~${SIZE_MB}MB)"

# Integridade de CONTEUDO (gzip -t + marcadores SQL) so no PLAINTEXT. Um .age nao
# pode ser inspecionado aqui: a chave PRIVADA nao vive na VM por design (fica no
# gerenciador de senhas). Para .age, garantimos presenca + tamanho + frescor; a
# verificacao de conteudo cifrado e exercitada no test_dr.sh (com a chave, fora de prod).
case "$LATEST_BACKUP" in
    *.age)
        echo "[$(date)] Encrypted backup (.age): checagem de conteudo pulada (chave privada nao esta na VM, SEC-017)."
        TABLE_COUNT="n/a (cifrado)"
        ;;
    *)
        mkdir -p "$TEMP_DIR"
        trap 'rm -rf "$TEMP_DIR"' EXIT
        echo "[$(date)] Testing gzip integrity..."
        if ! gzip -t "$LATEST_BACKUP"; then
            echo "[$(date)] ERROR: Backup file is corrupted!"
            exit 1
        fi
        echo "[$(date)] Checking SQL structure..."
        UNCOMPRESSED="$TEMP_DIR/backup.sql"
        gunzip -c "$LATEST_BACKUP" > "$UNCOMPRESSED"
        if ! grep -q "PostgreSQL database dump" "$UNCOMPRESSED"; then
            echo "[$(date)] ERROR: Not a valid PostgreSQL dump!"
            exit 1
        fi
        if ! grep -q "CREATE TABLE" "$UNCOMPRESSED"; then
            echo "[$(date)] ERROR: No CREATE TABLE statements found!"
            exit 1
        fi
        TABLE_COUNT=$(grep -c "CREATE TABLE" "$UNCOMPRESSED" || echo "0")
        echo "[$(date)] Found $TABLE_COUNT tables in backup"
        ;;
esac

# Frescor — informativo. O gate de frescor que BLOQUEIA deploy e o check_backup.sh;
# aqui e so um aviso ruidoso (age nao e corrupcao).
BACKUP_AGE=$(( ($(date +%s) - $(stat -c%Y "$LATEST_BACKUP" 2>/dev/null || stat -f%m "$LATEST_BACKUP")) / 86400 ))
echo "[$(date)] Backup age: ${BACKUP_AGE} days"
if [ "$BACKUP_AGE" -gt 1 ]; then
    echo "[$(date)] WARNING: Latest backup is ${BACKUP_AGE} days old!"
fi

echo "[$(date)] Backup verification completed successfully!"
echo "[$(date)] Latest backup: $LATEST_BACKUP"
echo "[$(date)] Size: ${SIZE}B, Tables: $TABLE_COUNT, Age: ${BACKUP_AGE} days"

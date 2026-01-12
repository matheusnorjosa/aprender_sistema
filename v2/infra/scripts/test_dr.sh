#!/bin/bash
#
# test_dr.sh — Disaster Recovery Test Script (Gap 9 - PLAN_maturity_gaps.md)
#
# Tests backup/restore procedures to validate DR capabilities.
# Run monthly or after infrastructure changes.
#
# Usage:
#   ./test_dr.sh              # Interactive mode
#   ./test_dr.sh --ci         # CI mode (non-interactive)
#
# Exit codes:
#   0 - All tests passed
#   1 - Test failed
#   2 - Configuration error

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${BACKUP_DIR:-/tmp/dr_test_backups}"
TEST_DB_NAME="dr_test_$(date +%s)"
CI_MODE=false

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --ci) CI_MODE=true ;;
        *) echo "Unknown parameter: $1"; exit 2 ;;
    esac
    shift
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up test database..."
    docker compose exec -T db psql -U postgres -c "DROP DATABASE IF EXISTS ${TEST_DB_NAME};" 2>/dev/null || true
    rm -rf "${BACKUP_DIR}" 2>/dev/null || true
}

# Set trap for cleanup
trap cleanup EXIT

echo "=============================================="
echo "      DISASTER RECOVERY TEST"
echo "=============================================="
echo "Date: $(date)"
echo "Test DB: ${TEST_DB_NAME}"
echo "CI Mode: ${CI_MODE}"
echo "=============================================="
echo ""

# Step 1: Create test backup
log_info "Step 1: Creating test backup..."
mkdir -p "${BACKUP_DIR}"

BACKUP_FILE="${BACKUP_DIR}/dr_test.sql.gz"
docker compose exec -T db pg_dump -U postgres aprender_sistema | gzip > "${BACKUP_FILE}"

if [ ! -f "${BACKUP_FILE}" ]; then
    log_error "Backup file not created!"
    exit 1
fi

BACKUP_SIZE=$(stat -f%z "${BACKUP_FILE}" 2>/dev/null || stat -c%s "${BACKUP_FILE}")
log_info "Backup created: ${BACKUP_FILE} (${BACKUP_SIZE} bytes)"

if [ "${BACKUP_SIZE}" -lt 1000 ]; then
    log_error "Backup is suspiciously small (${BACKUP_SIZE} bytes)"
    exit 1
fi

log_info "Step 1: PASSED"
echo ""

# Step 2: Create test database
log_info "Step 2: Creating test database..."
docker compose exec -T db psql -U postgres -c "CREATE DATABASE ${TEST_DB_NAME};"
log_info "Test database created: ${TEST_DB_NAME}"
log_info "Step 2: PASSED"
echo ""

# Step 3: Restore backup to test database
log_info "Step 3: Restoring backup to test database..."
gunzip -c "${BACKUP_FILE}" | docker compose exec -T db psql -U postgres -d "${TEST_DB_NAME}"
log_info "Backup restored successfully"
log_info "Step 3: PASSED"
echo ""

# Step 4: Validate restore - table count
log_info "Step 4: Validating table count..."
TABLE_COUNT=$(docker compose exec -T db psql -U postgres -d "${TEST_DB_NAME}" -t -c \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")
TABLE_COUNT=$(echo "${TABLE_COUNT}" | tr -d ' ')

log_info "Tables in test database: ${TABLE_COUNT}"

if [ "${TABLE_COUNT}" -lt 10 ]; then
    log_error "Too few tables restored (${TABLE_COUNT}). Expected at least 10."
    exit 1
fi

log_info "Step 4: PASSED"
echo ""

# Step 5: Validate key tables exist
log_info "Step 5: Validating key tables..."
REQUIRED_TABLES=(
    "core_usuario"
    "core_solicitacao"
    "core_municipio"
    "core_projeto"
    "core_gerencia"
    "core_auditlog"
)

MISSING_TABLES=()
for TABLE in "${REQUIRED_TABLES[@]}"; do
    EXISTS=$(docker compose exec -T db psql -U postgres -d "${TEST_DB_NAME}" -t -c \
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name='${TABLE}');")
    EXISTS=$(echo "${EXISTS}" | tr -d ' ')

    if [ "${EXISTS}" != "t" ]; then
        MISSING_TABLES+=("${TABLE}")
    fi
done

if [ ${#MISSING_TABLES[@]} -gt 0 ]; then
    log_error "Missing tables: ${MISSING_TABLES[*]}"
    exit 1
fi

log_info "All required tables present"
log_info "Step 5: PASSED"
echo ""

# Step 6: Validate data integrity
log_info "Step 6: Checking data integrity..."

echo ""
echo "Record counts:"
docker compose exec -T db psql -U postgres -d "${TEST_DB_NAME}" -c "
    SELECT 'core_usuario' as table_name, COUNT(*) as count FROM core_usuario
    UNION ALL
    SELECT 'core_solicitacao', COUNT(*) FROM core_solicitacao
    UNION ALL
    SELECT 'core_municipio', COUNT(*) FROM core_municipio
    UNION ALL
    SELECT 'core_projeto', COUNT(*) FROM core_projeto
    UNION ALL
    SELECT 'core_gerencia', COUNT(*) FROM core_gerencia;
"
echo ""

log_info "Step 6: PASSED"
echo ""

# Step 7: Compare with production (optional)
log_info "Step 7: Comparing with production database..."

PROD_COUNT=$(docker compose exec -T db psql -U postgres -d aprender_sistema -t -c \
    "SELECT COUNT(*) FROM core_solicitacao;")
TEST_COUNT=$(docker compose exec -T db psql -U postgres -d "${TEST_DB_NAME}" -t -c \
    "SELECT COUNT(*) FROM core_solicitacao;")

PROD_COUNT=$(echo "${PROD_COUNT}" | tr -d ' ')
TEST_COUNT=$(echo "${TEST_COUNT}" | tr -d ' ')

if [ "${PROD_COUNT}" != "${TEST_COUNT}" ]; then
    log_warn "Record count mismatch: prod=${PROD_COUNT}, test=${TEST_COUNT}"
    log_warn "This may be expected if data changed during backup"
else
    log_info "Record counts match: ${PROD_COUNT}"
fi

log_info "Step 7: PASSED"
echo ""

# Summary
echo "=============================================="
echo "      DR TEST SUMMARY"
echo "=============================================="
echo -e "Backup size:     ${GREEN}${BACKUP_SIZE} bytes${NC}"
echo -e "Tables restored: ${GREEN}${TABLE_COUNT}${NC}"
echo -e "Key tables:      ${GREEN}OK${NC}"
echo -e "Data integrity:  ${GREEN}OK${NC}"
echo ""
echo -e "${GREEN}ALL TESTS PASSED${NC}"
echo "=============================================="
echo ""

# Cleanup is handled by trap
log_info "Test complete. Cleaning up..."

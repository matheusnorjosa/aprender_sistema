#!/usr/bin/env bash
# ================================================================
# smoke_test_staging.sh — Staging Gate Smoke Test (Epic #838)
# ================================================================
# 8 checks validating prod-like staging stack health.
# Follows test_dr.sh patterns: colored output, numbered steps, exit codes.
#
# Usage:
#   bash scripts/smoke_test_staging.sh          # from v2/infra/
#   BACKEND_URL=http://localhost:18002 bash ...  # custom URLs
#
# Exit codes:
#   0 - All checks passed
#   1 - One or more checks failed
#   2 - Configuration error
# ================================================================

set -euo pipefail

# ── Paths ────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ── Configuration ────────────────────────────────────────────────
BACKEND_URL="${BACKEND_URL:-http://localhost:18002}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:15173}"
MAX_WAIT="${MAX_WAIT:-120}"
STAGING_TAG="${STAGING_TAG:-staging-local}"

# Python interpreter (Windows has 'python', Linux has 'python3')
PYTHON="${PYTHON:-$(command -v python3 2>/dev/null || command -v python 2>/dev/null || true)}"

# Backend curl: -s silent, -f fail on HTTP errors, X-Forwarded-Proto for SECURE_SSL_REDIRECT
BACKEND_CURL="curl -sf -H X-Forwarded-Proto:https"

# ── Compose helper (anchored to INFRA_DIR) ───────────────────────
compose_cmd() {
  (
    cd "${INFRA_DIR}"
    IMAGE_TAG="${STAGING_TAG}" docker compose \
      --env-file .env.staging \
      -f docker-compose.yml \
      -f docker-compose.staging-gate.yml \
      "$@"
  )
}

# ── Colors ───────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ── State ────────────────────────────────────────────────────────
TOTAL=8
PASSED=0
FAILED=0
CHECK=0
RESULTS=()

# ── Helpers ──────────────────────────────────────────────────────
pass() {
  local label="$1"; shift
  local detail="${1:-}"
  PASSED=$((PASSED + 1))
  CHECK=$((CHECK + 1))
  if [ -n "$detail" ]; then
    RESULTS+=("[${CHECK}/${TOTAL}] ${label}: ${GREEN}PASS${NC} (${detail})")
  else
    RESULTS+=("[${CHECK}/${TOTAL}] ${label}: ${GREEN}PASS${NC}")
  fi
}

fail() {
  local label="$1"; shift
  local detail="${1:-}"
  FAILED=$((FAILED + 1))
  CHECK=$((CHECK + 1))
  if [ -n "$detail" ]; then
    RESULTS+=("[${CHECK}/${TOTAL}] ${label}: ${RED}FAIL${NC} (${detail})")
  else
    RESULTS+=("[${CHECK}/${TOTAL}] ${label}: ${RED}FAIL${NC}")
  fi
}

# Retry helper: retry <max_attempts> <sleep_seconds> <command...>
retry() {
  local max="$1"; shift
  local delay="$1"; shift
  local attempt=1
  while [ "$attempt" -le "$max" ]; do
    if "$@" 2>/dev/null; then
      return 0
    fi
    echo -e "  ${YELLOW}retry ${attempt}/${max}...${NC}"
    sleep "$delay"
    attempt=$((attempt + 1))
  done
  return 1
}

# ── Preflight ────────────────────────────────────────────────────
if [ -z "$PYTHON" ]; then
  echo -e "${RED}ERROR: python3 or python not found in PATH${NC}"
  exit 2
fi

echo "=============================================="
echo "   STAGING GATE SMOKE TEST"
echo "=============================================="
echo "Backend:  ${BACKEND_URL}"
echo "Frontend: ${FRONTEND_URL}"
echo "Tag:      ${STAGING_TAG}"
echo ""

# ── [1/8] Backend readiness ──────────────────────────────────────
echo -n "[1/${TOTAL}] Backend readyz: waiting..."
ELAPSED=0
READY=false
while [ "$ELAPSED" -lt "$MAX_WAIT" ]; do
  BODY="$($BACKEND_CURL "${BACKEND_URL}/api/readyz/" 2>/dev/null || true)"
  if echo "$BODY" | grep -q "healthy"; then
    READY=true
    break
  fi
  sleep 2
  ELAPSED=$((ELAPSED + 2))
  echo -n "."
done
echo ""

if $READY; then
  pass "Backend readyz"
else
  fail "Backend readyz" "not healthy after ${MAX_WAIT}s"
fi

# ── [2/8] Backend version ────────────────────────────────────────
echo -n "[2/${TOTAL}] Backend version: "
VERSION_BODY="$($BACKEND_CURL "${BACKEND_URL}/api/version/" 2>/dev/null || true)"
if [ -n "$VERSION_BODY" ]; then
  APP_VER="$($PYTHON -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('version','unknown'))" <<< "$VERSION_BODY" 2>/dev/null || echo "unknown")"
  GIT_SHA="$($PYTHON -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('git_sha','unknown'))" <<< "$VERSION_BODY" 2>/dev/null || echo "unknown")"
  if [ "$APP_VER" != "unknown" ]; then
    pass "Backend version" "v=${APP_VER}, sha=${GIT_SHA}"
  else
    fail "Backend version" "version=unknown"
  fi
else
  fail "Backend version" "no response"
fi
echo ""

# ── [3/8] CSRF endpoint ─────────────────────────────────────────
echo -n "[3/${TOTAL}] CSRF endpoint: "
CSRF_BODY="$($BACKEND_CURL "${BACKEND_URL}/api/csrf/" 2>/dev/null || true)"
if echo "$CSRF_BODY" | grep -q "csrfToken"; then
  pass "CSRF endpoint"
else
  fail "CSRF endpoint" "csrfToken not found"
fi
echo ""

# ── [4/8] Auth pipeline ─────────────────────────────────────────
# NOTE: Does NOT use BACKEND_CURL (-f would fail on 4xx).
# We expect Django to process the request and return 4xx (not 301 redirect).
echo -n "[4/${TOTAL}] Auth pipeline: "
AUTH_CODE="$(curl -sS -o /dev/null -w '%{http_code}' \
  -H 'X-Forwarded-Proto: https' \
  -X POST "${BACKEND_URL}/api/auth/login/" \
  -H 'Content-Type: application/json' -d '{}' 2>/dev/null || echo "000")"
if [ "$AUTH_CODE" -ge 400 ] 2>/dev/null && [ "$AUTH_CODE" -lt 500 ] 2>/dev/null; then
  pass "Auth pipeline" "HTTP ${AUTH_CODE}"
else
  fail "Auth pipeline" "HTTP ${AUTH_CODE} (expected 4xx)"
fi
echo ""

# ── [5/8] Celery worker ─────────────────────────────────────────
echo -n "[5/${TOTAL}] Celery worker: "
worker_ping() {
  # Avoid pipefail + grep -q SIGPIPE false negatives by checking buffered output.
  local output
  output="$(compose_cmd exec -T worker celery -A config inspect ping --timeout=10 2>/dev/null)" || return 1
  [[ "$output" == *"pong"* ]]
}
if retry 12 5 worker_ping; then
  pass "Celery worker"
else
  fail "Celery worker" "no pong after 12 attempts"
fi
echo ""

# ── [6/8] Celery beat ───────────────────────────────────────────
echo -n "[6/${TOTAL}] Celery beat: "
beat_check() {
  # Container must be running
  compose_cmd ps --status running beat 2>/dev/null | grep -q "beat" || return 1
  # Process must be active (host-side inspection via compose top)
  compose_cmd top beat 2>/dev/null | grep -qE "celery.*beat|celery -A config beat" || return 1
  return 0
}
if retry 12 5 beat_check; then
  pass "Celery beat"
  # Complementary: show beat log tail as evidence
  echo "  (beat logs):"
  compose_cmd logs --tail=3 beat 2>/dev/null | sed 's/^/    /' || true
else
  fail "Celery beat" "not running after 12 attempts"
fi
echo ""

# ── [7/8] Frontend HTTP ─────────────────────────────────────────
echo -n "[7/${TOTAL}] Frontend HTTP: "
FE_BODY="$(curl -sf "${FRONTEND_URL}/" 2>/dev/null || true)"
if echo "$FE_BODY" | grep -q '<div id="root"'; then
  pass "Frontend HTTP"
else
  fail "Frontend HTTP" "root div not found"
fi
echo ""

# ── [8/8] Frontend health ────────────────────────────────────────
echo -n "[8/${TOTAL}] Frontend health: "
FE_HEALTH="$(curl -sf -o /dev/null -w '%{http_code}' "${FRONTEND_URL}/health" 2>/dev/null || echo "000")"
if [ "$FE_HEALTH" = "200" ]; then
  pass "Frontend health"
else
  fail "Frontend health" "HTTP ${FE_HEALTH}"
fi
echo ""

# ── Results ──────────────────────────────────────────────────────
echo ""
echo "=============================================="
echo "   STAGING GATE SMOKE TEST RESULTS"
echo "=============================================="
for LINE in "${RESULTS[@]}"; do
  echo -e "$LINE"
done
echo ""

if [ "$FAILED" -eq 0 ]; then
  echo -e "${GREEN}ALL ${TOTAL} CHECKS PASSED${NC}"
  echo "=============================================="
  exit 0
else
  echo -e "${RED}${FAILED}/${TOTAL} CHECKS FAILED${NC}"
  echo "=============================================="
  exit 1
fi

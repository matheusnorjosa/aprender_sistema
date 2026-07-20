#!/usr/bin/env bash
# staging-gate.sh — roda o staging gate local (build imagens prod + up + migrate + smoke)
# e, opcionalmente, atualiza um PR com os 3 marcadores + evidencia e marca Ready.
#
# ISOLADO POR SLOT (#1581): projeto Compose, tag de imagem e portas de host sao derivados
# de um numero de slot — igual ao stack de dev (worktree-env.sh, #1559/#1576). Dois gates
# em slots diferentes rodam em PARALELO sem se atropelar (projetos/portas/tags distintos) e
# o `down -v` de um NAO destroi a stack do outro. Slot 0 (default) mantem o comportamento
# historico: projeto aprender_staging, tag staging-local, portas 18002/15173/15434/16380.
#
# Resolucao do slot (primeiro que existir): --slot N > env DEV_SLOT > arquivo `.dev-slot`
# na raiz do worktree > 0. Reutiliza o MESMO `.dev-slot` do stack de dev, entao um worktree
# ja marcado com `echo 1 > .dev-slot` isola o gate automaticamente (sem sourcing).
#
# Substitui o copia-e-cola manual do gate. Equivale a `make staging-full` (que quebra
# no Windows GnuWin32 por causa do $(MAKE) recursivo) + a colagem dos marcadores.
#
# Uso:
#   v2/infra/scripts/staging-gate.sh                  # so roda o gate; imprime resultado
#   v2/infra/scripts/staging-gate.sh --slot 2         # forca slot 2 (projeto/portas/tag do slot 2)
#   v2/infra/scripts/staging-gate.sh --print-config   # imprime a config derivada e sai (nao toca Docker)
#   v2/infra/scripts/staging-gate.sh --pr 1494        # roda o gate; se 8/8, atualiza PR #1494 + marca Ready
#   v2/infra/scripts/staging-gate.sh --pr 1494 --no-ready   # atualiza o body mas NAO marca Ready
#   v2/infra/scripts/staging-gate.sh --keep           # nao derruba a stack no fim (debug)
#
# Pre-requisitos: Docker rodando; estar no commit/branch que vai virar a imagem
# (GIT_SHA = HEAD); para --pr, `gh` autenticado.
#
# NUNCA faz merge. Desde o cutover do ADR-018 (#1530) o merge na main TAMBEM NAO
# DEPLOYA: o job `deploy` do deploy.yaml esta `if: false`. O merge so faz build+sign.
# Prod muda quando alguem roda `promote.yml` (gated no Environment `production`) e o
# agente aprender-deployer, na VM01, pega o ponteiro assinado e aplica por digest.
#
# Exit codes: 0 ok | 2 precheck | 3 build backend | 4 build frontend | 5 up | 6 migrate
#             | 7 smoke falhou | 8 sem gh | 9 PR nao encontrado | 10 gh edit falhou
#             | 11 outro gate no mesmo slot em curso | 64 arg invalido
set -uo pipefail

PR=""
DO_READY=1
KEEP=0
SLOT_ARG=""
PRINT_CONFIG=0
while [ $# -gt 0 ]; do
  case "$1" in
    --pr)           PR="${2:-}"; shift 2;;
    --pr=*)         PR="${1#*=}"; shift;;
    --slot)         SLOT_ARG="${2:-}"; shift 2;;
    --slot=*)       SLOT_ARG="${1#*=}"; shift;;
    --no-ready)     DO_READY=0; shift;;
    --keep)         KEEP=1; shift;;
    --print-config) PRINT_CONFIG=1; shift;;
    -h|--help)  tail -n +2 "$0" | grep '^#' | sed 's/^#\{1,\} \{0,1\}//; s/^#//'; exit 0;;
    *) echo "arg desconhecido: $1 (use --help)" >&2; exit 64;;
  esac
done

# Resolve v2/infra a partir da localizacao do script (funciona de qualquer cwd).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"   # v2/infra
cd "$INFRA_DIR" || { echo "nao consegui cd para $INFRA_DIR" >&2; exit 1; }

# ---------- resolve slot + deriva projeto/tag/portas (isolamento #1581) ----------
SLOT="$SLOT_ARG"
[ -z "$SLOT" ] && SLOT="${DEV_SLOT:-}"
if [ -z "$SLOT" ]; then
  WT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
  [ -n "$WT_ROOT" ] && [ -f "$WT_ROOT/.dev-slot" ] && SLOT="$(tr -d '[:space:]' < "$WT_ROOT/.dev-slot")"
fi
SLOT="${SLOT:-0}"
case "$SLOT" in ''|*[!0-9]*) echo "slot invalido '$SLOT' (use inteiro >= 0)" >&2; exit 64;; esac

if [ "$SLOT" = "0" ]; then
  PROJECT_STAGING="aprender_staging"
  TAG="staging-local"
else
  PROJECT_STAGING="aprender_staging_s${SLOT}"
  TAG="staging-local-s${SLOT}"
fi
# Portas de host por slot (offset +10, como no worktree-env.sh). Base = .env.staging.
STAGING_BACKEND_PORT=$((18002 + SLOT * 10))
STAGING_DB_PORT=$((15434 + SLOT * 10))
STAGING_REDIS_PORT=$((16380 + SLOT * 10))
STAGING_FRONTEND_PORT=$((15173 + SLOT * 10))

BACKEND_IMG="norjosamatheus/aprender-backend:$TAG"
FRONTEND_IMG="norjosamatheus/aprender-frontend:$TAG"

if [ "$PRINT_CONFIG" -eq 1 ]; then
  echo "slot=$SLOT"
  echo "project=$PROJECT_STAGING"
  echo "tag=$TAG"
  echo "backend_image=$BACKEND_IMG"
  echo "frontend_image=$FRONTEND_IMG"
  echo "backend_port=$STAGING_BACKEND_PORT"
  echo "db_port=$STAGING_DB_PORT"
  echo "redis_port=$STAGING_REDIS_PORT"
  echo "frontend_port=$STAGING_FRONTEND_PORT"
  exit 0
fi

# Helper Compose: -p explicito + portas/tag inline. As vars inline vencem o --env-file
# (.env.staging) E qualquer BACKEND_HOST_PORT/etc herdado do worktree-env.sh de dev
# (provado: var inline > --env-file na interpolacao do Compose).
GATE() {
  COMPOSE_PROJECT_NAME="$PROJECT_STAGING" \
  IMAGE_TAG="$TAG" \
  BACKEND_HOST_PORT="$STAGING_BACKEND_PORT" \
  DB_HOST_PORT="$STAGING_DB_PORT" \
  REDIS_HOST_PORT="$STAGING_REDIS_PORT" \
  FRONTEND_HOST_PORT="$STAGING_FRONTEND_PORT" \
  docker compose -p "$PROJECT_STAGING" --env-file .env.staging \
    -f docker-compose.yml -f docker-compose.staging-gate.yml "$@"
}

# ---------- lock por slot (defesa contra dois gates no MESMO slot por engano) ----------
LOCK_DIR="${TMPDIR:-/tmp}/aprender-staging-gate-${PROJECT_STAGING}.lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "[gate] FALHOU: ja existe um gate rodando no slot ${SLOT} (lock: $LOCK_DIR)." >&2
  echo "[gate]   use outro slot (--slot N) ou, se tiver certeza que nada roda, remova: rmdir '$LOCK_DIR'" >&2
  exit 11
fi

teardown() {
  rmdir "$LOCK_DIR" 2>/dev/null || true
  if [ "$KEEP" -eq 1 ]; then
    echo "[gate] --keep: stack (slot $SLOT / $PROJECT_STAGING) mantida. Para derrubar:"
    echo "       docker compose -p $PROJECT_STAGING --env-file .env.staging -f docker-compose.yml -f docker-compose.staging-gate.yml down -v"
    return
  fi
  echo "[gate] teardown (down -v, projeto $PROJECT_STAGING)..."
  GATE down -v >/dev/null 2>&1 || true
}
trap teardown EXIT

LOG="$(mktemp)"
fail() { echo "[gate] FALHOU: $1" >&2; exit "${2:-1}"; }

echo "==> [gate] slot=$SLOT | projeto=$PROJECT_STAGING | tag=$TAG | backend :$STAGING_BACKEND_PORT | frontend :$STAGING_FRONTEND_PORT"

[ -f .env.staging ] || fail ".env.staging nao encontrado em $INFRA_DIR — crie a partir do template: cp .env.staging.example .env.staging" 2

echo "==> [1/5] precheck (compose valido / !reset suportado)"
GATE config >/dev/null 2>&1 || fail "precheck (atualize Docker Compose >= 2.24.6 p/ !reset)" 2

echo "==> [2/5] build backend prod ($BACKEND_IMG)"
docker build -f Dockerfile.prod \
  --build-arg GIT_SHA="$(git rev-parse --short HEAD)" \
  --build-arg BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --build-arg APP_VERSION="$TAG" \
  -t "$BACKEND_IMG" .. || fail "build backend" 3

echo "==> [3/5] build frontend prod ($FRONTEND_IMG)"
docker build -f ../frontend/Dockerfile.prod \
  --build-arg GIT_SHA="$(git rev-parse --short HEAD)" \
  -t "$FRONTEND_IMG" ../frontend || fail "build frontend" 4

echo "==> [4/5] up + migrate"
GATE up -d --no-build || fail "up" 5
GATE run --rm web python manage.py migrate --noinput || fail "migrate" 6

echo "==> [5/5] smoke (8 checks)"
BACKEND_URL="http://localhost:${STAGING_BACKEND_PORT}" \
FRONTEND_URL="http://localhost:${STAGING_FRONTEND_PORT}" \
STAGING_TAG="$TAG" \
STAGING_PROJECT="$PROJECT_STAGING" \
PYTHON=python bash scripts/smoke_test_staging.sh | tee "$LOG"
SMOKE=${PIPESTATUS[0]}

if [ "$SMOKE" -ne 0 ] || ! grep -q "ALL 8 CHECKS PASSED" "$LOG"; then
  fail "smoke NAO passou (exit=$SMOKE) — PR nao sera tocado" 7
fi
echo "[gate] ✅ ALL 8 CHECKS PASSED"

# ---------- atualizar PR (opcional) ----------
if [ -z "$PR" ]; then
  echo "[gate] sem --pr: gate verde, nada a atualizar."
  exit 0
fi

command -v gh >/dev/null 2>&1 || fail "gh (GitHub CLI) nao encontrado / nao no PATH" 8

# Evidencia = bloco de resultados do smoke, sem codigos ANSI.
EVID="$(sed 's/\x1b\[[0-9;]*m//g' "$LOG" | awk '/STAGING GATE SMOKE TEST RESULTS/{c=1} c{print} /ALL 8 CHECKS PASSED/{exit}')"
SHA="$(git rev-parse --short HEAD)"
SENTINEL="<!-- staging-gate-auto -->"

# Body atual SEM o bloco auto anterior (idempotente em re-runs).
CUR="$(gh pr view "$PR" --json body -q .body 2>/dev/null)" || fail "PR #$PR nao encontrado (gh autenticado?)" 9
BASE="$(printf '%s\n' "$CUR" | awk -v s="$SENTINEL" 'index($0,s){exit} {print}')"

NEWBODY="$(mktemp)"
{
  printf '%s\n' "$BASE"
  printf '%s\n' "$SENTINEL"
  echo "## Staging gate"
  echo
  echo "- [x] make staging-full executado com sucesso (8/8 PASS)"
  echo "- [x] Evidencia anexada no PR"
  echo
  echo "Evidencia (gate local, commit \`$SHA\`, slot \`$SLOT\` / projeto \`$PROJECT_STAGING\`):"
  echo
  echo '```'
  printf '%s\n' "$EVID"
  echo '```'
} > "$NEWBODY"

gh pr edit "$PR" --body-file "$NEWBODY" >/dev/null || { rm -f "$NEWBODY"; fail "gh pr edit" 10; }
rm -f "$NEWBODY"
echo "[gate] ✅ body do PR #$PR atualizado (3 marcadores + evidencia)"

if [ "$DO_READY" -eq 1 ]; then
  if gh pr ready "$PR" >/dev/null 2>&1; then echo "[gate] ✅ PR #$PR marcado Ready"; else echo "[gate] PR #$PR ja estava Ready (ou nada a mudar)"; fi
fi

echo "[gate] pronto. Merge final (squash) e MANUAL. O merge NAO deploya (ADR-018): so build+sign."
echo "[gate] para levar a prod: gh workflow run promote.yml -f release=<tag>  (gate 'production' pede aprovacao)."

# shellcheck shell=bash
# lib/common.sh — setup compartilhado do agente aprender-deployer (ADR-018 Fase 1).
#
# Sourced pelos entrypoints (reconcile.sh do deployer, apply.sh do applier).
# NAO executar direto. Define paths, binarios (caminho absoluto, hash-checados no
# install.sh), diretorios de runtime/estado, carrega as ancoras de identidade
# (trust/identity.env) e faz o source das demais libs.
#
# Convencao: as libs sao funcoes puras; quem define `set -euo pipefail` e o entrypoint.
# Tudo overridavel por env para os testes bats (mock de cosign/gh/curl/jq e fixtures).

# Raiz do agente (.../current). lib/ vive sob a raiz.
: "${DEPLOYER_HOME:=$(unset CDPATH; cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)}"
TRUST_DIR="${TRUST_DIR:-${DEPLOYER_HOME}/trust}"

# Binarios por caminho absoluto (validados por hash em bootstrap/install.sh).
: "${JQ_BIN:=/usr/bin/jq}"
: "${CURL_BIN:=/usr/bin/curl}"
: "${COSIGN_BIN:=/usr/local/bin/cosign}"
: "${GH_BIN:=/usr/local/bin/gh}"
: "${SHA256_BIN:=/usr/bin/sha256sum}"
: "${FLOCK_BIN:=/usr/bin/flock}"

# Diretorios de runtime/estado (systemd RuntimeDirectory/StateDirectory).
: "${RUN_DIR:=/run/aprender-deployer}"
: "${STATE_DIR:=/var/lib/aprender-deployer}"
: "${APPLIER_STATE_DIR:=/var/lib/aprender-applier}"
: "${HANDOFF_DIR:=${RUN_DIR}/handoff}"

# Ancoras de confianca versionadas em trust/ (tratadas como CODIGO, nao config).
# identity.env define: OIDC_ISSUER, POINTER_IDENTITY_RE, IMAGE_IDENTITY_RE,
# SIGNER_WORKFLOW, GH_REPO, BACKEND_REPO, FRONTEND_REPO, SIGSTORE_ROOT.
if [ -r "${TRUST_DIR}/identity.env" ]; then
  # shellcheck source=../trust/identity.env disable=SC1091
  . "${TRUST_DIR}/identity.env"
fi
: "${SIGSTORE_ROOT:=${TRUST_DIR}/sigstore-root.json}"
: "${COMPOSE_PINNED:=${TRUST_DIR}/compose.pinned.yml}"

# Valida presenca dos binarios essenciais (fail-closed).
common_require_bins() {
  local b
  for b in "$JQ_BIN" "$CURL_BIN"; do
    [ -x "$b" ] || { printf 'FATAL: binario ausente/nao-executavel: %s\n' "$b" >&2; return 3; }
  done
}

# Escrita atomica (temp no mesmo dir + mv). Uso: common_write_atomic <arquivo> < conteudo
common_write_atomic() {
  local dest="$1" tmp
  tmp="$(mktemp "${dest}.XXXXXX")" || return 1
  cat > "$tmp" || { rm -f "$tmp"; return 1; }
  mv -f "$tmp" "$dest"
}

# Source das demais libs (log primeiro — todas dependem dele).
for _lib in log notify state seal fetch pointer verify_image portainer compose confirm backup; do
  # shellcheck source=/dev/null
  . "${DEPLOYER_HOME}/lib/${_lib}.sh"
done
unset _lib

# tests/helper.bash — sandbox + mocks para os testes bats do aprender-deployer.
# shellcheck shell=bash

deployer_src() { CDPATH= cd -- "${BATS_TEST_DIRNAME}/.." && pwd -P; }

_mk() { printf '%s\n' "$2" > "$1"; chmod +x "$1"; }

# setup_sandbox — cria o sandbox, mocks de cosign/gh, trust/ e faz o source das libs.
setup_sandbox() {
  SANDBOX="$(mktemp -d)"; export SANDBOX
  export DEPLOYER_HOME; DEPLOYER_HOME="$(deployer_src)"

  export JQ_BIN;     JQ_BIN="$(command -v jq)"
  export CURL_BIN;   CURL_BIN="$(command -v curl)"
  export SHA256_BIN; SHA256_BIN="$(command -v sha256sum)"
  export FLOCK_BIN;  FLOCK_BIN="$(command -v flock)"

  _mk "$SANDBOX/cosign" '#!/usr/bin/env bash
exit "${MOCK_COSIGN_RC:-0}"'
  _mk "$SANDBOX/gh" '#!/usr/bin/env bash
exit "${MOCK_GH_RC:-0}"'
  export COSIGN_BIN="$SANDBOX/cosign" GH_BIN="$SANDBOX/gh"

  export RUN_DIR="$SANDBOX/run" STATE_DIR="$SANDBOX/state" APPLIER_STATE_DIR="$SANDBOX/applier"
  export HANDOFF_DIR="$RUN_DIR/handoff"
  mkdir -p "$RUN_DIR" "$STATE_DIR" "$APPLIER_STATE_DIR/seal" "$HANDOFF_DIR"

  export TRUST_DIR="$SANDBOX/trust"; mkdir -p "$TRUST_DIR"
  cp "$DEPLOYER_HOME/trust/identity.env" "$TRUST_DIR/identity.env"
  export SIGSTORE_ROOT="$TRUST_DIR/sigstore-root.json"; printf '{}' > "$SIGSTORE_ROOT"
  export COMPOSE_PINNED="$TRUST_DIR/compose.pinned.yml"; printf 'PINNEDCOMPOSE' > "$COMPOSE_PINNED"

  export PROD_HOST="test.local" BACKEND_HOST_PORT="8000" NOTIFY_URL=""

  # source do common (que faz o source de todas as libs), mantendo nossos overrides.
  # shellcheck source=../lib/common.sh
  . "$DEPLOYER_HOME/lib/common.sh"
}

teardown_sandbox() { [ -n "${SANDBOX:-}" ] && rm -rf "$SANDBOX"; }

# write_pointer <dest> [sequence] [expires_at]
write_pointer() {
  local dest="$1" seq="${2:-5}" exp="${3:-2999-01-01T00:00:00Z}"
  local a b; a="$(printf 'a%.0s' $(seq 1 64))"; b="$(printf 'b%.0s' $(seq 1 64))"
  cat > "$dest" <<JSON
{ "schema":1, "sequence":${seq}, "release":"v2026.07.08-abc1234",
  "backend": {"repo":"norjosamatheus/aprender-backend","digest":"sha256:${a}"},
  "frontend":{"repo":"norjosamatheus/aprender-frontend","digest":"sha256:${b}"},
  "rollback":false, "issued_at":"2026-07-08T00:00:00Z", "expires_at":"${exp}",
  "promoted_by":"promote.yml", "commit":"abc1234" }
JSON
}

# seed_seal <value>
seed_seal() { printf '%s' "$1" > "${APPLIER_STATE_DIR}/seal/last_sequence"; }

# install_mock_curl — CURL_BIN vira um mock que serve fixtures do Portainer/ponteiro.
# Vars: MOCK_POINTER, MOCK_SIG (arquivos), MOCK_STACK, MOCK_STACKFILE, MOCK_RELEASE (strings).
#
# Modelagem do PUT real (ADR-018 3e), para exercitar o confirm pos-PUT:
#   MOCK_PUT_CODE          http_code devolvido pelo PUT (default 200; use 000 = false-red)
#   MOCK_ENV_COMMIT_DELAY  N primeiras releituras pos-PUT ainda veem o Env ANTIGO
#   MOCK_STACK_READ_FAIL   N primeiras releituras pos-PUT falham (API ocupada no recreate)
install_mock_curl() {
  _mk "$SANDBOX/mock_curl" '#!/usr/bin/env bash
# mock stateful: apos um PUT, o GET da stack passa a devolver MOCK_STACK_AFTER
# (reflete o digest recem-aplicado, para o confirm pos-PUT passar).
url=""; out=""; method=GET; want_code=0; prev=""
for a in "$@"; do
  case "$prev" in -o) out="$a";; -X) method="$a";; esac
  case "$a" in http://*|https://*|file://*) url="$a";; -w) want_code=1;; esac
  prev="$a"
done
case "$url" in
  *auth.docker.io*|*registry-1.docker.io*) exit 1 ;;            # advisory: falha -> skip
  *.sigstore.json*) cp "$MOCK_SIG" "$out"; exit 0 ;;
  *production.json*) cp "$MOCK_POINTER" "$out"; exit 0 ;;
  */api/stacks/*/file) printf "%s" "$MOCK_STACKFILE"; exit 0 ;;
  */api/stacks/*)
     if [ "$method" = PUT ]; then
       touch "$MOCK_STATE_DIR/put_done"
       [ "$want_code" = 1 ] && printf "%s" "${MOCK_PUT_CODE:-200}"
       exit 0
     fi
     # GET da stack. Antes do PUT (ou sem fixture "depois") serve sempre o Env atual.
     if [ ! -f "$MOCK_STATE_DIR/put_done" ] || [ -z "${MOCK_STACK_AFTER:-}" ]; then
       printf "%s" "$MOCK_STACK"; exit 0
     fi
     # Releituras pos-PUT: contam para simular atraso de commit / API indisponivel.
     n=$(cat "$MOCK_STATE_DIR/reread_n" 2>/dev/null || printf 0)
     n=$((n + 1)); printf "%s" "$n" > "$MOCK_STATE_DIR/reread_n"
     [ "$n" -le "${MOCK_STACK_READ_FAIL:-0}" ] && exit 7
     [ "$n" -le "${MOCK_ENV_COMMIT_DELAY:-0}" ] && { printf "%s" "$MOCK_STACK"; exit 0; }
     printf "%s" "$MOCK_STACK_AFTER"; exit 0 ;;
  *readyz*)  [ "$want_code" = 1 ] && printf "200"; exit 0 ;;
  *version*) printf "{\"version\":\"%s\"}" "$MOCK_RELEASE"; exit 0 ;;
esac
exit 1'
  export CURL_BIN="$SANDBOX/mock_curl"
  export MOCK_STATE_DIR="$SANDBOX"
  export PORTAINER_CURLRC="$SANDBOX/curlrc"; printf 'header = "X-API-KEY: ptr_test"\n' > "$PORTAINER_CURLRC"
  export PORTAINER_BASE="https://127.0.0.1:9443" PORTAINER_STACK_ID="7" PORTAINER_ENDPOINT_ID="3"
  export POINTER_URL="https://raw.githubusercontent.com/matheusnorjosa/aprender_sistema/deploy-pointer/production.json"
  export POINTER_SIG_URL="https://raw.githubusercontent.com/matheusnorjosa/aprender_sistema/deploy-pointer/production.json.sigstore.json"
}

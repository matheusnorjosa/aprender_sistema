# shellcheck shell=bash
# lib/portainer.sh — cliente Portainer CE (SO o applier usa; detem o token).
#
# Token via `-K curlrc` (0400 applier) — NUNCA -H "X-API-KEY: $t" (cairia em
# /proc/<pid>/cmdline, world-readable). Espelha a API do deploy.yaml atual:
#   GET  /api/stacks/{id}          -> .Env
#   GET  /api/stacks/{id}/file     -> .StackFileContent
#   PUT  /api/stacks/{id}?endpointId={n}  {StackFileContent,Env,Prune,RepullImageAndRedeploy}

: "${PORTAINER_CURLRC:=/etc/aprender-deployer/portainer.curlrc}"

_portainer_curl() {
  "$CURL_BIN" -sS -K "$PORTAINER_CURLRC" \
    --max-time "${PORTAINER_MAX_TIME:-30}" --retry 2 --retry-connrefused "$@"
}

portainer_get_stack() {
  _portainer_curl "${PORTAINER_BASE}/api/stacks/${PORTAINER_STACK_ID}"
}

portainer_get_file() {
  _portainer_curl "${PORTAINER_BASE}/api/stacks/${PORTAINER_STACK_ID}/file"
}

# portainer_env_value <stack_json> <name> -> imprime o value do Env (ou "").
portainer_env_value() {
  local json="$1" name="$2"
  "$JQ_BIN" -r --arg n "$name" '([.Env[]?|select(.name==$n)|.value]|first)//""' <<<"$json"
}

# portainer_put <payload_file> -> dispara o PUT com retry.
# 2xx=ok; 000=timeout (o PUT pode ter chegado: false-red do :9443) => deixa o
# chamador CONFIRMAR relendo o Env; 5xx=retry; 4xx=falha dura.
portainer_put() {
  local payload_file="$1" attempt http
  local max="${PORTAINER_PUT_ATTEMPTS:-3}"
  for attempt in $(seq 1 "$max"); do
    http="$(_portainer_curl -o /dev/null -w '%{http_code}' \
        -X PUT -H 'Content-Type: application/json' \
        --data-binary @"$payload_file" \
        "${PORTAINER_BASE}/api/stacks/${PORTAINER_STACK_ID}?endpointId=${PORTAINER_ENDPOINT_ID}" \
        2>/dev/null || true)"
    log_info "portainer_put" "attempt=${attempt}" "http=${http}"
    case "$http" in
      2*)  return 0 ;;
      000) log_warn "portainer_put_timeout" "attempt=${attempt}"; return 0 ;;
      5*)  sleep "${PORTAINER_PUT_BACKOFF:-10}" ;;
      *)   log_error "portainer_put_http" "http=${http}"; return 1 ;;
    esac
  done
  return 0
}

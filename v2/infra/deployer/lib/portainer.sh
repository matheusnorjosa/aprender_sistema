# shellcheck shell=bash
# lib/portainer.sh — cliente Portainer CE (SO o applier usa; detem o token).
#
# Token via `-K curlrc` (0400 applier) — NUNCA -H "X-API-KEY: $t" (cairia em
# /proc/<pid>/cmdline, world-readable). Espelha a API do deploy.yaml atual:
#   GET  /api/stacks/{id}          -> .Env
#   GET  /api/stacks/{id}/file     -> .StackFileContent
#   PUT  /api/stacks/{id}?endpointId={n}  {StackFileContent,Env,Prune,RepullImageAndRedeploy}
#   GET    /api/endpoints/{n}/docker/images/json   -> lista de imagens (GC, lib/gc.sh)
#   DELETE /api/endpoints/{n}/docker/images/{id}   -> remove imagem (GC, force=false)

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

# portainer_wait_env_digest <backend_digest> <frontend_digest> -> 0 quando o Env da
# stack refletir os digests que o PUT enviou; !=0 se nao refletir dentro do orcamento.
#
# Por que POLL e nao uma releitura unica: o `portainer_put` acima devolve 0 no 000
# justamente porque o PUT pode ter chegado (false-red do :9443) — cabe ao chamador
# CONFIRMAR. Mas o Portainer nao commita o Env instantaneamente e, durante o recreate
# dos containers, a propria API fica indisponivel por alguns segundos. Ler uma unica
# vez, no instante seguinte ao PUT, reprova um deploy que deu certo e ainda arma o
# breaker (bug pego na 1a promocao real, ADR-018 3e).
#
# Confere os DOIS digests: convergencia parcial (so backend) nao e convergencia.
# Fail-closed — sem confirmacao, o chamador nao sela.
portainer_wait_env_digest() {
  local want_be="$1" want_fe="$2"
  local timeout="${PUT_CONFIRM_TIMEOUT:-180}" interval="${PUT_CONFIRM_INTERVAL:-5}"
  local deadline attempt=0 stack="" be="" fe=""
  deadline=$(( $(date +%s) + timeout ))
  while :; do
    attempt=$(( attempt + 1 ))
    if stack="$(portainer_get_stack)"; then
      be="$(portainer_env_value "$stack" "BACKEND_DIGEST")"
      fe="$(portainer_env_value "$stack" "FRONTEND_DIGEST")"
      if [ "$be" = "$want_be" ] && [ "$fe" = "$want_fe" ]; then
        log_info "put_confirmed_env" "attempt=${attempt}"
        return 0
      fi
      log_warn "put_env_pending" "attempt=${attempt}"
    else
      log_warn "put_confirm_read_failed" "attempt=${attempt}"   # API ocupada no recreate
    fi
    [ "$(date +%s)" -lt "$deadline" ] || break
    sleep "$interval"
  done
  log_error "put_unconfirmed_env" "attempts=${attempt}" \
      "want_backend=${want_be}"   "last_backend=${be}" \
      "want_frontend=${want_fe}"  "last_frontend=${fe}"
  return 1
}

# --- GC de imagens (Docker Engine API via proxy do Portainer; usado por lib/gc.sh) ---
# O mesmo token do applier proxya a Docker API sob /api/endpoints/{id}/docker/*. Requer
# que a chave tenha permissao de imagem no endpoint; sem ela o list/delete devolve 4xx
# e o GC apenas no-opa (best-effort, nao afeta o deploy).

# portainer_list_images -> imprime o JSON array das imagens do endpoint.
portainer_list_images() {
  _portainer_curl "${PORTAINER_BASE}/api/endpoints/${PORTAINER_ENDPOINT_ID}/docker/images/json"
}

# portainer_delete_image <ref> -> imprime o http_code do DELETE.
# <ref> = uma REFERENCIA (repo:tag ou repo@sha256:...), nunca o Id nu: por Id o Docker
# recusa (409) imagens com >1 referencia (o pin repo:tag@digest gera duas). Por referencia
# ele desreferencia; a imagem sai quando a ultima referencia sai.
# force=false: fail-safe — o Docker recusa (409) o delete final de uma imagem em uso.
# noprune=false: remove tambem as camadas-pai orfas (recupera mais espaco).
portainer_delete_image() {
  local ref="$1"
  _portainer_curl -o /dev/null -w '%{http_code}' -X DELETE \
    "${PORTAINER_BASE}/api/endpoints/${PORTAINER_ENDPOINT_ID}/docker/images/${ref}?force=false&noprune=false"
}

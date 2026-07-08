# shellcheck shell=bash
# lib/compose.sh — integridade da topologia + montagem do payload por DIGEST.
#
# ELO 4: o compose vivo na stack tem de bater byte-a-byte com o compose PINADO
# do agente (trust/compose.pinned.yml). Divergencia => REFUSE (tamper/drift).
# E o applier SEMPRE reenvia o PINADO, nunca o texto vindo da rede (fecha injecao
# de compose via StackFileContent). Deploy por digest = Opcao B do blueprint:
# o compose referencia repo:${IMAGE_TAG}@${DIGEST:?}; o agente so troca valores no Env.

compose_pinned_sha() { "$SHA256_BIN" < "$COMPOSE_PINNED" | awk '{print $1}'; }

# compose_live_sha <stack_file_json> -> sha256 do .StackFileContent.
# `jq -j` (NAO -r): -r acrescenta um \n que nunca bateria com os bytes do arquivo
# pinado. Com -j o hash e byte-a-byte identico ao compose.pinned.yml capturado no
# bootstrap com o mesmo `jq -j`.
compose_live_sha() {
  "$JQ_BIN" -j '.StackFileContent // ""' <<<"$1" | "$SHA256_BIN" | awk '{print $1}'
}

# compose_check_drift <stack_file_json> -> 0 se live==pinned; !=0 se divergir/faltar.
compose_check_drift() {
  local file_json="$1" live pinned
  [ -r "$COMPOSE_PINNED" ] || { log_error "compose_pinned_missing"; return 1; }
  live="$(compose_live_sha "$file_json")"   || return 1
  pinned="$(compose_pinned_sha)"            || return 1
  [ -n "$live" ] && [ "$live" = "$pinned" ] \
    || { log_error "compose_drift" "live=${live}" "pinned=${pinned}"; return 1; }
  return 0
}

# compose_build_env <stack_json> <release> <be_digest> <fe_digest> -> novo array Env (json).
compose_build_env() {
  local stack_json="$1" release="$2" be="$3" fe="$4"
  "$JQ_BIN" -c --arg t "$release" --arg bd "$be" --arg fd "$fe" '
    (.Env // [])
    | map(select(.name | IN("IMAGE_TAG","BACKEND_DIGEST","FRONTEND_DIGEST") | not))
    + [ {name:"IMAGE_TAG",value:$t},
        {name:"BACKEND_DIGEST",value:$bd},
        {name:"FRONTEND_DIGEST",value:$fd} ]
  ' <<<"$stack_json"
}

# compose_build_payload <new_env_json> -> imprime o payload PUT (com o compose PINADO).
compose_build_payload() {
  local new_env="$1" compose
  compose="$(cat "$COMPOSE_PINNED" 2>/dev/null)" || return 1
  "$JQ_BIN" -n --arg f "$compose" --argjson e "$new_env" \
    '{StackFileContent:$f, Env:$e, Prune:false, RepullImageAndRedeploy:true}'
}

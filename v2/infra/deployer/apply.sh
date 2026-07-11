#!/usr/bin/env bash
# apply.sh — entrypoint do APPLIER (usuario aprender-applier; detem token+compose+selo).
#
# Ativado pelo .path quando o deployer escreve o handoff. RE-VERIFICA tudo a
# partir dos bytes (um deployer comprometido nao fabrica ponteiro valido), aplica
# anti-rollback selado, confere a topologia (compose vivo == pinado), exige backup
# fresco, faz o PUT do compose PINADO por digest, confirma em localhost e SELA a
# sequence. Fail-closed. Sem auto-rollback (migrate e forward-only).
#
# ADR-018 Fase 1 · issue #1513 · blueprint §C.2
set -euo pipefail

export LOG_COMPONENT=applier
DEPLOYER_HOME="$(unset CDPATH; cd -- "$(dirname -- "$0")" && pwd -P)"
export DEPLOYER_HOME
# shellcheck source=lib/common.sh
. "${DEPLOYER_HOME}/lib/common.sh"

# --- circuit breaker (nao repetir PUT de uma release ruim) + ref de rollback ---
_breaker_file()  { printf '%s/breaker/%s' "$APPLIER_STATE_DIR" "$1"; }
_breaker_count() {
  local f n; f="$(_breaker_file "$1")"
  n="$(cat "$f" 2>/dev/null || true)"
  case "$n" in ''|*[!0-9]*) n=0 ;; esac
  printf '%s' "$n"
}
_breaker_inc() {
  local f n; f="$(_breaker_file "$1")"; mkdir -p "$(dirname "$f")" 2>/dev/null || true
  n="$(_breaker_count "$1")"; printf '%s' "$((n+1))" | common_write_atomic "$f" || true
}
_breaker_reset() { rm -f "$(_breaker_file "$1")" 2>/dev/null || true; }
_save_rollback_ref() {
  printf '%s' "$1" | "$JQ_BIN" -c '{Env:(.Env//[])}' \
    | common_write_atomic "${APPLIER_STATE_DIR}/rollback_ref.json" 2>/dev/null || true
}

main() {
  common_require_bins || exit 3
  mkdir -p "$APPLIER_STATE_DIR" 2>/dev/null || true

  # Lock e payload vivem no ESTADO do applier (/var/lib, RW), NAO em RUN_DIR: sob
  # ProtectSystem=strict o pai /run/aprender-deployer e RO para o applier (so o
  # subdir handoff e montado RW). Gravar em RUN_DIR aqui mataria o processo (EROFS)
  # antes de qualquer verificacao — quebrando 100% da operacao (bug pego no red-team).
  exec 8>"${APPLIER_STATE_DIR}/applier.lock"
  if ! "$FLOCK_BIN" -n 8; then log_info "already_running"; exit 0; fi

  local raw="${HANDOFF_DIR}/pointer.json" sig="${HANDOFF_DIR}/pointer.sig"
  { [ -r "$raw" ] && [ -r "$sig" ]; } || REFUSE "handoff_missing"

  # RE-verifica a partir dos bytes (defense-in-depth contra deployer comprometido).
  pointer_verify_sig "$raw" "$sig" || REFUSE "applier_pointer_sig"
  pointer_parse "$raw"             || REFUSE "applier_shape"
  pointer_check_fresh              || REFUSE "expired"

  # Anti-rollback SELADO (owner=applier; deployer nao escreve).
  local sealed
  sealed="$(seal_read)" || REFUSE "seal_unreadable"
  if [ "$P_SEQUENCE" -le "$sealed" ]; then
    REFUSE "rollback" "sequence=${P_SEQUENCE}" "sealed=${sealed}"
  fi
  if [ "$P_ROLLBACK" = "true" ]; then
    log_audit "rollback_flag_honored" "sequence=${P_SEQUENCE}"   # downgrade assinado; ainda exige seq>sealed
  fi

  # Re-verifica imagens.
  image_verify "$P_BACKEND_REPO"  "$P_BACKEND_DIGEST"  || REFUSE "verify_backend"
  image_verify "$P_FRONTEND_REPO" "$P_FRONTEND_DIGEST" || REFUSE "verify_frontend"

  # Estado autoritativo da stack (applier tem o token de leitura).
  local stack port be_live fe_live
  stack="$(portainer_get_stack)" || FAIL "portainer_read"
  port="$(portainer_env_value "$stack" "BACKEND_HOST_PORT")"
  [ -n "$port" ] || port="${BACKEND_HOST_PORT:-8000}"
  be_live="$(portainer_env_value "$stack" "BACKEND_DIGEST")"
  fe_live="$(portainer_env_value "$stack" "FRONTEND_DIGEST")"

  # Idempotencia: ja convergiu no Env?
  if [ "$be_live" = "$P_BACKEND_DIGEST" ] && [ "$fe_live" = "$P_FRONTEND_DIGEST" ]; then
    if confirm_localhost "$P_RELEASE" "$port"; then
      seal_bump "$P_SEQUENCE"; notify "NOOP" "already_converged" "$P_RELEASE"; exit 0
    fi
    notify "WARN" "converged_env_but_unhealthy" "$P_RELEASE"; exit 0   # nao redeploya cego
  fi

  # Circuit breaker: nao repetir PUT de release ruim.
  local bc; bc="$(_breaker_count "$P_SEQUENCE")"
  if [ "$bc" -ge "${BREAKER_MAX:-3}" ]; then
    log_warn "breaker_hold" "sequence=${P_SEQUENCE}" "count=${bc}"; notify "HOLD" "breaker" "$P_RELEASE"; exit 0
  fi

  # Integridade da topologia: compose vivo == pinado (senao tamper/drift).
  local file_json
  file_json="$(portainer_get_file)" || FAIL "portainer_read_file"
  compose_check_drift "$file_json" || REFUSE "compose_drift"

  # Precondicao dura: backup de DB fresco antes do migrate destrutivo verificado.
  ensure_fresh_db_backup || REFUSE "no_fresh_backup"

  _save_rollback_ref "$stack"

  # Monta Env + payload com o compose PINADO (nunca o texto vindo da rede) e faz o PUT.
  local new_env payload
  new_env="$(compose_build_env "$stack" "$P_RELEASE" "$P_BACKEND_DIGEST" "$P_FRONTEND_DIGEST")" || FAIL "build_env"
  payload="$(mktemp "${APPLIER_STATE_DIR}/payload.XXXXXX")" || FAIL "mktemp"
  if ! compose_build_payload "$new_env" > "$payload"; then rm -f "$payload"; FAIL "build_payload"; fi

  if ! portainer_put "$payload"; then rm -f "$payload"; _breaker_inc "$P_SEQUENCE"; FAIL "put_failed"; fi
  rm -f "$payload"

  # Confirma (false-red-safe): faz POLL do Env ate refletir os digests do PUT. O PUT
  # pode responder 000 (resposta perdida) e o Portainer leva alguns segundos para
  # commitar; uma releitura unica reprovaria um deploy bom e armaria o breaker.
  if ! portainer_wait_env_digest "$P_BACKEND_DIGEST" "$P_FRONTEND_DIGEST"; then
    _breaker_inc "$P_SEQUENCE"; FAIL "put_unconfirmed_env"
  fi

  # Liveness em localhost (readyz 200 + version == release).
  if confirm_localhost "$P_RELEASE" "$port"; then
    seal_bump "$P_SEQUENCE"; _breaker_reset "$P_SEQUENCE"
    gc_run || log_warn "gc_failed"   # retencao de imagens best-effort; NUNCA aborta (pos-selo)
    notify "OK" "deployed" "$P_RELEASE"; log_info "deploy_ok" "release=${P_RELEASE}"; exit 0
  fi

  _breaker_inc "$P_SEQUENCE"
  log_error "deploy_unhealthy" "release=${P_RELEASE}"   # migrate quebrado? dependentes nao sobem
  FAIL "release_not_confirmed_manual_rollback"          # SEM auto-rollback
}

main "$@"

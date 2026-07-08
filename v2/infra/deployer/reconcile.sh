#!/usr/bin/env bash
# reconcile.sh — entrypoint do DEPLOYER (usuario aprender-deployer, SEM token).
#
# Timer oneshot. Busca o ponteiro assinado, VERIFICA (assinatura do ponteiro +
# cosign/attestation de cada digest), e — se ha sequence nova — faz o handoff
# dos BYTES BRUTOS para o applier (que re-verifica tudo). NAO tem o token do
# Portainer nem toca a stack. Fail-closed: qualquer falha => REFUSE (nao avanca).
#
# ADR-018 Fase 1 · issue #1513 · blueprint §C.1
set -euo pipefail

export LOG_COMPONENT=deployer
DEPLOYER_HOME="$(unset CDPATH; cd -- "$(dirname -- "$0")" && pwd -P)"
export DEPLOYER_HOME
# shellcheck source=lib/common.sh
. "${DEPLOYER_HOME}/lib/common.sh"

main() {
  common_require_bins || exit 3
  mkdir -p "$RUN_DIR" "$STATE_DIR" "$HANDOFF_DIR" 2>/dev/null || true

  # G0 — lock nao-bloqueante (evita reconciles concorrentes).
  exec 9>"${RUN_DIR}/reconcile.lock"
  if ! "$FLOCK_BIN" -n 9; then
    log_info "already_running"; exit 0
  fi
  state_heartbeat

  local raw="${RUN_DIR}/pointer.json" sig="${RUN_DIR}/pointer.sig"
  fetch_url "$POINTER_URL"     "$raw" || REFUSE "pointer_fetch"
  fetch_url "$POINTER_SIG_URL" "$sig" || REFUSE "sig_fetch"

  # ELO 1 — assinatura do ponteiro (identidade == promote.yml).
  pointer_verify_sig "$raw" "$sig" || REFUSE "pointer_sig_invalid"
  pointer_parse "$raw"             || REFUSE "pointer_shape"
  pointer_check_fresh              || REFUSE "pointer_expired"

  # Curto-circuito: so segue se ha sequence nova a aplicar (selo lido, nunca default).
  local sealed
  sealed="$(seal_read)" || REFUSE "seal_unreadable"
  if [ "$P_SEQUENCE" -le "$sealed" ]; then
    log_info "converged" "sequence=${P_SEQUENCE}" "sealed=${sealed}"
    exit 0
  fi

  # ELO 3 — assinatura das IMAGENS por digest (gate duro, recusa cedo com alerta bom).
  image_verify "$P_BACKEND_REPO"  "$P_BACKEND_DIGEST"  || REFUSE "verify_backend"
  image_verify "$P_FRONTEND_REPO" "$P_FRONTEND_DIGEST" || REFUSE "verify_frontend"

  # Drift advisory (NAO bloqueia — evita DoS por tag movida).
  local d
  if d="$(registry_digest "$P_BACKEND_REPO" "$P_RELEASE")"; then
    if [ "$d" != "$P_BACKEND_DIGEST" ]; then
      log_warn "tag_drift" "repo=${P_BACKEND_REPO}" "got=${d}"; notify "WARN" "tag_drift_backend" "$P_RELEASE"
    fi
  fi
  if d="$(registry_digest "$P_FRONTEND_REPO" "$P_RELEASE")"; then
    if [ "$d" != "$P_FRONTEND_DIGEST" ]; then
      log_warn "tag_drift" "repo=${P_FRONTEND_REPO}" "got=${d}"; notify "WARN" "tag_drift_frontend" "$P_RELEASE"
    fi
  fi

  # Handoff: entrega os BYTES BRUTOS + bundle. O applier re-verifica tudo.
  install -m 0640 "$raw" "${HANDOFF_DIR}/pointer.json"
  install -m 0640 "$sig" "${HANDOFF_DIR}/pointer.sig"
  touch "${HANDOFF_DIR}/trigger"   # dispara aprender-applier.path
  log_info "handoff_written" "sequence=${P_SEQUENCE}" "release=${P_RELEASE}"
  exit 0
}

main "$@"

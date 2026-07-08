# shellcheck shell=bash
# lib/notify.sh — notificacao write-only (webhook), payload fixo, SEM segredos/PII.
#
# Canal de saida de status (OK/FAIL/REFUSE/HOLD/NOOP/WARN). Nao ecoa env, nao
# manda logs crus. So um objeto JSON minimo com component/status/reason/release/host.
# Se NOTIFY_URL nao estiver setado, vira no-op (nunca aborta o deploy).

# notify <STATUS> <REASON> [RELEASE]
notify() {
  local status="$1" reason="${2:-}" release="${3:-${RELEASE:-}}"
  [ -n "${NOTIFY_URL:-}" ] || { log_info "notify_skip" "status=${status}"; return 0; }
  local ts payload
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)" || ts="?"
  payload="$("$JQ_BIN" -cn \
    --arg comp "${LOG_COMPONENT:-deployer}" --arg st "$status" \
    --arg rs "$reason" --arg rel "$release" --arg host "${PROD_HOST:-}" --arg ts "$ts" \
    '{component:$comp, status:$st, reason:$rs, release:$rel, host:$host, ts:$ts}' 2>/dev/null)" \
    || return 0
  # Egress deve estar na allowlist (o host de notificacao). Timeout curto, sem retry longo.
  "$CURL_BIN" -sS --proto '=https' --max-time 10 \
    -H 'Content-Type: application/json' \
    -X POST --data-binary "$payload" \
    "$NOTIFY_URL" >/dev/null 2>&1 || log_warn "notify_failed" "status=${status}"
  return 0
}

# shellcheck shell=bash
# lib/backup.sh — precondicao: backup de DB fresco ANTES do PUT (migrate destrutivo).
#
# Assinatura != seguranca de schema. Uma imagem validamente assinada ainda pode
# conter uma migration destrutiva. Precondicao dura: so deploya se existir um
# backup de DB recente. O applier NAO tem docker.sock nem creds de DB, entao o
# mecanismo e PLUGAVEL (decisao aberta #5, mecanismo real definido na Fase 3):
#   BACKUP_FRESHNESS_CMD  -> comando que sai 0 se ha backup fresco (preferido)
#   BACKUP_FRESHNESS_URL  -> endpoint que devolve JSON {age_seconds:N} (ou 200 simples)
# Fail-closed: se BACKUP_REQUIRED=1 (default) e nenhum mecanismo configurado => recusa.

# ensure_fresh_db_backup -> 0 se garantido/dispensado; !=0 => chamador REFUSE.
ensure_fresh_db_backup() {
  local required="${BACKUP_REQUIRED:-1}" max_age="${BACKUP_MAX_AGE:-86400}"

  if [ -n "${BACKUP_FRESHNESS_CMD:-}" ]; then
    if sh -c "$BACKUP_FRESHNESS_CMD" >/dev/null 2>&1; then
      log_info "backup_fresh" "via=cmd"; return 0
    fi
    log_error "backup_stale_or_missing" "via=cmd"; return 1
  fi

  if [ -n "${BACKUP_FRESHNESS_URL:-}" ]; then
    local body code age
    body="$("$CURL_BIN" -sS --proto '=https' --max-time 15 \
        -w '\n%{http_code}' "$BACKUP_FRESHNESS_URL" 2>/dev/null || true)"
    code="${body##*$'\n'}"; body="${body%$'\n'*}"
    [ "$code" = "200" ] || { log_error "backup_check_http" "http=${code}"; return 1; }
    age="$("$JQ_BIN" -r '.age_seconds // empty' <<<"$body" 2>/dev/null || true)"
    if [ -n "$age" ]; then
      case "$age" in ''|*[!0-9]*) log_error "backup_age_bad"; return 1 ;; esac
      [ "$age" -le "$max_age" ] || { log_error "backup_stale" "age=${age}" "max=${max_age}"; return 1; }
    fi
    log_info "backup_fresh" "via=url"; return 0
  fi

  if [ "$required" = "1" ]; then
    log_error "backup_mechanism_undefined" "hint=set BACKUP_FRESHNESS_CMD/URL ou BACKUP_REQUIRED=0"
    return 1
  fi
  log_warn "backup_check_skipped" "reason=BACKUP_REQUIRED=0"
  return 0
}

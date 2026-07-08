# shellcheck shell=bash
# lib/log.sh — log estruturado (JSON) para stderr/journald, com redaction de segredos.
#
# Regra: NUNCA logar o token do Portainer. A redaction e defesa-em-profundidade
# (o token nem deveria chegar aqui). Logging e tolerante a falha: um erro de log
# jamais aborta um deploy (todas as chamadas terminam em `|| true`).

# Redige X-API-KEY e tokens ptr_ de qualquer texto.
_log_redact() {
  sed -E \
    -e 's/(X-API-KEY:[[:space:]]*)[^"[:space:]]+/\1<redacted>/Ig' \
    -e 's/ptr_[A-Za-z0-9._-]+/ptr_<redacted>/g'
}

# log <LEVEL> <EVENT> [key=value ...]
log() {
  local level="$1" event="$2"; shift 2 || true
  local ts extra='{}' kv k v
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)" || ts="?"
  for kv in "$@"; do
    k="${kv%%=*}"; v="${kv#*=}"
    extra="$("$JQ_BIN" -cn --argjson o "$extra" --arg k "$k" --arg v "$v" \
              '$o + {($k):$v}' 2>/dev/null)" || extra='{}'
  done
  "$JQ_BIN" -cn \
      --arg ts "$ts" --arg lvl "$level" --arg comp "${LOG_COMPONENT:-deployer}" \
      --arg ev "$event" --argjson x "$extra" \
      '{ts:$ts, level:$lvl, component:$comp, event:$ev} + $x' 2>/dev/null \
    | _log_redact >&2 || true
}

log_info()  { log INFO  "$@" || true; }
log_warn()  { log WARN  "$@" || true; }
log_error() { log ERROR "$@" || true; }
log_audit() { log AUDIT "$@" || true; }

# REFUSE <motivo> [key=value ...] — recusa de seguranca: nao toca a stack, notifica, sai 10.
# FAIL   <motivo> [key=value ...] — deploy iniciado e nao convergiu: notifica, sai 1.
# Ambos NAO avancam o selo. Os entrypoints chamam estes helpers e encerram.
REFUSE() {
  local reason="$1"; shift || true
  log_error "refuse" "reason=${reason}" "$@"
  notify "REFUSE" "${reason}" || true
  exit 10
}
FAIL() {
  local reason="$1"; shift || true
  log_error "fail" "reason=${reason}" "$@"
  notify "FAIL" "${reason}" || true
  exit 1
}

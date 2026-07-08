# shellcheck shell=bash
# lib/state.sh — estado local (nao-confiavel) + heartbeat do dead-man switch.
#
# state.json/result.json NAO contem nada de confianca verificavel (sao so
# observabilidade local). A seguranca vem da cadeia de verificacao, nao daqui.

# Heartbeat: cada tick do deployer registra que rodou. Um observador EXTERNO
# alerta na AUSENCIA de heartbeat (>15min), nao so quando recebe um alerta.
state_heartbeat() {
  : > "${STATE_DIR}/heartbeat" 2>/dev/null || true
  date -u +%Y-%m-%dT%H:%M:%SZ > "${STATE_DIR}/heartbeat" 2>/dev/null || true
}

# state_set <dir> <json> — grava estado atomico (0600).
state_set() {
  local dir="$1" json="$2"
  printf '%s\n' "$json" | common_write_atomic "${dir}/state.json" 2>/dev/null || true
  chmod 0600 "${dir}/state.json" 2>/dev/null || true
}

# shellcheck shell=bash
# lib/seal.sh — contador monotonico SELADO (anti-rollback / anti-replay).
#
# Ancora de frescor do ponteiro. Cobre o unico ataque que branch-protegido +
# assinatura NAO cobrem: re-servir um production.json ANTIGO e validamente
# assinado para forcar downgrade a uma versao vulneravel.
#
# Owner do arquivo = aprender-applier (SO o applier escreve). O deployer LE
# (grupo). Bootstrap semeia com a sequence do primeiro ponteiro. NUNCA existe
# default silencioso (ex.: -1): arquivo ausente/ilegivel => o chamador REFUSE.
#
# Caminho: ${APPLIER_STATE_DIR}/seal/last_sequence  (0640 applier:deployer)

_seal_file() { printf '%s/seal/last_sequence' "$APPLIER_STATE_DIR"; }

# seal_read -> imprime o inteiro selado em stdout; retorna !=0 se ausente/malformado.
seal_read() {
  local f val
  f="$(_seal_file)"
  [ -r "$f" ] || return 1
  val="$(cat "$f" 2>/dev/null)" || return 1
  # Somente digitos (inteiro nao-negativo). Rejeita vazio, espacos, sinais.
  case "$val" in
    ''|*[!0-9]*) return 1 ;;
  esac
  printf '%s' "$val"
}

# seal_bump <sequence> — avanca o selo (SO o applier). Recusa retrocesso.
seal_bump() {
  local new="$1" cur f
  case "$new" in ''|*[!0-9]*) return 1 ;; esac
  f="$(_seal_file)"
  if cur="$(seal_read)"; then
    [ "$new" -gt "$cur" ] || { log_warn "seal_no_advance" "cur=${cur}" "new=${new}"; return 0; }
  fi
  mkdir -p "$(dirname "$f")" 2>/dev/null || true
  printf '%s' "$new" | common_write_atomic "$f" || return 1
  chmod 0640 "$f" 2>/dev/null || true
  log_audit "seal_bump" "sequence=${new}"
}

# shellcheck shell=bash
# lib/pointer.sh — verificacao da assinatura do ponteiro + validacao de shape.
#
# ELO 1 da cadeia de confianca: liga sequence+digests ao promotor (promote.yml).
# Verifica os BYTES EXATOS baixados (nunca re-serializar antes de verificar).
# Regra de ouro: checar EXIT CODE do cosign, jamais grep do stdout.

# Casa <string> contra <ERE>. Retorna 0/1.
_re_match() { printf '%s' "$1" | grep -Eq "$2"; }

# pointer_verify_sig <raw_file> <sig_file> -> exit code do cosign verify-blob.
pointer_verify_sig() {
  local raw="$1" sig="$2"
  "$COSIGN_BIN" verify-blob "$raw" \
    --new-bundle-format --bundle "$sig" \
    --certificate-oidc-issuer   "$OIDC_ISSUER" \
    --certificate-identity-regexp "$POINTER_IDENTITY_RE" \
    --trusted-root "$SIGSTORE_ROOT" \
    >/dev/null 2>&1
}

# pointer_parse <raw_file> -> valida shape/regex/allowlist; seta globais P_*; !=0 se invalido.
# Globais (consumidos pelos entrypoints reconcile.sh/apply.sh, por isso o disable SC2034):
#   P_SCHEMA P_SEQUENCE P_RELEASE P_ROLLBACK P_EXPIRES_AT
#   P_BACKEND_REPO P_BACKEND_DIGEST P_FRONTEND_REPO P_FRONTEND_DIGEST
pointer_parse() {
  local raw="$1" j
  j="$(cat "$raw" 2>/dev/null)" || return 1
  # JSON valido?
  "$JQ_BIN" -e . >/dev/null 2>&1 <<<"$j" || { log_error "pointer_not_json"; return 1; }

  P_SCHEMA="$("$JQ_BIN"   -r '.schema         // empty' <<<"$j")"
  P_SEQUENCE="$("$JQ_BIN" -r '.sequence       // empty' <<<"$j")"
  P_RELEASE="$("$JQ_BIN"  -r '.release        // empty' <<<"$j")"
  # shellcheck disable=SC2034  # usado em apply.sh (flag de rollback assinado)
  P_ROLLBACK="$("$JQ_BIN" -r '.rollback       // false' <<<"$j")"
  P_EXPIRES_AT="$("$JQ_BIN" -r '.expires_at   // empty' <<<"$j")"
  P_BACKEND_REPO="$("$JQ_BIN"   -r '.backend.repo    // empty' <<<"$j")"
  P_BACKEND_DIGEST="$("$JQ_BIN" -r '.backend.digest  // empty' <<<"$j")"
  P_FRONTEND_REPO="$("$JQ_BIN"   -r '.frontend.repo   // empty' <<<"$j")"
  P_FRONTEND_DIGEST="$("$JQ_BIN" -r '.frontend.digest // empty' <<<"$j")"

  # schema conhecido
  [ "$P_SCHEMA" = "1" ] || { log_error "pointer_schema" "got=${P_SCHEMA}"; return 1; }
  # release: vYYYY.MM.DD-<sha/label>
  _re_match "$P_RELEASE" '^v[0-9]{4}\.[0-9]{2}\.[0-9]{2}-[0-9A-Za-z._-]+$' \
    || { log_error "pointer_release_bad" "release=${P_RELEASE}"; return 1; }
  # sequence: inteiro nao-negativo
  case "$P_SEQUENCE" in ''|*[!0-9]*) log_error "pointer_seq_bad" "seq=${P_SEQUENCE}"; return 1 ;; esac
  # repos batem com a allowlist (identity.env), nao apenas "algum repo"
  [ "$P_BACKEND_REPO"  = "$BACKEND_REPO"  ] || { log_error "pointer_be_repo"  "repo=${P_BACKEND_REPO}";  return 1; }
  [ "$P_FRONTEND_REPO" = "$FRONTEND_REPO" ] || { log_error "pointer_fe_repo"  "repo=${P_FRONTEND_REPO}"; return 1; }
  # digests: sha256:<64 hex>
  _re_match "$P_BACKEND_DIGEST"  '^sha256:[0-9a-f]{64}$' || { log_error "pointer_be_digest"; return 1; }
  _re_match "$P_FRONTEND_DIGEST" '^sha256:[0-9a-f]{64}$' || { log_error "pointer_fe_digest"; return 1; }
  # expires_at presente e parseavel
  [ -n "$P_EXPIRES_AT" ] || { log_error "pointer_no_expiry"; return 1; }
  return 0
}

# pointer_check_fresh -> 0 se now <= expires_at; !=0 se expirado/malformado.
pointer_check_fresh() {
  local exp now
  exp="$(date -u -d "$P_EXPIRES_AT" +%s 2>/dev/null)" || { log_error "pointer_expiry_unparseable" "expires_at=${P_EXPIRES_AT}"; return 1; }
  now="$(date -u +%s)"
  [ "$now" -le "$exp" ] || { log_error "pointer_expired" "expires_at=${P_EXPIRES_AT}"; return 1; }
  return 0
}

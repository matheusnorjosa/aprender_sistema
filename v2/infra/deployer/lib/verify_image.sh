# shellcheck shell=bash
# lib/verify_image.sh — GATE DURO: assinatura + attestation da imagem por DIGEST.
#
# ELO 3: liga o digest ao slsa-provenance.yml (identidade OIDC). cosign verify
# (Fulcio/Rekor, trusted-root pinado offline) + gh attestation verify (SLSA).
# Fail-closed: qualquer falha => o chamador REFUSE, nunca deploy.

# image_verify <repo> <digest> -> 0 se ambos passarem; !=0 caso contrario.
image_verify() {
  local repo="$1" digest="$2" ref="${1}@${2}"

  "$COSIGN_BIN" verify "$ref" \
    --certificate-oidc-issuer   "$OIDC_ISSUER" \
    --certificate-identity-regexp "$IMAGE_IDENTITY_RE" \
    --trusted-root "$SIGSTORE_ROOT" \
    >/dev/null 2>&1 \
    || { log_error "cosign_verify_failed" "repo=${repo}"; return 1; }

  # --bundle-from-oci evita depender de api.github.com no caminho quente.
  "$GH_BIN" attestation verify "oci://${ref}" \
    --repo "$GH_REPO" \
    --signer-workflow "$SIGNER_WORKFLOW" \
    --bundle-from-oci \
    >/dev/null 2>&1 \
    || { log_error "attestation_verify_failed" "repo=${repo}"; return 1; }

  log_info "image_verified" "repo=${repo}" "digest=${digest}"
  return 0
}

# registry_digest <repo> <tag> -> imprime o digest atual da tag no registry (ADVISORY).
# Best-effort: usado so para detectar tag-drift (nao bloqueia; evita DoS por tag movida).
registry_digest() {
  local repo="$1" tag="$2" tok got
  tok="$("$CURL_BIN" -fsS --proto '=https' --max-time 15 \
      "https://auth.docker.io/token?service=registry.docker.io&scope=repository:${repo}:pull" \
      2>/dev/null | "$JQ_BIN" -r '.token // empty' 2>/dev/null)" || return 1
  [ -n "$tok" ] || return 1
  got="$("$CURL_BIN" -fsSI --proto '=https' --max-time 15 \
      -H "Authorization: Bearer ${tok}" \
      -H 'Accept: application/vnd.oci.image.index.v1+json' \
      -H 'Accept: application/vnd.docker.distribution.manifest.list.v2+json' \
      "https://registry-1.docker.io/v2/${repo}/manifests/${tag}" 2>/dev/null \
      | tr -d '\r' | awk -F': ' 'tolower($1)=="docker-content-digest"{print $2}')" || return 1
  [ -n "$got" ] || return 1
  printf '%s' "$got"
}

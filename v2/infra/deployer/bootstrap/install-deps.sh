#!/usr/bin/env bash
# install-deps.sh — instala cosign + gh na VM (verificados por checksum publicado).
#
# Helper de bootstrap da Fase 3 (ADR-018). O agente aprender-deployer precisa de
# cosign e gh para verificar assinaturas/attestations, e eles nao vem no Ubuntu.
# Resolve a ULTIMA release de cada (api.github.com), baixa o binario + o arquivo
# de checksums DA MESMA release (ambos por HTTPS/TLS), verifica sha256 e instala
# em /usr/local/bin. Idempotente (pula o que ja existe). Rodar como root.
#
# Depois disto, `bootstrap/install.sh --record-bins` fixa o hash local (TOFU) em
# trust/bin.sha256 para as verificacoes seguintes.
set -euo pipefail

BIN=/usr/local/bin
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
have() { command -v "$1" >/dev/null 2>&1; }
die()  { printf 'install-deps: %s\n' "$1" >&2; exit 1; }

[ "$(id -u)" = "0" ] || die "rode como root"
for b in curl jq tar sha256sum install; do have "$b" || die "falta $b"; done

install_cosign() {
  if have cosign; then echo "cosign ja presente: $(cosign version 2>/dev/null | awk '/GitVersion/{print $2}')"; return; fi
  echo "==> cosign"
  local ver
  ver="$(curl -fsSL https://api.github.com/repos/sigstore/cosign/releases/latest | jq -r '.tag_name // empty')"
  [ -n "$ver" ] || die "nao resolvi a versao do cosign"
  local base="https://github.com/sigstore/cosign/releases/download/${ver}"
  curl -fsSL -o "$tmp/cosign-linux-amd64"  "${base}/cosign-linux-amd64"
  curl -fsSL -o "$tmp/cosign_checksums.txt" "${base}/cosign_checksums.txt"
  ( cd "$tmp" && grep ' cosign-linux-amd64$' cosign_checksums.txt | sha256sum -c - ) \
    || die "checksum do cosign FALHOU"
  install -m 0755 "$tmp/cosign-linux-amd64" "$BIN/cosign"
  echo "    cosign ${ver} OK -> $BIN/cosign"
}

install_gh() {
  if have gh; then echo "gh ja presente: $(gh --version | head -1)"; return; fi
  echo "==> gh"
  local ver num tgz
  ver="$(curl -fsSL https://api.github.com/repos/cli/cli/releases/latest | jq -r '.tag_name // empty')"
  [ -n "$ver" ] || die "nao resolvi a versao do gh"
  num="${ver#v}"
  tgz="gh_${num}_linux_amd64.tar.gz"
  local base="https://github.com/cli/cli/releases/download/${ver}"
  curl -fsSL -o "$tmp/$tgz"               "${base}/${tgz}"
  curl -fsSL -o "$tmp/gh_checksums.txt"   "${base}/gh_${num}_checksums.txt"
  ( cd "$tmp" && grep " ${tgz}\$" gh_checksums.txt | sha256sum -c - ) \
    || die "checksum do gh FALHOU"
  tar -xzf "$tmp/$tgz" -C "$tmp"
  install -m 0755 "$tmp/gh_${num}_linux_amd64/bin/gh" "$BIN/gh"
  echo "    gh ${ver} OK -> $BIN/gh"
}

install_cosign
install_gh
echo "==> pronto: cosign=$(command -v cosign)  gh=$(command -v gh)"
echo "    proximo: bootstrap/install.sh --src <arvore> --record-bins"

#!/usr/bin/env bash
# bootstrap/install.sh — instala o agente aprender-deployer na VM01 (rodar como root).
#
# Cria os 2 usuarios nao-root + grupo compartilhado, instala a arvore IMUTAVEL
# em /opt/aprender-deployer/<versao>/ (chattr +i), valida os binarios por hash,
# instala config em /etc, cria os diretorios de estado e habilita os units.
#
# O agente NUNCA se auto-atualiza (sem git pull+exec). Atualizar = rodar este
# script de novo com uma arvore nova e re-verificada (tarball assinado).
#
# Uso:
#   sudo ./install.sh --src <dir-da-arvore> [--record-bins]
#   --record-bins : grava os hashes atuais dos binarios em trust/bin.sha256 (TOFU 1a vez)
#
# ADR-018 Fase 1 · issue #1513 · blueprint §I(9)
set -euo pipefail

PREFIX="/opt/aprender-deployer"
ETC="/etc/aprender-deployer"
SRC=""
RECORD_BINS=0
DEPLOYER_USER="aprender-deployer"
APPLIER_USER="aprender-applier"
SHARED_GROUP="aprender-deploy"

die() { printf 'install: %s\n' "$1" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --src)          SRC="${2:-}"; shift 2;;
    --prefix)       PREFIX="${2:-}"; shift 2;;
    --record-bins)  RECORD_BINS=1; shift;;
    -h|--help)      grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
    *) die "arg desconhecido: $1";;
  esac
done

[ "$(id -u)" = "0" ] || die "precisa rodar como root"
[ -n "$SRC" ] && [ -d "$SRC" ] || die "informe --src <dir da arvore do agente>"
[ -f "$SRC/reconcile.sh" ] && [ -f "$SRC/apply.sh" ] || die "--src nao parece a arvore do agente"

echo "==> usuarios e grupo"
getent group "$SHARED_GROUP"   >/dev/null || groupadd --system "$SHARED_GROUP"
getent passwd "$DEPLOYER_USER" >/dev/null || useradd --system --no-create-home --shell /usr/sbin/nologin -g "$SHARED_GROUP" "$DEPLOYER_USER"
getent passwd "$APPLIER_USER"  >/dev/null || useradd --system --no-create-home --shell /usr/sbin/nologin "$APPLIER_USER"
usermod -aG "$SHARED_GROUP" "$APPLIER_USER"   # applier tambem no grupo compartilhado (le handoff/selo)

echo "==> valida binarios (trust/bin.sha256)"
BINS="$SRC/trust/bin.sha256"
if [ "$RECORD_BINS" = "1" ]; then
  : > "$BINS.new"
  for b in /usr/local/bin/cosign /usr/local/bin/gh /usr/bin/jq /usr/bin/curl; do
    [ -x "$b" ] || die "binario ausente: $b"
    sha256sum "$b" >> "$BINS.new"
  done
  mv "$BINS.new" "$BINS"
  echo "    hashes gravados em $BINS (revisar e commitar)"
else
  grep -vE '^\s*#|^\s*$' "$BINS" >/dev/null 2>&1 || die "trust/bin.sha256 vazio; rode --record-bins e revise"
  while read -r line; do
    case "$line" in ''|\#*) continue;; esac
    printf '%s\n' "$line" | sha256sum -c - >/dev/null 2>&1 || die "hash divergente: $line"
  done < "$BINS"
  echo "    binarios OK"
fi

echo "==> instala arvore imutavel"
VER="$(cat "$SRC/VERSION" 2>/dev/null || date -u +%Y%m%dT%H%M%SZ)"
DEST="$PREFIX/$VER"
mkdir -p "$PREFIX"
# se ja existe (re-run), remove o imutavel antes. Destrava tambem o PAI defensivamente
# (instalacoes antigas podiam te-lo deixado +i, o que impede remover o version dir).
if [ -d "$DEST" ]; then
  chattr -i "$PREFIX" 2>/dev/null || true
  chattr -R -i "$DEST" 2>/dev/null || true
  rm -rf "$DEST"
fi
cp -a "$SRC" "$DEST"
chown -R root:"$SHARED_GROUP" "$DEST"
chmod -R a-w,g-w "$DEST"
find "$DEST" -type d -exec chmod 0755 {} +
find "$DEST" -name '*.sh' -exec chmod 0755 {} +
ln -sfn "$DEST" "$PREFIX/current"
# imutavel: SO o codigo/ancoras da versao ($DEST). O pai $PREFIX fica MUTAVEL — ele
# precisa aceitar novas versoes e repontar o symlink 'current' nos updates; torna-lo
# imutavel quebraria o proprio re-install (rm do version dir falha com o pai +i).
chattr -R +i "$DEST" 2>/dev/null || echo "    (chattr +i indisponivel neste FS — garantir RO por outro meio)"

echo "==> /etc/aprender-deployer"
mkdir -p "$ETC"
[ -f "$ETC/config.env" ] || { cp "$DEST/config.env.example" "$ETC/config.env"; echo "    criado $ETC/config.env — PREENCHER STACK_ID/ENDPOINT_ID"; }
chmod 0644 "$ETC/config.env"; chown root:root "$ETC/config.env"
if [ ! -f "$ETC/portainer.curlrc" ]; then
  cp "$DEST/portainer.curlrc.example" "$ETC/portainer.curlrc"
  echo "    criado $ETC/portainer.curlrc — SUBSTITUIR o token real"
fi
chown "$APPLIER_USER":"$APPLIER_USER" "$ETC/portainer.curlrc"
chmod 0400 "$ETC/portainer.curlrc"

echo "==> diretorios de estado"
install -d -o "$DEPLOYER_USER" -g "$SHARED_GROUP" -m 0750 /var/lib/aprender-deployer
install -d -o "$APPLIER_USER"  -g "$SHARED_GROUP" -m 0750 /var/lib/aprender-applier
install -d -o "$APPLIER_USER"  -g "$SHARED_GROUP" -m 2750 /var/lib/aprender-applier/seal   # setgid: selo herda grupo

echo "==> systemd units"
cp "$DEST"/systemd/aprender-deployer.service /etc/systemd/system/
cp "$DEST"/systemd/aprender-deployer.timer   /etc/systemd/system/
cp "$DEST"/systemd/aprender-applier.service  /etc/systemd/system/
cp "$DEST"/systemd/aprender-applier.path     /etc/systemd/system/
systemctl daemon-reload
systemctl enable aprender-applier.path
systemctl enable aprender-deployer.timer
echo "    units instalados. NAO inicie o timer ate: (1) preencher config.env + token,"
echo "    (2) semear o selo e o compose pinado (bootstrap/migrate-stack.sh),"
echo "    (3) gerar trust/sigstore-root.json. Ver README.md."
echo "==> concluido (versao $VER)"

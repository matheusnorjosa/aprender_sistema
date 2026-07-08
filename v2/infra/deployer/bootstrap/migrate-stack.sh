#!/usr/bin/env bash
# bootstrap/migrate-stack.sh — cutover unico para o modelo pull-based (rodar no host).
#
# Operacao ATOMICA e IRREVERSIVEL-por-descuido (landmine #13): ao pinar o compose
# na forma Opcao-B (imagens por @${DIGEST:?}), o deploy push legado QUEBRA (ele so
# seta IMAGE_TAG). Logo este script tem de rodar JUNTO com a desativacao do
# escritor legado (o job deploy do deploy.yaml para de escrever a stack de prod).
#
# Passos (dry-run por padrao; --apply para efetivar):
#   1. GET /file da stack -> compose atual.
#   2. Transforma para Opcao-B: cada `image: repo:${IMAGE_TAG...}` vira
#        `image: repo:${IMAGE_TAG...}@${BACKEND_DIGEST:?...}` (backend) / FRONTEND_DIGEST (frontend).
#   3. Resolve os digests em execucao (do Env atual, se ja pinado, OU do registry pela tag atual).
#   4. PUT com o compose Opcao-B + Env semeando IMAGE_TAG/BACKEND_DIGEST/FRONTEND_DIGEST.
#   5. GET /file de novo -> captura a forma NORMALIZADA do Portainer -> grava como
#      trust/compose.pinned.yml (byte-estabilidade! o compose_check_drift compara com isto).
#   6. Semeia o selo: /var/lib/aprender-applier/seal/last_sequence = sequence do 1o production.json.
#   7. Desliga o escritor legado (remover/gate o job de PUT no deploy.yaml — Fase 2).
#
# Este arquivo e um SKELETON com os comandos-chave; revisar e completar os pontos
# marcados TODO(host) contra o ambiente real ANTES do --apply. Ver blueprint §I(12).
set -euo pipefail

APPLY=0
[ "${1:-}" = "--apply" ] && APPLY=1

echo "migrate-stack: modo=$([ "$APPLY" = 1 ] && echo APPLY || echo DRY-RUN)"
echo "PRE-REQUISITOS:"
echo "  - config.env preenchido (PORTAINER_STACK_ID, ENDPOINT_ID) + token no curlrc"
echo "  - trust/sigstore-root.json gerado"
echo "  - escritor legado (deploy.yaml PUT de prod) pronto para ser desligado no MESMO passo"
echo
cat <<'STEPS'
# --- 1/6 compose atual ---
# stack_file=$(curl -sS -K /etc/aprender-deployer/portainer.curlrc \
#   "$PORTAINER_BASE/api/stacks/$STACK_ID/file")
# echo "$stack_file" | jq -r .StackFileContent > /tmp/compose.current.yml

# --- 2/6 transforma p/ Opcao-B (revisar o sed contra o formato real!) ---
# sed -E \
#   -e 's#(image:\s*norjosamatheus/aprender-backend:\$\{IMAGE_TAG[^}]*\})#\1@${BACKEND_DIGEST:?BACKEND_DIGEST is required}#' \
#   -e 's#(image:\s*norjosamatheus/aprender-frontend:\$\{IMAGE_TAG[^}]*\})#\1@${FRONTEND_DIGEST:?FRONTEND_DIGEST is required}#' \
#   /tmp/compose.current.yml > /tmp/compose.optionb.yml
# TODO(host): conferir que os 4 servicos backend + 1 frontend foram cobertos.

# --- 3/6 digests em execucao (do primeiro production.json assinado) ---
# BE_DIGEST=... FE_DIGEST=...  (verificados por cosign ANTES de semear)

# --- 4/6 PUT Opcao-B + Env semeado --- (usa o compose.optionb + Env com digests)

# --- 5/6 captura a forma normalizada -> trust/compose.pinned.yml ---
# curl ... /api/stacks/$STACK_ID/file | jq -j .StackFileContent > trust/compose.pinned.yml
#   (jq -j, NAO -r: sem \n final, p/ o hash bater com compose_live_sha)
# (depois: chattr +i via re-run do install.sh)

# --- 6/6 semeia o selo ---
# echo "<sequence-do-1o-ponteiro>" > /var/lib/aprender-applier/seal/last_sequence
# chown aprender-applier:aprender-deploy /var/lib/aprender-applier/seal/last_sequence
# chmod 0640 /var/lib/aprender-applier/seal/last_sequence
STEPS

if [ "$APPLY" = 0 ]; then
  echo; echo "DRY-RUN: nada aplicado. Complete os TODO(host) e rode com --apply."
  exit 0
fi
echo "APPLY: implementar os passos acima contra o host (mantido como skeleton de proposito)."
exit 2

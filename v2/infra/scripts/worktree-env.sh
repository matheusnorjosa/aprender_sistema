#!/usr/bin/env bash
# worktree-env.sh — isola o stack Docker de dev por worktree (multi-worktree paralelo).
#
# Cada worktree paralelo precisa de um stack Docker próprio (nome + portas + volumes)
# para não colidir com os outros. Este script deriva TUDO de um número de slot e exporta
# as variáveis que o Makefile (PROJECT) e o compose (portas) leem.
#
# USO (precisa ser SOURCED, não executado — export só persiste no shell atual):
#   source infra/scripts/worktree-env.sh 1    # slot explícito
#   source infra/scripts/worktree-env.sh      # auto: lê .dev-slot do worktree (ou 0)
#   cd v2 && make up                          # sobe o stack isolado
#
# Resolução do slot (primeiro que existir): argumento $1 > env DEV_SLOT > arquivo
# `.dev-slot` na raiz do worktree > 0. Grave `echo 1 > .dev-slot` na raiz de cada
# worktree e os terminais só precisam de `source ... && make up`.
#
# Slot 0 (ou vazio) = default de sempre (aprender_dev, portas padrão). Cada worktree usa
# um slot distinto (1, 2, 3, ...). Offset de +10 por slot deixa folga entre os blocos.
#
# Portas por slot (host): backend=8002+slot*10 · db=5434+slot*10 · redis=6380+slot*10 ·
# frontend=5173+slot*10  (slot1 -> 8012/5444/6390/5183, slot2 -> 8022/5454/6400/5193, ...)

_wt_slot="${1:-}"

# Fallbacks: env DEV_SLOT, depois .dev-slot na raiz do worktree.
if [ -z "$_wt_slot" ]; then
  _wt_slot="${DEV_SLOT:-}"
fi
if [ -z "$_wt_slot" ]; then
  _wt_root="$(git rev-parse --show-toplevel 2>/dev/null)"
  if [ -n "$_wt_root" ] && [ -f "$_wt_root/.dev-slot" ]; then
    _wt_slot="$(tr -d '[:space:]' < "$_wt_root/.dev-slot")"
  fi
  unset _wt_root
fi
_wt_slot="${_wt_slot:-0}"

if ! printf '%s' "$_wt_slot" | grep -qE '^[0-9]+$'; then
  echo "worktree-env: slot inválido '$_wt_slot' (use um inteiro >= 0)" >&2
  unset _wt_slot
  return 1 2>/dev/null || exit 1
fi

if [ "$_wt_slot" = "0" ]; then
  export PROJECT="aprender_dev"
else
  export PROJECT="aprender_dev_s${_wt_slot}"
fi

export BACKEND_HOST_PORT=$((8002 + _wt_slot * 10))
export DB_HOST_PORT=$((5434 + _wt_slot * 10))
export REDIS_HOST_PORT=$((6380 + _wt_slot * 10))
export FRONTEND_HOST_PORT=$((5173 + _wt_slot * 10))

echo "worktree slot ${_wt_slot} -> PROJECT=${PROJECT} | backend :${BACKEND_HOST_PORT} | db :${DB_HOST_PORT} | redis :${REDIS_HOST_PORT} | frontend :${FRONTEND_HOST_PORT}"

unset _wt_slot

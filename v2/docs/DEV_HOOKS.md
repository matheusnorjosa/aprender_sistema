# Hooks Locais — v2

> ⚠️ **Leia antes de copiar o snippet (revisto 2026-07-24).**
>
> 1. **O git root é a raiz do repositório, não `v2/`.** Não existe `v2/.git`. A receita anterior
>    fazia `cd v2` e depois escrevia em `.git/hooks/pre-commit` — o redirecionamento falha.
>    Use o comando abaixo, que resolve o caminho via `git rev-parse` e funciona também em
>    **git worktrees** (onde `.git` é um arquivo, não um diretório).
> 2. **Este hook conflita com o `pre-commit` framework.** O repositório tem
>    `.pre-commit-config.yaml` na raiz e em `v2/backend/`. Rodar `pre-commit install`
>    **sobrescreve** `.git/hooks/pre-commit` e apaga este hook em silêncio.
>    Se você usa `pre-commit`, **não** use a receita manual: registre a checagem como um
>    hook `repo: local` no `.pre-commit-config.yaml` (já há exemplos lá).

Hook para garantir que containers antigos não estejam ativos:

```bash
HOOKS_DIR="$(git rev-parse --git-path hooks)"
mkdir -p "$HOOKS_DIR"
cat <<'HOOK' > "$HOOKS_DIR/pre-commit"
#!/usr/bin/env bash
set -euo pipefail

# Verificar se há containers com label antigo
if docker ps --format '{{.Label "com.docker.compose.project"}}' |
   grep -q '^aprendersistema$'; then
  echo "[pre-commit] Containers antigos ainda ativos. Rode make ban-v1." >&2
  exit 1
fi
HOOK
chmod +x "$HOOKS_DIR/pre-commit"
```

Scripts úteis (a partir de `v2/`):
- `make ban-v1` — Remove containers/redes/volumes antigos (`v2/Makefile:152-153`)
- `./scripts/ban_v1.sh` — Script de limpeza (`v2/scripts/ban_v1.sh`)

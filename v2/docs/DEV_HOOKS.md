# Hooks Locais — v2

Hook para garantir que containers antigos não estejam ativos:

```bash
cd v2
cat <<'HOOK' > .git/hooks/pre-commit
#!/usr/bin/env bash
set -euo pipefail

# Verificar se há containers com label antigo
if docker ps --format '{{.Label "com.docker.compose.project"}}' |
   grep -q '^aprendersistema$'; then
  echo "[pre-commit] Containers antigos ainda ativos. Rode make ban-v1." >&2
  exit 1
fi
HOOK
chmod +x .git/hooks/pre-commit
```

Scripts úteis:
- `make ban-v1` - Remove containers/redes/volumes antigos
- `./scripts/ban_v1.sh` - Script de limpeza

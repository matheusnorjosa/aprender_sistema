# Hooks Locais — v2

Para evitar tocar no sistema legado (archive/v1_legado/):

```bash
cd v2
cat <<'HOOK' > .git/hooks/pre-commit
#!/usr/bin/env bash
set -euo pipefail

if git diff --cached --name-only | grep -q '^archive/v1_legado/'; then
  echo "[pre-commit] archive/v1_legado é somente leitura." >&2
  exit 1
fi

if docker ps --format '{{.Label "com.docker.compose.project"}}' |
   grep -q '^aprendersistema$'; then
  echo "[pre-commit] Containers aprendersistema ainda ativos. Rode make ban-v1." >&2
  exit 1
fi
HOOK
chmod +x .git/hooks/pre-commit
```

Scripts úteis:

- `make ban-v1`
- `./scripts/ban_v1.sh`

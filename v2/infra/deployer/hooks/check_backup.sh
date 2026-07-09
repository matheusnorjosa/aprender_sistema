#!/usr/bin/env bash
# hooks/check_backup.sh — BACKUP_FRESHNESS_CMD do applier (ADR-018 B2 / issue #1455).
#
# Sai 0 se existe um backup de DB FRESCO (idade <= BACKUP_MAX_AGE) em BACKUP_DIR;
# !=0 caso contrario. E o gate que o applier consulta em ensure_fresh_db_backup
# (lib/backup.sh) ANTES de um PUT com migrate destrutivo verificado. Fail-closed:
# ausencia/velho/erro => nao-zero => o applier REFUSE o deploy.
#
# So faz stat (NUNCA le conteudo): os dumps sao .age (cifrados, SEC-017). Roda sob o
# sandbox do applier (ProtectSystem=strict) — BACKUP_DIR precisa ser legivel (nao /home,
# nao docker.sock). O naming vem de infra/scripts/backup_db.sh: backup_full_*.sql.gz[.age].
#
# Env (via /etc/aprender-deployer/config.env, herdado pelo EnvironmentFile do applier):
#   BACKUP_DIR      dir dos dumps no host (default /var/backups/aprender)
#   BACKUP_MAX_AGE  idade maxima em segundos (default 100800 = 28h; margem sobre 02:00 diario)
#
# ADR-018 · issue #1455 (backup morto: worker/beat sem mount /backups) + #1513
set -euo pipefail

dir="${BACKUP_DIR:-/var/backups/aprender}"
max_age="${BACKUP_MAX_AGE:-100800}"

# max_age precisa ser inteiro (fail-closed se lixo — nunca aceitar deploy por engano).
case "$max_age" in
  ''|*[!0-9]*) echo "check_backup: BACKUP_MAX_AGE invalido: '${max_age}'" >&2; exit 2 ;;
esac

[ -d "$dir" ] || { echo "check_backup: dir de backup ausente: ${dir}" >&2; exit 1; }

# Backup mais recente (glob nao-expandido some via [ -e ]; sem depender de nullglob).
newest=""
for f in "$dir"/backup_full_*.sql.gz "$dir"/backup_full_*.sql.gz.age; do
  [ -e "$f" ] || continue
  if [ -z "$newest" ] || [ "$f" -nt "$newest" ]; then newest="$f"; fi
done
[ -n "$newest" ] || { echo "check_backup: nenhum backup_full_*.sql.gz[.age] em ${dir}" >&2; exit 1; }

# mtime: GNU (stat -c %Y) com fallback BSD (stat -f %m) para portabilidade dos testes.
now="$(date +%s)"
mtime="$(stat -c %Y "$newest" 2>/dev/null || stat -f %m "$newest" 2>/dev/null || true)"
case "$mtime" in
  ''|*[!0-9]*) echo "check_backup: stat falhou em ${newest}" >&2; exit 2 ;;
esac

age=$(( now - mtime ))
if [ "$age" -lt 0 ]; then
  echo "check_backup: mtime no futuro (relogio?) file=$(basename "$newest")" >&2; exit 2
fi
if [ "$age" -le "$max_age" ]; then
  echo "check_backup: fresco age=${age}s max=${max_age}s file=$(basename "$newest")"
  exit 0
fi
echo "check_backup: STALE age=${age}s max=${max_age}s file=$(basename "$newest")" >&2
exit 1
#!/usr/bin/env bash
# hooks/check_backup.sh — BACKUP_FRESHNESS_CMD do applier (ADR-018 B2 / issue #1455).
#
# Sai 0 se existe um backup de DB VALIDO (fresco E grande o suficiente) em BACKUP_DIR;
# !=0 caso contrario. E o gate que o applier consulta em ensure_fresh_db_backup
# (lib/backup.sh) ANTES de um PUT com migrate destrutivo verificado. Fail-closed:
# ausencia/velho/pequeno/erro => nao-zero => o applier REFUSE o deploy.
#
# "Valido" = idade <= BACKUP_MAX_AGE E tamanho >= BACKUP_MIN_SIZE. O check de tamanho
# fecha o furo do backup 0-byte/truncado (um dump que falhou no meio deixa um arquivo
# fresco mas vazio, que passaria so pela idade). Escolhe o mais NOVO entre os validos,
# entao um backup falho recente nao bloqueia se houver um valido tambem recente.
#
# So faz stat (NUNCA le conteudo): os dumps sao .age (cifrados, SEC-017). Roda sob o
# sandbox do applier (ProtectSystem=strict) — BACKUP_DIR precisa ser legivel (nao /home,
# nao docker.sock). O naming vem de infra/scripts/backup_db.sh: backup_full_*.sql.gz[.age].
#
# Env (via /etc/aprender-deployer/config.env, herdado pelo EnvironmentFile do applier):
#   BACKUP_DIR      dir dos dumps no host (default /var/backups/aprender)
#   BACKUP_MAX_AGE  idade maxima em segundos (default 100800 = 28h; margem sobre 02:00 diario)
#   BACKUP_MIN_SIZE bytes minimos (default 1024; um dump real e ~300KB, um .age vazio <1KB)
#
# ADR-018 · issue #1455 (backup morto: worker/beat sem mount /backups) + #1513
set -euo pipefail

dir="${BACKUP_DIR:-/var/backups/aprender}"
max_age="${BACKUP_MAX_AGE:-100800}"
min_size="${BACKUP_MIN_SIZE:-1024}"

# Parametros precisam ser inteiros (fail-closed se lixo — nunca aceitar deploy por engano).
for _v in "$max_age" "$min_size"; do
  case "$_v" in
    ''|*[!0-9]*) echo "check_backup: parametro nao-inteiro: '${_v}'" >&2; exit 2 ;;
  esac
done

[ -d "$dir" ] || { echo "check_backup: dir de backup ausente: ${dir}" >&2; exit 1; }

# mtime/size via GNU (stat -c) com fallback BSD (stat -f) para portabilidade dos testes.
_mtime() { stat -c %Y "$1" 2>/dev/null || stat -f %m "$1" 2>/dev/null || echo 0; }
_size()  { stat -c %s "$1" 2>/dev/null || stat -f %z "$1" 2>/dev/null || echo 0; }

now="$(date +%s)"
newest=""; newest_mtime=0; newest_size=0
seen=0; small=0; old=0
# Glob nao-expandido some via [ -e ] (sem depender de nullglob). .gz e .gz.age nao colidem.
for f in "$dir"/backup_full_*.sql.gz "$dir"/backup_full_*.sql.gz.age; do
  [ -e "$f" ] || continue
  seen=$((seen + 1))
  mt="$(_mtime "$f")"; sz="$(_size "$f")"
  case "$mt" in ''|*[!0-9]*) mt=0 ;; esac
  case "$sz" in ''|*[!0-9]*) sz=0 ;; esac
  if [ "$sz" -lt "$min_size" ]; then small=$((small + 1)); continue; fi
  if [ "$(( now - mt ))" -gt "$max_age" ]; then old=$((old + 1)); continue; fi
  # candidato valido (fresco + grande) — guarda o de mtime mais alto.
  if [ "$mt" -gt "$newest_mtime" ]; then newest="$f"; newest_mtime="$mt"; newest_size="$sz"; fi
done

if [ -n "$newest" ]; then
  echo "check_backup: OK age=$(( now - newest_mtime ))s size=${newest_size}B file=$(basename "$newest")"
  exit 0
fi

echo "check_backup: SEM backup valido em ${dir} (vistos=${seen} pequenos=${small} velhos=${old} min_size=${min_size} max_age=${max_age})" >&2
exit 1

#!/usr/bin/env bats
# hooks_check_backup.bats — gate de frescor de backup (ADR-018 B2 / issue #1455).
# Cobre o hook standalone (check_backup.sh) + a integracao com ensure_fresh_db_backup.
# "Valido" = fresco (idade <= max_age) E grande (tamanho >= min_size).

load helper

setup() {
  setup_sandbox
  BKDIR="$SANDBOX/backups"; mkdir -p "$BKDIR"
  HOOK="$DEPLOYER_HOME/hooks/check_backup.sh"
}
teardown() { teardown_sandbox; }

# _mkbackup <nome> <segundos-atras> [bytes]   (default 2048 = acima do min_size 1024)
_mkbackup() {
  local f="$BKDIR/$1" ago="${2:-0}" bytes="${3:-2048}"
  head -c "$bytes" /dev/zero > "$f"
  touch -d "@$(( $(date +%s) - ago ))" "$f"
}

# ---------------- hook standalone: frescor ----------------

@test "check_backup: backup valido (.sql.gz) -> 0" {
  _mkbackup "backup_full_20260709_020000.sql.gz" 3600
  BACKUP_DIR="$BKDIR" BACKUP_MAX_AGE=100800 run "$HOOK"
  [ "$status" -eq 0 ]
}

@test "check_backup: backup valido cifrado (.sql.gz.age) -> 0" {
  _mkbackup "backup_full_20260709_020000.sql.gz.age" 3600
  BACKUP_DIR="$BKDIR" BACKUP_MAX_AGE=100800 run "$HOOK"
  [ "$status" -eq 0 ]
}

@test "check_backup: backup velho (> max_age) -> 1 (stale)" {
  _mkbackup "backup_full_20260701_020000.sql.gz" 200000   # ~55h
  BACKUP_DIR="$BKDIR" BACKUP_MAX_AGE=100800 run "$HOOK"
  [ "$status" -eq 1 ]
}

@test "check_backup: dir sem backups -> 1" {
  BACKUP_DIR="$BKDIR" BACKUP_MAX_AGE=100800 run "$HOOK"
  [ "$status" -eq 1 ]
}

@test "check_backup: dir ausente -> 1" {
  BACKUP_DIR="$SANDBOX/nao-existe" BACKUP_MAX_AGE=100800 run "$HOOK"
  [ "$status" -eq 1 ]
}

@test "check_backup: escolhe o MAIS NOVO entre validos" {
  _mkbackup "backup_full_20260701_020000.sql.gz"     200000   # velho
  _mkbackup "backup_full_20260709_020000.sql.gz.age" 1800     # novo (cifrado)
  BACKUP_DIR="$BKDIR" BACKUP_MAX_AGE=100800 run "$HOOK"
  [ "$status" -eq 0 ]
}

@test "check_backup: ignora arquivos fora do naming" {
  _mkbackup "dump_aleatorio.sql.gz" 60          # nome errado -> ignorado
  _mkbackup "README.txt"            60
  BACKUP_DIR="$BKDIR" BACKUP_MAX_AGE=100800 run "$HOOK"
  [ "$status" -eq 1 ]   # nenhum backup_full_* valido
}

@test "check_backup: defaults (sem BACKUP_MAX_AGE) usam 28h" {
  _mkbackup "backup_full_20260709_020000.sql.gz" 90000   # 25h < 28h default
  BACKUP_DIR="$BKDIR" run "$HOOK"
  [ "$status" -eq 0 ]
}

# ---------------- hook standalone: tamanho (furo do 0-byte) ----------------

@test "check_backup: backup 0-byte fresco -> 1 (rejeita vazio)" {
  _mkbackup "backup_full_20260709_020000.sql.gz.age" 60 0
  BACKUP_DIR="$BKDIR" BACKUP_MAX_AGE=100800 run "$HOOK"
  [ "$status" -eq 1 ]
}

@test "check_backup: backup pequeno (< min_size) fresco -> 1" {
  _mkbackup "backup_full_20260709_020000.sql.gz.age" 60 200
  BACKUP_DIR="$BKDIR" BACKUP_MAX_AGE=100800 run "$HOOK"
  [ "$status" -eq 1 ]
}

@test "check_backup: 0-byte novo + valido velho-mas-fresco -> 0 (usa o valido)" {
  _mkbackup "backup_full_20260709_020000.sql.gz.age" 3600 2048   # valido, fresco
  _mkbackup "backup_full_20260709_030000.sql.gz.age" 60   0      # falho (0-byte), mais novo
  BACKUP_DIR="$BKDIR" BACKUP_MAX_AGE=100800 run "$HOOK"
  [ "$status" -eq 0 ]
}

@test "check_backup: BACKUP_MIN_SIZE customizado corta o borderline" {
  _mkbackup "backup_full_20260709_020000.sql.gz.age" 60 1500
  BACKUP_DIR="$BKDIR" BACKUP_MAX_AGE=100800 BACKUP_MIN_SIZE=4096 run "$HOOK"
  [ "$status" -eq 1 ]   # 1500 < 4096
}

@test "check_backup: BACKUP_MAX_AGE invalido -> 2 (fail-closed)" {
  _mkbackup "backup_full_20260709_020000.sql.gz" 60
  BACKUP_DIR="$BKDIR" BACKUP_MAX_AGE=abc run "$HOOK"
  [ "$status" -eq 2 ]
}

@test "check_backup: BACKUP_MIN_SIZE invalido -> 2 (fail-closed)" {
  _mkbackup "backup_full_20260709_020000.sql.gz" 60
  BACKUP_DIR="$BKDIR" BACKUP_MIN_SIZE=xyz run "$HOOK"
  [ "$status" -eq 2 ]
}

# ---------------- integracao com ensure_fresh_db_backup (lib/backup.sh) ----------------

@test "ensure_fresh_db_backup: hook + backup valido -> 0 (deploy liberado)" {
  _mkbackup "backup_full_20260709_020000.sql.gz.age" 3600
  export BACKUP_FRESHNESS_CMD="env BACKUP_DIR=${BKDIR} BACKUP_MAX_AGE=100800 ${HOOK}"
  run ensure_fresh_db_backup
  [ "$status" -eq 0 ]
}

@test "ensure_fresh_db_backup: hook + backup velho -> !=0 (REFUSE)" {
  _mkbackup "backup_full_20260701_020000.sql.gz.age" 200000
  export BACKUP_FRESHNESS_CMD="env BACKUP_DIR=${BKDIR} BACKUP_MAX_AGE=100800 ${HOOK}"
  run ensure_fresh_db_backup
  [ "$status" -ne 0 ]
}

@test "ensure_fresh_db_backup: hook + backup 0-byte -> !=0 (REFUSE)" {
  _mkbackup "backup_full_20260709_020000.sql.gz.age" 60 0
  export BACKUP_FRESHNESS_CMD="env BACKUP_DIR=${BKDIR} BACKUP_MAX_AGE=100800 ${HOOK}"
  run ensure_fresh_db_backup
  [ "$status" -ne 0 ]
}

@test "ensure_fresh_db_backup: hook + sem backup -> !=0 (REFUSE)" {
  export BACKUP_FRESHNESS_CMD="env BACKUP_DIR=${BKDIR} BACKUP_MAX_AGE=100800 ${HOOK}"
  run ensure_fresh_db_backup
  [ "$status" -ne 0 ]
}

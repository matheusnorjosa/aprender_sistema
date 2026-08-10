#!/usr/bin/env bats
# restore_db.bats — cobertura do restore_db.sh (issue #1611 / M26-01).
#
# O bug: a Step 1 (verificacao de integridade) rodava `gzip -t` INCONDICIONALMENTE,
# antes do branch que decifra `.age`. Producao grava SO `.sql.gz.age` (SEC-017), cujo
# cabecalho e' texto (`age-encryption.org/v1`), nao gzip -> `gzip -t` falhava e o unico
# formato de backup de prod nao restaurava ("Backup file is corrupted!" — factualmente falso).
#
# Estes testes sao HERMETICOS: stubam `age` e `psql` no PATH (bats e `age` nem sempre
# existem no runner). Validam o FLUXO DE CONTROLE do script — que e' onde o bug vive.
# O ensaio de DR real (age de verdade + Postgres) fica no test_dr.sh / staging.
#
# Rodar:  bats v2/infra/scripts/tests/restore_db.bats
#     ou:  docker run --rm -v "$PWD:/code" -w /code bats/bats v2/infra/scripts/tests/

setup() {
  SCRIPT="${BATS_TEST_DIRNAME}/../restore_db.sh"
  STUB_BIN="${BATS_TEST_TMPDIR}/bin"
  mkdir -p "$STUB_BIN"

  # Registro das chamadas ao psql (p/ assertar se o DROP DATABASE chegou a ser emitido).
  PSQL_LOG="${BATS_TEST_TMPDIR}/psql.log"
  : > "$PSQL_LOG"
  export PSQL_LOG

  # Stub `psql`: nunca toca banco real. Loga os argumentos, dreno o stdin do pipe de
  # restore e devolve um numero para as queries de contagem (Step 5).
  cat > "$STUB_BIN/psql" <<'STUB'
#!/usr/bin/env bash
echo "psql $*" >> "$PSQL_LOG"
cat >/dev/null 2>&1 || true   # dreno do pipe (age|gunzip|psql); EOF imediato nos -c
for a in "$@"; do
  case "$a" in
    *information_schema*|*"count("*|*"COUNT("*) echo 42 ;;
  esac
done
exit 0
STUB
  chmod +x "$STUB_BIN/psql"

  # Stub `age`: ignora cripto; ao ser chamado como `age -d -i KEY FILE`, emite o
  # conteudo "decifrado" apontado por AGE_PAYLOAD (um .gz real nos testes de sucesso,
  # ou lixo nao-gzip nos testes de corrupcao). Assim o cabecalho on-disk do .age pode
  # ser nao-gzip (como um .age de verdade) enquanto o age -d entrega o gzip.
  cat > "$STUB_BIN/age" <<'STUB'
#!/usr/bin/env bash
cat "$AGE_PAYLOAD"
STUB
  chmod +x "$STUB_BIN/age"

  export PATH="$STUB_BIN:$PATH"

  # Chave age dummy (o fix exige que ela seja legivel antes de decifrar).
  export BACKUP_AGE_KEY="${BATS_TEST_TMPDIR}/backup-key.txt"
  echo "AGE-SECRET-KEY-STUB" > "$BACKUP_AGE_KEY"

  # Payload "decifrado" valido: um gzip real de um SQL minimo.
  VALID_GZ="${BATS_TEST_TMPDIR}/payload.sql.gz"
  printf 'CREATE TABLE t(id int);\n' | gzip > "$VALID_GZ"

  # Fixture .age on-disk: bytes NAO-gzip (cabecalho age real) — e' o que a Step 1
  # antiga passava direto p/ `gzip -t`.
  AGE_BACKUP="${BATS_TEST_TMPDIR}/backup_full_20260720_010000.sql.gz.age"
  { printf 'age-encryption.org/v1\n'; head -c 64 /dev/urandom; } > "$AGE_BACKUP"

  # Fixture .sql.gz simples (nao cifrado) p/ nao-regressao.
  PLAIN_GZ="${BATS_TEST_TMPDIR}/backup_plain_20260101_000000.sql.gz"
  printf 'CREATE TABLE u(id int);\n' | gzip > "$PLAIN_GZ"
}

# Invoca o script confirmando o prompt "yes" via stdin.
run_restore() { printf 'yes\n' | bash "$SCRIPT" "$@"; }

# 1) .age VALIDO passa na verificacao de integridade (o coracao do #1611).
@test "restore .age valido passa na verificacao de integridade" {
  export AGE_PAYLOAD="$VALID_GZ"
  run run_restore "$AGE_BACKUP"
  [ "$status" -eq 0 ]
  [[ "$output" == *"Backup integrity OK"* ]]
  [[ "$output" != *"Backup file is corrupted"* ]]
}

# 2) .age realmente corrompido FALHA — e falha ANTES do DROP DATABASE (fail-closed).
@test "restore .age corrompido falha antes do DROP DATABASE" {
  # age -d "decifra" para lixo nao-gzip -> gzip -t do stream deve falhar.
  GARBAGE="${BATS_TEST_TMPDIR}/garbage.bin"
  printf 'isto nao e gzip valido' > "$GARBAGE"
  export AGE_PAYLOAD="$GARBAGE"
  run run_restore "$AGE_BACKUP"
  [ "$status" -ne 0 ]
  # Nenhum DROP DATABASE pode ter sido emitido (parou na Step 1).
  ! grep -q "DROP DATABASE" "$PSQL_LOG"
}

# 3) .sql.gz simples (nao cifrado) continua funcionando — nao-regressao.
@test "restore .sql.gz simples continua passando na integridade" {
  run run_restore "$PLAIN_GZ"
  [ "$status" -eq 0 ]
  [[ "$output" == *"Backup integrity OK"* ]]
}

# 4) BACKUP_DIR respeita a env var (hoje esta hardcoded em :17) — --latest seleciona de la.
@test "--latest respeita BACKUP_DIR da env var" {
  export BACKUP_DIR="${BATS_TEST_TMPDIR}"
  export AGE_PAYLOAD="$VALID_GZ"
  run run_restore --latest
  [ "$status" -eq 0 ]
  [[ "$output" == *"${BATS_TEST_TMPDIR}/"* ]]
  [[ "$output" == *"Backup integrity OK"* ]]
}

# 5) REGRESSAO: prod tem SO `.age` no BACKUP_DIR, entao o glob `*.sql.gz` nao casa e `ls`
# sai 2. Se pipefail fosse GLOBAL, `BACKUP_FILE=$(ls A B | head)` herdaria o 2 e `set -e`
# abortaria a selecao antes do guard. Este teste trava esse comportamento (pipefail e' local).
@test "--latest com SO .age no diretorio nao aborta na selecao" {
  local onlydir="${BATS_TEST_TMPDIR}/onlyage"
  mkdir -p "$onlydir"
  cp "$AGE_BACKUP" "$onlydir/backup_full_20260720_010000.sql.gz.age"
  export BACKUP_DIR="$onlydir"
  export AGE_PAYLOAD="$VALID_GZ"
  run run_restore --latest
  [ "$status" -eq 0 ]
  [[ "$output" == *"Backup integrity OK"* ]]
}

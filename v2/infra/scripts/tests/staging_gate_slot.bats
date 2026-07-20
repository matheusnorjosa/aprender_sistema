#!/usr/bin/env bats
# staging_gate_slot.bats — unit da derivacao de config do gate por slot (issue #1581).
#
# Garante que projeto Compose, tag de imagem e portas de host sao derivados do slot, de
# forma que dois gates em slots diferentes NAO colidam. Slot 0 = comportamento historico.
# Usa `--print-config` (nao toca Docker), entao roda deterministico e offline.
#
# Rodar:  bats v2/infra/scripts/tests/staging_gate_slot.bats
#     ou:  docker run --rm -v "$PWD:/code" -w /code bats/bats v2/infra/scripts/tests/

setup() {
  GATE="${BATS_TEST_DIRNAME}/../staging-gate.sh"
}

# cfg <chave> a partir da saida de --print-config (KEY=VALUE por linha)
val() { printf '%s\n' "$1" | grep -E "^${2}=" | cut -d= -f2-; }

# ---------------- slot 0: retrocompat (comportamento historico) ----------------

@test "slot 0: projeto/tag/portas = valores historicos (.env.staging)" {
  run bash "$GATE" --slot 0 --print-config
  [ "$status" -eq 0 ]
  [ "$(val "$output" project)" = "aprender_staging" ]
  [ "$(val "$output" tag)" = "staging-local" ]
  [ "$(val "$output" backend_port)" = "18002" ]
  [ "$(val "$output" db_port)" = "15434" ]
  [ "$(val "$output" redis_port)" = "16380" ]
  [ "$(val "$output" frontend_port)" = "15173" ]
}

# ---------------- slot 1 e 2: isolados ----------------

@test "slot 1: projeto/tag/portas com sufixo e offset do slot" {
  run bash "$GATE" --slot 1 --print-config
  [ "$status" -eq 0 ]
  [ "$(val "$output" project)" = "aprender_staging_s1" ]
  [ "$(val "$output" tag)" = "staging-local-s1" ]
  [ "$(val "$output" backend_image)" = "norjosamatheus/aprender-backend:staging-local-s1" ]
  [ "$(val "$output" backend_port)" = "18012" ]
  [ "$(val "$output" db_port)" = "15444" ]
  [ "$(val "$output" redis_port)" = "16390" ]
  [ "$(val "$output" frontend_port)" = "15183" ]
}

@test "slot 2 via DEV_SLOT (env)" {
  DEV_SLOT=2 run bash "$GATE" --print-config
  [ "$status" -eq 0 ]
  [ "$(val "$output" project)" = "aprender_staging_s2" ]
  [ "$(val "$output" tag)" = "staging-local-s2" ]
  [ "$(val "$output" backend_port)" = "18022" ]
}

@test "--slot tem precedencia sobre DEV_SLOT" {
  DEV_SLOT=2 run bash "$GATE" --slot 3 --print-config
  [ "$(val "$output" project)" = "aprender_staging_s3" ]
  [ "$(val "$output" backend_port)" = "18032" ]
}

# ---------------- slots distintos NAO colidem (o objetivo do #1581) ----------------

@test "slots 1 e 2 produzem projeto/portas/tag disjuntos" {
  run bash "$GATE" --slot 1 --print-config; local o1="$output"
  run bash "$GATE" --slot 2 --print-config; local o2="$output"
  [ "$(val "$o1" project)"      != "$(val "$o2" project)" ]
  [ "$(val "$o1" tag)"          != "$(val "$o2" tag)" ]
  [ "$(val "$o1" backend_port)" != "$(val "$o2" backend_port)" ]
  [ "$(val "$o1" db_port)"      != "$(val "$o2" db_port)" ]
  [ "$(val "$o1" redis_port)"   != "$(val "$o2" redis_port)" ]
  [ "$(val "$o1" frontend_port)" != "$(val "$o2" frontend_port)" ]
}

# ---------------- validacao de entrada ----------------

@test "slot nao-inteiro -> exit 64" {
  run bash "$GATE" --slot abc --print-config
  [ "$status" -eq 64 ]
}

@test "--print-config nao exige Docker (sai antes do build/up)" {
  # Sem daemon Docker acessivel, ainda assim deve imprimir e sair 0.
  DOCKER_HOST=tcp://127.0.0.1:1 run bash "$GATE" --slot 1 --print-config
  [ "$status" -eq 0 ]
  [ "$(val "$output" project)" = "aprender_staging_s1" ]
}

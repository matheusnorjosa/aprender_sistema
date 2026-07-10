#!/usr/bin/env bats
# integration.bats — reconcile + apply end-to-end com mocks de cosign/gh/curl.
# ADR-018 Fase 1 · issue #1513

load helper

setup() {
  setup_sandbox
  install_mock_curl
  export MOCK_POINTER="$SANDBOX/pointer.json"
  export MOCK_SIG="$SANDBOX/pointer.sig"; printf 'sigbundle' > "$MOCK_SIG"
  export MOCK_RELEASE="v2026.07.08-abc1234"
  write_pointer "$MOCK_POINTER" 5
}
teardown() { teardown_sandbox; }

# fixtures de stack para os testes do applier
_setup_apply_fixtures() {
  local a b; a="$(printf 'a%.0s' $(seq 1 64))"; b="$(printf 'b%.0s' $(seq 1 64))"
  export MOCK_STACK
  MOCK_STACK="$("$JQ_BIN" -nc '{Env:[{name:"IMAGE_TAG",value:"v2026.07.01-old0000"},{name:"BACKEND_HOST_PORT",value:"8000"}]}')"
  export MOCK_STACK_AFTER
  MOCK_STACK_AFTER="$("$JQ_BIN" -nc --arg bd "sha256:$a" --arg fd "sha256:$b" \
    '{Env:[{name:"IMAGE_TAG",value:"v2026.07.08-abc1234"},{name:"BACKEND_HOST_PORT",value:"8000"},{name:"BACKEND_DIGEST",value:$bd},{name:"FRONTEND_DIGEST",value:$fd}]}')"
  export MOCK_STACKFILE
  MOCK_STACKFILE="$("$JQ_BIN" -nc '{StackFileContent:"PINNEDCOMPOSE"}')"
  write_pointer "$HANDOFF_DIR/pointer.json" 5
  printf 'sigbundle' > "$HANDOFF_DIR/pointer.sig"
}

# ---------------- reconcile (deployer) ----------------

@test "reconcile: happy path (seq>selo) verifica e escreve o handoff" {
  seed_seal 4
  MOCK_COSIGN_RC=0 MOCK_GH_RC=0 run bash "$DEPLOYER_HOME/reconcile.sh"
  [ "$status" -eq 0 ]
  [ -f "$HANDOFF_DIR/pointer.json" ]
  [ -f "$HANDOFF_DIR/trigger" ]
}

@test "reconcile: assinatura do ponteiro invalida -> REFUSE, sem handoff" {
  seed_seal 4
  MOCK_COSIGN_RC=1 run bash "$DEPLOYER_HOME/reconcile.sh"
  [ "$status" -eq 10 ]
  [ ! -f "$HANDOFF_DIR/trigger" ]
}

@test "reconcile: sequence <= selo -> no-op (converged), sem handoff" {
  seed_seal 5
  MOCK_COSIGN_RC=0 run bash "$DEPLOYER_HOME/reconcile.sh"
  [ "$status" -eq 0 ]
  [ ! -f "$HANDOFF_DIR/trigger" ]
}

@test "reconcile: selo ausente -> REFUSE (nunca default silencioso)" {
  MOCK_COSIGN_RC=0 run bash "$DEPLOYER_HOME/reconcile.sh"
  [ "$status" -eq 10 ]
}

# ---------------- apply (applier) ----------------

@test "apply: happy path deploya por digest, confirma e SELA" {
  seed_seal 4; _setup_apply_fixtures
  MOCK_COSIGN_RC=0 MOCK_GH_RC=0 BACKUP_REQUIRED=0 CONFIRM_INTERVAL=1 \
    run bash "$DEPLOYER_HOME/apply.sh"
  [ "$status" -eq 0 ]
  [ "$(cat "$APPLIER_STATE_DIR/seal/last_sequence")" = "5" ]
}

@test "apply: replay (seq<=selo) -> REFUSE, nao deploya" {
  seed_seal 5; _setup_apply_fixtures
  MOCK_COSIGN_RC=0 MOCK_GH_RC=0 BACKUP_REQUIRED=0 run bash "$DEPLOYER_HOME/apply.sh"
  [ "$status" -eq 10 ]
}

@test "apply: compose drift -> REFUSE (nao faz PUT)" {
  seed_seal 4; _setup_apply_fixtures
  MOCK_STACKFILE="$("$JQ_BIN" -nc '{StackFileContent:"HACKED"}')"
  MOCK_COSIGN_RC=0 MOCK_GH_RC=0 BACKUP_REQUIRED=0 run bash "$DEPLOYER_HOME/apply.sh"
  [ "$status" -eq 10 ]
  [ ! -f "$SANDBOX/put_done" ]
}

@test "apply: backup exigido sem mecanismo -> REFUSE (fail-closed)" {
  seed_seal 4; _setup_apply_fixtures
  MOCK_COSIGN_RC=0 MOCK_GH_RC=0 BACKUP_REQUIRED=1 run bash "$DEPLOYER_HOME/apply.sh"
  [ "$status" -eq 10 ]
}

@test "apply: imagem nao-verificada (cosign falha) -> REFUSE" {
  seed_seal 4; _setup_apply_fixtures
  MOCK_COSIGN_RC=1 MOCK_GH_RC=0 BACKUP_REQUIRED=0 run bash "$DEPLOYER_HOME/apply.sh"
  [ "$status" -eq 10 ]
}

# ---------------- confirm pos-PUT (regressao do BUG #4, ADR-018 3e) ----------------
#
# Na 1a promocao REAL o PUT respondeu http=000 (false-red: a resposta nao volta
# durante o recreate) e o applier releu o Env UMA vez, IMEDIATAMENTE — o Portainer
# ainda nao tinha commitado => `put_unconfirmed_env` FAIL + breaker armado, num
# deploy que na verdade deu certo. O confirm pos-PUT agora faz POLL com deadline.

@test "apply: PUT false-red (000) + Env commitado com atraso -> confirma, SELA, sem breaker" {
  seed_seal 4; _setup_apply_fixtures
  MOCK_COSIGN_RC=0 MOCK_GH_RC=0 BACKUP_REQUIRED=0 CONFIRM_INTERVAL=1 \
    MOCK_PUT_CODE=000 MOCK_ENV_COMMIT_DELAY=2 \
    PUT_CONFIRM_INTERVAL=1 PUT_CONFIRM_TIMEOUT=30 \
    run bash "$DEPLOYER_HOME/apply.sh"
  [ "$status" -eq 0 ]
  [ "$(cat "$APPLIER_STATE_DIR/seal/last_sequence")" = "5" ]
  [ ! -f "$APPLIER_STATE_DIR/breaker/5" ]
}

@test "apply: API do Portainer indisponivel no recreate -> retenta a releitura e converge" {
  seed_seal 4; _setup_apply_fixtures
  MOCK_COSIGN_RC=0 MOCK_GH_RC=0 BACKUP_REQUIRED=0 CONFIRM_INTERVAL=1 \
    MOCK_PUT_CODE=000 MOCK_STACK_READ_FAIL=2 \
    PUT_CONFIRM_INTERVAL=1 PUT_CONFIRM_TIMEOUT=30 \
    run bash "$DEPLOYER_HOME/apply.sh"
  [ "$status" -eq 0 ]
  [ "$(cat "$APPLIER_STATE_DIR/seal/last_sequence")" = "5" ]
}

@test "apply: Env nunca commita -> FAIL fail-closed (nao sela, arma o breaker)" {
  seed_seal 4; _setup_apply_fixtures
  MOCK_COSIGN_RC=0 MOCK_GH_RC=0 BACKUP_REQUIRED=0 \
    MOCK_PUT_CODE=000 MOCK_ENV_COMMIT_DELAY=999 \
    PUT_CONFIRM_INTERVAL=1 PUT_CONFIRM_TIMEOUT=2 \
    run bash "$DEPLOYER_HOME/apply.sh"
  [ "$status" -eq 1 ]                                            # FAIL (nao REFUSE)
  [ "$(cat "$APPLIER_STATE_DIR/seal/last_sequence")" = "4" ]     # selo intacto
  [ "$(cat "$APPLIER_STATE_DIR/breaker/5")" = "1" ]
}

# O Env tem de refletir os DOIS digests: um PUT que so commitou o backend deixaria
# o frontend na imagem antiga — convergencia parcial nao pode selar.
@test "apply: Env commita so o backend -> FAIL (confirm exige backend E frontend)" {
  seed_seal 4; _setup_apply_fixtures
  local a; a="$(printf 'a%.0s' $(seq 1 64))"
  MOCK_STACK_AFTER="$("$JQ_BIN" -nc --arg bd "sha256:$a" \
    '{Env:[{name:"BACKEND_HOST_PORT",value:"8000"},{name:"BACKEND_DIGEST",value:$bd}]}')"
  MOCK_COSIGN_RC=0 MOCK_GH_RC=0 BACKUP_REQUIRED=0 \
    PUT_CONFIRM_INTERVAL=1 PUT_CONFIRM_TIMEOUT=2 \
    run bash "$DEPLOYER_HOME/apply.sh"
  [ "$status" -eq 1 ]
  [ "$(cat "$APPLIER_STATE_DIR/seal/last_sequence")" = "4" ]
}

# Regressao do bug (red-team #1): sob systemd o pai RUN_DIR e READ-ONLY para o
# applier. O applier NAO pode gravar lock/payload em RUN_DIR — so em /var/lib.
# Simulamos deixando RUN_DIR sem permissao de escrita e conferindo que o deploy
# ainda converge (antes do fix, `exec 8>RUN_DIR/lock` matava o processo).
@test "apply: RUN_DIR read-only ainda deploya (lock/payload em /var/lib)" {
  seed_seal 4; _setup_apply_fixtures
  chmod 0500 "$RUN_DIR"
  MOCK_COSIGN_RC=0 MOCK_GH_RC=0 BACKUP_REQUIRED=0 CONFIRM_INTERVAL=1 \
    run bash "$DEPLOYER_HOME/apply.sh"
  chmod 0700 "$RUN_DIR"
  [ "$status" -eq 0 ]
  [ "$(cat "$APPLIER_STATE_DIR/seal/last_sequence")" = "5" ]
  [ ! -e "$RUN_DIR/applier.lock" ]
}

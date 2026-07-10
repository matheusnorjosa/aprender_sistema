#!/usr/bin/env bats
# lib_guards.bats — unit dos guards de seguranca (deterministicos, sem rede).
# ADR-018 Fase 1 · issue #1513

load helper

setup()    { setup_sandbox; }
teardown() { teardown_sandbox; }

# ---------------- pointer_parse ----------------

@test "pointer_parse: ponteiro valido passa e seta globais" {
  write_pointer "$SANDBOX/p.json" 5
  pointer_parse "$SANDBOX/p.json"
  [ "$P_SEQUENCE" = "5" ]
  [ "$P_RELEASE" = "v2026.07.08-abc1234" ]
  [ "$P_BACKEND_REPO" = "norjosamatheus/aprender-backend" ]
}

@test "pointer_parse: schema desconhecido -> recusa" {
  write_pointer "$SANDBOX/p.json"
  "$JQ_BIN" '.schema = 2' "$SANDBOX/p.json" > "$SANDBOX/p2.json"
  run pointer_parse "$SANDBOX/p2.json"
  [ "$status" -ne 0 ]
}

@test "pointer_parse: release fora do padrao -> recusa" {
  write_pointer "$SANDBOX/p.json"
  "$JQ_BIN" '.release = "latest"' "$SANDBOX/p.json" > "$SANDBOX/p2.json"
  run pointer_parse "$SANDBOX/p2.json"
  [ "$status" -ne 0 ]
}

@test "pointer_parse: repo backend fora da allowlist -> recusa" {
  write_pointer "$SANDBOX/p.json"
  "$JQ_BIN" '.backend.repo = "attacker/backend"' "$SANDBOX/p.json" > "$SANDBOX/p2.json"
  run pointer_parse "$SANDBOX/p2.json"
  [ "$status" -ne 0 ]
}

@test "pointer_parse: digest curto/invalido -> recusa" {
  write_pointer "$SANDBOX/p.json"
  "$JQ_BIN" '.backend.digest = "sha256:deadbeef"' "$SANDBOX/p.json" > "$SANDBOX/p2.json"
  run pointer_parse "$SANDBOX/p2.json"
  [ "$status" -ne 0 ]
}

@test "pointer_parse: expires_at ausente -> recusa" {
  write_pointer "$SANDBOX/p.json"
  "$JQ_BIN" 'del(.expires_at)' "$SANDBOX/p.json" > "$SANDBOX/p2.json"
  run pointer_parse "$SANDBOX/p2.json"
  [ "$status" -ne 0 ]
}

@test "pointer_parse: JSON invalido -> recusa" {
  printf 'not json' > "$SANDBOX/p.json"
  run pointer_parse "$SANDBOX/p.json"
  [ "$status" -ne 0 ]
}

# ---------------- pointer_check_fresh ----------------

@test "pointer_check_fresh: expiry no futuro -> ok" {
  write_pointer "$SANDBOX/p.json" 5 "2999-01-01T00:00:00Z"
  pointer_parse "$SANDBOX/p.json"
  run pointer_check_fresh
  [ "$status" -eq 0 ]
}

@test "pointer_check_fresh: expiry no passado -> recusa" {
  write_pointer "$SANDBOX/p.json" 5 "2000-01-01T00:00:00Z"
  pointer_parse "$SANDBOX/p.json"
  run pointer_check_fresh
  [ "$status" -ne 0 ]
}

# ---------------- seal ----------------

@test "seal_read: ausente -> falha (nunca default silencioso)" {
  run seal_read
  [ "$status" -ne 0 ]
}

@test "seal_read: valor semeado le corretamente" {
  seed_seal 41
  run seal_read
  [ "$status" -eq 0 ]
  [ "$output" = "41" ]
}

@test "seal_read: conteudo nao-inteiro -> falha" {
  printf 'abc' > "${APPLIER_STATE_DIR}/seal/last_sequence"
  run seal_read
  [ "$status" -ne 0 ]
}

@test "seal_bump: avanca e nao retrocede" {
  seed_seal 41
  seal_bump 42
  [ "$(seal_read)" = "42" ]
  seal_bump 40      # nao deve retroceder
  [ "$(seal_read)" = "42" ]
}

# ---------------- compose drift ----------------

@test "compose_check_drift: live == pinned -> ok" {
  local sf; sf="$("$JQ_BIN" -nc '{StackFileContent:"PINNEDCOMPOSE"}')"
  run compose_check_drift "$sf"
  [ "$status" -eq 0 ]
}

@test "compose_check_drift: live != pinned -> recusa" {
  local sf; sf="$("$JQ_BIN" -nc '{StackFileContent:"ALTERADO"}')"
  run compose_check_drift "$sf"
  [ "$status" -ne 0 ]
}

# ---------------- portainer_env_value ----------------

@test "portainer_env_value: extrai o value do Env" {
  local stack; stack="$("$JQ_BIN" -nc '{Env:[{name:"IMAGE_TAG",value:"v1"},{name:"BACKEND_HOST_PORT",value:"8000"}]}')"
  run portainer_env_value "$stack" "BACKEND_HOST_PORT"
  [ "$output" = "8000" ]
}

# ---------------- image_verify (gate duro) ----------------

@test "image_verify: cosign ok, default cosign-only -> passa (attestation nao barra)" {
  # default REQUIRE_ATTESTATION=0: mesmo com gh falhando, cosign ok => passa
  MOCK_COSIGN_RC=0 MOCK_GH_RC=1 run image_verify "norjosamatheus/aprender-backend" "sha256:deadbeef"
  [ "$status" -eq 0 ]
}

@test "image_verify: cosign falha -> recusa (gate sempre ativo)" {
  MOCK_COSIGN_RC=1 run image_verify "norjosamatheus/aprender-backend" "sha256:deadbeef"
  [ "$status" -ne 0 ]
}

@test "image_verify: REQUIRE_ATTESTATION=1 + attestation falha -> recusa" {
  MOCK_COSIGN_RC=0 MOCK_GH_RC=1 REQUIRE_ATTESTATION=1 run image_verify "norjosamatheus/aprender-backend" "sha256:deadbeef"
  [ "$status" -ne 0 ]
}

@test "image_verify: REQUIRE_ATTESTATION=1 + cosign+attestation ok -> passa" {
  MOCK_COSIGN_RC=0 MOCK_GH_RC=0 REQUIRE_ATTESTATION=1 run image_verify "norjosamatheus/aprender-backend" "sha256:deadbeef"
  [ "$status" -eq 0 ]
}

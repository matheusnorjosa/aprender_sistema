#!/usr/bin/env bats
# staging_gate_scope.bats — unit do filtro test-aware do staging gate (issue #1582).
#
# Garante que PRs SOMENTE-DE-TESTE (que moram sob src/ e apps/) NAO exigem o gate, sem
# nunca dispensar o gate quando ha arquivo de runtime de verdade.
#
# Rodar:  bats v2/infra/scripts/tests/staging_gate_scope.bats
#     ou:  docker run --rm -v "$PWD:/code" -w /code bats/bats v2/infra/scripts/tests/

setup() {
  SCOPE="${BATS_TEST_DIRNAME}/../staging-gate-scope.sh"
}

# decide <arquivo...> -> imprime true|false (uma linha por arquivo no stdin do script)
decide() { printf '%s\n' "$@" | bash "$SCOPE"; }

# ---------------- dispensa: SOMENTE-TESTE (o bug do #1582) ----------------

@test "PR #1580 (App.session-expiry.test.tsx) dispensa o gate" {
  run decide "v2/frontend/src/__tests__/App.session-expiry.test.tsx"
  [ "$status" -eq 0 ]
  [ "$output" = "false" ]
}

@test "teste backend em apps/**/tests dispensa" {
  run decide "v2/backend/apps/core/tests/test_availability_service.py"
  [ "$output" = "false" ]
}

@test "conftest.py dispensa" {
  run decide "v2/backend/apps/core/tests/conftest.py"
  [ "$output" = "false" ]
}

@test "spec de frontend dispensa" {
  run decide "v2/frontend/src/components/Foo.spec.tsx"
  [ "$output" = "false" ]
}

@test "teste .js legado dispensa" {
  run decide "v2/frontend/src/hooks/__tests__/useConfig.test.js"
  [ "$output" = "false" ]
}

@test "so testes (backend + frontend juntos) dispensa" {
  run decide "v2/backend/apps/core/tests/test_x.py" "v2/frontend/src/__tests__/y.test.tsx"
  [ "$output" = "false" ]
}

# ---------------- exige: RUNTIME de verdade (nunca pular o gate) ----------------

@test "runtime frontend (App.tsx) exige o gate" {
  run decide "v2/frontend/src/App.tsx"
  [ "$output" = "true" ]
}

@test "runtime backend (views.py) exige o gate" {
  run decide "v2/backend/apps/core/views.py"
  [ "$output" = "true" ]
}

@test "requirements.txt exige o gate" {
  run decide "v2/backend/requirements.txt"
  [ "$output" = "true" ]
}

@test "Dockerfile.prod do frontend exige o gate" {
  run decide "v2/frontend/Dockerfile.prod"
  [ "$output" = "true" ]
}

@test "docker-compose de infra exige o gate" {
  run decide "v2/infra/docker-compose.yml"
  [ "$output" = "true" ]
}

@test "smoke_test_staging.sh exige o gate" {
  run decide "v2/infra/scripts/smoke_test_staging.sh"
  [ "$output" = "true" ]
}

@test "runtime + teste juntos exige o gate (nao pular por causa do teste)" {
  run decide "v2/frontend/src/App.tsx" "v2/frontend/src/__tests__/App.test.tsx"
  [ "$output" = "true" ]
}

# ---------------- dispensa: nao-runtime que ja era dispensado ----------------

@test "docs dispensa" {
  run decide "docs/guia.md"
  [ "$output" = "false" ]
}

@test "workflow de CI dispensa" {
  run decide ".github/workflows/frontend-ci.yml"
  [ "$output" = "false" ]
}

@test "diff vazio dispensa" {
  run decide ""
  [ "$output" = "false" ]
}

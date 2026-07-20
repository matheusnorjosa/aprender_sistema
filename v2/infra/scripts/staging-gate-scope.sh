#!/usr/bin/env bash
# staging-gate-scope.sh — decide se um conjunto de arquivos alterados exige o staging gate.
#
# O staging gate (evidencia 8/8) e [required] APENAS para mudancas que impactam RUNTIME
# (backend app/config, frontend src/public, imagens/compose de infra). Mudancas de CI,
# docs e SOMENTE-TESTE nao tocam runtime e sao intencionalmente dispensadas — como o
# comentario do workflow sempre prometeu.
#
# Bug corrigido (issue #1582): o runtime_regex casa `v2/frontend/src/` e `v2/backend/apps/`,
# que TAMBEM contem os testes (`src/__tests__/*.test.tsx`, `apps/**/tests/test_*.py`). Um PR
# so-de-teste (zero runtime) caia no gate `[required]`. Evidencia: PR #1580 (1 arquivo
# `App.session-expiry.test.tsx`, +9/-1) falhou o gate sem tocar codigo de producao.
#
# Correcao: remover os caminhos de teste ANTES de avaliar o runtime_regex. Se, depois de
# tirar os testes, ainda sobra algum arquivo de runtime -> o gate e exigido. E seguro: so
# dispensamos o gate quando TODOS os candidatos a runtime sao arquivos de teste (nunca
# pulamos o gate por causa de um arquivo de runtime de verdade).
#
# Uso:
#   git diff --name-only BASE HEAD | staging-gate-scope.sh   # imprime: true|false
#   printf '%s\n' "$lista_de_arquivos" | staging-gate-scope.sh
#
# Saida (stdout): `true`  -> exige o gate (havia arquivo de runtime nao-teste)
#                 `false` -> dispensa (docs/CI/somente-teste)
# Exit code: sempre 0 — a decisao esta no stdout, nao no status.

set -uo pipefail

# Caminhos SOMENTE-TESTE (dispensados). Cobre os layouts reais do repo:
#   frontend: src/**/__tests__/**, *.test.{ts,tsx,js,jsx}, *.spec.{ts,tsx,js,jsx}
#   backend:  apps/**/tests/**, test_*.py, conftest*.py
TEST_PATH_REGEX='(^|/)(__tests__|tests)/|(^|/)conftest[^/]*\.py$|(^|/)test_[^/]*\.py$|\.(test|spec)\.[cm]?[jt]sx?$'

# Caminhos que impactam RUNTIME (exigem o gate). Identico ao filtro historico do workflow.
RUNTIME_REGEX='^(v2/backend/(apps/|config/|requirements\.txt$)|v2/frontend/(src/|public/|Dockerfile\.prod$)|v2/infra/(docker-compose(\.[^/]*)?\.yml$|Dockerfile(\.prod|\.dev)?$|scripts/smoke_test_staging\.sh$))'

changed="$(cat)"

# 1) Tira os arquivos SOMENTE-TESTE da consideracao (`|| true`: se tudo era teste, o
#    grep -v nao casa nada e retornaria 1 sob pipefail).
runtime_candidates="$(printf '%s\n' "$changed" | grep -Ev "$TEST_PATH_REGEX" || true)"

# 2) Sobrou algum arquivo de runtime? Entao o gate e exigido.
if printf '%s\n' "$runtime_candidates" | grep -Eq "$RUNTIME_REGEX"; then
  echo "true"
else
  echo "false"
fi

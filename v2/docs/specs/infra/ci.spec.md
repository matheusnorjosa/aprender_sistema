---
title: CI/CD (GitHub Actions)
status: canonical
last_verified: 2026-06-22
sources_of_truth:
  - .github/workflows/ci.yaml
  - codecov.yml
  - .github/workflows/deploy.yaml
  - .github/workflows/_backend-test.yml
  - .github/workflows/backend-xdist-canary.yml
  - .github/workflows/staging-gate-audit.yml
  - .github/workflows/frontend-ci.yml
  - .github/actions/setup-python-deps/action.yml
  - v2/backend/scripts/rbac_lint.py
  - v2/scripts/xdist_canary_report.py
  - docs/operations/ci-check-policy.md
owner: infra
supersedes:
  - docs/operations/ci-check-policy.md
  - docs/operations/ci-backend-xdist-canary.md
  - docs/operations/ci-backend-xdist-stabilization-backlog.md
  - docs/operations/ci-security-checks.md
related:
  - ./deploy.spec.md
  - ../INDEX_SDD.md
  - ../README.md
---

# CI/CD (GitHub Actions)

## Propósito

Pipeline de integração e entrega contínua do AS v2 sobre GitHub Actions. A CI valida cada PR para `main` (lint, RBAC lint, type-check, testes backend paralelos, paridade Docker, frontend) e bloqueia merge enquanto os gates `[required]` não passarem; o deploy publica imagens no Docker Hub e atualiza a stack via **Portainer CE API**. Como **não existe staging remoto** (merge na `main` = deploy direto em produção, ADR-010), os gates de PR são a única rede de proteção antes da produção.

A nomenclatura dos checks é o contrato de governança: `[required]` bloqueia merge, `[info]` é informativo, `[ops]` é rotina manual/agendada fora do gate de PR. A SSOT desta convenção e da lista de checks obrigatórios é [`docs/operations/ci-check-policy.md`](../../../../docs/operations/ci-check-policy.md).

## Fonte de verdade no código

- **Gate principal de PR** — [`.github/workflows/ci.yaml`](../../../../.github/workflows/ci.yaml): backend impact detector, lint, rbac-lint, testes backend (split core + dev_tools), combine de cobertura, pyright, docker parity e o agregador `[required] tests`.
- **Reusable de teste backend** — [`.github/workflows/_backend-test.yml`](../../../../.github/workflows/_backend-test.yml): SSOT do setup de teste (services postgres/redis, env vars, `migrate`, dirs, `pytest`, artifact). Consumido por `ci.yaml` e pelo canary (#1401).
- **Canary xdist (não-bloqueante)** — [`.github/workflows/backend-xdist-canary.yml`](../../../../.github/workflows/backend-xdist-canary.yml) + report [`v2/scripts/xdist_canary_report.py`](../../../../v2/scripts/xdist_canary_report.py).
- **Gate de staging (evidência)** — [`.github/workflows/staging-gate-audit.yml`](../../../../.github/workflows/staging-gate-audit.yml).
- **Frontend** — [`.github/workflows/frontend-ci.yml`](../../../../.github/workflows/frontend-ci.yml): react doctor, build/lint, checklist (meta/a11y/security).
- **Deploy** — [`.github/workflows/deploy.yaml`](../../../../.github/workflows/deploy.yaml) → ver [`deploy.spec.md`](./deploy.spec.md).
- **RBAC lint (AST)** — [`v2/backend/scripts/rbac_lint.py`](../../../../v2/backend/scripts/rbac_lint.py).
- **Setup de deps Python (composite)** — [`.github/actions/setup-python-deps/action.yml`](../../../../.github/actions/setup-python-deps/action.yml).

## Contratos e invariantes

- **Checks `[required]` (gate de merge em `main`)** — devem ficar obrigatórios no ruleset `Protect main`: `[required] tests`, `[required] lint`, `[required] backend rbac-lint`, `[required] build/lint do frontend`, `[required] checklist tests (meta, a11y, security)`, `[required] dependency review`, `[required] architecture dependency guardrails`, `[required] Python Dependencies`, `[required] Frontend Dependencies`, `[required] Container Scan`, `[required] Secret Detection`, `[required] staging gate evidence`. SSOT: [`ci-check-policy.md`](../../../../docs/operations/ci-check-policy.md).
- **Least-privilege do `GITHUB_TOKEN`** — workflow-level default = `contents: read`; cada job que precisa de mais declara o seu (#1397). Em `deploy.yaml`, `contents: write` existe **apenas** no job `tag_and_release` (git tag + `gh release`); o job que builda/pusha imagem fica em `contents: read` (desacopla `contents:write` de alvo de supply-chain). No canary, `issues: write` vive só no job `canary-report` que comenta na issue #677.
- **Cobertura backend ≥ 85%** — `coverage combine` dos dois jobs (core + dev_tools) com `coverage report --fail-under=85`. Falha abaixo do limiar bloqueia o gate.
- **Paralelização xdist no gate (M3, #1402/#1403)** — gate usa `pytest -n auto --dist loadscope` (~15min→~5min). `loadscope` mantém testes da mesma classe/módulo no mesmo worker. Habilitado **só** após a suíte estabilizar (causa raiz: `transaction=True` truncava o seed RBAC; fix de re-seed pós-truncate). O canary cobre a matriz `workers×dist` mas **nunca** bloqueia (`fail_on_test_error=false`).
- **Backend impact detector (fail-safe)** — eventos não-PR (push/dispatch) forçam `backend_changed=true` (modo full seguro); PR sem base/head SHA também. O agregador `[required] tests` exige que os jobs backend ou tenham passado (impacto) ou tenham `skipped` (sem impacto) — nunca silenciosamente verde por engano.
- **Docker parity (#1401 carve-out)** — `docker-parity-backend` NÃO consome o reusable: usa topologia de container (`host.docker.internal`, `REQUIRE_DOCKER=1`, migrate in-container, build via buildx). Versões de postgres/redis aqui devem ser sincronizadas manualmente com o `services` do reusable (SSOT das versões: `postgres:15.13`, `redis:7.4`).
- **Gate de staging (evidência)** — para PRs com impacto em runtime (`v2/backend/apps|config|requirements.txt`, `v2/frontend/src|public|Dockerfile.prod`, `v2/infra/...`), o corpo do PR precisa de 3 marcadores literais (sem acento, crase normalizada): checkbox `make staging-full ... (8/8 PASS)`, checkbox `Evidencia anexada no PR`, e o texto `ALL 8 CHECKS PASSED`. PRs em draft ou sem impacto em runtime são pulados.
- **Guard rails de lint** — Black/isort/Flake8 + ban de `/api/v1/` fora da allowlist (#796); RBAC lint AST bane `user.groups.filter(name=...)` e classes `Is<Role>` fora da whitelist (idioma canônico: `permission_classes=[HasPerm("codename")]`).
- **Deploy/security gate** — invariantes de imutabilidade de tag, fire-and-forget com confirmação (#1396) e gate Trivy (bloqueia HIGH/CRITICAL) são contrato do deploy: ver [`deploy.spec.md`](./deploy.spec.md).
- **Não usar `paths` no gatilho `pull_request` de workflow que publica check `[required]`** (senão o check fica pendente para sempre e trava o ruleset). `frontend-ci.yml` removeu path filters de PR exatamente por isso.

## API / Interface

- **CI (`ci.yaml`)** — dispara em `push`/`pull_request` para `main`. Jobs: `backend-impact`, `lint`, `rbac-lint`, `backend-tests-core`, `backend-tests-devtools`, `backend-tests` (combine+threshold), `backend-typecheck`, `docker-parity-backend`, `tests` (agregador `[required]`).
- **Reusable (`_backend-test.yml`)** — `workflow_call` com inputs: `pytest_paths`, `pytest_extra_args`, `coverage_file`, `validate_test_paths`, `fail_on_test_error`, `emit_canary_metadata`, `artifact_name`/`artifact_paths` (obrigatórios), entre outros. Roda em Python 3.12 com `COVERAGE_CORE=sysmon` (sys.monitoring do 3.12, #1399).
- **Canary (`backend-xdist-canary.yml`)** — `schedule` (cron `20 10 * * *`), `workflow_dispatch` e `push` em paths do próprio canary. Matriz `workers=[2,auto] × dist=[loadscope,loadfile]`; publica snapshot na issue #677.
- **Deploy (`deploy.yaml`)** — `push` em `main` → staging-auto; `workflow_dispatch` com `target_environment` (staging|production), `promotion_tag`, `rollback_tag`. Interface detalhada (modos, gate de promoção, polling): [`deploy.spec.md`](./deploy.spec.md).

## Fluxos principais

**PR → merge (caminho feliz):**

1. `backend-impact` decide se a suíte backend roda (PR sem impacto em backend pula os jobs pesados; push/dispatch sempre full).
2. `lint` + `rbac-lint` (rápidos, paralelos).
3. `backend-tests-core` e `backend-tests-devtools` rodam via reusable com `-n auto --dist loadscope`, cada um emitindo um artifact de cobertura.
4. `backend-tests` baixa os dois artifacts, faz `coverage combine`, **exige ≥85% (gate bloqueante)** e sobe a cobertura para o Codecov (analytics **informational**, não bloqueia PR — config em `codecov.yml`; upload só quando o secret `CODECOV_TOKEN` existe).
5. `backend-typecheck` (pyright em `apps/core config`) e `docker-parity-backend` (smoke em imagem `Dockerfile.prod`) rodam em paralelo.
6. `tests` agrega: verde só se todos passaram (ou todos `skipped` quando sem impacto).
7. `frontend-ci` (react doctor + build/lint + checklist) e `staging-gate-audit` (evidência no corpo) completam o gate.
8. Merge em `main` dispara `deploy.yaml`.

**Deploy (resumo — detalhe em `deploy.spec.md`):** build+scan(Trivy)+push das imagens → `validate_existing_tag` (promotion/rollback) → `deploy` chama Portainer CE API atualizando só o `IMAGE_TAG` → post-deploy verification (polling de versão + fallback via Portainer API quando o health externo está inacessível por rede).

**Erros relevantes:**

- Cobertura < 85% → `backend-tests` falha → `tests` vermelho.
- xdist instável → fica **isolado** no canary (não bloqueia); recorrências viram issues de estabilização antes de promover ao gate.
- Corpo de PR sem os 3 marcadores → `staging gate evidence` falha (exceto draft / sem runtime impact).
- Deploy timeout (HTTP 000 por firewall) → confirmação fail-fast via GET do `IMAGE_TAG` e fallback Portainer (não assume sucesso cego).

## Decisões relacionadas (ADRs)

- **ADR-010** — Deploy Portainer→prod, sem staging remoto (referenciado em [`deploy.spec.md`](./deploy.spec.md) e no índice de infra).
- **#1397** — least-privilege do `GITHUB_TOKEN` (M2).
- **#1401** — reusable `_backend-test.yml` (SSOT de setup de teste).
- **#1402 / #1403** — estabilização xdist + promoção de `-n auto --dist loadscope` no gate (M3).
- **#1399** — `COVERAGE_CORE=sysmon` (sys.monitoring do Python 3.12).
- **#1396 / #1394** — fail-fast pós-timeout do Portainer + token via `curl --config` (fora do argv).

## Testes que cobrem

A CI é infra-as-code; sua "prova" são os próprios checks de gate e o canary, não testes unitários de aplicação:

- **Auto-asserção do gate** — passo `Assert backend gates passed` em `ci.yaml::tests` e `Assert split backend test jobs passed` em `backend-tests` (validam que os resultados esperados ocorreram, inclusive `skipped`).
- **Threshold de cobertura** — `coverage report --fail-under=85` em `ci.yaml`.
- **RBAC lint** — [`v2/backend/scripts/rbac_lint.py`](../../../../v2/backend/scripts/rbac_lint.py) sobre `apps/`.
- **Docker parity smoke** — `apps/core/tests/test_modular_imports.py` + `apps/core/tests/test_auth_backends.py` dentro do container.
- **Validação de paths de teste** — guard `no /app hardcoded` no reusable (`validate_test_paths`).
- **Suíte backend completa** — `apps/core/tests` + `apps/dev_tools/tests` (não há `apps/dat_ingest` — módulo removido).

## Pontos de atenção / dívidas conhecidas

- **Drift de versões postgres/redis** — `docker-parity-backend` é carve-out do reusable; bump no reusable não propaga sozinho (sincronizar manualmente). Apps = `core` + `dev_tools` apenas.
- **Sem `makemigrations --check` na CI** — migrations não são validadas no gate e o deploy não aplica migrations automaticamente (manuais em prod). Rastreado em **#1456**.
- **Canary só mostra top-5** — o report da issue #677 lista os 5 piores; a magnitude total de falhas pode ficar subdimensionada no comentário (vide M3: a issue citava 6 testes, eram 537).
- **`pull_request` sem path filters em checks `[required]`** — necessário para o ruleset, mas faz `frontend-ci` rodar mesmo em PRs sem mudança de frontend (custo aceito por governança).
- **react-doctor exige `--offline`** — o score depende de telemetria remota; sem `--offline` o gate é não-determinístico (memória `react-doctor-offline-determinism`).
- **Deploy é Portainer→prod sem staging remoto** — o gate de evidência de staging depende de `make staging-full` **local** do autor; não há ambiente staging que a CI valide. Detalhe e gaps de deploy em [`deploy.spec.md`](./deploy.spec.md).

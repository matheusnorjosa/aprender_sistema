---
title: CI/CD (GitHub Actions)
status: canonical
last_verified: 2026-08-26
sources_of_truth:
  - .github/workflows/ci.yaml
  - .github/workflows/promote.yml
  - v2/infra/docker-compose.prod.yml
  - codecov.yml
  - .github/workflows/deploy.yaml
  - .github/workflows/_backend-test.yml
  - .github/workflows/backend-xdist-canary.yml
  - .github/workflows/staging-gate-audit.yml
  - .github/workflows/frontend-ci.yml
  - .github/workflows/frontend-metrics-monthly.yml
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

Pipeline de integração e entrega contínua do AS v2 sobre GitHub Actions. A CI valida cada PR para `main` (lint, RBAC lint, type-check, testes backend paralelos, paridade Docker, frontend) e bloqueia merge enquanto os gates `[required]` não passarem. **Merge na `main` NÃO deploya** (modelo pull-based, [ADR-018](../../../../docs/architecture/project-decisions/ADR-018-pull-based-deploy.md)): dispara `deploy.yaml` ("Build, sign and release"), que faz build+scan+push das imagens no Docker Hub, **assina** (cosign keyless + provenance SLSA) e cria a tag imutável `vYYYY.MM.DD-<sha7>` + Release. Produção só muda por **promoção deliberada** (`promote.yml`, gated no Environment `production`) aplicada pelo agente `aprender-deployer` na VM01 (ver [`deploy.spec.md`](./deploy.spec.md)). Como **não existe staging remoto**, os gates de PR + o staging-gate local são a única rede de proteção antes da produção.

A nomenclatura dos checks é o contrato de governança: `[required]` bloqueia merge, `[info]` é informativo, `[ops]` é rotina manual/agendada fora do gate de PR. A SSOT desta convenção e da lista de checks obrigatórios é [`docs/operations/ci-check-policy.md`](../../../../docs/operations/ci-check-policy.md).

## Fonte de verdade no código

- **Gate principal de PR** — [`.github/workflows/ci.yaml`](../../../../.github/workflows/ci.yaml): backend impact detector, lint, rbac-lint, testes backend (split core + dev_tools), combine de cobertura, pyright, docker parity e o agregador `[required] tests`.
- **Reusable de teste backend** — [`.github/workflows/_backend-test.yml`](../../../../.github/workflows/_backend-test.yml): SSOT do setup de teste (services postgres/redis, env vars, `migrate`, dirs, `pytest`, artifact). Consumido por `ci.yaml` e pelo canary (#1401).
- **Canary xdist (não-bloqueante)** — [`.github/workflows/backend-xdist-canary.yml`](../../../../.github/workflows/backend-xdist-canary.yml) + report [`v2/scripts/xdist_canary_report.py`](../../../../v2/scripts/xdist_canary_report.py).
- **Gate de staging (evidência)** — [`.github/workflows/staging-gate-audit.yml`](../../../../.github/workflows/staging-gate-audit.yml).
- **Frontend** — [`.github/workflows/frontend-ci.yml`](../../../../.github/workflows/frontend-ci.yml): react doctor, build/lint, checklist (meta/a11y/security, contrato funcional e sem rolagem horizontal).
- **Deploy** — [`.github/workflows/deploy.yaml`](../../../../.github/workflows/deploy.yaml) → ver [`deploy.spec.md`](./deploy.spec.md).
- **RBAC lint (AST)** — [`v2/backend/scripts/rbac_lint.py`](../../../../v2/backend/scripts/rbac_lint.py).
- **Setup de deps Python (composite)** — [`.github/actions/setup-python-deps/action.yml`](../../../../.github/actions/setup-python-deps/action.yml).

## Contratos e invariantes

- **Checks `[required]` no ruleset `Protect main` (14)** — bloqueiam o merge **direto** (todos sempre-reportantes): `[required] tests` (agregador dos gates de backend), `lint`, `backend rbac-lint`, `build/lint do frontend`, `checklist tests (meta, a11y, security)`, `dependency review`, `docs quality (links + frontmatter)`, `react doctor quality gate`, `staging gate evidence`, `architecture dependency guardrails`, `Python Dependencies`, `Frontend Dependencies`, `Container Scan`, `Secret Detection`. Os gates **condicionais** de backend (`backend impact`, `backend tests`, `backend typecheck (pyright)`, `docker parity`, `backend migrate-integrity`) **não** entram direto — ficam `skipped` em PR sem impacto backend (o que travaria o merge em *pending*); são enforçados pelo `needs`+assert do agregador `[required] tests`. O **path-filtered** `rbac matrix doc drift` também não pode ir direto sem remover os `paths`. SSOT: [`ci-check-policy.md`](../../../../docs/operations/ci-check-policy.md).
- **Least-privilege do `GITHUB_TOKEN`** — workflow-level default = `contents: read`; cada job que precisa de mais declara o seu (#1397). Em `deploy.yaml`, `contents: write` existe **apenas** no job de tag/release (git tag + `gh release`); o job que builda/pusha imagem fica em `contents: read` (desacopla `contents:write` de alvo de supply-chain). A assinatura das imagens usa `id-token: write` (cosign keyless OIDC). `release-notes-producao.yml` (disparado por `workflow_run` do promote) tem `permissions: {}` no topo e `contents: write` só no job que edita a Release promovida e a marca *Latest*. No canary, `issues: write` vive só no job `canary-report` que comenta na issue #677.
- **Cobertura backend ≥ 85%** — `coverage combine` dos dois jobs (core + dev_tools) com `coverage report --fail-under=85`. Falha abaixo do limiar bloqueia o gate.
- **Paralelização xdist no gate (M3, #1402/#1403)** — gate usa `pytest -n auto --dist loadscope` (~15min→~5min). `loadscope` mantém testes da mesma classe/módulo no mesmo worker. Habilitado **só** após a suíte estabilizar (causa raiz: `transaction=True` truncava o seed RBAC; fix de re-seed pós-truncate). O canary cobre a matriz `workers×dist` mas **nunca** bloqueia (`fail_on_test_error=false`).
- **Backend impact detector (fail-safe)** — eventos não-PR (push/dispatch) forçam `backend_changed=true` (modo full seguro); PR sem base/head SHA também. O agregador `[required] tests` exige que os jobs backend ou tenham passado (impacto) ou tenham `skipped` (sem impacto) — nunca silenciosamente verde por engano.
- **Integridade de migrations bloqueia o merge** — `backend-migrate-integrity` roda `makemigrations --check --dry-run` (model-drift), aplica a cadeia RunPython em DB limpo e roda os testes `-m migrations`; está no `needs` + assert do agregador `[required] tests`. Logo, **model alterado sem a migration correspondente — ou cadeia RunPython quebrada — reprova o gate** (a saída de escape é `manage.py makemigrations` + commit da migration). Como todo job backend, fica `skipped` (não bloqueante) em PR sem impacto de backend. O check `check_migrations` veio do #1456; este ajuste ligou o job ao agregador required (antes era `[info]`, só reportava).
- **Docker parity (#1401 carve-out)** — `docker-parity-backend` NÃO consome o reusable: usa topologia de container (`host.docker.internal`, `REQUIRE_DOCKER=1`, migrate in-container, build via buildx). Versões de postgres/redis aqui devem ser sincronizadas manualmente com o `services` do reusable (SSOT das versões: `postgres:15.13`, `redis:7.4`).
- **Gate de staging (evidência)** — para PRs com impacto em runtime (`v2/backend/apps|config|requirements.txt`, `v2/frontend/src|public|Dockerfile.prod`, `v2/infra/...`), o corpo do PR precisa de 3 marcadores literais (sem acento, crase normalizada): checkbox `make staging-full ... (8/8 PASS)`, checkbox `Evidencia anexada no PR`, e o texto `ALL 8 CHECKS PASSED`. PRs em draft ou sem impacto em runtime são pulados.
- **Guard rails de lint** — Black/isort/Flake8 + ban de `/api/v1/` fora da allowlist (#796); RBAC lint AST bane `user.groups.filter(name=...)` e classes `Is<Role>` fora da whitelist (idioma canônico: `permission_classes=[HasPerm("codename")]`).
- **Ratchet de cast inseguro no frontend** — o job `[required] build/lint do frontend` roda [`check-unknown-casts.mjs`](../../../frontend/scripts/check-unknown-casts.mjs) (mais o auto-teste `node:test`): qualquer `as unknown` (toda dupla conversão passa por ele, inclusive `(x as unknown) as T`) e `as never` em `src/` de produção não podem passar do teto **por arquivo** de [`unknown-casts-baseline.json`](../../../frontend/scripts/unknown-casts-baseline.json) (exit 1); cair passa e o script sugere apertar o teto; baseline ilegível ou 0 arquivos medidos sai 2.
- **Ratchet de rolagem horizontal (Programa C)** — o job `[required] checklist tests` roda [`sem-rolagem-horizontal.spec.ts`](../../../frontend/e2e/checklist/sem-rolagem-horizontal.spec.ts) (360 e 768 px) e [`sem-rolagem-horizontal.desktop.spec.ts`](../../../frontend/e2e/checklist/sem-rolagem-horizontal.desktop.spec.ts) (1024 e 1280 px, com a barra de rolagem clássica ocupando largura) sem mudar o workflow: o project `checklist` pega todo spec de `e2e/checklist/`, e os dados vêm do `seed_frontend_contract_data`, que o job já roda. A dívida medida fica em `PENDENTES` com `test.fail`; tela consertada faz o teste falhar até a combinação sair da lista. A pré-condição prova a tela, não a casca (título próprio, casca autenticada, nenhum erro na tela, a linha com o texto do seed, nenhuma requisição da mesma origem com falha), para uma tela quebrada nunca passar como falha esperada. No job `[required] build/lint do frontend`, o ESLint barra `Table` do `antd` (barris, caminhos profundos, `rc-table`, `import()` e `require`) fora da allowlist de [`eslint.tabela-antd-allowlist.js`](../../../frontend/eslint.tabela-antd-allowlist.js), e o Vitest trava as duas listas: o conjunto de arquivos que importam `Table`, medido sem os `eslint-disable`, tem de ser exatamente a allowlist, e `PENDENTES` tem de caber na linha de base medida, com tamanho igual a um teto que só desce. Custo medido em 29/09/2026: ~4,7 min com 2 workers para 192 testes (os dois specs); se o job passar do orçamento, a largura de 768 vai para um job noturno. Padrão: [`pages.spec.md`](../frontend/pages.spec.md), seção "Padrão responsivo".
- **Relatório do frontend no PR (`[info] frontend PR report`)** — em PR que toca `v2/frontend/**`, o job junta o `size-limit --json` do build/lint e o `.lighthouseci/summary.json` do Lighthouse e mantém **um** comentário por PR (achado pelo marcador `<!-- as-frontend-report -->`, atualizado a cada push) via [`pr-report.mjs`](../../../frontend/scripts/pr-report.mjs). Só observa: os passos que alimentam o relatório têm `continue-on-error` e não mudam gate nenhum; `pull-requests: write` vive só nesse job, e PR de fork/Dependabot fica só com o job summary.
- **Acompanhamento mensal do frontend (`[ops] frontend monthly metrics`)** — [`frontend-metrics-monthly.yml`](../../../../.github/workflows/frontend-metrics-monthly.yml) (cron dia 1º 12:17 UTC + `workflow_dispatch`) mede a `main` com o mesmo size-limit e Lighthouse e comenta, sempre em comentário novo, na issue #2066 (a série histórica) via `pr-report.mjs --mensal`; a linha "Contra a medição anterior (data)" compara, por métrica, com o valor não nulo mais recente que os comentários anteriores gravaram num bloco oculto (`<!-- as-frontend-monthly-dados … -->`). O Lighthouse não bloqueia merge (decisão do dono, 28/09). Dois jobs: `medir` (npm, build, size-limit, Lighthouse) só lê o repo; `publicar` tem o `issues: write`, não roda nada do npm e posta mesmo com `medir` vermelho ("Indisponível" no que faltar).
- **Deploy/security gate** — imutabilidade de tag, assinatura das imagens (cosign keyless + provenance SLSA) e gate Trivy (bloqueia HIGH/CRITICAL) são contrato do deploy; a aplicação em prod é **por digest**, verificada pelo agente na VM01 (`promote.yml` → `deploy-pointer` → `aprender-deployer`): ver [`deploy.spec.md`](./deploy.spec.md).
- **Não usar `paths` no gatilho `pull_request` de workflow que publica check `[required]`** (senão o check fica pendente para sempre e trava o ruleset). `frontend-ci.yml` removeu path filters de PR exatamente por isso.

## API / Interface

- **CI (`ci.yaml`)** — dispara em `push`/`pull_request` para `main`. Jobs: `backend-impact`, `lint`, `rbac-lint`, `backend-tests-core`, `backend-tests-devtools`, `backend-tests` (combine+threshold), `backend-typecheck`, `docker-parity-backend`, `tests` (agregador `[required]`).
- **Reusable (`_backend-test.yml`)** — `workflow_call` com inputs: `pytest_paths`, `pytest_extra_args`, `coverage_file`, `validate_test_paths`, `fail_on_test_error`, `emit_canary_metadata`, `artifact_name`/`artifact_paths` (obrigatórios), entre outros. Roda em Python 3.12 com `COVERAGE_CORE=sysmon` (sys.monitoring do 3.12, #1399).
- **Canary (`backend-xdist-canary.yml`)** — `schedule` (cron `20 10 * * *`), `workflow_dispatch` e `push` em paths do próprio canary. Matriz `workers=[2,auto] × dist=[loadscope,loadfile]`; publica snapshot na issue #677.
- **Deploy (`deploy.yaml`)** — `push` em `main` → build+scan+push+**sign**+tag/release (não deploya). Promoção/rollback e mudança de prod ficam no `promote.yml` (gated no Environment `production`) + agente `aprender-deployer` na VM01. O `workflow_dispatch` do `deploy.yaml` **não** tem mais `target_environment`/`promotion_tag`/`rollback_tag`. Interface detalhada: [`deploy.spec.md`](./deploy.spec.md).

## Fluxos principais

**PR → merge (caminho feliz):**

1. `backend-impact` decide se a suíte backend roda (PR sem impacto em backend pula os jobs pesados; push/dispatch sempre full).
2. `lint` + `rbac-lint` (rápidos, paralelos).
3. `backend-tests-core` e `backend-tests-devtools` rodam via reusable com `-n auto --dist loadscope`, cada um emitindo um artifact de cobertura.
4. `backend-tests` baixa os dois artifacts, faz `coverage combine`, **exige ≥85% (gate bloqueante)** e sobe a cobertura para o Codecov (analytics **informational**, não bloqueia PR — config em `codecov.yml`; upload só quando o secret `CODECOV_TOKEN` existe).
5. `backend-typecheck` (pyright em `apps/core config`) e `docker-parity-backend` (smoke em imagem `Dockerfile.prod`) rodam em paralelo.
6. `tests` agrega: verde só se todos passaram (ou todos `skipped` quando sem impacto).
7. `frontend-ci` (react doctor + build/lint + checklist) e `staging-gate-audit` (evidência no corpo) completam o gate.
8. Merge em `main` dispara `deploy.yaml` (build+sign+release; **não** deploya — prod só muda por `promote.yml` gated).

**Deploy (resumo — detalhe em `deploy.spec.md`):** merge na `main` → build+scan(Trivy)+push das imagens → **assina** (cosign keyless + provenance SLSA) → cria tag imutável `vYYYY.MM.DD-<sha7>` + Release. Prod muda depois em dois passos deliberados: `promote.yml` (gated no Environment `production`) resolve tag→digest e assina o ponteiro no branch `deploy-pointer`; o agente `aprender-deployer` na VM01 verifica com cosign e aplica **por digest** em `127.0.0.1:9443`, confirmando de dentro da VM.

**Erros relevantes:**

- Cobertura < 85% → `backend-tests` falha → `tests` vermelho.
- xdist instável → fica **isolado** no canary (não bloqueia); recorrências viram issues de estabilização antes de promover ao gate.
- Corpo de PR sem os 3 marcadores → `staging gate evidence` falha (exceto draft / sem runtime impact).
- Aplicação em prod (agente na VM01) é **fail-closed** por degrau (assinatura, digest, anti-rollback, drift do compose, backup fresco) e confirma em `localhost` — imune ao *false-red* do `:9443` público.

## Decisões relacionadas (ADRs)

- **[ADR-018](../../../../docs/architecture/project-decisions/ADR-018-pull-based-deploy.md)** — deploy **pull-based**: `promote.yml` (gated) → ponteiro assinado no branch `deploy-pointer` → agente `aprender-deployer` aplica por digest na VM01. **Supersede** o [ADR-010](../../../../docs/architecture/project-decisions/ADR-010-deploy-portainer-direct-to-prod.md) (PUT do CI ao Portainer `:9443` público), desligado no cutover #1515 e removido na Fase 4 #1516. Detalhe em [`deploy.spec.md`](./deploy.spec.md).
- **#1397** — least-privilege do `GITHUB_TOKEN` (M2).
- **#1401** — reusable `_backend-test.yml` (SSOT de setup de teste).
- **#1402 / #1403** — estabilização xdist + promoção de `-n auto --dist loadscope` no gate (M3).
- **#1399** — `COVERAGE_CORE=sysmon` (sys.monitoring do Python 3.12).
- **#1396 / #1394** (histórico, modelo antigo) — fail-fast pós-timeout do Portainer + token via `curl --config` (fora do argv); superados pelo modelo pull-based (ADR-018).

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
- **Canary só mostra top-5** — o report da issue #677 lista os 5 piores; a magnitude total de falhas pode ficar subdimensionada no comentário (vide M3: a issue citava 6 testes, eram 537).
- **`pull_request` sem path filters em checks `[required]`** — necessário para o ruleset, mas faz `frontend-ci` rodar mesmo em PRs sem mudança de frontend (custo aceito por governança).
- **react-doctor exige `--offline`** — o score depende de telemetria remota; sem `--offline` o gate é não-determinístico (memória `react-doctor-offline-determinism`).
- **Sem staging remoto; prod só muda por promoção gated (pull-based)** — merge na `main` não deploya; o gate de evidência de staging depende de `make staging-full` **local** do autor; não há ambiente staging que a CI valide. Detalhe e gaps de deploy em [`deploy.spec.md`](./deploy.spec.md).

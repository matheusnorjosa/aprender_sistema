# Referência — workflows do `.github/workflows/`

Consultado sob demanda pela skill `ci-github-actions`. Nomes (`name:`) e arquivo reais.

## Backend / orquestração

- **`ci.yaml`** — *CI – Continuous Integration*. Orquestrador. `backend-impact` (gate de impacto) → `lint`, `rbac-lint`, `backend-tests-core` + `backend-tests-ingest-devtools` (via reusable), `backend-migrate-integrity`, `backend-typecheck` (pyright), `docker-parity-backend`, e o agregador `tests`. Faz `coverage combine` (≥85%) e upload Codecov (guarded por token).
- **`_backend-test.yml`** — *Backend Test (reusable)*. Consumido pelo `ci.yaml`. Roda `pytest -n auto --dist loadscope`. Input `run_migrations` (default true) gateia o passo `manage.py migrate`; o gate core/ingest passa `run_migrations:false` + `--no-migrations`.

## Frontend

- **`frontend-ci.yml`** — *frontend-ci*. `build/lint do frontend`, `react doctor quality gate` (exige `--offline`), `checklist tests (meta, a11y, security)`, e `[info] e2e journeys` (Playwright, `continue-on-error: true` — candidato a promover a `[required]`).

## Segurança / supply-chain

- **`security-scan.yml`** — *Security Scan*. `Container Scan` (Trivy), `Secret Detection` (Gitleaks), Bandit. CVE de SO no Trivy → cache-bust `apt/apk upgrade` por `GIT_SHA` no `Dockerfile.prod`.
- **`dependency-review-scorecard.yml`** — *Dependency Review & Scorecard*. `dependency review` + OpenSSF Scorecard (`[info]`).
- **`strict-security-headers.yml`** — *Strict Security Headers*. Valida headers de segurança (CSP/HSTS/etc.).
- **`slsa-provenance.yml`** — *SLSA Provenance and Signing*. Proveniência/assinatura de artefatos.

## Docs / arquitetura

- **`docs-quality.yml`** — *Docs Quality*. `[required]`, **sem path filter** (precisa sempre reportar status). Roda `scripts/check_doc_links.py` (links vivos) + `scripts/check_doc_frontmatter.py` (frontmatter das specs).
- **`docs.yml`** — *Documentation*. `mkdocs build --strict` (árvore `docs/`).
- **`architecture-guardrails.yml`** — *Architecture Guardrails*. Guardrails de fronteiras/camadas de arquitetura.

## Gate de processo / deploy

- **`staging-gate-audit.yml`** — *Staging Gate Evidence*. `[required]`. Dispara em `v2/backend/apps/`; exige os 3 marcadores literais no corpo do PR (ver SKILL.md). `on: edited` re-roda.
- **`deploy.yaml`** — *Build, sign and release (main)*. Pós-merge: build/scan/push no Docker Hub, **assina** (cosign keyless + SLSA), cria tag imutável + GitHub Release. **NÃO deploya** — o job `deploy` (PUT ao `:9443` público) foi deletado na Fase 4 do ADR-018 (#1516).
- **`promote.yml`** — *Promote*. `workflow_dispatch`, gated no Environment `production` (required reviewer). Resolve tag→digest (com retry: o Docker Hub flaka), exige imagens assinadas, assina o `production.json` e publica no branch protegido `deploy-pointer`. O agente `aprender-deployer` (VM01, systemd ~60s) lê, verifica e aplica por digest em `127.0.0.1:9443` — imune ao *false-red* do `:9443`.

## Monitoramento (não bloqueia merge)

- **`ci-runtime-telemetry.yml`** — *CI Runtime Telemetry*. Cron diário; falha se p95 regride >35% vs `v2/docs/analysis/ci-runtime-baseline.json`. Re-baseline = promover report fresco ao JSON.
- **`backend-xdist-canary.yml`** — *Backend xdist Canary (non-blocking)*. 4 matrix runs; posta evidência de estabilidade (issue de tracking #677).
- **`agent-browser-smoke.yml`** — *agent-browser-smoke*. Smoke de browser via agente.

## Composite actions (`.github/actions/`)

- **`setup-python-deps/action.yml`** — instala deps Python (`requirements*.txt`). **No `BACKEND_IMPACT_REGEX`?** — gap conhecido (#1459): editar essa action sozinha pode dar false-green no gate.
- **`setup-node-deps/action.yml`** — instala deps Node/npm.

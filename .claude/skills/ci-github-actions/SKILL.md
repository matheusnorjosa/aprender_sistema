---
name: ci-github-actions
description: CI/CD do AS v2 (GitHub Actions). Use ao editar workflows, destravar checks [required], preparar PR para o staging gate, debugar CI vermelha, ou mexer no deploy. Cobre os gates obrigatorios, os 3 marcadores do staging-gate, pytest --no-migrations e os flakes recorrentes.
---

# CI/CD — Aprender Sistema v2 (GitHub Actions)

> Merge na `main` = **deploy direto pra prod** via Portainer. CI verde não é burocracia — é o portão de produção.
> SSOT do fluxo: [`v2/docs/specs/infra/ci.spec.md`](../../../v2/docs/specs/infra/ci.spec.md). Detalhe por-workflow: [reference/workflows.md](reference/workflows.md).

## Arquitetura

- **`ci.yaml`** orquestra o backend: `backend-impact` decide se a suíte roda (PR sem impacto em backend pula os jobs pesados); chama o reusable **`_backend-test.yml`** para `backend-tests-core` e `backend-tests-ingest-devtools` (`-n auto --dist loadscope`), faz `coverage combine` (gate **≥85%**) e roda `backend-migrate-integrity`.
- **`frontend-ci.yml`**: build/lint, react-doctor (exige `--offline`), checklist (meta/a11y/security), `[info] e2e journeys`.
- Segurança/infra: `security-scan.yml`, `dependency-review-scorecard.yml`, `strict-security-headers.yml`, `architecture-guardrails.yml`, `docs-quality.yml`, `staging-gate-audit.yml`.
- **`deploy.yaml`** (*Build, sign and release*): pós-merge, **não deploya** — build/scan/push + cosign + tag/release. Prod muda por `promote.yml` (gate `production`) + agente pull-based na VM01 (ADR-018).
- Monitoramento agendado (não bloqueia): `ci-runtime-telemetry.yml`, `backend-xdist-canary.yml`.

## Checks `[required]` (precisam estar verdes p/ merge)

`backend impact` · `backend tests (runner)` · `backend typecheck (pyright)` · `backend rbac-lint` · `docker parity (backend)` · `tests` (agregador) · `docs quality (links + frontmatter)` · `staging gate evidence` · `lint` · `build/lint do frontend` · `checklist tests` · `react doctor quality gate` · `Container Scan` · `Secret Detection` · `Python/Frontend Dependencies` · `dependency review`.

> Se `backend-impact` der `backend_changed=false`, os jobs de teste backend ficam **skipping** (correto p/ PR que não toca `v2/backend/`) e o agregador `tests` fica verde.

## Procedimento: deixar um PR verde

1. **Localize a falha:** `gh run view <id> --log-failed` (ou `gh pr checks <PR>`).
2. **Reproduza local** (CP-01, Docker): `docker exec aprender_dev-web-1 pytest apps/core/tests/ -q`; pyright via `cd v2/backend && pyright apps/core config`; lint com black+isort+flake8 nos arquivos tocados.
3. **Staging gate** (se tocar `v2/backend/apps/`): ver abaixo — exige marcadores literais no corpo do PR.
4. **Base mudou →** `gh pr update-branch <PR>` e **esperar o re-run** (~5-15min) antes de mergear; "N of N required checks expected" some sozinho.
5. **Done quando:** `gh pr view <PR> --json mergeStateStatus` = `CLEAN` e 0 checks `FAILURE`/pending.

## Staging gate — marcadores EXATOS (literais)

`staging-gate-audit.yml` dispara em mudanças sob `v2/backend/apps/` e exige no **corpo do PR** os 3 marcadores **literais** (regex sem acento):

- `- [x] make staging-full executado com sucesso (8/8 PASS)`
- `- [x] Evidencia anexada no PR`  ← **"Evidencia" SEM acento**
- texto `ALL 8 CHECKS PASSED`

Checkboxes precisam estar **marcados** (`- [x]`). Editar o body re-roda o gate (`on: edited`). PR draft pula o gate.

## Gotchas recorrentes (já nos morderam)

- **`pytest --no-migrations`** no gate (M4 #1404): seeds RBAC vêm de fixtures (`ensure_base_groups` + `seed_functional_permissions`), não das RunPython. Testes que exercitam data-migrations levam `@pytest.mark.migrations` e rodam no job `backend-migrate-integrity`.
- **Deploy `blob unknown to registry`** no buildx `--push` = **flake transitório**; `gh run rerun <id> --failed`. Prod intacta.
- **Rajada de merges** = N deploys seriais; alguns falham `curl 28` no Portainer 9443 (transiente) mas o último vence — não é alarme se o deploy do HEAD = success + prod HTTP 200.
- **Gate Trivy travando por CVE de SO** (não da app): cache-bust do `apt/apk upgrade` por `GIT_SHA` no `Dockerfile.prod` (#1407).
- **Codecov**: upload só roda `if: env.CODECOV_TOKEN != ''` (tokenless é rejeitado) — sem o secret, é pulado; cobertura é enforçada no gate, não no Codecov.
- **react-doctor**: score depende de telemetria remota → exige `--offline` para ser determinístico.
- **Telemetria de runtime** (`ci-runtime-telemetry.yml`): cron que falha se p95 regride >35% vs `v2/docs/analysis/ci-runtime-baseline.json`. Não bloqueia PR; re-baseline = promover o report fresco ao JSON.

## NÃO fazer

- Nunca `git push` direto na `main` (CP-07, enforce por hook) — sempre branch + PR.
- Nunca `systemctl restart docker` na VM01 (Kaspersky/KESL derruba o site) — usar `systemctl restart kesl`.
- Mudança em `docker-compose.prod.yml` exige update manual no Editor do Portainer (não vai pelo deploy).

---
name: ci-github-actions
description: CI/CD do AS v2 (GitHub Actions). Use ao editar workflows, destravar checks [required], preparar PR para o staging gate, debugar CI vermelha, ou mexer no deploy. Cobre os gates obrigatorios, os 3 marcadores do staging-gate, pytest --no-migrations e os flakes recorrentes.
---

# CI/CD — Aprender Sistema v2 (GitHub Actions)

> **Merge na `main` NÃO deploya** (ADR-018, 2026-07-10). O merge produz um artefato assinado e
> *promovível*; produção só muda por promoção humana (`promote.yml` + Environment `production`).
> CI verde continua não sendo burocracia — é o que decide se existe artefato promovível.
> ~~"Merge na `main` = deploy direto pra prod via Portainer"~~ era o **ADR-010**, **revogado**: os
> jobs `deploy` e `validate_existing_tag` foram **deletados** no **#1516**.
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

## Procedimento: levar uma versão a produção

1. **Merge na `main`** → `deploy.yaml` builda, escaneia e faz push das imagens, dispara o `sign` (cosign keyless + SLSA) e gera a tag imutável `vYYYY.MM.DD-<sha7>` + GitHub Release. `gh release list --limit 3` mostra a tag. **A tag não prova assinatura:** `tag_and_release` tem `needs: [prepare, build_and_push]` e o `sign` está fora do `needs` **e** fora do `if` (`.github/workflows/deploy.yaml:231-235`) — tag e Release nascem mesmo com o `sign` falhando. O gate **duro** de assinatura é o `promote.yml` (`.github/workflows/promote.yml:139`, *“Gate duro — imagens DEVEM estar assinadas (cosign)”*), e o agente da VM01 recusa digest que não passe no `cosign verify`.
2. **Promover:** `gh workflow run promote.yml -f release=v2026.MM.DD-<sha7>`.
3. **Aprovar** no GitHub Environment `production` (*required reviewer*). Enquanto isso o run fica `status: waiting` — não é falha.
4. **A VM01 puxa** (systemd, ~60s) e aplica **por digest**; o `PUT` é do `aprender-applier` em `127.0.0.1:9443`. Cada degrau é **fail-closed** — `REFUSE` significa que produção não mudou.
5. **Verificar:** `/api/version/` devolve a **release (tag)**, **não** o digest — payload `{"version": ...}`, com `git_sha`/`build_date` só para `is_staff` (`v2/backend/apps/core/views_health.py:93-99`). Compare com o `release` do `production.json`; mais `/api/readyz/`. A cor do job **não** é evidência.

**Rollback** = promover a tag anterior com `-f rollback=true` (ainda exige `sequence` > selo). Não existe `deploy.yaml -f rollback_tag=...`, e não há auto-rollback — migrations são forward-only.

## Gotchas recorrentes (já nos morderam)

- **`pytest --no-migrations`** no gate (M4 #1404): seeds RBAC vêm de fixtures (`ensure_base_groups` + `seed_functional_permissions`), não das RunPython. Testes que exercitam data-migrations levam `@pytest.mark.migrations` e rodam no job `backend-migrate-integrity`.
- **`blob unknown to registry`** no buildx `--push` = **flake transitório** do Docker Hub; `gh run rerun <id> --failed`. Prod intacta (nem foi tocada).
- **Rajada de merges** = N builds, **não** N deploys. Nenhum deles muda produção; o que interessa é a tag do HEAD existir e estar assinada. ~~"alguns falham `curl 28` no Portainer 9443 mas o último vence"~~ era do job `deploy`, **deletado** (#1516) — o *false-red* do `:9443` deixou de aparecer no CI porque a confirmação passou a ser feita de dentro da VM.
- **`promote.yml` parado em `waiting`** = gate do Environment `production` esperando reviewer. Não é falha de CI.
- **`REFUSE compose_drift`** no applier = `docker-compose.prod.yml` mudou sem re-captura do `trust/compose.pinned.yml` na VM. É o comportamento desejado, não um bug.
- **Gate Trivy travando por CVE de SO** (não da app): cache-bust do `apt/apk upgrade` por `GIT_SHA` no `Dockerfile.prod` (#1407).
- **Codecov**: upload só roda `if: env.CODECOV_TOKEN != ''` (tokenless é rejeitado) — sem o secret, é pulado; cobertura é enforçada no gate, não no Codecov.
- **react-doctor**: score depende de telemetria remota → exige `--offline` para ser determinístico.
- **Telemetria de runtime** (`ci-runtime-telemetry.yml`): cron que falha se p95 regride >35% vs `v2/docs/analysis/ci-runtime-baseline.json`. Não bloqueia PR; re-baseline = promover o report fresco ao JSON.

## NÃO fazer

- Nunca `git push` direto na `main` (CP-07, enforce por hook) — sempre branch + PR.
- Nunca `systemctl restart docker` na VM01 (Kaspersky/KESL derruba o site) — usar `systemctl restart kesl`.
- Mudança em `docker-compose.prod.yml` **não** viaja pelo pipeline: exige update manual no Editor do Portainer **e** re-captura do `trust/compose.pinned.yml` na VM01 (o applier reenvia o pinado, e recusa se o vivo divergir).
- Nunca tratar merge na `main` como deploy, nem procurar um job `deploy` no `deploy.yaml` — ele não existe desde o #1516.

# CI Check Policy

Esta política define quais checks de CI bloqueiam merge em `main` e quais são apenas informativos.

## Convenção de nomes

- `"[required] ..."`: check bloqueante de merge.
- `"[info] ..."`: check informativo, não bloqueia merge.
- `"[ops] ..."`: rotina operacional (manual/schedule), fora do gate de PR.

## Checks bloqueantes (gate de PR)

Inventário dos jobs nomeados `[required]` em `.github/workflows/` — estes devem ficar
obrigatórios no ruleset `Protect main`:

| Check | Workflow |
|---|---|
| `[required] backend impact` | `ci.yaml` |
| `[required] lint` | `ci.yaml` |
| `[required] backend rbac-lint` | `ci.yaml` |
| `[required] backend tests (runner)` | `ci.yaml` |
| `[required] backend typecheck (pyright)` | `ci.yaml` |
| `[required] docker parity (backend)` | `ci.yaml` |
| `[required] tests` | `ci.yaml` (agregador dos gates de backend) |
| `[required] react doctor quality gate` | `frontend-ci.yml` |
| `[required] build/lint do frontend` | `frontend-ci.yml` |
| `[required] checklist tests (meta, a11y, security)` | `frontend-ci.yml` |
| `[required] dependency review` | `dependency-review-scorecard.yml` |
| `[required] architecture dependency guardrails` | `architecture-guardrails.yml` |
| `[required] Python Dependencies` | `security-scan.yml` |
| `[required] Frontend Dependencies` | `security-scan.yml` |
| `[required] Container Scan` | `security-scan.yml` |
| `[required] Secret Detection` | `security-scan.yml` |
| `[required] docs quality (links + frontmatter)` | `docs-quality.yml` |
| `[required] staging gate evidence` | `staging-gate-audit.yml` |
| `[required] rbac matrix doc drift` | `rbac-doc-drift.yml` — **ver exceção abaixo** |

> **A composição efetiva do ruleset é uma configuração do GitHub, não um arquivo do
> repositório.** Esta tabela é o inventário do que *deveria* estar lá; conferir com
> `gh api /repos/<owner>/<repo>/rulesets` antes de assumir que estão todos ligados.

> **Exceção conhecida — `[required] rbac matrix doc drift`.** O workflow usa `paths` no
> gatilho de `pull_request` (`rbac-doc-drift.yml:32-37`), o que viola a regra de
> governança abaixo. O próprio cabeçalho do arquivo registra que ele ainda **não** foi
> adicionado à branch protection. Ligá-lo no ruleset sem antes remover o `paths`
> travaria todo PR que não toque `matrix.py`/`rbac_authorization_matrix.md`
> (check eternamente "Expected"). Ou remove-se o `paths`, ou renomeia-se para `[info]`.

## Checks informativos

Estes checks não bloqueiam merge:

- `[info] backend tests core (runner)` (`ci.yaml`)
- `[info] backend tests dev_tools (runner)` (`ci.yaml`)
- `[info] backend migrate-integrity` (`ci.yaml`)
- `[info] e2e journeys` (`frontend-ci.yml`)
- `[info] lighthouse CI` (`frontend-ci.yml`)
- `[info] openssf scorecard` (`dependency-review-scorecard.yml`)
- `[info] backend xdist canary (w=...,dist=...)` (`backend-xdist-canary.yml`)
- `[info] agent-browser smoke` (`agent-browser-smoke.yml`)
- `[info] documentation build` (`docs.yml`)
- `[info] backend test` (`_backend-test.yml`, workflow reutilizável — o nome efetivo
  vem do job que o chama)

## Checks operacionais

Executados por `schedule` ou `workflow_dispatch`:

- `[ops] strict security headers (staging/prod)`
- `[ops] backend xdist canary summary`
- `[ops] slsa provenance + cosign`
- `[ops] promote (assina ponteiro)` (`promote.yml`, gated no Environment `production`)

## Trilha Canary Backend xdist

- Documento operacional: [CI Backend xdist Canary](ci-backend-xdist-canary.md)
- Backlog de estabilizacao: [CI Backend xdist Stabilization Backlog](ci-backend-xdist-stabilization-backlog.md)
- Finalidade: experimentação de paralelismo (`pytest-xdist`) sem alterar o gate obrigatório.
- Regra: findings recorrentes da trilha canary viram issues de estabilização antes de qualquer promoção para o caminho obrigatório.

## Regras de governança

- Todo novo check de PR deve ser classificado como `required` ou `info` no próprio nome.
- Só checks `required` entram no ruleset.
- Workflow que publica check `required` não deve usar `paths` no gatilho de `pull_request`.
- Checks `info` podem usar `continue-on-error`, com artifact/log para análise posterior.
- Não usar runners `self-hosted` nos gates de PR.
- Preferir `ubuntu-slim` para jobs leves (lint/quality gates sem Docker) com timeout <= 15 min.
- Manter `ubuntu-latest` para jobs com Docker, Playwright/Lighthouse, build pesado ou timeout > 15 min.

## Monitoramento de custo (GitHub Actions)

- Revisão operacional mensal via API de billing:
  - `gh api /repos/<owner>/<repo>/actions/billing/usage`
- Correlacionar custo com a telemetria de duração:
  - workflow `[monitoring] ci runtime baseline (median/p95)` em `.github/workflows/ci-runtime-telemetry.yml`.

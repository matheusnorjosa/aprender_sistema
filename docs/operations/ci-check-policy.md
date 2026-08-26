# CI Check Policy

Esta política define quais checks de CI bloqueiam merge em `main` e quais são apenas informativos.

## Convenção de nomes

- `"[required] ..."`: check bloqueante de merge.
- `"[info] ..."`: check informativo, não bloqueia merge.
- `"[ops] ..."`: rotina operacional (manual/schedule), fora do gate de PR.

## Checks bloqueantes (gate de PR)

Inventário dos jobs nomeados `[required]` em `.github/workflows/`. O nome `[required]`
sozinho **não** diz como o check bloqueia o merge — há três mecanismos (coluna
**Enforcement**):

- **ruleset (direto)** — listado nos `required_status_checks` do ruleset `Protect main`.
  Só vale para checks **sempre-reportantes** (sem `if:`/`paths` que os pulem), senão o
  merge fica *pending* eterno.
- **via agregador `[required] tests`** — jobs **condicionais** de backend (rodam só com
  `backend_changed`; ficam `skipped` fora disso). NÃO entram direto no ruleset (o `skipped`
  travaria PR sem impacto backend); são enforçados pelo `needs` + assert do agregador, que
  **sempre reporta** (`if: always()`).
- **path-filtered — exceção** — jobs com `paths:` no gatilho de `pull_request` não reportam
  em PR fora dos paths → não entram no ruleset sem antes remover o `paths` (ver exceções abaixo).

| Check | Workflow | Enforcement |
|---|---|---|
| `[required] tests` | `ci.yaml` (agregador dos gates de backend) | ruleset (direto) |
| `[required] lint` | `ci.yaml` | ruleset (direto) |
| `[required] backend rbac-lint` | `ci.yaml` | ruleset (direto) |
| `[required] backend impact` | `ci.yaml` | via agregador `[required] tests` |
| `[required] backend tests (runner)` | `ci.yaml` | via agregador `[required] tests` |
| `[required] backend typecheck (pyright)` | `ci.yaml` | via agregador `[required] tests` |
| `[required] docker parity (backend)` | `ci.yaml` | via agregador `[required] tests` |
| `[required] backend migrate-integrity` | `ci.yaml` | via agregador `[required] tests` |
| `[required] build/lint do frontend` | `frontend-ci.yml` | ruleset (direto) |
| `[required] react doctor quality gate` | `frontend-ci.yml` | ruleset (direto) |
| `[required] checklist tests (meta, a11y, security)` | `frontend-ci.yml` | ruleset (direto) |
| `[required] dependency review` | `dependency-review-scorecard.yml` | ruleset (direto) |
| `[required] Python Dependencies` | `security-scan.yml` | ruleset (direto) |
| `[required] Frontend Dependencies` | `security-scan.yml` | ruleset (direto) |
| `[required] Container Scan` | `security-scan.yml` | ruleset (direto) |
| `[required] Secret Detection` | `security-scan.yml` | ruleset (direto) |
| `[required] docs quality (links + frontmatter)` | `docs-quality.yml` | ruleset (direto) |
| `[required] staging gate evidence` | `staging-gate-audit.yml` | ruleset (direto) |
| `[required] architecture dependency guardrails` | `architecture-guardrails.yml` | path-filtered — exceção (não no ruleset) |
| `[required] rbac matrix doc drift` | `rbac-doc-drift.yml` | path-filtered — exceção (não no ruleset) |

Os 13 marcados **ruleset (direto)** compõem exatamente os `required_status_checks` de
`Protect main` (verificado 2026-08-26).

> **A composição efetiva do ruleset é uma configuração do GitHub, não um arquivo do
> repositório.** A coluna **Enforcement** é o inventário do que *deveria* valer; conferir com
> `gh api /repos/<owner>/<repo>/rulesets` antes de assumir que os 13 diretos continuam ligados.

> **Exceções conhecidas (path-filtered) — `[required] architecture dependency guardrails` e
> `[required] rbac matrix doc drift`.** Ambos usam `paths` no gatilho de `pull_request`
> (`architecture-guardrails.yml`; `rbac-doc-drift.yml:32-37`), então **não reportam** em PR
> fora dos paths e **não estão no ruleset**. Ligá-los sem antes remover o `paths` travaria
> todo PR que não toque esses paths (check eternamente *pending*/"Expected"). Para promovê-los
> ao gate: remover o `paths` do `pull_request` (como `frontend-ci.yml` fez) ou renomeá-los
> para `[info]`.

## Checks informativos

Estes checks não bloqueiam merge:

- `[info] backend tests core (runner)` (`ci.yaml`)
- `[info] backend tests dev_tools (runner)` (`ci.yaml`)
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
- Só checks `required` **sempre-reportantes** entram direto no ruleset. Condicionais de
  backend (rodam com `backend_changed`) são enforçados pelo agregador `[required] tests`
  (`needs` + assert); nunca vão direto ao ruleset (o `skipped` travaria PR sem impacto backend).
- Workflow que publica check `required` não deve usar `paths` no gatilho de `pull_request`
  (senão o check não reporta em PR fora dos paths e o ruleset fica *pending* eterno).
- Checks `info` podem usar `continue-on-error`, com artifact/log para análise posterior.
- Não usar runners `self-hosted` nos gates de PR.
- Preferir `ubuntu-slim` para jobs leves (lint/quality gates sem Docker) com timeout <= 15 min.
- Manter `ubuntu-latest` para jobs com Docker, Playwright/Lighthouse, build pesado ou timeout > 15 min.

## Monitoramento de custo (GitHub Actions)

- Revisão operacional mensal via API de billing:
  - `gh api /repos/<owner>/<repo>/actions/billing/usage`
- Correlacionar custo com a telemetria de duração:
  - workflow `[monitoring] ci runtime baseline (median/p95)` em `.github/workflows/ci-runtime-telemetry.yml`.

---
title: Índice SDD (Spec-Driven Development)
status: active
last_verified: 2026-06-19
owner: docs
related:
  - ../plans/PLAN_sdd_migration_2026-06-19.md
  - ../reports/AUDITORIA_DOCUMENTAL_2026-06-19.md
---

# Índice SDD — Specs vivas do AS v2

Esta pasta (`v2/docs/specs/`) é a camada de **specs vivas** do modelo Spec-Driven Development: cada módulo ou
contrato em produção tem (ou terá) uma spec versionada, datada e rastreável ao código. O racional, a estrutura-alvo
e as fases estão no [plano SDD](../plans/PLAN_sdd_migration_2026-06-19.md), apoiado na
[auditoria documental 2026-06-19](../reports/AUDITORIA_DOCUMENTAL_2026-06-19.md).

> Estado: **specs escritas (Fases 3-4, 2026-06-19)**. Cada spec abaixo foi autorada e verificada contra o
> código (`sources_of_truth` confirmados). O modelo SDD está formalizado na
> [ADR-017](../../../docs/architecture/project-decisions/ADR-017-spec-driven-documentation.md).

## Convenção de frontmatter (obrigatória em todo doc vivo)

Todo arquivo em `specs/`, `runbooks/`, `reference/` e `decisions/` começa com:

```yaml
---
title: <nome legível>
status: canonical | active | draft | stale | historical
last_verified: YYYY-MM-DD     # data da última checagem contra o código
sources_of_truth:             # arquivos de código que esta spec descreve
  - v2/backend/apps/core/...
owner: backend | frontend | infra | docs | domain
supersedes: []                # docs que esta spec substitui (a arquivar)
related: []                   # links a specs/ADRs relacionados
---
```

## Legenda de `status`

| status | significado |
|---|---|
| `canonical` | fonte única de verdade, autoritativa hoje, casa com o código |
| `active` | útil/atual e mantido, mas não é o SSOT |
| `draft` | em construção, ainda não confiável |
| `stale` | desatualizado/contradiz o código (a reconciliar) |
| `historical` | registro datado/arquivado (não se "corrige") |

## Specs por área

### `domain/` — regras de negócio (contratos imutáveis)

| Spec | Cobre | Status |
|---|---|---|
| [clausulas-petreas.spec.md](./domain/clausulas-petreas.spec.md) | CP-01..CP-08 (enforcement real) | canonical |
| [regras-disponibilidade.spec.md](./domain/regras-disponibilidade.spec.md) | RD-01..RD-08 | canonical |
| [politica-aprovacao.spec.md](./domain/politica-aprovacao.spec.md) | PA-01..PA-07 | canonical |
| [requisitos-funcionais.spec.md](./domain/requisitos-funcionais.spec.md) | RF01..RF08 (índice) | canonical |

### `backend/` — subsistemas de `apps/core` + `apps/dev_tools`

| Spec | Cobre | Status |
|---|---|---|
| [rbac.spec.md](./backend/rbac.spec.md) | HasPerm, policies, matriz, lint | canonical |
| [availability.spec.md](./backend/availability.spec.md) | serviço de disponibilidade (RD) | canonical |
| [solicitacao-approval.spec.md](./backend/solicitacao-approval.spec.md) | fluxo de aprovação (PA/RF04) | canonical |
| [gcal.spec.md](./backend/gcal.spec.md) | Google Calendar + Meet (RF05/06) | canonical |
| [imports.spec.md](./backend/imports.spec.md) | pipeline export-contract | canonical |
| [backup-dr.spec.md](./backend/backup-dr.spec.md) | backup & disaster recovery (dívida #1455) | active |
| [dat.spec.md](./backend/dat.spec.md) | módulo DAT (ações/cadastros/registros) | canonical |
| [notificacoes.spec.md](./backend/notificacoes.spec.md) | sistema 32 Passos | canonical |
| [deslocamento.spec.md](./backend/deslocamento.spec.md) | deslocamento (GAP preenchido) | active |
| [dev-tools.spec.md](./backend/dev-tools.spec.md) | catálogo de seeds (CP-08) | canonical |

### `frontend/` — pages, hooks, api clients

| Spec | Cobre | Status |
|---|---|---|
| [pages.spec.md](./frontend/pages.spec.md) | páginas React (rotas + guards) | canonical |
| [hooks-rbac.spec.md](./frontend/hooks-rbac.spec.md) | hooks de RBAC/guards (GAP preenchido) | canonical |
| [api-clients.spec.md](./frontend/api-clients.spec.md) | clientes axios/fetch | canonical |

### `infra/` — deploy, ambientes, CI

| Spec | Cobre | Status |
|---|---|---|
| [deploy.spec.md](./infra/deploy.spec.md) | deploy → Portainer (prod verificado) | canonical |
| [environments.spec.md](./infra/environments.spec.md) | dev / staging / prod-like | canonical |
| [ci.spec.md](./infra/ci.spec.md) | GitHub Actions, gates, deploy | canonical |

> READMEs de área: [`domain/`](./domain/README.md) · [`backend/`](./backend/README.md) ·
> [`frontend/`](./frontend/README.md) · [`infra/`](./infra/README.md).

## Template de spec por módulo

O template canônico de `*.spec.md` está na seção 5 do
[plano SDD](../plans/PLAN_sdd_migration_2026-06-19.md).

---
title: Índice SDD (Spec-Driven Development)
status: active
last_verified: 2026-07-24
owner: docs
related:
  - ../plans/PLAN_sdd_migration_2026-06-19.md
  - ../reports/AUDITORIA_DOCUMENTAL_2026-06-19.md
  - ../audits/ACHADOS_REAIS.md
  - ../audits/VARREDURA_DOCS_2026-07-24.md
---

# Índice SDD — Specs vivas do AS v2

Esta pasta (`v2/docs/specs/`) é a camada de **specs vivas** do modelo Spec-Driven Development: cada módulo ou
contrato em produção tem (ou terá) uma spec versionada, datada e rastreável ao código. O racional, a estrutura-alvo
e as fases estão no [plano SDD](../plans/PLAN_sdd_migration_2026-06-19.md), apoiado na
[auditoria documental 2026-06-19](../reports/AUDITORIA_DOCUMENTAL_2026-06-19.md).

> Estado: **as 21 specs foram reverificadas contra o código** (varredura documental
> pós-auditoria M00–M28); **20 `canonical` + 1 `draft`** (`at-rest-encryption`, pendente de verificação
> de infra). O modelo SDD está formalizado na
> [ADR-017](../../../docs/architecture/project-decisions/ADR-017-spec-driven-documentation.md).
>
> **Leia junto:** [`ACHADOS_REAIS.md`](../audits/ACHADOS_REAIS.md) é a fila viva de defeitos (57
> achados: 2 P0, 36 P1, 19 P2). Várias specs abaixo têm uma seção **Divergências**, que registra
> onde o código **não** cumpre a regra descrita — com link para o achado. Uma spec descrever o
> comportamento real, inclusive quando ele é o errado, é intencional: o comportamento pretendido
> só entra como "pretendido", nunca como se já existisse.
>
> O que foi corrigido, o que ficou pendente de decisão humana e o que já estava certo está em
> [`VARREDURA_DOCS_2026-07-24.md`](../audits/VARREDURA_DOCS_2026-07-24.md).

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
| [backup-dr.spec.md](./backend/backup-dr.spec.md) | backup & disaster recovery (#1455 fechado; **restore quebrado, #1611 P0**) | canonical |
| [dat.spec.md](./backend/dat.spec.md) | módulo DAT (ações/cadastros/registros) | canonical |
| [notificacoes.spec.md](./backend/notificacoes.spec.md) | sistema 32 Passos | canonical |
| [deslocamento.spec.md](./backend/deslocamento.spec.md) | deslocamento (gate owner-or-delegate, #1454) | canonical |
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
| [deploy.spec.md](./infra/deploy.spec.md) | deploy pull-based (ADR-018): promote → ponteiro assinado → agente na VM01 | canonical |
| [environments.spec.md](./infra/environments.spec.md) | dev / staging / prod-like | canonical |
| [ci.spec.md](./infra/ci.spec.md) | GitHub Actions, gates, deploy | canonical |
| [at-rest-encryption.spec.md](./infra/at-rest-encryption.spec.md) | cifra de dados em repouso (CPF/PII): decisão = cifra de disco VM02 | draft |

> READMEs de área: [`domain/`](./domain/README.md) · [`backend/`](./backend/README.md) ·
> [`frontend/`](./frontend/README.md) · [`infra/`](./infra/README.md).

## Template de spec por módulo

O template canônico de `*.spec.md` está na seção 5 do
[plano SDD](../plans/PLAN_sdd_migration_2026-06-19.md).

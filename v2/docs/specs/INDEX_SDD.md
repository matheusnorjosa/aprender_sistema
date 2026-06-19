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

> Estado: **esqueleto (Fase 0)**. As specs por módulo ainda não foram escritas — esta estrutura existe para
> receber a migração das Fases 3-4. Os ponteiros abaixo marcam o que está planejado.

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

## Áreas

- [`domain/`](./domain/README.md) — regras de negócio (CP, RD, PA, RF)
- [`backend/`](./backend/README.md) — subsistemas de `apps/core` + `apps/dev_tools`
- [`frontend/`](./frontend/README.md) — pages, hooks, api clients
- [`infra/`](./infra/README.md) — deploy, ambientes, CI

## Template de spec por módulo

O template canônico de `*.spec.md` está na seção 5 do
[plano SDD](../plans/PLAN_sdd_migration_2026-06-19.md).

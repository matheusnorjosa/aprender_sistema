---
title: Specs de Backend
status: active
last_verified: 2026-06-19
owner: backend
related:
  - ../INDEX_SDD.md
---

# Specs de Backend (`apps/core` + `apps/dev_tools`)

Backend real = **apenas** `apps/core` (28 models) + `apps/dev_tools`. Voltar ao [índice SDD](../INDEX_SDD.md).

## Specs planejadas (Fase 3-4)

| Spec | Estado da doc hoje | Fonte canônica / código |
|---|---|---|
| `deslocamento.spec.md` | **GAP — sem doc** | `apps/core/views_deslocamento.py`, `services/deslocamentos_import.py` |
| `rbac.spec.md` | reescrever (`docs/guides/rbac.md` é stale) | `apps/core/rbac/`, `RBAC_NAMING.md` |
| `imports.spec.md` | reescrever (`docs/guides/etl.md` é stale) | `apps/core/imports/`, `v2/docs/imports/` |
| `availability.spec.md` | migrar | `services/availability_service.py`, `GUIDE_AVAILABILITY.md` |
| `solicitacao-approval.spec.md` | migrar | `services/solicitacao_approval.py`, `IMPLEMENTACAO_PA.md` |
| `gcal.spec.md` | migrar | `services/gcal/`, `GUIDE_GCAL.md` |
| `backup-dr.spec.md` | migrar | `tasks_backup.py`, `BACKUP_OPERATIONS.md` |
| `dat.spec.md` | migrar | `views/dat_module.py`, `SPEC_DAT_REGISTROS.md` |
| `notificacoes.spec.md` | consolidar | `services/notificacoes_acoes_service.py`, `PLANO_NOTIFICACOES_TIMING.md` |

> Status: esqueleto. Nenhuma spec escrita ainda (Fase 0).

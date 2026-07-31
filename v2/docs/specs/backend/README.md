---
title: Specs de Backend
status: active
last_verified: 2026-07-24
owner: backend
related:
  - ../INDEX_SDD.md
  - ../../audits/ACHADOS_REAIS.md
---

# Specs de Backend (`apps/core` + `apps/dev_tools`)

Backend real = **apenas** `apps/core` (42 models concretos em `apps/core/models/`) + `apps/dev_tools`.
Voltar ao [índice SDD](../INDEX_SDD.md).

## As 10 specs e o código que cada uma descreve

| Spec | Cobre | Fonte canônica no código |
|---|---|---|
| [`rbac.spec.md`](./rbac.spec.md) | `HasPerm`, policies, matriz viva, lint | `apps/core/rbac/`, `scripts/rbac_lint.py` |
| [`availability.spec.md`](./availability.spec.md) | RD-01..RD-08 + guard de enforcement | `services/availability_service.py`, `services/solicitacao_availability.py` |
| [`solicitacao-approval.spec.md`](./solicitacao-approval.spec.md) | PA-01..PA-07 / RF04 | `services/solicitacao_approval.py`, `views_solicitacao.py` |
| [`gcal.spec.md`](./gcal.spec.md) | Google Calendar + Meet (RF05/RF06), OAuth | `services/gcal/`, `services/oauth/` |
| [`imports.spec.md`](./imports.spec.md) | export-contract + endpoints de import | `apps/core/imports/`, `services/*_import.py` |
| [`backup-dr.spec.md`](./backup-dr.spec.md) | backup & disaster recovery | `tasks_backup.py`, `v2/infra/scripts/` |
| [`dat.spec.md`](./dat.spec.md) | módulo DAT (ações/cadastros/registros/compras) | `views/dat_module.py`, `views/dat.py`, `models/dat_*.py` |
| [`notificacoes.spec.md`](./notificacoes.spec.md) | 32 Passos (ações internas) | `services/notificacoes_acoes_service.py`, `models/acoes_notificacao.py` |
| [`deslocamento.spec.md`](./deslocamento.spec.md) | cadastro de deslocamentos + grade | `views_deslocamento.py`, `services/deslocamentos_import.py` |
| [`dev-tools.spec.md`](./dev-tools.spec.md) | catálogo de seeds (CP-08) | `apps/dev_tools/`, `config/settings.py` |

## Histórico

Escritas em 2026-06-19 (Fases 3-4 do plano SDD, ADR-017). Os guias legados que motivaram
cada spec — `docs/guides/rbac.md` e `docs/guides/etl.md` — **já foram reconciliados** na mesma
onda e hoje são apenas ponteiros para a documentação canônica; não são mais stale.

Revarredura em **2026-07-24**: as 10 specs foram reconferidas contra o código após a auditoria
modular M00-M28. Onde a spec descrevia o comportamento pretendido como se fosse o real, o texto
passou a descrever o código atual e a apontar o achado correspondente em
[`ACHADOS_REAIS.md`](../../audits/ACHADOS_REAIS.md) — que é o documento vivo e a **única** fonte
de severidade válida (o relatório longo `2026-07-17-system-module-audit.md` acerta os mecanismos
e erra as consequências).

---
description: DEPRECADO — ETL legado removido. Import atual = import_export_contract (dry-run por padrão) + endpoints DRF.
argument-hint: [deprecated]
---

> **⚠️ DEPRECADO (2026-06).** O ETL legado (`apps.dat_ingest`, comandos `etl_upsert_*`/`etl_import_*`) foi **REMOVIDO** (#967/#971). Este command **não executa nada útil** — não rode os comandos antigos, eles não existem.

# ETL Dry-Run — DEPRECADO

Fluxo de import atual (preview/dry-run):

- **Command**: `import_export_contract` — **dry-run por padrão** (sem `--apply` = nada escrito).
- **API**: endpoints DRF `POST /api/<recurso>/import/` (pipeline async `ImportJob`).
- **Spec viva**: `v2/docs/specs/backend/imports.spec.md`.

Não codar contra `apps.dat_ingest` — o módulo não existe mais.

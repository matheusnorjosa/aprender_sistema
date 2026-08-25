---
description: DEPRECADO — ETL legado removido. Import atual = import_export_contract --apply (allowlist) + endpoints DRF.
argument-hint: [deprecated]
---

> **⚠️ DEPRECADO (2026-06).** O ETL legado (`apps.dat_ingest`, comandos `etl_upsert_*`/`etl_import_*`) foi **REMOVIDO** (#967/#971). Este command **não executa nada útil** — não rode os comandos antigos, eles não existem.

# ETL Apply — DEPRECADO

Fluxo de import atual (commit/apply):

- **Command**: `import_export_contract` — `--apply` exige allowlist (bloqueado por padrão; nenhum import real até dry-run verde + autorização).
- **API**: endpoints DRF `POST /api/<recurso>/import/` (pipeline async `ImportJob`).
- **Spec viva**: `v2/docs/specs/backend/imports.spec.md`.

Não codar contra `apps.dat_ingest` — o módulo não existe mais.

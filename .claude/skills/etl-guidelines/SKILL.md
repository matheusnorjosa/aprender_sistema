---
name: etl-guidelines
description: DEPRECADA — ETL legado (apps.dat_ingest) REMOVIDO. Import atual = import_export_contract + endpoints DRF. Não codar contra apps.dat_ingest.
disable-model-invocation: true
---

# ETL Guidelines — DEPRECADA (2026-06)

> ⚠️ O ETL legado (`apps.dat_ingest`, comandos `etl_upsert_*` / `etl_import_*`) foi **REMOVIDO** (#967/#971).
> **Não escreva código contra `apps.dat_ingest`** — o módulo não existe mais. Esta skill é só um redirect.

**Import atual (SSOT):**

- **Command**: `import_export_contract` — dry-run por padrão; `--apply` exige allowlist (bloqueado).
- **API**: endpoints DRF `POST /api/<recurso>/import/` — pipeline async `ImportJob`.
- **Padrões de import**: `apps/core/imports/` (hashing / normalization).
- **Spec viva**: `v2/docs/specs/backend/imports.spec.md`.

Conteúdo histórico do ETL legado não é mantido aqui (ver git history se necessário).

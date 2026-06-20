# Importação de Dados

> **Atualizado (SDD 2026-06).** O antigo pipeline ETL (`apps.dat_ingest`, ~21 comandos `import_usuarios`/`import_formadores`/`import_projetos`/`import_solicitacoes`/…) foi **removido** (#967/#971). Aquele guia não reflete mais o sistema — o único management command de import real hoje é `import_export_contract`.

A importação de dados agora usa o **pipeline export-contract** (`apps/core/imports/`), com idempotência por `external_hash` SHA1 (ADR-012) e os contratos documentados no SSOT:

> **[v2/docs/imports/README.md](https://github.com/matheusnorjosa/aprender_sistema/blob/main/v2/docs/imports/README.md)** — contratos por entidade (usuários, disponibilidade, agenda/solicitações, produtos/controle), ordem de importação e contrato de resposta de dry-run.

Mecanismos:

- **Endpoints DRF**: `POST /api/<recurso>/import/` (síncrono) ou `POST /api/imports/<tipo>/` (assíncrono, ASQ-005).
- **Management command**: `python manage.py import_export_contract` (dry-run por padrão; `--apply` exige allowlist e nunca sobrescreve campos protegidos).

Regra de ouro: todo import roda **dry-run por padrão**; só aplica com autorização explícita.

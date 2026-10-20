# Importação de Dados

> **Atualizado (SDD 2026-06).** O antigo pipeline ETL (`apps.dat_ingest`, ~21 comandos `import_usuarios`/`import_formadores`/`import_projetos`/`import_solicitacoes`/…) foi **removido** (#967/#971). Aquele guia não reflete mais o sistema — o único management command de import real hoje é `import_export_contract`.

A importação de dados agora usa o **pipeline export-contract** (`apps/core/imports/`), com idempotência por `external_hash` SHA1 (ADR-012) e os contratos documentados no SSOT:

> - **[specs/backend/imports.spec.md](https://github.com/matheusnorjosa/aprender_sistema/blob/main/v2/docs/specs/backend/imports.spec.md)** — spec canônica: contrato, invariantes e campos protegidos.
> - **[v2/docs/imports/README.md](https://github.com/matheusnorjosa/aprender_sistema/blob/main/v2/docs/imports/README.md)** — contratos por entidade (usuários, disponibilidade, agenda/solicitações, produtos/controle), ordem de importação e contrato de resposta de dry-run.

Mecanismos:

- **Endpoints DRF**: `POST /api/<recurso>/import/` (síncrono) ou `POST /api/imports/<tipo>/` (assíncrono, ASQ-005).
- **Management command**: `python manage.py import_export_contract` (dry-run por padrão; `--apply` exige allowlist). No modo padrão, `--mode create-only`, o apply só insere e nunca sobrescreve campos protegidos.
  - **Exceção: `--mode virada`** (#2116, carga única da virada). Com `--apply` e allowlist, o evento existente que ninguém mexeu pela tela é **atualizado** pela planilha (projeto, data e hora, formadores) e o status pode mudar: cancelado → reprovado, e SUPER aprovado com mudança material → pendente. Essa é a única exceção aos campos protegidos; o modo nunca aprova e nunca chama o Google. A adoção do Event ID do Google (entidade `gcal_adocao`) roda à parte. SSOT: `export_contract_importer.py` e a imports.spec.md.

Regra de ouro: todo import roda **dry-run por padrão**; só aplica com autorização explícita.

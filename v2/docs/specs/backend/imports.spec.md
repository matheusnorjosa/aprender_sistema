---
title: Importação de Dados (export-contract)
status: canonical
last_verified: 2026-06-19
sources_of_truth:
  - v2/backend/apps/core/imports/__init__.py
  - v2/backend/apps/core/imports/hashing.py
  - v2/backend/apps/core/imports/normalization.py
  - v2/backend/apps/core/services/usuarios_import.py
  - v2/backend/apps/core/services/municipios_import.py
  - v2/backend/apps/core/services/controle_imports.py
  - v2/backend/apps/core/services/export_contract_importer.py
  - v2/backend/apps/core/services/export_contract_projeto_resolver.py
  - v2/backend/apps/core/management/commands/import_export_contract.py
  - v2/backend/apps/core/views_import_usuarios.py
  - v2/backend/apps/core/views_controle_imports.py
  - v2/backend/apps/core/views/imports.py
  - v2/backend/apps/core/models/import_job.py
  - v2/backend/apps/core/rbac/policies.py
  - v2/backend/apps/core/urls.py
owner: backend
supersedes:
  - v2/docs/imports/README.md
  - v2/docs/imports/usuarios.md
  - v2/docs/imports/disponibilidade.md
  - v2/docs/imports/produtos_controle.md
  - v2/docs/imports/agenda_solicitacoes.md
  - v2/docs/imports/ordem_de_importacao.md
  - v2/docs/imports/dry_run_response_contract.md
related:
  - v2/docs/adr/ADR-012-sha1-idempotency-hashes.md
  - v2/docs/specs/backend/rbac.spec.md
  - v2/docs/API_REFERENCE.md
---

# Importação de Dados (export-contract)

## Propósito

Este módulo importa dados da planilha consolidada externa (`sheets.banco`, materializada como `export-contract`) para o PostgreSQL de `apps.core`, substituindo a digitação manual e as fórmulas Excel pela origem operacional do sistema. Cobre dois caminhos complementares: (1) os **services de import por entidade** (`*_import.py`) expostos como endpoints DRF síncronos e — para `bloqueios` — assíncronos via `ImportJob`/Celery; e (2) o **importer dedicado do export-contract** (`import_export_contract`), um pipeline dry-run-first que classifica linhas de um diretório de export contra o estado atual do banco.

A regra de ouro é a segurança contra reimportação cega: todo import valida em **dry-run** antes de qualquer escrita, é **idempotente** por `external_hash`, e **nunca** sobrescreve campos protegidos ou dispara efeitos colaterais perigosos (GCal, aprovação, atribuição de grupos privilegiados). O ETL legado `apps.dat_ingest` foi **removido**; não existem mais management commands `etl_*.py`/`import_*.py` históricos — o import real é `import_export_contract` + os endpoints DRF.

## Fonte de verdade no código

- Pacote canônico de helpers puros: [`apps/core/imports/`](../../../backend/apps/core/imports/) — [`hashing.py`](../../../backend/apps/core/imports/hashing.py) (`stable_import_hash`, `hash_event_v2`) e [`normalization.py`](../../../backend/apps/core/imports/normalization.py) (SSOT de normalização: `normalize_blank`, `normalize_cpf_digits`, `normalize_active_flag`, datas/horas/email/setor). Sem I/O, sem ORM.
- Services por entidade em `apps/core/services/*_import.py`: [`usuarios_import.py`](../../../backend/apps/core/services/usuarios_import.py), [`municipios_import.py`](../../../backend/apps/core/services/municipios_import.py), [`produtos_import.py`](../../../backend/apps/core/services/produtos_import.py), [`colecoes_import.py`](../../../backend/apps/core/services/colecoes_import.py), [`equipe_gerencia_import.py`](../../../backend/apps/core/services/equipe_gerencia_import.py), [`eventos_import.py`](../../../backend/apps/core/services/eventos_import.py), [`bloqueios_import.py`](../../../backend/apps/core/services/bloqueios_import.py), [`controle_imports.py`](../../../backend/apps/core/services/controle_imports.py) (alimenta `Compra`), [`controle_acoes_import.py`](../../../backend/apps/core/services/controle_acoes_import.py), [`dat_cadastros_import.py`](../../../backend/apps/core/services/dat_cadastros_import.py), [`deslocamentos_import.py`](../../../backend/apps/core/services/deslocamentos_import.py).
- Importer do export-contract: [`apps/core/services/export_contract_importer.py`](../../../backend/apps/core/services/export_contract_importer.py) (`ExportContractImporter`, `diff_and_classify`, `PROTECTED_FIELDS`, `IMPLEMENTED`) + resolver [`export_contract_projeto_resolver.py`](../../../backend/apps/core/services/export_contract_projeto_resolver.py) + command [`management/commands/import_export_contract.py`](../../../backend/apps/core/management/commands/import_export_contract.py).
- Views DRF síncronas: [`views_import_usuarios.py`](../../../backend/apps/core/views_import_usuarios.py), [`views_controle_imports.py`](../../../backend/apps/core/views_controle_imports.py), [`views_import_municipios.py`](../../../backend/apps/core/views_import_municipios.py), [`views_import_produtos.py`](../../../backend/apps/core/views_import_produtos.py), [`views_import_colecoes.py`](../../../backend/apps/core/views_import_colecoes.py), [`views_import_equipe_gerencia.py`](../../../backend/apps/core/views_import_equipe_gerencia.py), [`views_import_eventos.py`](../../../backend/apps/core/views_import_eventos.py), [`views_import_bloqueios.py`](../../../backend/apps/core/views_import_bloqueios.py), [`views_import_deslocamentos.py`](../../../backend/apps/core/views_import_deslocamentos.py).
- Caminho assíncrono (ASQ-005): [`views/imports.py`](../../../backend/apps/core/views/imports.py) + model [`models/import_job.py`](../../../backend/apps/core/models/import_job.py).
- Roteamento: [`apps/core/urls.py`](../../../backend/apps/core/urls.py).
- Detalhe de cada contrato de planilha (colunas, normalizações, gates): doc canônico [`v2/docs/imports/README.md`](../../imports/README.md) e arquivos por tipo (`usuarios.md`, `disponibilidade.md`, `produtos_controle.md`, `agenda_solicitacoes.md`).

## Contratos e invariantes

- **Dry-run obrigatório antes de apply**. Endpoints síncronos aceitam `?dry_run=true|false` (default `true`); o importer do export-contract é dry-run salvo `--apply`. Dry-run valida e retorna preview sem persistir (rollback via `transaction.atomic`).
- **Idempotência via `external_hash` (SHA1, ADR-012)**. `stable_import_hash(*parts)` = `hashlib.sha1("|".join(parts), usedforsecurity=False).hexdigest()`. O algoritmo, encoding (UTF-8) e delimitador (`|`) são **congelados** — alterá-los quebra os hashes históricos gravados em `Compra`, `Solicitacao`, `Deslocamento`, `AcaoControle`, `AcaoDAT`, `Acompanhamento`. `controle_imports.sha1_str` delega a `stable_import_hash`. Reimportar o mesmo arquivo não duplica linhas.
- **`--apply` sem allowlist é BLOQUEADO** no `import_export_contract`: sem `--allow-entity`, `report["apply_blocked"]` é verdadeiro e nada é escrito. Modo `create-only`: só insere `would_create`, nunca faz update.
- **Never-overwrite de campos protegidos** (`PROTECTED_FIELDS`): `Solicitacao.status`, `Formacao.data_formacao`, `Acompanhamento.{data_acompanhamento,realizado}`. Linha que diverge num campo protegido vira `protected_diff` e fica para decisão humana — jamais sobrescrita.
- **Nenhum efeito colateral perigoso** (CP-02/PA-01): import NUNCA publica no Google Calendar, NUNCA aprova solicitação SUPER, NUNCA atribui grupos `Gerente`/`Superintendência`, NUNCA cria `is_superuser=True`. RBAC é admin-driven (D17): import não roda `seed_rbac` nem concede capabilities.
- **RBAC por capability, não por grupo** (`scripts/rbac_lint.py` bane grupos diretos): gates via `permission_classes=[HasPerm("import_spreadsheet")]` ou `HasPerm("manage_admin_registries")`; o upload assíncrono usa a Policy `CanImportGenericSpreadsheet` (`import_spreadsheet` OU `run_daily_operations` — Controle/DAT).
- **Timezone** (RD-06): datas de calendário armazenadas em UTC, interpretadas como `America/Fortaleza`. Datas do CSV (`dd/mm/yyyy`) são local Fortaleza antes de virar UTC.
- **Sem PII no relatório** do export-contract: só counts e nomes de entidade.

## API / Interface

Endpoints síncronos (`{stats, pendencias, dry_run, file}`; todos com `?dry_run`, default `true`). Detalhes em [`API_REFERENCE.md`](../../API_REFERENCE.md):

| Endpoint | Gate |
|---|---|
| `POST /api/usuarios/import/` | `HasPerm("manage_admin_registries")` |
| `POST /api/municipios/import/` | `HasPerm("manage_admin_registries")` |
| `POST /api/colecoes/import/` | `HasPerm("manage_admin_registries")` |
| `POST /api/equipe-gerencia/import/` | `HasPerm("manage_admin_registries")` |
| `POST /api/dat/import-cadastros/` | `HasPerm("manage_admin_registries")` |
| `POST /api/produtos/import/` | `HasPerm("import_spreadsheet")` |
| `POST /api/solicitacoes/import/` | `HasPerm("import_spreadsheet")` (com PA-01) |
| `POST /api/disponibilidade/import-bloqueios/` | `HasPerm("import_spreadsheet")` |
| `POST /api/controle/import-compras/` | `HasPerm("import_spreadsheet")` |
| `POST /api/controle/import-acoes/` | `HasPerm("import_spreadsheet")` |

Endpoints assíncronos (ASQ-005 Fase 1 — só `bloqueios`):

- `POST /api/imports/bloqueios/` — cria `ImportJob` (status `QUEUED`) + despacha Celery `task_run_import_job`; retorna `202 Accepted` com o job serializado. Gate: `IsAuthenticated + CanImportGenericSpreadsheet`.
- `GET /api/imports/<id>/` — estado do job (owner ou superuser).
- `GET /api/imports/` — lista jobs do usuário (filtros `type=`, `status=`).

Management command:

```bash
# dry-run (default — só classifica, nada escrito):
python manage.py import_export_contract --path <dir-com-manifest.json>

# apply create-only de entidades explicitamente permitidas:
python manage.py import_export_contract --path <dir> --apply --allow-entity municipio
```

Entidades implementadas no importer (`IMPLEMENTED`): `municipio`, `projeto_geral`, `produto`, `usuario`, `gerencia`, `tipo_evento`, `dat_coordenador`, `dat_area`, `dat_acao`, `plano_formacao`. Demais (`solicitacao`, `formacao`, `acompanhamento`, ...) → `not_implemented` (só count reportado).

## Fluxos principais

**Import síncrono por endpoint (caminho feliz)**: cliente faz `POST .../import/?dry_run=true` (multipart `file`) → view valida upload (`validate_upload`, magic bytes) e grava temp seguro → service `import_<entidade>_from_file(path, dry_run=True)` normaliza linhas (helpers de `apps/core/imports/normalization.py`), reconcilia FKs e calcula `external_hash` → retorna `{stats, pendencias, dry_run, file}` sob `transaction.atomic` revertido. Operador revisa `pendencias`; sem erros bloqueantes, repete com `?dry_run=false` para persistir + grava `AuditLog`.

**Import assíncrono de bloqueios**: `POST /api/imports/bloqueios/` cria `ImportJob` (arquivo em `imports/%Y/%m/%d/`), retorna `202` imediato; Celery transiciona `QUEUED→RUNNING→SUCCESS|FAILED` (`mark_running/success/failed`), preenchendo `stats`/`pendencias`/`duration_ms`. Cliente faz polling em `GET /api/imports/<id>/`. `error_traceback` fica só em log, nunca na API.

**Importer do export-contract**: `ExportContractImporter.run()` lê `manifest.json` + CSVs do diretório, e por entidade chama `diff_and_classify(existing, export, protected)` → tally `{would_create, would_update, would_skip_same, protected_diff, would_reject}`. Sem `--apply` o relatório só classifica; com `--apply` + allowlist, escreve apenas `would_create` (create-only).

**Erros relevantes**: linha sem chave natural (ex.: `nome` vazio) → `would_reject` / `pendencias`; FK não resolvida (município/projeto) → pendência (resolver de Projeto canonicaliza & vs E, hífen, prefixo PROJETO, aliases); upload inválido (mime/magic) → `400`; `--apply` sem allowlist → bloqueado, nada escrito.

## Decisões relacionadas (ADRs)

- [ADR-012 — SHA1 idempotency hashes](../../adr/ADR-012-sha1-idempotency-hashes.md): `external_hash` é SHA1 congelado; migração para SHA256 é proibida.
- ASQ-005 (async `ImportJob` + Celery, Fase 1 `bloqueios`; #778/#1162) e ASQ-016 (savepoint-per-row) — referenciados no código dos services e do model.
- D17 (RBAC admin-driven): import não atribui capabilities — ver [`rbac.spec.md`](./rbac.spec.md).

## Testes que cobrem

- [`tests/test_imports_hashing.py`](../../../backend/apps/core/tests/test_imports_hashing.py) e [`tests/test_imports_normalization.py`](../../../backend/apps/core/tests/test_imports_normalization.py) — congelam `stable_import_hash`/normalizadores.
- [`tests/test_export_contract_importer.py`](../../../backend/apps/core/tests/test_export_contract_importer.py) e [`tests/test_export_contract_projeto_resolver.py`](../../../backend/apps/core/tests/test_export_contract_projeto_resolver.py) — classificação dry-run + apply-blocked + resolver de Projeto.
- [`tests/test_import_usuarios.py`](../../../backend/apps/core/tests/test_import_usuarios.py), [`tests/test_import_compras.py`](../../../backend/apps/core/tests/test_import_compras.py), [`tests/test_import_deslocamentos.py`](../../../backend/apps/core/tests/test_import_deslocamentos.py), [`tests/test_import_produtos.py`](../../../backend/apps/core/tests/test_import_produtos.py), [`tests/test_import_colecoes.py`](../../../backend/apps/core/tests/test_import_colecoes.py), [`tests/test_import_equipe_gerencia.py`](../../../backend/apps/core/tests/test_import_equipe_gerencia.py), [`tests/test_import_bloqueios.py`](../../../backend/apps/core/tests/test_import_bloqueios.py), [`tests/test_import_eventos.py`](../../../backend/apps/core/tests/test_import_eventos.py), [`tests/test_municipios_import_service.py`](../../../backend/apps/core/tests/test_municipios_import_service.py) — services por entidade (idempotência + dry-run).
- [`tests/test_import_endpoints.py`](../../../backend/apps/core/tests/test_import_endpoints.py) e [`tests/test_dat_imports_dat_only.py`](../../../backend/apps/core/tests/test_dat_imports_dat_only.py) — gates RBAC dos endpoints.
- [`tests/test_import_job_model.py`](../../../backend/apps/core/tests/test_import_job_model.py), [`tests/test_import_job_task.py`](../../../backend/apps/core/tests/test_import_job_task.py), [`tests/test_import_job_endpoints.py`](../../../backend/apps/core/tests/test_import_job_endpoints.py), [`tests/test_import_job_integration.py`](../../../backend/apps/core/tests/test_import_job_integration.py) — ciclo async.

## Pontos de atenção / dívidas conhecidas

- **ImportJob cobre só `bloqueios`** (Fase 1). Os outros 9 imports (usuários, compras, ações, deslocamentos, eventos, produtos, municípios, coleções, equipe_gerência) seguem síncronos; migração para async é Fase 2 (ASQ-005, ver `import_job.py`).
- **Importer do export-contract não importou dados reais**: `--apply` permanece bloqueado por allowlist. Regra operacional: NÃO importar de verdade até um dry-run real do `--apply` passar verde + autorização — reimport cego sobrescreveria data-fixes manuais (D2/C3-A/C4.4).
- **Reconciliação de `Usuario` por nome** em Agenda (Formador 1..5) é fuzzy (CPF não aparece na planilha de agenda) — risco de match errado; ver pendências em [`v2/docs/imports/README.md`](../../imports/README.md) §6.
- **Shape de retorno dos services não é 100% uniforme** historicamente — contrato-alvo em [`dry_run_response_contract.md`](../../imports/dry_run_response_contract.md).
- **Documentação histórica menciona `make etl-*` e management commands `etl_*.py`**: não existem mais (`apps.dat_ingest` removido). Os targets de Makefile que sobrevivem chamam os endpoints HTTP via `curl`.

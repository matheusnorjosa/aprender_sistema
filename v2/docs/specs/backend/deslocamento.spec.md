---
title: Deslocamento (GAP — criar)
status: active
last_verified: 2026-06-19
sources_of_truth:
  - v2/backend/apps/core/models/workflow.py
  - v2/backend/apps/core/migrations/0016_create_deslocamento.py
  - v2/backend/apps/core/views_deslocamento.py
  - v2/backend/apps/core/serializers/workflow.py
  - v2/backend/apps/core/views_import_deslocamentos.py
  - v2/backend/apps/core/services/deslocamentos_import.py
  - v2/backend/apps/core/services/monthly_grid_service.py
  - v2/backend/apps/core/services/availability_service.py
  - v2/backend/apps/core/urls.py
  - v2/backend/apps/core/admin.py
  - v2/backend/apps/core/models/auditoria.py
  - v2/backend/apps/core/rbac/matrix.py
  - v2/frontend/src/pages/Deslocamentos/DeslocamentosPage.tsx
owner: backend
supersedes: []
related:
  - v2/docs/specs/backend/availability.spec.md
  - v2/docs/specs/backend/rbac.spec.md
  - v2/docs/GUIDE_AVAILABILITY.md
  - v2/docs/rbac_authorization_matrix.md
---

# Deslocamento

## Proposito

O modulo de **Deslocamento** registra periodos em que um usuario (tipicamente formador/coordenador) esta em transito entre municipios — origem, destino e o intervalo de datas (`start_date`..`end_date`). Existe para tornar visivel, na **grade mensal de disponibilidade**, os dias em que a pessoa esta viajando: a grade emite o codigo `D` (deslocamento sem evento/bloqueio) ou `D1` (evento + deslocamento) para esses dias, evitando que o operador agende formacoes para alguem que ja esta em deslocamento.

E um cadastro operacional simples (CRUD + import em massa), sem fluxo de aprovacao. **Nota de escopo importante:** o modelo `Deslocamento` *informa* a grade mensal, mas **nao** alimenta o motor de conflitos da disponibilidade. A regra **RD-04** ("buffer de viagem entre municipios") e implementada separadamente em [`availability_service.py`](../../../backend/apps/core/services/availability_service.py) calculando o `TRAVEL_BUFFER_MINUTES` entre os municipios de *eventos* consecutivos — ela nao le registros de `Deslocamento`. Os dois compartilham o tema "viagem", mas sao mecanismos distintos.

## Fonte de verdade no codigo

- **Model**: [`apps/core/models/workflow.py`](../../../backend/apps/core/models/workflow.py) — classe `Deslocamento` (tabela `core_deslocamento`).
- **Migration de criacao**: [`apps/core/migrations/0016_create_deslocamento.py`](../../../backend/apps/core/migrations/0016_create_deslocamento.py).
- **ViewSet CRUD**: [`apps/core/views_deslocamento.py`](../../../backend/apps/core/views_deslocamento.py) — `DeslocamentoViewSet` (+ `DeslocamentoPagination`, `_get_client_ip`).
- **Serializer**: [`apps/core/serializers/workflow.py`](../../../backend/apps/core/serializers/workflow.py) — `DeslocamentoSerializer`.
- **Import (endpoint)**: [`apps/core/views_import_deslocamentos.py`](../../../backend/apps/core/views_import_deslocamentos.py) — `ImportDeslocamentosView`.
- **Import (service)**: [`apps/core/services/deslocamentos_import.py`](../../../backend/apps/core/services/deslocamentos_import.py) — `import_deslocamentos_from_file()`.
- **Consumo na grade mensal**: [`apps/core/services/monthly_grid_service.py`](../../../backend/apps/core/services/monthly_grid_service.py) — distribui deslocamentos por dia/pessoa e gera codigos `D`/`D1`.
- **Rotas**: [`apps/core/urls.py`](../../../backend/apps/core/urls.py) — router `deslocamentos` + rota `deslocamentos/import/`.
- **AuditLog actions**: [`apps/core/models/auditoria.py`](../../../backend/apps/core/models/auditoria.py) — `CREATE_DESLOCAMENTO`, `UPDATE_DESLOCAMENTO`, `DELETE_DESLOCAMENTO`.
- **Admin**: [`apps/core/admin.py`](../../../backend/apps/core/admin.py) — `DeslocamentoAdmin`.
- **RBAC (cobertura)**: [`apps/core/rbac/matrix.py`](../../../backend/apps/core/rbac/matrix.py) — resource `deslocamentos` mapeado para `_ALL_AUTH`.
- **Frontend**: [`v2/frontend/src/pages/Deslocamentos/DeslocamentosPage.tsx`](../../../frontend/src/pages/Deslocamentos/DeslocamentosPage.tsx).

### Campos do model

`usuario` (FK `Usuario`, `on_delete=PROTECT`, `related_name="deslocamentos"`), `origem` (CharField 200), `destino` (CharField 200), `start_date` (DateField), `end_date` (DateField), `observacao` (TextField, opcional), `external_hash` (CharField 64, `unique=True`, `db_index`, idempotencia de import), `created_at`, `updated_at`. Indices em `(usuario, start_date, end_date)` e `(external_hash)`.

> **Inexistente / nao usar:** nao ha management command de import (so o endpoint DRF). A funcao legada `etl_upsert_deslocamento` **nao existe** no codigo atual — o import passa exclusivamente por `import_deslocamentos_from_file` + `ImportDeslocamentosView`.

## Contratos e invariantes

- **Validacao de datas** (serializer): exige `end_date > start_date` (estrito; `end_date <= start_date` -> 400 em `end_date`). Suporta PATCH parcial (usa o valor da instancia para o campo ausente).
- **Origem != destino** (serializer): comparacao case-insensitive (`.strip().lower()`); igual -> 400 em `destino`.
- **Idempotencia de import**: `external_hash = SHA1(usuario_id|origem|destino|start_iso|end_iso)` via `stable_import_hash` (byte-equivalente ao formato historico). Re-import do mesmo registro nao duplica; so `observacao` e atualizada quando muda (never-overwrite dos demais campos). `unique=True` no `external_hash` e a barreira de banco.
- **Dry-run por padrao no import**: `dry_run=true` faz `transaction.set_rollback(True)`; nada e persistido. `dry_run=false` exige `HasPerm("import_spreadsheet")` (DAT ou superuser). Isolamento savepoint-por-linha (ASQ-016): uma linha ruim nao derruba o lote.
- **Scope RBAC (Onda 1 C2, 2026-04-27)** no `get_queryset`:
  - Superuser **ou** capability `view_all_availability` (Controle/Gerente via seed 0078) -> ve todos os deslocamentos.
  - Demais autenticados (Coord/Apoio/DAT) -> veem **apenas** deslocamentos de usuarios em gerencias vinculadas via `EquipeGerencia`. Sem vinculo -> **0 resultados** (fail-safe).
- **Auditoria obrigatoria**: todo CREATE/UPDATE/DELETE grava `AuditLog` com `usuario`, IP (X-Forwarded-For -> X-Real-IP -> REMOTE_ADDR), user-agent (truncado 200) e diff dos campos (no UPDATE). DELETE registra antes de deletar.
- **CP**: roda apenas em Docker (CP-01); idioma RBAC e `permission_classes=[HasPerm("...")]` (CP — grupos diretos banidos por `scripts/rbac_lint.py`).
- **Codigos de grade** (precedencia `X > D1 > 2 > E > T/P > D`): `D` = deslocamento sem evento/bloqueio; `D1` = evento + deslocamento sem bloqueio. Definidos em `monthly_grid_service.py`.

## API / Interface

CRUD (router DRF, basename `deslocamento`):

- `GET /api/deslocamentos/` — lista paginada (50/pagina, `page_size` ate 100), ordenada por `-start_date`.
- `GET /api/deslocamentos/{id}/`, `POST /api/deslocamentos/`, `PUT/PATCH /api/deslocamentos/{id}/`, `DELETE /api/deslocamentos/{id}/`.
- **Permissao do ViewSet**: `[IsAuthenticated]` + scope no queryset (nao `HasPerm` no nivel de classe; o controle e por *visibilidade* via `EquipeGerencia`).
- **Filtros** (query params, aplicados manualmente em `get_queryset`): `usuario_id` (exato), `data_inicio` (`start_date >=`), `data_fim` (`end_date <=`), `origem` (`icontains`), `destino` (`icontains`). **Nao ha `FilterSet`/`filterset_fields` declarado** — `DjangoFilterBackend` esta em `filter_backends` mas o filtro real e o codigo manual; `OrderingFilter` cobre `start_date|end_date|origem|destino`.

Import em massa:

- `POST /api/deslocamentos/import/` — `ImportDeslocamentosView`. Permissao `[IsAuthenticated, HasPerm("import_spreadsheet")]` (DAT ou superuser). Query `dry_run=true|false` (default `true`). Body multipart `file` (CSV/XLSX). Validacao de upload (tamanho/MIME/magic bytes) e temp-file sanitizado (path-injection mitigado). Retorna `{stats:{created,updated,unchanged,skipped}, pendencias:{usuarios,dates,outros}, dry_run, file}`. Colunas aceitas com headers flexiveis (`usuario|email|nome`, `origem`, `destino`, `data_inicio`, `data_fim`, `observacao`); datas parseadas em ISO, `dd/mm/yyyy` e serial Excel.

Schema detalhado/exemplos: ver `API_REFERENCE` quando disponivel.

## Fluxos principais

**Lancamento manual (UI dedicada)**: operador abre `DeslocamentosPage`, filtra por usuario/datas/origem/destino, cria/edita via modal -> `POST`/`PUT` -> serializer valida (datas, origem!=destino) -> `perform_create/update` grava registro + `AuditLog`. `external_hash` so e setado pelo import (CRUD manual deixa null).

**Import em massa (caminho feliz)**: DAT envia planilha -> `dry_run=true` retorna `stats`/`pendencias` para revisao -> apos validacao, `dry_run=false` persiste create-only (atualiza so `observacao`). Idempotente por `external_hash`.

**Erros relevantes do import**: usuario nao resolvido (email>nome) -> `skipped.usuario` + `pendencias.usuarios`; origem/destino ausentes -> `skipped.other`; data invalida ou `data_fim < data_inicio` -> `skipped.dates`; qualquer excecao de linha e isolada por savepoint e some em `pendencias.outros` (o lote continua).

**Reflexo na disponibilidade**: a grade mensal carrega os deslocamentos do mes, distribui por dia/pessoa e aplica precedencia, emitindo `D`/`D1`. Nao bloqueia agendamento por si so — e sinalizacao visual.

## Decisoes relacionadas (ADRs)

- Idempotencia de import via SHA1 — ADR-012 (hashing `apps/core/imports/hashing.py`), reutilizada por `_compute_external_hash`.
- Scope C2 de Deslocamentos (Coord/Apoio/DAT scoped via `EquipeGerencia`, Controle/Gerente full) — decisao de stakeholder 2026-04-27, documentada em [`rbac_authorization_matrix.md`](../../rbac_authorization_matrix.md) (§3) e PR #1250.
- Centralizacao DAT-only do import (`HasPerm("import_spreadsheet")`) — PR-A1 DAT-Imports (2026-04-29).

## Testes que cobrem

- [`apps/core/tests/test_deslocamento_api.py`](../../../backend/apps/core/tests/test_deslocamento_api.py) — CRUD, filtros, validacoes (datas, origem!=destino), AuditLog.
- [`apps/core/tests/test_deslocamento_rbac.py`](../../../backend/apps/core/tests/test_deslocamento_rbac.py) — scope C2 (Coord/DAT veem so a propria gerencia; sem vinculo -> 0; Controle/Gerente full).
- [`apps/core/tests/test_import_deslocamentos.py`](../../../backend/apps/core/tests/test_import_deslocamentos.py) — service + view + RBAC `import_spreadsheet` + idempotencia.
- [`apps/core/tests/test_monthly_with_deslocamento.py`](../../../backend/apps/core/tests/test_monthly_with_deslocamento.py) — codigos `D`/`D1` e precedencia na grade.
- [`apps/core/tests/test_rbac_matrix_endpoint_coverage.py`](../../../backend/apps/core/tests/test_rbac_matrix_endpoint_coverage.py) / [`test_rbac_matrix_living.py`](../../../backend/apps/core/tests/test_rbac_matrix_living.py) — `deslocamentos` na matriz viva (`_ALL_AUTH`).

## Pontos de atencao / dividas conhecidas

- **GAP de documentacao**: este modulo nao tinha spec/doc canonico ate aqui (criada do zero). Confirmar dono de produto da regra de negocio de viagem.
- **RD-04 vs Deslocamento**: facil confundir. RD-04 (buffer entre municipios) le municipios de *eventos*, **nao** o modelo `Deslocamento`. Nao assumir que cadastrar um deslocamento gera buffer no motor de conflitos — hoje **nao gera**. Avaliar se essa desconexao e intencional ou divida.
- **`DjangoFilterBackend` decorativo**: esta em `filter_backends` mas sem `filterset_class`/`filterset_fields`; o filtro efetivo e manual em `get_queryset`. Remover o backend ocioso ou migrar para `FilterSet` (alinhar com a convencao do resto do app; cuidado com sufixo `_id` — ver memoria de FilterSet naming).
- **`external_hash` nulo no CRUD manual**: registros criados pela UI nao tem hash; um import posterior com os mesmos campos-chave criaria uma 2a linha (hash so e calculado no import). Possivel duplicacao cruzada UI x import.
- **`origem`/`destino` sao texto livre** (CharField, nao FK `Municipio`) — sem normalizacao canonica de nomes de municipio; risca consistencia com o resto do dominio.
- **Import e sincrono** (nao usa ImportJob/Celery do ASQ-005); planilhas grandes ocupam o request. Avaliar migracao para import assincrono.

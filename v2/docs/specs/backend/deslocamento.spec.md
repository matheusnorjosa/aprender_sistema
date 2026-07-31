---
title: Deslocamento
status: canonical
last_verified: 2026-07-24
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
  - v2/backend/apps/core/rbac/policies.py
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
- **Dry-run por padrao no import**: `dry_run=true` faz `transaction.set_rollback(True)`; nada e persistido. O endpoint inteiro exige `HasPerm("import_spreadsheet")` (DAT ou superuser), tanto em dry-run quanto em apply. Isolamento savepoint-por-linha (ASQ-016): uma linha ruim nao derruba o lote. ⚠️ **O parse de `dry_run` e fail-OPEN** (achado `M04-05`, issue #1649): `views_import_deslocamentos.py:96-97` faz `dry_run = dry_run_param in {"1","true","t","yes","y"}` — qualquer valor fora dessa allowlist (`sim`, `maybe`, typo, string vazia) vira **apply**. Só a ausencia do parametro cai no default `true`.
- **Leitura: scope por gerencia + self-service** (`views_deslocamento.py:147-153`):
  - Superuser **ou** capability `view_all_availability` (Controle/Gerente via seed 0078) -> ve todos os deslocamentos.
  - Demais autenticados -> `Q(usuario=user) | Q(usuario__equipes__gerencia_id__in=<gerencias do user>)`. **O proprio dono SEMPRE ve os proprios deslocamentos**, mesmo sem vinculo de `EquipeGerencia` (#1454, comentario em `:149-150`). A regra anterior desta spec ("sem vinculo -> 0 resultados") deixou de valer.
- **Escrita: owner-forced com delegacao por capability** (#1454, audit 2026-07-10) — **isto NAO estava documentado**:
  - `perform_create` (`:196-222`): `usuario` omitido ou == `request.user` -> grava para o proprio (`delegated=False`). `usuario` != `request.user` -> exige `user_can_delegate_deslocamento`, senao **403** (`:219-220`).
  - `perform_update`/`perform_destroy` passam por `_ensure_owner_or_delegate` (`:182-194`): mexer no registro de outro exige a mesma capability, senao 403.
  - `user_can_delegate_deslocamento` (`rbac/policies.py:449-468`) so aceita superuser, `operate_preagenda` ou `view_all_availability`. O docstring e explicito: **Coordenador, Apoio, Gerente, Diretoria e Formador -> `False`**.
  - ⚠️ Consequencia real (achado `M09-05`, issue #1621, épico #1655): o formulario da UI marca "Formador" como **obrigatorio** (`DeslocamentosPage.tsx:431-447`) e sempre envia `usuario` de terceiro (`:209-216`), com opcoes vindas de `/api/options/formadores-do-setor/`, que filtra `papel="FORMADOR"` (`views_options.py:377-381`). Um Coordenador **nao aparece na propria lista**, nao consegue se auto-selecionar nem omitir o campo — logo todo POST dele cai no ramo de delegacao e recebe **403**. O comentario de `v2/frontend/src/api/deslocamentos.ts:91` ("Backend força `usuario=request.user`") so vale quando o campo e omitido, o que a UI impede.
- **Auditoria**: CREATE (`:225-241`) e DELETE (`:321-336`, antes de deletar) gravam sempre `AuditLog` com `usuario`, IP (X-Forwarded-For -> X-Real-IP -> REMOTE_ADDR, `:64-72`), user-agent truncado em 200 e — no CREATE — o flag `delegated`. **O UPDATE só grava se houver mudança** (`if changed_fields:`, `:293`) e o diff cobre apenas `origem, destino, start_date, end_date, observacao` (`:273`): **troca de `usuario` (transferência do registro) não entra no diff nem gera log**.
- **CP**: roda apenas em Docker (CP-01); idioma RBAC e `permission_classes=[HasPerm("...")]` (CP — grupos diretos banidos por `scripts/rbac_lint.py`).
- **Codigos de grade** (precedencia `X > D1 > 2 > E > T/P > D`): `D` = deslocamento sem evento/bloqueio; `D1` = evento + deslocamento sem bloqueio. Definidos em `monthly_grid_service.py`.

## API / Interface

CRUD (router DRF, basename `deslocamento`):

- `GET /api/deslocamentos/` — lista paginada (50/pagina; `page_size_query_param="page_size"` **esta definido** em `views_deslocamento.py:79`, com `max_page_size=100`, entao `?page_size=N` e respeitado), ordenada por `-start_date`.
- `GET /api/deslocamentos/{id}/`, `POST /api/deslocamentos/`, `PUT/PATCH /api/deslocamentos/{id}/`, `DELETE /api/deslocamentos/{id}/`.
- **Permissao do ViewSet**: `[IsAuthenticated]` no nivel de classe (`:123`), **mas a escrita nao e livre**: `perform_create`/`perform_update`/`perform_destroy` aplicam o gate owner-or-delegate descrito em §Contratos. Nao ha `HasPerm` de classe porque a leitura e controlada por *visibilidade* (queryset).
- **Filtros** (query params, aplicados manualmente em `get_queryset`): `usuario_id` (exato), `data_inicio` (`start_date >=`), `data_fim` (`end_date <=`), `origem` (`icontains`), `destino` (`icontains`). **Nao ha `FilterSet`/`filterset_fields` declarado** — `DjangoFilterBackend` esta em `filter_backends` mas o filtro real e o codigo manual; `OrderingFilter` cobre `start_date|end_date|origem|destino`.

Import em massa:

- `POST /api/deslocamentos/import/` — `ImportDeslocamentosView`. Permissao `[IsAuthenticated, HasPerm("import_spreadsheet")]` (DAT ou superuser). Query `dry_run=true|false` (default `true`). Body multipart `file` (CSV/XLSX). Validacao de upload (tamanho/MIME/magic bytes) e temp-file sanitizado (path-injection mitigado). Retorna `{stats:{created,updated,unchanged,skipped}, pendencias:{usuarios,dates,outros}, dry_run, file}`. Colunas aceitas com headers flexiveis (`usuario|email|nome`, `origem`, `destino`, `data_inicio`, `data_fim`, `observacao`); datas parseadas em ISO, `dd/mm/yyyy` e serial Excel.

Schema detalhado/exemplos: ver `API_REFERENCE` quando disponivel.

## Fluxos principais

**Lancamento manual (UI dedicada)**: operador abre `DeslocamentosPage`, filtra por usuario/datas/origem/destino, cria/edita via modal -> `POST`/`PUT` -> serializer valida (datas, origem!=destino) -> `perform_create/update` aplica o gate owner-or-delegate, grava registro + `AuditLog`. `external_hash` so e setado pelo import (CRUD manual deixa null). ⚠️ Hoje esse fluxo **falha com 403 para Coordenador** — ver `M09-05` em §Contratos.

**Import em massa (caminho feliz)**: DAT envia planilha -> `dry_run=true` retorna `stats`/`pendencias` para revisao -> apos validacao, `dry_run=false` persiste create-only (atualiza so `observacao`). Idempotente por `external_hash`.

**Erros relevantes do import**: usuario nao resolvido (email>nome) -> `skipped.usuario` + `pendencias.usuarios`; origem/destino ausentes -> `skipped.other`; data invalida ou `data_fim < data_inicio` -> `skipped.dates`; qualquer excecao de linha e isolada por savepoint e some em `pendencias.outros` (o lote continua).

**Reflexo na disponibilidade**: a grade mensal carrega os deslocamentos do mes, distribui por dia/pessoa e aplica precedencia, emitindo `D`/`D1`. Nao bloqueia agendamento por si so — e sinalizacao visual.

## Decisoes relacionadas (ADRs)

- Idempotencia de import via SHA1 — ADR-012 (hashing `apps/core/imports/hashing.py`), reutilizada por `_compute_external_hash`.
- Scope C2 de Deslocamentos (Coord/Apoio/DAT scoped via `EquipeGerencia`, Controle/Gerente full) — decisao de stakeholder 2026-04-27, documentada em [`rbac_authorization_matrix.md`](../../rbac_authorization_matrix.md) (§3) e PR #1250.
- Centralizacao DAT-only do import (`HasPerm("import_spreadsheet")`) — PR-A1 DAT-Imports (2026-04-29).

## Testes que cobrem

- [`apps/core/tests/test_deslocamento_api.py`](../../../backend/apps/core/tests/test_deslocamento_api.py) — CRUD, filtros, validacoes (datas, origem!=destino), AuditLog.
- [`apps/core/tests/test_deslocamento_rbac.py`](../../../backend/apps/core/tests/test_deslocamento_rbac.py) — scope de leitura (Coord/DAT veem a propria gerencia; Controle/Gerente full).
- [`apps/core/tests/test_deslocamento_idor_1454.py`](../../../backend/apps/core/tests/test_deslocamento_idor_1454.py) — gate owner-or-delegate no create/update/destroy (#1454).
- [`apps/core/tests/test_import_deslocamentos.py`](../../../backend/apps/core/tests/test_import_deslocamentos.py) — service + view + RBAC `import_spreadsheet` + idempotencia.
- [`apps/core/tests/test_monthly_with_deslocamento.py`](../../../backend/apps/core/tests/test_monthly_with_deslocamento.py) — codigos `D`/`D1` e precedencia na grade.
- [`apps/core/tests/test_rbac_matrix_endpoint_coverage.py`](../../../backend/apps/core/tests/test_rbac_matrix_endpoint_coverage.py) / [`test_rbac_matrix_living.py`](../../../backend/apps/core/tests/test_rbac_matrix_living.py) — `deslocamentos` na matriz viva (`_ALL_AUTH`).

## Pontos de atencao / dividas conhecidas

- **Contrato FE↔BE quebrado no create** (`M09-05`, issue #1621): ver §Contratos. A decisao pendente e de produto — ou o backend passa a aceitar auto-registro de Coordenador, ou a UI para de exigir "Formador" e passa a permitir o proprio usuario. Nao "consertar" so um lado.
- **Filtros Origem/Destino inutilizaveis na UI** (`M09-06`, issue #1622, épico #1668): o defeito e de frontend e o mecanismo e o early-return `if (loading) return <div>Carregando...</div>` em `DeslocamentosPage.tsx:324-326`. Cada tecla -> `handleFilterChange` (`:387-400`, `:160-162`) -> `filters` muda -> `loadDeslocamentos` recriado (`useCallback([filters])`, `:120-135`) -> `setLoading(true)` -> **a arvore inteira, filtros inclusive, desmonta**. Os `<Input>` sao nao-controlados, entao remontam vazios e sem foco. Nao ha debounce: 1 request por tecla. (Nao e "componente redefinido no render".)
- **Paginacao**: o backend respeita `?page_size` (`views_deslocamento.py:79`); a `DeslocamentosPage` fixa `pageSize: 50` e nunca envia o parametro (`:90`, `:126-128`), sem `showSizeChanger`. O achado `M18-06` (épico #1653) e de frontend neste modulo.
- **GAP de documentacao (resolvido)**: este modulo nao tinha spec/doc canonico ate 2026-06-19. Confirmar dono de produto da regra de negocio de viagem.
- **RD-04 vs Deslocamento**: facil confundir. RD-04 (buffer entre municipios) le municipios de *eventos*, **nao** o modelo `Deslocamento`. Nao assumir que cadastrar um deslocamento gera buffer no motor de conflitos — hoje **nao gera**. Avaliar se essa desconexao e intencional ou divida.
- **`DjangoFilterBackend` decorativo**: esta em `filter_backends` mas sem `filterset_class`/`filterset_fields`; o filtro efetivo e manual em `get_queryset`. Remover o backend ocioso ou migrar para `FilterSet` (alinhar com a convencao do resto do app; cuidado com sufixo `_id` — ver memoria de FilterSet naming).
- **`external_hash` nulo no CRUD manual**: registros criados pela UI nao tem hash; um import posterior com os mesmos campos-chave criaria uma 2a linha (hash so e calculado no import). Possivel duplicacao cruzada UI x import.
- **`origem`/`destino` sao texto livre** (CharField, nao FK `Municipio`) — sem normalizacao canonica de nomes de municipio; risca consistencia com o resto do dominio.
- **Import e sincrono** (nao usa ImportJob/Celery do ASQ-005); planilhas grandes ocupam o request. Avaliar migracao para import assincrono.

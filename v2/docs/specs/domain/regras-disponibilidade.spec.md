---
title: Regras de Disponibilidade (RD-01..RD-08)
status: canonical
last_verified: 2026-06-19
sources_of_truth:
  - v2/backend/apps/core/services/availability_service.py
  - v2/backend/apps/core/views_availability.py
  - v2/backend/apps/core/views_availability_monthly.py
  - v2/backend/apps/core/types.py
  - v2/backend/apps/core/services/config_service.py
  - v2/backend/apps/core/utils/cache_utils.py
  - v2/backend/apps/core/tests/test_availability_service.py
  - v2/backend/config/settings.py
  - v2/docs/GUIDE_AVAILABILITY.md
  - docs/architecture/project-decisions/ADR-003-availability-rules-timezone.md
owner: domain
supersedes:
  - v2/docs/GUIDE_AVAILABILITY.md
  - docs/architecture/project-decisions/ADR-003-availability-rules-timezone.md
related:
  - v2/docs/specs/backend/rbac.spec.md
  - v2/docs/specs/domain/politica-aprovacao.spec.md
---

# Regras de Disponibilidade (RD-01..RD-08)

## Proposito

As Regras de Disponibilidade (RD-01 a RD-08, **CP-03**) definem como o sistema detecta conflitos de agenda de um formador/coordenador ao se considerar um novo intervalo de evento. Substituem as antigas formulas Excel que falhavam em bordas de timezone (eventos proximos da meia-noite caiam no dia errado). O nucleo e um servico **puro e consultivo**: dado um usuario, um intervalo `(inicio, fim)` e um municipio opcional, devolve uma lista estruturada de conflitos. Nao grava, nao aprova, nao bloqueia nada por si so.

O servico e a SSOT da logica de conflito. Os endpoints DRF (`/api/availability/check/`, `check-many/`) e a Grade Mensal apenas o consomem. A decisao final de disponibilidade e operacional/humana (Superintendencia via Grade Mensal); o check e ferramenta de apoio a criacao e aprovacao de solicitacoes.

## Fonte de verdade no codigo

- [`v2/backend/apps/core/services/availability_service.py`](../../../backend/apps/core/services/availability_service.py) — `check_conflicts(*, usuario, inicio, fim, municipio=None) -> CheckResult`; dataclasses `Conflict` e `CheckResult`; helpers `to_local`, `same_day_local`, `_fmt_interval_local`. Decorado com `@cache_availability_check(timeout=300)`.
- [`v2/backend/apps/core/types.py`](../../../backend/apps/core/types.py) — `ConflictCode: TypeAlias = Literal["X", "T", "P", "D", "M", "E"]`.
- [`v2/backend/apps/core/views_availability.py`](../../../backend/apps/core/views_availability.py) — `AvailabilityCheckView`, `AvailabilityCheckManyView`, `AvailabilityBlockViewSet`, helpers `is_privileged_user` / `can_check_availability_for_others`.
- [`v2/backend/apps/core/views_availability_monthly.py`](../../../backend/apps/core/views_availability_monthly.py) — `MonthlyAvailabilityView` (grade mensal, codigos de celula).
- [`v2/backend/apps/core/services/config_service.py`](../../../backend/apps/core/services/config_service.py) — `get_cfg("availability", {})` (overrides em runtime de buffer/limite).
- [`v2/backend/config/settings.py`](../../../backend/config/settings.py) — `TIME_ZONE = TZ_PROJECT = "America/Fortaleza"`; `TRAVEL_BUFFER_MINUTES` (default 120); `AVAILABILITY_DAILY_LIMIT_HOURS` (default 8).

Doc detalhado da API/permissoes da grade: [`v2/docs/GUIDE_AVAILABILITY.md`](../../GUIDE_AVAILABILITY.md). Decisao arquitetural: [`ADR-003`](../../../../docs/architecture/project-decisions/ADR-003-availability-rules-timezone.md).

## Contratos e invariantes

Codigos de conflito **emitidos pelo servico** (confirmado no codigo):

| Codigo | Regra | Significado | Condicao |
|--------|-------|-------------|----------|
| `X` | RD-01 | Sobreposicao com evento aprovado | `inicio < ev.fim AND fim > ev.inicio` (overlap >= 1 min). Tambem usado em "intervalo invalido". |
| `T` | RD-02 | Bloqueio total | `AvailabilityBlock` aprovado, `tipo="T"`, interseccao com o intervalo. |
| `P` | RD-03 | Bloqueio parcial | `AvailabilityBlock` aprovado, `tipo != "T"` (ex.: `"P"`), interseccao com o subintervalo. |
| `D` | RD-04 | Buffer de deslocamento insuficiente | Evento vizinho (anterior/posterior) em cidade diferente com gap `< buffer_min`. |
| `M` | RD-05 | Capacidade diaria excedida | Soma de minutos no mesmo dia local `> AVAILABILITY_DAILY_LIMIT_HOURS * 60`. |

Invariantes (NAO podem ser violados):

- **CP-03** — RD-01..RD-08 sao clausula petrea. Timezone Fortaleza com storage UTC.
- **RD-01 (adjacencia)**: `fim == inicio_vizinho` NAO conflita. Interseccao usa `<`/`>` estritos, nunca `<=`/`>=`.
- **RD-04 (limite exato)**: gap exatamente igual ao buffer **passa**; so `mins < buffer_min` conflita. `municipio=None` (de qualquer lado) e tratado como **cidade diferente** → exige buffer (fix #588). Mesmo municipio → buffer 0.
- **RD-05**: a duracao do **novo** intervalo entra na soma do dia; o recorte por dia usa range de datetime UTC derivado do dia local (`day_start`/`day_end`), nunca `.date()` cru (fix #249, bordas de meia-noite).
- **RD-06**: comparacao sempre em `America/Fortaleza` via `to_local()`; entradas naive sao assumidas UTC (`make_aware(..., utc)`).
- **RD-07**: o servico **reporta TODOS** os conflitos encontrados, na ordem Bloqueios (T/P) → Sobreposicao (X) → Buffer (D) → Capacidade (M). Nao ha short-circuit.
- **RD-08**: cada `Conflict` carrega `code`, `title`, `detail` (com intervalo formatado `HH:MM dd/mm`) e `ref_id` opcional.
- **Pureza**: `check_conflicts` so le; considera apenas `Solicitacao.status == APROVADO` e `AvailabilityBlock.status == APROVADO`. Validacao basica: `fim <= inicio` → `ok=False` com conflito `X` "Intervalo invalido".
- **Cache**: resultado cacheado por 300s (`@cache_availability_check`); TTL curto porque dados mudam com frequencia.

> Nota: `ConflictCode` inclui `E`, mas o servico **nao emite `E`** — `E`/`D1`/`2` sao codigos de celula da legenda da Grade Mensal (`GUIDE_AVAILABILITY.md`), nao saidas de `check_conflicts`.

## API / Interface

Funcao publica: `check_conflicts(*, usuario: Usuario, inicio: datetime, fim: datetime, municipio: Municipio | None = None) -> CheckResult`.

Endpoints DRF (rota em `apps/core/urls.py`):

- `GET /api/availability/check/` — params `usuario_id` (obrig.), `inicio`/`fim` ISO8601 (obrig.), `municipio_id` (opc.). Resposta `{ "ok": bool, "conflicts": [{code,title,detail,ref_id}] }`.
- `POST /api/availability/check-many/` — body `{ "usuarios_ids": [...], "inicio", "fim", "municipio_id"? }`. Resposta `{ "results": [{usuario_id, ok, conflicts}] }`.
- `GET /api/availability/monthly/` — grade mensal (legenda/celulas); ver `GUIDE_AVAILABILITY.md`.
- `GET/POST /api/availability-blocks/` — CRUD de `AvailabilityBlock` (formador declara os proprios; RD-02/RD-03).

RBAC dos endpoints de check: `permission_classes = [HasPerm("view_all_availability") | HasPerm("create_solicitation") | HasPerm("approve_solicitation_batch")]`. Filtro fino em runtime: consultar **outro** usuario exige `can_check_availability_for_others`; senao 403. Throttle scope `availability_check`. (Linguagem RBAC canonica `HasPerm`; grupos diretos banidos por `scripts/rbac_lint.py`.)

## Fluxos principais

Caminho feliz / deteccao (`check_conflicts`):

1. Valida `fim > inicio` (senao retorna `X` "Intervalo invalido").
2. Carrega `buffer_min` e `daily_limit_h` de `get_cfg("availability", {})` com fallback para settings (120 min / 8 h).
3. Monta `events_qs` = `Solicitacao` APROVADO onde o usuario e dono **ou** participante (`participations__usuario`).
4. RD-02/RD-03: itera blocos aprovados que intersectam → emite `T` ou `P`.
5. RD-01: itera eventos aprovados que intersectam → emite `X`.
6. RD-04: pega evento imediatamente anterior (`fim__lte=inicio`) e posterior (`inicio__gte=fim`); se cidade difere e gap `< buffer_min`, emite `D`.
7. RD-05: soma minutos dos eventos que tocam o dia local + duracao do novo intervalo; se `> limite`, emite `M`.
8. Retorna `CheckResult(ok=(len(conflicts)==0), conflicts=...)`.

Caminhos de erro do endpoint `check/`: `usuario_id` ausente/invalido → 400; usuario inexistente → 404; consultar outro sem permissao → 403; `municipio_id` invalido → 400; `inicio`/`fim` ausentes ou nao-ISO → 400; `fim <= inicio` → 400; nao autenticado → 401/403. Datetimes naive sao convertidos para UTC antes do servico (RD-06).

## Decisoes relacionadas (ADRs)

- [ADR-003 — Regras de Disponibilidade e Timezone (RD-01..RD-08)](../../../../docs/architecture/project-decisions/ADR-003-availability-rules-timezone.md) — decisao de timezone-aware + os 8 codigos/regras.
- Fixes historicos referenciados no codigo: #588 (`municipio=None` = cidade diferente), #249 (bordas de meia-noite via range UTC), #1222/PR #1183 (realinhamento RBAC do check), D9/PR #1308 hardening (`can_check_availability_for_others`).

## Testes que cobrem

[`v2/backend/apps/core/tests/test_availability_service.py`](../../../backend/apps/core/tests/test_availability_service.py):

- `TestAvailabilityServiceRules` — `test_conflict_overlap_total`/`_partial` (X), `test_no_conflict_adjacent_end_equals_start` (RD-01 adjacencia), `test_block_total_T_prevents_any_event` (T), `test_block_partial_P_prevents_inside_allows_outside` (P), `test_travel_buffer_between_cities_required` / `test_same_city_allows_zero_buffer` (D), `test_daily_capacity_M_exceeded` (M), `test_timezone_aware_fortaleza_localtime` + `test_midnight_boundary_timezone_aware` (RD-06).
- `TestAvailabilityCheckEndpoint` — 200/400/401-403/404, `usuario_id` obrigatorio, validacao de datas, batch `check-many/`, e `test_permission_only_self_or_privileged` (403 RBAC ao checar outro).
- `TestAvailabilityServiceAdditional` — `test_multi_formador_any_conflict_blocks` (RD-01 multi-formador), `test_conflict_messages_include_codes_and_intervals` (RD-08: estrutura `{code,title,detail}` + intervalo).

## Pontos de atencao / dividas conhecidas

- **Codigo `E` orfao no `ConflictCode`**: presente no `Literal` mas nunca emitido pelo servico (so legenda da grade). Possivel fonte de confusao entre saida do check e celulas da Grade Mensal.
- **TOCTOU**: `check_conflicts` e consultivo e cacheado por 300s; entre o check e a aprovacao/criacao real outro evento pode ser aprovado. A decisao final NAO e atomica com o check — por design, a aprovacao manual (Superintendencia) e o gate. Nao tratar o `ok=True` como garantia transacional.
- **Sem checagem de buffer transitivo**: RD-04 so olha o evento imediatamente anterior e o imediatamente posterior; cadeias com 3+ eventos no mesmo dia nao reavaliam o buffer entre pares nao-adjacentes.
- **Participacoes**: `events_qs` inclui solicitacoes onde o usuario e participante (`participations__usuario`) alem de dono; confirmar que novas relacoes de participacao mantenham esse filtro ao evoluir o modelo.
- **GUIDE_AVAILABILITY.md** descreve gerencias/setores de forma resumida (lista parcial); a SSOT de setores/funcoes e `apps.core.constants` (13 setores / 5 funcoes, sendo 4 funcoes RBAC + Gerente). Nao tratar a tabela do guia como SSOT organizacional.

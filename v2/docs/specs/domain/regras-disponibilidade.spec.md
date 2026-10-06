---
title: Regras de Disponibilidade (RD-01..RD-08)
status: canonical
last_verified: 2026-10-05
sources_of_truth:
  - v2/backend/apps/core/services/availability_service.py
  - v2/backend/apps/core/services/horas_formacao.py
  - v2/backend/apps/core/services/solicitacao_availability.py
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

As Regras de Disponibilidade (RD-01 a RD-08, **CP-03**) definem como o sistema detecta conflitos de agenda de um formador/coordenador ao se considerar um novo intervalo de evento. Substituem as antigas formulas Excel que falhavam em bordas de timezone (eventos proximos da meia-noite caiam no dia errado). O nucleo e uma funcao pura de calculo: dado um usuario, um intervalo `(inicio, fim)` e um municipio opcional, devolve uma lista estruturada de conflitos. Ela propria nao grava e nao aprova.

O calculo e a SSOT da logica de conflito, e hoje ele tem **dois consumidores com semanticas diferentes** (#1452):

| Camada | Funcao | Cache | Efeito |
|---|---|---|---|
| **Consultiva** | `check_conflicts` | 300s | So informa. Telas de disponibilidade, Grade Mensal, feedback no wizard. |
| **Enforcement** | `check_conflicts_uncached` via `solicitacao_availability.enforce_solicitacao_availability` | nenhum | **Bloqueia** create/update/approve/batch_approve com HTTP 400 `availability_conflict` quando ha conflito `X`, `T`, `P` ou `D`. O limite diario (`M`) nao existe mais (05/10/2026). |

A afirmacao "RD e apenas consultivo" era verdadeira ate o #1452 e **nao vale mais**: conflito e bloqueio duro, sem override, inclusive no fluxo `NAO_SUPER` ([`solicitacao_availability.py`](../../../backend/apps/core/services/solicitacao_availability.py)). A decisao humana da Superintendencia continua sendo o gate de *aprovacao* (PA), mas ela nao consegue mais aprovar por cima de um conflito.

> **Decisao do dono, 02/10/2026 — o limite diario avisa, nao barra.** "O evento na agenda pode ter quantas horas quiser." O motor continua calculando o RD-05, mas devolve o `M` em `warnings`, separado de `conflicts`. Criar, editar, aprovar (um e lote), a checagem previa do assistente e o importador de eventos **nao recusam mais** por limite diario. Sobreposicao (`X`), bloqueio (`T`, `P`) e deslocamento (`D`) continuam barrando exatamente como antes. A contagem de horas de formacao com teto por dia **ainda nao existe** (esta na fila): o aviso so diz que o dia passa de N horas e que isso nao impede o evento. *(Historico: o aviso saiu em 05/10/2026, ver abaixo.)*

> **Decisao do dono, 05/10/2026 (OK explicito para mudar a RD-05 e a CP-03) — o aviso `M` sai; o parametro vira so o teto da contagem de horas.** O motor **nao calcula mais** o RD-05 e nao emite `M` em nenhum caminho (criar, editar, aprovar, lote, `check/`, `check-many/`, importador de eventos, 400 por outro motivo). O parametro `AVAILABILITY_DAILY_LIMIT_HOURS` continua em Configuracoes, editavel de 1 a 12 (padrao 8), com o rotulo "Teto de horas por evento (contagem)": e o teto da **contagem de horas de formacao (CH)**, nao limita a agenda. A regra da contagem (decisoes de 02/10 e 05/10/2026, como a planilha `Eventos!R`, exceto o coordenador): CH de um evento para uma pessoa = `min(fim − inicio, teto)`; as CH do dia se somam (5 h + 5 h = 10 h; nao ha teto por dia); evento que cruza a meia-noite conta inteiro no dia local do **inicio**; sem desconto de almoco; online conta igual; so evento **aprovado**, de qualquer projeto ou gerencia; conta o participante `FORMADOR` sempre e o coordenador responsavel (`Solicitacao.coordenador`; sem ele, quem criou) **so** com `coordenador_acompanha=True`; `COORD_ACOMPANHA` e `CONVIDADO` nao contam; a mesma pessoa conta uma vez por evento. SSOT: [`horas_formacao.py`](../../../backend/apps/core/services/horas_formacao.py), usada pela Grade Mensal (`ch_month`, `ch_year`, ranking; as duas abas) e pelo painel de Equipe (`horas_trabalhadas`), que dao o mesmo numero para a mesma pessoa e periodo. A decisao 6 de 02/10 falava em teto "por dia"; a de 05/10 a corrigiu para **por evento**.

> **Decisao do dono, 05/10/2026 (OK explicito para mudar a CP-03) — o coordenador so ocupa a agenda quando acompanha.** A conferencia de agenda (RD-01 sobreposicao, RD-02/03 bloqueios, RD-04 deslocamento e o aviso M) vale para **todos os formadores** do evento, sempre, e para o **coordenador responsavel** (`Solicitacao.coordenador`; sem ele, quem criou) **so quando `coordenador_acompanha=True`** ("O coordenador responsavel vai acompanhar o evento?", obrigatoria na criacao). Quem cria deixa de ser conferido por ter criado; os papeis `COORDENADOR` e `COORD_ACOMPANHA` nao ocupam mais (servem ao convite do Google). Segundo coordenador num evento entra na lista de formadores e e conferido como formador. Mudar a resposta de Nao para Sim num evento com conflito → 400 `availability_conflict` com o motivo. Eventos ja gravados ficam com a marca que tem no banco (um script de dados separado zera as importadas); o codigo nao depende dele.

## Fonte de verdade no codigo

- [`v2/backend/apps/core/services/availability_service.py`](../../../backend/apps/core/services/availability_service.py) — `_check_conflicts_impl` e o calculo RD-01..RD-08; dataclasses `Conflict` e `CheckResult`; helpers `to_local`, `same_day_local`, `_fmt_interval_local`. Duas entradas publicas:
  - `check_conflicts` — consultiva, decorada com `@cache_availability_check(timeout=300)`. A assinatura **nao** expoe `exclude_solicitacao_id` de proposito: a chave de cache vem de uma whitelist fixa de campos, entao um argumento extra mudaria o resultado sem mudar a chave (envenenamento de cache).
  - `check_conflicts_uncached` — enforcement, sempre le do banco, aceita `exclude_solicitacao_id` para o evento nao conflitar consigo mesmo ao ser revalidado.
- [`v2/backend/apps/core/services/solicitacao_availability.py`](../../../backend/apps/core/services/solicitacao_availability.py) — guard por participante (#1452). `collect_participants` le a tabela `Participation` ja gravada (nunca o payload) filtrando `role__in=ENFORCED_ROLES`; `lock_participants` toma `pg_advisory_xact_lock` por `usuario_id` em ordem ASC; `enforce_solicitacao_availability` e o ponto de entrada de create/update/approve. Antes do #1452 a checagem rodava **so no criador** da solicitacao — como o coordenador que cria tipicamente nao e o formador que atende, as regras rodavam na pessoa errada.
- [`v2/backend/apps/core/types.py`](../../../backend/apps/core/types.py) — `ConflictCode: TypeAlias = Literal["X", "T", "P", "D", "M", "E"]`.
- [`v2/backend/apps/core/views_availability.py`](../../../backend/apps/core/views_availability.py) — `AvailabilityCheckView`, `AvailabilityCheckManyView`, `AvailabilityBlockViewSet`, helpers `is_privileged_user` / `can_check_availability_for_others`.
- [`v2/backend/apps/core/views_availability_monthly.py`](../../../backend/apps/core/views_availability_monthly.py) — `MonthlyAvailabilityView` (grade mensal, codigos de celula).
- [`v2/backend/apps/core/services/config_service.py`](../../../backend/apps/core/services/config_service.py) — `parametros_disponibilidade()` (overrides em runtime de buffer/limite, via `get_cfg("availability", {})`; a mesma função alimenta a tela de Configurações).
- [`v2/backend/config/settings.py`](../../../backend/config/settings.py) — `TIME_ZONE = TZ_PROJECT = "America/Fortaleza"`; `TRAVEL_BUFFER_MINUTES` (default 120); `AVAILABILITY_DAILY_LIMIT_HOURS` (default 8).

Doc detalhado da API/permissoes da grade: [`v2/docs/GUIDE_AVAILABILITY.md`](../../GUIDE_AVAILABILITY.md). Decisao arquitetural: [`ADR-003`](../../../../docs/architecture/project-decisions/ADR-003-availability-rules-timezone.md).

## Contratos e invariantes

Codigos **emitidos pelo servico** (confirmado no codigo). `X`, `T`, `P` e `D` saem em `CheckResult.conflicts` e **barram**. `CheckResult.warnings` continua no contrato (chave aditiva de 02/10/2026), mas hoje vem sempre vazio: o `M` nao e mais emitido desde 05/10/2026.

| Codigo | Regra | Significado | Condicao |
|--------|-------|-------------|----------|
| `X` | RD-01 | Sobreposicao com evento aprovado | `inicio < ev.fim AND fim > ev.inicio` (overlap >= 1 min). Tambem usado em "intervalo invalido". |
| `T` | RD-02 | Bloqueio total | `AvailabilityBlock` aprovado, `tipo="T"`, interseccao com o intervalo. |
| `P` | RD-03 | Bloqueio parcial | `AvailabilityBlock` aprovado, `tipo != "T"` (ex.: `"P"`), interseccao com o subintervalo. |
| `D` | RD-04 | Buffer de deslocamento insuficiente | Evento vizinho (anterior/posterior) em cidade diferente com gap `< buffer_min`. |
| ~~`M`~~ | RD-05 | **Nao emitido desde 05/10/2026.** Era "dia com mais de N horas de eventos" (aviso). | O RD-05 agora e o teto da contagem de horas de formacao (`horas_formacao.py`), fora do motor de conflito. |

Invariantes (NAO podem ser violados):

- **CP-03** — RD-01..RD-08 sao clausula petrea. Timezone Fortaleza com storage UTC.
- **RD-01 (adjacencia)**: `fim == inicio_vizinho` NAO conflita. Interseccao usa `<`/`>` estritos, nunca `<=`/`>=`.
- **RD-04 (limite exato)**: gap exatamente igual ao buffer **passa**; so `mins < buffer_min` conflita. `municipio=None` (de qualquer lado) e tratado como **cidade diferente** → exige buffer (fix #588). Mesmo municipio → buffer 0.
- **RD-05 (teto da contagem de horas)**: desde 05/10/2026 (decisao do dono) nao e checagem de agenda: o motor nao soma horas do dia nem emite `M`. `AVAILABILITY_DAILY_LIMIT_HOURS` e o teto **por evento** da contagem de horas de formacao ([`horas_formacao.py`](../../../backend/apps/core/services/horas_formacao.py)): `min(fim − inicio, teto)`, somado no dia local do inicio, sem teto por dia. Regra completa na decisao de 05/10 acima. (De 02/10 a 05/10/2026 o `M` foi aviso em `warnings`; antes de 02/10, barrava.)
- **RD-06**: comparacao sempre em `America/Fortaleza` via `to_local()`; entradas naive sao assumidas UTC (`make_aware(..., utc)`).
- **RD-07**: o servico **reporta TUDO** o que encontra, sem short-circuit: em `conflicts`, na ordem Bloqueios (T/P) → Sobreposicao (X) → Buffer (D); `warnings` vem vazio desde 05/10/2026 (era o limite diario M). Invariante: `ok` e verdadeiro exatamente quando `conflicts` esta vazio; tudo em `conflicts` barra; nada em `warnings` barra.
- **RD-08**: cada `Conflict` carrega `code`, `title`, `detail` (com intervalo formatado `HH:MM dd/mm`) e `ref_id` opcional.
- **Pureza do calculo**: o calculo so le; considera apenas `Solicitacao.status == APROVADO` e `AvailabilityBlock.status == APROVADO`. Validacao basica: `fim <= inicio` → `ok=False` com conflito `X` "Intervalo invalido". Solicitacao `pendente` e **invisivel** para a checagem — e por isso que o guard precisa do advisory lock (duas transacoes concorrentes leriam a outra como inexistente).
- **Cache**: so na camada consultiva (`check_conflicts`, 300s via `@cache_availability_check`); TTL curto porque dados mudam com frequencia. O caminho de enforcement **nunca** le do cache. A chave tem versao no prefixo (`availability_check:v2:`): o objeto guardado ganhou `warnings` em 02/10/2026 e a versao impede servir um resultado antigo, sem o campo.
- **Quem e checado (enforcement)** (decisao do dono, 05/10/2026): os participantes gravados com `role` em `ENFORCED_ROLES` = `FORMADOR`, mais o coordenador responsavel quando o evento tem `coordenador_acompanha=True` (`coordenador_ocupante`: `solicitacao.coordenador`, ou `solicitacao.usuario` se a FK estiver vazia), deduplicados por id ([`solicitacao_availability.py`](../../../backend/apps/core/services/solicitacao_availability.py)). Quem criou **nao** entra por ter criado; `COORDENADOR` e `COORD_ACOMPANHA` nao ocupam. `CONVIDADO` fica de fora **de proposito** — e audiencia, nao recurso alocado; checa-lo estouraria o RD-05 de quem e convidado a varios eventos no mesmo dia. Convidado externo sem cadastro (`usuario=NULL` + `guest_email`) e fisicamente nao-checavel e volta em `skipped_guests`, sempre logado como `availability_guest_check_skipped` — nunca ignorado em silencio.
- **Evento existente que ocupa (SSOT `ocupa_agenda_q`)**: um evento aprovado ocupa a agenda de uma pessoa se ela e FORMADORA nele, ou se e a responsavel e ele tem `coordenador_acompanha=True` (mesma queda para `usuario` quando a FK esta vazia). E o par de `coordenador_ocupante`; os dois vivem em [`availability_service.py`](../../../backend/apps/core/services/availability_service.py) e valem para criar, editar, aprovar (um e lote), `check`/`check-many` e o importador de eventos.
- **Exclusao mutua (enforcement)**: `pg_advisory_xact_lock(1452, usuario_id)` em ordem ASC de id antes de ler. `select_for_update` sozinho tranca so a linha da propria solicitacao; duas solicitacoes distintas do mesmo formador trancam linhas disjuntas e ambas commitariam.

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
2. Carrega `buffer_min` por `parametros_disponibilidade()`: a chave gravada no Config `availability` vale (inclusive Buffer 0); sem ela, o settings (env; default 120 min). O teto de horas (default 8 h) vem da mesma funcao, mas so a contagem de horas o le. É a mesma fonte do `GET /api/config/`, então o valor que a tela mostra é o aplicado (auditoria UX 30/09).
3. Monta `events_qs` = `Solicitacao` APROVADO filtrada por `ocupa_agenda_q(usuario)`: a pessoa e FORMADORA, ou e a responsavel de evento com `coordenador_acompanha=True`.
4. RD-02/RD-03: itera blocos aprovados que intersectam → emite `T` ou `P`.
5. RD-01: itera eventos aprovados que intersectam → emite `X`.
6. RD-04: pega evento imediatamente anterior (`fim__lte=inicio`) e posterior (`inicio__gte=fim`); se cidade difere e gap `< buffer_min`, emite `D`.
7. (RD-05 nao roda aqui desde 05/10/2026.)
8. Retorna `CheckResult(ok=(len(conflicts)==0), conflicts=..., warnings=...)`.

Caminho de enforcement (`enforce_solicitacao_availability`, dentro de `transaction.atomic()`):

1. `collect_participants` le `Participation` gravada (`role__in=ENFORCED_ROLES`, so FORMADOR) + o responsavel se acompanha (`coordenador_ocupante`), dedup por id.
2. `lock_participants` toma `pg_advisory_xact_lock(1452, usuario_id)` em ordem ASC.
3. Para cada participante, `check_conflicts_uncached(..., exclude_solicitacao_id=solicitacao.pk)`.
4. `skipped_guests` nao vazio → `logger.warning("availability_guest_check_skipped")` (nao bloqueia).
5. Aviso (`guard.warnings`) → `logger.info("availability_warning")` com ids, sem nome (nao bloqueia). Hoje nao dispara: o motor nao emite aviso desde 05/10/2026.
6. Qualquer bloqueado → `ValidationAPIError` **400 `availability_conflict`**, com `conflicts` achatado (contrato legado) e `blocked_participants` por pessoa. A mensagem e `conflicts` so falam do que barra; os avisos calculados na mesma checagem vao em chaves aditivas (`errors.warnings` e `blocked_participants[].warnings`). A transacao inteira e desfeita — no `update`, a edicao nao persiste.

Call-sites: `perform_create` e `perform_update` ([`views_solicitacao.py`](../../../backend/apps/core/views_solicitacao.py)); `approve_solicitacao` e `batch_approve_solicitacoes` ([`solicitacao_approval.py`](../../../backend/apps/core/services/solicitacao_approval.py)). O importador de eventos pela tela (`eventos_import.py`, so evento futuro) usa `check_solicitacao_availability` e segue a mesma regra (sem `M`, nenhum dia cheio vira pendencia).

Caminhos de erro do endpoint `check/`: `usuario_id` ausente/invalido → 400; usuario inexistente → 404; consultar outro sem permissao → 403; `municipio_id` invalido → 400; `inicio`/`fim` ausentes ou nao-ISO → 400; `fim <= inicio` → 400; nao autenticado → 401/403. Datetimes naive sao convertidos para UTC antes do servico (RD-06).

## Decisoes relacionadas (ADRs)

- [ADR-003 — Regras de Disponibilidade e Timezone (RD-01..RD-08)](../../../../docs/architecture/project-decisions/ADR-003-availability-rules-timezone.md) — decisao de timezone-aware + os 8 codigos/regras.
- Fixes historicos referenciados no codigo: #588 (`municipio=None` = cidade diferente), #249 (bordas de meia-noite via range UTC), #1222/PR #1183 (realinhamento RBAC do check), D9/PR #1308 hardening (`can_check_availability_for_others`).

## Testes que cobrem

[`v2/backend/apps/core/tests/test_availability_service.py`](../../../backend/apps/core/tests/test_availability_service.py):

- `TestAvailabilityServiceRules` — `test_conflict_overlap_total`/`_partial` (X), `test_no_conflict_adjacent_end_equals_start` (RD-01 adjacencia), `test_block_total_T_prevents_any_event` (T), `test_block_partial_P_prevents_inside_allows_outside` (P), `test_travel_buffer_between_cities_required` / `test_same_city_allows_zero_buffer` (D), `test_dia_acima_de_8_horas_nao_gera_M` (sem M), `test_timezone_aware_fortaleza_localtime` + `test_midnight_boundary_timezone_aware` (RD-06).
- `TestAvailabilityCheckEndpoint` — 200/400/401-403/404, `usuario_id` obrigatorio, validacao de datas, batch `check-many/`, e `test_permission_only_self_or_privileged` (403 RBAC ao checar outro).
- `TestAvailabilityServiceAdditional` — `test_multi_formador_any_conflict_blocks` (RD-01 multi-formador), `test_conflict_messages_include_codes_and_intervals` (RD-08: estrutura `{code,title,detail}` + intervalo).

[`v2/backend/apps/core/tests/test_availability_sem_aviso_m.py`](../../../backend/apps/core/tests/test_availability_sem_aviso_m.py) (decisao de 05/10/2026): nenhum caminho devolve `M` — motor (inclusive teto 1 h e dia com 10 h), criar, editar, aprovar, lote, `check/` e `check-many/` (`warnings` vazio) e o 400 por sobreposicao; o evento das 07:00 as 23:00 e criado e aprovado sem log de aviso; e a guarda `TestOQueBarraContinuaBarrando`: `X`, `T`, `P` e `D` seguem dando 400 em criar, editar, aprovar e lote.

[`v2/backend/apps/core/tests/test_horas_formacao.py`](../../../backend/apps/core/tests/test_horas_formacao.py) (RD-05 como teto da contagem): 7h–23h = 8 h; 5 h + 5 h = 10 h; 22h–02h no dia do inicio; pendente nao conta; coordenador so com `coordenador_acompanha=True`; `COORD_ACOMPANHA`/convidado nao contam; online e `NAO_SUPER` contam; teto vem de Configuracoes; varias pessoas sem N+1; Grade Mensal (mes, ano, aba Coordenadores) e painel de Equipe dao o mesmo numero; grade em cache acompanha o teto salvo.

## Divergencias entre a regra escrita e o codigo

> As duas divergencias abaixo foram reconfirmadas por execucao contra `main d08acfa5` e depois
> **corrigidas no codigo** (epico #1664; detalhe e commits em
> [`availability.spec.md`](../backend/availability.spec.md)). Ficam aqui como historico; o texto
> de cada uma descreve o comportamento **anterior** ao conserto. Fonte:
> [`ACHADOS_REAIS.md`](../../audits/ACHADOS_REAIS.md).

### `M08-09` — RD-05 nao vale para intervalos que cruzam a meia-noite

**Severidade P2 · resolvido (PR #1796) · epico #1664 (`motor-disponibilidade-sem-ssot-de-regra`).** Desde 02/10/2026 o RD-05 e so aviso, entao o efeito que restava (recusa indevida) deixou de existir de qualquer forma; desde 05/10/2026 o motor nem calcula mais o RD-05.

O que a regra diz: nenhum usuario acumula mais de `AVAILABILITY_DAILY_LIMIT_HOURS` por dia local.

O que o codigo faz (em [`availability_service.py`](../../../backend/apps/core/services/availability_service.py)):

1. Deriva `inicio_date` **apenas** do dia local de `inicio`. Nenhum outro dia e avaliado.
2. Os eventos **ja existentes** sao recortados ao dia (`overlap_start`/`overlap_end`).
3. O **novo** intervalo entra inteiro, sem recorte (`new_duration = int((fim - inicio) ...)`).

Consequencia: um evento das 22:00 as 06:00 debita 480 min no dia 1 (onde so 120 min sao reais) e
**nao debita nada no dia 2** — a carga ja agendada do dia 2 nunca e somada. A regra falha nos dois
sentidos: falso positivo no dia de inicio, falso negativo no dia seguinte.

O fix #249 citado no invariante RD-05 corrigiu a **query** dos eventos existentes (range UTC em vez
de `.date()` cru); ele nao cobre o novo intervalo nem a avaliacao multi-dia.

### `M08-07` — a query de eventos existentes nao filtra papeis ocupantes

**Severidade P2 · resolvido (PR #1794) · epico #1664.** Hoje `events_qs` filtra `participations__role__in=ENFORCED_ROLES`.

`ENFORCED_ROLES` exclui `CONVIDADO` ao decidir **quem** e checado, mas `events_qs`
([`availability_service.py`](../../../backend/apps/core/services/availability_service.py))
monta os eventos ja existentes com `Q(usuario=usuario) | Q(participations__usuario=usuario)`,
**sem** `role__in`. As duas pontas discordam:

- Como *sujeito* da checagem, o convidado e ignorado (correto, por design).
- Como *evento existente*, uma participacao `CONVIDADO` bloqueia — conta em RD-01 (X), em RD-04 (D)
  e nos minutos de RD-05 (M).

Efeito pratico: a pessoa convidada a um evento fica indisponivel para ser **alocada** em outro,
que e exatamente o caso que a exclusao de `CONVIDADO` existia para evitar. Alcance atual e
estreito — hoje so o superuser (1 ativo) cria `Participation` `CONVIDADO` por `ParticipationAdmin`.

## Pontos de atencao / dividas conhecidas

- **Codigo `E` orfao no `ConflictCode`**: presente no `Literal` mas nunca emitido pelo servico (so legenda da grade). Possivel fonte de confusao entre saida do check e celulas da Grade Mensal.
- **TOCTOU: depende da camada.** No caminho **consultivo** (`check_conflicts`) o `ok=True` continua sem valor transacional — resultado cacheado por 300s, e outro evento pode ser aprovado no meio. No caminho de **enforcement** a janela esta fechada: `enforce_solicitacao_availability` roda dentro de `transaction.atomic()`, depois de `pg_advisory_xact_lock` por participante, lendo sem cache. Nao trocar um pelo outro: usar `check_conflicts` em enforcement reabre o double-booking que o lock existe para impedir.
- **Sem checagem de buffer transitivo**: RD-04 so olha o evento imediatamente anterior e o imediatamente posterior; cadeias com 3+ eventos no mesmo dia nao reavaliam o buffer entre pares nao-adjacentes.
- **Participacoes**: `events_qs` inclui solicitacoes onde o usuario e participante (`participations__usuario`) alem de dono; confirmar que novas relacoes de participacao mantenham esse filtro ao evoluir o modelo.
- **GUIDE_AVAILABILITY.md** descreve gerencias/setores de forma resumida (lista parcial); a SSOT de setores/funcoes e `apps.core.constants` (13 setores / 5 funcoes, sendo 4 funcoes RBAC + Gerente). Nao tratar a tabela do guia como SSOT organizacional.

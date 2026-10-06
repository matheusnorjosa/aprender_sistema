---
title: Disponibilidade (serviço)
status: canonical
last_verified: 2026-10-05
verified_at_commit: 0dd1dcb630fdc1cf9b2b488121553e89488dde3c
sources_of_truth:
  - v2/backend/apps/core/services/availability_service.py
  - v2/backend/apps/core/services/solicitacao_availability.py
  - v2/backend/apps/core/views_availability.py
  - v2/backend/apps/core/views_availability_monthly.py
  - v2/backend/apps/core/models/agenda.py
  - v2/backend/apps/core/utils/cache_utils.py
  - v2/backend/apps/core/urls.py
  - v2/docs/GUIDE_AVAILABILITY.md
owner: backend
supersedes:
  - v2/docs/GUIDE_AVAILABILITY.md
related:
  - ../domain/regras-disponibilidade.spec.md
  - ./solicitacao-approval.spec.md
  - ../../../../docs/architecture/project-decisions/ADR-003-availability-rules-timezone.md
  - ../../../../docs/business-rules/regras-disponibilidade.md
---

# Disponibilidade (serviço)

## Propósito

O módulo de disponibilidade calcula, de forma **consultiva**, se um formador/coordenador pode atender um novo evento num intervalo `(inicio, fim)`, aplicando as regras RD-01 a RD-08 (não-sobreposição, bloqueios total/parcial, buffer de deslocamento entre municípios, capacidade diária e timezone-aware). É a implementação de software das regras de negócio de agenda: substitui a planilha manual em que a Superintendência conferia conflitos à mão.

O coração é um **serviço puro, sem efeitos colaterais** (`check_conflicts`): não grava, não aprova e não muda estado — apenas retorna uma lista estruturada de conflitos. Quem transforma o cálculo em **bloqueio** é o guard `services/solicitacao_availability.py` (`enforce_solicitacao_availability`, #1452), chamado nos call-sites que gravam/aprovam evento (ver [solicitacao-approval.spec](./solicitacao-approval.spec.md)). Sobre o serviço existem três superfícies HTTP: check pontual, check em lote e a grade mensal usada pela UI da Superintendência.

## Fonte de verdade no código

- [`services/availability_service.py`](../../../backend/apps/core/services/availability_service.py) — `check_conflicts(*, usuario, inicio, fim, municipio=None) -> CheckResult` (variante cacheada) e `check_conflicts_uncached` (mesma assinatura, sem cache, usada pelo check em lote e por todo o enforcement transacional); ambas delegam a `_check_conflicts_impl`, que aceita `exclude_solicitacao_id`. Dataclasses `Conflict` (code/title/detail/ref_id) e `CheckResult` (ok/conflicts); helpers `to_local`, `same_day_local`, `_fmt_interval_local`. **SSOT das RD-01 a RD-08.**
- [`services/solicitacao_availability.py`](../../../backend/apps/core/services/solicitacao_availability.py) — guard de enforcement (#1452): `enforce_solicitacao_availability(solicitacao, *, action)` decide **quem** é checado (decisão do dono, 05/10/2026: todos os FORMADORES — `ENFORCED_ROLES` = FORMADOR — e o coordenador responsável só com `coordenador_acompanha=True`, via `coordenador_ocupante`; quem cria não entra por ter criado; COORDENADOR, COORD_ACOMPANHA e CONVIDADO não ocupam), toma advisory lock por participante e traduz conflito em `ValidationAPIError`. Chamado em create/update (`perform_create`/`perform_update` em `views_solicitacao.py`) e em approve/batch-approve (`approve_solicitacao`/`batch_approve_solicitacoes` em `solicitacao_approval.py`).
- [`views_availability.py`](../../../backend/apps/core/views_availability.py) (raiz de `apps/core/` — **arquivo ativo**) — `AvailabilityBlockViewSet`, `AvailabilityCheckView`, `AvailabilityCheckManyView` + helpers `is_privileged_user`, `can_check_availability_for_others`, `get_user_gerencias_ids`.
- [`views_availability_monthly.py`](../../../backend/apps/core/views_availability_monthly.py) — `MonthlyAvailabilityView` (grade mensal; delega para `services/monthly_grid_service.build_monthly_grid`).
- [`models/agenda.py`](../../../backend/apps/core/models/agenda.py) — `AvailabilityBlock` (`tipo` T/P, `status` aprovado, `inicio`/`fim` UTC; check constraints `fim>inicio` e `tipo in {T,P}`).
- [`utils/cache_utils.py`](../../../backend/apps/core/utils/cache_utils.py) — decorator `cache_availability_check` + `invalidate_availability_cache` (versionamento por usuário no Redis).
- [`urls.py`](../../../backend/apps/core/urls.py) — registro das rotas sob `/api/`.
- Guia detalhado (grade multi-setor, permissões, exemplos de payload): [`GUIDE_AVAILABILITY.md`](../../GUIDE_AVAILABILITY.md).

> Nota: `apps/core/views/availability.py` **não** é roteado — `urls.py` importa de `views_availability` (raiz, `urls.py`). Desde a correção do drift ele é apenas um **shim de compatibilidade**, que reexporta as views ativas (`views/availability.py`); não há mais cópia divergente do código.

## Contratos e invariantes

- **RD-01 (X)** — sobreposição com evento aprovado: overlap `inicio__lt=fim & fim__gt=inicio` ≥ 1 min gera conflito; intervalos **adjacentes** (`fim == inicio`) **não** conflitam.
- **RD-02 (T)** — bloqueio total aprovado que intersecta o intervalo impede qualquer evento.
- **RD-03 (P)** — bloqueio parcial aprovado impede só dentro do subintervalo.
- **RD-04 (D)** — buffer de deslocamento entre municípios distintos: exige `>= TRAVEL_BUFFER_MINUTES` (default 120). `municipio=None` é tratado como **cidade diferente** (fix #588) → exige buffer. Buffer **exato** (`== buffer`) passa; só `< buffer` conflita.
- **RD-05 (M)** — limite diário, **só aviso** (decisão do dono, 02/10/2026: "o evento na agenda pode ter quantas horas quiser"): quando a soma das durações (eventos do dia + novo intervalo) passa de `AVAILABILITY_DAILY_LIMIT_HOURS` (default 8h), o motor devolve `Conflict("M", ...)` em `CheckResult.warnings`, **não** em `conflicts`, e `ok` não muda. Nada é recusado por isso: criar, editar, aprovar (um e lote), a checagem prévia e o importador de eventos passam. O texto do aviso é para quem usa e não promete contagem de horas com teto, que ainda não existe (fila). Janela do dia calculada por **range de datetime em UTC** derivado do dia local (issue #249), não por `.date()`.
  - **Comportamento na virada do dia** (`_check_conflicts_impl`, achado M08-09 / épico #1664 — **resolvido** na PR #1796, commit `a986a250`): a capacidade é avaliada em **cada dia local** que o novo evento toca (`while day <= last_day`, de `to_local(inicio).date()` até `to_local(fim).date()`). Tanto os eventos **existentes** quanto o **novo** intervalo são recortados à janela de cada dia via `_clip_minutes` (`day_start = time.min`, `day_end = time.max`). Um evento que atravessa a meia-noite contribui apenas a fração correta em cada dia, e a capacidade do **dia seguinte também é avaliada**. Não existe mais `new_duration` somando o intervalo inteiro ao dia de início.
- **RD-06 (timezone)** — armazenamento em UTC; comparações de "mesmo dia" e formatação em `America/Fortaleza` (`settings.TZ_PROJECT`). Datas naive recebidas são tratadas como UTC.
- **RD-07** — reporta **tudo** o que encontra (sem short-circuit): `conflicts` (X, T, P, D) barra, `warnings` (M) só avisa; `ok = (len(conflicts) == 0)`. `CODIGOS_DE_AVISO = frozenset({"M"})` documenta quais códigos são aviso.
- **Contrato do guard** (`solicitacao_availability.py`): `ParticipantConflicts` e `GuardResult` têm `warnings` (padrão vazio). `GuardResult.ok` só olha `conflicts`. `enforce_solicitacao_availability` registra `availability_warning` (ids, sem nome) e segue. O 400 `availability_conflict` ganhou as chaves aditivas `errors.warnings` e `errors.blocked_participants[].warnings`; `errors.conflicts` e a mensagem só trazem o que barra, e `_MOTIVO_TEXTO` não tem mais a entrada `M`.
- **RD-08** — cada `Conflict` carrega `code`, `title`, `detail` (com formador/intervalo formatado) e `ref_id` quando aplicável.
- **Sem efeito colateral**: `check_conflicts` nunca grava nem aprova. Decisão de aprovação é externa.
- **Quem um evento existente ocupa** (decisão do dono, 05/10/2026; SSOT `ocupa_agenda_q` em `availability_service.py`): a pessoa é FORMADORA no evento (`participations__role__in=ENFORCED_ROLES`, só FORMADOR), **ou** é a coordenadora responsável (`coordenador`; sem FK, quem criou) e o evento tem `coordenador_acompanha=True`. Ser quem criou não ocupa mais (antes `Q(usuario=usuario)` ocupava sempre), nem os papéis COORDENADOR/COORD_ACOMPANHA. `CONVIDADO` segue fora (achado M08-07, PR #1794). O predicado é **único**: `ocupa_agenda_q` (evento existente) e `coordenador_ocupante` (evento novo) vivem lado a lado e o guard importa os dois, então criar, editar, aprovar, lote, `check`/`check-many` e o importador de eventos usam a mesma regra.
- **Idempotência/cache**: `check_conflicts` é cacheado por **300 s fixos** (`availability_service.py` passa `timeout=300` explícito ao decorator) com chave versionada por usuário e prefixo `availability_check:v2:` (o `v2` entrou em 02/10/2026 junto com `CheckResult.warnings`, para não servir objeto guardado antes do deploy, sem o campo; `test_cache_availability.py::test_resultado_guardado_na_chave_antiga_nao_e_lido`); mudanças nos dados do usuário fazem `invalidate_availability_cache(usuario_id)` bumpar a versão (miss natural, sem scan de Redis). A chave leva também os parâmetros vigentes (`parametros_disponibilidade()`: Buffer e limite diário), então salvar Configurações já vale na consulta seguinte, sem esperar os 300 s (auditoria UX 30/09, rodada 4; `test_config_api.py::test_config_buffer_salvo_vale_ja_na_checagem_consultiva_com_cache`). O **jitter ≤30 s** de `cache_utils._ttl_with_jitter()` só se aplica quando `timeout=None` — hoje isso vale apenas para a grade mensal (`MonthlyAvailabilityView`), **não** para o check de conflitos. O endpoint de lote não usa cache: chama `check_conflicts_uncached` (`AvailabilityCheckManyView`).
- **CP-03 (timezone Fortaleza)** e configuração via `config_service.get_cfg("availability", ...)` com fallback para `settings` — limites são **configuráveis**, não hardcoded.

## API / Interface

Todas montadas sob `/api/` (`config/urls.py` → `apps.core.urls`). Catálogo completo de payloads em [`GUIDE_AVAILABILITY.md`](../../GUIDE_AVAILABILITY.md) e `v2/docs/API_REFERENCE.md`.

| Método/rota | View | Permissão | Função |
|---|---|---|---|
| `GET /api/availability/check/` | `AvailabilityCheckView` | `HasPerm("view_all_availability") \| HasPerm("create_solicitation") \| HasPerm("approve_solicitation_batch")` + filtro runtime (próprio vs outros) | Check pontual de 1 usuário. Params: `usuario_id`, `inicio`, `fim` (ISO8601), `municipio_id?`. Resposta `{ok, conflicts[], warnings[]}` (`warnings` = limite diário; não muda `ok`). Throttle `availability_check` (60/min prod). |
| `POST /api/availability/check-many/` | `AvailabilityCheckManyView` | idem | Check em lote. Body `{usuarios_ids[], inicio, fim, municipio_id?}`. Resposta `{ok, results[]}`; cada item traz `{usuario_id, ok, conflicts[], warnings[]}`. |
| `GET /api/availability/monthly/` | `MonthlyAvailabilityView` | `[IsAuthenticated, CanViewAllAvailability \| HasSectorAccess]` (`MonthlyAvailabilityView`); superuser passa pelo bypass interno das policies, e o recorte fino por `EquipeGerencia` é feito em runtime (`allowed_user_ids`) | Grade mensal por gerência/setor. Params `year`, `month`, `role` (FORMADOR/COORDENADOR), `gerencia_id?`, `sector?` (casa `projeto__nome` exato; na tela é o campo "Projeto"), `q?`. Sem `gerencia_id`, a grade traz os **participantes de projetos SUPER** — é esse o rótulo da opção na `FiltersBar` (decisão 3 do dono, PR A de 2026-09-29). A `FiltersBar` oferece essa opção e as gerências ativas **só** a quem tem a policy `view_all_availability` (mesma SSOT do `CanViewAllAvailability`); os demais escolhem entre `GET /api/me/.gerencias` (vínculo `EquipeGerencia` vigente, gerência ativa), que é o que o `HasSectorAccess` aceita — grupo de setor não conta. Cache Redis 5 min (com jitter). |
| `GET/POST/PATCH/DELETE /api/availability-blocks/` | `AvailabilityBlockViewSet` | `IsAuthenticated` (escopo via queryset) | CRUD de bloqueios. Formador cria os próprios (auto `status="aprovado"`); delegação para outro Formador **no create** exige `user_can_delegate_availability_block` (+ AuditLog `DELEGATE_BLOCK_CREATE`). ⚠️ o **update não repete esse gate** — ver M08-01 abaixo. |

Idioma RBAC canônico: `permission_classes=[HasPerm("codename")]` (grupos diretos banidos por `scripts/rbac_lint.py`).

## Fluxos principais

**Check de conflito (`check_conflicts`)**

1. Valida intervalo (`fim > inicio`); inválido → `CheckResult(ok=False)` com `Conflict("X", "Intervalo inválido", ...)`.
2. Carrega `TRAVEL_BUFFER_MINUTES` e `AVAILABILITY_DAILY_LIMIT_HOURS` por `parametros_disponibilidade()` (`config_service.py`): vale a chave gravada no Config `availability` (inclusive Buffer 0); sem ela, o settings (env). A tela de Configurações (`GET /api/config/`) mostra pela mesma função, então o valor exibido é o aplicado (auditoria UX 30/09; antes a tela completava com 120/8 fixos e o motor ignorava o Buffer 0 por causa de `or`). Travado em `test_config_api.py::test_config_buffer_exibido_e_o_aplicado_no_rd04`.
3. **RD-02/03**: bloqueios aprovados que intersectam → conflito T ou P por `tipo`.
4. **RD-01**: eventos aprovados que sobrepõem → conflito X (`distinct()` por causa do JOIN de participação).
5. **RD-04**: evento imediatamente anterior/posterior; se cidade distinta e gap `< buffer` → conflito D.
6. **RD-05**: soma durações de cada dia local tocado (eventos existentes + novo intervalo, recortados ao dia); se `> limite` → aviso M em `warnings` (não barra).
7. **RD-07**: retorna `CheckResult(ok=len(conflicts)==0, conflicts=[...], warnings=[...])`.

**Endpoint de check pontual** — valida `usuario_id`/datas (400 em entrada inválida; 404 se usuário não existe); 403 se consultar outro usuário sem `can_check_availability_for_others`; força timezone-aware (RD-06); chama o serviço; serializa conflitos e avisos via `__dict__` (`conflicts` e `warnings`).

**Criação de bloqueio** — sem `usuario_id` (ou self): `usuario=created_by=request.user`, `status="aprovado"`. Com `usuario_id` de terceiro: 403 **antes** de qualquer lookup (anti-enumeração); depois valida target ativo + Função Formador (400 senão), salva e grava AuditLog.

**Edição de bloqueio (comportamento real, achado M08-01 / issue #1619)** — o `AvailabilityBlockViewSet` **não define** `update`/`partial_update`/`perform_update` (`get_queryset` e `perform_create` são os únicos overrides). Todo o gate de delegação vive em `perform_create`. No serializer, `usuario_id` é campo gravável e **não** está em `read_only_fields` (`AvailabilityBlockSerializer` em `serializers/agenda.py`) — e `usuario_id` é o *attname* da FK. Consequência: `PATCH /api/availability-blocks/{id}/` com `{"usuario_id": <outro>}` **transfere o bloqueio já aprovado para outro usuário**, sem `user_can_delegate_availability_block`, sem validar "target é Formador ativo" e sem AuditLog. O `get_queryset` limita *qual* registro um não-privilegiado pode editar (só os próprios), não *para quem* ele é transferido — qualquer autenticado pode criar um bloqueio próprio e reatribuí-lo. `status` continua `aprovado` porque é read-only e já foi persistido.

## Decisões relacionadas (ADRs)

- [ADR-003 — Availability rules & timezone](../../../../docs/architecture/project-decisions/ADR-003-availability-rules-timezone.md) (UTC storage + America/Fortaleza).
- Regra de negócio canônica: [`docs/business-rules/regras-disponibilidade.md`](../../../../docs/business-rules/regras-disponibilidade.md) (indexada por [regras-disponibilidade.spec](../domain/regras-disponibilidade.spec.md)).
- ASQ-007 (#780): invalidação granular de cache por versionamento (sem `cache.keys` pattern delete).

## Testes que cobrem

- [`tests/test_availability_service.py`](../../../backend/apps/core/tests/test_availability_service.py) — RD-01..08: overlap total/parcial, adjacência permitida, T/P, buffer entre cidades, mesma cidade buffer-zero, limite diário M como aviso, timezone Fortaleza, fronteira de meia-noite, multi-formador, mensagens com código/intervalo; endpoint check (auth, validações, lote, permissão self-vs-privileged).
- [`tests/test_availability_limite_diario_aviso.py`](../../../backend/apps/core/tests/test_availability_limite_diario_aviso.py) — decisão de 02/10/2026: M em `warnings`; criar, editar, aprovar e lote não recusam por limite diário (evento das 07:00 às 23:00 é criado e aprovado com aviso); `check/` e `check-many/` devolvem `warnings`; X + M dá 400 só pelo X; guarda de que X, T, P e D continuam barrando nos quatro pontos.
- [`tests/test_d9_availability_check.py`](../../../backend/apps/core/tests/test_d9_availability_check.py) — composição de permissão D9 (check de terceiros por Coord/Gerente Sup/Controle).
- [`tests/test_availability_batch.py`](../../../backend/apps/core/tests/test_availability_batch.py) — check-many.
- [`tests/test_api_availability_blocks.py`](../../../backend/apps/core/tests/test_api_availability_blocks.py), [`tests/test_availability_block_idor.py`](../../../backend/apps/core/tests/test_availability_block_idor.py), [`tests/test_availability_block_autoapproval.py`](../../../backend/apps/core/tests/test_availability_block_autoapproval.py), [`tests/test_pr13_delegated_availability_blocks.py`](../../../backend/apps/core/tests/test_pr13_delegated_availability_blocks.py) — CRUD de bloqueios, escopo IDOR, auto-aprovação, delegação.
- [`tests/test_availability_monthly_api.py`](../../../backend/apps/core/tests/test_availability_monthly_api.py), [`tests/test_availability_monthly_rbac.py`](../../../backend/apps/core/tests/test_availability_monthly_rbac.py) — grade mensal e RBAC por gerência.
- [`tests/test_cache_availability.py`](../../../backend/apps/core/tests/test_cache_availability.py) — cache versionado e invalidação.

## Pontos de atenção / dívidas conhecidas

- **`apps/core/views/availability.py` é shim, não cópia**: reexporta `views_availability` (`views/availability.py`); manter assim ou remover, mas não reimplementar ali.
- **TOCTOU**: o check é consultivo e cacheado (300 s); entre o check e a gravação da solicitação o estado pode mudar (novo evento/bloqueio concorrente). A garantia real de não-conflito é o guard `enforce_solicitacao_availability` (`services/solicitacao_availability.py`, #1452), que revalida sob advisory lock por participante em create/update/approve/batch-approve — não este serviço.
- **Motor de regra — achados M08-07 e M08-09 corrigidos** (épico #1664, `ACHADOS_REAIS.md`): M08-07 (ocupação sem filtro de papel) foi resolvido na PR #1794 (commit `cd60882a`) — a query de eventos existentes agora filtra por `ENFORCED_ROLES`; M08-09 (janela diária derivada só do dia de início) foi resolvido na PR #1796 (commit `a986a250`) — a capacidade passa a ser avaliada por dia local com recorte via `_clip_minutes`. Ambos descritos em §Contratos e invariantes. O épico #1664 segue **aberto** (a decisão de fechá-lo é do dono); estes dois achados de código já não descrevem defeito.
- **Bloqueio transferível por PATCH** (M08-01 / #1619): ver §Fluxos. Enquanto não houver `perform_update` com gate, tratar `usuario_id` como campo sensível em qualquer refactor do serializer.
- **`municipio=None` = cidade diferente** (RD-04): chamadas sem `municipio_id` disparam buffer; intencional (fix #588), mas pode gerar conflito D inesperado quando o município simplesmente não foi informado.
- **Permissão por composition OR** nos endpoints de check (3 caps) é tática; se a matriz crescer, migrar para Policy class (ver `feedback_composition_or_is_tactical`).
- **Grade mensal**: legenda/células dependem de `monthly_grid_service`; este spec cobre o contrato HTTP, não o algoritmo da grade (ver `GUIDE_AVAILABILITY.md`).
- Throttle dev relaxado (`600/min`) vs prod (`60/min`) — não confundir limites em testes locais.

---
title: Disponibilidade (serviço)
status: canonical
last_verified: 2026-07-24
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
- [`services/solicitacao_availability.py`](../../../backend/apps/core/services/solicitacao_availability.py) — guard de enforcement (#1452): `enforce_solicitacao_availability(solicitacao, *, action)` decide **quem** é checado (`ENFORCED_ROLES` = COORDENADOR, FORMADOR, COORD_ACOMPANHA — CONVIDADO fica de fora de propósito, `solicitacao_availability.py:28-37`), toma advisory lock por participante e traduz conflito em `ValidationAPIError`. Chamado em create/update (`views_solicitacao.py:308,452`) e em approve/batch-approve (`solicitacao_approval.py:136,305`).
- [`views_availability.py`](../../../backend/apps/core/views_availability.py) (raiz de `apps/core/` — **arquivo ativo**) — `AvailabilityBlockViewSet`, `AvailabilityCheckView`, `AvailabilityCheckManyView` + helpers `is_privileged_user`, `can_check_availability_for_others`, `get_user_gerencias_ids`.
- [`views_availability_monthly.py`](../../../backend/apps/core/views_availability_monthly.py) — `MonthlyAvailabilityView` (grade mensal; delega para `services/monthly_grid_service.build_monthly_grid`).
- [`models/agenda.py`](../../../backend/apps/core/models/agenda.py) — `AvailabilityBlock` (`tipo` T/P, `status` aprovado, `inicio`/`fim` UTC; check constraints `fim>inicio` e `tipo in {T,P}`).
- [`utils/cache_utils.py`](../../../backend/apps/core/utils/cache_utils.py) — decorator `cache_availability_check` + `invalidate_availability_cache` (versionamento por usuário no Redis).
- [`urls.py`](../../../backend/apps/core/urls.py) — registro das rotas sob `/api/`.
- Guia detalhado (grade multi-setor, permissões, exemplos de payload): [`GUIDE_AVAILABILITY.md`](../../GUIDE_AVAILABILITY.md).

> Nota: `apps/core/views/availability.py` **não** é roteado — `urls.py` importa de `views_availability` (raiz, `urls.py:46-47`). Desde a correção do drift ele é apenas um **shim de compatibilidade**, que reexporta as views ativas (`views/availability.py:15-19`); não há mais cópia divergente do código.

## Contratos e invariantes

- **RD-01 (X)** — sobreposição com evento aprovado: overlap `inicio__lt=fim & fim__gt=inicio` ≥ 1 min gera conflito; intervalos **adjacentes** (`fim == inicio`) **não** conflitam.
- **RD-02 (T)** — bloqueio total aprovado que intersecta o intervalo impede qualquer evento.
- **RD-03 (P)** — bloqueio parcial aprovado impede só dentro do subintervalo.
- **RD-04 (D)** — buffer de deslocamento entre municípios distintos: exige `>= TRAVEL_BUFFER_MINUTES` (default 120). `municipio=None` é tratado como **cidade diferente** (fix #588) → exige buffer. Buffer **exato** (`== buffer`) passa; só `< buffer` conflita.
- **RD-05 (M)** — capacidade diária: soma das durações (eventos do dia + novo intervalo) não pode exceder `AVAILABILITY_DAILY_LIMIT_HOURS` (default 8h). Janela do dia calculada por **range de datetime em UTC** derivado do dia local (issue #249), não por `.date()`.
  - **Comportamento real na virada do dia** (`availability_service.py:280-306`, achado M08-09 / épico #1664): a janela é derivada **só do dia local de `inicio`**. Eventos **existentes** que cruzam a meia-noite entram na soma, mas *clampados* à janela (`overlap_start = max(ev.inicio, day_start)`, `overlap_end = min(ev.fim, day_end)`), e `day_end` é `time.max` (23:59:59.999999), não o `00:00` do dia seguinte. Já o **novo** intervalo é somado **inteiro** ao dia de início (`new_duration = fim - inicio`, `:305`) e a capacidade do **dia seguinte nunca é avaliada**. Ou seja: um evento novo que atravessa a meia-noite carrega toda a sua duração para o primeiro dia e não consome capacidade do segundo. A spec descreve o código atual — não a regra pretendida.
- **RD-06 (timezone)** — armazenamento em UTC; comparações de "mesmo dia" e formatação em `America/Fortaleza` (`settings.TZ_PROJECT`). Datas naive recebidas são tratadas como UTC.
- **RD-07** — reporta **todos** os conflitos encontrados (sem short-circuit); `ok = (len(conflicts) == 0)`.
- **RD-08** — cada `Conflict` carrega `code`, `title`, `detail` (com formador/intervalo formatado) e `ref_id` quando aplicável.
- **Sem efeito colateral**: `check_conflicts` nunca grava nem aprova. Decisão de aprovação é externa.
- **Multi-formador**: considera eventos onde o usuário é `usuario` OU participante (`participations__usuario`). **Sem filtro de papel** (`availability_service.py:166-168`): participações `CONVIDADO` e `COORD_ACOMPANHA` contam como ocupação em RD-01/RD-04/RD-05. Isso é **assimétrico** em relação ao guard de enforcement, que exclui `CONVIDADO` de propósito (`solicitacao_availability.py:28-37,92`) — achado M08-07 / épico #1664. Consequência real: quem é apenas convidado de vários eventos no mesmo dia acumula capacidade diária como se fosse recurso alocado.
- **Idempotência/cache**: `check_conflicts` é cacheado por **300 s fixos** (`availability_service.py:326` passa `timeout=300` explícito ao decorator) com chave versionada por usuário; mudanças nos dados do usuário fazem `invalidate_availability_cache(usuario_id)` bumpar a versão (miss natural, sem scan de Redis). O **jitter ≤30 s** de `cache_utils._ttl_with_jitter()` só se aplica quando `timeout=None` — hoje isso vale apenas para a grade mensal (`views_availability_monthly.py:252`), **não** para o check de conflitos. O endpoint de lote não usa cache: chama `check_conflicts_uncached` (`views_availability.py:470`).
- **CP-03 (timezone Fortaleza)** e configuração via `config_service.get_cfg("availability", ...)` com fallback para `settings` — limites são **configuráveis**, não hardcoded.

## API / Interface

Todas montadas sob `/api/` (`config/urls.py` → `apps.core.urls`). Catálogo completo de payloads em [`GUIDE_AVAILABILITY.md`](../../GUIDE_AVAILABILITY.md) e `v2/docs/API_REFERENCE.md`.

| Método/rota | View | Permissão | Função |
|---|---|---|---|
| `GET /api/availability/check/` | `AvailabilityCheckView` | `HasPerm("view_all_availability") \| HasPerm("create_solicitation") \| HasPerm("approve_solicitation_batch")` + filtro runtime (próprio vs outros) | Check pontual de 1 usuário. Params: `usuario_id`, `inicio`, `fim` (ISO8601), `municipio_id?`. Resposta `{ok, conflicts[]}`. Throttle `availability_check` (60/min prod). |
| `POST /api/availability/check-many/` | `AvailabilityCheckManyView` | idem | Check em lote. Body `{usuarios_ids[], inicio, fim, municipio_id?}`. Resposta `{ok, results[]}`. |
| `GET /api/availability/monthly/` | `MonthlyAvailabilityView` | `[IsAuthenticated, CanViewAllAvailability \| HasSectorAccess]` (`views_availability_monthly.py:80`); superuser passa pelo bypass interno das policies, e o recorte fino por `EquipeGerencia` é feito em runtime (`allowed_user_ids`, `:185-215`) | Grade mensal por gerência/setor. Params `year`, `month`, `role` (FORMADOR/COORDENADOR), `gerencia_id?`, `sector?`, `q?`. Cache Redis 5 min (com jitter). |
| `GET/POST/PATCH/DELETE /api/availability-blocks/` | `AvailabilityBlockViewSet` | `IsAuthenticated` (escopo via queryset) | CRUD de bloqueios. Formador cria os próprios (auto `status="aprovado"`); delegação para outro Formador **no create** exige `user_can_delegate_availability_block` (+ AuditLog `DELEGATE_BLOCK_CREATE`). ⚠️ o **update não repete esse gate** — ver M08-01 abaixo. |

Idioma RBAC canônico: `permission_classes=[HasPerm("codename")]` (grupos diretos banidos por `scripts/rbac_lint.py`).

## Fluxos principais

**Check de conflito (`check_conflicts`)**

1. Valida intervalo (`fim > inicio`); inválido → `CheckResult(ok=False)` com `Conflict("X", "Intervalo inválido", ...)`.
2. Carrega `TRAVEL_BUFFER_MINUTES` e `AVAILABILITY_DAILY_LIMIT_HOURS` (config → fallback settings).
3. **RD-02/03**: bloqueios aprovados que intersectam → conflito T ou P por `tipo`.
4. **RD-01**: eventos aprovados que sobrepõem → conflito X (`distinct()` por causa do JOIN de participação).
5. **RD-04**: evento imediatamente anterior/posterior; se cidade distinta e gap `< buffer` → conflito D.
6. **RD-05**: soma durações do dia (range UTC do dia local) + novo intervalo; se `> limite` → conflito M.
7. **RD-07**: retorna `CheckResult(ok=len==0, conflicts=[...])`.

**Endpoint de check pontual** — valida `usuario_id`/datas (400 em entrada inválida; 404 se usuário não existe); 403 se consultar outro usuário sem `can_check_availability_for_others`; força timezone-aware (RD-06); chama o serviço; serializa conflitos via `c.__dict__`.

**Criação de bloqueio** — sem `usuario_id` (ou self): `usuario=created_by=request.user`, `status="aprovado"`. Com `usuario_id` de terceiro: 403 **antes** de qualquer lookup (anti-enumeração); depois valida target ativo + Função Formador (400 senão), salva e grava AuditLog.

**Edição de bloqueio (comportamento real, achado M08-01 / issue #1619)** — o `AvailabilityBlockViewSet` **não define** `update`/`partial_update`/`perform_update` (`views_availability.py:114,138` são os únicos overrides). Todo o gate de delegação vive em `perform_create` (`:162,170`). No serializer, `usuario_id` é campo gravável e **não** está em `read_only_fields` (`serializers/agenda.py:35,42,51`) — e `usuario_id` é o *attname* da FK. Consequência: `PATCH /api/availability-blocks/{id}/` com `{"usuario_id": <outro>}` **transfere o bloqueio já aprovado para outro usuário**, sem `user_can_delegate_availability_block`, sem validar "target é Formador ativo" e sem AuditLog. O `get_queryset` (`:122-123`) limita *qual* registro um não-privilegiado pode editar (só os próprios), não *para quem* ele é transferido — qualquer autenticado pode criar um bloqueio próprio e reatribuí-lo. `status` continua `aprovado` porque é read-only e já foi persistido.

## Decisões relacionadas (ADRs)

- [ADR-003 — Availability rules & timezone](../../../../docs/architecture/project-decisions/ADR-003-availability-rules-timezone.md) (UTC storage + America/Fortaleza).
- Regra de negócio canônica: [`docs/business-rules/regras-disponibilidade.md`](../../../../docs/business-rules/regras-disponibilidade.md) (indexada por [regras-disponibilidade.spec](../domain/regras-disponibilidade.spec.md)).
- ASQ-007 (#780): invalidação granular de cache por versionamento (sem `cache.keys` pattern delete).

## Testes que cobrem

- [`tests/test_availability_service.py`](../../../backend/apps/core/tests/test_availability_service.py) — RD-01..08: overlap total/parcial, adjacência permitida, T/P, buffer entre cidades, mesma cidade buffer-zero, capacidade M, timezone Fortaleza, fronteira de meia-noite, multi-formador, mensagens com código/intervalo; endpoint check (auth, validações, lote, permissão self-vs-privileged).
- [`tests/test_d9_availability_check.py`](../../../backend/apps/core/tests/test_d9_availability_check.py) — composição de permissão D9 (check de terceiros por Coord/Gerente Sup/Controle).
- [`tests/test_availability_batch.py`](../../../backend/apps/core/tests/test_availability_batch.py) — check-many.
- [`tests/test_api_availability_blocks.py`](../../../backend/apps/core/tests/test_api_availability_blocks.py), [`tests/test_availability_block_idor.py`](../../../backend/apps/core/tests/test_availability_block_idor.py), [`tests/test_availability_block_autoapproval.py`](../../../backend/apps/core/tests/test_availability_block_autoapproval.py), [`tests/test_pr13_delegated_availability_blocks.py`](../../../backend/apps/core/tests/test_pr13_delegated_availability_blocks.py) — CRUD de bloqueios, escopo IDOR, auto-aprovação, delegação.
- [`tests/test_availability_monthly_api.py`](../../../backend/apps/core/tests/test_availability_monthly_api.py), [`tests/test_availability_monthly_rbac.py`](../../../backend/apps/core/tests/test_availability_monthly_rbac.py) — grade mensal e RBAC por gerência.
- [`tests/test_cache_availability.py`](../../../backend/apps/core/tests/test_cache_availability.py) — cache versionado e invalidação.

## Pontos de atenção / dívidas conhecidas

- **`apps/core/views/availability.py` é shim, não cópia**: reexporta `views_availability` (`views/availability.py:15-19`); manter assim ou remover, mas não reimplementar ali.
- **TOCTOU**: o check é consultivo e cacheado (300 s); entre o check e a gravação da solicitação o estado pode mudar (novo evento/bloqueio concorrente). A garantia real de não-conflito é o guard `enforce_solicitacao_availability` (`services/solicitacao_availability.py`, #1452), que revalida sob advisory lock por participante em create/update/approve/batch-approve — não este serviço.
- **Gaps abertos do motor de regra** (épico #1664, `ACHADOS_REAIS.md`): M08-07 (ocupação sem filtro de papel, assimétrica com `ENFORCED_ROLES`) e M08-09 (janela diária derivada só do dia de início). Ambos estão descritos como comportamento **real** nas seções acima — não corrigir a spec escrevendo a regra pretendida.
- **Bloqueio transferível por PATCH** (M08-01 / #1619): ver §Fluxos. Enquanto não houver `perform_update` com gate, tratar `usuario_id` como campo sensível em qualquer refactor do serializer.
- **`municipio=None` = cidade diferente** (RD-04): chamadas sem `municipio_id` disparam buffer; intencional (fix #588), mas pode gerar conflito D inesperado quando o município simplesmente não foi informado.
- **Permissão por composition OR** nos endpoints de check (3 caps) é tática; se a matriz crescer, migrar para Policy class (ver `feedback_composition_or_is_tactical`).
- **Grade mensal**: legenda/células dependem de `monthly_grid_service`; este spec cobre o contrato HTTP, não o algoritmo da grade (ver `GUIDE_AVAILABILITY.md`).
- Throttle dev relaxado (`600/min`) vs prod (`60/min`) — não confundir limites em testes locais.

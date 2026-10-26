---
title: Disponibilidade (serviço)
status: canonical
last_verified: 2026-10-26
verified_at_commit: 804df36a1741d1faa53586eafade5c4c74c0659d
sources_of_truth:
  - v2/backend/apps/core/services/availability_service.py
  - v2/backend/apps/core/services/solicitacao_availability.py
  - v2/backend/apps/core/views_availability.py
  - v2/backend/apps/core/views_availability_monthly.py
  - v2/backend/apps/core/services/horas_formacao.py
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

O módulo de disponibilidade calcula, de forma **consultiva**, se um formador/coordenador pode atender um novo evento num intervalo `(inicio, fim)`, aplicando as regras RD-01 a RD-08 (não-sobreposição, bloqueios total/parcial, buffer de deslocamento entre municípios e timezone-aware; a capacidade diária saiu em 05/10/2026). É a implementação de software das regras de negócio de agenda: substitui a planilha manual em que a Superintendência conferia conflitos à mão.

O coração é um **serviço puro, sem efeitos colaterais** (`check_conflicts`): não grava, não aprova e não muda estado — apenas retorna uma lista estruturada de conflitos. Quem transforma o cálculo em **bloqueio** é o guard `services/solicitacao_availability.py` (`enforce_solicitacao_availability`, #1452), chamado nos call-sites que gravam/aprovam evento (ver [solicitacao-approval.spec](./solicitacao-approval.spec.md)). Sobre o serviço existem três superfícies HTTP: check pontual, check em lote e a grade mensal usada pela UI da Superintendência.

## Fonte de verdade no código

- [`services/availability_service.py`](../../../backend/apps/core/services/availability_service.py) — `check_conflicts(*, usuario, inicio, fim, municipio=None) -> CheckResult` (variante cacheada) e `check_conflicts_uncached` (mesma assinatura, sem cache, usada pelo check em lote e por todo o enforcement transacional); ambas delegam a `_check_conflicts_impl`, que aceita `exclude_solicitacao_id`. Dataclasses `Conflict` (code/title/detail/ref_id) e `CheckResult` (ok/conflicts); helpers `to_local`, `same_day_local`, `_fmt_interval_local`. **SSOT das RD-01 a RD-08.**
- [`services/solicitacao_availability.py`](../../../backend/apps/core/services/solicitacao_availability.py) — guard de enforcement (#1452): `enforce_solicitacao_availability(solicitacao, *, action)` decide **quem** é checado (decisão do dono, 05/10/2026: todos os FORMADORES — `ENFORCED_ROLES` = FORMADOR — e o coordenador responsável só com `coordenador_acompanha=True`, via `coordenador_ocupante`; quem cria não entra por ter criado; COORDENADOR, COORD_ACOMPANHA e CONVIDADO não ocupam), toma advisory lock por participante e traduz conflito em `ValidationAPIError`. Chamado em create/update (`perform_create`/`perform_update` em `views_solicitacao.py`) e em approve/batch-approve (`approve_solicitacao`/`batch_approve_solicitacoes` em `solicitacao_approval.py`).
- [`views_availability.py`](../../../backend/apps/core/views_availability.py) (raiz de `apps/core/` — **arquivo ativo**) — `AvailabilityBlockViewSet`, `AvailabilityCheckView`, `AvailabilityCheckManyView` + helpers `is_privileged_user`, `can_check_availability_for_others`. Os bloqueios dos colegas seguem `EquipeGerencia.gerencias_de_atuacao` (PR 9).
- [`views_availability_monthly.py`](../../../backend/apps/core/views_availability_monthly.py) — `MonthlyAvailabilityView` (grade mensal; delega para `services/monthly_grid_service.build_monthly_grid`).
- [`models/agenda.py`](../../../backend/apps/core/models/agenda.py) — `AvailabilityBlock` (`tipo` T/P, `status` aprovado, `inicio`/`fim` UTC; check constraints `fim>inicio` e `tipo in {T,P}`).
- [`utils/cache_utils.py`](../../../backend/apps/core/utils/cache_utils.py) — decorator `cache_availability_check` + `invalidate_availability_cache` (versionamento no Redis: a versão por usuário, `avail_ver:<id>`, vale para o cache dos checks de conflito; a grade mensal usa a versão global `monthly_ver:__global__`, que toda invalidação sobe).
- [`urls.py`](../../../backend/apps/core/urls.py) — registro das rotas sob `/api/`.
- Guia detalhado (grade multi-setor, permissões, exemplos de payload): [`GUIDE_AVAILABILITY.md`](../../GUIDE_AVAILABILITY.md).

> Nota: `apps/core/views/availability.py` **não** é roteado — `urls.py` importa de `views_availability` (raiz, `urls.py`). Desde a correção do drift ele é apenas um **shim de compatibilidade**, que reexporta as views ativas (`views/availability.py`); não há mais cópia divergente do código.

## Contratos e invariantes

- **RD-01 (X)** — sobreposição com evento aprovado: overlap `inicio__lt=fim & fim__gt=inicio` ≥ 1 min gera conflito; intervalos **adjacentes** (`fim == inicio`) **não** conflitam.
- **RD-02 (T)** — bloqueio total aprovado que intersecta o intervalo impede qualquer evento.
- **RD-03 (P)** — bloqueio parcial aprovado impede só dentro do subintervalo.
- **RD-04 (D)** — buffer de deslocamento entre municípios distintos: exige `>= TRAVEL_BUFFER_MINUTES` (default 120). `municipio=None` é tratado como **cidade diferente** (fix #588) → exige buffer. Buffer **exato** (`== buffer`) passa; só `< buffer` conflita.
- **RD-05** — **não é mais checagem de agenda** (decisão do dono, 05/10/2026, OK explícito para mudar RD-05/CP-03; de 02/10 a 05/10 foi aviso M em `warnings`, antes barrava). O motor não soma horas do dia nem emite `M` em nenhum caminho; o bloco RD-05 e `_clip_minutes` saíram de `_check_conflicts_impl`. `AVAILABILITY_DAILY_LIMIT_HOURS` virou o **teto por evento da contagem de horas de formação**: [`services/horas_formacao.py`](../../../backend/apps/core/services/horas_formacao.py) (`horas_formacao(usuario_ids, *, de, ate)`), CH de um evento = `min(fim − início, teto)`, somada no dia local do início, sem teto por dia; só aprovado, qualquer projeto; FORMADOR sempre, responsável só com `coordenador_acompanha=True`. Regra completa em [regras-disponibilidade.spec](../domain/regras-disponibilidade.spec.md).
- **RD-06 (timezone)** — armazenamento em UTC; comparações de "mesmo dia" e formatação em `America/Fortaleza` (`settings.TZ_PROJECT`). Datas naive recebidas são tratadas como UTC.
- **RD-07** — reporta **tudo** o que encontra (sem short-circuit): `conflicts` (X, T, P, D) barra; `ok = (len(conflicts) == 0)`. `CheckResult.warnings` fica só para a checagem prévia (`check/` e `check-many/`, que o assistente lê) e vem sempre vazio desde 05/10/2026 (era o M).
- **Contrato do guard** (`solicitacao_availability.py`): `ParticipantConflicts` (`usuario_id`, `usuario_nome`, `conflicts`) e `GuardResult` (`ok`, `blocked`, `skipped_guests`, `checked_usuario_ids`). `GuardResult.ok` só olha `conflicts`. O 400 `availability_conflict` traz `errors.conflicts`, `errors.blocked_participants[]` e `errors.skipped_guests`; a mensagem só fala do que barra, e `_MOTIVO_TEXTO` não tem entrada `M`. Os `warnings` do guard, do 400 e o log `availability_warning` (criados em 02/10/2026 para o aviso M) saíram em 06/10/2026: sem o M, nada os produzia e nenhum cliente os lia.
- **RD-08** — cada `Conflict` carrega `code`, `title`, `detail` (com formador/intervalo formatado) e `ref_id` quando aplicável.
- **Sem efeito colateral**: `check_conflicts` nunca grava nem aprova. Decisão de aprovação é externa.
- **Quem um evento existente ocupa** (decisão do dono, 05/10/2026; SSOT `ocupa_agenda_q` em `availability_service.py`): a pessoa é FORMADORA no evento (`participations__role__in=ENFORCED_ROLES`, só FORMADOR), **ou** é a coordenadora responsável (`coordenador`; sem FK, quem criou) e o evento tem `coordenador_acompanha=True`. Ser quem criou não ocupa mais (antes `Q(usuario=usuario)` ocupava sempre), nem os papéis COORDENADOR/COORD_ACOMPANHA. `CONVIDADO` segue fora (achado M08-07, PR #1794). O predicado é **único**: `ocupa_agenda_q` (evento existente) e `coordenador_ocupante` (evento novo) vivem lado a lado e o guard importa os dois, então criar, editar, aprovar, lote, `check`/`check-many` e o importador de eventos usam a mesma regra.
- **Idempotência/cache**: `check_conflicts` é cacheado por **300 s fixos** (`availability_service.py` passa `timeout=300` explícito ao decorator) com chave versionada por usuário e prefixo `availability_check:v2:` (o `v2` entrou em 02/10/2026 junto com `CheckResult.warnings`, para não servir objeto guardado antes do deploy, sem o campo; `test_cache_availability.py::test_resultado_guardado_na_chave_antiga_nao_e_lido`); mudanças nos dados do usuário fazem `invalidate_availability_cache(usuario_id)` bumpar a versão (miss natural, sem scan de Redis). A chave leva também os parâmetros vigentes (`parametros_disponibilidade()`: Buffer e teto de horas), então salvar Configurações já vale na consulta seguinte, sem esperar os 300 s (auditoria UX 30/09, rodada 4; `test_config_api.py::test_config_buffer_salvo_vale_ja_na_checagem_consultiva_com_cache`). O **jitter ≤30 s** de `cache_utils._ttl_with_jitter()` só se aplica quando `timeout=None` — hoje isso vale apenas para a grade mensal (`MonthlyAvailabilityView`), **não** para o check de conflitos. O endpoint de lote não usa cache: chama `check_conflicts_uncached` (`AvailabilityCheckManyView`).
- **CP-03 (timezone Fortaleza)** e configuração via `config_service.get_cfg("availability", ...)` com fallback para `settings` — limites são **configuráveis**, não hardcoded.

## API / Interface

Todas montadas sob `/api/` (`config/urls.py` → `apps.core.urls`). Catálogo completo de payloads em [`GUIDE_AVAILABILITY.md`](../../GUIDE_AVAILABILITY.md) e `v2/docs/API_REFERENCE.md`.

| Método/rota | View | Permissão | Função |
|---|---|---|---|
| `GET /api/availability/check/` | `AvailabilityCheckView` | `HasPerm("view_all_availability") \| HasPerm("create_solicitation") \| HasPerm("approve_solicitation")` + escopo do alvo (`_alvos_no_escopo`, F4 do scan de 16/10/2026) | Check pontual de 1 usuário. **Escopo (F4)**: global (`user_is_solicitacao_global`: superusuário, Superintendência, Controle, DAT) ou `view_all_availability` consulta qualquer pessoa; os demais (G/C/A pelo papel) só a si e quem tem vínculo vigente ≠ EQUIPE nas gerências onde têm papel G/C/A (`scope_usuarios_por_gerencia`, o filtro do seletor de pessoas do assistente). Fora disso, `404 Usuário não encontrado`, igual a id inexistente (mesma regra P9-1 do `/availability-blocks/`). Params: `usuario_id`, `inicio`, `fim` (ISO8601), `municipio_id?`. Resposta `{ok, conflicts[], warnings[]}` (`warnings` sempre vazio desde 05/10/2026; não muda `ok`). Throttle `availability_check` (60/min prod). |
| `POST /api/availability/check-many/` | `AvailabilityCheckManyView` | idem | Check em lote. Body `{usuarios_ids[], inicio, fim, municipio_id?}`. `usuarios_ids` (F3): até **50** inteiros positivos, contados antes de tirar a repetição; acima disso ou com item de outro tipo, `400`; id repetido dá um resultado só; as contas vêm num `in_bulk`. Pessoa fora do escopo (F4) volta como id inexistente: `ok=false` com o conflito `X` "Usuário não encontrado". O assistente manda só quem o `/lookup/usuarios/` ofereceu, então não esbarra no escopo. Resposta `{ok, results[]}`; cada item traz `{usuario_id, ok, conflicts[], warnings[]}`. |
| `GET /api/availability/monthly/` | `MonthlyAvailabilityView` | `[IsAuthenticated, CanViewAllAvailability \| HasSectorAccess]` (`MonthlyAvailabilityView`); superuser passa pelo bypass interno das policies, e o recorte fino por `EquipeGerencia` é feito em runtime (`allowed_user_ids`) | Grade mensal por gerência/setor. Params `year`, `month`, `role` (FORMADOR/COORDENADOR), `gerencia_id?`, `sector?` (casa `projeto__nome` exato; na tela é o campo "Projeto"), `q?` (casa o nome; o e-mail só quando o termo não tem dígito, porque pode levar o CPF; termo com mais de uma palavra, como "Ana Silva", casa também quando cada palavra está no nome ou no sobrenome da pessoa, sem olhar o e-mail: `busca_por_nome` em `pii.py`, item 38). Em `people[]`, conta sem nome sai como `Usuario #id` e o `email` vem `null` quando é o de reserva (`<cpf>@placeholder.local`) ou leva CPF (S5). Sem `gerencia_id`, a grade traz os **participantes de projetos SUPER** — é esse o rótulo da opção na `FiltersBar` (decisão 3 do dono, PR A de 2026-09-29). A `FiltersBar` oferece essa opção e as gerências ativas **só** a quem tem a policy `view_all_availability` (mesma SSOT do `CanViewAllAvailability`); os demais escolhem entre `GET /api/me/.gerencias` (vínculo `EquipeGerencia` vigente, gerência ativa), que é o que o `HasSectorAccess` aceita — grupo de setor não conta. Na aba Coordenadores (`role=COORDENADOR`) a célula do dia conta os eventos que ocupam a agenda pela regra do motor de conflito (`ocupa_agenda_q`: formador, ou responsável com `coordenador_acompanha=True`); o responsável que não acompanha fica sem E/2 naquele dia (item 38, 20/10/2026; `test_horas_formacao.py::test_aba_coordenadores_so_marca_o_dia_de_quem_acompanha`). `ch_month`/`ch_year` (e o ranking) vêm de `horas_formacao` (teto por evento, dia do início; as duas abas; não seguem o filtro `sector`). Cache Redis 5 min (com jitter); a chave (`chave_cache_grade`, `monthly:v9:` + sha256 do JSON de ano, mês, papel, escopo, setor, busca e teto; F8; o `v9` entrou com a regra da aba Coordenadores, para não servir a grade velha) leva o teto vigente, então salvar o teto vale na consulta seguinte. A versão da chave (`get_monthly_cache_version()`, `monthly_ver:__global__`) é uma só para todos que olham: bloqueio, evento ou participação de qualquer pessoa sobe a versão e a grade de todos refaz na consulta seguinte (item 38, 26/10/2026; antes a chave levava a versão de quem olha e a mudança subia só a do dono, e a agenda de outra pessoa ficava velha por até ~5 min). Setor ausente é `null` e não colide com `sector=*`; `:` no setor ou na busca não desloca os campos. |
| `GET/POST/PATCH/DELETE /api/availability-blocks/` | `AvailabilityBlockViewSet` | `IsAuthenticated` (escopo via queryset: `view_all_availability` vê tudo; GERENTE/COORDENADOR/APOIO veem os das pessoas das gerências onde têm o papel; a formadora só os próprios — PR 9, P9-1) | CRUD de bloqueios. Formador cria os próprios (auto `status="aprovado"`); delegação para outro Formador **no create** exige `user_can_delegate_availability_block` (+ AuditLog `DELEGATE_BLOCK_CREATE`). Editar ou apagar bloqueio de outra pessoa exige o mesmo `user_can_delegate_availability_block` (`_assert_can_mutate`, GAP-1), com AuditLog `DELEGATE_BLOCK_UPDATE`/`DELEGATE_BLOCK_DELETE`; a edição nunca troca o dono (M08-01, ver §Fluxos). |

Idioma RBAC canônico: `permission_classes=[HasPerm("codename")]` (grupos diretos banidos por `scripts/rbac_lint.py`).

## Fluxos principais

**Check de conflito (`check_conflicts`)**

1. Valida intervalo (`fim > inicio`); inválido → `CheckResult(ok=False)` com `Conflict("X", "Intervalo inválido", ...)`.
2. Carrega `TRAVEL_BUFFER_MINUTES` por `parametros_disponibilidade()` (`config_service.py`): vale a chave gravada no Config `availability` (inclusive Buffer 0); sem ela, o settings (env). A tela de Configurações (`GET /api/config/`) mostra pela mesma função, então o valor exibido é o aplicado (auditoria UX 30/09; antes a tela completava com 120/8 fixos e o motor ignorava o Buffer 0 por causa de `or`). Travado em `test_config_api.py::test_config_buffer_exibido_e_o_aplicado_no_rd04`.
3. **RD-02/03**: bloqueios aprovados que intersectam → conflito T ou P por `tipo`.
4. **RD-01**: eventos aprovados que sobrepõem → conflito X (`distinct()` por causa do JOIN de participação).
5. **RD-04**: evento imediatamente anterior/posterior; se cidade distinta e gap `< buffer` → conflito D.
6. (**RD-05** não roda aqui desde 05/10/2026: é o teto da contagem de horas.)
7. **RD-07**: retorna `CheckResult(ok=len(conflicts)==0, conflicts=[...], warnings=[...])`.

**Endpoint de check pontual** — valida `usuario_id`/datas (400 em entrada inválida; 404 se usuário não existe); 403 se consultar outro usuário sem `can_check_availability_for_others`; força timezone-aware (RD-06); chama o serviço; serializa conflitos e avisos via `__dict__` (`conflicts` e `warnings`).

**Criação de bloqueio** — sem `usuario_id` (ou self): `usuario=created_by=request.user`, `status="aprovado"`. Com `usuario_id` de terceiro: 403 **antes** de qualquer lookup (anti-enumeração); depois valida target ativo + papel FORMADOR vigente (`EquipeGerencia.gerencias_com_papel`, desde o PR 8; o grupo Formador sozinho não basta) (400 senão), salva e grava AuditLog.

**Edição de bloqueio (achado M08-01 / issue #1619, corrigido em `c2ff044f`)** — a titularidade é **imutável** na edição: `AvailabilityBlockViewSet.perform_update` tira `usuario_id` do payload e responde 403 se a edição tentar mudar o dono (a concessão de titularidade só existe no create delegado, `perform_create`). Antes de salvar, `_assert_can_mutate` exige `user_can_delegate_availability_block` para editar bloqueio de outra pessoa (GAP-1, 403 senão) e a edição delegada grava AuditLog `DELEGATE_BLOCK_UPDATE`; o próprio bloqueio segue livre. `perform_destroy` usa o mesmo gate, com AuditLog `DELEGATE_BLOCK_DELETE`. SSOT: `views_availability.py`.

## Decisões relacionadas (ADRs)

- [ADR-003 — Availability rules & timezone](../../../../docs/architecture/project-decisions/ADR-003-availability-rules-timezone.md) (UTC storage + America/Fortaleza).
- Regra de negócio canônica: [`docs/business-rules/regras-disponibilidade.md`](../../../../docs/business-rules/regras-disponibilidade.md) (indexada por [regras-disponibilidade.spec](../domain/regras-disponibilidade.spec.md)).
- ASQ-007 (#780): invalidação granular de cache por versionamento (sem `cache.keys` pattern delete).

## Testes que cobrem

- [`tests/test_availability_service.py`](../../../backend/apps/core/tests/test_availability_service.py) — RD-01..08: overlap total/parcial, adjacência permitida, T/P, buffer entre cidades, mesma cidade buffer-zero, dia acima de 8 h sem M, timezone Fortaleza, fronteira de meia-noite, multi-formador, mensagens com código/intervalo; endpoint check (auth, validações, lote, permissão self-vs-privileged).
- [`tests/test_availability_sem_aviso_m.py`](../../../backend/apps/core/tests/test_availability_sem_aviso_m.py) — decisão de 05/10/2026: nenhum caminho devolve M (motor, criar, editar, aprovar, lote, `check/`, `check-many/`, 400 por outro motivo); guarda de que X, T, P e D continuam barrando nos quatro pontos.
- [`tests/test_horas_formacao.py`](../../../backend/apps/core/tests/test_horas_formacao.py) — contagem de horas com teto por evento; Grade Mensal e painel de Equipe dão o mesmo número; cache da grade acompanha o teto.
- [`tests/test_d9_availability_check.py`](../../../backend/apps/core/tests/test_d9_availability_check.py) — composição de permissão D9 (check de terceiros por Coord/Gerente Sup/Controle).
- [`tests/test_availability_batch.py`](../../../backend/apps/core/tests/test_availability_batch.py) — check-many.
- [`tests/test_seguranca_availability_check_many.py`](../../../backend/apps/core/tests/test_seguranca_availability_check_many.py) — F3: teto de 50 ids, item inteiro positivo, repetição e uma consulta para as contas.
- [`tests/test_rbac_escopo_por_papel.py`](../../../backend/apps/core/tests/test_rbac_escopo_por_papel.py) (`TestChecagemDeDisponibilidadeF4`) — F4: escopo por gerência no `/check/` e no `/check-many/`.
- [`tests/test_api_availability_blocks.py`](../../../backend/apps/core/tests/test_api_availability_blocks.py), [`tests/test_availability_block_idor.py`](../../../backend/apps/core/tests/test_availability_block_idor.py), [`tests/test_availability_block_autoapproval.py`](../../../backend/apps/core/tests/test_availability_block_autoapproval.py), [`tests/test_pr13_delegated_availability_blocks.py`](../../../backend/apps/core/tests/test_pr13_delegated_availability_blocks.py) — CRUD de bloqueios, escopo IDOR, auto-aprovação, delegação.
- [`tests/test_availability_monthly_api.py`](../../../backend/apps/core/tests/test_availability_monthly_api.py), [`tests/test_availability_monthly_rbac.py`](../../../backend/apps/core/tests/test_availability_monthly_rbac.py) — grade mensal e RBAC por gerência.
- [`tests/test_cache_availability.py`](../../../backend/apps/core/tests/test_cache_availability.py) — cache versionado e invalidação.

## Pontos de atenção / dívidas conhecidas

- **`apps/core/views/availability.py` é shim, não cópia**: reexporta `views_availability` (`views/availability.py`); manter assim ou remover, mas não reimplementar ali.
- **TOCTOU**: o check é consultivo e cacheado (300 s); entre o check e a gravação da solicitação o estado pode mudar (novo evento/bloqueio concorrente). A garantia real de não-conflito é o guard `enforce_solicitacao_availability` (`services/solicitacao_availability.py`, #1452), que revalida sob advisory lock por participante em create/update/approve/batch-approve — não este serviço.
- **Motor de regra — achados M08-07 e M08-09 corrigidos** (épico #1664, `ACHADOS_REAIS.md`): M08-07 (ocupação sem filtro de papel) foi resolvido na PR #1794 (commit `74e6cc34`) — a query de eventos existentes agora filtra por `ENFORCED_ROLES`; M08-09 (janela diária derivada só do dia de início) foi resolvido na PR #1796 (commit `b0529225`) — a capacidade passou a ser avaliada por dia local (e, desde 05/10/2026, o RD-05 saiu do motor). M08-07 está descrito em §Contratos e invariantes. O épico #1664 segue **aberto** (a decisão de fechá-lo é do dono); estes dois achados de código já não descrevem defeito.
- **Bloqueio transferível por PATCH** (M08-01 / #1619): **corrigido** em `c2ff044f` (`perform_update` torna o dono imutável; ver §Fluxos). `usuario_id` segue gravável no serializer por causa do create delegado, então qualquer refactor do serializer ou do `perform_update` precisa manter a troca de dono bloqueada.
- **`municipio=None` = cidade diferente** (RD-04): chamadas sem `municipio_id` disparam buffer; intencional (fix #588), mas pode gerar conflito D inesperado quando o município simplesmente não foi informado.
- **Permissão por composition OR** nos endpoints de check (3 caps) é tática; se a matriz crescer, migrar para Policy class (ver `feedback_composition_or_is_tactical`).
- **Grade mensal**: legenda/células dependem de `monthly_grid_service`; este spec cobre o contrato HTTP, não o algoritmo da grade (ver `GUIDE_AVAILABILITY.md`).
- Throttle dev relaxado (`600/min`) vs prod (`60/min`) — não confundir limites em testes locais.

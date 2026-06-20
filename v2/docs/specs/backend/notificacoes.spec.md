---
title: Notificações (32 Passos)
status: canonical
last_verified: 2026-06-19
sources_of_truth:
  - v2/backend/apps/core/models/acoes_notificacao.py
  - v2/backend/apps/core/services/prazo_engine_service.py
  - v2/backend/apps/core/services/notificacoes_acoes_service.py
  - v2/backend/apps/core/services/business_calendar_service.py
  - v2/backend/apps/core/services/acoes_notificacao_seed.py
  - v2/backend/apps/core/management/commands/seed_acoes_notificacao.py
  - v2/backend/apps/core/views/acoes_notificacao.py
  - v2/backend/apps/core/serializers/acoes_notificacao.py
  - v2/backend/apps/core/urls.py
  - v2/backend/apps/core/tasks.py
  - v2/backend/config/celery.py
  - v2/backend/apps/core/rbac/matrix.py
  - v2/backend/apps/core/migrations/0060_seed_acoes_notificacao_templates.py
  - v2/backend/apps/core/migrations/0079_add_manage_internal_actions.py
owner: backend
supersedes:
  - v2/docs/_archive/PLANO_NOTIFICACOES_TIMING.md
related:
  - ../INDEX_SDD.md
  - ./README.md
  - ./rbac.spec.md
  - ../../RBAC_NAMING.md
---

# Notificações (32 Passos)

## Propósito

O módulo de "Ações Internas / Notificações" (codinome **32 Passos**) modela o ciclo operacional de 32 ações que cada par **Projeto × Município** percorre em um semestre — da entrega de materiais ao último feedback da equipe técnica. Para cada ação há uma regra de prazo em **dias úteis** ancorada num evento (entrega, formação, marco de calendário, ou conclusão da ação anterior). Um processador diário avalia os prazos e gera **notificações in-app** em cascata hierárquica (responsável → coordenador → gerente → DAT), com lembretes pré-vencimento e escalonamento pós-vencimento.

O objetivo é substituir o acompanhamento manual de prazos por uma régua determinística de cobrança: cada ação tem âncora, vencimento calculado sobre o calendário útil de Fortaleza/CE/Brasil, e estado operacional (`AGUARDANDO_ANCORA` → `EM_ANDAMENTO`/`ATRASADA` → `CONCLUIDA`). A feature está **em desenvolvimento** (CRUD de ciclos/ações é superuser-only por enquanto); a inbox de notificações já é exposta a qualquer usuário autenticado.

> ⚠️ NÃO confundir com o plano arquivado [`PLANO_NOTIFICACOES_TIMING.md`](../../_archive/PLANO_NOTIFICACOES_TIMING.md), que propunha os models `EtapaProjeto`/`CicloFormacao`/`Notification` — **nunca implementados**. O sistema vivo usa `AcaoTemplate`/`CicloAcoes`/`AcaoInstancia`/`NotificacaoInterna`.

## Fonte de verdade no código

- **Models** — [`apps/core/models/acoes_notificacao.py`](../../../backend/apps/core/models/acoes_notificacao.py): `AcaoTemplate`, `AcaoTemplateExecutor`, `CicloAcoes`, `AcaoInstancia`, `RegistroAncora`, `RegistroConclusaoAcao`, `FeriadoLocal`, `NotificacaoInterna` + enums (`TipoAncoraChoices`, `SemestreChoices`, `EstadoAcaoChoices`, `TipoNotificacaoChoices`, `NivelNotificacaoChoices`, `PrioridadeNotificacaoChoices`).
- **Engine de prazo** — [`services/prazo_engine_service.py`](../../../backend/apps/core/services/prazo_engine_service.py) (`PrazoEngineService`): resolve âncora, calcula vencimento e estado, e propaga recálculo a dependentes.
- **Calendário útil** — [`services/business_calendar_service.py`](../../../backend/apps/core/services/business_calendar_service.py) (`BusinessCalendarService`): feriados nacionais/CE/Fortaleza (móveis via Páscoa) + `FeriadoLocal` do DB; `add_business_days`, `business_days_between`.
- **Processador / escalonamento** — [`services/notificacoes_acoes_service.py`](../../../backend/apps/core/services/notificacoes_acoes_service.py): `EscalonamentoService` (régua D-7…D+3), `NotificationService` (resolução de destinatários + dedup), `AcoesNotificacaoDailyService.run()`.
- **Seed dos 32 templates** — [`services/acoes_notificacao_seed.py`](../../../backend/apps/core/services/acoes_notificacao_seed.py) + comando [`management/commands/seed_acoes_notificacao.py`](../../../backend/apps/core/management/commands/seed_acoes_notificacao.py) + migration de dados [`0060_seed_acoes_notificacao_templates.py`](../../../backend/apps/core/migrations/0060_seed_acoes_notificacao_templates.py).
- **API** — [`views/acoes_notificacao.py`](../../../backend/apps/core/views/acoes_notificacao.py) + [`serializers/acoes_notificacao.py`](../../../backend/apps/core/serializers/acoes_notificacao.py) + rotas em [`urls.py`](../../../backend/apps/core/urls.py).
- **Agendamento** — task [`apps/core/tasks.py::processar_notificacoes_acoes_diarias`](../../../backend/apps/core/tasks.py) + Celery beat em [`config/celery.py`](../../../backend/config/celery.py).
- **RBAC** — capability `manage_internal_actions` (key de matriz `ciclos_acoes`) em [`rbac/matrix.py`](../../../backend/apps/core/rbac/matrix.py) + migration [`0079_add_manage_internal_actions.py`](../../../backend/apps/core/migrations/0079_add_manage_internal_actions.py).

## Contratos e invariantes

- **32 ações exatas**: o seed valida `ordens == 1..32` sem gaps; cada ação tem ≥1 grupo executor. Templates são idempotentes (`update_or_create` por `ordem`).
- **Âncoras (`TipoAncoraChoices`)**: `EVENTO_EXTERNO` exige `ref_evento_externo` não-vazio (data manual via `data_ancora`); `ACAO_ANTERIOR` exige `ref_acao_template` (âncora = `data_realizacao` da ação referenciada no mesmo ciclo); `MARCO_CALENDARIO` ancora no início do semestre (`1S` → 01/03, `2S` → 01/08). CheckConstraints no DB reforçam `ancora_acao_requer_ref` e `ancora_evento_requer_ref`.
- **Prazo em dias úteis**: vencimento = `add_business_days(âncora, dias_prazo_uteis)`. `dias_prazo_uteis > 0` (CheckConstraint). Calendário útil = fins de semana + feriados nacionais/CE/Fortaleza + `FeriadoLocal` ativos. Timezone do projeto: **America/Fortaleza**.
- **Unicidade de ciclo**: um único `CicloAcoes` por `(projeto, municipio, semestre, ano)`; `ano >= 2020`. Ao criar o ciclo, gera-se uma `AcaoInstancia` por template ativo (`unique (ciclo, ordem)` e `unique (ciclo, template)`); `instancia.ordem == template.ordem` (validado em `clean()`).
- **Conclusão irreversível (MVP)**: `concluir()` exige `observacao` não-vazia e `data_realizacao` (CheckConstraints `concluida_requer_observacao`/`concluida_requer_data_realizacao`); cria `RegistroConclusaoAcao` (OneToOne) — **reabertura não permitida**. Concluir dispara `recalculate_dependents` (recálculo das ações que ancoram nesta, com proteção contra ciclo via `visited`). Não é permitido registrar/alterar âncora de ação já concluída.
- **Idempotência de notificação**: `NotificacaoInterna` tem `unique (destinatario, acao_instancia, fase_disparo, referencia_data)`; o `get_or_create` + tratamento de `IntegrityError` garantem que rodar o processador N vezes no mesmo dia não duplica (contabilizado como `deduplicated`). O processador ignora ações `CONCLUIDA` e ciclos não `EM_ANDAMENTO`.
- **Acesso (CP-02/RBAC)**: ciclos e ações exigem `permission_classes = [HasPerm("manage_internal_actions")]`. No seed essa capability **não recebe grupos** → na prática **somente superuser** passa (matriz `ciclos_acoes`: SUPERUSER=ALLOW, todos os demais DENY). A inbox (`NotificacaoInterna`) é `IsAuthenticated` e escopada ao `destinatario == request.user` (cada um só vê o próprio inbox).

## API / Interface

Rotas DRF (router em [`urls.py`](../../../backend/apps/core/urls.py); prefixo `/api/`):

- `ciclos-acoes/` — `CicloAcoesViewSet` (CRUD; cria as 32 instâncias no `create`). Action extra `GET ciclos-acoes/{id}/acoes/`. Filtros: `projeto, municipio, semestre, ano, status`.
- `acoes-instancia/` — `AcaoInstanciaViewSet` (read-only) + comandos `POST acoes-instancia/{id}/registrar-ancora/` (`data_ancora`, `observacao?`; usa `select_for_update`) e `POST acoes-instancia/{id}/concluir/` (`data_realizacao`, `observacao` obrigatória).
- `notificacoes-internas/` — `NotificacaoInternaViewSet` (read-only, inbox do usuário) + `POST {id}/marcar-lida/`, `GET unread-count/`, `POST marcar-todas-lidas/`. Filtros: `lida, tipo, nivel, fase_disparo, referencia_data`.

Operações administrativas:

- `python manage.py seed_acoes_notificacao [--verbose]` — semeia/atualiza os 32 templates + executores (idempotente).
- Task Celery `apps.core.tasks.processar_notificacoes_acoes_diarias(reference_date_iso?)` — beat diário às **08:00** (`config/celery.py`, key `acoes-notificacoes-diarias`). Retorna métricas (`actions_evaluated/triggered`, `notifications_created/deduplicated`, `fallback_actions`, `phases`) e grava `AuditLog` (`ACOES_NOTIFICACOES_DAILY`).

Toda mutação relevante grava `AuditLog`: `CICLO_ACOES_CREATE`, `ACAO_REGISTRAR_ANCORA`, `ACAO_CONCLUIR`.

## Fluxos principais

1. **Provisionamento**: `seed_acoes_notificacao` cria os 32 `AcaoTemplate` + grupos executores (ação 1 → Logística Galpão; ação 2 → Comercial/Relacionamento/DAT; ações 3–32 → Coordenador/Gerente).
2. **Abertura de ciclo**: `POST ciclos-acoes/` → cria `CicloAcoes` + 32 `AcaoInstancia` (`AGUARDANDO_ANCORA`).
3. **Registro de âncora**: `POST .../registrar-ancora/` → `PrazoEngineService.recalculate_action` resolve âncora, calcula `data_vencimento` em dias úteis e move o estado para `EM_ANDAMENTO`/`ATRASADA`. Grava `RegistroAncora` (histórico).
4. **Processamento diário** (`AcoesNotificacaoDailyService.run`): para cada ação de ciclo `EM_ANDAMENTO` com vencimento e não concluída → recalcula estado → `EscalonamentoService.resolve_rule` mapeia a distância em dias úteis até o vencimento para uma fase (**D-7** lembrete/responsável, **D-3**/**D-1** alta, **D0** vencimento/crítica, **D+1** escala p/ coordenador, **D+3** escala p/ gerente) → `NotificationService.dispatch_for_action` resolve destinatários (executores ∩ papel do nível) e cria notificações dedup.
5. **Conclusão**: `POST .../concluir/` → estado `CONCLUIDA`, `RegistroConclusaoAcao` único, e recálculo das ações dependentes (que ancoram nesta).
6. **Erros relevantes**: âncora/conclusão em ação já concluída → 400 (ValidationError); conclusão sem observação → 400; recriação de conclusão → erro; sem destinatários elegíveis → notificação não criada, registrada em `fallback_actions`.

**Fallback determinístico de destinatário** (`_resolve_recipients`): se não houver executor+papel, tenta gerente do mesmo executor (para D+1) → gerentes globais → DAT como último recurso. Nota RBAC: os filtros `groups__name__in` aqui são **data-scope** (whitelistados no `rbac_lint`), não autorização.

## Decisões relacionadas (ADRs)

- RBAC: capability hardcoded + atribuição group×capability admin-driven — ver [`rbac.spec.md`](./rbac.spec.md) e [`RBAC_NAMING.md`](../../RBAC_NAMING.md). A feature segue o padrão "capability sem grupos no seed = superuser-only" até maturar.
- Issues de origem: `#870` (engine de prazo/calendário), `#871` (processador diário/escalonamento + beat), `#872` (API). Capability `manage_internal_actions` introduzida na Onda 1 C3 (migration `0079`).
- Sem ADR formal dedicado; o plano antigo [`PLANO_NOTIFICACOES_TIMING.md`](../../_archive/PLANO_NOTIFICACOES_TIMING.md) está arquivado e foi superado por esta implementação.

## Testes que cobrem

- [`tests/test_acoes_notificacao_models.py`](../../../backend/apps/core/tests/test_acoes_notificacao_models.py) — models, constraints, `registrar_ancora`/`concluir`.
- [`tests/test_prazo_engine_service.py`](../../../backend/apps/core/tests/test_prazo_engine_service.py) — resolução de âncora, vencimento, estados, dependentes.
- [`tests/test_business_calendar_service.py`](../../../backend/apps/core/tests/test_business_calendar_service.py) — feriados, dias úteis, distância assinada.
- [`tests/test_notificacoes_acoes_service.py`](../../../backend/apps/core/tests/test_notificacoes_acoes_service.py) — régua de escalonamento, destinatários, dedup, métricas da task.
- [`tests/test_api_acoes_notificacao.py`](../../../backend/apps/core/tests/test_api_acoes_notificacao.py) — endpoints (ciclos/ações/inbox) + RBAC superuser-only.
- [`tests/test_seed_acoes_notificacao.py`](../../../backend/apps/core/tests/test_seed_acoes_notificacao.py) — idempotência do seed e validação 1..32.
- [`tests/test_celery_notificacoes_schedule.py`](../../../backend/apps/core/tests/test_celery_notificacoes_schedule.py) e `test_celery_task_suite.py` — agendamento e execução da task.

## Pontos de atenção / dívidas conhecidas

- **Feature superuser-only**: `manage_internal_actions` não tem grupos no seed; nenhum papel operacional acessa ciclos/ações pela UI hoje. Maturar = admin atribui grupo via interface (sem code change).
- **Sem reabertura de ação concluída** (decisão MVP): conclusões são irreversíveis; correções exigem intervenção manual/admin.
- **Cache de feriados com TTL**: `BusinessCalendarService` cacheia `FeriadoLocal` por 300s por ano; mudanças em feriados só refletem após `invalidate_cache()` ou expiração — relevante ao editar `FeriadoLocal` perto de um vencimento.
- **Régua de notificação discreta**: o processador só dispara nas distâncias exatas {7,3,1,0,-1,-3} dias úteis; se o beat falhar/pular um dia, aquela fase específica não é reemitida (a janela é por dia, não acumulativa).
- **`registrar_ancora` faz `select_for_update`, `concluir` não**: a conclusão não trava a linha; concorrência alta poderia gerar corrida, mitigada pela OneToOne de conclusão e pelo `unique (ciclo, template)`.
- **Texto do seed**: alguns `nome`/`descricao_prazo` carregam typos do material de negócio (ex.: "inicío", relatórios duplicados nas ações 14/21) — preservados como fonte de negócio, não normalizados.

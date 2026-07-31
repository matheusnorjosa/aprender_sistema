---
title: Política de Aprovação (PA-01..PA-07)
status: canonical
last_verified: 2026-07-24
sources_of_truth:
  - v2/backend/apps/core/models/solicitacao.py
  - v2/backend/apps/core/services/solicitacao_create.py
  - v2/backend/apps/core/services/solicitacao_approval.py
  - v2/backend/apps/core/services/solicitacao_availability.py
  - v2/backend/apps/core/services/usuarios_import.py
  - v2/backend/apps/core/rbac/policies.py
  - v2/backend/apps/core/views_solicitacao.py
  - v2/backend/apps/core/tests/test_approval_policy_PA.py
  - v2/backend/apps/core/tests/test_solicitacao_fluxo.py
  - v2/backend/apps/core/tests/test_pr3_approvals_policy.py
  - v2/backend/apps/core/tests/test_auditlog_approve_reject.py
owner: domain
supersedes:
  - docs/business-rules/politica-aprovacao.md
  - docs/architecture/project-decisions/ADR-002-approval-policy-manual.md
  - v2/docs/IMPLEMENTACAO_PA.md
related:
  - ../INDEX_SDD.md
  - ../../rbac_authorization_matrix.md
  - ../../RBAC_NAMING.md
  - ./regras-disponibilidade.spec.md
  - ./clausulas-petreas.spec.md
---

# Política de Aprovação (PA-01..PA-07)

## Propósito

A Política de Aprovação governa o fluxo de aprovação manual de `Solicitacao` (pré-agenda de eventos). É a materialização da Cláusula Pétrea **CP-02**: nenhuma solicitação de projeto que exige decisão humana entra na agenda sem aprovação explícita de um perfil autorizado, e nenhuma integração externa (Google Calendar / Meet) executa antes disso. O objetivo é manter a Superintendência como ponto de decisão com contexto humano que o sistema não captura (exceções, prioridades organizacionais, negociações).

A política distingue dois fluxos de projeto: `SUPER` (requer aprovação manual, nasce `pendente`) e `NAO_SUPER` (auto-aprovado na criação, nasce `aprovado`). Essa distinção é decidida em camada de serviço no momento da criação — não no `save()` do model — para que PA-01 (sem auto-aprovação implícita) seja inviolável por gravações de campo subsequentes.

## Fonte de verdade no código

- **Estado inicial / sem auto-aprovação (PA-01, PA-04)**: [`v2/backend/apps/core/models/solicitacao.py`](../../../backend/apps/core/models/solicitacao.py) — campo `status` com `default="pendente"`, `CheckConstraint` `solicitacao_status_valid` (`pendente|aprovado|reprovado`). O model **não** sobrescreve `save()`: não há lógica de auto-aprovação ali (a regra histórica de auto-aprovar `NAO_SUPER` no `save()` foi removida).
- **Resolução do estado inicial por fluxo**: [`v2/backend/apps/core/services/solicitacao_create.py`](../../../backend/apps/core/services/solicitacao_create.py) — `resolve_initial_status(projeto=...)` retorna `aprovado` sse `projeto.fluxo == "NAO_SUPER"`, senão `pendente`. Aplicado em `SolicitacaoViewSet.perform_create` ([`views_solicitacao.py`](../../../backend/apps/core/views_solicitacao.py)).
- **Perfil exigido (PA-02)**: [`v2/backend/apps/core/rbac/policies.py`](../../../backend/apps/core/rbac/policies.py) — Policy composite `CanAccessSolicitationApprovals` (key `access_solicitation_approvals`) delegando para o helper SSOT `_user_has_solicitation_approvals`.
- **Transições + auditoria + idempotência (PA-05)**: [`v2/backend/apps/core/services/solicitacao_approval.py`](../../../backend/apps/core/services/solicitacao_approval.py) — `approve_solicitacao`, `reject_solicitacao`, `batch_approve_solicitacoes`, `batch_reject_solicitacoes`.
- **Endpoints (PA-02, PA-03)**: [`v2/backend/apps/core/views_solicitacao.py`](../../../backend/apps/core/views_solicitacao.py) — actions `approve`/`reject`/`batch_approve`/`batch_reject` (gate `CanAccessSolicitationApprovals`) e `publish`/`resync_gcal`/`cancel_gcal` (gate `CanUseGcal`, só pós-aprovação).
- **Detalhe canônico das regras**: [`docs/business-rules/politica-aprovacao.md`](../../../../docs/business-rules/politica-aprovacao.md) e [ADR-002](../../../../docs/architecture/project-decisions/ADR-002-approval-policy-manual.md). Matriz de quem aprova: [`v2/docs/rbac_authorization_matrix.md`](../../rbac_authorization_matrix.md).

## Contratos e invariantes

- **PA-01 — Sem auto-aprovação implícita**: `Solicitacao.save()` / `full_clean()` nunca promovem `pendente → aprovado`. A única auto-aprovação válida é a explícita de projeto `NAO_SUPER` no `perform_create`, via `resolve_initial_status`.
- **PA-02 — Perfil exigido**: aprovar/reprovar exige **superuser** OU composite **Gerente da Superintendência** (Setor `Superintendência` + Função `Gerente`) OU **Assistente Administrativo do Controle** (Setor `Controle` + Função `Assistente Administrativo`) — [`policies.py:395-421`](../../../backend/apps/core/rbac/policies.py). DAT, Controle puro e Gerente pedagógico **não** aprovam. ⚠️ O gate é correto no ponto de decisão, mas a **autoridade não é imutável**: o DAT consegue se conceder o composite. Ver `M03-01` em §Divergências. Idioma RBAC: `permission_classes = [CanAccessSolicitationApprovals]` (grupos diretos via `user.groups.filter(name=...)` são banidos por `scripts/rbac_lint.py`, salvo a whitelist `# noqa: RBAC-composite-allowed` no helper composite).
- **PA-03 — Gatilhos pós-aprovação**: integrações externas (GCal/Meet) só rodam com `status == "aprovado"`. `publish` rejeita solicitação pendente e **não** enfileira a task Celery.
- **PA-04 — Estado inicial**: toda solicitação nasce `pendente`, exceto fluxo `NAO_SUPER` (nasce `aprovado`). Garantido por `default="pendente"` + `resolve_initial_status`.
- **PA-05 — Auditoria**: toda aprovação/reprovação grava `AuditLog` (`APPROVE`/`REJECT`) com `solicitacao_id`, `prev_status`, `new_status`, `justificativa`, `ip_address`, `user_agent`; em lote, `details["batch"] = True` por item.
- **PA-06 — UI/UX**: botões de aprovar/reprovar ocultos para perfis sem a policy (frontend consome `access_solicitation_approvals` via `/api/me/policies/`; o legado `can_approve_super` em `/api/me/` **não** é fonte de decisão).
- **PA-07 — Testes obrigatórios**: os 5 testes nomeados existem e passam (ver §Testes).
- **Idempotência / concorrência**: transição só ocorre se `status == "pendente"` sob `select_for_update()` (single) e `select_for_update(skip_locked=True)` (lote) dentro de `transaction.atomic()`; reentrada em solicitação já `aprovado`/`reprovado` retorna `ValidationAPIError` (`already_approved` / `already_rejected` / `invalid_status`), não duplica AuditLog.
- **Limites**: lote máximo de **100** ids por chamada (`batch_limit_exceeded`); `ids` vazio → `ids_required`. ⚠️ `ids` **não é validado como lista de inteiros** — ver `M11-04` em §Divergências.
- **Aprovação REVALIDA conflitos (#1452)**: `approve_solicitacao` chama `enforce_solicitacao_availability(solicitacao, action="approve")` ([`solicitacao_approval.py:136`](../../../backend/apps/core/services/solicitacao_approval.py)) dentro do mesmo `transaction.atomic()` do `select_for_update`; `batch_approve_solicitacoes` faz o mesmo por item (`:305`). Conflito em qualquer participante → **400 `availability_conflict`** e a aprovação não acontece. Em lote, o item conflitante entra em `errors[]` e o resto do lote segue. Como o lote aprova em sequência dentro da mesma transação, a checagem do item N já enxerga os N-1 anteriores como aprovados — é isso que impede um lote de aprovar dois eventos conflitantes do mesmo formador de uma vez. Detalhe do guard em [`regras-disponibilidade.spec.md`](./regras-disponibilidade.spec.md).
- **CP-02** é a cláusula pétrea que ancora toda esta política; ver [`clausulas-petreas.spec.md`](./clausulas-petreas.spec.md).

## API / Interface

Endpoints DRF do `SolicitacaoViewSet` (prefixo `/api/solicitacoes/`):

| Ação | Método | Rota | Gate | Sucesso |
|---|---|---|---|---|
| Criar | POST | `/api/solicitacoes/` | `HasPerm("create_solicitation")` | 201 (`status` = `pendente`/`aprovado`) |
| Aprovar | PATCH | `/api/solicitacoes/{id}/approve/` | `CanAccessSolicitationApprovals` | 200 |
| Reprovar | PATCH | `/api/solicitacoes/{id}/reject/` | `CanAccessSolicitationApprovals` | 200 |
| Aprovar em lote | POST | `/api/solicitacoes/batch_approve/` | `CanAccessSolicitationApprovals` | 200 |
| Reprovar em lote | POST | `/api/solicitacoes/batch_reject/` | `CanAccessSolicitationApprovals` | 200 |
| Publicar (GCal) | POST | `/api/solicitacoes/{id}/publish/` | `CanUseGcal` | 202 (só se `aprovado`; senão 400) |
| Policies do usuário | GET | `/api/me/policies/` | `IsAuthenticated` | lista com `access_solicitation_approvals` quando elegível |

Corpo de `approve`/`reject` aceita `{"justificativa": "..."}` (opcional). Lote aceita `{"ids": [...]}` e retorna `approved_count`/`rejected_count` + `errors[]` por id não processado.

## Fluxos principais

**Fluxo SUPER (aprovação manual):**

1. Coordenador cria solicitação para projeto `fluxo == "SUPER"` → `perform_create` valida disponibilidade (`check_conflicts`) e grava `status="pendente"` (`resolve_initial_status`).
2. Gerente da Superintendência (ou Assistente Administrativo do Controle) chama `approve`/`reject`.
3. Service trava a linha (`select_for_update`), exige `status == "pendente"`, **revalida a disponibilidade de todos os participantes** (`enforce_solicitacao_availability`, #1452), grava novo status e cria `AuditLog`. `reject` não revalida — reprovar não aloca agenda.
4. Aprovada → entra na Pré-Agenda; Controle/Super publica no GCal via `publish` (PA-03).

**Fluxo NAO_SUPER (auto-aprovado):**

1. Coordenador cria solicitação para projeto `fluxo == "NAO_SUPER"` → nasce `status="aprovado"` e vai direto à Pré-Agenda. Não passa pelos endpoints de aprovação.

**Erros relevantes:**

- Perfil não autorizado em `approve`/`reject` → **403** (mensagem cita "permissão"/"Superintendência").
- `publish` em solicitação `pendente` → **400** e task Celery não enfileirada.
- Reaprovar item já decidido → **400** (`already_approved`/`already_rejected`).
- Lote > 100 ou `ids` vazio → **400** (`batch_limit_exceeded`/`ids_required`).
- Aprovar com participante em conflito → **400** `availability_conflict`, com `blocked_participants`. Em lote, vira entrada em `errors[]` e não interrompe os demais itens.

## Decisões relacionadas (ADRs)

- [ADR-002 — Approval Policy Manual](../../../../docs/architecture/project-decisions/ADR-002-approval-policy-manual.md) (CP-02).
- Evolução do gate PA-02 para composite Setor × Função (PR 3 hardening RBAC, #1308) e exposição via `access_solicitation_approvals`: ver [`rbac_authorization_matrix.md`](../../rbac_authorization_matrix.md) e [`RBAC_NAMING.md`](../../RBAC_NAMING.md) §9 (Policy Resolution Rules).

## Testes que cobrem

- [`v2/backend/apps/core/tests/test_approval_policy_PA.py`](../../../backend/apps/core/tests/test_approval_policy_PA.py) — os 5 testes obrigatórios PA-07: `test_never_auto_approves_on_clean_or_save` (PA-01), `test_only_superintendencia_can_approve_or_reject` + `test_non_privileged_user_gets_403_on_approval_endpoint` (PA-02), `test_calendar_integration_not_called_before_approval` + `test_calendar_integration_is_called_after_approval` (PA-03), `test_approval_flow_records_audit_log` (PA-05).
- [`v2/backend/apps/core/tests/test_solicitacao_fluxo.py`](../../../backend/apps/core/tests/test_solicitacao_fluxo.py) — PA-04: SUPER nasce `pendente`, NAO_SUPER nasce `aprovado`, `coordenador_acompanha` não altera fluxo, fallback de projeto ausente.
- [`v2/backend/apps/core/tests/test_pr3_approvals_policy.py`](../../../backend/apps/core/tests/test_pr3_approvals_policy.py) — gate composite `access_solicitation_approvals` (PA-02).
- [`v2/backend/apps/core/tests/test_auditlog_approve_reject.py`](../../../backend/apps/core/tests/test_auditlog_approve_reject.py) — auditoria de approve/reject (PA-05).

## Divergências entre a política escrita e o código

> Reconfirmadas por execução contra `main d08acfa5` e **vivas em produção**. Fonte:
> [`ACHADOS_REAIS.md`](../../audits/ACHADOS_REAIS.md). Uma cláusula pétrea que o código não
> cumpre é um fato do contrato — está registrada aqui, não corrigida no papel.

### `M03-01` — a autoridade de aprovação (PA-02 / CP-02) é auto-concedível

**Severidade P0 · aberto · issue #1610 · vivo em produção.**

PA-02 e CP-02 tratam "quem aprova" como invariante. O import de usuários fura isso:

- Gate do endpoint: `permission_classes = [IsAuthenticated, HasPerm("manage_admin_registries")]` ([`views_import_usuarios.py:66`](../../../backend/apps/core/views_import_usuarios.py)) — capability do grupo **DAT** (3 contas ativas não-superuser em produção).
- `_assign_groups` ([`usuarios_import.py:374-382`](../../../backend/apps/core/services/usuarios_import.py)) resolve o grupo por nome (`Group.objects.filter(name__iexact=...)`) e faz `usuario.groups.add(grupo)`. **Não há allowlist de grupos concedíveis nem comparação ator × alvo** — a única proteção é `superuser_protected`, que cobre o alvo superuser, não a escalação de privilégio do próprio ator.

Cadeia: um usuário só do grupo DAT faz `POST /api/usuarios/import/?dry_run=false` com um CSV contendo o próprio CPF e `grupos="Gerente,Superintendencia"` → **HTTP 200**, zero pendências, zero skips. Os dois grupos concedidos são exatamente os que `_user_has_solicitation_approvals` exige ([`policies.py:415-418`](../../../backend/apps/core/rbac/policies.py)), então o ator passa a aprovar as próprias solicitações.

Consequência para esta spec: **PA-02 descreve corretamente o gate, mas o gate não é uma fronteira de confiança.** Enquanto #1610 estiver aberto, "só Gerente da Superintendência aprova" é uma afirmação sobre a matriz RBAC, não sobre quem de fato consegue aprovar.

### `M10-02` — trocar o projeto para fluxo SUPER preserva `status=aprovado` (lavagem de aprovação)

**Severidade P1 · aberto · issue #1624 · vivo em produção.**

PA-04 diz que solicitação de projeto `SUPER` nasce `pendente` e só vira `aprovado` pelos endpoints de aprovação. `perform_update` ([`views_solicitacao.py:401-497`](../../../backend/apps/core/views_solicitacao.py)) trata `projeto_id` como campo editável comum: ele é lido em `old_data` (`:428`) e `new_data` (`:464`) apenas para o AuditLog, e **`resolve_initial_status` não é reavaliado** — não há nenhum reset de `status` no caminho de update.

Cadeia: criar solicitação em projeto `NAO_SUPER` → nasce `aprovado` sem passar por ninguém (`resolve_initial_status`, [`solicitacao_create.py:33-38`](../../../backend/apps/core/services/solicitacao_create.py)) → `PATCH` trocando `projeto` para um de fluxo `SUPER` → o registro fica `SUPER` **e** `aprovado`, sem nunca ter tido `AuditLog` de `APPROVE`.

Resultado: o evento entra na Pré-Agenda e fica elegível a `publish` (que só checa `status == "aprovado"`, [`solicitacao_publish.py:197`](../../../backend/apps/core/services/solicitacao_publish.py)). PA-01 é respeitada na letra (nada promoveu `pendente → aprovado`) e violada no efeito.

### `M11-04` — `ids` em lote sem validação decompõe string em dígitos

**Severidade P2 · aberto · issue #1650 · vivo em produção.**

`ids = request.data.get("ids", [])` ([`views_solicitacao.py:857`](../../../backend/apps/core/views_solicitacao.py), e `:894` para `batch_reject`) vai direto ao service sem coerção de tipo. Em [`solicitacao_approval.py:272-291`](../../../backend/apps/core/services/solicitacao_approval.py) as duas guardas são `if not ids` e `if len(ids) > 100` — ambas passam para uma **string**, cujo `len` é a contagem de caracteres. `Solicitacao.objects.filter(id__in="123")` faz o Django iterar a string, e o lote alveja as solicitações **1, 2 e 3**.

O aprovador precisa da policy `access_solicitation_approvals`, então não é escalação de privilégio; o defeito é de **integridade da decisão**: aprova alvo que não foi nomeado, e cada item aprovado grava `AuditLog` com `batch: True` como se tivesse sido pedido. O `select_for_update(skip_locked=True)` e o guard de disponibilidade continuam valendo — o dano é aprovar o item errado, não corromper o estado.

## Pontos de atenção / dívidas conhecidas

- **`approve` revalida conflitos desde o #1452** — o texto anterior desta spec dizia o oposto ("decisão deliberada de não revalidar; não reintroduzir `check_conflicts` em `approve`"). Isso descrevia o comportamento pré-#1452 e induzia a remover um guard que hoje é load-bearing. A janela entre criação e aprovação manual **é** revalidada, dentro da transação e sob advisory lock por participante. Conflito é bloqueio duro, sem override, inclusive para `NAO_SUPER` (decisão de negócio, 2026-07-16).
- **Doc legado desatualizado**: `v2/docs/IMPLEMENTACAO_PA.md` ainda cita `Solicitacao.save()` e o caminho obsoleto `apps/core/models.py` (linhas 412-436) e a "PA-02 Adaptada (inclui DAT)". A implementação atual decide estado inicial em `services/solicitacao_create.py` (não no `save()`) e o gate PA-02 é o composite que **exclui** DAT. Esta spec é o índice canônico; arquivar o doc legado em onda futura.
- **`can_approve_super` (legado)**: permanece no payload de `/api/me/` apenas como contrato legado; consumidores novos devem usar `access_solicitation_approvals`. Remover após período de depreciação.
- **Whitelist de lint**: o composite usa `groups.filter(name="Gerente"/"Superintendência")` com `# noqa: RBAC-composite-allowed` — qualquer novo caller que precise do composite deve reusar `_user_has_solicitation_approvals`/`user_has_policy`, não replicar o `groups.filter`.

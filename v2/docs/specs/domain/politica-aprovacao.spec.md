---
title: Política de Aprovação (PA-01..PA-07)
status: canonical
last_verified: 2026-09-29
sources_of_truth:
  - v2/backend/apps/core/models/solicitacao.py
  - v2/backend/apps/core/services/solicitacao_create.py
  - v2/backend/apps/core/services/solicitacao_approval.py
  - v2/backend/apps/core/services/solicitacao_availability.py
  - v2/backend/apps/core/services/usuarios_import.py
  - v2/backend/apps/core/rbac/policies.py
  - v2/backend/apps/core/rbac/helpers.py
  - v2/backend/apps/core/views_solicitacao.py
  - v2/backend/apps/core/tests/test_approval_policy_PA.py
  - v2/backend/apps/core/tests/test_solicitacao_fluxo.py
  - v2/backend/apps/core/tests/test_pr3_approvals_policy.py
  - v2/backend/apps/core/tests/test_auditlog_approve_reject.py
  - v2/backend/apps/core/tests/test_aprovacao_por_gerencia.py
  - v2/backend/apps/core/tests/test_autoaprovacao_bloqueada.py
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
- **Perfil exigido (PA-02)**: [`v2/backend/apps/core/rbac/policies.py`](../../../backend/apps/core/rbac/policies.py) — Policy composite `CanAccessSolicitationApprovals` (key `access_solicitation_approvals`); a regra vive em `solicitation_approval_basis(user)` (SSOT) e `_user_has_solicitation_approvals` é `basis is not None`. O vínculo com a gerência aprovadora é lido por `user_is_gerente_superintendencia` em [`rbac/helpers.py`](../../../backend/apps/core/rbac/helpers.py), com a chave `GERENCIA_APROVADORA_NOME`.
- **Segregação (PA-02, adendo)**: [`services/solicitacao_approval.py`](../../../backend/apps/core/services/solicitacao_approval.py) — `_bloquear_decisao_propria` (individual) e `_decisao_propria_bloqueada` (lote), depois do `select_for_update` e antes do check de status.
- **Transições + auditoria + idempotência (PA-05)**: [`v2/backend/apps/core/services/solicitacao_approval.py`](../../../backend/apps/core/services/solicitacao_approval.py) — `approve_solicitacao`, `reject_solicitacao`, `batch_approve_solicitacoes`, `batch_reject_solicitacoes`.
- **Endpoints (PA-02, PA-03)**: [`v2/backend/apps/core/views_solicitacao.py`](../../../backend/apps/core/views_solicitacao.py) — actions `approve`/`reject`/`batch_approve`/`batch_reject` (gate `CanAccessSolicitationApprovals`) e `publish`/`resync_gcal`/`cancel_gcal` (gate `CanUseGcal`, ou `CanPublishSetorSolicitacao` para a Apoio de Coordenação do setor do evento; só pós-aprovação).
- **Detalhe canônico das regras**: [`docs/business-rules/politica-aprovacao.md`](../../../../docs/business-rules/politica-aprovacao.md) e [ADR-002](../../../../docs/architecture/project-decisions/ADR-002-approval-policy-manual.md). Matriz de quem aprova: [`v2/docs/rbac_authorization_matrix.md`](../../rbac_authorization_matrix.md).

## Contratos e invariantes

- **PA-01 — Sem auto-aprovação implícita**: `Solicitacao.save()` / `full_clean()` nunca promovem `pendente → aprovado`. A única auto-aprovação válida é a explícita de projeto `NAO_SUPER` no `perform_create`, via `resolve_initial_status`.
- **PA-02 — Perfil exigido** (reescrita no PR B1, 2026-09-29): aprovar/reprovar exige, nesta ordem de precedência (`solicitation_approval_basis` em [`policies.py`](../../../backend/apps/core/rbac/policies.py), que devolve a base gravada no AuditLog):
  1. **superuser** (`superuser`);
  2. **gerência da Superintendência por vínculo** (`gerente_superintendencia`): `EquipeGerencia` **vigente** (`vigentes_em()`: `ativo` + janela `valid_from`/`valid_to`) com papel `GERENTE` na gerência cujo `Gerencia.nome == "SUPERINTENDENCIA"` (`GERENCIA_APROVADORA_NOME`). Não depende de grupo Django e **não** checa `Gerencia.ativo` (o vínculo tem o próprio desligamento). A chave é `nome` — técnica e imutável pela API —, não `nome_setor`/rótulo, `setor_canonico` ou id;
  3. **Assistente Administrativo do Controle** (`asst_admin_controle`): Setor `Controle` + Função `Assistente Administrativo`;
  4. **legado até o B2** (`grupo_superintendencia_gerente`): composite Setor `Superintendência` + Função `Gerente`.

  DAT, Controle puro, Gerente pedagógico e COORDENADOR/APOIO/FORMADOR da Superintendência **não** aprovam. Sem gerência `SUPERINTENDENCIA` no banco, a regra por vínculo **falha fechada** (ninguém novo aprova). A aprovadora tem visão global das solicitações (a policy entra em `user_is_solicitacao_global`) e vê a prévia do Google (`preview-gcal`), mas publicar continua exigindo `use_gcal`. Idioma RBAC: `permission_classes = [CanAccessSolicitationApprovals]` (grupos diretos via `user.groups.filter(name=...)` são banidos por `scripts/rbac_lint.py`, salvo a whitelist `# noqa: RBAC-composite-allowed` no helper composite).
- **PA-02 — Adendo de segregação** (PR B1): quem criou a solicitação (`Solicitacao.usuario`) **não aprova nem reprova a própria**. A trava é do service, sob o `select_for_update` e antes do check de status (logo, sem corrida): individual → **403 `self_approval_forbidden`**, nada muda e nenhum AuditLog é gravado; lote → o item próprio entra em `errors[]` com `code: "self_approval_forbidden"` e o resto segue. **Superuser pode** (break-glass): a decisão passa e o AuditLog marca `details.autoaprovacao = true`. Toda decisão grava `details.autoridade` (a base acima). Não se cria PA-08: a CP-02 enumera PA-01..PA-07, e segregação é parte de "quem decide".
- **PA-02 — Anti-escalada** (PR B1): o vínculo que dá o poder de aprovar só nasce pelo formulário de usuário (superuser-only; a concessão e a revogação ficam no AuditLog, `details.autoridade_aprovacao`). Os importers de equipe **recusam criar ou reativar** GERENTE na `SUPERINTENDENCIA` (pendência `vinculo_aprovador_bloqueado`; desativar segue permitido), e `GerenciaSerializer.validate_nome` impede renomear essa gerência ou dar esse nome a outra. Ver [`imports.spec.md`](../backend/imports.spec.md).
- **PA-03 — Gatilhos pós-aprovação**: integrações externas (GCal/Meet) só rodam com `status == "aprovado"`. `publish` rejeita solicitação pendente e **não** enfileira a task Celery.
- **PA-04 — Estado inicial**: toda solicitação nasce `pendente`, exceto fluxo `NAO_SUPER` (nasce `aprovado`). Garantido por `default="pendente"` + `resolve_initial_status`.
- **PA-05 — Auditoria**: toda aprovação/reprovação grava `AuditLog` (`APPROVE`/`REJECT`) com `solicitacao_id`, `prev_status`, `new_status`, `justificativa`, `ip_address`, `user_agent`; em lote, `details["batch"] = True` por item.
- **PA-06 — UI/UX**: botões de aprovar/reprovar ocultos para perfis sem a policy (frontend consome `access_solicitation_approvals` via `/api/me/policies/`; o legado `can_approve_super` em `/api/me/` **não** é fonte de decisão).
- **PA-07 — Testes obrigatórios**: os 5 testes nomeados existem e passam (ver §Testes).
- **Idempotência / concorrência**: transição só ocorre se `status == "pendente"` sob `select_for_update()` (single) e `select_for_update(skip_locked=True)` (lote) dentro de `transaction.atomic()`; reentrada em solicitação já `aprovado`/`reprovado` retorna `ValidationAPIError` (`already_approved` / `already_rejected` / `invalid_status`), não duplica AuditLog.
- **Limites**: lote máximo de **100** ids por chamada (`batch_limit_exceeded`); `ids` vazio → `ids_required`; `ids` é **validado como lista de inteiros** por `_BatchIdsSerializer` (#1650) antes do service — ver `M11-04` em §Divergências.
- **Aprovação REVALIDA conflitos (#1452)**: `approve_solicitacao` chama `enforce_solicitacao_availability(solicitacao, action="approve")` ([`solicitacao_approval.py`](../../../backend/apps/core/services/solicitacao_approval.py)) dentro do mesmo `transaction.atomic()` do `select_for_update`; `batch_approve_solicitacoes` faz o mesmo por item. Conflito em qualquer participante → **400 `availability_conflict`** e a aprovação não acontece. Em lote, o item conflitante entra em `errors[]` e o resto do lote segue. Como o lote aprova em sequência dentro da mesma transação, a checagem do item N já enxerga os N-1 anteriores como aprovados — é isso que impede um lote de aprovar dois eventos conflitantes do mesmo formador de uma vez. Detalhe do guard em [`regras-disponibilidade.spec.md`](./regras-disponibilidade.spec.md).
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
| Publicar (GCal) | POST | `/api/solicitacoes/{id}/publish/` | `CanUseGcal` ou `CanPublishSetorSolicitacao` | 202 (só se `aprovado`; senão 400) |
| Policies do usuário | GET | `/api/me/policies/` | `IsAuthenticated` | lista com `access_solicitation_approvals` quando elegível |

Corpo de `approve`/`reject` aceita `{"justificativa": "..."}` (opcional). Lote aceita `{"ids": [...]}` e retorna `approved_count`/`rejected_count` + `errors[]` por id não processado.

## Fluxos principais

**Fluxo SUPER (aprovação manual):**

1. Coordenador cria solicitação para projeto `fluxo == "SUPER"` → `perform_create` valida disponibilidade (`check_conflicts`) e grava `status="pendente"` (`resolve_initial_status`).
2. A gerência da Superintendência (ou o Assistente Administrativo do Controle) chama `approve`/`reject` — nunca na própria solicitação (segregação).
3. Service trava a linha (`select_for_update`), recusa a decisão própria (403 `self_approval_forbidden`, salvo superuser), exige `status == "pendente"`, **revalida a disponibilidade de todos os participantes** (`enforce_solicitacao_availability`, #1452), grava novo status e cria `AuditLog`. `reject` não revalida — reprovar não aloca agenda.
4. Aprovada → entra na Pré-Agenda; Controle/Super (ou a Apoio de Coordenação do setor do evento) publica no GCal via `publish` (PA-03).

**Fluxo NAO_SUPER (auto-aprovado):**

1. Coordenador cria solicitação para projeto `fluxo == "NAO_SUPER"` → nasce `status="aprovado"` e vai direto à Pré-Agenda. Não passa pelos endpoints de aprovação.

**Erros relevantes:**

- Perfil não autorizado em `approve`/`reject` → **403** (mensagem cita "permissão"/"Superintendência").
- Decidir a própria solicitação → **403** `self_approval_forbidden` ("Você não pode aprovar/reprovar a própria solicitação. Outra pessoa aprovadora precisa decidir."). Em lote, entrada em `errors[]` com o código.
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
- [`v2/backend/apps/core/tests/test_aprovacao_por_gerencia.py`](../../../backend/apps/core/tests/test_aprovacao_por_gerencia.py) — PA-02 por vínculo: GERENTE vigente na SUPERINTENDENCIA aprova sem grupo; outros papéis, outra gerência e vínculo não vigente → 403; sentinela do seed; `validate_nome`; prévia do Google.
- [`v2/backend/apps/core/tests/test_autoaprovacao_bloqueada.py`](../../../backend/apps/core/tests/test_autoaprovacao_bloqueada.py) — adendo de segregação (individual, lote, superuser marcado, `details.autoridade`).

## Divergências entre a política escrita e o código

> Estas divergências foram **fechadas e corrigidas** (verificado no código +
> [`ACHADOS_REAIS.md`](../../audits/ACHADOS_REAIS.md)). Ficam registradas com o que **eram** e
> como foram fechadas — uma cláusula pétrea violada é um fato do contrato, e a correção também.
> Residuais adjacentes seguem apontados para as issues que os rastreiam.

### `M03-01` — a autoridade de aprovação (PA-02 / CP-02) era auto-concedível — **RESOLVIDO (#1610)**

PA-02 e CP-02 tratam "quem aprova" como invariante. O import de usuários **furava** isso; corrigido em `ccbe1e05` (2026-07-30).

- O gate do endpoint segue sendo a capability do grupo **DAT** ([`views_import_usuarios.py`](../../../backend/apps/core/views_import_usuarios.py)), mas a concessão de grupos passou a ser **gated por superuser**: `_actor_pode_atribuir_grupos` ([`usuarios_import.py`](../../../backend/apps/core/services/usuarios_import.py)) só retorna `True` para `actor.is_superuser`, e tanto a decisão quanto a primitiva `_assign_groups` aplicam o gate; um ator não-superuser recebe `grupos_ignorados`, não a escalação. O importer de export-contract só concede grupo do allowlist `ALLOWED_USER_GROUPS` ([`export_contract_importer.py`](../../../backend/apps/core/services/export_contract_importer.py)).
- Cadeia antiga (um usuário DAT importava o próprio CPF com `grupos="Gerente,Superintendencia"` → HTTP 200 → passava a auto-aprovar) está **fechada**: hoje esses grupos só são concedidos por superuser.

Residual: a política **ator × alvo** abrangente — outros writers que mutam contas de terceiros — não é encerrada por M03-01; segue no épico **#1656** (`M07-02` = takeover de conta aprovadora pelo DAT; `M07-01` já resolvido em #1616). O gate de auto-escalação **via import** está fechado.

Com o PR B1 a autoridade passou a vir do **vínculo** `EquipeGerencia`, e o mesmo caminho reabriria por outro import (DAT importando o próprio CPF como GERENTE de "Super"). Fechado no mesmo PR: os importers de equipe recusam criar/reativar esse vínculo (`vinculo_aprovador_bloqueado`), e a conta da aprovadora por vínculo herda a proteção ator×alvo (`can_admin_mutate_target` lê a mesma policy).

### `M11-06` — autoaprovação permitida e sem regra canônica — **fechado no PR B1**

O service não comparava o ator com o dono, `test_auditlog_approve_reject.py` cobria a autoaprovação como comportamento esperado e `compliance_audit` a chamava de violação de PA-01. Hoje o adendo de segregação da PA-02 fecha a regra: 403 `self_approval_forbidden` (lote: `errors[]`), superuser como break-glass marcado em `details.autoaprovacao`; o teste do AuditLog passou a usar um dono diferente do aprovador.

### `M10-02` — trocar o projeto para fluxo SUPER preservava `status=aprovado` (lavagem de aprovação) — **RESOLVIDO (#1624)**

PA-04 diz que solicitação de projeto `SUPER` nasce `pendente` e só vira `aprovado` pelos endpoints de aprovação. O `perform_update` **preservava** `aprovado` ao trocar o projeto; corrigido em #1775: [`views_solicitacao.py`](../../../backend/apps/core/views_solicitacao.py) — se o `projeto_id` mudou, a solicitação estava `aprovado` e o novo projeto resolve para `pendente` (`resolve_initial_status(projeto=instance.projeto).status == "pendente"`), o status é **rebaixado para `pendente`** (`instance.save(update_fields=["status"])`), re-exigindo aprovação.

Cadeia antiga (criar em `NAO_SUPER` → nasce `aprovado` → `PATCH` trocando para projeto `SUPER` → ficava `SUPER` **e** `aprovado` sem `AuditLog` de `APPROVE`, elegível a `publish` que só checa `status == "aprovado"`) está **fechada**: trocar para um fluxo que exige aprovação rebaixa o status.

### `M11-04` — `ids` em lote sem validação decompunha string em dígitos — **RESOLVIDO (#1650)**

`batch_approve`/`batch_reject` **não coagiam o tipo** de `ids`: uma string `"123"` chegava ao service e `Solicitacao.objects.filter(id__in="123")` iterava a string, alvejando as solicitações **1, 2 e 3**. Corrigido em #1773: [`views_solicitacao.py`](../../../backend/apps/core/views_solicitacao.py) define `_BatchIdsSerializer` (`ids = ListField(child=IntegerField(min_value=1))`), aplicado com `is_valid(raise_exception=True)` em `batch_approve` e `batch_reject` — um `ids` que não seja lista de inteiros falha com **400** antes de chegar ao service.

As guardas de vazio/limite em [`solicitacao_approval.py`](../../../backend/apps/core/services/solicitacao_approval.py), o `select_for_update(skip_locked=True)` e o guard de disponibilidade seguem por design. O defeito era de **integridade da decisão** (aprovar alvo não-nomeado, gravando `AuditLog` `batch: True`) — fechado pela validação de tipo.

## Pontos de atenção / dívidas conhecidas

- **`approve` revalida conflitos desde o #1452** — o texto anterior desta spec dizia o oposto ("decisão deliberada de não revalidar; não reintroduzir `check_conflicts` em `approve`"). Isso descrevia o comportamento pré-#1452 e induzia a remover um guard que hoje é load-bearing. A janela entre criação e aprovação manual **é** revalidada, dentro da transação e sob advisory lock por participante. Conflito é bloqueio duro, sem override, inclusive para `NAO_SUPER` (decisão de negócio, 2026-07-16).
- **Doc legado desatualizado**: `v2/docs/IMPLEMENTACAO_PA.md` ainda cita `Solicitacao.save()` e o caminho obsoleto `apps/core/models.py` (linhas 412-436) e a "PA-02 Adaptada (inclui DAT)". A implementação atual decide estado inicial em `services/solicitacao_create.py` (não no `save()`) e o gate PA-02 é o composite que **exclui** DAT. Esta spec é o índice canônico; arquivar o doc legado em onda futura.
- **`can_approve_super` (legado)**: permanece no payload de `/api/me/` apenas como contrato legado; consumidores novos devem usar `access_solicitation_approvals`. Remover após período de depreciação.
- **Whitelist de lint**: o composite usa `groups.filter(name="Gerente"/"Superintendência")` com `# noqa: RBAC-composite-allowed` — qualquer novo caller que precise do composite deve reusar `solicitation_approval_basis`/`user_has_policy`, não replicar o `groups.filter`.
- **B2 pendente**: o composite de grupos (Superintendência + Gerente) segue valendo em paralelo ao vínculo. Removê-lo (B2) só depois do B1 em produção e da conferência nome a nome da lista (`manage.py relatorio_aprovadores`, somente leitura).
- **Gargalo da segregação**: uma pendente criada por uma das poucas aprovadoras só sai com outra aprovadora ou com superuser. As pendentes próprias não entram no card da Home (`pending_approvals` exclui as do próprio usuário não-superuser), mas aparecem na lista de Aprovações com a Tag "Sua solicitação".

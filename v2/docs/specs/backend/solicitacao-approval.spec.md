---
title: Aprovação de Solicitações
status: canonical
last_verified: 2026-06-19
sources_of_truth:
  - v2/backend/apps/core/services/solicitacao_approval.py
  - v2/backend/apps/core/models/solicitacao.py
  - v2/backend/apps/core/views_solicitacao.py
  - v2/backend/apps/core/rbac/policies.py
  - v2/backend/apps/core/services/db_retry.py
  - v2/backend/apps/core/services/solicitacao_create.py
owner: backend
supersedes: []
related:
  - v2/docs/specs/backend/politica-aprovacao.spec.md
  - v2/docs/specs/backend/rbac.spec.md
  - v2/docs/rbac_authorization_matrix.md
  - v2/docs/API_REFERENCE.md
---

# Aprovação de Solicitações

## Propósito

Toda solicitação de evento (pré-agenda) nasce com status `pendente` e só vira agenda real (publicável no Google Calendar, RF05/RF06) depois de uma decisão humana de aprovação. Este módulo é a camada de serviço que executa essa transição de estado de forma transacional, auditável e segura contra corrida: aprovar (`pendente → aprovado`), reprovar (`pendente → reprovado`) e as variantes em lote. É o ponto onde a Política de Aprovação (PA-01..PA-07) deixa de ser regra escrita e vira código que muda o banco.

A regra de *quem* pode decidir vive na camada de Policy RBAC; este módulo cuida do *como* a decisão é aplicada com integridade (lock de linha, idempotência por status, `AuditLog` por registro). A spec é o contrato conciso; a política autorizativa detalhada está em [politica-aprovacao.spec.md](../domain/politica-aprovacao.spec.md) e na [rbac_authorization_matrix.md](../../rbac_authorization_matrix.md).

## Fonte de verdade no código

- [`apps/core/services/solicitacao_approval.py`](../../../backend/apps/core/services/solicitacao_approval.py) — SSOT da transição de estado. Funções públicas: `approve_solicitacao`, `reject_solicitacao`, `batch_approve_solicitacoes`, `batch_reject_solicitacoes`. Dataclasses `ApprovalResult` e `BatchApprovalResult`. Helper de erros de status `_raise_invalid_status_error` e `_build_batch_status_errors`.
- [`apps/core/models/solicitacao.py`](../../../backend/apps/core/models/solicitacao.py) — model `Solicitacao` com `Status` (`PENDENTE`/`APROVADO`/`REPROVADO`, valores `pendente`/`aprovado`/`reprovado`), `default="pendente"` (PA-01) e `CheckConstraint` `solicitacao_status_valid`.
- [`apps/core/views_solicitacao.py`](../../../backend/apps/core/views_solicitacao.py) — `SolicitacaoViewSet` expõe as `@action` `approve`, `reject`, `batch_approve`, `batch_reject` e delega 100% ao service. Gate em `permission_classes=[CanAccessSolicitationApprovals]`.
- [`apps/core/rbac/policies.py`](../../../backend/apps/core/rbac/policies.py) — Policy `CanAccessSolicitationApprovals` (key `access_solicitation_approvals`) + SSOT semântico `_user_has_solicitation_approvals`.
- [`apps/core/services/db_retry.py`](../../../backend/apps/core/services/db_retry.py) — decorator `@retry_on_deadlock` aplicado às 4 funções.
- [`apps/core/services/solicitacao_create.py`](../../../backend/apps/core/services/solicitacao_create.py) — origem do `status="pendente"` (PA-01: nunca auto-aprova na criação).

## Contratos e invariantes

- **PA-01 (status inicial)**: a criação sempre persiste `pendente`; este módulo NUNCA cria solicitação, só transiciona. Nenhum caminho aprova automaticamente.
- **PA-02 (quem decide)**: o gate é `CanAccessSolicitationApprovals` — Gerente da Superintendência **OU** Assistente Administrativo do Controle **OU** superuser. É policy composta (Setor × Função), não OR de capabilities. SSOT em `_user_has_solicitation_approvals`. O service NÃO re-checa autorização — confia na Policy da view; chamadas diretas ao service assumem autorização já validada.
- **Transição válida única**: só `pendente` é mutável. Se `status != "pendente"`, `_raise_invalid_status_error` levanta `ValidationAPIError` com code `already_approved`, `already_rejected` ou `invalid_status` (HTTP 400). Estado terminal: `aprovado` e `reprovado` são imutáveis por esta API.
- **Idempotência / anti-corrida (issue #744)**: cada operação roda em `transaction.atomic()` e relê a linha com `select_for_update()` (lote usa `skip_locked=True`) antes de checar/gravar. Duas aprovações concorrentes no mesmo ID produzem exatamente um vencedor; o perdedor recebe erro de status.
- **Auditoria obrigatória (PA-05)**: toda mudança grava um `AuditLog` (`Action.APPROVE`/`REJECT`) com `solicitacao_id`, `prev_status`, `new_status`, `justificativa`, `ip_address` e `user_agent` (truncado em 200). No lote, **um AuditLog por solicitação** com `batch=True` (nunca um log agregado).
- **Limite de lote**: `ids` é obrigatório (`ids_required`) e no máximo **100** por requisição (`batch_limit_exceeded`); excedente levanta `ValidationAPIError`.
- **Resiliência transitória**: `@retry_on_deadlock` reexecuta a função inteira em deadlock de banco (idempotente porque a re-leitura sob lock revalida o status).
- **CP-04 / camadas**: regra de negócio vive no service (Single Responsibility, Epic #459); a view só orquestra e serializa.

## API / Interface

Endpoints do `SolicitacaoViewSet` (prefixo `/api/solicitacoes/`). Catálogo completo em [API_REFERENCE.md](../../API_REFERENCE.md).

| Método | Rota | Ação | Corpo | Gate |
|--------|------|------|-------|------|
| PATCH | `/api/solicitacoes/{id}/approve/` | `approve` | `reason` ou `justificativa` (opcional) | `CanAccessSolicitationApprovals` |
| PATCH | `/api/solicitacoes/{id}/reject/` | `reject` | `reason` ou `justificativa` (opcional) | `CanAccessSolicitationApprovals` |
| POST | `/api/solicitacoes/batch-approve/` | `batch_approve` | `{ "ids": [int,...] }` | `CanAccessSolicitationApprovals` |
| POST | `/api/solicitacoes/batch-reject/` | `batch_reject` | `{ "ids": [int,...] }` | `CanAccessSolicitationApprovals` |

- Individual → `200 OK` com `{ "detail", "solicitacao": <SolicitacaoSerializer> }`.
- Lote → `200 OK` com `{ "approved" | "rejected": int, "errors": [{ "id", "detail" }] }`. Erros por-ID em vez de falha global: IDs inexistentes (`"Solicitação não encontrada"`) ou já decididos (`"Status já é 'X'"`) entram em `errors` sem abortar os válidos.
- Erros de status / validação → `400` via `ValidationAPIError`. Falta de permissão → `403`. Não autenticado → `401/403`.

Interface de serviço (chamável internamente): `approve_solicitacao(solicitacao, user, request, justificativa="") -> ApprovalResult` e simétricos; lote recebe `ids: list[int]` e devolve `BatchApprovalResult(approved_count, rejected_count, errors)`.

## Fluxos principais

**Aprovação individual (caminho feliz)**
1. View resolve `get_object()` e extrai `reason`/`justificativa`.
2. Service abre transação, faz `select_for_update().get(pk=...)` (relê sob lock).
3. Valida `status == "pendente"`; senão levanta erro de status (400).
4. Grava `status = "aprovado"`, salva, cria `AuditLog` APPROVE e loga evento estruturado.
5. Commit; retorna `ApprovalResult(success=True, ...)`; view responde 200.

**Reprovação**: idêntico, com `status = "reprovado"`, `AuditLog` REJECT e mensagem "Solicitação reprovada.".

**Lote (approve/reject)**
1. Valida `ids` não vazio e `len(ids) <= 100`.
2. Em uma transação, carrega `filter(id__in=ids, status="pendente").select_for_update(skip_locked=True).order_by("id")`.
3. `_build_batch_status_errors` calcula em **uma query** os IDs faltantes/não-pendentes e os anexa a `errors`.
4. Itera os pendentes travados, transiciona cada um, grava `AuditLog` com `batch=True`, incrementa contador.
5. Commit; retorna contadores + `errors` parciais.

**Erros relevantes**: já aprovado/reprovado (400 com code específico no individual; entra em `errors` no lote); deadlock → retry automático; concorrência → perdedor recebe erro de status (sem dupla escrita).

## Decisões relacionadas (ADRs)

- Política PA-02 adaptada (PR 3 #1308): composite Gerente Superintendência **+** Assistente Administrativo do Controle — ver `rbac_authorization_matrix.md` §6 (decisões D10–D17) e [politica-aprovacao.spec.md](../domain/politica-aprovacao.spec.md).
- Camada Policy declarativa (capability/policy layer): contrato público `GET /api/me/policies/` expõe `access_solicitation_approvals` (Epic 4.4/4.5).
- Extração para service layer: Epic #459 (`SolicitacaoViewSet` delega à camada de serviço).
- Anti-corrida de dupla aprovação: issue #744 (`transaction.atomic` + `select_for_update`).

## Testes que cobrem

- [`tests/test_pr3_approvals_policy.py`](../../../backend/apps/core/tests/test_pr3_approvals_policy.py) — personas permitidas/proibidas (403) nos 4 endpoints; superuser permitido; anônimo bloqueado.
- [`tests/test_solicitacao_approval_concurrency.py`](../../../backend/apps/core/tests/test_solicitacao_approval_concurrency.py) — único vencedor sob concorrência (individual e lote), issue #744.
- [`tests/test_approval_policy_PA.py`](../../../backend/apps/core/tests/test_approval_policy_PA.py) — conformidade PA-01..PA-07.
- [`tests/test_solicitacao_fluxo.py`](../../../backend/apps/core/tests/test_solicitacao_fluxo.py) — fluxo de transição de estado fim a fim.
- [`tests/test_views_solicitacao_coverage.py`](../../../backend/apps/core/tests/test_views_solicitacao_coverage.py) — cobertura das actions da view.
- Cobertura de matriz RBAC: `rbac/matrix.py` (`solicitacoes_batch_approve` representa os 4 endpoints) + `tests/test_rbac_matrix_endpoint_coverage.py`.

## Pontos de atenção / dívidas conhecidas

- **Divergência de doc**: [API_REFERENCE.md](../../API_REFERENCE.md) (linhas ~117–118) lista `approve`/`reject` como **POST** com gate `IsSuperintendencia`. O código atual usa **PATCH** e a policy composta `CanAccessSolicitationApprovals` (Super + Assistente Admin Controle + superuser). A spec reflete o código; o API_REFERENCE precisa ser sincronizado (método e gate).
- **Justificativa não obrigatória na reprovação**: o docstring do endpoint diz "Requer justificativa", mas o service aceita `justificativa=""` (default). Não há validação que force texto ao reprovar — gap entre intenção e implementação.
- **Service confia na view para autorização**: chamadas diretas ao service (Celery, management commands, futuros callers) NÃO re-checam `CanAccessSolicitationApprovals`. Qualquer novo caller fora da view deve validar a policy antes (ou expor a regra via `user_has_policy("access_solicitation_approvals")`).
- **Sem efeito colateral de publicação na aprovação**: aprovar apenas muda `status`; a publicação no GCal (RF05/RF06) é um passo separado via actions `publish`/`resync-gcal` (gate `CanUseGcal`). PA-03 (integração externa só após aprovação) é garantido por convenção operacional, não por um trigger acoplado — não há enforcement de "não publicar antes de aprovar" neste módulo.

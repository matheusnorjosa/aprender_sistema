# Implementação PA-01 a PA-07 (PR17)

**Branch**: `feat/pr17-politica-aprovacao` (histórico)
**Status**: ✅ Implementado — **registro do PR17, revisado contra o código em 2026-07-24**
**Data original**: 2025-10-23 · **Revisão**: 2026-07-24

> 🔴 **Leia primeiro — três correções de fato (2026-07-24).** Este documento é o registro de uma PR
> de 2025 e envelheceu. O que mudou desde então:
>
> 1. **PA-01 não é "nenhuma solicitação é auto-aprovada".** O código decide o status inicial em
>    `resolve_initial_status` (`apps/core/services/solicitacao_create.py:23-44`):
>    `fluxo == "NAO_SUPER"` → **`"aprovado"`** (`:33-38`); qualquer outro caso (SUPER, fluxo
>    desconhecido, `projeto is None`) → `"pendente"` (`:40-44`). A garantia real é: **fluxo SUPER
>    nunca auto-aprova.**
> 2. **A data do evento não influencia o status.** `resolve_initial_status` **não recebe data
>    nenhuma** — a assinatura é `(*, projeto: Projeto | None)`. SUPER nasce `pendente` no passado e
>    no futuro; NAO_SUPER nasce `aprovado` nos dois. Confirmado pelo teste
>    `apps/core/tests/test_import_eventos.py:289`. Qualquer doc que diga "SUPER + data futura →
>    pendente" está errado.
> 3. **A aprovação manual passou a revalidar conflitos** (#1452, 2026-07-16). A §"Limitações
>    Conhecidas" no fim deste documento dizia o contrário e está corrigida lá.
>
> A decisão de status vive na **camada de serviço**, não em `Solicitacao.save()` — ver comentário
> em `apps/core/views_solicitacao.py:300`.

## Resumo da Implementação

PR17 implementa conformidade com a Política de Aprovação Manual (CP-02), garantindo que:
1. **Fluxo SUPER** nunca é auto-aprovado (PA-01). *(NAO_SUPER é auto-aprovado por decisão de
   negócio — ver bloco acima.)*
2. Apenas perfis autorizados podem aprovar/reprovar (PA-02 — composite Setor × Função após PR 3 #1308)
3. Integrações externas só executam após aprovação (PA-03)
4. Auditoria completa em AuditLog (PA-05)
5. Botões ocultos para não-autorizados no frontend (PA-06)
6. Testes obrigatórios implementados e passando (PA-07) — hoje **6** funções de teste em
   `apps/core/tests/test_approval_policy_PA.py`

> **Atualização hardening RBAC (2026-04-29 — PR 3 #1308):** PA-02 evoluiu da
> regra original "Superintendência ou superuser" e da "PA-02 Adaptada" intermediária
> ("Sup OR DAT") para uma policy composite Setor × Função:
> `access_solicitation_approvals` exige **Gerente da Superintendência** (Setor
> `Superintendência` + Função `Gerente`) **OU** **Assistente Administrativo do
> Controle** (Setor `Controle` + Função `Assistente Administrativo`).
> DAT, Controle puro e Gerente pedagógico **não aprovam** mais.
> Frontend usa `access_solicitation_approvals` direto (PR 10 #1315);
> `can_approve_super` permanece no payload de `/api/me/` apenas como
> contrato legado — não é fonte de decisão.

## Mudanças Implementadas

### Backend (Django)

#### 1. Decisão de status inicial (PA-01) — **hoje na camada de serviço**

> 🔴 Reescrito em 2026-07-24. O bloco original citava `apps/core/models.py` (linhas 412-436) e um
> override `Solicitacao.save()`. **Nenhum dos dois existe**: `apps/core/models.py` é um *pacote*
> (`apps/core/models/`), e `apps/core/models/solicitacao.py` **não tem `def save`**.

- **Arquivo real**: `v2/backend/apps/core/services/solicitacao_create.py:23-44`
- **Call sites**: `apps/core/views_solicitacao.py:297` (API) e
  `apps/core/services/eventos_import.py:497` (import de eventos)
- **Regra real**:

```python
# apps/core/services/solicitacao_create.py:23
def resolve_initial_status(*, projeto: Projeto | None) -> InitialStatusDecision:
    # :33-38  fluxo == "NAO_SUPER"  -> "aprovado"  (reason: projeto_fluxo_nao_super)
    # :40-44  demais (SUPER, fluxo desconhecido, projeto None) -> "pendente"
    #         (reason: default_or_super_flow)
    ...
```

Não há parâmetro de data. O default do campo no model continua `"pendente"`
(`apps/core/models/solicitacao.py:80-83`), e a decisão explícita é aplicada em
`views_solicitacao.py:301` (`serializer.save(..., status=initial_status.status)`).
Comentário no próprio código: *"status inicial decidido em camada de serviço (não no
model.save())"* (`views_solicitacao.py:300`).

#### 2. Auditoria Persistente (PA-05)
- **Arquivo real**: `v2/backend/apps/core/services/solicitacao_approval.py`
  — `AuditLog.objects.create()` em `:143-155` (approve) e `:214-226` (reject)
- **Endpoints**: `apps/core/views_solicitacao.py:635` (`approve`), `:677` (`reject`)
- **Problema original**: métodos só faziam `logger.info()`, sem AuditLog persistente
- **Código** *(o snippet abaixo é o do PR17; a estrutura atual vive no service acima)*:
```python
# PA-05: AuditLog persistente (compliance)
AuditLog.objects.create(
    usuario=request.user,
    action="APPROVE",  # ou "REJECT"
    model_name="Solicitacao",
    details={
        "solicitacao_id": solicitacao.id,
        "prev_status": prev_status,
        "new_status": "aprovado",  # ou "reprovado"
        "justificativa": justificativa,
        "ip_address": client_ip,
        "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
    },
)
```

#### 3. Testes Obrigatórios (PA-07)
- **Arquivo**: `v2/backend/apps/core/tests/test_approval_policy_PA.py` (344 linhas)
- **5 testes implementados e passando**:
  1. `test_never_auto_approves_on_clean_or_save` - Valida PA-01
  2. `test_only_superintendencia_can_approve_or_reject` - Valida PA-02
  3. `test_non_privileged_user_gets_403_on_approval_endpoint` - Valida PA-02 (complementar)
  4. `test_calendar_integration_not_called_before_approval` - Valida PA-03
  5. `test_approval_flow_records_audit_log` - Valida PA-05

### Frontend (React)

#### 4. ApprovalsPage — Botões Ocultos (PA-06)

> 🔴 Reescrito em 2026-07-24. O arquivo é `.tsx`, não `.jsx`, e a lógica mudou com o PR 10 #1315:
> a decisão passou de **grupos** para **policy**.

- **Arquivo real**: `v2/frontend/src/pages/Aprovacoes/ApprovalsPage.tsx`
- **Linhas**: `:107` (estado `canApprove`), `:158-159` (carga), `:384` (gate do botão)
- **Implementação real**:
  - Chama `getMyPolicies()` (`:158`), **não** `getMe`
  - Deriva com `computeAccess(policies)` (`:159`), chaveado em `access_solicitation_approvals`
    (comentário `:152-153`)
  - **Não** existe `groups.includes('Superintendência')` — a decisão não olha grupos
  - Botões só renderizam se `record.status === 'pendente' && canApprove`
- **Conformidade ISO 9241-110**: Controle explícito (usuário vê apenas ações permitidas)

## Resultados dos Testes

```bash
cd v2/infra && docker compose exec -T web pytest apps/core/tests/test_approval_policy_PA.py -v

test_approval_policy_PA.py::test_never_auto_approves_on_clean_or_save PASSED
test_approval_policy_PA.py::test_only_superintendencia_can_approve_or_reject PASSED
test_approval_policy_PA.py::test_non_privileged_user_gets_403_on_approval_endpoint PASSED
test_approval_policy_PA.py::test_calendar_integration_not_called_before_approval PASSED
test_approval_policy_PA.py::test_approval_flow_records_audit_log PASSED

========================= 5 passed in 2.34s =========================
```

## Conformidade PA-01 a PA-07

> Tabela reconstruída em 2026-07-24 contra o código. Todos os paths da versão anterior
> (`models.py`, `views.py`, `permissions.py::IsSuperintendencia`, `ApprovalsPage.jsx`) não existem.

| Requisito | Status | Implementação real | Arquivo:linha |
|-----------|--------|---------------|---------|
| **PA-01** | ✅ (SUPER) | `resolve_initial_status(*, projeto)` — SUPER→`pendente`, NAO_SUPER→`aprovado`. A **data não entra** na decisão | `services/solicitacao_create.py:23-44` |
| **PA-02** | ✅ | Gate `CanAccessSolicitationApprovals`. A classe `IsSuperintendencia` **não existe**; `apps/core/permissions.py:14-21` exporta só `HasFunctionalPermission, HasPerm, HasSectorAccess, IsGerenteSuperintendencia, IsOwnerOrPrivileged, SuperuserOnly`. **DAT não aprova** | `views_solicitacao.py:632,674,840,877`; `rbac/policies.py:395-421` |
| **PA-03** | ✅ | Celery task `task_publish_solicitacao_to_gcal` validado via mock | `tests/test_approval_policy_PA.py:213,247` |
| **PA-04** | ✅ | Campo `status` com `default="pendente"` | `models/solicitacao.py:80-83` |
| **PA-05** | ✅ | `AuditLog.objects.create()` em approve/reject | `services/solicitacao_approval.py:143-155, 214-226` |
| **PA-06** | ✅ | Botões gateados por policy `access_solicitation_approvals` | `ApprovalsPage.tsx:107,158-159,384` |
| **PA-07** | ✅ | **6** funções de teste (372 linhas) | `tests/test_approval_policy_PA.py:94,127,178,213,247,313` |

## ✅ Atualização #1452 (2026-07-16): a aprovação manual **revalida** conflitos

> 🔴 **Esta seção dizia o contrário até 2026-07-24.** O texto anterior ("Aprovação Manual NÃO
> Revalida Conflitos — comportamento intencional") descrevia o estado anterior ao #1452 e não
> vale mais. Além disso, apontava `views_solicitacao.py:268-323`, que é `perform_create`,
> não `approve()`.

`aprovar_solicitacao` chama `enforce_solicitacao_availability(solicitacao, action="approve")`
**dentro da transação** (`apps/core/services/solicitacao_approval.py:136`, justificativa em
`:132-135`). Isso executa `check_conflicts_uncached` por participante
(`apps/core/services/solicitacao_availability.py:164-170`) e levanta **`400 availability_conflict`**
em caso de choque (`:210-225`).

Comentário do código (`solicitacao_availability.py:201-203`):
*"Conflito é bloqueio duro, sem override: vale para todos os fluxos, inclusive NAO_SUPER
(decisão de negócio, 2026-07-16)."*

Ou seja: **não há mais override por contexto humano na aprovação.** A grade em `/disponibilidade`
continua sendo a ferramenta de consulta, mas deixou de ser a única barreira.

⚠️ **Exceção conhecida**: o **import de eventos** não passa por esse gate — grava `aprovado`
direto para `NAO_SUPER` sem chamar `check_conflicts` (`M08-12`, issue
[#1620](https://github.com/matheusnorjosa/aprender_sistema/issues/1620)). Ver
[imports/agenda_solicitacoes.md](./imports/agenda_solicitacoes.md).

## Arquivos Modificados (registro do PR17 — paths de 2025)

> Os caminhos abaixo refletem a árvore de 2025-10 e **não existem mais**. Equivalentes atuais na
> tabela de conformidade acima.

**Backend**:
- ~~`v2/backend/apps/core/models.py`~~ → `apps/core/services/solicitacao_create.py`
- ~~`v2/backend/apps/core/views.py`~~ → `apps/core/views_solicitacao.py` + `apps/core/services/solicitacao_approval.py`
- `v2/backend/apps/core/tests/test_approval_policy_PA.py` (hoje 372 linhas, 6 testes)

**Frontend**:
- ~~`.../ApprovalsPage.jsx`~~ → `v2/frontend/src/pages/Aprovacoes/ApprovalsPage.tsx`

## Commits

- `ab1858b` - fix(approval): remove auto-approval, add AuditLog, fix tests (5/5 passing)
- `[próximo]` - feat(frontend): add PA-06 permission check in ApprovalsPage

## Próximos Passos

*(Seção histórica — PR17 foi mergeada em 2025. Mantida como registro.)*

✅ PA-01 a PA-07 completo
✅ Push branch + PR17 · ✅ Review e merge

### Backlog atual relacionado a PA (2026-07-24)

- [#1620](https://github.com/matheusnorjosa/aprender_sistema/issues/1620) — import de eventos grava
  `aprovado` sem o hard gate de disponibilidade do #1452.
- [#1624](https://github.com/matheusnorjosa/aprender_sistema/issues/1624) — troca de projeto para
  fluxo SUPER mantém status aprovado (lavagem de aprovação).
- [#1628](https://github.com/matheusnorjosa/aprender_sistema/issues/1628) — reimport sobrescreve a
  decisão de aprovação e reporta "unchanged".

Documento vivo: [audits/ACHADOS_REAIS.md](./audits/ACHADOS_REAIS.md).

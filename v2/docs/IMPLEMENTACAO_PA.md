# Implementação PA-01 a PA-07 (PR17)

**Branch**: `feat/pr17-politica-aprovacao` (histórico)
**Status**: ✅ Implementado — **registro do PR17, revisado contra o código em 2026-07-24**
**Data original**: 2025-10-23 · **Revisão**: 2026-07-24

> 🔴 **Leia primeiro — três correções de fato (2026-07-24).** Este documento é o registro de uma PR
> de 2025 e envelheceu. O que mudou desde então:
>
> 1. **PA-01 não é "nenhuma solicitação é auto-aprovada".** O código decide o status inicial em
>    `resolve_initial_status` (`apps/core/services/solicitacao_create.py`):
>    `fluxo == "NAO_SUPER"` → **`"aprovado"`** (`:33-38`); qualquer outro caso (SUPER, fluxo
>    desconhecido, `projeto is None`) → `"pendente"` (`:40-44`). A garantia real é: **fluxo SUPER
>    nunca auto-aprova.**
> 2. **A data do evento não influencia o status.** `resolve_initial_status` **não recebe data
>    nenhuma** — a assinatura é `(*, projeto: Projeto | None)`. SUPER nasce `pendente` no passado e
>    no futuro; NAO_SUPER nasce `aprovado` nos dois. Confirmado pelo teste
>    `test_projeto_super_passado_status_pendente` (`apps/core/tests/test_import_eventos.py`). Qualquer doc que diga "SUPER + data futura →
>    pendente" está errado.
> 3. **A aprovação manual passou a revalidar conflitos** (#1452, 2026-07-16). A §"Limitações
>    Conhecidas" no fim deste documento dizia o contrário e está corrigida lá.
>
> A decisão de status vive na **camada de serviço**, não em `Solicitacao.save()` — ver comentário
> em `perform_create` (`apps/core/views_solicitacao.py`).

## Resumo da Implementação

PR17 implementa conformidade com a Política de Aprovação Manual (CP-02), garantindo que:
1. **Fluxo SUPER** nunca é auto-aprovado (PA-01). *(NAO_SUPER é auto-aprovado por decisão de
   negócio — ver bloco acima.)*
2. Apenas perfis autorizados podem aprovar/reprovar (PA-02 — hoje `solicitation_approval_basis`, 3 bases; ver bloco abaixo)
3. Integrações externas só executam após aprovação (PA-03)
4. Auditoria completa em AuditLog (PA-05)
5. Botões ocultos para não-autorizados no frontend (PA-06)
6. Testes obrigatórios implementados e passando (PA-07) — hoje **7** funções de teste em
   `apps/core/tests/test_approval_policy_PA.py` (PR 10: + `test_segregacao_conta_alterada_bloqueia_decisao`)

> **Atualização PR 11 das permissões (2026-10-17):** PA-02 passou pela regra original
> "Superintendência ou superuser", pela "PA-02 Adaptada" ("Sup OR DAT") e pelo composite
> Setor × Função do PR 3 #1308. Hoje **nenhum grupo aprova**: `access_solicitation_approvals`
> segue a SSOT `solicitation_approval_basis` (`apps/core/rbac/policies.py`), com 3 bases —
> superuser; vínculo `GERENTE` vigente na gerência Superintendência; a capacidade
> `approve_solicitation` do pacote do perfil, pelo vínculo `EQUIPE`/`GERENTE` na gerência DAT
> (`ADMIN_OPERACIONAL`, PR 10) ou Controle (`CONTROLE`, PR 11) — com a segregação por histórico.
> Regra completa: [`politica-aprovacao.spec.md`](specs/domain/politica-aprovacao.spec.md) (PA-02)
> e [`rbac.spec.md`](specs/backend/rbac.spec.md).
> Frontend usa `access_solicitation_approvals` direto (PR 10 #1315);
> `can_approve_super` permanece no payload de `/api/me/` apenas como
> contrato legado — não é fonte de decisão.

## Mudanças Implementadas

### Backend (Django)

#### 1. Decisão de status inicial (PA-01) — **hoje na camada de serviço**

> 🔴 Reescrito em 2026-07-24. O bloco original citava `apps/core/models.py` (linhas 412-436) e um
> override `Solicitacao.save()`. **Nenhum dos dois existe**: `apps/core/models.py` é um *pacote*
> (`apps/core/models/`), e `apps/core/models/solicitacao.py` **não tem `def save`**.

- **Arquivo real**: `v2/backend/apps/core/services/solicitacao_create.py`
- **Call sites**: `apps/core/views_solicitacao.py` (na API, dentro de `perform_create`) e
  `apps/core/services/eventos_import.py` (import de eventos)
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
(`Solicitacao.status`, `apps/core/models/solicitacao.py`), e a decisão explícita é aplicada em
`perform_create` (`views_solicitacao.py`), no `serializer.save(..., status=initial_status.status)`.
Comentário no próprio código: *"status inicial decidido em camada de serviço (não no
model.save())"* (mesmo `perform_create`).

#### 2. Auditoria Persistente (PA-05)
- **Arquivo real**: `v2/backend/apps/core/services/solicitacao_approval.py`
  — `AuditLog.objects.create()` dentro de `approve_solicitacao` (approve) e `reject_solicitacao` (reject)
- **Endpoints**: métodos `approve` e `reject` do `SolicitacaoViewSet` (`apps/core/views_solicitacao.py`)
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
- **Arquivo**: `v2/backend/apps/core/tests/test_approval_policy_PA.py`
- **7 testes implementados e passando** (o 7º entrou no PR 10 das permissões):
  1. `test_never_auto_approves_on_clean_or_save` - Valida PA-01
  2. `test_only_superintendencia_can_approve_or_reject` - Valida PA-02
  3. `test_non_privileged_user_gets_403_on_approval_endpoint` - Valida PA-02 (complementar)
  4. `test_calendar_integration_not_called_before_approval` - Valida PA-03
  5. `test_calendar_integration_is_called_after_approval` - Valida PA-03 (lado positivo)
  6. `test_approval_flow_records_audit_log` - Valida PA-05
  7. `test_segregacao_conta_alterada_bloqueia_decisao` - Valida a segregação (`decisoes_impedidas`) na decisão

### Frontend (React)

#### 4. ApprovalsPage — Botões Ocultos (PA-06)

> 🔴 Reescrito em 2026-07-24. O arquivo é `.tsx`, não `.jsx`, e a lógica mudou com o PR 10 #1315:
> a decisão passou de **grupos** para **policy**.

- **Arquivo real**: `v2/frontend/src/pages/Aprovacoes/ApprovalsPage.tsx`
- **Onde**: estado `canApprove` (`useState`), carga no `useEffect` `loadAccess`, gate nas
  colunas de ação e na barra de seleção em lote
- **Implementação real**:
  - `loadAccess` chama `getMyPolicies()`; o `getMe()` em paralelo só alimenta a regra de
    segregação (PA-02) na tabela, não a decisão de mostrar os botões
  - Deriva com `computeCapabilities(policies).canAccessApprovals`, chaveado em
    `access_solicitation_approvals` (comentário acima do `useEffect`)
  - **Não** existe `groups.includes('Superintendência')` — a decisão não olha grupos
  - Botões só renderizam se `record.status === 'pendente' && canApprove`; com impedimento
    (`impedimento(record)`, PA-02) a linha mostra uma etiqueta da decisão impedida em vez dos botões
- **Conformidade ISO 9241-110**: Controle explícito (usuário vê apenas ações permitidas)

## Resultados dos Testes

> Saída registrada no PR17, com os 6 testes da época. Hoje o arquivo tem 7 (ver lista acima).

```bash
cd v2/infra && docker compose exec -T web pytest apps/core/tests/test_approval_policy_PA.py -v

test_approval_policy_PA.py::test_never_auto_approves_on_clean_or_save PASSED
test_approval_policy_PA.py::test_only_superintendencia_can_approve_or_reject PASSED
test_approval_policy_PA.py::test_non_privileged_user_gets_403_on_approval_endpoint PASSED
test_approval_policy_PA.py::test_calendar_integration_not_called_before_approval PASSED
test_approval_policy_PA.py::test_calendar_integration_is_called_after_approval PASSED
test_approval_policy_PA.py::test_approval_flow_records_audit_log PASSED

========================= 6 passed in 2.34s =========================
```

## Conformidade PA-01 a PA-07

> Tabela reconstruída em 2026-07-24 contra o código. Todos os paths da versão anterior
> (`models.py`, `views.py`, `permissions.py::IsSuperintendencia`, `ApprovalsPage.jsx`) não existem.

| Requisito | Status | Implementação real | Arquivo:linha |
|-----------|--------|---------------|---------|
| **PA-01** | ✅ (SUPER) | `resolve_initial_status(*, projeto)` — SUPER→`pendente`, NAO_SUPER→`aprovado`. A **data não entra** na decisão | `services/solicitacao_create.py` |
| **PA-02** | ✅ | Gate `CanAccessSolicitationApprovals`. A classe `IsSuperintendencia` **não existe**; `apps/core/permissions.py` exporta só `HasFunctionalPermission, HasPerm, HasSectorAccess, IsOwnerOrPrivileged, SuperuserOnly` (`IsGerenteSuperintendencia` saiu no PR 8). **DAT aprova desde o PR 10 e o Controle desde o PR 11** (base `capacidade_aprovar`) | 4 `@action` gateados por `CanAccessSolicitationApprovals` (`approve`/`reject`/`batch_approve`/`batch_reject`); `_user_has_solicitation_approvals` (`rbac/policies.py`) |
| **PA-03** | ✅ | Celery task `task_publish_solicitacao_to_gcal` validado via mock | `test_calendar_integration_not_called_before_approval` / `test_calendar_integration_is_called_after_approval` (`tests/test_approval_policy_PA.py`) |
| **PA-04** | ✅ | Campo `status` com `default="pendente"` | `Solicitacao.status` (`models/solicitacao.py`) |
| **PA-05** | ✅ | `AuditLog.objects.create()` em approve/reject | `approve_solicitacao`/`reject_solicitacao` (`services/solicitacao_approval.py`) |
| **PA-06** | ✅ | Botões gateados por policy `access_solicitation_approvals` | `ApprovalsPage.tsx` |
| **PA-07** | ✅ | **7** funções de teste | as funções de teste em `tests/test_approval_policy_PA.py` |

## ✅ Atualização #1452 (2026-07-16): a aprovação manual **revalida** conflitos

> 🔴 **Esta seção dizia o contrário até 2026-07-24.** O texto anterior ("Aprovação Manual NÃO
> Revalida Conflitos — comportamento intencional") descrevia o estado anterior ao #1452 e não
> vale mais. Além disso, apontava `perform_create` (`views_solicitacao.py`),
> não `approve()`.

`approve_solicitacao` (`apps/core/services/solicitacao_approval.py`) chama
`enforce_solicitacao_availability(solicitacao, action="approve")` **dentro da transação**. Isso
executa `check_conflicts_uncached` por participante (em `check_solicitacao_availability`,
`apps/core/services/solicitacao_availability.py`) e levanta **`400 availability_conflict`**
em caso de choque (`raise_if_blocked`).

Comentário do código (docstring de `raise_if_blocked`, `solicitacao_availability.py`):
*"Conflito é bloqueio duro, sem override: vale para todos os fluxos, inclusive NAO_SUPER
(decisão de negócio, 2026-07-16)."*

Ou seja: **não há mais override por contexto humano na aprovação.** A grade em `/disponibilidade`
continua sendo a ferramenta de consulta, mas deixou de ser a única barreira.

✅ **Resolvido (#2021)**: o **import de eventos** passa pelo gate `check_solicitacao_availability`
(RD-01..08) para evento **FUTURO** — conflito vira pendência `availability` sem gravar; evento
**histórico** (data passada) entra sem checar (decisão do dono). `M08-12`, issue
[#1620](https://github.com/matheusnorjosa/aprender_sistema/issues/1620). Ver
[imports/agenda_solicitacoes.md](./imports/agenda_solicitacoes.md).

## Arquivos Modificados (registro do PR17 — paths de 2025)

> Os caminhos abaixo refletem a árvore de 2025-10 e **não existem mais**. Equivalentes atuais na
> tabela de conformidade acima.

**Backend**:
- ~~`v2/backend/apps/core/models.py`~~ → `apps/core/services/solicitacao_create.py`
- ~~`v2/backend/apps/core/views.py`~~ → `apps/core/views_solicitacao.py` + `apps/core/services/solicitacao_approval.py`
- `v2/backend/apps/core/tests/test_approval_policy_PA.py` (hoje 7 testes)

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

- ✅ [#1620](https://github.com/matheusnorjosa/aprender_sistema/issues/1620) — **resolvido no #2021**:
  import de eventos aplica o hard gate de disponibilidade a evento futuro (histórico entra sem checar).
- ✅ [#1628](https://github.com/matheusnorjosa/aprender_sistema/issues/1628) — **resolvido no #2021**
  (itens 2/3/4): reimport não sobrescreve mais decisão humana e reporta diff real. Item 1 (hash) pendente.

Documento vivo: [audits/ACHADOS_REAIS.md](./audits/ACHADOS_REAIS.md).

# Implementação PA-01 a PA-07 (PR17)

**Branch**: `feat/pr17-politica-aprovacao`
**Status**: ✅ Implementado e testado (commit ab1858b + PA-06 frontend)
**Data**: 2025-10-23

## Resumo da Implementação

PR17 implementa conformidade total com a Política de Aprovação Manual (CP-02), garantindo que:
1. Nenhuma solicitação é auto-aprovada (PA-01)
2. Apenas Superintendência pode aprovar/reprovar (PA-02)
3. Integrações externas só executam após aprovação (PA-03)
4. Auditoria completa em AuditLog (PA-05)
5. Botões ocultos para não-autorizados no frontend (PA-06)
6. 5 testes obrigatórios implementados e passando (PA-07)

## Mudanças Implementadas

### Backend (Django)

#### 1. models.py - Remoção de Auto-Aprovação (PA-01)
- **Arquivo**: `v2/backend/apps/core/models.py` (linhas 412-436)
- **Problema**: `Solicitacao.save()` auto-aprovava quando `projeto.fluxo == "NAO_SUPER"`
- **Correção**: Removida lógica de auto-aprovação completamente
- **Código**:
```python
def save(self, *args, **kwargs):
    """
    Override save para garantir conformidade com PA-01.

    PA-01: Nenhuma solicitação é auto-aprovada, independentemente do fluxo do projeto.

    Histórico:
    - PR 13/N: Auto-aprovação implementada (REMOVIDA em PR17)
    - PR17: Conformidade com PA-01 (Política de Aprovação Manual obrigatória)
    """
    # PA-01: Sem auto-aprovação. Status sempre começa 'pendente'.
    if self.pk is None and not hasattr(self, '_status_explicitly_set'):
        pass  # Mantém o default do campo (status='pendente')

    super().save(*args, **kwargs)
```

#### 2. views.py - Auditoria Persistente (PA-05)
- **Arquivo**: `v2/backend/apps/core/views.py`
- **Métodos**: `approve()` (linhas 165-220), `reject()` (linhas 236-290)
- **Problema**: Métodos só faziam `logger.info()`, sem AuditLog persistente
- **Correção**: Adicionado `AuditLog.objects.create()` em ambos os métodos
- **Código**:
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

#### 4. ApprovalsPage.jsx - Botões Ocultos (PA-06)
- **Arquivo**: `v2/frontend/src/pages/Aprovacoes/ApprovalsPage.jsx`
- **Linhas**: 66-68 (estado), 89-109 (useEffect), 211 (botões)
- **Implementação**:
  - Importa `getMe` da API
  - Carrega dados do usuário no mount
  - Verifica `is_superuser || is_superintendencia || groups.includes('Superintendência')`
  - Armazena em `canApprove` state
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

| Requisito | Status | Implementação | Arquivo |
|-----------|--------|---------------|---------|
| **PA-01** | ✅ | Sem auto-aprovação em `Solicitacao.save()` | `models.py:412-436` |
| **PA-02** | ✅ | Permission class `IsSuperintendencia` + endpoints protegidos | `permissions.py`, `views.py` |
| **PA-03** | ✅ | Celery task `task_publish_solicitacao_to_gcal` validado via mock | `test_approval_policy_PA.py:201-262` |
| **PA-04** | ✅ | Campo `status` tem `default='pendente'` | `models.py:120` |
| **PA-05** | ✅ | `AuditLog.objects.create()` em approve/reject | `views.py:165-220, 236-290` |
| **PA-06** | ✅ | Botões ocultos para não-Superintendência | `ApprovalsPage.jsx:66-68, 211` |
| **PA-07** | ✅ | 5 testes obrigatórios implementados e passando | `test_approval_policy_PA.py` |

## ⚠️ Nota Importante: Aprovação Manual NÃO Revalida Conflitos

**Comportamento intencional**: O endpoint `approve()` (views_solicitacao.py:268-323) **NÃO** chama `check_conflicts()` antes de aprovar.

**Razão**: Superintendência toma decisões com **contexto humano** que o sistema não captura:
- Exceções autorizadas
- Prioridades políticas/organizacionais
- Contexto específico do município/projeto
- Negociações não-formalizadas

**Fluxo**: Superintendência acessa `/disponibilidade` (visualização da grade) e verifica **manualmente** antes de aprovar em `/aprovacoes`.

**Sistema = ferramenta de suporte à decisão, NÃO automatização total.**

## Arquivos Modificados

**Backend**:
- `v2/backend/apps/core/models.py` (Solicitacao.save)
- `v2/backend/apps/core/views.py` (approve/reject methods)
- `v2/backend/apps/core/tests/test_approval_policy_PA.py` (novo, 344 linhas)

**Frontend**:
- `v2/frontend/src/pages/Aprovacoes/ApprovalsPage.jsx` (PA-06)

## Commits

- `ab1858b` - fix(approval): remove auto-approval, add AuditLog, fix tests (5/5 passing)
- `[próximo]` - feat(frontend): add PA-06 permission check in ApprovalsPage

## Próximos Passos

✅ PA-01 a PA-07 completo
⏳ Push branch + criar PR17
⏳ Review e merge

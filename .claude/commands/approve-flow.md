---
description: Test PA-01 to PA-07 approval policy compliance
argument-hint: [optional: specific test or 'all']
---

# Approve Flow — PA-01 to PA-07 Compliance

Test approval policy: ${ARGUMENTS:-all}

## Approach:

### 1. Run Tests

```bash
# All PA-01 to PA-07 tests
docker compose exec -T web pytest apps/core/tests/test_approval_policy_PA.py -v

# Specific test
docker compose exec -T web pytest apps/core/tests/test_approval_policy_PA.py::$ARGUMENTS -v

# With coverage
docker compose exec -T web pytest apps/core/tests/test_approval_policy_PA.py --cov=apps.core.models --cov=apps.core.views --cov-report=term-missing
```

### 2. Expected Results (5 mandatory tests)

#### PA-01: No Auto-Approval (SUPER Projects)
- [ ] `test_never_auto_approves_on_clean_or_save`

**Validates**:
- Solicitação with `projeto.fluxo == 'SUPER'` NEVER auto-approves
- Status remains 'pendente' after save/clean
- No auto-approval in Solicitacao.save() method

**Note**: NAO_SUPER projects ARE auto-approved (tested in `test_solicitacao_fluxo.py`)

#### PA-02: Required Profile (Superintendência Only)
- [ ] `test_only_superintendencia_can_approve_or_reject`
- [ ] `test_non_privileged_user_gets_403_on_approval_endpoint`

**Validates**:
- Permission class `IsSuperintendencia` blocks non-authorized users
- 403 Forbidden for Coordenador/Formador on approve/reject endpoints
- Only Superintendência (or Admin) can approve/reject

#### PA-03: Post-Approval Triggers
- [ ] `test_calendar_integration_not_called_before_approval`

**Validates**:
- `task_publish_solicitacao_to_gcal` is NOT called during Solicitacao.save()
- External integrations only execute AFTER manual approval
- Google Calendar integration respects approval flow

#### PA-05: Audit Persistent
- [ ] `test_approval_flow_records_audit_log`

**Validates**:
- AuditLog.objects.create() called on approve/reject
- Fields: usuario, action, model_name, details (JSON)
- Details include: solicitacao_id, prev_status, new_status, justificativa, ip_address, user_agent

### 3. Manual Validation

If tests fail, validate PA rules manually:

#### PA-01: No Auto-Approval
```python
from apps.core.models import Usuario, Projeto, Municipio, Solicitacao
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Create SUPER project
projeto_super = Projeto.objects.get_or_create(
    nome='Teste SUPER',
    fluxo='SUPER'
)[0]

# Create solicitacao
usuario = Usuario.objects.first()
municipio = Municipio.objects.first()
tz = ZoneInfo('America/Fortaleza')

solicitacao = Solicitacao.objects.create(
    projeto=projeto_super,
    usuario=usuario,
    municipio=municipio,
    inicio=datetime(2025, 1, 15, 9, 0, tzinfo=tz),
    fim=datetime(2025, 1, 15, 12, 0, tzinfo=tz)
)

print(f"Status after save: {solicitacao.status}")  # Should be 'pendente'
assert solicitacao.status == 'pendente', "PA-01 VIOLATED: Auto-approved!"

# Verify NAO_SUPER auto-approval
projeto_nao_super = Projeto.objects.get_or_create(
    nome='Teste NAO_SUPER',
    fluxo='NAO_SUPER'
)[0]

solicitacao_nao_super = Solicitacao.objects.create(
    projeto=projeto_nao_super,
    usuario=usuario,
    municipio=municipio,
    inicio=datetime(2025, 1, 16, 9, 0, tzinfo=tz),
    fim=datetime(2025, 1, 16, 12, 0, tzinfo=tz)
)

print(f"NAO_SUPER status: {solicitacao_nao_super.status}")  # Should be 'aprovado'
```

#### PA-02: Permission Class
```python
from django.test import Client
from django.contrib.auth.models import Group

client = Client()

# Login as Coordenador (non-authorized)
coordenador = Usuario.objects.filter(groups__name='Coordenador').first()
client.force_login(coordenador)

# Try to approve (should fail with 403)
response = client.post(f'/api/solicitacoes/{solicitacao.id}/approve/')
print(f"Response status: {response.status_code}")  # Should be 403
assert response.status_code == 403, "PA-02 VIOLATED: Non-authorized can approve!"

# Login as Superintendência (authorized)
superintendencia = Usuario.objects.filter(groups__name='Superintendência').first()
client.force_login(superintendencia)

# Try to approve (should succeed with 200)
response = client.post(f'/api/solicitacoes/{solicitacao.id}/approve/')
print(f"Response status: {response.status_code}")  # Should be 200
```

#### PA-05: Audit Log
```python
from apps.core.models import AuditLog

# Approve solicitacao
response = client.post(f'/api/solicitacoes/{solicitacao.id}/approve/')

# Check AuditLog
audit_log = AuditLog.objects.filter(
    action='APPROVE',
    details__solicitacao_id=solicitacao.id
).first()

print(f"Audit log exists: {audit_log is not None}")
print(f"Usuario: {audit_log.usuario}")
print(f"Details: {audit_log.details}")

assert audit_log is not None, "PA-05 VIOLATED: No AuditLog created!"
assert audit_log.details['prev_status'] == 'pendente'
assert audit_log.details['new_status'] == 'aprovado'
```

### 4. Frontend Validation (PA-06)

**File**: `v2/frontend/src/pages/Aprovacoes/ApprovalsPage.jsx`

Check:
- [ ] Component imports `getMe` from API
- [ ] `useEffect` calls `getMe()` on mount (lines 89-109)
- [ ] State `canApprove` is set based on:
  - `is_superuser || is_superintendencia || groups.includes('Superintendência')`
- [ ] Approve/Reject buttons only render if:
  - `record.status === 'pendente' && canApprove` (line 211)

**Manual test**:
1. Login as Coordenador → Go to `/aprovacoes`
2. Verify Approve/Reject buttons are HIDDEN
3. Login as Superintendência → Go to `/aprovacoes`
4. Verify Approve/Reject buttons are VISIBLE

### 5. API Endpoint Testing

```bash
# Test approve endpoint (as Superintendência)
curl -X POST "http://localhost:8002/api/solicitacoes/1/approve/" \
  -H "Authorization: Bearer $TOKEN_SUPERINTENDENCIA" \
  -H "Content-Type: application/json" \
  -d '{"justificativa": "Teste aprovação"}'

# Expected: 200 OK

# Test approve endpoint (as Coordenador)
curl -X POST "http://localhost:8002/api/solicitacoes/1/approve/" \
  -H "Authorization: Bearer $TOKEN_COORDENADOR" \
  -H "Content-Type: application/json" \
  -d '{"justificativa": "Teste aprovação"}'

# Expected: 403 Forbidden

# Test reject endpoint
curl -X POST "http://localhost:8002/api/solicitacoes/1/reject/" \
  -H "Authorization: Bearer $TOKEN_SUPERINTENDENCIA" \
  -H "Content-Type: application/json" \
  -d '{"justificativa": "Teste reprovação"}'

# Expected: 200 OK
```

### 6. Compliance Matrix

| Requisito | Implementação | Teste | Status |
|-----------|---------------|-------|--------|
| **PA-01** | `models.py:431-448` (SUPER only) | `test_never_auto_approves_on_clean_or_save` | ✅ |
| **PA-02** | `permissions.py:IsSuperintendencia` | `test_only_superintendencia_can_approve_or_reject` | ✅ |
| **PA-03** | `views.py:approve()` (no task call) | `test_calendar_integration_not_called_before_approval` | ✅ |
| **PA-04** | `models.py:120` (`default='pendente'`) | Implicit in PA-01 test | ✅ |
| **PA-05** | `views.py:165-220, 236-290` | `test_approval_flow_records_audit_log` | ✅ |
| **PA-06** | `ApprovalsPage.jsx:66-68, 211` | Manual UI test | ✅ |
| **PA-07** | All tests above | Run pytest | ✅ |

### 7. Output

**If all tests pass (5/5)**:
```
✅ PA-01 to PA-07 COMPLIANT
- PA-01: No auto-approval (SUPER) ✓
- PA-02: Superintendência only ✓
- PA-03: Post-approval triggers ✓
- PA-04: Initial status pendente ✓
- PA-05: AuditLog persistent ✓
- PA-06: UI buttons hidden (manual check)
- PA-07: 5 mandatory tests passing ✓

Total: 5/5 tests passing

Approval policy fully compliant with CP-02.
```

**If tests fail**:
```
❌ PA-01 to PA-07 NON-COMPLIANT
Failed tests: N/5

[List failed tests with details]

Next steps:
1. Review failure logs
2. Check `apps/core/models.py:Solicitacao.save()`
3. Check `apps/core/views.py:approve()` and `reject()`
4. Verify `apps/core/permissions.py:IsSuperintendencia`
5. Check AuditLog creation in approve/reject methods
```

### 8. Important Note: Manual Approval Does NOT Revalidate Conflicts

**Behavior**: The `approve()` endpoint **DOES NOT** call `check_conflicts()` before approving.

**Reason**: Superintendência decisions include **human context** that the system cannot capture:
- Authorized exceptions
- Political/organizational priorities
- Municipality/project specific context
- Non-formalized negotiations

**Workflow**: Superintendência accesses `/disponibilidade` (grid view) and verifies **manually** before approving in `/aprovacoes`.

**System = decision support tool, NOT total automation.**

## Reference

- **Business Rules**: `.claude/skills/aprender-domain/SKILL.md` (PA-01 to PA-07)
- **Implementation**: `apps/core/models.py`, `apps/core/views.py`
- **Tests**: `apps/core/tests/test_approval_policy_PA.py`
- **Frontend**: `v2/frontend/src/pages/Aprovacoes/ApprovalsPage.jsx`

---

**Expected**: 5/5 tests passing (PR17 baseline)

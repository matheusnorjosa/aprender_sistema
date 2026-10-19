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
docker exec aprender_dev-web-1 pytest apps/core/tests/test_approval_policy_PA.py -v

# Specific test
docker exec aprender_dev-web-1 pytest apps/core/tests/test_approval_policy_PA.py::$ARGUMENTS -v

# With coverage
docker exec aprender_dev-web-1 pytest apps/core/tests/test_approval_policy_PA.py --cov=apps.core.services.solicitacao_create --cov=apps.core.views_solicitacao --cov-report=term-missing
```

### 2. Expected Results (5 mandatory tests)

#### PA-01: No Auto-Approval (SUPER Projects)
- [ ] `test_never_auto_approves_on_clean_or_save`

**Validates**:
- Solicitação with `projeto.fluxo == 'SUPER'` NEVER auto-approves
- Status remains 'pendente' after save/clean
- No auto-approval — decided in `resolve_initial_status()` (`apps/core/services/solicitacao_create.py`), not a model `save()`

**Note**: NAO_SUPER projects ARE auto-approved (tested in `test_solicitacao_fluxo.py`)

#### PA-02: Required Profile (only who has an approval basis)
- [ ] `test_only_superintendencia_can_approve_or_reject` (legacy name; parametrized over the `APROVADORAS` bases)
- [ ] `test_non_privileged_user_gets_403_on_approval_endpoint`

**Validates**:
- Policy permission `CanAccessSolicitationApprovals` (from `apps.core.rbac`) blocks non-authorized users
- 403 Forbidden for Coordenador/Formador on approve/reject endpoints
- Who approves/rejects: single rule `solicitation_approval_basis` (`apps/core/rbac/policies.py`) with 3 bases: `superuser`, `gerente_superintendencia` (EquipeGerencia GERENTE vigente in gerência `SUPERINTENDENCIA`) and `capacidade_aprovar` (`approve_solicitation` from the gerência profile package: ADMIN_OPERACIONAL of the DAT and CONTROLE, via EQUIPE/GERENTE vínculo). No group grants approval — a user with only the Superintendência group gets 403. See PA-02 in v2/docs/specs/domain/politica-aprovacao.spec.md
- Nobody approves/rejects their own solicitação (403 `self_approval_forbidden`, except superuser), and the rest of the segregation (`impedimentos` / `decisoes_impedidas` in `services/solicitacao_approval.py`: conta alterada, editada pelo ator) also blocks a decision
- The `gerente_superintendencia` base only decides projects of fluxo SUPER in gerência SUPERINTENDENCIA (`projeto_no_escopo_da_superintendencia`); outside that → 403 `out_of_approval_scope`. Superuser and `capacidade_aprovar` have no scope limit

#### PA-03: Post-Approval Triggers
- [ ] `test_calendar_integration_not_called_before_approval`

**Validates**:
- `task_publish_solicitacao_to_gcal` is NOT called during creation (service-layer flow, post-approval only)
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
from apps.core.models import EquipeGerencia
from apps.core.rbac.helpers import GERENCIA_APROVADORA_NOME

client = Client()

# Login as Coordenador (non-authorized)
# NOTE: groups.filter(name=) aqui e DIAGNOSTICO DE SHELL apenas. Em codigo de
# producao e BANIDO por scripts/rbac_lint.py — use HasPerm(...) / user_has_any_perm(...).
coordenador = Usuario.objects.filter(groups__name='Coordenador').first()
client.force_login(coordenador)

# Try to approve (should fail with 403) — approve/reject are PATCH (POST gives 405)
response = client.patch(f'/api/solicitacoes/{solicitacao.id}/approve/')
print(f"Response status: {response.status_code}")  # Should be 403
assert response.status_code == 403, "PA-02 VIOLATED: Non-authorized can approve!"

# Login as an approver chosen by VÍNCULO, not by group (no group grants approval):
# GERENTE vigente in gerência SUPERINTENDENCIA (base `gerente_superintendencia`).
# Must not be the solicitação's own author (403 self_approval_forbidden), and this base only
# decides projects of fluxo SUPER in gerência SUPERINTENDENCIA (else 403 out_of_approval_scope):
# the PA-01 `projeto_super` above has no gerência, so give it that gerência first.
vinculo = (
    EquipeGerencia.vigentes_em()
    .filter(papel='GERENTE', gerencia__nome=GERENCIA_APROVADORA_NOME)
    .exclude(usuario=solicitacao.usuario)
    .select_related('usuario')
    .first()
)
aprovador = vinculo.usuario
client.force_login(aprovador)

# Try to approve (should succeed with 200)
response = client.patch(f'/api/solicitacoes/{solicitacao.id}/approve/')
print(f"Response status: {response.status_code}")  # Should be 200
```

#### PA-05: Audit Log
```python
from apps.core.models import AuditLog

# Approve solicitacao
response = client.patch(f'/api/solicitacoes/{solicitacao.id}/approve/')

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

**File**: `v2/frontend/src/pages/Aprovacoes/ApprovalsPage.tsx`

Check:
- [ ] Component imports `getMe` from API
- [ ] `useEffect` calls `getMe()` on mount
- [ ] State `canApprove` is set based on the canonical rule:
  - single rule solicitation_approval_basis; see PA-02 in v2/docs/specs/domain/politica-aprovacao.spec.md (no group grants approval)
- [ ] Approve/Reject buttons only render if:
  - `record.status === 'pendente' && canApprove`

**Manual test**:
1. Login as Coordenador → Go to `/aprovacoes`
2. Verify Approve/Reject buttons are HIDDEN
3. Login as an approver (GERENTE vigente in gerência SUPERINTENDENCIA, or a DAT/Controle vínculo) → Go to `/aprovacoes`
4. Verify Approve/Reject buttons are VISIBLE

### 5. API Endpoint Testing

The API uses DRF `SessionAuthentication` (no Bearer token) and approve/reject are
`PATCH` actions. Log in through the browser/session first and send the session
cookie plus the CSRF token (`$SESSION_*` / `$CSRF_*` below come from that login).

```bash
# Test approve endpoint (as an approver: GERENTE vigente in SUPERINTENDENCIA, DAT or Controle vínculo)
curl -X PATCH "http://localhost:8002/api/solicitacoes/1/approve/" \
  -b "sessionid=$SESSION_APROVADOR; csrftoken=$CSRF_APROVADOR" \
  -H "X-CSRFToken: $CSRF_APROVADOR" \
  -H "Referer: http://localhost:8002/" \
  -H "Content-Type: application/json" \
  -d '{"justificativa": "Teste aprovação"}'

# Expected: 200 OK

# Test approve endpoint (as Coordenador)
curl -X PATCH "http://localhost:8002/api/solicitacoes/1/approve/" \
  -b "sessionid=$SESSION_COORDENADOR; csrftoken=$CSRF_COORDENADOR" \
  -H "X-CSRFToken: $CSRF_COORDENADOR" \
  -H "Referer: http://localhost:8002/" \
  -H "Content-Type: application/json" \
  -d '{"justificativa": "Teste aprovação"}'

# Expected: 403 Forbidden

# Test reject endpoint
curl -X PATCH "http://localhost:8002/api/solicitacoes/1/reject/" \
  -b "sessionid=$SESSION_APROVADOR; csrftoken=$CSRF_APROVADOR" \
  -H "X-CSRFToken: $CSRF_APROVADOR" \
  -H "Referer: http://localhost:8002/" \
  -H "Content-Type: application/json" \
  -d '{"justificativa": "Teste reprovação"}'

# Expected: 200 OK
```

In Python, prefer `APIClient().force_authenticate(user=...)` + `client.patch(...)`, as `test_approval_policy_PA.py` does.

### 6. Compliance Matrix

| Requisito | Implementação | Teste | Status |
|-----------|---------------|-------|--------|
| **PA-01** | `services/solicitacao_create.py:resolve_initial_status` (SUPER only) | `test_never_auto_approves_on_clean_or_save` | ✅ |
| **PA-02** | `rbac/policies.py:CanAccessSolicitationApprovals` → `solicitation_approval_basis` (superuser, gerente_superintendencia, capacidade_aprovar) | `test_only_superintendencia_can_approve_or_reject` (parametrized over `APROVADORAS`) | ✅ |
| **PA-03** | `views_solicitacao.py:approve()` (no task call) | `test_calendar_integration_not_called_before_approval` | ✅ |
| **PA-04** | `services/solicitacao_create.py` (SUPER → `pendente`) | Implicit in PA-01 test | ✅ |
| **PA-05** | `views_solicitacao.py` `approve()` / `reject()` actions | `test_approval_flow_records_audit_log` | ✅ |
| **PA-06** | `ApprovalsPage.tsx` (`canApprove` gate) | Manual UI test | ✅ |
| **PA-07** | All tests above | Run pytest | ✅ |

### 7. Output

**If all tests pass (5/5)**:
```
✅ PA-01 to PA-07 COMPLIANT
- PA-01: No auto-approval (SUPER) ✓
- PA-02: only who has a basis in solicitation_approval_basis (superuser, gerente_superintendencia, capacidade_aprovar) ✓
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
2. Check `apps/core/services/solicitacao_create.py:resolve_initial_status()`
3. Check `apps/core/views_solicitacao.py:approve()` and `reject()`
4. Verify `apps/core/rbac/policies.py:CanAccessSolicitationApprovals` (Policy on approve/reject `@action`)
5. Check AuditLog creation in approve/reject methods
```

### 8. Important Note: Manual Approval Does NOT Revalidate Conflicts

**Behavior**: The `approve()` endpoint **DOES NOT** call `check_conflicts()` before approving.

**Reason**: approvers' decisions (Superintendência gerente, DAT, Controle) include **human context** that the system cannot capture:
- Authorized exceptions
- Political/organizational priorities
- Municipality/project specific context
- Non-formalized negotiations

**Workflow**: the approver accesses `/disponibilidade` (grid view) and verifies **manually** before approving in `/aprovacoes`.

**System = decision support tool, NOT total automation.**

## Reference

- **Business Rules**: `.claude/skills/aprender-domain/SKILL.md` (PA-01 to PA-07)
- **Implementation**: `apps/core/views_solicitacao.py`, `apps/core/services/solicitacao_approval.py`, `apps/core/services/solicitacao_create.py`
- **Tests**: `apps/core/tests/test_approval_policy_PA.py`
- **Frontend**: `v2/frontend/src/pages/Aprovacoes/ApprovalsPage.tsx`

---

**Expected**: 5/5 PA-07 mandatory tests passing (test_approval_policy_PA.py; o arquivo tem 6 funcoes — 5 mandatorias PA-07 + 1 extra)

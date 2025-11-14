---
description: Test RF03 (RD-01 to RD-08) availability rules compliance
argument-hint: [optional: specific test or 'all']
---

# Check Conflicts — RF03 Compliance (RD-01 to RD-08)

Test availability rules: ${ARGUMENTS:-all}

## Approach:

### 1. Run Tests

```bash
# All RF03 tests (RD-01 to RD-08)
docker compose exec -T web pytest apps/core/tests/test_availability_service.py -v

# Specific test
docker compose exec -T web pytest apps/core/tests/test_availability_service.py::$ARGUMENTS -v

# With coverage
docker compose exec -T web pytest apps/core/tests/test_availability_service.py --cov=apps.core.services.availability_service --cov-report=term-missing
```

### 2. Expected Results (17 tests)

#### TestAvailabilityServiceRules (11 tests)
- [ ] `test_conflict_overlap_total` — RD-01 (overlap ≥ 1 min)
- [ ] `test_conflict_overlap_partial` — RD-01 (partial overlap)
- [ ] `test_no_conflict_adjacent_end_equals_start` — RD-01 (fim==início OK)
- [ ] `test_block_total_T_prevents_any_event` — RD-02 (bloqueio total)
- [ ] `test_block_partial_P_prevents_inside_allows_outside` — RD-03 (bloqueio parcial)
- [ ] `test_travel_buffer_between_cities_required` — RD-04 (deslocamento)
- [ ] `test_same_city_allows_zero_buffer` — RD-04 (mesmo município OK)
- [ ] `test_daily_capacity_M_exceeded` — RD-05 (capacidade diária)
- [ ] `test_multi_formador_any_conflict_blocks` — Multi-formador
- [ ] `test_timezone_aware_fortaleza_localtime` — RD-06 (timezone)
- [ ] `test_conflict_messages_include_codes_and_intervals` — RD-08 (mensagens)

#### TestAvailabilityCheckEndpoint (6 tests)
- [ ] `test_check_conflicts_requires_authentication` — Security
- [ ] `test_check_conflicts_missing_params_returns_400` — Validation
- [ ] `test_check_conflicts_returns_conflicts` — API structure
- [ ] `test_check_many_batch_processing` — Batch endpoint
- [ ] `test_check_conflicts_rbac_self_or_privileged` — RBAC
- [ ] `test_check_conflicts_structured_messages` — RD-08 (API)

### 3. Manual Validation

If tests fail, validate rules manually:

#### RD-01: Non-Overlapping
```python
# Shell test
from apps.core.services.availability_service import check_conflicts
from apps.core.models import Usuario, Municipio, Solicitacao
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

usuario = Usuario.objects.first()
municipio = Municipio.objects.first()
tz = ZoneInfo('America/Fortaleza')

# Create event 09:00-12:00
inicio1 = datetime(2025, 1, 15, 9, 0, tzinfo=tz)
fim1 = datetime(2025, 1, 15, 12, 0, tzinfo=tz)
Solicitacao.objects.create(
    usuario=usuario,
    municipio=municipio,
    inicio=inicio1,
    fim=fim1,
    status='aprovado'
)

# Test overlap 10:00-11:00 (should conflict)
inicio2 = datetime(2025, 1, 15, 10, 0, tzinfo=tz)
fim2 = datetime(2025, 1, 15, 11, 0, tzinfo=tz)
result = check_conflicts(usuario, inicio2, fim2, municipio)
print(f"Conflicts: {result.conflicts}")  # Should have 1 conflict

# Test adjacent 12:00-15:00 (should NOT conflict)
inicio3 = datetime(2025, 1, 15, 12, 0, tzinfo=tz)
fim3 = datetime(2025, 1, 15, 15, 0, tzinfo=tz)
result = check_conflicts(usuario, inicio3, fim3, municipio)
print(f"Conflicts: {result.conflicts}")  # Should be empty
```

#### RD-02: Total Block (T)
```python
from apps.core.models import AvailabilityBlock

# Create total block 09:00-17:00
AvailabilityBlock.objects.create(
    usuario=usuario,
    start_date=datetime(2025, 1, 15).date(),
    end_date=datetime(2025, 1, 15).date(),
    start_time=datetime.strptime('09:00', '%H:%M').time(),
    end_time=datetime.strptime('17:00', '%H:%M').time(),
    tipo='T',
    status='ativo'
)

# Test event 10:00-11:00 (should conflict with code 'X')
result = check_conflicts(usuario, inicio2, fim2, municipio)
print(f"Conflicts: {result.conflicts}")  # Should have code='X'
```

#### RD-04: Travel Buffer (D)
```python
# Create event in Fortaleza 09:00-12:00
municipio_fortaleza = Municipio.objects.get(nome='Fortaleza')
Solicitacao.objects.create(
    usuario=usuario,
    municipio=municipio_fortaleza,
    inicio=inicio1,
    fim=fim1,
    status='aprovado'
)

# Test event in Caucaia 12:30-15:00 (should conflict, buffer < 60 min)
municipio_caucaia = Municipio.objects.get(nome='Caucaia')
inicio4 = datetime(2025, 1, 15, 12, 30, tzinfo=tz)
fim4 = datetime(2025, 1, 15, 15, 0, tzinfo=tz)
result = check_conflicts(usuario, inicio4, fim4, municipio_caucaia)
print(f"Conflicts: {result.conflicts}")  # Should have code='D'
```

### 4. Conflict Codes Reference

| Code | Title | Description | Rule |
|------|-------|-------------|------|
| **E** | Evento aprovado | Single approved event | RD-01 |
| **M** | Mais de um evento | Daily capacity exceeded | RD-05 |
| **D** | Deslocamento necessário | Travel buffer required | RD-04 |
| **P** | Bloqueio parcial | Partial block | RD-03 |
| **T** | Bloqueio total | Total block | RD-02 |
| **X** | Conflito (evento + bloqueio) | Event + block overlap | RD-01 + RD-02/03 |

### 5. Priority Verification (RD-07)

Check order:
1. **Bloqueios** (T, P) — Highest priority
2. **Conflitos** (overlapping approved events)
3. **Buffer** (D) — Travel time
4. **Capacidade** (M) — Daily limit

Implementation: `apps/core/services/availability_service.py:check_conflicts()`

### 6. Timezone Validation (RD-06)

```python
# Verify UTC storage, America/Fortaleza comparison
from django.utils import timezone
from zoneinfo import ZoneInfo

solicitacao = Solicitacao.objects.first()
print(f"DB (UTC): {solicitacao.inicio}")
print(f"Local (Fortaleza): {solicitacao.inicio.astimezone(ZoneInfo('America/Fortaleza'))}")

# All comparisons MUST use America/Fortaleza
```

### 7. API Endpoint Testing

```bash
# Individual check
curl -X GET "http://localhost:8002/api/availability/check/?usuario_id=1&inicio=2025-01-15T09:00:00-03:00&fim=2025-01-15T12:00:00-03:00&municipio_id=1" \
  -H "Authorization: Bearer $TOKEN"

# Batch check
curl -X POST "http://localhost:8002/api/availability/check-many/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "checks": [
      {"usuario_id": 1, "inicio": "2025-01-15T09:00:00-03:00", "fim": "2025-01-15T12:00:00-03:00", "municipio_id": 1},
      {"usuario_id": 2, "inicio": "2025-01-15T10:00:00-03:00", "fim": "2025-01-15T11:00:00-03:00", "municipio_id": 2}
    ]
  }'
```

### 8. Output

**If all tests pass (17/17)**:
```
✅ RF03 COMPLIANT (RD-01 to RD-08)
- 11 business rules tests passing
- 6 API endpoint tests passing
- Total: 17/17 tests

All availability rules validated:
✓ RD-01: Non-overlapping
✓ RD-02: Total block (T)
✓ RD-03: Partial block (P)
✓ RD-04: Travel buffer (D)
✓ RD-05: Daily capacity (M)
✓ RD-06: Timezone-aware
✓ RD-07: Priority enforcement
✓ RD-08: Structured messages
```

**If tests fail**:
```
❌ RF03 NON-COMPLIANT
Failed tests: N/17

[List failed tests with details]

Next steps:
1. Review failure logs
2. Check `apps/core/services/availability_service.py`
3. Verify test fixtures in `apps/core/tests/test_availability_service.py`
4. Validate RD-01 to RD-08 implementation
```

## Reference

- **Business Rules**: `.claude/skills/aprender-domain/SKILL.md` (RD-01 to RD-08)
- **Implementation**: `apps/core/services/availability_service.py`
- **Tests**: `apps/core/tests/test_availability_service.py`
- **API**: `apps/core/views_availability.py`

---

**Expected**: 17/17 tests passing (PR16 baseline)

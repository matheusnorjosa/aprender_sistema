---
description: Run ETL in apply mode (commit changes to database)
argument-hint: [etl command name]
---

# ETL Apply — Commit Import

Run ETL in apply mode: $ARGUMENTS

## ⚠️ IMPORTANT: Pre-Requisites

**NEVER run apply mode without completing dry-run first!**

### Mandatory Checklist

- [ ] **Dry-run completed**: `docker compose exec web python manage.py $ARGUMENTS` (without --apply)
- [ ] **Report reviewed**: Check `out_etl/{command}_{timestamp}.json`
- [ ] **Quality gates**: ALL PASS (duplicates <5%, invalid <10%)
- [ ] **Errors**: Zero critical errors
- [ ] **Database backup**: Created (see step 1)
- [ ] **Apply mode approved**: By project lead or data steward

**If ANY item is unchecked, STOP and run dry-run first.**

## Approach:

### 1. Backup Database (CRITICAL)

**Before ANY apply operation**:
```bash
# Backup PostgreSQL
docker compose exec db pg_dump -U postgres aprender_v2 > backup_$(date +%Y%m%d_%H%M%S).sql

# Verify backup
ls -lh backup_*.sql
```

**Restoration** (if needed):
```bash
# Restore from backup
docker compose exec -T db psql -U postgres aprender_v2 < backup_20250115_103000.sql
```

### 2. Apply Execution

**Command structure**:
```bash
docker compose exec web python manage.py $ARGUMENTS --apply
```

**Examples**:
```bash
# Acompanhamento
docker compose exec web python manage.py etl_upsert_acompanhamento --apply

# Deslocamento
docker compose exec web python manage.py etl_upsert_deslocamento --apply

# Ações Controle
docker compose exec web python manage.py etl_import_acoes_controle --apply

# Cadastros DAT
docker compose exec web python manage.py etl_import_cadastros_dat --apply
```

### 3. Monitor Execution

**Watch for**:
- Progress indicators (% complete)
- Warning messages (skipped rows)
- Error messages (should be ZERO if dry-run passed)
- Final summary

**Example output**:
```
Processing Acompanhamento ETL (APPLY MODE)
========================================
Source: data/csv-import/Acompanhamento de Agenda _ 2025.xlsx

Tab: ACerta
  - Rows processed: 250/250 (100%)
  - Inserts: 120
  - Updates: 125
  - Skipped (duplicates): 5

Tab: Outros
  - Rows processed: 180/180 (100%)
  - Inserts: 90
  - Updates: 85
  - Skipped (duplicates): 5

...

SUMMARY
=======
Total rows: 1250
Inserts: 600
Updates: 575
Skipped: 25
Errors: 0

✅ ETL COMPLETED SUCCESSFULLY
Report: out_etl/acompanhamento_20250115_103000_APPLY.json
```

### 4. Validate Results

**Database verification**:
```python
# Django shell
docker compose exec web python manage.py shell

from apps.core.models import Solicitacao, Participacao
from datetime import date

# Check total count
print(f"Total Solicitações: {Solicitacao.objects.count()}")

# Check recent imports (by external_hash presence)
imported = Solicitacao.objects.exclude(external_hash='').count()
print(f"Imported from ETL: {imported}")

# Check date range
latest = Solicitacao.objects.order_by('-inicio').first()
print(f"Latest event: {latest.inicio} - {latest.projeto.nome}")

# Check participants
participacoes = Participacao.objects.count()
print(f"Total Participações: {participacoes}")
```

**Quality checks**:
```bash
# Run tests to verify data integrity
docker compose exec web pytest apps/core/tests/test_models.py -v
docker compose exec web pytest apps/core/tests/test_solicitacao_fluxo.py -v
```

### 5. Idempotence Verification

**Test re-running apply (should be safe)**:
```bash
# Re-run same ETL (should skip all existing)
docker compose exec web python manage.py etl_upsert_acompanhamento --apply

# Expected output:
# Total rows: 1250
# Inserts: 0
# Updates: 0 (or minimal if data changed)
# Skipped: 1250 (all duplicates via external_hash)
```

**Verify external_hash**:
```python
from apps.core.models import Solicitacao

# Check hash consistency
duplicates = Solicitacao.objects.values('external_hash').annotate(
    count=models.Count('id')
).filter(count__gt=1)

print(f"Duplicate hashes: {duplicates.count()}")  # Should be 0
```

### 6. Rollback (If Needed)

**If apply fails or produces unexpected results**:
```bash
# Stop services
docker compose down

# Restore database
docker compose up -d db
docker compose exec -T db psql -U postgres aprender_v2 < backup_20250115_103000.sql

# Restart services
docker compose up -d
```

### 7. Post-Apply Checklist

- [ ] **Inserts**: Match dry-run prediction
- [ ] **Updates**: Match dry-run prediction
- [ ] **Skipped**: Match dry-run duplicates count
- [ ] **Errors**: Zero errors
- [ ] **Tests**: All passing
- [ ] **Idempotence**: Re-run produces zero inserts
- [ ] **Report**: Saved in `out_etl/` with `_APPLY` suffix
- [ ] **Backup**: Retained for 30 days

### 8. ETL-Specific Post-Validation

#### Acompanhamento (Events + Participants)
```python
# Verify Solicitacao + Participacao creation
from apps.core.models import Solicitacao, Participacao

# Count by projeto
from django.db.models import Count
Solicitacao.objects.values('projeto__nome').annotate(count=Count('id')).order_by('-count')

# Verify participants
Participacao.objects.filter(
    solicitacao__external_hash__isnull=False
).count()

# Check SUPER vs NAO_SUPER auto-approval
super_pendente = Solicitacao.objects.filter(
    projeto__fluxo='SUPER',
    status='pendente'
).count()

nao_super_aprovado = Solicitacao.objects.filter(
    projeto__fluxo='NAO_SUPER',
    status='aprovado'
).count()

print(f"SUPER pendente: {super_pendente}")
print(f"NAO_SUPER aprovado: {nao_super_aprovado}")
```

#### Deslocamento (Travel)
```python
from apps.core.models import Deslocamento

# Verify travel records
Deslocamento.objects.filter(external_hash__isnull=False).count()

# Check origem/destino distribution
Deslocamento.objects.values('origem__nome', 'destino__nome').annotate(
    count=Count('id')
).order_by('-count')
```

#### Ações Controle
```python
from apps.core.models import AcaoControle

# Verify Controle actions
AcaoControle.objects.filter(external_hash__isnull=False).count()

# Check status distribution
AcaoControle.objects.values('status').annotate(count=Count('id'))
```

#### Cadastros DAT
```python
from apps.core.models import CadastroDAT

# Verify DAT registry
CadastroDAT.objects.filter(external_hash__isnull=False).count()

# Check CPF uniqueness
duplicates = CadastroDAT.objects.values('cpf').annotate(
    count=Count('id')
).filter(count__gt=1)

print(f"Duplicate CPFs: {duplicates.count()}")  # Should be 0
```

### 9. Output Report

**File**: `out_etl/{command}_{timestamp}_APPLY.json`

**Content** (same structure as dry-run, with `mode: "apply"`):
```json
{
  "command": "etl_upsert_acompanhamento",
  "timestamp": "2025-01-15T10:35:00-03:00",
  "mode": "apply",
  "source_file": "data/csv-import/Acompanhamento de Agenda _ 2025.xlsx",
  "summary": {
    "total_rows": 1250,
    "valid_rows": 1200,
    "invalid_rows": 0,
    "duplicates_skipped": 25,
    "new_inserts": 600,
    "existing_updates": 575
  },
  "quality_gates": {
    "ETL_MAX_DUPLICATES_PCT": {"status": "PASS"},
    "ETL_MAX_INVALID_PCT": {"status": "PASS"}
  },
  "errors": [],
  "database_changes": {
    "inserts": 600,
    "updates": 575,
    "deletes": 0
  }
}
```

### 10. Output

**If apply successful**:
```
✅ ETL APPLY SUCCESSFUL
Command: $ARGUMENTS --apply
Report: out_etl/{command}_{timestamp}_APPLY.json

Database Changes:
- Inserts: 600
- Updates: 575
- Deletes: 0

Post-validation:
- Tests: ALL PASSING
- Idempotence: VERIFIED (re-run = 0 inserts)
- Data integrity: VALID

Backup retained: backup_20250115_103000.sql
```

**If apply failed**:
```
❌ ETL APPLY FAILED
Command: $ARGUMENTS --apply

Error: [Error message]

ROLLBACK INITIATED
1. Stopping services
2. Restoring database from backup_20250115_103000.sql
3. Restarting services

Status: Database restored to pre-apply state.
Next step: Review error, fix source data, retry dry-run.
```

## Reference

- **ETL Guidelines**: `.claude/skills/etl-guidelines/SKILL.md` (when created)
- **Commands**: `apps/dat_ingest/management/commands/`
- **Dry-Run**: `.claude/commands/etl-dry.md`
- **Quality Gates**: `config/settings.py`

---

**Focus**: Safely commit ETL changes with validation, idempotence, and rollback capability.

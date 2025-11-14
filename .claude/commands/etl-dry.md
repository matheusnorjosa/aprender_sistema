---
description: Run ETL in dry-run mode (preview only, no database changes)
argument-hint: [etl command name]
---

# ETL Dry-Run — Preview Import

Run ETL in preview mode: $ARGUMENTS

## Approach:

### 1. Available ETL Commands

```bash
# Acompanhamento (events + participants)
docker compose exec web python manage.py etl_upsert_acompanhamento

# Deslocamento (travel records)
docker compose exec web python manage.py etl_upsert_deslocamento

# Ações Controle (Controle actions)
docker compose exec web python manage.py etl_import_acoes_controle

# Cadastros DAT (DAT registry)
docker compose exec web python manage.py etl_import_cadastros_dat

# Compras (purchases, CSV/XLSX upload)
# Via API POST /api/controle/compras/upload/ (dry_run parameter)
```

### 2. Dry-Run Execution

**Default behavior**: All ETL commands run in **dry-run** mode by default.
- Reads source files
- Validates data
- Generates report in `out_etl/`
- **DOES NOT** modify database

**Example**:
```bash
# Dry-run Acompanhamento (default)
docker compose exec web python manage.py etl_upsert_acompanhamento

# Generates: v2/backend/out_etl/acompanhamento_YYYYMMDD_HHMMSS.json
```

### 3. Output Report Structure

**File**: `out_etl/{command}_{timestamp}.json`

**Content**:
```json
{
  "command": "etl_upsert_acompanhamento",
  "timestamp": "2025-01-15T10:30:00-03:00",
  "mode": "dry_run",
  "source_file": "data/csv-import/Acompanhamento de Agenda _ 2025.xlsx",
  "summary": {
    "total_rows": 1250,
    "valid_rows": 1200,
    "invalid_rows": 50,
    "duplicates_skipped": 25,
    "new_inserts": 600,
    "existing_updates": 575
  },
  "quality_gates": {
    "ETL_MAX_DUPLICATES_PCT": {
      "threshold": 0.05,
      "actual": 0.02,
      "status": "PASS"
    },
    "ETL_MAX_INVALID_PCT": {
      "threshold": 0.10,
      "actual": 0.04,
      "status": "PASS"
    }
  },
  "errors": [
    {
      "row": 42,
      "field": "inicio",
      "error": "Invalid datetime format",
      "value": "2025-01-XX"
    }
  ],
  "warnings": [
    {
      "row": 105,
      "field": "municipio",
      "warning": "Municipality not found",
      "value": "Cidade Nova"
    }
  ]
}
```

### 4. Quality Gates Validation

**Thresholds** (`config/settings.py`):
```python
ETL_MAX_DUPLICATES_PCT = 0.05  # 5% max duplicates
ETL_MAX_INVALID_PCT = 0.10     # 10% max invalid rows
```

**Check**:
- [ ] Duplicates < 5% (via `external_hash` SHA1/SHA256)
- [ ] Invalid rows < 10%
- [ ] All quality gates status = "PASS"

**If quality gate fails**:
```
❌ QUALITY GATE FAILED
- ETL_MAX_DUPLICATES_PCT: 0.12 > 0.05 (FAIL)

ETL will NOT proceed in apply mode.
Fix source data and retry.
```

### 5. Idempotence Verification

**Mechanism**: `external_hash` field (SHA1 or SHA256)
- Generated from source row data
- Used for `get_or_create()` logic
- Prevents duplicate inserts

**Check**:
```json
{
  "summary": {
    "total_rows": 100,
    "duplicates_skipped": 25,  // Already in DB
    "new_inserts": 50,          // Will be created
    "existing_updates": 25      // Will be updated
  }
}
```

### 6. Error Analysis

**Common errors**:
- **Invalid datetime**: Fix format in source (YYYY-MM-DD HH:MM:SS)
- **Missing FK**: Create referenced entity first (Municipio, Projeto, Usuario)
- **Constraint violation**: Check DB constraints (UNIQUE, CHECK)
- **Encoding**: UTF-8 BOM issues (convert to UTF-8)

**Example fix**:
```
Error: Municipality not found "Cidade Nova"
Fix: Add to Municipio table or fix typo in source ("Cidade Nova" → "Caucaia")
```

### 7. Dry-Run Checklist

Before running apply mode:
- [ ] **Quality gates**: All PASS
- [ ] **Errors**: Zero critical errors
- [ ] **Warnings**: Reviewed and acceptable
- [ ] **Duplicates**: Within threshold (<5%)
- [ ] **Invalid rows**: Within threshold (<10%)
- [ ] **FK references**: All exist in DB
- [ ] **Source file**: Latest version
- [ ] **Timezone**: America/Fortaleza consistent

### 8. Next Steps

**If dry-run successful**:
```bash
# Proceed to apply mode (see /etl-apply command)
docker compose exec web python manage.py etl_upsert_acompanhamento --apply
```

**If dry-run failed**:
1. Review errors in `out_etl/*.json`
2. Fix source data
3. Re-run dry-run
4. Repeat until quality gates pass

### 9. ETL-Specific Guidelines

#### Acompanhamento (Events + Participants)
- **Source**: `data/csv-import/Acompanhamento de Agenda _ 2025.xlsx`
- **Tabs**: ACerta, Outros, Super, Brincando, Vidas
- **Hash**: SHA256 (projeto, municipio, tipo, data, inicio, fim, formadores)
- **Relations**: Creates Solicitacao + Participacao (M2M)

#### Deslocamento (Travel)
- **Source**: `data/csv-import/Deslocamento.xlsx`
- **Hash**: SHA1 (usuario, data, origem, destino)
- **Idempotence**: Skip if external_hash exists

#### Ações Controle (Controle Actions)
- **Source**: `data/csv-import/Planilha de Controle - 2025.xlsx` (tab "🟥 AÇÕES")
- **Hash**: SHA256 (projeto, tipo, data, responsavel, status)
- **Output**: Report in `out_etl/acoes_controle_*.json`

#### Cadastros DAT (DAT Registry)
- **Source**: `data/csv-import/Planilha de Controle - 2025.xlsx` (tab "☑️ CADASTROS")
- **Hash**: SHA1 (nome, cpf, email)
- **Validation**: CPF format, email unique

### 10. Output

**If dry-run successful**:
```
✅ DRY-RUN SUCCESSFUL
Command: $ARGUMENTS
Report: out_etl/{command}_{timestamp}.json

Summary:
- Total rows: 1250
- Valid rows: 1200 (96%)
- Duplicates: 25 (2%)
- New inserts: 600
- Existing updates: 575

Quality Gates: ALL PASS

Next step: Run with --apply flag to commit changes.
```

**If dry-run failed**:
```
❌ DRY-RUN FAILED
Command: $ARGUMENTS

Errors found: 50
Warnings: 15

Quality Gates:
- ETL_MAX_DUPLICATES_PCT: PASS
- ETL_MAX_INVALID_PCT: FAIL (actual: 0.12 > 0.10)

Fix errors and retry. See out_etl/{command}_{timestamp}.json for details.
```

## Reference

- **ETL Guidelines**: `.claude/skills/etl-guidelines/SKILL.md` (when created)
- **Commands**: `apps/dat_ingest/management/commands/`
- **Quality Gates**: `config/settings.py`
- **Idempotence**: `apps/core/models.py` (external_hash fields)

---

**Focus**: Preview import, validate quality gates, identify errors before applying changes.

---
name: etl-guidelines
description: ETL development guidelines for AS v2. Use when creating data import commands, ensuring idempotence, implementing quality gates, and handling CSV/XLSX imports. Covers dry-run/apply patterns, error handling, and rollback strategies.
---

# ETL Guidelines — Aprender Sistema v2

## 🎯 Purpose

This skill provides ETL (Extract, Transform, Load) implementation patterns for Aprender Sistema v2. Use this when:
- Creating new data import commands
- Implementing idempotence via external_hash
- Setting up quality gates
- Handling CSV/XLSX imports
- Implementing dry-run/apply pattern
- Writing error reports

---

## 📋 Quick Reference

| Task | Pattern | Example |
|------|---------|---------|
| **Command** | Django management command | `etl_upsert_acompanhamento.py` |
| **Idempotence** | external_hash SHA1/SHA256 | `get_or_create(external_hash=...)` |
| **Quality Gates** | Thresholds validation | Duplicates <5%, Invalid <10% |
| **Dry-run** | Preview without DB changes | Default behavior |
| **Apply** | Commit with --apply flag | Requires dry-run first |
| **Report** | JSON in out_etl/ | `{command}_{timestamp}.json` |
| **Rollback** | pg_dump before apply | Restore if needed |

---

## 🔧 Management Command Template

### File Structure

```
apps/dat_ingest/management/commands/
├── __init__.py
├── etl_upsert_acompanhamento.py
├── etl_upsert_deslocamento.py
├── etl_import_acoes_controle.py
└── etl_import_cadastros_dat.py
```

### Command Template

```python
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.conf import settings
from apps.core.models import Solicitacao, Usuario, Municipio, Projeto
import pandas as pd
import hashlib
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo


class Command(BaseCommand):
    help = 'Import Acompanhamento data from XLSX (idempotent via external_hash)'

    def add_arguments(self, parser):
        """
        Add command arguments.

        --apply: Commit changes to DB (default: dry-run)
        --source: Custom source file path
        """
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Apply changes to database (default: dry-run only)'
        )
        parser.add_argument(
            '--source',
            type=str,
            default='data/csv-import/Acompanhamento de Agenda _ 2025.xlsx',
            help='Source file path'
        )

    def handle(self, *args, **options):
        """
        Main command handler.

        Workflow:
        1. Load and validate source file
        2. Transform data (parse, validate, generate external_hash)
        3. Quality gates check
        4. Load (dry-run or apply)
        5. Generate report
        """
        apply_mode = options['apply']
        source_path = Path(settings.BASE_DIR) / options['source']

        self.stdout.write(
            self.style.WARNING(
                f"{'APPLY MODE' if apply_mode else 'DRY-RUN MODE'}"
            )
        )

        # Initialize report
        report = {
            'command': 'etl_upsert_acompanhamento',
            'timestamp': datetime.now(ZoneInfo('America/Fortaleza')).isoformat(),
            'mode': 'apply' if apply_mode else 'dry_run',
            'source_file': str(source_path),
            'summary': {
                'total_rows': 0,
                'valid_rows': 0,
                'invalid_rows': 0,
                'duplicates_skipped': 0,
                'new_inserts': 0,
                'existing_updates': 0
            },
            'quality_gates': {},
            'errors': [],
            'warnings': []
        }

        try:
            # 1. Extract
            raw_data = self._extract(source_path)
            report['summary']['total_rows'] = len(raw_data)

            # 2. Transform
            transformed_data = self._transform(raw_data, report)

            # 3. Quality Gates
            self._check_quality_gates(report)

            # 4. Load (dry-run or apply)
            if apply_mode:
                self._load_apply(transformed_data, report)
            else:
                self._load_dryrun(transformed_data, report)

            # 5. Report
            self._write_report(report, apply_mode)

            # Summary
            self._print_summary(report, apply_mode)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
            raise CommandError(f"ETL failed: {e}")

    def _extract(self, source_path: Path) -> pd.DataFrame:
        """
        Extract data from source file.

        Returns:
            DataFrame with raw data
        """
        if not source_path.exists():
            raise CommandError(f"Source file not found: {source_path}")

        # Read XLSX (or CSV)
        if source_path.suffix == '.xlsx':
            # Read specific sheet
            df = pd.read_excel(source_path, sheet_name='ACerta')
        elif source_path.suffix == '.csv':
            df = pd.read_csv(source_path, encoding='utf-8')
        else:
            raise CommandError(f"Unsupported file type: {source_path.suffix}")

        self.stdout.write(f"Extracted {len(df)} rows from {source_path.name}")
        return df

    def _transform(self, df: pd.DataFrame, report: dict) -> list:
        """
        Transform raw data into validated records.

        Returns:
            List of dicts ready for load
        """
        transformed = []

        for idx, row in df.iterrows():
            try:
                # Parse row
                record = self._parse_row(row)

                # Validate
                errors = self._validate_record(record)
                if errors:
                    report['errors'].append({
                        'row': idx + 2,  # Excel row (1-indexed + header)
                        'errors': errors
                    })
                    report['summary']['invalid_rows'] += 1
                    continue

                # Generate external_hash (idempotence)
                record['external_hash'] = self._generate_hash(record)

                transformed.append(record)
                report['summary']['valid_rows'] += 1

            except Exception as e:
                report['errors'].append({
                    'row': idx + 2,
                    'error': str(e)
                })
                report['summary']['invalid_rows'] += 1

        return transformed

    def _parse_row(self, row: pd.Series) -> dict:
        """
        Parse single row into structured dict.

        Returns:
            Dict with parsed fields
        """
        from zoneinfo import ZoneInfo

        tz = ZoneInfo('America/Fortaleza')

        # Parse dates (handle multiple formats)
        data_str = str(row['Data'])
        if pd.notna(data_str):
            data = pd.to_datetime(data_str, format='%d/%m/%Y').date()
        else:
            raise ValueError("Data is required")

        # Parse times
        inicio_str = str(row['Início'])
        fim_str = str(row['Fim'])

        inicio = datetime.combine(data, pd.to_datetime(inicio_str, format='%H:%M').time())
        fim = datetime.combine(data, pd.to_datetime(fim_str, format='%H:%M').time())

        # Make timezone-aware
        inicio = inicio.replace(tzinfo=tz)
        fim = fim.replace(tzinfo=tz)

        return {
            'projeto_nome': str(row['Projeto']),
            'municipio_nome': str(row['Município']),
            'tipo_nome': str(row['Tipo']),
            'inicio': inicio,
            'fim': fim,
            'formadores': [str(row['Formador 1']), str(row['Formador 2'])],
            'observacao': str(row.get('Observação', ''))
        }

    def _validate_record(self, record: dict) -> list:
        """
        Validate single record.

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        # Required fields
        if not record.get('projeto_nome'):
            errors.append("Projeto is required")

        if not record.get('municipio_nome'):
            errors.append("Município is required")

        # Time range
        if record['fim'] <= record['inicio']:
            errors.append("Fim must be after Início")

        # Foreign key existence
        if not Projeto.objects.filter(nome=record['projeto_nome']).exists():
            errors.append(f"Projeto not found: {record['projeto_nome']}")

        if not Municipio.objects.filter(nome=record['municipio_nome']).exists():
            errors.append(f"Município not found: {record['municipio_nome']}")

        return errors

    def _generate_hash(self, record: dict) -> str:
        """
        Generate external_hash for idempotence.

        Strategy:
        - Use fields that uniquely identify the record
        - SHA256 for collision resistance
        - Deterministic (same input = same hash)

        Returns:
            SHA256 hex digest
        """
        hash_input = '|'.join([
            record['projeto_nome'],
            record['municipio_nome'],
            record['tipo_nome'],
            record['inicio'].isoformat(),
            record['fim'].isoformat(),
            '|'.join(sorted(record['formadores']))  # Sorted for consistency
        ])

        return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()

    def _check_quality_gates(self, report: dict) -> None:
        """
        Validate quality gates.

        Gates:
        - ETL_MAX_DUPLICATES_PCT: Max % of duplicates (default: 5%)
        - ETL_MAX_INVALID_PCT: Max % of invalid rows (default: 10%)

        Raises:
            CommandError if any gate fails
        """
        total = report['summary']['total_rows']
        duplicates = report['summary']['duplicates_skipped']
        invalid = report['summary']['invalid_rows']

        # Gate 1: Duplicates
        max_dup_pct = getattr(settings, 'ETL_MAX_DUPLICATES_PCT', 0.05)
        dup_pct = duplicates / total if total > 0 else 0

        report['quality_gates']['ETL_MAX_DUPLICATES_PCT'] = {
            'threshold': max_dup_pct,
            'actual': dup_pct,
            'status': 'PASS' if dup_pct <= max_dup_pct else 'FAIL'
        }

        # Gate 2: Invalid
        max_inv_pct = getattr(settings, 'ETL_MAX_INVALID_PCT', 0.10)
        inv_pct = invalid / total if total > 0 else 0

        report['quality_gates']['ETL_MAX_INVALID_PCT'] = {
            'threshold': max_inv_pct,
            'actual': inv_pct,
            'status': 'PASS' if inv_pct <= max_inv_pct else 'FAIL'
        }

        # Check if any gate failed
        failed_gates = [
            name for name, gate in report['quality_gates'].items()
            if gate['status'] == 'FAIL'
        ]

        if failed_gates:
            self.stdout.write(self.style.ERROR(f"Quality gates FAILED: {failed_gates}"))
            raise CommandError(f"Quality gates failed: {failed_gates}")

    def _load_dryrun(self, records: list, report: dict) -> None:
        """
        Dry-run: Check what would happen without DB changes.

        Simulates get_or_create() to count inserts/updates.
        """
        for record in records:
            # Check if exists
            exists = Solicitacao.objects.filter(
                external_hash=record['external_hash']
            ).exists()

            if exists:
                report['summary']['duplicates_skipped'] += 1
            else:
                report['summary']['new_inserts'] += 1

        self.stdout.write(self.style.SUCCESS("Dry-run completed (no DB changes)"))

    @transaction.atomic
    def _load_apply(self, records: list, report: dict) -> None:
        """
        Apply: Commit changes to database.

        Uses transaction.atomic() for rollback on error.
        """
        for record in records:
            # Resolve foreign keys
            projeto = Projeto.objects.get(nome=record['projeto_nome'])
            municipio = Municipio.objects.get(nome=record['municipio_nome'])
            tipo = TipoEvento.objects.get(nome=record['tipo_nome'])

            # Get or create (idempotent)
            solicitacao, created = Solicitacao.objects.get_or_create(
                external_hash=record['external_hash'],
                defaults={
                    'projeto': projeto,
                    'municipio': municipio,
                    'tipo': tipo,
                    'inicio': record['inicio'],
                    'fim': record['fim'],
                    'observacao': record['observacao'],
                    'status': 'aprovado' if projeto.fluxo == 'NAO_SUPER' else 'pendente'
                }
            )

            if created:
                report['summary']['new_inserts'] += 1
            else:
                report['summary']['duplicates_skipped'] += 1

            # Add M2M (participacoes)
            for formador_nome in record['formadores']:
                if pd.notna(formador_nome) and formador_nome:
                    formador = Usuario.objects.get(nome=formador_nome)
                    Participacao.objects.get_or_create(
                        solicitacao=solicitacao,
                        usuario=formador
                    )

        self.stdout.write(self.style.SUCCESS("Apply completed (DB updated)"))

    def _write_report(self, report: dict, apply_mode: bool) -> None:
        """
        Write JSON report to out_etl/.

        File format: {command}_{timestamp}_[APPLY].json
        """
        out_dir = Path(settings.BASE_DIR) / 'out_etl'
        out_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        suffix = '_APPLY' if apply_mode else ''
        filename = f"{report['command']}_{timestamp}{suffix}.json"

        report_path = out_dir / filename

        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        self.stdout.write(f"Report saved: {report_path}")

    def _print_summary(self, report: dict, apply_mode: bool) -> None:
        """
        Print summary to stdout.
        """
        summary = report['summary']

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(f"ETL SUMMARY ({'APPLY' if apply_mode else 'DRY-RUN'})")
        self.stdout.write("=" * 50)

        self.stdout.write(f"Total rows: {summary['total_rows']}")
        self.stdout.write(f"Valid rows: {summary['valid_rows']}")
        self.stdout.write(f"Invalid rows: {summary['invalid_rows']}")
        self.stdout.write(f"Duplicates skipped: {summary['duplicates_skipped']}")
        self.stdout.write(f"New inserts: {summary['new_inserts']}")

        # Quality gates
        self.stdout.write("\nQuality Gates:")
        for name, gate in report['quality_gates'].items():
            status_style = self.style.SUCCESS if gate['status'] == 'PASS' else self.style.ERROR
            self.stdout.write(
                status_style(f"  {name}: {gate['status']} ({gate['actual']:.2%} <= {gate['threshold']:.2%})")
            )

        # Errors summary
        if report['errors']:
            self.stdout.write(self.style.WARNING(f"\nErrors: {len(report['errors'])}"))
            for error in report['errors'][:5]:  # Show first 5
                self.stdout.write(f"  Row {error['row']}: {error.get('error', error.get('errors'))}")

        self.stdout.write("=" * 50 + "\n")
```

---

## 🔑 Idempotence Patterns

### 1. external_hash Strategy

**Purpose**: Ensure the same source data doesn't create duplicates on re-run.

**Implementation**:
```python
def _generate_hash(self, record: dict) -> str:
    """
    Generate deterministic hash for idempotence.

    Rules:
    - Include all fields that uniquely identify the record
    - Use consistent ordering (sorted lists)
    - Use consistent formatting (isoformat for dates)
    - SHA256 for collision resistance
    """
    hash_input = '|'.join([
        record['projeto_nome'],
        record['municipio_nome'],
        record['tipo_nome'],
        record['inicio'].isoformat(),
        record['fim'].isoformat(),
        '|'.join(sorted(record['formadores']))  # Sorted!
    ])

    return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
```

### 2. get_or_create Pattern

```python
# Idempotent insert
solicitacao, created = Solicitacao.objects.get_or_create(
    external_hash=record['external_hash'],
    defaults={
        'projeto': projeto,
        'municipio': municipio,
        # ... other fields
    }
)

if created:
    report['summary']['new_inserts'] += 1
else:
    report['summary']['duplicates_skipped'] += 1
```

### 3. update_or_create Pattern

```python
# Idempotent upsert (update existing)
solicitacao, created = Solicitacao.objects.update_or_create(
    external_hash=record['external_hash'],
    defaults={
        'projeto': projeto,
        'municipio': municipio,
        'inicio': record['inicio'],
        'fim': record['fim'],
        # ... all updatable fields
    }
)

if created:
    report['summary']['new_inserts'] += 1
else:
    report['summary']['existing_updates'] += 1
```

---

## 📊 Quality Gates

### Configuration (settings.py)

```python
# Quality gate thresholds
ETL_MAX_DUPLICATES_PCT = 0.05  # 5% max duplicates
ETL_MAX_INVALID_PCT = 0.10     # 10% max invalid rows
```

### Validation Logic

```python
def _check_quality_gates(self, report: dict) -> None:
    """
    Validate quality gates and fail if thresholds exceeded.

    Gates:
    1. Duplicates: Max % of rows that are duplicates
    2. Invalid: Max % of rows that fail validation

    Raises:
        CommandError if any gate fails
    """
    total = report['summary']['total_rows']

    # Gate 1: Duplicates
    dup_pct = report['summary']['duplicates_skipped'] / total
    max_dup_pct = settings.ETL_MAX_DUPLICATES_PCT

    if dup_pct > max_dup_pct:
        raise CommandError(
            f"Quality gate failed: Duplicates {dup_pct:.2%} > {max_dup_pct:.2%}"
        )

    # Gate 2: Invalid
    inv_pct = report['summary']['invalid_rows'] / total
    max_inv_pct = settings.ETL_MAX_INVALID_PCT

    if inv_pct > max_inv_pct:
        raise CommandError(
            f"Quality gate failed: Invalid {inv_pct:.2%} > {max_inv_pct:.2%}"
        )
```

---

## 📝 Report Format

### JSON Structure

```json
{
  "command": "etl_upsert_acompanhamento",
  "timestamp": "2025-01-15T10:30:00-03:00",
  "mode": "apply",
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
  ],
  "database_changes": {
    "inserts": 600,
    "updates": 575,
    "deletes": 0
  }
}
```

---

## 🔄 Dry-Run vs Apply Pattern

### Decision Flow

```
1. Always run dry-run first
   ↓
2. Review report in out_etl/
   ↓
3. Quality gates PASS?
   ├─ NO → Fix source data, retry
   └─ YES → Continue
   ↓
4. Create database backup
   ↓
5. Run apply mode
   ↓
6. Validate results
   ├─ Success → Keep changes
   └─ Failure → Rollback from backup
```

### Commands

```bash
# Step 1: Dry-run (default)
docker compose exec web python manage.py etl_upsert_acompanhamento

# Step 2: Review report
cat out_etl/etl_upsert_acompanhamento_20250115_103000.json

# Step 3: Backup
docker compose exec db pg_dump -U postgres aprender_v2 > backup_20250115.sql

# Step 4: Apply
docker compose exec web python manage.py etl_upsert_acompanhamento --apply

# Step 5 (if needed): Rollback
docker compose exec -T db psql -U postgres aprender_v2 < backup_20250115.sql
```

---

## 🛡️ Error Handling

### Validation Errors

```python
def _validate_record(self, record: dict) -> list:
    """
    Validate record and collect all errors.

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Required fields
    if not record.get('projeto_nome'):
        errors.append("Projeto is required")

    # Format validation
    try:
        inicio = pd.to_datetime(record['inicio'])
    except Exception as e:
        errors.append(f"Invalid inicio format: {e}")

    # Business logic validation
    if record['fim'] <= record['inicio']:
        errors.append("Fim must be after Início")

    # FK validation
    if not Projeto.objects.filter(nome=record['projeto_nome']).exists():
        errors.append(f"Projeto not found: {record['projeto_nome']}")

    return errors
```

### Transaction Rollback

```python
from django.db import transaction

@transaction.atomic
def _load_apply(self, records: list, report: dict) -> None:
    """
    Load with automatic rollback on error.

    If ANY error occurs, entire transaction is rolled back.
    """
    try:
        for record in records:
            # Process record
            pass

    except Exception as e:
        # Transaction automatically rolls back
        self.stdout.write(self.style.ERROR(f"Load failed: {e}"))
        raise CommandError(f"ETL apply failed: {e}")
```

---

## 📦 Data Source Patterns

### CSV Import

```python
def _extract(self, source_path: Path) -> pd.DataFrame:
    """Extract from CSV with encoding handling."""
    try:
        # Try UTF-8 first
        df = pd.read_csv(source_path, encoding='utf-8')
    except UnicodeDecodeError:
        # Fallback to latin-1
        df = pd.read_csv(source_path, encoding='latin-1')

    return df
```

### XLSX Import (Multiple Sheets)

```python
def _extract(self, source_path: Path) -> dict:
    """Extract from XLSX with multiple sheets."""
    sheets = ['ACerta', 'Outros', 'Super', 'Brincando', 'Vidas']

    data = {}
    for sheet in sheets:
        try:
            df = pd.read_excel(source_path, sheet_name=sheet)
            data[sheet] = df
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Sheet {sheet} not found: {e}"))

    return data
```

### API Import

```python
def _extract(self, api_url: str) -> dict:
    """Extract from external API."""
    import requests

    response = requests.get(api_url, timeout=30)
    response.raise_for_status()

    return response.json()
```

---

## 🧪 Testing ETL Commands

### Test Template

```python
import pytest
from django.core.management import call_command
from io import StringIO
from pathlib import Path


class TestETLAcompanhamento:
    """Tests for etl_upsert_acompanhamento command."""

    @pytest.fixture
    def sample_xlsx(self, tmp_path):
        """Create sample XLSX for testing."""
        import pandas as pd

        data = {
            'Projeto': ['ACerta', 'Brincando'],
            'Município': ['Fortaleza', 'Caucaia'],
            'Tipo': ['Formação', 'Oficina'],
            'Data': ['15/01/2025', '16/01/2025'],
            'Início': ['09:00', '14:00'],
            'Fim': ['12:00', '17:00'],
            'Formador 1': ['Maria Silva', 'João Santos'],
            'Formador 2': ['', '']
        }

        df = pd.DataFrame(data)
        xlsx_path = tmp_path / 'test_acompanhamento.xlsx'
        df.to_excel(xlsx_path, index=False)

        return xlsx_path

    def test_dry_run_generates_report(self, sample_xlsx):
        """Dry-run generates report without DB changes."""
        out = StringIO()

        call_command(
            'etl_upsert_acompanhamento',
            source=str(sample_xlsx),
            stdout=out
        )

        output = out.getvalue()
        assert 'DRY-RUN MODE' in output
        assert 'Total rows: 2' in output

        # Verify report exists
        report_path = Path('out_etl').glob('etl_upsert_acompanhamento_*.json')
        assert any(report_path)

    def test_apply_mode_creates_records(self, sample_xlsx):
        """Apply mode creates Solicitacao records."""
        call_command(
            'etl_upsert_acompanhamento',
            source=str(sample_xlsx),
            apply=True
        )

        from apps.core.models import Solicitacao
        assert Solicitacao.objects.count() == 2

    def test_idempotence(self, sample_xlsx):
        """Re-running apply doesn't create duplicates."""
        # First run
        call_command('etl_upsert_acompanhamento', source=str(sample_xlsx), apply=True)

        # Second run
        call_command('etl_upsert_acompanhamento', source=str(sample_xlsx), apply=True)

        from apps.core.models import Solicitacao
        assert Solicitacao.objects.count() == 2  # Still 2, not 4

    def test_quality_gate_fail_blocks_apply(self, tmp_path):
        """Quality gate failure prevents apply."""
        # Create invalid data (>10% invalid)
        data = {
            'Projeto': ['ACerta'] * 5 + ['INVALID'] * 5,
            'Município': ['Fortaleza'] * 10,
            # ... other fields
        }

        df = pd.DataFrame(data)
        xlsx_path = tmp_path / 'invalid.xlsx'
        df.to_excel(xlsx_path, index=False)

        with pytest.raises(Exception):
            call_command('etl_upsert_acompanhamento', source=str(xlsx_path), apply=True)
```

---

## 🔗 Related Documentation

- **Commands**: `.claude/commands/etl-dry.md`, `.claude/commands/etl-apply.md`
- **Business Rules**: `.claude/skills/aprender-domain/SKILL.md`
- **Django Patterns**: `.claude/skills/django-patterns/SKILL.md`
- **Project Context**: `.claude/CLAUDE.md`

---

## 📚 Real Examples

### ETL Commands Available (21 commands)

**Core ETL Commands**:
- `etl_upsert_acompanhamento.py` - Import events from Acompanhamento spreadsheet
- `etl_upsert_deslocamento.py` - Import travel/displacement data
- `etl_upsert_core.py` - Core entities (Municipio, Projeto, TipoEvento)
- `etl_all.py` - Run all ETLs in sequence

**DAT Module ETL**:
- `etl_import_acoes_controle.py` - Import Ações Controle data
- `etl_import_dat_cadastros.py` - Import DAT Cadastros
- `etl_load_xlsx.py` - Generic XLSX loader

**User Management**:
- `import_usuarios_from_csv.py` - Import users from CSV
- `assign_cpf_from_excel.py` - Assign CPF from Excel cross-reference
- `backfill_user_groups.py` - Backfill user groups
- `backfill_coordenador.py` - Backfill coordinator field
- `audit_agenda_users.py` - Audit users from agenda

**Seeding/Setup**:
- `load_tipos_evento.py` - Load TipoEvento seed data
- `seed_formadores_fluir.py` - Seed Fluir formadores
- `seed_projetos_extras.py` - Seed additional projects
- `import_fluir_eventos.py` - Import Fluir-specific events

**Utilities**:
- `backfill_external_hash_v2.py` - Recalculate external_hash
- `benchmark_etl.py` - Performance benchmarking
- `gen_top50_usuarios.py` - Generate test data
- `load_full_pipeline.py` - Run complete pipeline

### Usage Pattern

```bash
# Dry-run (default) - preview changes
docker compose exec web python manage.py etl_upsert_acompanhamento

# Apply mode - commit changes
docker compose exec web python manage.py etl_upsert_acompanhamento --apply

# Run all ETLs in sequence
docker compose exec web python manage.py etl_all --apply
```

---

## 🔗 Related Documentation

- **Commands**: `.claude/commands/etl-dry.md`, `.claude/commands/etl-apply.md`
- **Business Rules**: `.claude/skills/aprender-domain/SKILL.md`
- **Django Patterns**: `.claude/skills/django-patterns/SKILL.md`
- **Project Context**: `.claude/CLAUDE.md`

---

**Last Updated**: 23/12/2025
**Version**: 1.1 (Updated: Complete ETL command list, DAT module commands)
**Based on**: AS v2 ETL patterns + idempotence best practices

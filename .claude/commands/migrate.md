---
description: Create and apply Django migrations with validation and safety checks
argument-hint: [optional: app name]
---

# Django Migrations — Safe Workflow

Create and apply migrations: ${ARGUMENTS:-all apps}

## Approach:

### 1. Pre-Migration Checklist

Before creating migrations:
- [ ] **Models finalized**: All model changes complete
- [ ] **Tests passing**: Current tests green
- [ ] **Branch clean**: No uncommitted changes
- [ ] **Docs updated**: Model changes documented

### 2. Create Migrations

```bash
# All apps (default)
docker compose exec web python manage.py makemigrations

# Specific app
docker compose exec web python manage.py makemigrations $ARGUMENTS

# Dry-run (see what would be created)
docker compose exec web python manage.py makemigrations --dry-run

# With custom name
docker compose exec web python manage.py makemigrations --name add_prioridade_field
```

### 3. Inspect Generated Migrations

**Check migration file**:
```bash
# List migrations
docker compose exec web python manage.py showmigrations

# View SQL (before applying)
docker compose exec web python manage.py sqlmigrate core 0024
```

**Review checklist**:
- [ ] **Migration number**: Sequential (no conflicts)
- [ ] **Dependencies**: Correct `dependencies = [...]`
- [ ] **Operations**: Expected changes only
- [ ] **Reversible**: Has reverse operations (when possible)
- [ ] **Data migrations**: Separate from schema changes

### 4. Validate Migrations

```bash
# Check for issues
docker compose exec web python manage.py check

# Detect conflicts
docker compose exec web python manage.py makemigrations --check

# Run migrations (dry-run equivalent)
docker compose exec web python manage.py migrate --plan
```

**Common issues**:
- **Circular dependencies**: Resolve with `run_before` or split migrations
- **Non-nullable field**: Add `default=` or `null=True`
- **Unique constraint**: Handle existing duplicates first
- **Rename detection**: Use `RenameField`/`RenameModel` operations

### 5. Backup Database (CRITICAL)

**Before applying migrations in staging/production**:
```bash
# Backup PostgreSQL
docker compose exec db pg_dump -U postgres aprender_v2 > backup_pre_migration_$(date +%Y%m%d_%H%M%S).sql

# Verify backup
ls -lh backup_*.sql
```

**Restoration** (if needed):
```bash
# Restore from backup
docker compose down
docker compose up -d db
docker compose exec -T db psql -U postgres aprender_v2 < backup_pre_migration_20250115.sql
docker compose up -d
```

### 6. Apply Migrations

```bash
# Development (local)
docker compose exec web python manage.py migrate

# Specific app
docker compose exec web python manage.py migrate core

# Specific migration
docker compose exec web python manage.py migrate core 0024

# With verbosity
docker compose exec web python manage.py migrate --verbosity 2
```

**Watch for**:
- **Errors**: Stop immediately, rollback
- **Warnings**: Review, may indicate issues
- **Time**: Long migrations may need downtime

### 7. Validate Post-Migration

```bash
# Run checks
docker compose exec web python manage.py check

# Run tests (critical)
docker compose exec web pytest apps/core/tests/ -v

# Verify data integrity
docker compose exec web python manage.py shell

>>> from apps.core.models import Solicitacao
>>> Solicitacao.objects.count()  # Should match pre-migration
>>> Solicitacao.objects.first().status  # Check new fields
```

### 8. Migration Types and Patterns

#### Schema Migration (Simple)

**Example**: Add field
```python
# Generated automatically
operations = [
    migrations.AddField(
        model_name='solicitacao',
        name='prioridade',
        field=models.IntegerField(default=3),
    ),
]
```

**Safe**: Can be applied directly

#### Schema Migration (Complex)

**Example**: Add non-nullable field to existing model
```python
# Step 1: Add field with default
operations = [
    migrations.AddField(
        model_name='solicitacao',
        name='prioridade',
        field=models.IntegerField(default=3),
    ),
]

# Step 2 (separate migration): Remove default if needed
operations = [
    migrations.AlterField(
        model_name='solicitacao',
        name='prioridade',
        field=models.IntegerField(),
    ),
]
```

**Pattern**: Add with default → Populate → Remove default (3 migrations)

#### Data Migration

**Example**: Populate new field
```python
from django.db import migrations


def populate_prioridade(apps, schema_editor):
    """Populate prioridade based on projeto.fluxo."""
    Solicitacao = apps.get_model('core', 'Solicitacao')

    for solicitacao in Solicitacao.objects.all():
        if solicitacao.projeto.fluxo == 'SUPER':
            solicitacao.prioridade = 5
        else:
            solicitacao.prioridade = 3
        solicitacao.save()


def reverse_populate_prioridade(apps, schema_editor):
    """Reverse: Set all to default."""
    Solicitacao = apps.get_model('core', 'Solicitacao')
    Solicitacao.objects.update(prioridade=3)


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0024_add_prioridade_field'),
    ]

    operations = [
        migrations.RunPython(
            populate_prioridade,
            reverse_populate_prioridade
        ),
    ]
```

**Critical**:
- [ ] Always provide reverse function
- [ ] Use `apps.get_model()` (not direct import)
- [ ] Test with sample data
- [ ] Handle large datasets (batch updates)

#### Rename Migration

**Example**: Rename field
```python
# Use RenameField (preserves data)
operations = [
    migrations.RenameField(
        model_name='solicitacao',
        old_name='observacao',
        new_name='observacoes',
    ),
]
```

**NOT**:
```python
# WRONG: Don't remove + add (loses data!)
migrations.RemoveField(...),
migrations.AddField(...),
```

### 9. Migration Conflicts

**Scenario**: Two branches create same migration number

**Detection**:
```bash
docker compose exec web python manage.py makemigrations --check
# Error: Conflicting migrations detected
```

**Resolution**:
```bash
# Step 1: Pull latest main
git checkout main
git pull

# Step 2: Rebase feature branch
git checkout feature/my-changes
git rebase main

# Step 3: Recreate migration
rm apps/core/migrations/0024_*.py  # Remove conflicting
docker compose exec web python manage.py makemigrations

# Step 4: Test
docker compose exec web python manage.py migrate
docker compose exec web pytest -v
```

### 10. Rollback Migrations

**Revert to specific migration**:
```bash
# Rollback last migration
docker compose exec web python manage.py migrate core 0023

# Rollback all migrations for app
docker compose exec web python manage.py migrate core zero

# See migration history
docker compose exec web python manage.py showmigrations core
```

**When to rollback**:
- Migration failed partway
- Data corruption detected
- Critical bug introduced
- Need to apply hotfix on older version

**After rollback**:
1. Fix the issue in models/migration
2. Recreate migration
3. Re-apply with validation

### 11. Production Deployment Pattern

**Safe deployment workflow**:

```bash
# Step 1: Staging test
# Apply migrations in staging first
docker compose -f staging.yml exec web python manage.py migrate

# Run full test suite
docker compose -f staging.yml exec web pytest -v

# Manual QA testing
# ...

# Step 2: Production backup (CRITICAL)
ssh production "cd /app && docker compose exec db pg_dump -U postgres aprender_v2 > /backups/backup_$(date +%Y%m%d_%H%M%S).sql"

# Step 3: Production maintenance mode
# Enable maintenance page
ssh production "touch /app/MAINTENANCE_MODE"

# Step 4: Apply migrations
ssh production "cd /app && docker compose exec web python manage.py migrate"

# Step 5: Validate
ssh production "cd /app && docker compose exec web python manage.py check"
ssh production "cd /app && docker compose exec web pytest apps/core/tests/test_critical.py -v"

# Step 6: Disable maintenance mode
ssh production "rm /app/MAINTENANCE_MODE"
```

### 12. Squash Migrations (Optional)

**When to squash**:
- Many small migrations accumulated (20+)
- Slow initial migration for new environments
- Cleanup before major release

**How to squash**:
```bash
# Squash migrations 0010-0025 into single migration
docker compose exec web python manage.py squashmigrations core 0010 0025

# Test squashed migration
docker compose exec web python manage.py migrate

# After testing, delete old migrations (keep squashed)
```

**Warning**: Only squash migrations that are already applied in production.

### 13. Output

**If successful**:
```
✅ MIGRATION SUCCESSFUL

Pre-checks:
- Models finalized ✓
- Tests passing ✓
- Database backup created ✓

Migration applied:
- apps/core/migrations/0024_add_prioridade_field.py

Post-validation:
- Checks: OK ✓
- Tests: 56/56 passing ✓
- Data integrity: Verified ✓

Backup retained: backup_pre_migration_20250115_103000.sql
```

**If failed**:
```
❌ MIGRATION FAILED

Error: [Error message]

ROLLBACK RECOMMENDED
1. Restore database: docker compose exec -T db psql -U postgres aprender_v2 < backup_pre_migration_20250115.sql
2. Review migration: apps/core/migrations/0024_*.py
3. Fix issues in models.py
4. Recreate migration: rm 0024_*.py && python manage.py makemigrations
5. Retry after validation
```

### 14. Best Practices

#### DO
- ✅ Create small, atomic migrations
- ✅ Separate schema and data migrations
- ✅ Always provide reverse operations
- ✅ Test migrations on sample data first
- ✅ Backup before applying in staging/production
- ✅ Use `RenameField`/`RenameModel` (not remove+add)
- ✅ Handle large datasets with batch updates
- ✅ Document complex migrations

#### DON'T
- ❌ Edit applied migrations (create new instead)
- ❌ Commit migration files without testing
- ❌ Skip backups in production
- ❌ Apply migrations without reviewing SQL
- ❌ Use `null=True` as workaround (add default instead)
- ❌ Ignore migration warnings
- ❌ Apply untested migrations to production

### 15. Common Scenarios

#### Add Field with Default
```bash
# Edit model
# Add: prioridade = models.IntegerField(default=3)

docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
```

#### Add Non-Nullable Field (Existing Data)
```bash
# Step 1: Add nullable with default
# prioridade = models.IntegerField(default=3, null=True)
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate

# Step 2: Populate (data migration)
# Create 0025_populate_prioridade.py
docker compose exec web python manage.py migrate

# Step 3: Remove null
# prioridade = models.IntegerField(default=3)
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
```

#### Rename Model
```bash
# Use RenameModel
# Create migration manually or let Django detect

# Migration will be:
# migrations.RenameModel(old_name='Solicitacao', new_name='Pedido')

docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
```

#### Add Unique Constraint (Existing Data)
```bash
# Step 1: Check for duplicates
docker compose exec web python manage.py shell
>>> Solicitacao.objects.values('projeto', 'inicio').annotate(count=Count('id')).filter(count__gt=1)

# Step 2: Handle duplicates (data migration)

# Step 3: Add constraint
# Meta: constraints = [models.UniqueConstraint(fields=['projeto', 'inicio'], name='...')]
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
```

## Reference

- **Django Migrations**: https://docs.djangoproject.com/en/5.1/topics/migrations/
- **Django Patterns**: `.claude/skills/django-patterns/SKILL.md`
- **Project Context**: `.claude/CLAUDE.md`

---

**Focus**: Safe, tested migrations with backup and rollback capability.

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
docker exec aprender_dev-web-1 python manage.py makemigrations

# Specific app
docker exec aprender_dev-web-1 python manage.py makemigrations $ARGUMENTS

# Dry-run (see what would be created)
docker exec aprender_dev-web-1 python manage.py makemigrations --dry-run

# With custom name
docker exec aprender_dev-web-1 python manage.py makemigrations --name add_prioridade_field
```

### 3. Inspect Generated Migrations

**Check migration file**:
```bash
# List migrations
docker exec aprender_dev-web-1 python manage.py showmigrations

# View SQL (before applying)
docker exec aprender_dev-web-1 python manage.py sqlmigrate core 0024
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
docker exec aprender_dev-web-1 python manage.py check

# Detect conflicts
docker exec aprender_dev-web-1 python manage.py makemigrations --check

# Run migrations (dry-run equivalent)
docker exec aprender_dev-web-1 python manage.py migrate --plan
```

**Common issues**:
- **Circular dependencies**: Resolve with `run_before` or split migrations
- **Non-nullable field**: Add `default=` or `null=True`
- **Unique constraint**: Handle existing duplicates first
- **Rename detection**: Use `RenameField`/`RenameModel` operations

### 5. Backup Database (CRITICAL)

> **Em produção você não aplica migration à mão** (ver §11). O backup de produção não é um passo
> seu: o `aprender-applier` na VM01 **exige backup de DB fresco** antes de fazer o `PUT`, e recusa
> o deploy (fail-closed) se não houver. O que segue é o backup **local**, antes de aplicar no seu
> ambiente de dev/prod-like.

**Before applying migrations locally**:
```bash
# Backup PostgreSQL
docker exec aprender_dev-db-1 pg_dump -U aprender_user aprender_db > backup_pre_migration_$(date +%Y%m%d_%H%M%S).sql

# Verify backup
ls -lh backup_*.sql
```

**Restoration** (if needed):
```bash
# Restore from backup
docker compose down
docker compose up -d db
docker exec -i aprender_dev-db-1 psql -U aprender_user aprender_db < backup_pre_migration_20250115.sql
docker compose up -d
```

### 6. Apply Migrations

```bash
# Development (local)
docker exec aprender_dev-web-1 python manage.py migrate

# Specific app
docker exec aprender_dev-web-1 python manage.py migrate core

# Specific migration
docker exec aprender_dev-web-1 python manage.py migrate core 0024

# With verbosity
docker exec aprender_dev-web-1 python manage.py migrate --verbosity 2
```

**Watch for**:
- **Errors**: Stop immediately, rollback
- **Warnings**: Review, may indicate issues
- **Time**: Long migrations may need downtime

### 7. Validate Post-Migration

```bash
# Run checks
docker exec aprender_dev-web-1 python manage.py check

# Run tests (critical)
docker exec aprender_dev-web-1 pytest apps/core/tests/ -v

# Verify data integrity
docker exec aprender_dev-web-1 python manage.py shell

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
docker exec aprender_dev-web-1 python manage.py makemigrations --check
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
docker exec aprender_dev-web-1 python manage.py makemigrations

# Step 4: Test
docker exec aprender_dev-web-1 python manage.py migrate
docker exec aprender_dev-web-1 pytest -v
```

### 10. Rollback Migrations (local/dev — **não** em produção)

> Em produção migrations são **forward-only** (ADR-018): não há `migrate <app> <n-1>` manual, e a
> promoção para trás (`promote.yml -f rollback=true`) troca a **imagem**, não desfaz o schema. Se o
> schema precisa voltar, o caminho é restaurar backup (`v2/docs/DISASTER_RECOVERY.md`). O que segue
> vale para o seu ambiente local.

**Revert to specific migration**:
```bash
# Rollback last migration
docker exec aprender_dev-web-1 python manage.py migrate core 0023

# Rollback all migrations for app
docker exec aprender_dev-web-1 python manage.py migrate core zero

# See migration history
docker exec aprender_dev-web-1 python manage.py showmigrations core
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

> **Realidade de deploy (AS v2, ADR-018 — 2026-07-10)**: não há staging remoto nem
> `ssh production`. A validação é LOCAL via `make staging-full` (8/8). **Merge na `main` NÃO
> deploya** — ele builda, assina e libera uma tag imutável. Produção muda por **promoção humana**
> (`promote.yml`, gated no Environment `production`), e a VM01 **puxa** por digest.
>
> **Em produção, migrations são automáticas e BLOQUEANTES (#1456):** o serviço one-shot `migrate`
> do `docker-compose.prod.yml` roda `python manage.py migrate --noinput`, e `web`/`worker`/`beat`
> só sobem com `depends_on: service_completed_successfully`. Migration quebrada **trava o deploy**
> em vez de servir schema meio-migrado.

> [!warning] Procedimento revogado
> ~~"Rodar `python manage.py migrate` manualmente no container de produção"~~ (instrução do
> **ADR-010**) está **revogada desde o ADR-018, 2026-07-10**. Não é só desnecessário: aplicar
> migration por fora do serviço `migrate` desalinha o schema do que o applier acabou de selar.
> ~~"Merge na `main` → deploy automático via Portainer"~~ também caiu — os jobs `deploy` e
> `validate_existing_tag` foram **deletados** no **#1516**.

**Safe deployment workflow**:

```bash
# Step 1: Validacao LOCAL (staging-like) — gate obrigatorio antes da PR
#   build + up + migrate + test suite + down, tudo em containers locais
make staging-full          # precisa fechar 8/8 PASS

# Step 2: Abrir/atualizar a PR com a evidencia do gate
#   (makemigrations --check limpo: migration faltando quebra o servico `migrate` em prod)

# Step 3: Merge na main -> BUILD + ASSINATURA + TAG (nao e deploy)
#   deploy.yaml = "Build, sign and release": build/scan/push + cosign + SLSA
#   -> tag imutavel vYYYY.MM.DD-<sha7>. Producao NAO muda aqui.

# Step 4: Promover (ato humano, gated)
gh workflow run promote.yml -f release=v2026.MM.DD-<sha7>
#   Pausa no GitHub Environment `production` (required reviewer). Assina o
#   production.json e publica no branch protegido `deploy-pointer`.

# Step 5: A VM01 puxa (~60s, systemd timer)
#   aprender-deployer verifica assinatura + digests; aprender-applier confere
#   anti-rollback, drift do compose, EXIGE backup de DB fresco, faz o PUT em
#   127.0.0.1:9443. O servico one-shot `migrate` roda AI, antes de web/worker/beat.
#   Migration que falha = deploy fail-closed; producao segue na versao anterior.

# Step 6: Validar pos-promocao
#   curl /api/version/  -> {"version":"<release>"} deve casar com o release do production.json.
#                          A rota NAO devolve digest (views_health.py:93-99); o digest verificado
#                          no PUT fica no selo do applier, dentro da VM.
#   curl /api/readyz/   -> 200
#   Probe externo HTTP 000 (Kaspersky/KESL) nao indica deploy quebrado: a confirmacao
#   canonica e a que o applier ja fez de DENTRO da VM (localhost).

# Rollback: NAO ha auto-rollback — migrations sao forward-only.
gh workflow run promote.yml -f release=<tag-anterior> -f rollback=true
#   Se a migration corrompeu dados, promover para tras NAO desfaz o schema:
#   restaurar do backup conforme v2/docs/DISASTER_RECOVERY.md / BACKUP_OPERATIONS.md
#   (secrets de producao vivem no Portainer, nao no repo)
```

**Consequência prática para quem escreve a migration**: ela é o degrau que pode derrubar a
promoção inteira, e não existe janela manual para "consertar em produção". Migration não-reversível
ou destrutiva precisa do padrão expand/contract (§8) espalhado por releases separados.

### 12. Squash Migrations (Optional)

**When to squash**:
- Many small migrations accumulated (20+)
- Slow initial migration for new environments
- Cleanup before major release

**How to squash**:
```bash
# Squash migrations 0010-0025 into single migration
docker exec aprender_dev-web-1 python manage.py squashmigrations core 0010 0025

# Test squashed migration
docker exec aprender_dev-web-1 python manage.py migrate

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
1. Restore database: docker exec -i aprender_dev-db-1 psql -U aprender_user aprender_db < backup_pre_migration_20250115.sql
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
- ✅ Backup before applying locally (em prod o applier exige backup fresco sozinho)
- ✅ Use `RenameField`/`RenameModel` (not remove+add)
- ✅ Handle large datasets with batch updates
- ✅ Document complex migrations

#### DON'T
- ❌ Edit applied migrations (create new instead)
- ❌ Commit migration files without testing
- ❌ **Rodar `manage.py migrate` a mão no container de produção** — revogado (ADR-018); o serviço
  one-shot `migrate` é quem aplica, e aplicar por fora desalinha o schema do que o applier selou
- ❌ Apply migrations without reviewing SQL
- ❌ Use `null=True` as workaround (add default instead)
- ❌ Ignore migration warnings
- ❌ Promover uma tag cuja migration não passou no gate local (ela **bloqueia** o deploy em prod)

### 15. Common Scenarios

#### Add Field with Default
```bash
# Edit model
# Add: prioridade = models.IntegerField(default=3)

docker exec aprender_dev-web-1 python manage.py makemigrations
docker exec aprender_dev-web-1 python manage.py migrate
```

#### Add Non-Nullable Field (Existing Data)
```bash
# Step 1: Add nullable with default
# prioridade = models.IntegerField(default=3, null=True)
docker exec aprender_dev-web-1 python manage.py makemigrations
docker exec aprender_dev-web-1 python manage.py migrate

# Step 2: Populate (data migration)
# Create 0025_populate_prioridade.py
docker exec aprender_dev-web-1 python manage.py migrate

# Step 3: Remove null
# prioridade = models.IntegerField(default=3)
docker exec aprender_dev-web-1 python manage.py makemigrations
docker exec aprender_dev-web-1 python manage.py migrate
```

#### Rename Model
```bash
# Use RenameModel
# Create migration manually or let Django detect

# Migration will be:
# migrations.RenameModel(old_name='Solicitacao', new_name='Pedido')

docker exec aprender_dev-web-1 python manage.py makemigrations
docker exec aprender_dev-web-1 python manage.py migrate
```

#### Add Unique Constraint (Existing Data)
```bash
# Step 1: Check for duplicates
docker exec aprender_dev-web-1 python manage.py shell
>>> Solicitacao.objects.values('projeto', 'inicio').annotate(count=Count('id')).filter(count__gt=1)

# Step 2: Handle duplicates (data migration)

# Step 3: Add constraint
# Meta: constraints = [models.UniqueConstraint(fields=['projeto', 'inicio'], name='...')]
docker exec aprender_dev-web-1 python manage.py makemigrations
docker exec aprender_dev-web-1 python manage.py migrate
```

## Reference

- **Django Migrations**: https://docs.djangoproject.com/en/5.2/topics/migrations/
- **Django Patterns**: `.claude/skills/django-patterns/SKILL.md`
- **Project Context**: `.claude/CLAUDE.md`

---

**Focus**: Safe, tested migrations with backup and rollback capability.

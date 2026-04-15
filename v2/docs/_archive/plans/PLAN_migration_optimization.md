# Plano: Otimização de Migrations (core + dat_ingest)

**Status:** Planejado
**Data:** 2026-04-14
**Branch:** `chore/optimize-migrations`

---

## 1. Resumo Executivo

O app `core` tem 70 migrations com oportunidades de otimização em 3 categorias:

| Categoria | Qty | Ação |
|-----------|-----|------|
| Data migrations one-time (no-op) | 6 | Converter RunPython para noop |
| Data migrations mistas (schema+data) | 2 | Separar schema de data, converter data para noop |
| Ping-pong / redundantes | 2 | Documentar (não alterar agora) |
| **Total de migrations otimizáveis** | **10** | |

**Impacto:** `migrate --run-syncdb` do zero ~15% mais rápido (pula 8 RunPython/RunSQL).
**Risco:** Zero em produção (migrations já marcadas como applied em django_migrations).

---

## 2. Fase 1 — Converter 6 data migrations puras em no-op

Estas migrations contêm APENAS RunPython/RunSQL, sem operações de schema.
Já rodaram em produção. Em fresh install, não fazem nada útil.

### 0024_backfill_is_online.py

**O que faz:** Seta is_online=True onde meet_link existe.
**Por que no-op:** Fresh install não tem Solicitacoes. Backfill inútil.
**Reverse atual:** noop (pass).
**Ação:**
```python
# ANTES
operations = [
    migrations.RunPython(forwards, backwards),
]

# DEPOIS
operations = [
    migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop),
]
```

### 0029_normalize_codigo_null.py

**O que faz:** RunSQL: `UPDATE core_projeto SET codigo = '' WHERE codigo IS NULL`
**Por que no-op:** Fresh install nunca terá NULLs (0030 faz default='').
**Ação:**
```python
# ANTES
operations = [
    migrations.RunSQL(
        "UPDATE core_projeto SET codigo = '' WHERE codigo IS NULL;",
        "UPDATE core_projeto SET codigo = NULL WHERE codigo = '';",
    ),
]

# DEPOIS
operations = [
    migrations.RunSQL(migrations.RunSQL.noop, migrations.RunSQL.noop),
]
```

### 0034_populate_compra_produto.py

**O que faz:** Popula Compra.produto FK por matching de codigo.
**Por que no-op:** Fresh install não tem Compras. Backfill inútil.
**Reverse atual:** noop.
**Ação:** Substituir RunPython por noop.

### 0036_consolidate_duplicate_projetos.py

**O que faz:** Merge 3 projetos duplicados por case/spacing.
**Por que no-op:** Fresh install não tem projetos duplicados.
**Reverse atual:** noop.
**Ação:** Substituir RunPython por noop.

### 0037_fix_superintendencia_fluxo.py

**O que faz:** Muda fluxo de 4 projetos para SUPER.
**Por que no-op:** Fresh install não tem esses projetos.
**Reverse atual:** Explicit reverse.
**Ação:** Substituir RunPython por noop.

### 0038_mark_test_projects.py

**O que faz:** Marca 8 projetos como is_test=True.
**Por que no-op:** Fresh install não tem esses projetos de teste.
**Reverse atual:** Explicit reverse.
**Ação:** Substituir RunPython por noop.

---

## 3. Fase 2 — Separar schema de data em 2 migrations mistas

Estas migrations misturam RunPython (data) com AlterField (schema).
O RunPython é one-time, mas o AlterField DEVE permanecer.

### 0021_change_outros_to_nao_super.py

**Operações atuais:**
1. `RunPython(migrate_outros_to_nao_super, reverse)` — backfill OUTROS→NAO_SUPER
2. `AlterField(Projeto.fluxo)` — atualiza choices do campo

**Ação:** Converter APENAS o RunPython para noop, manter AlterField:
```python
operations = [
    migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop),
    migrations.AlterField(
        model_name='projeto',
        name='fluxo',
        # ... (manter exatamente como está)
    ),
]
```

### 0057_normalize_acao_dat_tipo_acao_choices.py

**Operações atuais:**
1. `RunPython(normalize_acao_dat_tipo_acao, reverse_noop)` — normaliza strings
2. `AlterField(AcaoDAT.tipo_acao)` — atualiza choices

**Ação:** Mesmo padrão — converter RunPython para noop, manter AlterField.

---

## 4. Fase 3 — Documentar ping-pong e redundâncias (NÃO alterar)

Estas migrations não podem ser alteradas sem squash, mas devem ser documentadas.

### 0050 → 0051: GIN index adicionado e removido

- 0050 adiciona `idx_auditlog_details_gin` (GIN em AuditLog.details)
- 0051 remove esse mesmo índice + migra unique_together→UniqueConstraint

**Decisão:** NÃO alterar. O GIN foi removido por decisão técnica (performance).
Em squash futuro, 0050 desapareceria automaticamente.

### 0061 → 0063: FK cascade ping-pong

- 0061 muda AcaoTemplateExecutor.group de PROTECT→CASCADE + adiciona related_name
- 0063 reverte CASCADE→PROTECT, mantém related_name

**Decisão:** NÃO alterar. O related_name foi mantido.
Em squash futuro, 0061 desapareceria e 0063 seria absorvido em 0059.

### 0006 → 0007: Config.key unique→not unique

**Decisão:** NÃO alterar. Funcional como está.
Em squash futuro, 0006 já criaria com unique=False.

---

## 5. Fase 4 — Limpar código morto nas migrations convertidas

Após converter para noop, as funções Python definidas no topo dos arquivos ficam mortas.
Removê-las para clareza.

### Padrão de limpeza

```python
# ANTES
from django.db import migrations

def migrate_outros_to_nao_super(apps, schema_editor):
    Projeto = apps.get_model('core', 'Projeto')
    Projeto.objects.filter(fluxo='OUTROS').update(fluxo='NAO_SUPER')

def reverse_nao_super_to_outros(apps, schema_editor):
    Projeto = apps.get_model('core', 'Projeto')
    Projeto.objects.filter(fluxo='NAO_SUPER').update(fluxo='OUTROS')

class Migration(migrations.Migration):
    dependencies = [('core', '0020_...')]
    operations = [
        migrations.RunPython(migrate_outros_to_nao_super, reverse_nao_super_to_outros),
        migrations.AlterField(...),
    ]

# DEPOIS
from django.db import migrations, models

class Migration(migrations.Migration):
    """Originally backfilled OUTROS→NAO_SUPER. Converted to noop (2026-04-14)
    as all prod environments have been migrated. AlterField retained."""
    dependencies = [('core', '0020_...')]
    operations = [
        migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop),
        migrations.AlterField(...),
    ]
```

---

## 6. Resumo de Arquivos Tocados

| Ação | Arquivo |
|------|---------|
| Editar | `core/migrations/0021_change_outros_to_nao_super.py` |
| Editar | `core/migrations/0024_backfill_is_online.py` |
| Editar | `core/migrations/0029_normalize_codigo_null.py` |
| Editar | `core/migrations/0034_populate_compra_produto.py` |
| Editar | `core/migrations/0036_consolidate_duplicate_projetos.py` |
| Editar | `core/migrations/0037_fix_superintendencia_fluxo.py` |
| Editar | `core/migrations/0038_mark_test_projects.py` |
| Editar | `core/migrations/0057_normalize_acao_dat_tipo_acao_choices.py` |

**Total: 8 edições**

---

## 7. Validação

### Antes de implementar
```bash
# Baseline: migration plan atual
docker exec aprender_dev-web-1 python manage.py showmigrations core
docker exec aprender_dev-web-1 python manage.py migrate --check
```

### Após implementar
```bash
# 1. Verificar que migrations são válidas
docker exec aprender_dev-web-1 python manage.py migrate --check

# 2. Verificar que nenhum migration detecta mudança pendente
docker exec aprender_dev-web-1 python manage.py makemigrations --check --dry-run

# 3. Testar migrate do zero (fresh DB)
docker exec aprender_dev-web-1 python manage.py migrate --run-syncdb

# 4. Rodar testes
docker exec aprender_dev-web-1 pytest apps/core/tests/ -v
```

---

## 8. Riscos

| Risco | Prob. | Impacto | Mitigação |
|-------|-------|---------|-----------|
| Prod quebra | **Zero** | — | Migrations já aplicadas, noop não re-executa |
| Fresh install falha | Baixa | Alto | Testar migrate do zero em Docker |
| makemigrations detecta diff | Baixa | Baixo | Não alterar AlterField, apenas RunPython |
| Reverse migration falha | Baixa | Médio | Noop reverse é seguro |

---

## 9. Commits

```text
chore(migrations): convert 6 one-time data migrations to noop

Migrations 0024, 0029, 0034, 0036, 0037, 0038 contained one-time
backfills that already ran in production. Converting RunPython/RunSQL
to noop speeds up fresh installs and clarifies intent.

chore(migrations): extract noop from mixed schema+data migrations

Migrations 0021 and 0057 mixed RunPython (one-time backfill) with
AlterField (permanent schema change). RunPython converted to noop,
AlterField preserved. Dead Python functions removed.
```

---

## 10. Decisão sobre squashmigrations

### Agora: NÃO fazer squash

Com 70 migrations e as otimizações acima, o sistema está saudável.
O squash seria premature optimization.

### Futuro: Trigger para squash

Fazer squash quando QUALQUER destes critérios for atingido:
- [ ] core ultrapassar 150 migrations
- [ ] `migrate` do zero levar >30 segundos
- [ ] Schema estabilizar (>2 meses sem migration nova)
- [ ] Múltiplos ambientes (staging, QA) com migrate frequente

### Preparação para squash futuro (já feita por este plano)

1. Data migrations convertidas para noop → squash as elimina automaticamente
2. Ping-pong documentado → squash colapsa automaticamente
3. God migrations documentadas → squash otimiza operações internamente

---

## 11. Referências

- Django docs: https://docs.djangoproject.com/en/5.2/topics/migrations/#squashing-migrations
- django-squash: https://pypi.org/project/django-squash/
- ADR a criar: ADR-014-migration-optimization-strategy

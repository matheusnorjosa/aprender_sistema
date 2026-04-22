# Epic 4 — Codename rename para verb_noun inglês

**Parent plan:** [master-plan.md](./master-plan.md)
**Dependências:** Epic 3 (caminho único `has_perm` limpo é pré-requisito)
**Bloqueia:** Epic 5 (class sweep assume codenames finais)
**Issues:** 3
**PR size total:** ~900 linhas (split em 3 PRs)
**Tempo estimado:** 6h total + 1 semana soak entre E4.2 e E4.3

---

## Por que este epic existe

Codenames atuais violam convenção Django + GitLab:

| Problema | Exemplo | Fonte que condena |
|---|---|---|
| Prefixo `pode_` em português | `pode_operar_dat` | Django docs padrão: `verb_noun` inglês |
| Verbo `operar` | `pode_operar_*` | GitLab: banido (escopo indefinido) |
| Nome de setor | `pode_operar_dat` | GitLab: "permissions MUST NOT encode resource boundary" |
| Inconsistência | `pode_aprovar_*`, `pode_acessar_*` | Convenção única quebra a legibilidade |

Codename é **contrato interno estável** — aparece em `has_perm("...")` espalhado. Mudar requer dual-write para não quebrar consumidores.

## Escopo

### Dentro do escopo
- 14 novos codenames em inglês `verb_noun`
- Seed dual-write: mantém codenames antigos + cria novos, copia assignments de grupo
- Script de migração de usagens internas (`has_perm("pode_X")` → `has_perm("new_X")`)
- Período de soak de 1 semana entre dual-write e deleção
- Deleção dos codenames antigos após soak

### Fora do escopo
- Renomear labels (já foi em Epic 1)
- Renomear classes DRF (Epic 5)
- Eliminar hardcoded checks (Epic 3 já fez)

## Issues

- [ ] **Issue 4.1** — Seed dual-write (novos codenames coexistem com antigos, mesmos assignments)
- [ ] **Issue 4.2** — Migrar usagens internas (`functional_codename` nas classes legacy, `has_perm(...)`, testes)
- [ ] **Issue 4.3** — Remover codenames antigos (após 1 semana de soak, sem consumidores externos usando)

## Mapeamento old → new (canônico)

| codename atual | **codename novo** | Justificativa |
|---|---|---|
| pode_aprovar_superintendencia | `approve_solicitation` | Verbo ação + substantivo recurso |
| pode_aprovar_gerente_superintendencia | `approve_solicitation_batch` | Qualifier para o caso em lote |
| pode_gerenciar_superintendencia_only | `execute_restricted_operations` | Remove nome de setor, mantém semântica "restricted" |
| pode_criar_solicitacao_coord_dat | `create_solicitation` | CRUD puro |
| pode_importar_controle_super | `import_spreadsheet` | Verbo+recurso |
| pode_operar_dat | `manage_admin_registries` | GitLab desaconselha `manage_` mas alternativas ficam longas demais; aceita exceção documentada |
| pode_acessar_dashboard_compras | `view_compras_dashboard` | `view_` + recurso |
| pode_operar_dat_exclusivo | `manage_purchases_and_materials` | Decomposição semântica |
| pode_operar_controle_dat | `operate_preagenda` | Escopo funcional único |
| pode_operar_controle | `run_daily_operations` | Substantivo composto ok |
| pode_operar_gerencia | `supervise_operations` | Verbo ação |
| pode_acessar_dashboard_overview | `view_overview_dashboard` | |
| pode_acessar_map_metrics | `view_map_metrics` | |
| pode_editar_como_owner_ou_privilegiado | `edit_solicitation_as_owner_or_privileged` | Nome composto preserva semântica |
| pode_ver_todas_disponibilidades (criado em E3) | `view_all_availability` | Já nasceu próximo do ideal; só vira inglês |

**Nota sobre `manage_`**: a convenção GitLab bane `manage_` por bundling CRUD. Aceitamos 2 exceções (`manage_admin_registries`, `manage_purchases_and_materials`) porque decompor agora em CRUD completo (create/update/delete separados) produz 8+ codenames que sempre são atribuídos juntos (YAGNI explícito — ver master-plan §9.3). Documentado em `RBAC_NAMING.md` como exceção consciente.

## Acceptance criteria

### 4.1 (seed dual-write)
- [ ] `FUNCTIONAL_PERMISSIONS_SEED` atualizado: cada entrada mantida + novo `aliases` tuple com codename novo
- [ ] Migration 0076 cria rows novas; M2M de groups copiado de velha para nova
- [ ] `seed_functional_permissions` atualizado para seedar ambos
- [ ] Frontend `listPermissoesFuncionais` retorna AMBOS (old + new) durante soak
- [ ] Admin UI marca velhas como "[DEPRECATED]" na interface (sufixo no label)
- [ ] Teste: `has_perm("pode_operar_dat")` E `has_perm("manage_admin_registries")` ambos retornam True para user em group DAT

### 4.2 (migrar usagens internas)
- [ ] Todas as 15 classes legacy (`IsDAT`, etc.) passam a apontar para codename NOVO em `functional_codename`
- [ ] Todas as chamadas `user.has_perm("pode_...")` em services, views, tests atualizadas para codename novo
- [ ] Testes antigos que asseram em codename específico atualizados
- [ ] Baseline parity permanece verde

### 4.3 (remover antigos)
- [ ] Pré-requisito: staging rodou 1 semana sem erros de `has_perm` em logs
- [ ] Migration 0077 remove rows antigas de `PermissaoFuncional`
- [ ] Seed atualizado: só os 14 novos codenames existem
- [ ] Grep final: nenhum `pode_` em `apps.core`

## Dual-write data migration (esqueleto)

```python
# v2/backend/apps/core/migrations/0076_seed_new_codenames.py
from django.db import migrations

MAPPING = [
    ("pode_aprovar_superintendencia", "approve_solicitation"),
    ("pode_operar_dat", "manage_admin_registries"),
    # ... 14 entries
]

def forwards(apps, _):
    PF = apps.get_model("core", "PermissaoFuncional")
    for old, new in MAPPING:
        old_row = PF.objects.get(codename=old)
        # Idempotência: só cria se não existir
        new_row, created = PF.objects.get_or_create(
            codename=new,
            defaults={
                "label": old_row.label,  # será atualizado pela seed em runtime
                "description": old_row.description,
                "category": old_row.category,
                "is_system": True,
            },
        )
        if created:
            new_row.groups.set(old_row.groups.all())  # copia M2M

def backwards(apps, _):
    PF = apps.get_model("core", "PermissaoFuncional")
    PF.objects.filter(codename__in=[new for _, new in MAPPING]).delete()

class Migration(migrations.Migration):
    dependencies = [("core", "0075_rbac_layer3_helpers")]
    operations = [migrations.RunPython(forwards, backwards)]
```

## Script de migração de usagens (PR 4.2)

Use `libcst` codemod para trocar:
```python
user.has_perm("pode_operar_dat")
# →
user.has_perm("manage_admin_registries")
```

E também:
```python
HasPerm("pode_operar_dat")
# →
HasPerm("manage_admin_registries")
```

Codemod rodado localmente, PR tem apenas mudanças geradas + testes. Review foca no `MAPPING` do codemod, não nas ~40 linhas trocadas.

## Fontes autoritativas

- [Django — canonical permission format `app_label.codename`](https://docs.djangoproject.com/en/5.2/topics/auth/default/#permission-caching)
- [GitLab — Permissions conventions: verb+resource form, prohibited verbs](https://docs.gitlab.com/development/permissions/conventions/)
- [Django ticket #27489 — history of auto-rename on model rename (revertido, fazer explicitamente)](https://code.djangoproject.com/ticket/27489)

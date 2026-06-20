# Epic 5 — Class sweep: remover 15 classes `Is<Role>` via codemod

**Parent plan:** [master-plan.md](./master-plan.md)
**Dependências:** Epic 4 (codenames já em forma final)
**Bloqueia:** Epic 6 (lint rule assume classes legacy já foram)
**Issues:** 3
**PR size total:** ~1000 linhas auto-geradas + ~200 manuais (split em 3 PRs)
**Tempo estimado:** 8h total + 24h soak após E5.2

---

## Por que este epic existe

Após E1-E4, as 15 classes legacy (`IsDAT`, `IsControleOrDAT`, etc.) ainda existem com `@typing.deprecated`. Cada uma é usada em 5-15 arquivos de views. Sweep manual é tedioso e prone to typo — `libcst` codemod faz de forma segura.

Target final: `apps/core/permissions.py` com **apenas** `HasPerm` + 2-3 classes com `has_object_permission` complexo (`IsOwnerOrPrivileged`, `HasSectorAccess`). Todos os ~85 pontos de uso usam `HasPerm("codename")` direto.

## Escopo

### Dentro do escopo
- Script `libcst` codemod em `v2/backend/tools/rbac_codemod.py`
- Dry-run do codemod em submódulo para validação (PR E5.1)
- Aplicação do codemod em todos os views (PR E5.2, auto-gerado majoritário)
- Deleção das 15 classes legacy de `permissions.py` (PR E5.3)
- Atualização de imports em `__init__.py` e arquivos que re-exportam

### Fora do escopo
- Renomear `HasSectorAccess` ou `IsOwnerOrPrivileged` (já são capability-oriented)
- Migrar testes que usam classes legacy diretamente (fazem parte do codemod)
- Lint rule (Epic 6)

## Issues

- [ ] **Issue 5.1** — Codemod script + dry-run em `views/reports.py` (scope-piloto)
- [ ] **Issue 5.2** — Aplicar codemod em todos os views (~85 arquivos)
- [ ] **Issue 5.3** — Deletar as 15 classes legacy + atualizar imports

## Mapeamento class → HasPerm

| Classe legacy | Substituição |
|---|---|
| `IsSuperintendencia` | `HasPerm("approve_solicitation")` |
| `IsSuperintendenciaOnly` | `HasPerm("execute_restricted_operations")` |
| `IsCoordenadorOrDAT` | `HasPerm("create_solicitation")` |
| `IsControleOrSuper` | `HasPerm("import_spreadsheet")` |
| `IsDATOrSuper` | `HasPerm("manage_admin_registries")` |
| `IsComprasDashboardAccess` | `HasPerm("view_compras_dashboard")` |
| `IsDAT` | `HasPerm("manage_admin_registries_exclusive")` ou `HasPerm("manage_purchases_and_materials")` (depende do contexto) |
| `IsControleOrDAT` | `HasPerm("operate_preagenda")` |
| `IsControle` | `HasPerm("run_daily_operations")` |
| `IsGerencia` | `HasPerm("supervise_operations")` |
| `IsDashboardOverview` | `HasPerm("view_overview_dashboard")` |
| `IsMapMetrics` | `HasPerm("view_map_metrics")` |
| `IsGerenteSuperintendencia` | Manter (tem lógica composite: codename + group check) — marcar `@typing.deprecated` permanente com nota "will be refactored to HasPerm + predicate in future" |
| `IsOwnerOrPrivileged` | Manter (object-level check legítimo) |
| `HasSectorAccess` | Manter (usa scope dinâmico via query param) |

## Acceptance criteria

### 5.1 (codemod script)
- [ ] `v2/backend/tools/rbac_codemod.py` criado usando `libcst`
- [ ] Script testado em `apps/core/views_reports.py` (4 usages de `IsControleOrDAT`)
- [ ] Dry-run output mostra diff limpo
- [ ] Testes do codemod: entrada sintética com casos edge (decorator-style, class-attr-style, import star)
- [ ] PR size: ~200 linhas (tool + 1 arquivo migrado como prova)

### 5.2 (aplicar codemod global)
- [ ] Codemod rodado em todo `v2/backend/apps/core/views*/` + `v2/backend/apps/core/serializers/` + `v2/backend/apps/core/tests/`
- [ ] Imports atualizados (remove imports de classes legacy, adiciona `HasPerm`)
- [ ] PR tem ~800 linhas mas 700 auto-geradas + 100 manuais
- [ ] Baseline parity test verde
- [ ] Nenhum import quebrado (`python manage.py check`)
- [ ] Pyright limpo (`cd v2/backend && pyright apps/core`)
- [ ] Full test suite verde (`pytest apps/core/tests/`)

### 5.3 (deletar legacy)
- [ ] Verificação: `grep -r "IsDAT\|IsControle\|IsSuperintendencia" v2/backend` retorna 0
- [ ] Classes deletadas de `permissions.py`
- [ ] Exceções mantidas documentadas: `HasSectorAccess`, `IsOwnerOrPrivileged`, `IsGerenteSuperintendencia`
- [ ] `permissions.py` tem <200 linhas (era ~275)
- [ ] `funcperm_factory` pode ser deletado (só usado pelas classes legacy)
- [ ] PR size: ~300 linhas (deleção + cleanup + testes de regression)

## Codemod skeleton

```python
# v2/backend/tools/rbac_codemod.py
"""
libcst codemod to replace legacy Is<Role> permission classes with HasPerm(codename).

Usage:
    python -m libcst.tool codemod rbac_codemod.PermissionClassSweep v2/backend/apps/core/views/

Dry-run:
    python -m libcst.tool codemod -x --no-format rbac_codemod.PermissionClassSweep v2/backend/apps/core/views_reports.py

This maps 12 legacy classes to HasPerm("codename") calls. Three classes are
excluded (HasSectorAccess, IsOwnerOrPrivileged, IsGerenteSuperintendencia) because
they have object-level or composite logic that HasPerm can't express.
"""
import libcst as cst
from libcst.codemod import VisitorBasedCodemodCommand, CodemodContext

MAPPING = {
    "IsSuperintendencia": "approve_solicitation",
    "IsSuperintendenciaOnly": "execute_restricted_operations",
    "IsCoordenadorOrDAT": "create_solicitation",
    "IsControleOrSuper": "import_spreadsheet",
    "IsDATOrSuper": "manage_admin_registries",
    "IsComprasDashboardAccess": "view_compras_dashboard",
    "IsDAT": "manage_admin_registries_exclusive",
    "IsControleOrDAT": "operate_preagenda",
    "IsControle": "run_daily_operations",
    "IsGerencia": "supervise_operations",
    "IsDashboardOverview": "view_overview_dashboard",
    "IsMapMetrics": "view_map_metrics",
}

EXCLUDED = {"HasSectorAccess", "IsOwnerOrPrivileged", "IsGerenteSuperintendencia"}


class PermissionClassSweep(VisitorBasedCodemodCommand):
    DESCRIPTION = "Replace legacy Is<Role> permission classes with HasPerm(codename)"

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.BaseExpression:
        if updated_node.value in MAPPING:
            codename = MAPPING[updated_node.value]
            return cst.Call(
                func=cst.Name("HasPerm"),
                args=[cst.Arg(value=cst.SimpleString(f'"{codename}"'))],
            )
        return updated_node

    def leave_ImportFrom(self, original_node, updated_node):
        # Remove imports of legacy classes, add HasPerm if needed
        # ... (implementation)
        pass
```

## Strategy: codemod vs manual sweep

Codemod ganha porque:
- 85+ arquivos tocados; manual = 4h + alto risco de typo silencioso
- Pyright pode passar mesmo com import errado se `from .permissions import *`
- libcst preserva formatação (black/isort não são re-rodados, só o diff real aparece no PR)

Manual resiste onde codemod não alcança:
- Casos com mistura (ex: `[IsAuthenticated, IsDAT, IsOwnerOrPrivileged]` onde só `IsDAT` deve trocar)
- Testes que mockam classes legacy
- Docstrings que mencionam classe legacy

Codemod = 90% auto; 10% review manual na PR.

## Fontes autoritativas

- [libcst documentation](https://libcst.readthedocs.io/)
- [Instagram — libcst codemod use cases](https://engineering.fb.com/2019/03/15/developer-tools/libcst/)
- [DRF — composition vs subclassing permissions](https://www.django-rest-framework.org/api-guide/permissions/#composed-permissions)

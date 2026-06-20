# Epic 6 — RBAC architectural module + lint guard

**Parent plan:** [master-plan.md](./master-plan.md)
**Dependências:** Epic 5 (classes legacy já removidas)
**Bloqueia:** nada (é o último)
**Issues:** 1
**PR size total:** ~400 linhas
**Tempo estimado:** 3h + 24h soak

---

## Por que este epic existe

Sem guard institucional, em 6-12 meses alguém escreve `user.groups.filter(name="DAT")` de novo e a dívida retorna silenciosamente. Este epic:

1. **Consolida** o código RBAC num módulo coeso (`apps/core/rbac/`)
2. **Impõe** a convenção via lint rule custom no CI — PRs com uso proibido falham automaticamente
3. **Documenta** no CONTRIBUTING / CLAUDE.md como fazer RBAC corretamente

## Escopo

### Dentro do escopo
- Criar módulo `apps/core/rbac/` com submódulos: `permissions.py` (HasPerm), `helpers.py` (user_has_any_perm), `constants.py` (role group constants)
- Mover código de `apps/core/permissions.py` + `apps/core/rbac_helpers.py` + `apps/core/constants/rbac.py` para dentro do módulo novo
- Lint rule custom em `v2/backend/tools/rbac_lint.py` (AST-based) que:
  - Proíbe `user.groups.filter(name=...)` em `apps/core/views*/` e `apps/core/services/`
  - Proíbe import direto de Django Group para checagem (whitelist: fixtures, migrations, tests)
  - Proíbe criação de classes permission com padrão `Is<Word>` (exceto whitelist de 3 classes mantidas)
- CI job que roda lint rule e falha PR com violações
- Documentação oficial em `v2/docs/RBAC_NAMING.md` com exemplos good/bad
- Atualizar `CLAUDE.md` (root) com referência ao módulo e convenção

### Fora do escopo
- Lint rule para TypeScript (frontend) — separate concern, baixa prioridade
- Migrar papel ↔ Group unification (ticket separado, fora do scope RBAC)

## Issues

- [ ] **Issue 6.1** — Consolidar módulo `rbac/` + lint rule + docs + CI integration

## Acceptance criteria

- [ ] Estrutura criada:
  ```
  v2/backend/apps/core/rbac/
    __init__.py       # re-exporta API pública
    permissions.py    # HasPerm + mantidas (HasSectorAccess, IsOwnerOrPrivileged, IsGerenteSuperintendencia)
    helpers.py        # user_has_any_perm, user_has_all_perms
    constants.py      # COORDENADOR_ROLE_GROUPS, FORMADOR_ROLE_GROUPS
    README.md         # documentação interna do módulo
  ```
- [ ] `apps/core/permissions.py` deixa de existir OU vira shim de re-export para `apps.core.rbac` (decidir durante execução; prefiro shim para não quebrar imports em branches em andamento)
- [ ] `apps/core/rbac_helpers.py` deletado (moveu para `rbac/helpers.py`)
- [ ] `apps/core/constants/rbac.py` deletado (moveu para `rbac/constants.py`)
- [ ] `v2/backend/tools/rbac_lint.py` criado (AST check)
- [ ] Novo CI job `backend rbac-lint` integrado em `.github/workflows/ci.yaml`
- [ ] Job roda em <20s e falha PR com violações
- [ ] `v2/docs/RBAC_NAMING.md` atualizado com a convenção final
- [ ] `CLAUDE.md` menciona o módulo `apps.core.rbac` como ponto de entrada
- [ ] Grep final (success criteria S1, S2 do master plan) retorna 0
- [ ] Baseline parity test continua verde
- [ ] Teste de auto-verificação: PR synthetic com `user.groups.filter(name="DAT")` em views → lint job falha

## Estrutura do módulo rbac/

```python
# apps/core/rbac/__init__.py
"""
Centralized RBAC (Role-Based Access Control) module.

Public API:
    HasPerm              — Parametric DRF permission class
    user_has_any_perm    — Check if user has ANY of given codenames
    user_has_all_perms   — Check if user has ALL of given codenames
    IsOwnerOrPrivileged  — Object-level: owner or privileged user
    HasSectorAccess      — Dynamic scope check via query param
    COORDENADOR_ROLE_GROUPS  — Data-scope filter constants
    FORMADOR_ROLE_GROUPS     — Data-scope filter constants

Never do:
    user.groups.filter(name="X")         # → use user.has_perm("app.codename")
    class IsDAT(...)                     # → use HasPerm("codename") inline
    permission_classes = [IsControleOrDAT]  # → use HasPerm(...) directly

See: v2/docs/RBAC_NAMING.md
"""
from apps.core.rbac.permissions import (
    HasPerm,
    HasSectorAccess,
    IsGerenteSuperintendencia,
    IsOwnerOrPrivileged,
)
from apps.core.rbac.helpers import user_has_any_perm, user_has_all_perms
from apps.core.rbac.constants import COORDENADOR_ROLE_GROUPS, FORMADOR_ROLE_GROUPS

__all__ = [
    "HasPerm",
    "HasSectorAccess",
    "IsGerenteSuperintendencia",
    "IsOwnerOrPrivileged",
    "user_has_any_perm",
    "user_has_all_perms",
    "COORDENADOR_ROLE_GROUPS",
    "FORMADOR_ROLE_GROUPS",
]
```

## Lint rule (AST)

```python
# v2/backend/tools/rbac_lint.py
"""
Custom AST lint for RBAC convention enforcement.

Violations:
- V001: user.groups.filter(name=...) in views/ or services/
- V002: Class name matching Is<Word> pattern (except whitelist)
- V003: Direct import of Django Group for authz check

Whitelist:
- tests/ — fixtures can create groups by name
- migrations/ — data migrations can reference group names
- fixtures/ — test data
- apps/core/rbac/constants.py — this is the canonical place

Exit code:
- 0 if clean
- 1 if any violation (CI fails)

Usage:
    python v2/backend/tools/rbac_lint.py v2/backend/apps/core/
"""
import ast
import pathlib
import sys
from typing import Iterator

# Permitted legacy class names (object-level or composite)
WHITELISTED_CLASS_NAMES = {"IsOwnerOrPrivileged", "IsGerenteSuperintendencia"}
WHITELIST_PATHS = {"tests", "migrations", "fixtures", "rbac"}

class RBACLintVisitor(ast.NodeVisitor):
    def __init__(self, filepath: pathlib.Path):
        self.filepath = filepath
        self.violations: list[tuple[int, str, str]] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        # V002: Is<Word> class name
        if (
            node.name.startswith("Is")
            and len(node.name) > 2
            and node.name[2].isupper()
            and node.name not in WHITELISTED_CLASS_NAMES
        ):
            self.violations.append(
                (node.lineno, "V002", f"Class '{node.name}' violates RBAC naming: prefer HasPerm()")
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # V001: user.groups.filter(name=...) or groups__name= in filter
        if isinstance(node.func, ast.Attribute) and node.func.attr == "filter":
            for kw in node.keywords:
                if kw.arg == "name" and self._is_group_filter(node):
                    self.violations.append(
                        (node.lineno, "V001", "Use has_perm() instead of groups.filter(name=...)")
                    )
        self.generic_visit(node)

    def _is_group_filter(self, node: ast.Call) -> bool:
        # Walk back to check if func chain has 'groups'
        current = node.func
        while isinstance(current, ast.Attribute):
            if current.attr == "groups":
                return True
            current = current.value
        return False


def should_skip(path: pathlib.Path) -> bool:
    return any(part in WHITELIST_PATHS for part in path.parts)


def check_file(path: pathlib.Path) -> list[tuple[int, str, str]]:
    if should_skip(path):
        return []
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return []
    visitor = RBACLintVisitor(path)
    visitor.visit(tree)
    return [(v[0], v[1], v[2], str(path)) for v in visitor.violations]


def main(root: str) -> int:
    root_path = pathlib.Path(root)
    violations = []
    for py_file in root_path.rglob("*.py"):
        violations.extend(check_file(py_file))

    if not violations:
        print("✓ RBAC lint: no violations")
        return 0

    print(f"✗ RBAC lint: {len(violations)} violation(s):")
    for line, code, msg, path in violations:
        print(f"  {path}:{line} [{code}] {msg}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "apps/core/"))
```

## CI integration

```yaml
# .github/workflows/ci.yaml (adicionar job)
rbac-lint:
  name: '[required] backend rbac-lint'
  runs-on: ubuntu-latest
  needs: setup
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: "3.12"
    - run: |
        cd v2/backend
        python tools/rbac_lint.py apps/core/
```

## Test de self-verification

```python
# v2/backend/apps/core/tests/test_rbac_lint.py
import subprocess, pathlib, pytest

def test_lint_passes_on_current_codebase():
    result = subprocess.run(
        ["python", "tools/rbac_lint.py", "apps/core/"],
        capture_output=True, text=True, cwd="v2/backend",
    )
    assert result.returncode == 0, f"Lint violations:\n{result.stdout}\n{result.stderr}"

def test_lint_catches_violation(tmp_path):
    """Sanity: feed a bad file, expect lint to fail."""
    bad_file = tmp_path / "bad_views.py"
    bad_file.write_text("def view(request): request.user.groups.filter(name='DAT')")
    result = subprocess.run(
        ["python", "tools/rbac_lint.py", str(tmp_path)],
        capture_output=True, text=True, cwd="v2/backend",
    )
    assert result.returncode == 1
    assert "V001" in result.stdout
```

## Documentação final

Após Epic 6, `v2/docs/RBAC_NAMING.md` é **a** referência para RBAC no projeto. PR reviewers, novos devs, Claude Code (via CLAUDE.md) sempre consultam este doc primeiro.

## Fontes autoritativas

- [Python AST — official](https://docs.python.org/3/library/ast.html)
- [GitHub Actions — custom lint jobs in CI](https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/about-custom-actions)
- [Casbin — enforcement gates as architectural pattern](https://casbin.org/docs/overview)

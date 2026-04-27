#!/usr/bin/env python3
"""
RBAC lint — enforça a convenção capability-oriented + Capability Policy Layer.

Histórico:
- Epic 6 (2026-04-24): introduziu V001/V002 banindo `user.groups.filter(name=...)`
  e classes legacy `IsControleOrSuper` etc.
- Epic 4.3 (2026-04-26): atualizou docs/mensagens para refletir Capability Policy
  Layer (`Can*` classes) como forma canônica nova alongside `HasPerm("codename")`.

Sem este guard, em 6-12 meses alguém escreveria `user.groups.filter(name="DAT")`
em uma view e a dívida voltaria.

## Formas canônicas (PERMITIDAS)

1. **Capability Policy Layer (Epic 4.1, preferida quando há OR semântico)**:
   ```python
   from apps.core.rbac import CanAccessAuditLogs
   permission_classes = [CanAccessAuditLogs]
   ```

2. **HasPerm direto (single capability)**:
   ```python
   from apps.core.rbac import HasPerm
   permission_classes = [HasPerm("approve_solicitation")]
   ```

3. **DRF built-ins**: `IsAuthenticated`, `AllowAny`, `IsAdminUser` (via
   `rest_framework.permissions`).

4. **Composition OR temporária** (`HasPerm("a") | HasPerm("b")`): aceita pelo
   lint atual; cleanup via Policy Layer é incremental (Epic 4.6 follow-up).

5. **Whitelist de classes não-reduzíveis**: `IsGerenteSuperintendencia` (composite
   funcperm + grupo Django) e `IsOwnerOrPrivileged` (object-level).

## Regras enforçadas

- **V001** `user.groups.filter(name=...)` em `apps/core/views*/` ou
  `apps/core/services/`. Usar `user_has_any_perm(user, "<codename>")` ou
  `HasPerm("<codename>")`. Se o uso for legítimo (composite, block, data scope),
  adicionar marcador `# noqa: RBAC-<tipo>-allowed` na mesma linha.

- **V002** `class Is<Word>(...):` fora da whitelist (`IsGerenteSuperintendencia`,
  `IsOwnerOrPrivileged`). Use a forma canônica nova:
  `Can<Word>` (Capability Policy Layer) ou `HasPerm(codename)` inline.

  Nota: classes `Can*` são automaticamente aceitas (não match no V002 — só
  prefixo `Is<Upper>` é banido). Não precisam whitelist.

Whitelist de paths (não linta):
- `tests/`, `migrations/`, `fixtures/` (test data e data migrations podem
  referenciar nomes de grupos por design)
- `apps/core/rbac/` (o próprio módulo RBAC, incluindo `policies.py` Epic 4.1)
- `apps/core/constants.py`, `apps/core/permissions.py`, `apps/core/rbac_helpers.py`
  (shims e data-scope constants)
- `scripts/rbac_lint.py`, `scripts/rbac_codemod.py` (o próprio lint e histórico)

Exit code:
- 0 se limpo
- 1 se alguma violação (CI falha)

Uso:
    python scripts/rbac_lint.py apps/core/
    python scripts/rbac_lint.py apps/           # scan tudo
"""

from __future__ import annotations

import ast
import pathlib
import sys
from collections.abc import Iterable
from dataclasses import dataclass

# Classes `Is<Word>` permitidas (não-reduzíveis a HasPerm — ver RBAC_NAMING §3).
WHITELISTED_CLASS_NAMES: frozenset[str] = frozenset(
    {
        "IsGerenteSuperintendencia",  # composite: funcperm + grupo Django
        "IsOwnerOrPrivileged",  # object-level: checa obj.usuario
    }
)

# Substrings de path que isentam um arquivo do lint.
# Usamos substring (não exact) para cobrir variações (apps/core/tests vs
# apps/dev_tools/tests, etc).
WHITELIST_PATH_SUBSTRINGS: tuple[str, ...] = (
    "/tests/",
    "\\tests\\",
    "/migrations/",
    "\\migrations\\",
    "/fixtures/",
    "\\fixtures\\",
    "/apps/core/rbac/",
    "\\apps\\core\\rbac\\",
    # `apps/dev_tools/` é seed/admin tooling por design — comandos como
    # `seed_gerentes`, `seed_rbac`, `seed_e2e_users` criam e atribuem
    # grupos por nome, que é operação legítima de bootstrap, não authz.
    "/apps/dev_tools/",
    "\\apps\\dev_tools\\",
    "/scripts/rbac_lint.py",
    "\\scripts\\rbac_lint.py",
    "/scripts/rbac_codemod.py",
    "\\scripts\\rbac_codemod.py",
)

# Arquivos específicos whitelisted (shims + data-scope SSOT).
WHITELIST_EXACT_FILES: tuple[str, ...] = (
    "apps/core/constants.py",
    "apps/core/permissions.py",
    "apps/core/rbac_helpers.py",
)

# Kwargs de filter/exclude que indicam authz por nome de grupo.
GROUP_NAME_KWARGS: frozenset[str] = frozenset({"name", "name__in", "name__exact", "name__iexact"})


@dataclass(frozen=True)
class Violation:
    filepath: str
    lineno: int
    code: str
    message: str


class RBACLintVisitor(ast.NodeVisitor):
    """Varre um AST procurando violações V001/V002."""

    def __init__(self, filepath: pathlib.Path, source_lines: list[str]) -> None:
        self.filepath: pathlib.Path = filepath
        self.source_lines: list[str] = source_lines
        self.violations: list[Violation] = []

    # V002 — nomes de classe começando com Is<Upper>
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        name = node.name
        if name.startswith("Is") and len(name) > 2 and name[2].isupper() and name not in WHITELISTED_CLASS_NAMES:
            self.violations.append(
                Violation(
                    filepath=str(self.filepath),
                    lineno=node.lineno,
                    code="V002",
                    message=(
                        f"Classe '{name}' viola convenção RBAC. Formas canônicas:\n"
                        f"    1. Capability Policy Layer:  permission_classes = [CanXxx]\n"
                        f"    2. HasPerm direto:           permission_classes = [HasPerm('codename')]\n"
                        f"    3. DRF built-ins:            IsAuthenticated, AllowAny, IsAdminUser\n"
                        f"  Whitelist (não-reduzíveis): {sorted(WHITELISTED_CLASS_NAMES)}\n"
                        f"  Ver v2/docs/RBAC_NAMING.md §3 e §9 (Policy Resolution Rules)."
                    ),
                )
            )
        self.generic_visit(node)

    # V001 — groups.filter(name=...) ou equivalentes
    def visit_Call(self, node: ast.Call) -> None:
        if self._is_groups_filter_with_name_kw(node) and not self._has_noqa_marker(node.lineno):
            self.violations.append(
                Violation(
                    filepath=str(self.filepath),
                    lineno=node.lineno,
                    code="V001",
                    message=(
                        "user.groups.filter(name=...) é bypass do RBAC funcional. "
                        "Use user_has_any_perm(user, '<codename>') / HasPerm('<codename>'). "
                        "Se o uso for legítimo, adicione '# noqa: RBAC-<tipo>-allowed' na linha."
                    ),
                )
            )
        self.generic_visit(node)

    @staticmethod
    def _is_groups_filter_with_name_kw(node: ast.Call) -> bool:
        """True se `node` é `<expr>.groups.filter(name=...)` (ou variantes)."""
        func = node.func
        if not isinstance(func, ast.Attribute):
            return False
        if func.attr not in ("filter", "exclude"):
            return False
        inner = func.value
        if not isinstance(inner, ast.Attribute):
            return False
        if inner.attr != "groups":
            return False
        return any(kw.arg in GROUP_NAME_KWARGS for kw in node.keywords if kw.arg)

    def _has_noqa_marker(self, lineno: int) -> bool:
        """True se a linha tem '# noqa: RBAC-<tipo>-allowed'."""
        if lineno < 1 or lineno > len(self.source_lines):
            return False
        line = self.source_lines[lineno - 1]
        return "# noqa: RBAC-" in line and "-allowed" in line


def _is_path_whitelisted(path: pathlib.Path, root: pathlib.Path) -> bool:
    """True se `path` está na whitelist (não deve ser lintado)."""
    path_str = str(path).replace("\\", "/")
    # Substrings (cobre dirs em qualquer nível)
    if any(s.replace("\\", "/") in path_str for s in WHITELIST_PATH_SUBSTRINGS):
        return True
    # Arquivos exatos — normalizar relativo ao root
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        rel = path.as_posix()
    if rel in WHITELIST_EXACT_FILES:
        return True
    # Casos onde o user passa o próprio arquivo — cheque por suffix
    return any(rel.endswith("/" + f) or rel == f for f in WHITELIST_EXACT_FILES)


def check_file(path: pathlib.Path, root: pathlib.Path) -> list[Violation]:
    if _is_path_whitelisted(path, root):
        return []
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []
    visitor = RBACLintVisitor(path, source.splitlines())
    visitor.visit(tree)
    return visitor.violations


def iter_py_files(root: pathlib.Path) -> Iterable[pathlib.Path]:
    if root.is_file():
        if root.suffix == ".py":
            yield root
        return
    for py in root.rglob("*.py"):
        yield py


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Uso: python scripts/rbac_lint.py <dir_ou_arquivo>", file=sys.stderr)
        return 2
    target = pathlib.Path(argv[1]).resolve()
    if not target.exists():
        print(f"Path não encontrado: {target}", file=sys.stderr)
        return 2

    root = target if target.is_dir() else target.parent
    violations: list[Violation] = []
    for py_file in iter_py_files(target):
        violations.extend(check_file(py_file, root))

    if not violations:
        print("OK RBAC lint: 0 violacoes")
        return 0

    print(f"X RBAC lint: {len(violations)} violacao(oes):", file=sys.stderr)
    for v in violations:
        rel = pathlib.Path(v.filepath)
        try:
            rel = rel.relative_to(pathlib.Path.cwd())
        except ValueError:
            pass
        print(f"  {rel}:{v.lineno} [{v.code}] {v.message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))

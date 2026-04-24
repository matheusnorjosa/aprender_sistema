"""
Epic 5 RBAC Refactor — codemod para substituir 12 classes factory
legacy por `HasPerm(codename)` em todo o backend.

Usage:
    python scripts/rbac_codemod.py --dry-run <file_or_dir>
    python scripts/rbac_codemod.py --apply <file_or_dir>

Passos aplicados:
1. Remover imports das 12 classes legacy (`IsDAT`, `IsControleOrSuper`, ...)
2. Adicionar import `HasPerm` se há qualquer substituição
3. Substituir `permission_classes = [IsDAT]` → `[HasPerm("manage_purchases_and_materials")]`
4. Substituir `@permission_classes([IsDAT])` (decorator) idem
5. Substituir referências inline `IsDAT()` → `HasPerm("manage_purchases_and_materials")`
6. Preservar as 3 classes mantidas (`IsGerenteSuperintendencia`,
   `IsOwnerOrPrivileged`, `HasSectorAccess`) inalteradas

Ver v2/docs/plans/rbac-refactor/epic-5-class-sweep.md.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Mapeamento canônico: classe legacy → HasPerm(codename_novo).
# Espelha o mapeamento de Epic 4.2 (codenames verb_noun já aplicados).
CLASS_TO_CODENAME: dict[str, str] = {
    "IsSuperintendencia": "approve_solicitation",
    "IsSuperintendenciaOnly": "execute_restricted_operations",
    "IsCoordenadorOrDAT": "create_solicitation",
    "IsControleOrSuper": "import_spreadsheet",
    "IsDATOrSuper": "manage_admin_registries",
    "IsComprasDashboardAccess": "view_compras_dashboard",
    "IsDAT": "manage_purchases_and_materials",
    "IsControleOrDAT": "operate_preagenda",
    "IsControle": "run_daily_operations",
    "IsGerencia": "supervise_operations",
    "IsDashboardOverview": "view_overview_dashboard",
    "IsMapMetrics": "view_map_metrics",
}

# Classes que DEVEM ser mantidas (object-level, composite, dynamic scope).
KEEP_CLASSES: frozenset[str] = frozenset({"IsGerenteSuperintendencia", "IsOwnerOrPrivileged", "HasSectorAccess"})


def transform_source(source: str) -> tuple[str, int]:
    """
    Aplica as substituições ao source code. Retorna (novo_source, n_changes).
    """
    new_source = source
    changes = 0

    # Passo 1: substituir uso `ClassName` → `HasPerm("codename")` em contextos
    # de permission_classes (lista) e inline.
    # Padrão: ClassName como identifier ou instanciação — em permission_classes.
    # Usamos \b e não confundimos com KEEP_CLASSES ou prefixos.
    for legacy_class, codename in CLASS_TO_CODENAME.items():
        # Substituir em `permission_classes([X, Y])` e `[X, Y]` listings:
        # pattern: `\bLegacyClass\b(?!\s*=)` (não em atribuição/definição)
        # Trocamos apenas quando o token está sozinho em expressão (não como
        # base class de `class X(Legacy):`).
        # Abordagem simples: substituir todas as ocorrências do identifier
        # exceto:
        # - Em `class XXX(LegacyClass)` (herança — já foi migrada em 4.2)
        # - Em linhas com `from .permissions import` (tratadas no passo 2)
        pattern = rf"\b{legacy_class}\b"

        def _replace(match: re.Match[str], codename: str = codename, legacy: str = legacy_class) -> str:
            nonlocal changes
            # Verifica contexto: se está em linha de import, deixa (será limpo
            # no passo 2). Se está em `class X(Legacy)`, deixa. Caso contrário,
            # substitui por HasPerm("codename").
            start = match.start()
            # Busca começo da linha
            line_start = new_source.rfind("\n", 0, start) + 1
            line = new_source[line_start : new_source.find("\n", start)]
            if re.match(r"\s*(from|import)\s+", line):
                return legacy  # não muda; passo 2 remove
            if re.match(r"\s*class\s+", line):
                return legacy  # classe def ou herança; não substitui
            changes += 1
            return f'HasPerm("{codename}")'

        new_source = re.sub(pattern, _replace, new_source)

    # Passo 2: limpar imports legacy (remove referências em `from ... import`)
    # e garantir que HasPerm está importado se houve substituições.
    # Pattern: `from (...).permissions import ...IsDAT, IsControle, ...`
    def _clean_import_line(match: re.Match[str]) -> str:
        nonlocal changes
        prefix = match.group(1)
        names_str = match.group(2)
        names = [n.strip() for n in names_str.split(",") if n.strip()]
        kept = [n for n in names if n in KEEP_CLASSES or n not in CLASS_TO_CODENAME]
        # Garante HasPerm se substituímos alguma classe
        removed_any = any(n in CLASS_TO_CODENAME for n in names)
        if removed_any and "HasPerm" not in kept:
            kept.append("HasPerm")
        if not kept:
            changes += 1
            return ""  # remove a linha inteira
        if kept == names:
            return match.group(0)  # nenhuma mudança
        changes += 1
        return f"{prefix}{', '.join(sorted(kept))}"

    # Match imports from permissions module
    import_pattern = re.compile(
        r"(from\s+[\w.]*\.?permissions\s+import\s+)([^\n]+)",
    )
    new_source = import_pattern.sub(_clean_import_line, new_source)

    # Remove linhas vazias de import que ficaram (a substituição acima retorna ""
    # mas fica "\n" na string — normalize linhas órfãs)
    new_source = re.sub(r"\n\n\n+", "\n\n", new_source)

    return new_source, changes


def process_file(path: Path, apply: bool) -> tuple[int, str, str]:
    """
    Processa um arquivo. Retorna (n_changes, original, new).
    Se apply=True, escreve o novo source no arquivo.
    """
    original = path.read_text(encoding="utf-8")
    new_source, changes = transform_source(original)
    if apply and changes > 0:
        path.write_text(new_source, encoding="utf-8")
    return changes, original, new_source


def main() -> int:
    parser = argparse.ArgumentParser(description="RBAC codemod (Epic 5)")
    parser.add_argument("targets", nargs="+", help="Files or directories to process")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default: dry-run)")
    parser.add_argument("--quiet", action="store_true", help="Only print summary")
    args = parser.parse_args()

    files_to_process: list[Path] = []
    for target_str in args.targets:
        target = Path(target_str)
        if target.is_file() and target.suffix == ".py":
            files_to_process.append(target)
        elif target.is_dir():
            files_to_process.extend(target.rglob("*.py"))
        else:
            print(f"[WARN] ignoring {target}", file=sys.stderr)

    # Excluir arquivos do próprio módulo de permissões + migrations + o próprio tool
    EXCLUDE_PATTERNS = (
        "apps/core/permissions.py",
        "apps/core/migrations/",
        "scripts/rbac_codemod.py",
        "tests/test_permissions_hasperm.py",
    )

    filtered: list[Path] = []
    for f in files_to_process:
        s = str(f).replace("\\", "/")
        if any(pat in s for pat in EXCLUDE_PATTERNS):
            continue
        filtered.append(f)

    total_changes = 0
    files_changed = 0
    for path in filtered:
        changes, original, new = process_file(path, apply=args.apply)
        if changes > 0:
            files_changed += 1
            total_changes += changes
            if not args.quiet:
                marker = "[APPLIED]" if args.apply else "[DRY-RUN]"
                print(f"{marker} {path}: {changes} change(s)")

    mode = "applied" if args.apply else "would change"
    print(f"\n{files_changed} file(s) {mode}, {total_changes} total replacements.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

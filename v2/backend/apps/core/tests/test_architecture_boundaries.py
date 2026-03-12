"""
Guard rails arquiteturais para apps.core.

Este teste impede regressao de acoplamento ciclico entre apps:
apps.core nao deve importar apps.dat_ingest diretamente.
"""

from __future__ import annotations

import ast
from pathlib import Path


CORE_APP_DIR = Path(__file__).resolve().parents[1]


def _iter_core_python_files() -> list[Path]:
    files: list[Path] = []
    for path in CORE_APP_DIR.rglob("*.py"):
        posix_path = path.as_posix()
        if "/tests/" in posix_path or "/migrations/" in posix_path:
            continue
        files.append(path)
    return files


def _imports_dat_ingest(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "apps.dat_ingest" or alias.name.startswith("apps.dat_ingest."):
                    return True
            continue

        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "apps.dat_ingest" or module.startswith("apps.dat_ingest."):
                return True

    return False


def test_core_must_not_import_dat_ingest() -> None:
    violating_files = [
        str(path.relative_to(CORE_APP_DIR))
        for path in _iter_core_python_files()
        if _imports_dat_ingest(path)
    ]

    assert not violating_files, (
        "apps.core nao deve importar apps.dat_ingest diretamente.\n"
        f"Arquivos com violacao: {sorted(violating_files)}"
    )

from __future__ import annotations

import os
import shutil
import site
import subprocess
import sys
import sysconfig
from pathlib import Path


def _candidate_script_dirs() -> list[Path]:
    dirs: list[Path] = []
    script_dir = sysconfig.get_path("scripts")
    if script_dir:
        dirs.append(Path(script_dir))

    user_site = site.getusersitepackages()
    if user_site:
        user_site_path = Path(user_site)
        dirs.append(user_site_path.parent / ("Scripts" if os.name == "nt" else "bin"))

    user_bin = Path(site.USER_BASE) / ("Scripts" if os.name == "nt" else "bin")
    dirs.append(user_bin)

    return dirs


def _resolve_lint_imports_binary() -> str | None:
    for binary_name in ("lint-imports", "lint-imports.exe"):
        located = shutil.which(binary_name)
        if located:
            return located

    for script_dir in _candidate_script_dirs():
        for binary_name in ("lint-imports", "lint-imports.exe"):
            candidate = script_dir / binary_name
            if candidate.exists():
                return str(candidate)

    return None


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    config_file = project_root / ".importlinter"
    if not config_file.exists():
        print(f"Config file not found: {config_file}", file=sys.stderr)
        return 2

    lint_binary = _resolve_lint_imports_binary()
    if not lint_binary:
        print(
            "Could not find 'lint-imports'. Install with: python -m pip install import-linter==2.6",
            file=sys.stderr,
        )
        return 2

    command = [lint_binary, "--config", str(config_file)]
    completed = subprocess.run(command, cwd=project_root)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())

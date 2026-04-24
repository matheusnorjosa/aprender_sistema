"""
Self-verification do lint RBAC (Epic 6).

Verifica que:
1. O lint aceita o codebase atual (baseline limpo).
2. O lint rejeita um arquivo sintético com violação V001.
3. O lint rejeita um arquivo sintético com violação V002.
4. O lint aceita um arquivo V001 com marcador noqa válido.
5. Paths whitelisted (tests/, migrations/) são ignorados.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingTypeStubs=false

from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

# parents[0]=tests, [1]=core, [2]=apps, [3]=backend root (local: v2/backend, container: /app)
BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[3]
LINT_SCRIPT = BACKEND_ROOT / "scripts" / "rbac_lint.py"


def _run_lint(target: pathlib.Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(LINT_SCRIPT), str(target)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_lint_script_exists():
    assert LINT_SCRIPT.exists(), f"rbac_lint.py não encontrado em {LINT_SCRIPT}"


def test_lint_passes_on_current_apps_core():
    """Baseline: o codebase atual passa limpo."""
    target = BACKEND_ROOT / "apps" / "core"
    result = _run_lint(target)
    assert result.returncode == 0, (
        f"Lint violações inesperadas no baseline:\n" f"STDOUT: {result.stdout}\n" f"STDERR: {result.stderr}"
    )


def test_lint_catches_v001_in_views(tmp_path):
    """Feed bad view — expect V001 violation."""
    views_dir = tmp_path / "apps" / "core" / "views_fake"
    views_dir.mkdir(parents=True)
    (views_dir / "bad_view.py").write_text(
        "def handler(request):\n" "    return request.user.groups.filter(name='DAT').exists()\n"
    )
    result = _run_lint(views_dir)
    assert result.returncode == 1
    assert "V001" in result.stderr


def test_lint_catches_v002_class_name(tmp_path):
    """Feed Is<Word> class — expect V002 violation."""
    mod = tmp_path / "bad_module.py"
    mod.write_text("class IsDATManager:\n" "    pass\n")
    result = _run_lint(mod)
    assert result.returncode == 1
    assert "V002" in result.stderr


def test_lint_accepts_noqa_marker(tmp_path):
    """V001 com `# noqa: RBAC-block-allowed` é aceito."""
    views_dir = tmp_path / "apps" / "core" / "views_fake"
    views_dir.mkdir(parents=True)
    (views_dir / "allowed_view.py").write_text(
        "def handler(request):\n"
        "    # Block específico por design documentado.\n"
        "    return request.user.groups.filter(name='Controle').exists()  # noqa: RBAC-block-allowed\n"
    )
    result = _run_lint(views_dir)
    assert result.returncode == 0, f"Esperava passar com noqa, mas: {result.stderr}"


def test_lint_skips_tests_path(tmp_path):
    """Arquivos em tests/ devem ser ignorados (fixtures podem usar nomes de grupo)."""
    tests_dir = tmp_path / "apps" / "core" / "tests"
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_something.py").write_text(
        "def test_user_has_group(user):\n" "    assert user.groups.filter(name='Coordenador').exists()\n"
    )
    result = _run_lint(tests_dir)
    assert result.returncode == 0, f"Esperava pular tests/, mas deu erro: {result.stderr}"


def test_lint_skips_dev_tools_path(tmp_path):
    """Arquivos em apps/dev_tools/ devem ser ignorados (seeds manipulam grupos por design)."""
    seeds_dir = tmp_path / "apps" / "dev_tools" / "management" / "commands"
    seeds_dir.mkdir(parents=True)
    (seeds_dir / "seed_fake.py").write_text(
        "def handle(user):\n"
        "    if not user.groups.filter(name='Gerência').exists():\n"
        "        user.groups.add(...)\n"
    )
    result = _run_lint(seeds_dir)
    assert result.returncode == 0, f"Esperava pular apps/dev_tools/, mas deu erro: {result.stderr}"


def test_lint_whitelisted_classes_pass(tmp_path):
    """IsGerenteSuperintendencia e IsOwnerOrPrivileged são whitelisted (V002)."""
    mod = tmp_path / "apps" / "sample" / "permissions.py"
    mod.parent.mkdir(parents=True)
    mod.write_text("class IsGerenteSuperintendencia:\n" "    pass\n" "class IsOwnerOrPrivileged:\n" "    pass\n")
    result = _run_lint(mod.parent)
    assert result.returncode == 0, f"Esperava whitelist passar, mas: {result.stderr}"


@pytest.mark.parametrize(
    "bad_call",
    [
        "request.user.groups.filter(name='DAT').exists()",
        "user.groups.filter(name__in=['DAT', 'Controle']).exists()",
        "usuario.groups.exclude(name='Superintendência')",
    ],
)
def test_lint_v001_variants(tmp_path, bad_call):
    """V001 pega variantes: name=, name__in=, exclude()."""
    views_dir = tmp_path / "apps" / "core" / "views_fake"
    views_dir.mkdir(parents=True)
    (views_dir / "bad.py").write_text(f"def h():\n    {bad_call}\n")
    result = _run_lint(views_dir)
    assert result.returncode == 1, f"Esperava V001 em '{bad_call}', mas passou."
    assert "V001" in result.stderr

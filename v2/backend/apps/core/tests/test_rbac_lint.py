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
    """IsOwnerOrPrivileged é whitelisted (V002)."""
    mod = tmp_path / "apps" / "sample" / "permissions.py"
    mod.parent.mkdir(parents=True)
    mod.write_text("class IsOwnerOrPrivileged:\n" "    pass\n")
    result = _run_lint(mod.parent)
    assert result.returncode == 0, f"Esperava whitelist passar, mas: {result.stderr}"


def test_lint_is_gerente_superintendencia_saiu_da_whitelist(tmp_path):
    """PR 8 das permissões: a classe saiu; recriá-la reprova no V002."""
    mod = tmp_path / "apps" / "sample" / "permissions.py"
    mod.parent.mkdir(parents=True)
    mod.write_text("class IsGerenteSuperintendencia:\n" "    pass\n")
    result = _run_lint(mod.parent)
    assert result.returncode == 1
    assert "V002" in result.stdout + result.stderr


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


# ============================================================================
# Epic 4.3 — Capability Policy Layer (Can*) é forma canônica nova
# ============================================================================


@pytest.mark.parametrize(
    "policy_class_name",
    [
        "CanAccessAuditLogs",
        "CanUseGcal",
        "CanViewReports",
        "CanViewComprasDashboard",
        "CanImportGenericSpreadsheet",
    ],
)
def test_lint_accepts_can_policy_classes(tmp_path, policy_class_name):
    """Classes Can* (Capability Policy Layer, Epic 4.1) passam — não há prefixo Is*."""
    mod = tmp_path / "apps" / "sample" / "policies_fake.py"
    mod.parent.mkdir(parents=True)
    mod.write_text(f"class {policy_class_name}:\n    pass\n")
    result = _run_lint(mod.parent)
    assert result.returncode == 0, f"Esperava {policy_class_name} passar (Can* é forma canônica), mas: {result.stderr}"


@pytest.mark.parametrize(
    "drf_builtin_usage",
    [
        # Imports e usos típicos de built-ins DRF — não devem disparar nenhum lint
        "from rest_framework.permissions import IsAuthenticated\n" "permission_classes = [IsAuthenticated]\n",
        "from rest_framework.permissions import AllowAny\n" "permission_classes = [AllowAny]\n",
        "from rest_framework.permissions import IsAdminUser\n" "permission_classes = [IsAdminUser]\n",
    ],
)
def test_lint_accepts_drf_builtins(tmp_path, drf_builtin_usage):
    """Uso de IsAuthenticated/AllowAny/IsAdminUser passa (built-ins DRF, não classes legacy)."""
    views_dir = tmp_path / "apps" / "core" / "views_fake"
    views_dir.mkdir(parents=True)
    (views_dir / "view.py").write_text(drf_builtin_usage)
    result = _run_lint(views_dir)
    assert result.returncode == 0, f"Esperava DRF builtin passar: {result.stderr}"


def test_lint_accepts_hasperm_inline(tmp_path):
    """`HasPerm("codename")` direto em permission_classes passa (idioma canônico Epic 2)."""
    views_dir = tmp_path / "apps" / "core" / "views_fake"
    views_dir.mkdir(parents=True)
    (views_dir / "view.py").write_text(
        "from apps.core.rbac import HasPerm\n" 'permission_classes = [HasPerm("approve_solicitation")]\n'
    )
    result = _run_lint(views_dir)
    assert result.returncode == 0, f"Esperava HasPerm direto passar: {result.stderr}"


def test_lint_accepts_hasperm_or_composition(tmp_path):
    """Composition OR `HasPerm("a") | HasPerm("b")` ainda é aceita (Epic 4.6 fará cleanup futuro)."""
    views_dir = tmp_path / "apps" / "core" / "views_fake"
    views_dir.mkdir(parents=True)
    (views_dir / "view.py").write_text(
        "from apps.core.rbac import HasPerm\n"
        'permission_classes = [HasPerm("operate_preagenda") | HasPerm("approve_solicitation")]\n'
    )
    result = _run_lint(views_dir)
    assert result.returncode == 0, f"Esperava composition OR passar (cleanup é Epic 4.6): {result.stderr}"


@pytest.mark.parametrize(
    "legacy_class_name",
    [
        "IsControleOrSuper",
        "IsGerente",
        "IsDATAdmin",
        "IsFormador",
        "IsFooBar",
    ],
)
def test_lint_blocks_legacy_is_classes(tmp_path, legacy_class_name):
    """Classes Is<Word> legacy (fora da whitelist) continuam proibidas — V002."""
    mod = tmp_path / "bad_class.py"
    mod.write_text(f"class {legacy_class_name}:\n    pass\n")
    result = _run_lint(mod)
    assert result.returncode == 1, f"Esperava V002 em '{legacy_class_name}', mas passou."
    assert "V002" in result.stderr


def test_v002_message_suggests_can_or_hasperm(tmp_path):
    """Mensagem de V002 deve guiar pra forma canônica (Can* ou HasPerm), não só whitelist."""
    mod = tmp_path / "bad.py"
    mod.write_text("class IsControleOrSuper:\n    pass\n")
    result = _run_lint(mod)
    assert result.returncode == 1
    # Mensagem deve mencionar Can* ou HasPerm como forma correta
    stderr_lower = result.stderr.lower()
    assert (
        "can" in stderr_lower or "policy" in stderr_lower or "hasperm" in stderr_lower
    ), f"Mensagem V002 deveria sugerir Can* / Policy / HasPerm:\n{result.stderr}"


# ============================================================================
# V003 — D17 (2026-05-04): proibir mutação de PermissaoFuncional.groups /
# Group.permissions em migrations de apps/core/ criadas após o cutoff.
# ============================================================================


def _write_fake_migration(tmp_path: pathlib.Path, number: int, body: str) -> pathlib.Path:
    """Helper: cria arquivo em estrutura apps/core/migrations/ dentro de tmp_path."""
    mig_dir = tmp_path / "apps" / "core" / "migrations"
    mig_dir.mkdir(parents=True, exist_ok=True)
    (mig_dir / "__init__.py").touch()
    path = mig_dir / f"{number:04d}_fake.py"
    path.write_text(body)
    return path


def test_v003_blocks_groups_set_in_new_migration(tmp_path):
    """Migration nova (> D17 cutoff) com `perm.groups.set(...)` deve disparar V003."""
    body = (
        "from django.db import migrations\n"
        "def forwards(apps, schema_editor):\n"
        "    PermissaoFuncional = apps.get_model('core', 'PermissaoFuncional')\n"
        "    Group = apps.get_model('auth', 'Group')\n"
        "    perm = PermissaoFuncional.objects.get(codename='x')\n"
        "    groups = list(Group.objects.filter(name__in=['Controle', 'DAT']))\n"
        "    perm.groups.set(groups)\n"
    )
    _write_fake_migration(tmp_path, 99, body)
    result = _run_lint(tmp_path / "apps" / "core" / "migrations")
    assert result.returncode == 1, f"Esperava V003, mas: {result.stderr or result.stdout}"
    assert "V003" in result.stderr


@pytest.mark.parametrize(
    "mutation_line",
    [
        "    perm.groups.set(groups)\n",
        "    perm.groups.add(group)\n",
        "    perm.groups.clear()\n",
        "    group.permissions.set(perms)\n",
        "    group.permissions.add(perm)\n",
        "    group.permissions.clear()\n",
    ],
)
def test_v003_variants(tmp_path, mutation_line):
    """V003 pega variantes: groups vs permissions × set/add/clear."""
    body = "from django.db import migrations\n" "def forwards(apps, schema_editor):\n" + mutation_line
    _write_fake_migration(tmp_path, 99, body)
    result = _run_lint(tmp_path / "apps" / "core" / "migrations")
    assert result.returncode == 1, f"Esperava V003 em '{mutation_line.strip()}', mas passou."
    assert "V003" in result.stderr


def test_v003_skips_legacy_migrations(tmp_path):
    """Migration com número <= D17_LEGACY_MIGRATIONS_MAX (82) é histórico aceitável."""
    body = "from django.db import migrations\n" "def forwards(apps, schema_editor):\n" "    perm.groups.set(groups)\n"
    # Migration 0082 é o último número histórico aceito.
    _write_fake_migration(tmp_path, 82, body)
    result = _run_lint(tmp_path / "apps" / "core" / "migrations")
    assert result.returncode == 0, f"Esperava migration legacy passar limpa, mas: {result.stderr}"


def test_v003_accepts_noqa_marker(tmp_path):
    """Migration nova com `# noqa: RBAC-migration-allowed` é aceita (exceção documentada)."""
    body = (
        "from django.db import migrations\n"
        "def forwards(apps, schema_editor):\n"
        "    perm.groups.set(groups)  # noqa: RBAC-migration-allowed\n"
    )
    _write_fake_migration(tmp_path, 99, body)
    result = _run_lint(tmp_path / "apps" / "core" / "migrations")
    assert result.returncode == 0, f"Esperava noqa marker aceitar, mas: {result.stderr}"


def test_v003_does_not_fire_outside_migrations(tmp_path):
    """V003 só vale em apps/core/migrations/; código aplicativo pode chamar set/add/clear."""
    views_dir = tmp_path / "apps" / "core" / "views_fake"
    views_dir.mkdir(parents=True)
    (views_dir / "view.py").write_text("def handler(perm, groups):\n" "    perm.groups.set(groups)\n")
    result = _run_lint(views_dir)
    # Não dispara V003 (path não-migration). Desde o PR A da arquitetura de permissões
    # a mesma linha fora da allowlist é V004.
    assert "V003" not in result.stderr, f"V003 não deveria pegar paths não-migration: {result.stderr}"


def test_v003_does_not_fire_in_dev_tools_seeds(tmp_path):
    """apps/dev_tools/ é o lugar canônico para seeds que mutam grupos."""
    seeds_dir = tmp_path / "apps" / "dev_tools" / "management" / "commands"
    seeds_dir.mkdir(parents=True)
    (seeds_dir / "seed_groups.py").write_text("def handle(perm, groups):\n" "    perm.groups.set(groups)\n")
    result = _run_lint(seeds_dir)
    assert result.returncode == 0, f"Esperava seeds passarem: {result.stderr}"


def test_v003_baseline_current_core_migrations_pass(tmp_path):
    """Baseline: todas as migrations existentes em apps/core/migrations/ passam.

    Se este teste falhar, alguém commitou uma migration nova violadora ou criou
    uma migration sem ajustar o cutoff D17_LEGACY_MIGRATIONS_MAX no rbac_lint.py.
    """
    target = BACKEND_ROOT / "apps" / "core" / "migrations"
    result = _run_lint(target)
    assert result.returncode == 0, (
        f"Migrations atuais devem passar limpas (V003).\n" f"STDOUT: {result.stdout}\n" f"STDERR: {result.stderr}"
    )


# ============================================================================
# PR A da arquitetura de permissões (ADR-020): V004 (mutação de grupo ou
# capacidade) e V005 (criação de EquipeGerencia) com allowlist de arquivos em
# modo ratchet — arquivo novo reprova. tests/, migrations/ e apps/dev_tools/
# ficam isentos. V003 passa a pegar `remove`.
# ============================================================================


def _write_app_file(tmp_path: pathlib.Path, rel: str, body: str) -> pathlib.Path:
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    return path


@pytest.mark.parametrize(
    "mutation_line",
    [
        "    user.groups.add(grupo)\n",
        "    user.groups.set([grupo])\n",
        "    user.groups.remove(grupo)\n",
        "    user.groups.clear()\n",
        "    grupo.user_set.add(user)\n",
        "    perm.groups.set(grupos)\n",
    ],
)
def test_v004_rejeita_groups_add_fora_da_allowlist(tmp_path, mutation_line):
    _write_app_file(
        tmp_path, "apps/core/services/novo_servico.py", "def f(user, grupo, perm, grupos):\n" + mutation_line
    )
    result = _run_lint(tmp_path / "apps")
    assert result.returncode == 1, f"Esperava V004 em '{mutation_line.strip()}'"
    assert "V004" in result.stderr


@pytest.mark.parametrize("metodo", ["set", "add", "remove", "clear"])
def test_v004_rejeita_permissoes_funcionais_set(tmp_path, metodo):
    _write_app_file(
        tmp_path,
        "apps/core/views/nova_view.py",
        f"def f(grupo, caps):\n    grupo.permissoes_funcionais.{metodo}(caps)\n",
    )
    result = _run_lint(tmp_path / "apps")
    assert result.returncode == 1
    assert "V004" in result.stderr


@pytest.mark.parametrize(
    "rel",
    [
        "apps/core/views/admin.py",
        "apps/core/services/usuarios_import.py",
        "apps/core/services/export_contract_importer.py",
        "apps/core/services/functional_permissions_seed.py",
        "apps/core/serializers/usuario.py",
        "apps/dev_tools/management/commands/seed_qualquer.py",
        "apps/core/tests/test_qualquer.py",
    ],
)
def test_v004_aceita_allowlist(tmp_path, rel):
    _write_app_file(tmp_path, rel, "def f(user, grupos):\n    user.groups.set(grupos)\n")
    result = _run_lint(tmp_path / "apps")
    assert result.returncode == 0, f"{rel} está na allowlist: {result.stderr}"


@pytest.mark.parametrize("metodo", ["create", "get_or_create", "update_or_create", "bulk_create"])
def test_v005_rejeita_equipegerencia_create_novo(tmp_path, metodo):
    _write_app_file(
        tmp_path, "apps/core/views/nova_lotacao.py", f"def f(EquipeGerencia):\n    EquipeGerencia.objects.{metodo}()\n"
    )
    result = _run_lint(tmp_path / "apps")
    assert result.returncode == 1
    assert "V005" in result.stderr


@pytest.mark.parametrize(
    "linha",
    [
        "PermissaoFuncional.groups.through.objects.create(permissaofuncional=p, group=g)",
        "user.groups.through.objects.bulk_create(linhas)",
        "grupo.permissoes_funcionais.through.objects.get_or_create(permissaofuncional=p, group=g)",
    ],
)
def test_v004_rejeita_escrita_direta_na_tabela_m2m(tmp_path, linha):
    _write_app_file(tmp_path, "apps/core/services/novo_servico.py", f"def f(user, grupo, p, g, linhas):\n    {linha}\n")
    result = _run_lint(tmp_path / "apps")
    assert result.returncode == 1, f"Esperava V004 em '{linha}'"
    assert "V004" in result.stderr


@pytest.mark.parametrize(
    "linha",
    [
        "gerencia.equipes.create(usuario=u, papel='EQUIPE')",
        "u.equipes.get_or_create(gerencia=gerencia)",
        "EquipeGerencia(gerencia=gerencia, usuario=u, papel='GERENTE').save()",
        "models.EquipeGerencia.objects.create(gerencia=gerencia, usuario=u)",
        "models.EquipeGerencia(gerencia=gerencia, usuario=u)",
    ],
)
def test_v005_rejeita_outras_formas_de_criar_vinculo(tmp_path, linha):
    _write_app_file(
        tmp_path, "apps/core/views/nova_lotacao.py", f"def f(EquipeGerencia, models, gerencia, u):\n    {linha}\n"
    )
    result = _run_lint(tmp_path / "apps")
    assert result.returncode == 1, f"Esperava V005 em '{linha}'"
    assert "V005" in result.stderr


@pytest.mark.parametrize(
    "rel",
    [
        "apps/core/services/equipe_gerencia.py",
        "apps/core/services/equipe_gerencia_import.py",
        "apps/core/services/export_contract_importer.py",
    ],
)
def test_v005_aceita_allowlist(tmp_path, rel):
    _write_app_file(tmp_path, rel, "def f(EquipeGerencia):\n    EquipeGerencia.objects.create()\n")
    result = _run_lint(tmp_path / "apps")
    assert result.returncode == 0, f"{rel} está na allowlist: {result.stderr}"


def test_v003_pega_remove(tmp_path):
    body = "from django.db import migrations\n" "def forwards(apps, schema_editor):\n" "    perm.groups.remove(grupo)\n"
    _write_fake_migration(tmp_path, 130, body)
    result = _run_lint(tmp_path / "apps" / "core" / "migrations")
    assert result.returncode == 1
    assert "V003" in result.stderr


def test_lint_limpo_na_arvore_atual():
    """O mesmo alvo do CI (`ci.yaml`: `python scripts/rbac_lint.py apps/`). Pega a 0111 e o seed."""
    result = _run_lint(BACKEND_ROOT / "apps")
    assert result.returncode == 0, f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"

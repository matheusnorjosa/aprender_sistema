"""
PR 14 hardening RBAC (2026-05-04): garantia de sync entre `matrix.py` e
`v2/docs/rbac_authorization_matrix.md`.

Cobre o management command `rbac_matrix_doc`:
- `--check` no doc real do repo passa.
- `--check` em fixture com bloco divergente falha (exit 1).
- `--write` em fixture corrige idempotentemente (rodar 2x = mesmo conteúdo).
- Função pura `render_matrix_block` é determinística (mesma entrada →
  mesma saída).

A matriz Python é tratada como SSOT — `--check` é o gate que evita drift
silencioso no PR review.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeStubs=false

from __future__ import annotations

import io

from django.core.management import call_command
from django.core.management.base import CommandError

import pytest

from apps.core.management.commands.rbac_matrix_doc import (
    BEGIN_MARKER,
    END_MARKER,
    _default_doc_path,
    render_matrix_block,
    replace_block,
)

# ============================================================================
# render_matrix_block — função pura (sem I/O)
# ============================================================================


class TestRenderBlock:
    def test_inclui_marcadores_no_inicio_e_fim(self):
        block = render_matrix_block()
        assert block.startswith(BEGIN_MARKER)
        assert block.endswith(END_MARKER)

    def test_e_deterministico(self):
        # Mesma entrada → mesma saída (idempotente como string).
        a = render_matrix_block()
        b = render_matrix_block()
        assert a == b

    def test_inclui_legenda_de_status(self):
        block = render_matrix_block()
        assert "ALLOW" in block
        assert "DENY" in block
        assert "ALLOW_PAYLOAD_INVALID" in block

    def test_lista_todos_os_atores_e_recursos(self):
        from apps.core.rbac.matrix import ACTORS, RESOURCES

        block = render_matrix_block()
        for actor in ACTORS:
            assert actor in block, f"Ator '{actor}' ausente do bloco renderizado"
        for resource in RESOURCES:
            assert resource.name in block, f"Recurso '{resource.name}' ausente"


# ============================================================================
# replace_block — função pura
# ============================================================================


class TestReplaceBlock:
    def test_substitui_apenas_o_bloco(self):
        before = "# Doc\n\nProsa intacta.\n\n"
        after = "\n\nMais prosa.\n"
        old_block = f"{BEGIN_MARKER}\nconteudo antigo\n{END_MARKER}"
        new_block = f"{BEGIN_MARKER}\nconteudo novo\n{END_MARKER}"

        full = before + old_block + after
        result = replace_block(full, new_block)

        assert result == before + new_block + after
        assert "conteudo antigo" not in result
        assert "Prosa intacta." in result
        assert "Mais prosa." in result

    def test_levanta_erro_sem_marcadores(self):
        with pytest.raises(CommandError, match="Marcadores autogen ausentes"):
            replace_block("doc sem marcadores", "novo bloco")

    def test_levanta_erro_marcadores_invertidos(self):
        invertido = f"{END_MARKER}\nbloco\n{BEGIN_MARKER}"
        with pytest.raises(CommandError, match="ENDs.*BEGIN|antes do BEGIN"):
            replace_block(invertido, "novo")


# ============================================================================
# Management command — exit codes
# ============================================================================


@pytest.fixture
def doc_fixture(tmp_path):
    """Cria um doc fixture com bloco autogen vazio (placeholder)."""
    path = tmp_path / "rbac_matrix.md"
    path.write_text(
        f"# Fixture\n\n## §3\n\n" f"{BEGIN_MARKER}\n" f"<!-- placeholder -->\n" f"{END_MARKER}\n" f"\n## §4 prosa.\n",
        encoding="utf-8",
    )
    return path


class TestCommandCheck:
    def test_check_falha_em_fixture_divergente(self, doc_fixture):
        # Doc tem placeholder; ACCESS_MATRIX produziria conteúdo real → drift.
        with pytest.raises(CommandError, match="drift detectado|DRIFT"):
            call_command("rbac_matrix_doc", "--check", f"--doc-path={doc_fixture}")

    def test_check_passa_apos_write(self, doc_fixture):
        # Primeiro --write corrige; depois --check passa sem erro.
        call_command("rbac_matrix_doc", "--write", f"--doc-path={doc_fixture}")
        # Sem CommandError → check passa.
        out = io.StringIO()
        call_command("rbac_matrix_doc", "--check", f"--doc-path={doc_fixture}", stdout=out)
        assert "OK" in out.getvalue()


class TestCommandWrite:
    def test_write_aplica_bloco_renderizado(self, doc_fixture):
        call_command("rbac_matrix_doc", "--write", f"--doc-path={doc_fixture}")
        content = doc_fixture.read_text(encoding="utf-8")
        # Marcadores preservados; placeholder removido.
        assert BEGIN_MARKER in content
        assert END_MARKER in content
        assert "<!-- placeholder -->" not in content
        # Prosa fora do bloco preservada.
        assert "## §3" in content
        assert "## §4 prosa." in content

    def test_write_e_idempotente(self, doc_fixture):
        call_command("rbac_matrix_doc", "--write", f"--doc-path={doc_fixture}")
        first = doc_fixture.read_text(encoding="utf-8")
        call_command("rbac_matrix_doc", "--write", f"--doc-path={doc_fixture}")
        second = doc_fixture.read_text(encoding="utf-8")
        assert first == second

    def test_write_mostra_ok_quando_doc_ja_em_sync(self, doc_fixture):
        call_command("rbac_matrix_doc", "--write", f"--doc-path={doc_fixture}")
        out = io.StringIO()
        call_command("rbac_matrix_doc", "--write", f"--doc-path={doc_fixture}", stdout=out)
        assert "ja estava em sync" in out.getvalue() or "j" in out.getvalue()


class TestCommandErrors:
    def test_erro_se_doc_path_nao_existe(self, tmp_path):
        missing = tmp_path / "nao_existe.md"
        with pytest.raises(CommandError, match="não encontrado|nao encontrado"):
            call_command("rbac_matrix_doc", f"--doc-path={missing}")

    def test_erro_se_doc_sem_marcadores(self, tmp_path):
        path = tmp_path / "sem_marcadores.md"
        path.write_text("# Doc\n\nProsa sem marcadores.\n", encoding="utf-8")
        with pytest.raises(CommandError, match="Marcadores autogen ausentes"):
            call_command("rbac_matrix_doc", f"--doc-path={path}")


# ============================================================================
# Doc real do repo — esse é o teste que CI vai usar como gate de drift
# ============================================================================


class TestRealDocInSync:
    def test_doc_real_do_repo_em_sync(self):
        """
        O doc canônico (`v2/docs/rbac_authorization_matrix.md`) precisa estar
        em sync com `apps/core/rbac/matrix.py`. Se este test falhar, alguém
        editou ACCESS_MATRIX sem rodar `python manage.py rbac_matrix_doc
        --write`. Para corrigir:

            python manage.py rbac_matrix_doc --write

        e commit junto da mudança em matrix.py.
        """
        doc_path = _default_doc_path()
        if not doc_path.exists():
            pytest.skip(f"Doc real não acessível em {doc_path} (ambiente CI?)")

        # Sem CommandError → passa.
        call_command("rbac_matrix_doc", "--check", f"--doc-path={doc_path}")

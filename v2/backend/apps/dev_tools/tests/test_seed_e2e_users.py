"""Tests for seed_e2e_users idempotency and resilience."""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false, reportPrivateUsage=false

from __future__ import annotations

from io import StringIO

from django.core.management import call_command

import pytest

from apps.core.models import Compra, EquipeGerencia, Municipio, Projeto, Usuario

SEED_USERNAMES = [
    "coord_e2e@test.com",
    "super_e2e@test.com",
    "controle_e2e@test.com",
    "formador_e2e@test.com",
]

SEED_PROJETOS = ["TESTE E2E", "TESTE E2E NAO_SUPER"]
SEED_MUNICIPIOS = [("Salvador", "BA"), ("Fortaleza", "CE")]


def _clean_seed_entities() -> None:
    """Remove entidades seedadas pelo comando, respeitando FK PROTECT.

    Ordem importa: Compra tem FK PROTECT para Municipio e Projeto. Se
    apagarmos Municipio/Projeto antes, o Django levanta ProtectedError
    no teardown.
    """
    Compra.objects.filter(
        projeto__nome__in=SEED_PROJETOS,
    ).delete()
    # EquipeGerencia.usuario é PROTECT: o vínculo GERENTE de super_e2e (PR B1) sai antes.
    EquipeGerencia.objects.filter(usuario__username__in=SEED_USERNAMES).delete()
    Usuario.objects.filter(username__in=SEED_USERNAMES).delete()
    Projeto.objects.filter(nome__in=SEED_PROJETOS).delete()
    for nome, uf in SEED_MUNICIPIOS:
        Municipio.objects.filter(nome=nome, uf=uf).delete()


@pytest.fixture
def clean_seed_e2e_state(db):
    """Keep seed_e2e tests deterministic and independent."""
    _clean_seed_entities()
    yield
    _clean_seed_entities()


def _run_seed_command() -> str:
    out = StringIO()
    call_command("seed_e2e_users", stdout=out)
    return out.getvalue()


@pytest.mark.django_db
class TestSeedE2EUsersCommand:
    def test_seed_e2e_users_is_idempotent(self, clean_seed_e2e_state):
        """Running command twice should not duplicate rows."""
        output_first = _run_seed_command()
        output_second = _run_seed_command()

        assert "SEED E2E concluído com sucesso" in output_first
        assert "SEED E2E concluído com sucesso" in output_second

        assert Usuario.objects.filter(username__in=SEED_USERNAMES).count() == 4
        assert Municipio.objects.filter(nome="Salvador", uf="BA").count() == 1
        assert Projeto.objects.filter(codigo="E2E", nome="TESTE E2E").count() == 1

        # Command should keep a deterministic group set for each seed user.
        assert set(Usuario.objects.get(username="coord_e2e@test.com").groups.values_list("name", flat=True)) == {
            "Coordenador"
        }
        assert set(Usuario.objects.get(username="super_e2e@test.com").groups.values_list("name", flat=True)) == {
            "Superintendência",
            "Gerente",
        }
        assert set(Usuario.objects.get(username="controle_e2e@test.com").groups.values_list("name", flat=True)) == {
            "Controle"
        }
        assert set(Usuario.objects.get(username="formador_e2e@test.com").groups.values_list("name", flat=True)) == {
            "Formador"
        }

    def test_seed_upserts_existing_salvador_without_ibge(self, clean_seed_e2e_state):
        """Should not fail when Salvador/BA exists without ibge_code."""
        municipio = Municipio.objects.create(nome="Salvador", uf="BA", ativo=False, ibge_code=None)

        output = _run_seed_command()

        municipio.refresh_from_db()
        assert municipio.ibge_code == "2927408"
        assert municipio.ativo is True
        assert Municipio.objects.filter(nome="Salvador", uf="BA").count() == 1
        assert "SEED E2E concluído com sucesso" in output

    def test_seed_does_not_abort_with_conflicting_ibge_owner(self, clean_seed_e2e_state):
        """
        If ibge_code is already bound to another row, command should still complete
        and keep E2E entities created/updated.
        """
        Municipio.objects.create(nome="Outro Município", uf="BA", ibge_code="2927408", ativo=True)
        salvador = Municipio.objects.create(nome="Salvador", uf="BA", ibge_code=None, ativo=False)

        output = _run_seed_command()

        salvador.refresh_from_db()
        assert salvador.ativo is True
        assert Municipio.objects.filter(nome="Salvador", uf="BA").count() == 1
        assert Usuario.objects.filter(username__in=SEED_USERNAMES).count() == 4
        assert Projeto.objects.filter(nome="TESTE E2E").exists()
        assert "SEED E2E concluído com sucesso" in output

    def test_personas_aprovadoras_tem_vinculo_gerente_na_superintendencia(self, clean_seed_e2e_state):
        """PR B1: aprovar passa pelo vínculo GERENTE vigente na SUPERINTENDENCIA — as
        personas aprovadoras dos E2E (j01/j04/j08/j10) precisam dele."""
        _run_seed_command()

        vinculados = set(
            EquipeGerencia.vigentes_em()
            .filter(papel="GERENTE", gerencia__nome="SUPERINTENDENCIA")
            .values_list("usuario__username", flat=True)
        )
        assert {"super_e2e@test.com", "super_geral@test.com", "approver_03@test.com"} <= vinculados

    def test_cleanup_remove_persona_com_vinculo(self, clean_seed_e2e_state):
        """`cleanup_e2e_data` apaga super_e2e mesmo com o vínculo GERENTE (FK PROTECT).

        Chama só o passo de usuários: o passo de município do comando já falha por outro
        motivo, anterior ao PR B1 (Compra.municipio PROTECT), fora deste escopo."""
        from apps.dev_tools.management.commands.cleanup_e2e_data import Command as Cleanup

        _run_seed_command()

        Cleanup(stdout=StringIO())._delete_users(dry_run=False)

        assert not Usuario.objects.filter(username="super_e2e@test.com").exists()

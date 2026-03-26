"""Tests for seed_e2e_users idempotency and resilience."""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from io import StringIO

from django.core.management import call_command

import pytest

from apps.core.models import Municipio, Projeto, Usuario

SEED_USERNAMES = [
    "coord_e2e@test.com",
    "super_e2e@test.com",
    "controle_e2e@test.com",
    "formador_e2e@test.com",
]


@pytest.fixture
def clean_seed_e2e_state(db):
    """Keep seed_e2e tests deterministic and independent."""
    Usuario.objects.filter(username__in=SEED_USERNAMES).delete()
    Projeto.objects.filter(nome="TESTE E2E").delete()
    Municipio.objects.filter(nome="Salvador", uf="BA").delete()
    yield
    Usuario.objects.filter(username__in=SEED_USERNAMES).delete()
    Projeto.objects.filter(nome="TESTE E2E").delete()
    Municipio.objects.filter(nome="Salvador", uf="BA").delete()


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

"""Tests for seed_frontend_contract_data deterministic behavior."""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from io import StringIO

from django.core.management import call_command

import pytest

from apps.core.models import Compra, DATCompra, Municipio, PermissaoFuncional, Projeto, Usuario

SEED_EXTERNAL_HASH = "9" * 64
SEED_COMPRA_CODE = "MATRIX-PEND-001"
SEED_DAT_DESCRICAO = "KIT MATRIX CONTRACT"
SEED_DAT_USERNAME = "dat_matrix@test.com"
SEED_CONTROLE_USERNAME = "controle_e2e@test.com"


@pytest.fixture
def clean_contract_seed_state(db):
    """Keep seed_frontend_contract_data tests deterministic and independent."""
    DATCompra.objects.filter(descricao_produto=SEED_DAT_DESCRICAO, ano_uso=2026).delete()
    Compra.objects.filter(external_hash=SEED_EXTERNAL_HASH).delete()
    Municipio.objects.filter(nome="Matrizopolis", uf="BA").delete()
    Usuario.objects.filter(username__in=[SEED_DAT_USERNAME, SEED_CONTROLE_USERNAME]).delete()
    yield
    DATCompra.objects.filter(descricao_produto=SEED_DAT_DESCRICAO, ano_uso=2026).delete()
    Compra.objects.filter(external_hash=SEED_EXTERNAL_HASH).delete()
    Municipio.objects.filter(nome="Matrizopolis", uf="BA").delete()
    Usuario.objects.filter(username__in=[SEED_DAT_USERNAME, SEED_CONTROLE_USERNAME]).delete()


def _run_seed_command() -> str:
    out = StringIO()
    call_command("seed_frontend_contract_data", stdout=out)
    return out.getvalue()


@pytest.mark.django_db
class TestSeedFrontendContractDataCommand:
    def test_seed_frontend_contract_data_is_idempotent(self, clean_contract_seed_state):
        """Running command twice should keep deterministic single rows."""
        output_first = _run_seed_command()
        output_second = _run_seed_command()

        assert "Seed funcional da matriz concluido" in output_first
        assert "Seed funcional da matriz concluido" in output_second

        projeto = Projeto.objects.get(codigo="E2E")
        municipio = Municipio.objects.get(nome="Matrizopolis", uf="BA")

        assert Compra.objects.filter(external_hash=SEED_EXTERNAL_HASH).count() == 1
        compra = Compra.objects.get(external_hash=SEED_EXTERNAL_HASH)
        assert compra.codigo == SEED_COMPRA_CODE
        assert compra.quantidade == 15
        assert compra.projeto_id == projeto.id
        assert compra.municipio_id == municipio.id

        assert (
            DATCompra.objects.filter(
                municipio=municipio,
                projeto=projeto,
                descricao_produto=SEED_DAT_DESCRICAO,
                ano_uso=2026,
            ).count()
            == 1
        )
        dat_compra = DATCompra.objects.get(
            municipio=municipio,
            projeto=projeto,
            descricao_produto=SEED_DAT_DESCRICAO,
            ano_uso=2026,
        )
        assert dat_compra.quantidade == 77
        assert dat_compra.ativo is True

        dat_user = Usuario.objects.get(username=SEED_DAT_USERNAME)
        assert dat_user.check_password("testpass123")
        assert set(dat_user.groups.values_list("name", flat=True)) == {"DAT"}
        assert (
            PermissaoFuncional.objects.get(codename="pode_acessar_dashboard_compras").groups.filter(name="DAT").exists()
        )

        assert Usuario.objects.filter(username=SEED_CONTROLE_USERNAME).exists()

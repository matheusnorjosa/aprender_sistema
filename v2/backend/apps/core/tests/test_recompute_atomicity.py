"""
Wave 4 — atomicidade mutação + recompute de valor derivado.

Dois call-sites gravavam a mutação e SÓ DEPOIS rodavam o recompute do valor
derivado, cada um como escrita autocommit separada (ATOMIC_REQUESTS=False neste
projeto → a request não é envolvida em transação). Se o recompute falhasse, a
mutação já estava persistida com o valor derivado STALE:

- `DATCompraViewSet.perform_create/update/destroy` (views/dat_module.py):
  `serializer.save()`/`instance.delete()` + `recompute_registros()` → `DATRegistro.nr_codigos`;
- `PlanoFormacoesViewSet.update_formacao` (views/plano_formacoes.py):
  `serializer.save()` + `plano.recalcular_ch()` + `plano.save()` → CH do plano.

Contrato: mutação + recompute no MESMO `transaction.atomic()` — se o recompute
falhar, a mutação é desfeita (nada de estado parcial). Erro interno segue 500,
mas o banco não fica inconsistente.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false, reportMissingTypeStubs=false

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

from rest_framework.test import APIClient

import pytest

from apps.core.models import DATCompra, Formacao, PlanoFormacoes
from apps.core.tests.factories import (
    GroupFactory,
    MunicipioFactory,
    ProjetoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def municipio():
    return MunicipioFactory(nome="Fortaleza RA", uf="CE", ativo=True)


@pytest.fixture
def projeto():
    return ProjetoFactory(nome="Projeto RA", codigo="PRA", fluxo="NAO_SUPER", ativo=True)


@pytest.fixture
def dat_user():
    u = UsuarioFactory(username="dat_ra", cpf="66600000601")
    u.groups.add(GroupFactory(name="DAT"))
    return u


@pytest.fixture
def super_user():
    return UsuarioFactory(username="super_ra", cpf="77700000701", is_superuser=True, is_staff=True)


def _compra(municipio, projeto, user, **kw):
    defaults = dict(
        municipio=municipio,
        projeto=projeto,
        descricao_produto="Produto RA",
        quantidade=10,
        ano_uso=2025,
        created_by=user,
    )
    defaults.update(kw)
    return DATCompra.objects.create(**defaults)


class TestDATCompraRecomputeAtomic:
    def test_create_rolls_back_when_recompute_fails(self, municipio, projeto, dat_user):
        """RED: create commita a Compra e depois recompute (autocommit) — falhou → Compra fica órfã."""
        client = APIClient()
        client.raise_request_exception = False  # 500 vira resposta, não propaga a exceção
        client.force_authenticate(dat_user)
        antes = DATCompra.objects.count()

        with patch("apps.core.views.dat_module.recompute_registros", side_effect=RuntimeError("boom")):
            resp = client.post(
                "/api/dat/compras-materiais/",
                {
                    "municipio": municipio.id,
                    "projeto": projeto.id,
                    "descricao_produto": "Nova RA",
                    "quantidade": 5,
                    "ano_uso": 2025,
                },
                format="json",
            )

        assert resp.status_code == 500
        assert DATCompra.objects.count() == antes, "recompute falho não pode deixar a Compra criada"

    def test_update_rolls_back_when_recompute_fails(self, municipio, projeto, dat_user):
        client = APIClient()
        client.raise_request_exception = False  # 500 vira resposta, não propaga a exceção
        client.force_authenticate(dat_user)
        compra = _compra(municipio, projeto, dat_user, quantidade=10)

        with patch("apps.core.views.dat_module.recompute_registros", side_effect=RuntimeError("boom")):
            resp = client.patch(
                f"/api/dat/compras-materiais/{compra.id}/",
                {"quantidade": 99},
                format="json",
            )

        assert resp.status_code == 500
        compra.refresh_from_db()
        assert compra.quantidade == 10, "recompute falho não pode persistir a alteração da Compra"

    def test_destroy_rolls_back_when_recompute_fails(self, municipio, projeto, dat_user, super_user):
        client = APIClient()
        client.raise_request_exception = False  # 500 vira resposta, não propaga a exceção
        client.force_authenticate(super_user)
        compra = _compra(municipio, projeto, dat_user)

        with patch("apps.core.views.dat_module.recompute_registros", side_effect=RuntimeError("boom")):
            resp = client.delete(f"/api/dat/compras-materiais/{compra.id}/")

        assert resp.status_code == 500
        assert DATCompra.objects.filter(pk=compra.pk).exists(), "recompute falho não pode deletar a Compra"


class TestPlanoFormacaoRecomputeAtomic:
    def test_update_formacao_rolls_back_when_recalcular_ch_fails(self, municipio, projeto, dat_user):
        """RED: update_formacao salva a formacao e depois recalcular_ch()+save() — falhou → formacao fica alterada."""
        client = APIClient()
        client.raise_request_exception = False  # 500 vira resposta, não propaga a exceção
        client.force_authenticate(dat_user)
        plano = PlanoFormacoes.objects.create(municipio=municipio, projeto=projeto, ano=2025, created_by=dat_user)
        Formacao.objects.create(plano=plano, numero_formacao=1, carga_horaria=Decimal("4.00"))

        with patch.object(PlanoFormacoes, "recalcular_ch", side_effect=RuntimeError("boom")):
            resp = client.patch(
                f"/api/dat/plano-formacoes/{plano.id}/formacao/1/",
                {"data_formacao": "2025-05-01", "realizada": True},
                format="json",
            )

        assert resp.status_code == 500
        formacao = plano.formacoes.get(numero_formacao=1)
        assert formacao.data_formacao is None, "recalcular_ch falho não pode persistir a alteração da formacao"
        assert formacao.realizada is False

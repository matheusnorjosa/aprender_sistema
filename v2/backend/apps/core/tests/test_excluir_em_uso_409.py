"""
C2 (Programa C) — excluir registro em uso responde 409 com o motivo, não 500.

As FKs `on_delete=PROTECT` (Solicitacao/Compra → Município, Projeto → Gerência, Compra → Produto,
Cadastro DAT → Projeto Geral) levantam `ProtectedError`, que o handler de exceção não tratava: a
tela recebia 500 e mostrava "Erro 500". Agora é 409 dizendo o TIPO de registro que impede a
exclusão, nunca os registros em si (podem ser de outro setor).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

import itertools
from datetime import date

from rest_framework.test import APIClient

import pytest

from apps.core.models import Compra, DATCadastro, Gerencia, Municipio, Produto, Projeto, ProjetoGeral, Solicitacao
from apps.core.tests.factories import MunicipioFactory, ProjetoFactory, SolicitacaoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

_SEQ = itertools.count(1)


def _root_client() -> APIClient:
    # Sem relançar a exceção da view: o teste vê a resposta que a tela recebe (antes, 500).
    client = APIClient(raise_request_exception=False)
    client.force_authenticate(user=UsuarioFactory(superuser=True))
    return client


def _compra(**kwargs) -> Compra:
    n = next(_SEQ)
    kwargs.setdefault("projeto", ProjetoFactory())
    kwargs.setdefault("municipio", MunicipioFactory())
    return Compra.objects.create(
        codigo=f"C409-{n}", quantidade=1, data=date(2026, 9, 30), uso="Formação", external_hash=f"h409-{n}", **kwargs
    )


def _assert_409_em_uso(resp, tipo: str, *segredos: str) -> None:
    assert resp.status_code == 409, f"status {resp.status_code}"
    assert resp.data["code"] == "CONFLICT"
    detalhe = str(resp.data["detail"])
    assert detalhe == f"Este registro não pode ser excluído porque está em uso ({tipo})."
    for segredo in segredos:
        assert segredo not in detalhe  # só o tipo do registro, nunca o registro de outro setor


def test_municipio_com_solicitacao_da_409_sem_citar_a_solicitacao():
    municipio = MunicipioFactory()
    SolicitacaoFactory(municipio=municipio, observacoes="Formação Sigilosa de Outro Setor")

    resp = _root_client().delete(f"/api/municipios/{municipio.id}/")

    _assert_409_em_uso(resp, str(Solicitacao._meta.verbose_name_plural), "Formação Sigilosa de Outro Setor")
    assert Municipio.objects.filter(pk=municipio.pk).exists()


def test_gerencia_com_projeto_inativo_da_409():
    gerencia = Gerencia.objects.create(nome="GERENCIA 409", nome_setor="Setor 409")
    ProjetoFactory(gerencia=gerencia, ativo=False, nome="Projeto Inativo 409")

    resp = _root_client().delete(f"/api/gerencias/{gerencia.id}/")

    _assert_409_em_uso(resp, str(Projeto._meta.verbose_name_plural), "Projeto Inativo 409")
    assert Gerencia.objects.filter(pk=gerencia.pk).exists()


def test_produto_com_compra_da_409():
    produto = Produto.objects.create(codigo="P409", nome="Kit 409", projeto=ProjetoFactory())
    _compra(produto=produto)

    resp = _root_client().delete(f"/api/produtos/{produto.id}/")

    _assert_409_em_uso(resp, str(Compra._meta.verbose_name_plural))
    assert Produto.objects.filter(pk=produto.pk).exists()


def test_projeto_geral_com_cadastro_dat_da_409():
    projeto_geral = ProjetoGeral.objects.create(nome="PROJETO 409")
    DATCadastro.objects.create(
        municipio=MunicipioFactory(), projeto_geral=projeto_geral, plataforma="FORMAR", created_by=UsuarioFactory()
    )

    resp = _root_client().delete(f"/api/projetos-gerais/{projeto_geral.id}/")

    _assert_409_em_uso(resp, str(DATCadastro._meta.verbose_name_plural))
    assert ProjetoGeral.objects.filter(pk=projeto_geral.pk).exists()


def test_varios_tipos_saem_em_ordem_e_sem_repetir():
    municipio = MunicipioFactory()
    SolicitacaoFactory(municipio=municipio)
    SolicitacaoFactory(municipio=municipio)
    _compra(municipio=municipio)

    resp = _root_client().delete(f"/api/municipios/{municipio.id}/")

    tipos = sorted({str(Compra._meta.verbose_name_plural), str(Solicitacao._meta.verbose_name_plural)})
    _assert_409_em_uso(resp, ", ".join(tipos))


def test_excluir_sem_vinculo_continua_204():
    municipio = MunicipioFactory()

    resp = _root_client().delete(f"/api/municipios/{municipio.id}/")

    assert resp.status_code == 204
    assert not Municipio.objects.filter(pk=municipio.pk).exists()

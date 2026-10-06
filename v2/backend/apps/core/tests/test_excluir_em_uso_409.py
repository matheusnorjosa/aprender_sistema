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

from django.apps import apps
from django.db.models import PROTECT, ProtectedError
from rest_framework.test import APIClient

import pytest

from apps.core.exceptions import _mensagem_em_uso
from apps.core.models import (
    Compra,
    DATCadastro,
    EquipeGerencia,
    Gerencia,
    Municipio,
    Produto,
    Projeto,
    ProjetoGeral,
)
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

    # C2b: com acento (o `verbose_name_plural` do model é "Solicitacoes de Evento").
    _assert_409_em_uso(resp, "Solicitações de Evento", "Formação Sigilosa de Outro Setor")
    assert Municipio.objects.filter(pk=municipio.pk).exists()


def test_gerencia_com_projeto_inativo_da_409():
    gerencia = Gerencia.objects.create(nome="GERENCIA 409", nome_setor="Setor 409")
    ProjetoFactory(gerencia=gerencia, ativo=False, nome="Projeto Inativo 409")

    resp = _root_client().delete(f"/api/gerencias/{gerencia.id}/")

    _assert_409_em_uso(resp, str(Projeto._meta.verbose_name_plural), "Projeto Inativo 409")
    assert Gerencia.objects.filter(pk=gerencia.pk).exists()


def test_gerencia_com_equipe_da_409_com_acento():
    gerencia = Gerencia.objects.create(nome="GERENCIA 409 EQUIPE", nome_setor="Setor 409 Equipe")
    EquipeGerencia.objects.create(gerencia=gerencia, usuario=UsuarioFactory(), papel="COORDENADOR")

    resp = _root_client().delete(f"/api/gerencias/{gerencia.id}/")

    _assert_409_em_uso(resp, "Equipes de Gerências")
    assert Gerencia.objects.filter(pk=gerencia.pk).exists()


def test_projeto_com_produto_da_409():
    projeto = ProjetoFactory()
    Produto.objects.create(codigo="P409-PROJ", nome="Kit Projeto 409", projeto=projeto)

    resp = _root_client().delete(f"/api/projetos/{projeto.id}/")

    _assert_409_em_uso(resp, str(Produto._meta.verbose_name_plural), "Kit Projeto 409")
    assert Projeto.objects.filter(pk=projeto.pk).exists()


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

    _assert_409_em_uso(resp, "Compras, Solicitações de Evento")


def test_excluir_sem_vinculo_continua_204():
    municipio = MunicipioFactory()

    resp = _root_client().delete(f"/api/municipios/{municipio.id}/")

    assert resp.status_code == 204
    assert not Municipio.objects.filter(pk=municipio.pk).exists()


def _tipo_no_409(model) -> str:
    mensagem = _mensagem_em_uso(ProtectedError("em uso", [model()]))
    return mensagem.removeprefix("Este registro não pode ser excluído porque está em uso (").removesuffix(").")


def test_sentinela_todo_model_com_fk_protect_sai_com_acento_no_409():
    """O motivo do 409 vai para a tela: model novo com FK PROTECT entra aqui com o nome que ela mostra.

    Vários `verbose_name_plural` saíram sem acento ("Solicitacoes de Evento"); corrigir o Meta pede
    migration, então o nome com acento fica no `_mensagem_em_uso`.
    """
    com_protect = [
        model
        for model in apps.get_models()
        if any(getattr(campo.remote_field, "on_delete", None) is PROTECT for campo in model._meta.concrete_fields)
    ]

    assert {model._meta.label: _tipo_no_409(model) for model in com_protect} == {
        "core.AcaoDAT": "Ações DAT",
        "core.AcaoInstancia": "Ações Instância",
        "core.AcaoTemplate": "Ações Template",
        "core.AcaoTemplateExecutor": "Executores de Ações Template",
        "core.AvailabilityBlock": "Bloqueios de Disponibilidade",
        "core.CicloAcoes": "Ciclos de Ações",
        "core.Compra": "Compras",
        "core.DATAcao": "Ações DAT",
        "core.DATCadastro": "Cadastros DAT",
        "core.DATCompra": "Compras DAT",
        "core.DATCoordenador": "Coordenadores DAT",
        "core.DATRegistro": "Registros DAT",
        "core.Deslocamento": "Deslocamentos",
        "core.EquipeGerencia": "Equipes de Gerências",
        "core.ImportJob": "Jobs de Importação",
        "core.Participation": "Participações",
        "core.PlanoFormacoes": "Planos de Formações",
        "core.Produto": "Produtos",
        "core.Projeto": "Projetos",
        "core.Solicitacao": "Solicitações de Evento",
    }

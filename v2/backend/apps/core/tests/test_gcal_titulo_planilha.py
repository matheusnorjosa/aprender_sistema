"""Título do evento no Google igual ao da planilha (decisão do dono, 03/11/2026).

Medido em produção em 417 títulos da planilha:
- formação: `MUNICÍPIO - UF {N}º EF - {Tipo de Evento} [{NOME NA AGENDA} {segmento}]`;
- acompanhamento: `MUNICÍPIO - UF {N}º Acompanhamento [{NOME NA AGENDA} {segmento}]`.

O nome entre colchetes vem da coleção (`ProjetoGeral.nome_na_agenda`); vazio, o nome da coleção em
maiúsculas; sem coleção, o nome do projeto em maiúsculas.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

from rest_framework.test import APIClient

import pytest

from apps.core.models import ProjetoGeral
from apps.core.services.gcal_sync_service import build_event_payload
from apps.core.tests.factories import (
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db


def _titulo(
    *,
    municipio=("Curvelo", "MG"),
    encontro="4",
    tipo="Presencial",
    colecao="Superativar",
    nome_na_agenda="",
    segmento="4º ano MAT",
    is_online=False,
) -> str:
    projeto = None
    if colecao is not None:
        geral = ProjetoGeral.objects.create(nome=colecao, nome_na_agenda=nome_na_agenda)
        projeto = ProjetoFactory(nome=f"{colecao} 4", projeto_geral=geral)
    s = SolicitacaoFactory(
        municipio=MunicipioFactory(nome=municipio[0], uf=municipio[1]) if municipio else None,
        projeto=projeto,
        tipo_evento=TipoEventoFactory(nome=tipo or "Formação"),
        encontro=encontro,
        segmento=segmento,
        is_online=is_online,
    )
    if tipo is None:
        s.tipo_evento = None  # só em memória: a coluna é NOT NULL
    return build_event_payload(s, enable_meet=False)["summary"]


def test_formacao_presencial_com_segmento():
    assert _titulo() == "CURVELO - MG 4º EF - Presencial [SUPERATIVAR 4º ano MAT]"


@pytest.mark.parametrize("segmento", ["", None])
def test_formacao_online_sem_segmento_usa_o_nome_na_agenda(segmento):
    titulo = _titulo(
        municipio=("Tamandaré", "PE"),
        tipo="Online",
        colecao="Vida e Linguagem",
        nome_na_agenda="VIDA & LINGUAGEM",
        segmento=segmento,
    )

    assert titulo == "TAMANDARÉ - PE 4º EF - Online [VIDA & LINGUAGEM]"


@pytest.mark.parametrize("tipo", ["Acompanhamento", "ACOMPANHAMENTO", "acompanhamento "])
def test_acompanhamento_sem_ef(tipo):
    titulo = _titulo(municipio=("Craíbas", "AL"), encontro="2", tipo=tipo, colecao="Uni Duni Tê", segmento="4 e 5 anos")

    assert titulo == "CRAÍBAS - AL 2º Acompanhamento [UNI DUNI TÊ 4 e 5 anos]"


@pytest.mark.parametrize("tipo", ["Aulão", "Seminário", "Reunião"])
def test_o_texto_depois_de_ef_e_o_nome_do_tipo_de_evento(tipo):
    assert _titulo(encontro="3", tipo=tipo, segmento="") == f"CURVELO - MG 3º EF - {tipo} [SUPERATIVAR]"


def test_nome_na_agenda_preenchido_vence_o_nome_da_colecao():
    assert _titulo(nome_na_agenda="SUPER ATIVAR", segmento="") == "CURVELO - MG 4º EF - Presencial [SUPER ATIVAR]"


def test_projeto_sem_colecao_usa_o_nome_do_projeto_em_maiusculas():
    s = SolicitacaoFactory(
        municipio=MunicipioFactory(nome="Curvelo", uf="MG"),
        projeto=ProjetoFactory(nome="Projeto Solto", codigo="SOLTO"),
        tipo_evento=TipoEventoFactory(nome="Presencial"),
        encontro="1",
        segmento="",
    )

    assert build_event_payload(s, enable_meet=False)["summary"] == "CURVELO - MG 1º EF - Presencial [PROJETO SOLTO]"


@pytest.mark.parametrize("encontro", ["", None, "   "])
def test_sem_numero_nao_sobra_espaco_nem_grau(encontro):
    assert _titulo(encontro=encontro, segmento="") == "CURVELO - MG EF - Presencial [SUPERATIVAR]"


def test_sem_numero_no_acompanhamento():
    assert _titulo(encontro="", tipo="Acompanhamento", segmento="") == "CURVELO - MG Acompanhamento [SUPERATIVAR]"


@pytest.mark.parametrize(
    ("encontro", "numero"),
    [("4º", "4º"), (" 4 ", "4º"), ("10", "10º"), ("Encontro 1", "Encontro 1")],
)
def test_numero_ja_com_grau_ou_texto_fica_como_esta(encontro, numero):
    assert _titulo(encontro=encontro, segmento="") == f"CURVELO - MG {numero} EF - Presencial [SUPERATIVAR]"


@pytest.mark.parametrize(("is_online", "meio"), [(True, "Online"), (False, "Presencial")])
def test_sem_tipo_de_evento_usa_a_modalidade(is_online, meio):
    assert _titulo(tipo=None, is_online=is_online, segmento="") == f"CURVELO - MG 4º EF - {meio} [SUPERATIVAR]"


def test_sem_projeto_sem_colchetes():
    assert _titulo(colecao=None) == "CURVELO - MG 4º EF - Presencial"


def test_sem_municipio_comeca_pelo_numero():
    assert _titulo(municipio=None, segmento="") == "4º EF - Presencial [SUPERATIVAR]"


def test_api_da_colecao_grava_e_le_o_nome_na_agenda():
    client = APIClient()
    client.force_authenticate(user=UsuarioFactory(superuser=True))

    criado = client.post(
        "/api/projetos-gerais/", {"nome": "Vida e Linguagem", "nome_na_agenda": "VIDA & LINGUAGEM"}, format="json"
    )
    assert criado.status_code == 201, criado.data
    assert criado.data["nome_na_agenda"] == "VIDA & LINGUAGEM"

    url = f"/api/projetos-gerais/{criado.data['id']}/"
    assert client.patch(url, {"nome_na_agenda": "V&L"}, format="json").status_code == 200
    assert client.get(url).data["nome_na_agenda"] == "V&L"
    assert ProjetoGeral.objects.get(pk=criado.data["id"]).nome_na_agenda == "V&L"

    # Opcional: sem o campo, fica vazio (o título usa o nome da coleção em maiúsculas).
    sem = client.post("/api/projetos-gerais/", {"nome": "Uni Duni Tê"}, format="json")
    assert sem.status_code == 201, sem.data
    assert sem.data["nome_na_agenda"] == ""


def test_api_da_colecao_recusa_nome_na_agenda_acima_de_100():
    client = APIClient()
    client.force_authenticate(user=UsuarioFactory(superuser=True))

    resp = client.post("/api/projetos-gerais/", {"nome": "Longa", "nome_na_agenda": "X" * 101}, format="json")

    assert resp.status_code == 400

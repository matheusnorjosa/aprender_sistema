"""
Gerências e Projetos (lote C do alinhamento, 06/11/2026).

- Cada setor tem uma gerência só (D03, D74): criar ou editar uma gerência ATIVA com o mesmo `setor_canonico`
  (não vazio) ou o mesmo rótulo de tela (sem diferenciar maiúsculas) de OUTRA gerência ativa dá 400 no campo.
  Sem constraint no banco por agora.
- `em_espera` (só leitura) no projeto: sem compra que o libere em município nenhum, ele some da Nova
  Solicitação (D41); a tela mostra a etiqueta "Em espera". Calculado uma vez por requisição.
- Os erros do projeto vêm no campo: a trava SUPER em `gerencia`, série com nome geral em `eh_nome_geral`.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

import pytest

from apps.core.models import Gerencia
from apps.core.tests.factories import GerenciaFactory, MunicipioFactory, ProjetoFactory, UsuarioFactory, liberar_par

pytestmark = pytest.mark.django_db

MSG = "Já existe a gerência {} para este setor. Cada setor tem uma gerência só."


@pytest.fixture
def client(db) -> APIClient:
    c = APIClient()
    c.force_authenticate(UsuarioFactory(superuser=True))
    return c


def _nova(client, **dados):
    payload = {"nome": "GERENCIA NOVA", "nome_setor": "Nova", "ativo": True, **dados}
    return client.post("/api/gerencias/", payload, format="json")


def test_nova_gerencia_com_o_setor_de_outra_ativa_da_400_no_setor(client):
    GerenciaFactory(nome="GERENCIA VIDAS", nome_setor="Vidas", setor_canonico="Vidas")

    resp = _nova(client, setor_canonico="Vidas")

    assert resp.status_code == 400, resp.content
    assert resp.data["errors"]["setor_canonico"] == [MSG.format("Vidas")]


def test_nova_gerencia_com_o_rotulo_de_outra_ativa_da_400_no_nome_de_tela(client):
    GerenciaFactory(nome="GERENCIA 4", nome_setor="ACerta", nome_exibicao="Superativar")

    resp = _nova(client, nome_exibicao="superativar")

    assert resp.status_code == 400, resp.content
    assert resp.data["errors"]["nome_exibicao"] == [MSG.format("Superativar")]


def test_sem_nome_de_tela_o_rotulo_e_o_das_planilhas(client):
    GerenciaFactory(nome="GERENCIA FLUIR", nome_setor="Fluir")

    resp = _nova(client, nome_setor="FLUIR")

    assert resp.status_code == 400, resp.content
    assert resp.data["errors"]["nome_setor"] == [MSG.format("Fluir")]


def test_editar_para_o_setor_de_outra_ativa_da_400(client):
    GerenciaFactory(nome="GERENCIA VIDAS", nome_setor="Vidas", setor_canonico="Vidas")
    outra = GerenciaFactory(nome="GERENCIA FLUIR", nome_setor="Fluir", setor_canonico="Fluir")

    resp = client.patch(f"/api/gerencias/{outra.pk}/", {"setor_canonico": "Vidas"}, format="json")

    assert resp.status_code == 400, resp.content
    assert "setor_canonico" in resp.data["errors"]


def test_gerencia_inativa_nao_conta_e_inativa_nao_e_barrada(client):
    GerenciaFactory(nome="GERENCIA VIDAS ANTIGA", nome_setor="Vidas", setor_canonico="Vidas", ativo=False)

    assert _nova(client, nome_setor="Vidas", setor_canonico="Vidas").status_code == 201
    assert (
        _nova(client, nome="GERENCIA VIDAS 2", nome_setor="Vidas", setor_canonico="Vidas", ativo=False).status_code
        == 201
    )


def test_setor_vazio_nao_conta(client):
    GerenciaFactory(nome="GERENCIA A", nome_setor="A")

    assert _nova(client, nome_setor="B", setor_canonico="").status_code == 201


def test_salvar_a_propria_gerencia_sem_mudar_passa(client):
    g = GerenciaFactory(nome="GERENCIA VIDAS", nome_setor="Vidas", setor_canonico="Vidas")

    resp = client.patch(
        f"/api/gerencias/{g.pk}/", {"nome_setor": "Vidas", "setor_canonico": "Vidas", "descricao": "x"}, format="json"
    )

    assert resp.status_code == 200, resp.content
    assert Gerencia.objects.filter(setor_canonico="Vidas").count() == 1


def test_dado_antigo_repetido_nao_trava_salvar_sem_mudar_setor_nem_rotulo(client):
    GerenciaFactory(nome="GERENCIA VIDAS", nome_setor="Vidas", setor_canonico="Vidas")
    repetida = GerenciaFactory(nome="GERENCIA VIDAS 2", nome_setor="vidas", setor_canonico="Vidas")

    resp = client.patch(
        f"/api/gerencias/{repetida.pk}/",
        {"nome_setor": "vidas", "setor_canonico": "Vidas", "pergunta_avaliar_formador": False},
        format="json",
    )

    assert resp.status_code == 200, resp.content


def test_reativar_gerencia_com_setor_ja_ativo_em_outra_da_400(client):
    GerenciaFactory(nome="GERENCIA VIDAS", nome_setor="Vidas", setor_canonico="Vidas")
    antiga = GerenciaFactory(
        nome="GERENCIA VIDAS ANTIGA", nome_setor="Vidas Antiga", setor_canonico="Vidas", ativo=False
    )

    resp = client.patch(f"/api/gerencias/{antiga.pk}/", {"ativo": True}, format="json")

    assert resp.status_code == 400, resp.content
    assert "setor_canonico" in resp.data["errors"]


def _em_espera(client) -> dict[str, bool]:
    resp = client.get("/api/projetos/", {"page_size": 100})
    assert resp.status_code == 200, resp.content
    return {p["nome"]: p["em_espera"] for p in resp.data["results"]}


def test_em_espera_antes_e_depois_de_liberar_o_par(client):
    projeto = ProjetoFactory(nome="Projeto Espera")
    ProjetoFactory(nome="Projeto Outro")

    assert _em_espera(client) == {"Projeto Espera": True, "Projeto Outro": True}

    liberar_par(MunicipioFactory(), projeto)

    assert _em_espera(client) == {"Projeto Espera": False, "Projeto Outro": True}


def test_em_espera_nao_cresce_em_consultas_com_mais_projetos(client):
    ProjetoFactory.create_batch(2)
    with CaptureQueriesContext(connection) as poucos:
        _em_espera(client)
    ProjetoFactory.create_batch(8)
    with CaptureQueriesContext(connection) as muitos:
        _em_espera(client)

    assert len(muitos) == len(poucos)


def test_trava_super_volta_no_campo_gerencia(client):
    vidas = GerenciaFactory(nome="GERENCIA VIDAS", nome_setor="Vidas")

    resp = client.post(
        "/api/projetos/", {"nome": "P", "codigo": "P", "fluxo": "SUPER", "gerencia": vidas.pk}, format="json"
    )

    assert resp.status_code == 400, resp.content
    assert "gerencia" in resp.data["errors"]


def test_serie_com_nome_geral_volta_no_campo_nome_geral(client):
    vidas = GerenciaFactory(nome="GERENCIA VIDAS", nome_setor="Vidas")

    resp = client.post(
        "/api/projetos/",
        {
            "nome": "P",
            "codigo": "P",
            "fluxo": "NAO_SUPER",
            "gerencia": vidas.pk,
            "eh_serie": True,
            "eh_nome_geral": True,
        },
        format="json",
    )

    assert resp.status_code == 400, resp.content
    assert "eh_nome_geral" in resp.data["errors"]

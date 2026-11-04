"""
Métricas com vários coordenadores no evento (decisão do dono, 03/11/2026).

Os coordenadores além do responsável (`Participation(role=COORD_ACOMPANHA)`) ocupam a agenda e
contam horas como o formador. Nas métricas:

- Ranking de formadores (`/api/metrics/team/formadores/`): "eventos" e municípios contam a mesma
  população das horas (`horas_formacao`): `ENFORCED_ROLES` sempre e o coordenador responsável
  (`coordenador`; sem ele, quem criou) só quando acompanha. Um por evento (decisão do dono, 04/11).
- Mapa (`/api/metrics/map/` e `/api/metrics/map/coordinators/`): os coordenadores do evento são o
  responsável (`Solicitacao.coordenador`; sem ele, quem criou) mais os COORD_ACOMPANHA, sem repetir
  pessoa no evento. Quem só criou o evento para outro responsável não conta (decisão do dono, 04/11).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportOptionalMemberAccess=false, reportIndexIssue=false

from __future__ import annotations

from datetime import date, datetime
from itertools import count
from typing import Any
from zoneinfo import ZoneInfo

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.test import APIClient

import pytest

from apps.core.models import Participation, Solicitacao
from apps.core.services.config_service import bust_cfg
from apps.core.tests.factories import (
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db

TZ = ZoneInfo("America/Fortaleza")
AGORA = datetime(2026, 3, 31, 12, 0, tzinfo=TZ)
_SEQ = count()

FORMADOR = Participation.Role.FORMADOR
COORDENADOR = Participation.Role.COORDENADOR
EXTRA = Participation.Role.COORD_ACOMPANHA


@pytest.fixture(autouse=True)
def _relogio_e_teto(monkeypatch, settings):
    monkeypatch.setattr("django.utils.timezone.now", lambda: AGORA)
    settings.AVAILABILITY_DAILY_LIMIT_HOURS = 8
    bust_cfg("availability")


@pytest.fixture
def client():
    c = APIClient()
    c.force_authenticate(user=UsuarioFactory(is_superuser=True, email="adm_extras@example.invalid"))
    return c


def _pessoa(nome: str):
    n = next(_SEQ)
    return UsuarioFactory(username=f"extras_{n}", email=f"extras_{n}@example.invalid", first_name=nome)


def _evento(dia: int, *, municipio=None, criador=None, coordenador=None, acompanha=False, projeto=None):
    """Evento aprovado de 4 h em março/2026, com a linha COORDENADOR de quem criou (como a tela grava)."""
    criador = criador or _pessoa("Criador")
    sol = SolicitacaoFactory(
        usuario=criador,
        coordenador=coordenador,
        coordenador_acompanha=acompanha,
        municipio=municipio or MunicipioFactory(),
        tipo_evento=TipoEventoFactory(),
        projeto=projeto or ProjetoFactory(),
        inicio=datetime(2026, 3, dia, 8, 0, tzinfo=TZ),
        fim=datetime(2026, 3, dia, 12, 0, tzinfo=TZ),
        status=Solicitacao.Status.APROVADO,
    )
    Participation.objects.create(solicitacao=sol, usuario=criador, role=COORDENADOR)
    if coordenador is not None and coordenador != criador:
        Participation.objects.create(solicitacao=sol, usuario=coordenador, role=COORDENADOR)
    return sol


def _papel(sol, usuario, role):
    Participation.objects.create(solicitacao=sol, usuario=usuario, role=role)


# ============================================================================
# Ranking de formadores
# ============================================================================


def _ranking(client) -> dict[int, dict[str, Any]]:
    resposta = client.get("/api/metrics/team/formadores/", {"days": 30})
    assert resposta.status_code == 200, resposta.data
    return {f["id"]: f for f in resposta.json()["formadores"]}


class TestRankingDeFormadores:
    def test_formador_e_convidado(self, client):
        """Formador conta; convidado não; quem só criou o evento (sem acompanhar) não."""
        bia = _pessoa("Bia")
        caio = _pessoa("Caio")
        for dia in (10, 11, 12):
            _papel(_evento(dia), bia, FORMADOR)
        _papel(_evento(13), caio, Participation.Role.CONVIDADO)

        ranking = _ranking(client)

        assert set(ranking) == {bia.id}
        assert (ranking[bia.id]["eventos"], ranking[bia.id]["horas_trabalhadas"]) == (3, 12.0)
        assert ranking[bia.id]["municipios_atendidos"] == 3

    def test_responsavel_que_acompanha_entra(self, client):
        """Decisão do dono (04/11): o responsável que acompanha conta evento e município, como conta hora."""
        bia = _pessoa("Bia")
        caio = _pessoa("Caio")
        mun = MunicipioFactory()
        _papel(_evento(10, coordenador=caio, acompanha=True, municipio=mun), bia, FORMADOR)
        _evento(11, coordenador=caio, acompanha=True, municipio=mun)

        ranking = _ranking(client)

        assert (ranking[caio.id]["eventos"], ranking[caio.id]["horas_trabalhadas"]) == (2, 8.0)
        assert ranking[caio.id]["municipios_atendidos"] == 1
        assert ranking[bia.id]["eventos"] == 1

    def test_responsavel_que_nao_acompanha_nao_entra(self, client):
        caio = _pessoa("Caio")
        criadora = _pessoa("Criadora")
        _evento(10, coordenador=caio, acompanha=False)
        _evento(11, criador=criadora, acompanha=False)

        assert _ranking(client) == {}

    def test_sem_fk_coordenador_quem_criou_e_o_responsavel(self, client):
        criadora = _pessoa("Criadora")
        apoio = _pessoa("Apoio")
        caio = _pessoa("Caio")
        _evento(10, criador=criadora, acompanha=True)
        # Apoio criou para Caio, que acompanha: conta Caio, não o Apoio.
        _evento(11, criador=apoio, coordenador=caio, acompanha=True)

        ranking = _ranking(client)

        assert set(ranking) == {criadora.id, caio.id}
        assert ranking[criadora.id]["eventos"] == 1

    def test_responsavel_que_acompanha_e_formador_no_mesmo_evento_conta_uma_vez(self, client):
        caio = _pessoa("Caio")
        sol = _evento(10, coordenador=caio, acompanha=True)
        _papel(sol, caio, FORMADOR)
        _papel(sol, caio, EXTRA)

        linha = _ranking(client)[caio.id]

        assert (linha["eventos"], linha["horas_trabalhadas"], linha["municipios_atendidos"]) == (1, 4.0, 1)

    def test_top_10_ve_o_responsavel_que_acompanha(self, client):
        """O corte do top 10 vê o responsável que acompanha: com mais eventos, ele entra no lugar de um formador."""
        for _ in range(10):
            _papel(_evento(10), _pessoa("Formador"), FORMADOR)
        caio = _pessoa("Caio")
        for dia in (11, 12):
            _evento(dia, coordenador=caio, acompanha=True)

        ranking = _ranking(client)

        assert len(ranking) == 10
        assert ranking[caio.id]["eventos"] == 2

    def test_extra_conta_evento_como_conta_hora(self, client):
        bia = _pessoa("Bia")
        _papel(_evento(10), bia, FORMADOR)
        _papel(_evento(11), bia, EXTRA)

        linha = _ranking(client)[bia.id]

        assert linha["eventos"] == 2
        assert linha["horas_trabalhadas"] == 8.0
        assert linha["municipios_atendidos"] == 2

    def test_so_extra_entra_no_ranking(self, client):
        dora = _pessoa("Dora")
        _papel(_evento(10), dora, EXTRA)

        linha = _ranking(client)[dora.id]

        assert (linha["eventos"], linha["horas_trabalhadas"]) == (1, 4.0)

    def test_formador_e_extra_no_mesmo_evento_conta_uma_vez(self, client):
        bia = _pessoa("Bia")
        sol = _evento(10)
        _papel(sol, bia, FORMADOR)
        _papel(sol, bia, EXTRA)

        linha = _ranking(client)[bia.id]

        assert (linha["eventos"], linha["horas_trabalhadas"], linha["municipios_atendidos"]) == (1, 4.0, 1)


# ============================================================================
# Mapa
# ============================================================================


def _municipio(nome: str, uf: str = "CE"):
    n = next(_SEQ)
    return MunicipioFactory(nome=nome, uf=uf, ibge_code=f"29{n:05d}", latitude=-3.7, longitude=-38.5)


def _mapa(client) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    resposta = client.get(reverse("core:metrics-map"))
    assert resposta.status_code == 200, resposta.data
    dados = resposta.json()
    return {m["municipio"]: m for m in dados["by_municipio"]}, {u["uf"]: u for u in dados["by_uf"]}


def _coordenadores_da_uf(client, uf: str = "CE") -> dict[int, dict[str, Any]]:
    resposta = client.get(reverse("core:metrics-map-coordinators"), {"uf": uf})
    assert resposta.status_code == 200, resposta.data
    return {c["id"]: c for c in resposta.json()["coordenadores"]}


class TestMapa:
    def test_responsavel_conta_quem_so_criou_nao(self, client):
        """Decisão do dono (04/11): o Apoio que criou para outro responsável não conta; formador não."""
        mun = _municipio("Aracati")
        apoio = _pessoa("Apoio")
        responsavel = _pessoa("Responsável")
        sol = _evento(10, municipio=mun, criador=apoio, coordenador=responsavel)
        _papel(sol, _pessoa("Formadora"), FORMADOR)
        _evento(11, municipio=mun, criador=apoio, coordenador=responsavel)

        por_mun, por_uf = _mapa(client)
        detalhe = _coordenadores_da_uf(client)

        assert por_mun["Aracati"]["coordenadores"] == 1
        assert por_uf["CE"]["coordenadores"] == 1
        assert {k: v["eventos"] for k, v in detalhe.items()} == {responsavel.id: 2}

    def test_sem_fk_coordenador_quem_criou_conta(self, client):
        mun = _municipio("Sobral")
        criadora = _pessoa("Criadora")
        apoio = _pessoa("Apoio")
        responsavel = _pessoa("Responsável")
        _evento(10, municipio=mun, criador=criadora)
        _evento(11, municipio=mun, criador=apoio, coordenador=responsavel)

        por_mun, por_uf = _mapa(client)
        detalhe = _coordenadores_da_uf(client)

        assert por_mun["Sobral"]["coordenadores"] == 2
        assert por_uf["CE"]["coordenadores"] == 2
        assert {k: v["eventos"] for k, v in detalhe.items()} == {criadora.id: 1, responsavel.id: 1}

    def test_responsavel_que_tambem_e_extra_conta_uma_vez(self, client):
        mun = _municipio("Quixadá")
        criadora = _pessoa("Criadora")
        sol = _evento(10, municipio=mun, criador=criadora)
        _papel(sol, criadora, EXTRA)

        por_mun, por_uf = _mapa(client)
        detalhe = _coordenadores_da_uf(client)

        assert (por_mun["Quixadá"]["coordenadores"], por_uf["CE"]["coordenadores"]) == (1, 1)
        assert detalhe[criadora.id]["eventos"] == 1

    def test_por_uf_e_detalhe_respeitam_a_uf(self, client):
        responsavel = _pessoa("Responsável")
        _evento(10, municipio=_municipio("Fortaleza", "CE"), coordenador=responsavel)
        _evento(11, municipio=_municipio("Natal", "RN"), coordenador=responsavel)
        _evento(12, municipio=_municipio("Mossoró", "RN"))

        _, por_uf = _mapa(client)
        detalhe_rn = _coordenadores_da_uf(client, "RN")

        assert (por_uf["CE"]["coordenadores"], por_uf["RN"]["coordenadores"]) == (1, 2)
        assert detalhe_rn[responsavel.id]["eventos"] == 1
        assert detalhe_rn[responsavel.id]["municipios"] == [{"nome": "Natal", "eventos": 1}]
        assert len(detalhe_rn) == 2

    def test_extra_conta_como_coordenador_do_evento(self, client):
        mun = _municipio("Iguatu")
        criador = _pessoa("Criadora")
        extra = _pessoa("Extra")
        sol = _evento(10, municipio=mun, criador=criador)
        _papel(sol, extra, EXTRA)

        por_mun, por_uf = _mapa(client)
        detalhe = _coordenadores_da_uf(client)

        assert por_mun["Iguatu"]["coordenadores"] == 2
        assert por_uf["CE"]["coordenadores"] == 2
        assert detalhe[extra.id]["eventos"] == 1
        assert detalhe[extra.id]["municipios"] == [{"nome": "Iguatu", "eventos": 1}]

    def test_mesma_pessoa_em_dois_papeis_conta_uma_vez_no_evento(self, client):
        """Quem criou e também é extra (pode, se não for o responsável), e o formador que também é
        extra: um coordenador, um evento."""
        mun = _municipio("Crato")
        criador = _pessoa("Criadora")
        responsavel = _pessoa("Responsável")
        formadora = _pessoa("Formadora")
        projeto = ProjetoFactory(nome="Projeto Extras")
        sol = _evento(10, municipio=mun, criador=criador, coordenador=responsavel, projeto=projeto)
        _papel(sol, criador, EXTRA)
        _papel(sol, formadora, FORMADOR)
        _papel(sol, formadora, EXTRA)

        por_mun, por_uf = _mapa(client)
        detalhe = _coordenadores_da_uf(client)

        assert por_mun["Crato"]["coordenadores"] == 3
        assert por_uf["CE"]["coordenadores"] == 3
        assert {k: v["eventos"] for k, v in detalhe.items()} == {criador.id: 1, responsavel.id: 1, formadora.id: 1}
        assert detalhe[criador.id]["projetos"] == [{"nome": "Projeto Extras", "eventos": 1}]
        assert detalhe[criador.id]["municipios"] == [{"nome": "Crato", "eventos": 1}]

    def test_detalhe_ignora_evento_que_sai_do_filtro_entre_as_leituras(self, client, monkeypatch):
        """Os pares e os eventos vêm de consultas separadas: um evento reprovado no meio não dá 500."""
        from apps.core.views.metrics import map_metrics

        mun = _municipio("Canindé")
        fica = _pessoa("Fica")
        sai = _pessoa("Sai")
        _evento(10, municipio=mun, coordenador=fica)
        reprovado_no_meio = _evento(11, municipio=mun, coordenador=sai)
        original = map_metrics.coordenadores_do_evento

        def reprova_depois_de_ler(solicitacoes):
            pares = original(solicitacoes)
            Solicitacao.objects.filter(pk=reprovado_no_meio.pk).update(status=Solicitacao.Status.REPROVADO)
            return pares

        monkeypatch.setattr(map_metrics, "coordenadores_do_evento", reprova_depois_de_ler)
        resposta = client.get(reverse("core:metrics-map-coordinators"), {"uf": "CE", "status": "aprovado"})

        assert resposta.status_code == 200
        assert [c["id"] for c in resposta.json()["coordenadores"]] == [fica.id]


# ============================================================================
# Sem N+1: o número de consultas não cresce com eventos e pessoas
# ============================================================================


def _consultas(client, url: str, params: dict[str, Any]) -> int:
    with CaptureQueriesContext(connection) as ctx:
        assert client.get(url, params).status_code == 200
    return len(ctx.captured_queries)


def _eventos_variados(n: int, mun):
    for i in range(n):
        sol = _evento(10 + i, municipio=mun, criador=_pessoa("Apoio"), coordenador=_pessoa("Resp"), acompanha=True)
        _papel(sol, _pessoa("Formadora"), FORMADOR)
        _papel(sol, _pessoa("Extra"), EXTRA)


@pytest.mark.parametrize(
    ("url", "params"),
    [
        ("/api/metrics/team/formadores/", {"days": 30}),
        ("/api/metrics/map/", {}),
        ("/api/metrics/map/coordinators/", {"uf": "CE"}),
    ],
)
def test_consultas_nao_crescem_com_os_eventos(client, url, params):
    _eventos_variados(1, _municipio("Pacatuba"))
    _consultas(client, url, params)  # aquece o cache de Configurações
    poucas = _consultas(client, url, params)
    _eventos_variados(5, _municipio("Maranguape"))

    assert _consultas(client, url, params) == poucas

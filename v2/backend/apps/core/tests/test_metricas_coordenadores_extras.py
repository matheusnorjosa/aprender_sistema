"""
Métricas com vários coordenadores no evento (decisão do dono, 03/11/2026).

Os coordenadores além do responsável (`Participation(role=COORD_ACOMPANHA)`) ocupam a agenda e
contam horas como o formador. Nas métricas:

- Ranking de formadores (`/api/metrics/team/formadores/`): "eventos" conta os mesmos papéis que as
  horas contam sempre (`ENFORCED_ROLES`), um por evento.
- Mapa (`/api/metrics/map/` e `/api/metrics/map/coordinators/`): os coordenadores do evento são os
  do convite (papel COORDENADOR: quem criou e o responsável) mais os COORD_ACOMPANHA, sem repetir
  pessoa no evento.

Sem COORD_ACOMPANHA os números são os de antes (em produção, 04/11/2026, há 0 dessas linhas).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportOptionalMemberAccess=false, reportIndexIssue=false

from __future__ import annotations

from datetime import date, datetime
from itertools import count
from typing import Any
from zoneinfo import ZoneInfo

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
    def test_sem_extra_numeros_de_antes(self, client):
        """Sem COORD_ACOMPANHA: formador, responsável que acompanha e convidado como antes."""
        bia = _pessoa("Bia")
        caio = _pessoa("Caio")
        for dia in (10, 11):
            _papel(_evento(dia), bia, FORMADOR)
        # Caio é responsável que acompanha (conta hora, não entra no ranking por evento) e convidado.
        sol = _evento(12, coordenador=caio, acompanha=True)
        _papel(sol, bia, FORMADOR)
        _papel(_evento(13), caio, Participation.Role.CONVIDADO)

        ranking = _ranking(client)

        assert set(ranking) == {bia.id}
        assert ranking[bia.id]["eventos"] == 3
        assert ranking[bia.id]["horas_trabalhadas"] == 12.0
        assert ranking[bia.id]["municipios_atendidos"] == 3

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
    def test_sem_extra_numeros_de_antes(self, client):
        """Sem COORD_ACOMPANHA: quem criou e o responsável (papel COORDENADOR) contam; formador não."""
        mun = _municipio("Aracati")
        criador = _pessoa("Criadora")
        responsavel = _pessoa("Responsável")
        sol = _evento(10, municipio=mun, criador=criador, coordenador=responsavel)
        _papel(sol, _pessoa("Formadora"), FORMADOR)
        _evento(11, municipio=mun, criador=criador)

        por_mun, por_uf = _mapa(client)
        detalhe = _coordenadores_da_uf(client)

        assert por_mun["Aracati"]["coordenadores"] == 2
        assert por_uf["CE"]["coordenadores"] == 2
        assert {k: v["eventos"] for k, v in detalhe.items()} == {criador.id: 2, responsavel.id: 1}

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

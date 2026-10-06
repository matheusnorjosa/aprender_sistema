"""
Horas de formação (CH) com teto por evento — decisão do dono, 02/10 e 05/10/2026.

CH de um evento para uma pessoa = min(fim − início, TETO). TETO = o parâmetro de
Configurações `AVAILABILITY_DAILY_LIMIT_HOURS` (padrão 8 h). As CH do dia se somam (não há
teto por dia). Evento que cruza a meia-noite conta inteiro no dia local do INÍCIO
(America/Fortaleza). Online conta igual. Só evento aprovado, de qualquer projeto. Conta o
FORMADOR sempre e o coordenador responsável só quando `coordenador_acompanha=True`;
COORD_ACOMPANHA e convidado não contam.

A Grade Mensal e o painel de Equipe usam a mesma função e dão o mesmo número.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportOptionalMemberAccess=false, reportIndexIssue=false

from __future__ import annotations

from datetime import date, datetime
from itertools import count
from zoneinfo import ZoneInfo

from rest_framework.test import APIClient

import pytest

from apps.core.models import Participation, Solicitacao
from apps.core.services.config_service import bust_cfg
from apps.core.services.horas_formacao import horas_formacao
from apps.core.services.monthly_grid_service import build_monthly_grid
from apps.core.tests.factories import (
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db

TZ = ZoneInfo("America/Fortaleza")
DIA = date(2026, 3, 10)
_SEQ = count()


def _local(dia: date, hora: int) -> datetime:
    return datetime(dia.year, dia.month, dia.day, hora, 0, tzinfo=TZ)


@pytest.fixture(autouse=True)
def _teto_padrao(settings):
    settings.AVAILABILITY_DAILY_LIMIT_HOURS = 8
    # O cache de Config sobrevive ao rollback: um valor deixado por outro arquivo valeria aqui.
    bust_cfg("availability")


@pytest.fixture
def formador():
    return UsuarioFactory(username="formador_ch", email="formador_ch@example.invalid", first_name="Bia")


@pytest.fixture
def coordenador():
    return UsuarioFactory(username="coord_ch", email="coord_ch@example.invalid", first_name="Caio")


@pytest.fixture
def projeto_super():
    return ProjetoFactory(nome="Projeto CH SUPER", fluxo="SUPER")


def _evento(
    inicio: datetime,
    fim: datetime,
    *,
    formador=None,
    status: str = "aprovado",
    projeto=None,
    coordenador=None,
    acompanha: bool = False,
    is_online: bool = False,
    papel: str = Participation.Role.FORMADOR,
) -> Solicitacao:
    n = next(_SEQ)
    criador = coordenador or UsuarioFactory(email=f"criador_ch_{n}@example.invalid", username=f"criador_ch_{n}")
    sol = SolicitacaoFactory(
        usuario=criador,
        coordenador=coordenador,
        coordenador_acompanha=acompanha,
        municipio=MunicipioFactory(),
        tipo_evento=TipoEventoFactory(),
        projeto=projeto or ProjetoFactory(),
        inicio=inicio,
        fim=fim,
        status=status,
        is_online=is_online,
    )
    if formador is not None:
        Participation.objects.create(solicitacao=sol, usuario=formador, role=papel)
    return sol


def _ch(usuario, de: date = DIA, ate: date = DIA) -> float:
    return horas_formacao([usuario.id], de=de, ate=ate)[usuario.id].total


# ============================================================================
# A regra
# ============================================================================


class TestRegraDaContagem:
    def test_evento_das_7_as_23_conta_8_horas(self, formador):
        _evento(_local(DIA, 7), _local(DIA, 23), formador=formador)

        assert _ch(formador) == 8.0

    def test_dois_eventos_de_5_horas_no_dia_somam_10(self, formador):
        _evento(_local(DIA, 7), _local(DIA, 12), formador=formador)
        _evento(_local(DIA, 13), _local(DIA, 18), formador=formador)

        resultado = horas_formacao([formador.id], de=DIA, ate=DIA)[formador.id]
        assert resultado.total == 10.0
        assert resultado.por_dia == {DIA: 10.0}

    def test_evento_das_22_as_02_conta_inteiro_no_dia_do_inicio(self, formador):
        dia_seguinte = date(2026, 3, 11)
        _evento(_local(DIA, 22), _local(dia_seguinte, 2), formador=formador)

        resultado = horas_formacao([formador.id], de=DIA, ate=dia_seguinte)[formador.id]
        assert resultado.por_dia == {DIA: 4.0}
        # Pedindo só o dia seguinte, o evento não aparece: ele é do dia do início.
        assert _ch(formador, de=dia_seguinte, ate=dia_seguinte) == 0.0

    def test_pendente_nao_conta(self, formador):
        _evento(_local(DIA, 8), _local(DIA, 12), formador=formador, status="pendente")

        assert _ch(formador) == 0.0

    def test_coordenador_que_nao_acompanha_nao_conta(self, coordenador):
        _evento(_local(DIA, 8), _local(DIA, 12), coordenador=coordenador, acompanha=False)

        assert _ch(coordenador) == 0.0

    def test_coordenador_que_acompanha_conta(self, coordenador):
        _evento(_local(DIA, 8), _local(DIA, 12), coordenador=coordenador, acompanha=True)

        assert _ch(coordenador) == 4.0

    def test_coordenador_que_acompanha_e_tambem_formador_conta_uma_vez(self, coordenador):
        _evento(_local(DIA, 8), _local(DIA, 12), formador=coordenador, coordenador=coordenador, acompanha=True)

        assert _ch(coordenador) == 4.0

    @pytest.mark.parametrize("papel", [Participation.Role.COORD_ACOMPANHA, Participation.Role.CONVIDADO])
    def test_coord_acompanha_e_convidado_nao_contam(self, formador, papel):
        _evento(_local(DIA, 8), _local(DIA, 12), formador=formador, papel=papel)

        assert _ch(formador) == 0.0

    def test_online_conta_igual(self, formador):
        _evento(_local(DIA, 8), _local(DIA, 12), formador=formador, is_online=True)

        assert _ch(formador) == 4.0

    def test_projeto_nao_super_conta(self, formador):
        _evento(_local(DIA, 8), _local(DIA, 12), formador=formador, projeto=ProjetoFactory(fluxo="NAO_SUPER"))

        assert _ch(formador) == 4.0

    def test_teto_vem_de_configuracoes(self, formador, settings):
        settings.AVAILABILITY_DAILY_LIMIT_HOURS = 6
        bust_cfg("availability")
        _evento(_local(DIA, 8), _local(DIA, 15), formador=formador)

        assert _ch(formador) == 6.0

    def test_varias_pessoas_sem_consulta_por_pessoa(self, django_assert_max_num_queries):
        pessoas = [UsuarioFactory(username=f"ch_lote_{i}", email=f"ch_lote_{i}@example.invalid") for i in range(5)]
        for pessoa in pessoas:
            _evento(_local(DIA, 8), _local(DIA, 10), formador=pessoa)
            _evento(_local(DIA, 14), _local(DIA, 16), formador=pessoa)
        ids = [p.id for p in pessoas]
        horas_formacao(ids[:1], de=DIA, ate=DIA)  # aquece o cache de Config

        with django_assert_max_num_queries(2):
            resultado = horas_formacao(ids, de=DIA, ate=DIA)

        assert {uid: r.total for uid, r in resultado.items()} == dict.fromkeys(ids, 4.0)

    def test_pessoa_sem_evento_volta_com_zero(self, formador):
        resultado = horas_formacao([formador.id], de=DIA, ate=DIA)

        assert resultado[formador.id].total == 0.0
        assert resultado[formador.id].por_dia == {}


# ============================================================================
# Grade Mensal e painel de Equipe usam a mesma conta
# ============================================================================


class TestGradeEPainel:
    def test_grade_aplica_o_teto_no_mes_e_no_ano(self, formador, projeto_super):
        _evento(_local(DIA, 7), _local(DIA, 23), formador=formador, projeto=projeto_super)
        _evento(_local(date(2026, 1, 5), 7), _local(date(2026, 1, 5), 23), formador=formador, projeto=projeto_super)

        grade = build_monthly_grid(year=2026, month=3, role="FORMADOR")
        pessoa = next(p for p in grade["people"] if p["id"] == formador.id)

        assert pessoa["ch_month"] == 8.0
        assert pessoa["ch_year"] == 16.0

    def test_aba_coordenadores_so_conta_quem_acompanha(self, coordenador, projeto_super):
        outro = UsuarioFactory(username="coord_ch_2", email="coord_ch_2@example.invalid", first_name="Duda")
        for coord, acompanha in ((coordenador, True), (outro, False)):
            sol = _evento(
                _local(DIA, 8), _local(DIA, 12), coordenador=coord, acompanha=acompanha, projeto=projeto_super
            )
            Participation.objects.create(solicitacao=sol, usuario=coord, role=Participation.Role.COORDENADOR)

        grade = build_monthly_grid(year=2026, month=3, role="COORDENADOR")
        ch = {p["id"]: p["ch_month"] for p in grade["people"]}

        assert ch == {coordenador.id: 4.0, outro.id: 0.0}

    def test_grade_e_painel_dao_o_mesmo_numero(self, formador, projeto_super, monkeypatch):
        _evento(_local(DIA, 7), _local(DIA, 23), formador=formador, projeto=projeto_super)
        _evento(_local(date(2026, 3, 20), 7), _local(date(2026, 3, 20), 12), formador=formador)
        _evento(_local(date(2026, 3, 20), 13), _local(date(2026, 3, 20), 18), formador=formador, is_online=True)
        # Fora do período nos dois: fevereiro.
        _evento(_local(date(2026, 2, 27), 8), _local(date(2026, 2, 27), 12), formador=formador)
        # Criado há muito tempo não importa: vale o início do evento.
        agora = _local(date(2026, 3, 31), 12)
        monkeypatch.setattr("django.utils.timezone.now", lambda: agora)

        grade = build_monthly_grid(year=2026, month=3, role="FORMADOR")
        ch_grade = next(p for p in grade["people"] if p["id"] == formador.id)["ch_month"]

        client = APIClient()
        client.force_authenticate(user=UsuarioFactory(is_superuser=True, email="adm_ch@example.invalid"))
        resposta = client.get("/api/metrics/team/formadores/", {"days": 30})
        assert resposta.status_code == 200, resposta.data
        ch_painel = next(f for f in resposta.json()["formadores"] if f["id"] == formador.id)["horas_trabalhadas"]

        assert ch_grade == 18.0
        assert ch_painel == ch_grade

    def test_painel_filtra_pelo_inicio_do_evento_nao_pela_criacao(self, formador, monkeypatch):
        agora = _local(date(2026, 3, 31), 12)
        monkeypatch.setattr("django.utils.timezone.now", lambda: agora)
        sol = _evento(_local(date(2025, 6, 2), 8), _local(date(2025, 6, 2), 12), formador=formador)
        # Evento antigo gravado agora (ex.: importação): não é hora do período.
        Solicitacao.objects.filter(pk=sol.pk).update(created_at=agora)

        client = APIClient()
        client.force_authenticate(user=UsuarioFactory(is_superuser=True, email="adm_ch2@example.invalid"))
        resposta = client.get("/api/metrics/team/formadores/", {"days": 30})

        assert resposta.status_code == 200, resposta.data
        assert [f["id"] for f in resposta.json()["formadores"]] == []

    def test_grade_em_cache_acompanha_o_teto_salvo(self, formador, projeto_super, settings):
        _evento(_local(DIA, 7), _local(DIA, 23), formador=formador, projeto=projeto_super)
        client = APIClient()
        client.force_authenticate(user=UsuarioFactory(is_superuser=True, email="adm_ch3@example.invalid"))
        params = {"year": 2026, "month": 3, "role": "FORMADOR"}

        def ch_mes() -> float:
            resposta = client.get("/api/availability/monthly/", params)
            assert resposta.status_code == 200, resposta.data
            return next(p for p in resposta.json()["people"] if p["id"] == formador.id)["ch_month"]

        assert ch_mes() == 8.0
        settings.AVAILABILITY_DAILY_LIMIT_HOURS = 10
        bust_cfg("availability")

        assert ch_mes() == 10.0

    def test_grade_e_painel_arredondam_igual(self, formador, projeto_super, monkeypatch):
        # 08:00–11:45 = 3,75 h e 14:00–15:20 = 1h20 (1,333… h) em dias diferentes.
        _evento(_local(DIA, 8), datetime(2026, 3, 10, 11, 45, tzinfo=TZ), formador=formador, projeto=projeto_super)
        _evento(_local(date(2026, 3, 12), 14), datetime(2026, 3, 12, 15, 20, tzinfo=TZ), formador=formador)
        monkeypatch.setattr("django.utils.timezone.now", lambda: _local(date(2026, 3, 31), 12))

        grade = build_monthly_grid(year=2026, month=3, role="FORMADOR")
        ch_grade = next(p for p in grade["people"] if p["id"] == formador.id)["ch_month"]
        client = APIClient()
        client.force_authenticate(user=UsuarioFactory(is_superuser=True, email="adm_ch4@example.invalid"))
        resposta = client.get("/api/metrics/team/formadores/", {"days": 31})
        ch_painel = next(f for f in resposta.json()["formadores"] if f["id"] == formador.id)["horas_trabalhadas"]

        assert ch_grade == 5.08
        assert ch_painel == ch_grade

    def test_painel_de_7_dias_cobre_7_dias_locais(self, formador, monkeypatch):
        monkeypatch.setattr("django.utils.timezone.now", lambda: _local(date(2026, 10, 5), 12))
        _evento(_local(date(2026, 9, 28), 8), _local(date(2026, 9, 28), 10), formador=formador)  # 8º dia: fora
        _evento(_local(date(2026, 9, 29), 8), _local(date(2026, 9, 29), 11), formador=formador)  # 1º dia: dentro

        client = APIClient()
        client.force_authenticate(user=UsuarioFactory(is_superuser=True, email="adm_ch5@example.invalid"))
        resposta = client.get("/api/metrics/team/formadores/", {"days": 7})

        (linha,) = [f for f in resposta.json()["formadores"] if f["id"] == formador.id]
        assert linha["eventos"] == 1
        assert linha["horas_trabalhadas"] == 3.0

    def test_openapi_do_check_nao_fala_mais_do_limite_diario(self):
        client = APIClient()
        client.force_authenticate(user=UsuarioFactory(is_superuser=True, email="adm_ch6@example.invalid"))
        schema = client.get("/api/schema/?format=json").json()
        descricao = schema["paths"]["/api/availability/check/"]["get"]["description"]

        assert "não impede o evento" not in descricao
        assert "não é mais emitido" in descricao

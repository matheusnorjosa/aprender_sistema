"""CON-08 B, decisões do dono de 24/11/2026 (P6 e P7): o evento cancelado na agenda não vai acontecer.

A linha segue `aprovado` com `cancelado_na_agenda=True` (o título no Google tem "(CANCELADO)"). Desde 24/11, com o
Cancelar confirmado (a linha marcada e `PUBLISHED`, revisão da rodada 6), ela:

- libera a agenda do formador e do coordenador que acompanha (motor de conflito, consultivo e de enforcement);
- sai das horas de formação (CH do painel de Equipe e ranking de formadores) e da Grade Mensal;
- sai das contagens de "eventos futuros" (Início e Dashboard Geral), da auditoria RD-02 e das pendências de compra
  do DAT (evento cancelado não atende a compra).

Continua nas listas, com a etiqueta "Cancelado na agenda" (Meus Eventos, Pré-agenda, Publicar na agenda).
Cada teste põe, ao lado da linha marcada, uma igual sem a marca: o que muda é só a marca.

A marca vem do pedido, antes do Google: marcada em `PENDING` (o Cancelar na fila) ou em `ERROR` (o Cancelar que
falhou, sem nada escrito no Google), a linha segue ocupando tudo, porque o evento continua ativo lá.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportOptionalMemberAccess=false, reportIndexIssue=false, reportCallIssue=false

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from io import StringIO
from itertools import count
from zoneinfo import ZoneInfo

from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import AvailabilityBlock, Participation, Solicitacao
from apps.core.services.availability_service import check_conflicts, check_conflicts_uncached
from apps.core.services.config_service import bust_cfg
from apps.core.services.horas_formacao import horas_formacao, ocupacoes_aprovadas
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
def _parametros_padrao(settings):
    settings.AVAILABILITY_DAILY_LIMIT_HOURS = 8
    settings.TRAVEL_BUFFER_MINUTES = 60
    bust_cfg("availability")


@pytest.fixture
def formador():
    n = next(_SEQ)
    return UsuarioFactory(username=f"formador_cancelado_{n}", email=f"formador_cancelado_{n}@example.invalid")


def _evento(
    inicio: datetime,
    fim: datetime,
    *,
    formador=None,
    cancelado: bool,
    projeto=None,
    municipio=None,
    coordenador=None,
    acompanha: bool = False,
    gcal_status: str | None = None,
) -> Solicitacao:
    """`cancelado=True` sem `gcal_status`: o Cancelar confirmado (a linha marcada volta a PUBLISHED)."""
    n = next(_SEQ)
    criador = coordenador or UsuarioFactory(username=f"criador_cancelado_{n}", email=f"criador_c_{n}@example.invalid")
    s = SolicitacaoFactory(
        usuario=criador,
        coordenador=coordenador,
        coordenador_acompanha=acompanha,
        municipio=municipio or MunicipioFactory(),
        tipo_evento=TipoEventoFactory(nome="Presencial"),
        projeto=projeto or ProjetoFactory(),
        inicio=inicio,
        fim=fim,
        status="aprovado",
        cancelado_na_agenda=cancelado,
        gcal_status=gcal_status or ("PUBLISHED" if cancelado else "NONE"),
    )
    if formador is not None:
        Participation.objects.create(solicitacao=s, usuario=formador, role=Participation.Role.FORMADOR)
    return s


# =============================================================================
# Disponibilidade (RD-01 e RD-04)
# =============================================================================


class TestDisponibilidade:
    def test_evento_cancelado_nao_conflita_com_o_mesmo_horario(self, formador):
        _evento(_local(DIA, 8), _local(DIA, 12), formador=formador, cancelado=True)

        resultado = check_conflicts_uncached(usuario=formador, inicio=_local(DIA, 9), fim=_local(DIA, 11))

        assert (resultado.ok, resultado.conflicts) == (True, [])

    def test_evento_igual_sem_a_marca_conflita(self, formador):
        normal = _evento(_local(DIA, 8), _local(DIA, 12), formador=formador, cancelado=False)

        resultado = check_conflicts_uncached(usuario=formador, inicio=_local(DIA, 9), fim=_local(DIA, 11))

        assert [(c.code, c.ref_id) for c in resultado.conflicts] == [("X", normal.pk)]

    def test_evento_cancelado_nao_pede_deslocamento(self, formador):
        """RD-04: o vizinho cancelado em outra cidade não conta; o vizinho real (mais longe) é o conferido."""
        _evento(_local(DIA, 8), _local(DIA, 12), formador=formador, cancelado=True)

        resultado = check_conflicts_uncached(
            usuario=formador, inicio=_local(DIA, 12), fim=_local(DIA, 14), municipio=MunicipioFactory()
        )

        assert resultado.ok, resultado.conflicts

    def test_coordenador_que_acompanha_fica_livre(self):
        coordenador = UsuarioFactory(username="coord_cancelado", email="coord_cancelado@example.invalid")
        _evento(_local(DIA, 8), _local(DIA, 12), coordenador=coordenador, acompanha=True, cancelado=True)

        resultado = check_conflicts_uncached(usuario=coordenador, inicio=_local(DIA, 9), fim=_local(DIA, 11))

        assert resultado.ok, resultado.conflicts

    def test_lote_tambem_ignora_o_cancelado(self, formador):
        """No POST do lote a consulta é outra (aprovado OU irmão do lote): a marca vale nela também."""
        _evento(_local(DIA, 8), _local(DIA, 12), formador=formador, cancelado=True)
        irmao = _evento(_local(DIA, 15), _local(DIA, 16), formador=formador, cancelado=False)

        resultado = check_conflicts_uncached(
            usuario=formador, inicio=_local(DIA, 9), fim=_local(DIA, 11), lote={irmao.pk: 2}
        )

        assert resultado.ok, resultado.conflicts

    def test_checagem_com_cache_ve_a_marca_na_hora(self, formador):
        """A tela consulta a versão com cache: marcar a linha (sem mexer na participação) libera já na consulta
        seguinte, e tirar a marca (o Cancelar que não achou o evento) ocupa de novo."""
        s = _evento(_local(DIA, 8), _local(DIA, 12), formador=formador, cancelado=False, gcal_status="PUBLISHED")
        janela = {"usuario": formador, "inicio": _local(DIA, 9), "fim": _local(DIA, 11)}
        assert not check_conflicts(**janela).ok

        s.cancelado_na_agenda = True
        s.save(update_fields=["cancelado_na_agenda"])
        assert check_conflicts(**janela).ok

        s.cancelado_na_agenda = False
        s.save(update_fields=["cancelado_na_agenda"])
        assert not check_conflicts(**janela).ok

    def test_checagem_com_cache_libera_so_quando_o_google_confirma(self, formador):
        """Revisão da rodada 6: o pedido marca e põe PENDING (ainda ocupa); a tarefa que termina volta a linha a
        PUBLISHED pelo `mark_gcal`, sem mexer na marca, e só então a consulta com cache vê a agenda livre."""
        s = _evento(_local(DIA, 8), _local(DIA, 12), formador=formador, cancelado=False, gcal_status="PUBLISHED")
        janela = {"usuario": formador, "inicio": _local(DIA, 9), "fim": _local(DIA, 11)}
        assert not check_conflicts(**janela).ok

        s.cancelado_na_agenda = True
        s.save(update_fields=["cancelado_na_agenda"])
        s.mark_gcal(status=Solicitacao.GCalStatus.PENDING, payload_hash=s.gcal_payload_hash, error="")
        assert not check_conflicts(**janela).ok, "na fila, o evento segue ativo no Google"

        s.mark_gcal(status=Solicitacao.GCalStatus.PUBLISHED, payload_hash=s.gcal_payload_hash, error="")
        assert check_conflicts(**janela).ok


# =============================================================================
# Revisão da rodada 6: a marca sem o Cancelar confirmado não libera nada
# =============================================================================

_SEM_CONFIRMACAO = pytest.mark.parametrize("gcal_status", ["PENDING", "ERROR"])


class TestMarcaSemConfirmacaoSegueOcupando:
    """O pedido grava a marca antes do Google. Em PENDING (na fila) ou ERROR (o Cancelar falhou antes de escrever:
    disjuntor, 5xx, sem acesso, credencial), o evento segue ativo no Google e no DFF: ocupa a agenda e conta na CH,
    na Grade e nos eventos futuros, como o sem marca."""

    @_SEM_CONFIRMACAO
    def test_conflita(self, formador, gcal_status):
        marcado = _evento(_local(DIA, 8), _local(DIA, 12), formador=formador, cancelado=True, gcal_status=gcal_status)

        resultado = check_conflicts_uncached(usuario=formador, inicio=_local(DIA, 9), fim=_local(DIA, 11))

        assert [(c.code, c.ref_id) for c in resultado.conflicts] == [("X", marcado.pk)]

    @_SEM_CONFIRMACAO
    def test_lote_tambem_conflita(self, formador, gcal_status):
        _evento(_local(DIA, 8), _local(DIA, 12), formador=formador, cancelado=True, gcal_status=gcal_status)
        irmao = _evento(_local(DIA, 15), _local(DIA, 16), formador=formador, cancelado=False)

        resultado = check_conflicts_uncached(
            usuario=formador, inicio=_local(DIA, 9), fim=_local(DIA, 11), lote={irmao.pk: 2}
        )

        assert not resultado.ok

    @_SEM_CONFIRMACAO
    def test_conta_na_ch_e_na_grade(self, formador, gcal_status):
        projeto_super = ProjetoFactory(nome=f"Projeto Grade {gcal_status}", fluxo="SUPER")
        marcado = _evento(
            _local(DIA, 8),
            _local(DIA, 12),
            formador=formador,
            projeto=projeto_super,
            cancelado=True,
            gcal_status=gcal_status,
        )

        assert (formador.id, marcado.pk) in ocupacoes_aprovadas(de=DIA, ate=DIA)
        grade = build_monthly_grid(year=2026, month=3, role="FORMADOR")
        linha = {p["id"]: i for i, p in enumerate(grade["people"])}[formador.id]
        assert grade["cells"][linha][DIA.day - 1] == "E"
        assert grade["people"][linha]["ch_month"] == 4.0

    @_SEM_CONFIRMACAO
    def test_conta_nos_eventos_futuros(self, gcal_status):
        _futuro(cancelado=True, gcal_status=gcal_status)

        resposta = _superusuario().get("/api/stats/home/")

        assert resposta.status_code == 200, resposta.data
        assert resposta.json()["upcoming_events"] == 1


# =============================================================================
# Horas de formação (CH, ranking) e Grade Mensal
# =============================================================================


class TestHorasEGrade:
    def test_ocupacoes_do_formador_e_do_coordenador_que_acompanha_ignoram_o_cancelado(self, formador):
        coordenador = UsuarioFactory(username="coord_ch_cancelado", email="coord_ch_cancelado@example.invalid")
        cancelado = _evento(
            _local(DIA, 8), _local(DIA, 12), formador=formador, coordenador=coordenador, acompanha=True, cancelado=True
        )
        normal = _evento(
            _local(DIA, 14),
            _local(DIA, 16),
            formador=formador,
            coordenador=coordenador,
            acompanha=True,
            cancelado=False,
        )

        ocupacoes = ocupacoes_aprovadas(de=DIA, ate=DIA)

        assert (formador.id, cancelado.pk) not in ocupacoes and (coordenador.id, cancelado.pk) not in ocupacoes
        assert (formador.id, normal.pk) in ocupacoes and (coordenador.id, normal.pk) in ocupacoes
        ch = horas_formacao([formador.id, coordenador.id], de=DIA, ate=DIA)
        assert (ch[formador.id].total, ch[coordenador.id].total) == (2.0, 2.0)

    def test_grade_nao_marca_o_dia_nem_conta_a_ch(self, formador):
        projeto_super = ProjetoFactory(nome="Projeto Grade Cancelado", fluxo="SUPER")
        outro_dia = date(2026, 3, 12)
        _evento(_local(DIA, 8), _local(DIA, 12), formador=formador, projeto=projeto_super, cancelado=False)
        _evento(_local(outro_dia, 8), _local(outro_dia, 12), formador=formador, projeto=projeto_super, cancelado=True)

        grade = build_monthly_grid(year=2026, month=3, role="FORMADOR")
        linha = {p["id"]: i for i, p in enumerate(grade["people"])}[formador.id]

        assert grade["cells"][linha][DIA.day - 1] == "E"
        assert grade["cells"][linha][outro_dia.day - 1] == ""
        assert f"{linha}:{outro_dia.day - 1}" not in grade["details_index"]
        assert grade["people"][linha]["ch_month"] == 4.0


# =============================================================================
# Contagens de "eventos futuros", auditoria RD-02 e pendências de compra
# =============================================================================


def _futuro(*, cancelado: bool, gcal_status: str | None = None) -> Solicitacao:
    inicio = timezone.now() + timedelta(days=5)
    return SolicitacaoFactory(
        status="aprovado",
        inicio=inicio,
        fim=inicio + timedelta(hours=2),
        cancelado_na_agenda=cancelado,
        gcal_status=gcal_status or ("PUBLISHED" if cancelado else "NONE"),
    )


def _superusuario() -> APIClient:
    api = APIClient()
    api.force_authenticate(UsuarioFactory(superuser=True))
    return api


def test_inicio_nao_conta_o_cancelado_nos_eventos_futuros():
    _futuro(cancelado=False)
    _futuro(cancelado=True)

    resposta = _superusuario().get("/api/stats/home/")

    assert resposta.status_code == 200, resposta.data
    assert resposta.json()["upcoming_events"] == 1


def test_dashboard_geral_nao_conta_o_cancelado_nos_eventos_futuros():
    """ "Eventos aprovados" segue contando: a aprovação aconteceu. "Eventos futuros" não: o evento não vai acontecer."""
    _futuro(cancelado=False)
    _futuro(cancelado=True)

    resposta = _superusuario().get("/api/dashboard/overview/")

    assert resposta.status_code == 200, resposta.data
    assert (resposta.data["kpis"]["eventos_futuros"], resposta.data["kpis"]["eventos_aprovados"]) == (1, 2)


@pytest.mark.parametrize(("cancelado", "violacoes"), [(True, 0), (False, 1)])
def test_auditoria_rd02_nao_conta_o_cancelado_no_bloqueio_total(cancelado, violacoes):
    pessoa = UsuarioFactory(username="pessoa_rd02_cancelado", email="rd02_cancelado@example.invalid")
    inicio = timezone.now() + timedelta(days=5)
    AvailabilityBlock.objects.create(usuario=pessoa, tipo="T", inicio=inicio, fim=inicio + timedelta(hours=4))
    SolicitacaoFactory(
        usuario=pessoa,
        status="aprovado",
        inicio=inicio + timedelta(hours=1),
        fim=inicio + timedelta(hours=2),
        cancelado_na_agenda=cancelado,
        gcal_status="PUBLISHED",
    )

    saida = StringIO()
    call_command("compliance_audit", "--days=30", "--format=json", stdout=saida)

    rd02 = next(c for c in json.loads(saida.getvalue())["checks"] if c["rule"] == "RD-02")
    assert rd02["violations"] == violacoes

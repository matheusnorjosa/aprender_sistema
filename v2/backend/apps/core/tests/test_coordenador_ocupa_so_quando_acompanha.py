"""
Agenda: o coordenador responsável só ocupa a agenda quando acompanha o evento.

Decisão do dono (05/10/2026, OK explícito para mudar a regra de disponibilidade, CP-03):
- a conferência de agenda (RD-01 sobreposição, RD-02/03 bloqueios, RD-04 deslocamento e o
  aviso M) vale para TODOS os formadores do evento, sempre;
- o coordenador responsável (`Solicitacao.coordenador`; sem ele, quem criou) só entra quando
  `coordenador_acompanha=True`;
- quem cria deixa de entrar automaticamente; as linhas COORDENADOR e COORD_ACOMPANHA não
  ocupam mais (continuam servindo ao convite do Google).

Um evento existente ocupa a agenda de uma pessoa se ela é FORMADORA nele, ou se é a
responsável e ele tem `coordenador_acompanha=True` (`availability_service.ocupa_agenda_q`).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false

from __future__ import annotations

import itertools
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from rest_framework.test import APIClient

import pytest

from apps.core.models import AvailabilityBlock, Compra, Participation, Solicitacao
from apps.core.services.availability_service import check_conflicts, check_conflicts_uncached
from apps.core.services.solicitacao_availability import collect_participants
from apps.core.tests.factories import (
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db

_TZ = ZoneInfo("America/Fortaleza")
# Relógio fixo: um dia útil bem no futuro, para o evento nunca virar "passado".
_DIA = datetime(2031, 3, 10, tzinfo=_TZ)
_INICIO = _DIA.replace(hour=9)
_FIM = _DIA.replace(hour=11)
_HASH = itertools.count(1)
_N = itertools.count(1)


def _pessoa(*grupos: str):
    n = next(_N)
    return UsuarioFactory(
        username=f"agenda_acomp_{n}",
        email=f"agenda_acomp_{n}@example.invalid",
        first_name=f"Pessoa{n}",
        last_name="Ficticia",
        groups=list(grupos),
    )


def _evento_aprovado(*, criador, formadores=(), acompanha=False, coordenador=None, inicio=_INICIO, fim=_FIM):
    sol = SolicitacaoFactory(
        usuario=criador,
        coordenador=coordenador,
        coordenador_acompanha=acompanha,
        status=Solicitacao.Status.APROVADO,
        inicio=inicio,
        fim=fim,
    )
    Participation.objects.create(solicitacao=sol, usuario=criador, role=Participation.Role.COORDENADOR)
    for f in formadores:
        Participation.objects.create(solicitacao=sol, usuario=f, role=Participation.Role.FORMADOR)
    return sol


def _ok(usuario) -> bool:
    return check_conflicts_uncached(usuario=usuario, inicio=_INICIO, fim=_FIM).ok


class TestEventoExistenteOcupa:
    """`availability_service`: quem um evento aprovado ocupa."""

    def test_quem_criou_e_nao_acompanha_nao_fica_ocupado(self):
        coord, formador = _pessoa("Coordenador"), _pessoa("Formador")
        _evento_aprovado(criador=coord, coordenador=coord, formadores=[formador], acompanha=False)
        assert _ok(coord), "coordenador que não acompanha não pode ter a agenda ocupada"

    def test_formador_continua_ocupado(self):
        coord, formador = _pessoa("Coordenador"), _pessoa("Formador")
        _evento_aprovado(criador=coord, coordenador=coord, formadores=[formador], acompanha=False)
        assert not _ok(formador)

    def test_responsavel_que_acompanha_fica_ocupado(self):
        coord, formador = _pessoa("Coordenador"), _pessoa("Formador")
        _evento_aprovado(criador=coord, coordenador=coord, formadores=[formador], acompanha=True)
        assert not _ok(coord)

    def test_ocupa_o_responsavel_e_nao_quem_criou(self):
        criador, responsavel, formador = _pessoa("Apoio de Coordenação"), _pessoa("Coordenador"), _pessoa("Formador")
        _evento_aprovado(criador=criador, coordenador=responsavel, formadores=[formador], acompanha=True)
        assert not _ok(responsavel)
        assert _ok(criador), "quem criou não é o responsável: não ocupa"

    def test_sem_responsavel_cai_para_quem_criou(self):
        """Evento antigo com a marca e sem FK: o responsável é quem criou (mesma queda da tela)."""
        criador, formador = _pessoa("Coordenador"), _pessoa("Formador")
        _evento_aprovado(criador=criador, coordenador=None, formadores=[formador], acompanha=True)
        assert not _ok(criador)

    def test_coord_acompanha_antigo_nao_ocupa(self):
        """Linha COORD_ACOMPANHA (lista que saiu da tela): convite do Google, sem ocupar."""
        coord, formador, outro = _pessoa("Coordenador"), _pessoa("Formador"), _pessoa("Coordenador")
        sol = _evento_aprovado(criador=coord, coordenador=coord, formadores=[formador], acompanha=False)
        Participation.objects.create(solicitacao=sol, usuario=outro, role=Participation.Role.COORD_ACOMPANHA)
        assert _ok(outro)

    def test_deslocamento_so_confere_responsavel_que_acompanha(self):
        coord, formador = _pessoa("Coordenador"), _pessoa("Formador")
        outra_cidade = MunicipioFactory(nome="Cidade Ficticia RD04", uf="CE")
        _evento_aprovado(
            criador=coord,
            coordenador=coord,
            formadores=[formador],
            acompanha=False,
            inicio=_DIA.replace(hour=7),
            fim=_DIA.replace(hour=8, minute=30),
        )
        r = check_conflicts_uncached(usuario=coord, inicio=_INICIO, fim=_FIM, municipio=outra_cidade)
        assert r.ok, r.conflicts


def test_salvar_evento_renova_o_cache_do_responsavel_que_nao_criou():
    """O responsável pode não ser quem criou: o sinal de Solicitacao renova o cache dele também."""
    criador, responsavel = _pessoa("Apoio de Coordenação"), _pessoa("Coordenador")
    assert check_conflicts(usuario=responsavel, inicio=_INICIO, fim=_FIM).ok  # guarda no cache
    _evento_aprovado(criador=criador, coordenador=responsavel, acompanha=True)
    assert not check_conflicts(usuario=responsavel, inicio=_INICIO, fim=_FIM).ok


class TestQuemEConferidoNoEvento:
    """`solicitacao_availability.collect_participants`: quem o evento novo confere."""

    def test_nao_acompanha_confere_so_formadores(self):
        coord, formador = _pessoa("Coordenador"), _pessoa("Formador")
        sol = _evento_aprovado(criador=coord, coordenador=coord, formadores=[formador], acompanha=False)
        usuarios, _ = collect_participants(sol)
        assert [u.id for u in usuarios] == [formador.id]

    def test_acompanha_confere_formadores_e_responsavel(self):
        criador, responsavel, formador = _pessoa("Apoio de Coordenação"), _pessoa("Coordenador"), _pessoa("Formador")
        sol = _evento_aprovado(criador=criador, coordenador=responsavel, formadores=[formador], acompanha=True)
        usuarios, _ = collect_participants(sol)
        assert sorted(u.id for u in usuarios) == sorted([responsavel.id, formador.id])

    def test_responsavel_que_tambem_e_formador_conta_uma_vez(self):
        coord = _pessoa("Coordenador")
        sol = _evento_aprovado(criador=coord, coordenador=coord, formadores=[coord], acompanha=True)
        usuarios, _ = collect_participants(sol)
        assert [u.id for u in usuarios] == [coord.id]

    def test_coordenador_na_lista_de_formadores_e_conferido_mesmo_sem_acompanhar(self):
        coord, outra_coord = _pessoa("Coordenador"), _pessoa("Coordenador")
        sol = _evento_aprovado(criador=coord, coordenador=coord, formadores=[outra_coord], acompanha=False)
        usuarios, _ = collect_participants(sol)
        assert [u.id for u in usuarios] == [outra_coord.id]


# ---------------------------------------------------------------- API: criar, editar, aprovar


@pytest.fixture
def cenario():
    municipio = MunicipioFactory(nome="Municipio Ficticio Agenda", uf="CE")
    projeto = ProjetoFactory(nome="Projeto Ficticio Agenda", codigo="PFAG", fluxo="NAO_SUPER", ativo=True)
    projeto_super = ProjetoFactory(nome="Projeto Ficticio Agenda Super", codigo="PFAGS", fluxo="SUPER", ativo=True)
    for p in (projeto, projeto_super):
        Compra.objects.create(
            codigo=f"C-AG-{p.codigo}",
            projeto=p,
            municipio=municipio,
            quantidade=1,
            data=date(2026, 3, 1),
            uso="teste",
            external_hash=f"{next(_HASH):064d}",
        )
    return {
        "municipio": municipio,
        "projeto": projeto,
        "projeto_super": projeto_super,
        "tipo": TipoEventoFactory(nome="Formacao Ficticia Agenda"),
        "coord": _pessoa("Coordenador"),
    }


def _client(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


def _criar(c, user, formador, *, acompanha, projeto=None, inicio=_INICIO, fim=_FIM):
    payload = {
        "municipio": c["municipio"].id,
        "projeto": (projeto or c["projeto"]).id,
        "tipo_evento": c["tipo"].id,
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
        "coordenador_acompanha": acompanha,
        "pretende_avaliar_formador": False,
        "extra_participants": {"formador_ids": [formador.id]},
    }
    return _client(user).post("/api/solicitacoes/", payload, format="json")


class TestCriarEditarAprovar:
    def test_coordenador_cria_dois_eventos_no_mesmo_horario_sem_acompanhar(self, cenario):
        coord = cenario["coord"]
        r1 = _criar(cenario, coord, _pessoa("Formador"), acompanha=False)
        r2 = _criar(cenario, coord, _pessoa("Formador"), acompanha=False)
        assert r1.status_code == 201, r1.data
        assert r2.status_code == 201, r2.data

    def test_acompanha_com_conflito_recusa_com_motivo(self, cenario):
        coord = cenario["coord"]
        assert _criar(cenario, coord, _pessoa("Formador"), acompanha=True).status_code == 201
        r = _criar(cenario, coord, _pessoa("Formador"), acompanha=True)
        assert r.status_code == 400, r.data
        assert r.data["code"] == "availability_conflict"
        assert [p["usuario_id"] for p in r.data["errors"]["blocked_participants"]] == [coord.id]
        assert "tem outro evento aprovado neste horário" in r.data["detail"]

    def test_acompanha_com_bloqueio_total_recusa(self, cenario):
        coord = cenario["coord"]
        AvailabilityBlock.objects.create(
            usuario=coord,
            inicio=_DIA.replace(hour=0),
            fim=_DIA.replace(hour=23),
            tipo="T",
            status=AvailabilityBlock.Status.APROVADO,
        )
        assert _criar(cenario, coord, _pessoa("Formador"), acompanha=False).status_code == 201
        r = _criar(cenario, coord, _pessoa("Formador"), acompanha=True)
        assert r.status_code == 400, r.data
        assert "tem bloqueio de agenda no período" in r.data["detail"]

    def test_editar_de_nao_para_sim_com_conflito_recusa_e_nao_grava(self, cenario):
        coord = cenario["coord"]
        assert _criar(cenario, coord, _pessoa("Formador"), acompanha=True).status_code == 201
        r = _criar(cenario, coord, _pessoa("Formador"), acompanha=False)
        assert r.status_code == 201, r.data
        sol_id = r.data["id"]

        resp = _client(coord).patch(f"/api/solicitacoes/{sol_id}/", {"coordenador_acompanha": True}, format="json")
        assert resp.status_code == 400, resp.data
        assert resp.data["code"] == "availability_conflict"
        assert "Não é possível salvar a alteração" in resp.data["detail"]
        assert Solicitacao.objects.get(pk=sol_id).coordenador_acompanha is False

    def test_editar_de_sim_para_nao_libera(self, cenario):
        coord = cenario["coord"]
        r = _criar(cenario, coord, _pessoa("Formador"), acompanha=True)
        sol_id = r.data["id"]
        resp = _client(coord).patch(f"/api/solicitacoes/{sol_id}/", {"coordenador_acompanha": False}, format="json")
        assert resp.status_code == 200, resp.data
        assert _criar(cenario, coord, _pessoa("Formador"), acompanha=True).status_code == 201

    def test_aprovar_segundo_evento_do_coordenador_que_nao_acompanha(self, cenario):
        coord = cenario["coord"]
        aprovadora = UsuarioFactory(superuser=True, username="aprov_agenda", email="aprov_agenda@example.invalid")
        r1 = _criar(cenario, coord, _pessoa("Formador"), acompanha=False, projeto=cenario["projeto_super"])
        r2 = _criar(cenario, coord, _pessoa("Formador"), acompanha=False, projeto=cenario["projeto_super"])
        assert r1.status_code == r2.status_code == 201
        for sol_id in (r1.data["id"], r2.data["id"]):
            resp = _client(aprovadora).patch(f"/api/solicitacoes/{sol_id}/approve/", {}, format="json")
            assert resp.status_code == 200, resp.data

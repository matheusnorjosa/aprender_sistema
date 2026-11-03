"""
Vários coordenadores no mesmo evento (decisão do dono, 03/11/2026).

A caixa "Coordenador(es)" de cada horário aceita mais de um. O 1º é o responsável (FK
`Solicitacao.coordenador`, com a pergunta "vai acompanhar?" e a regra de hoje). Os demais chegam em
`extra_participants.coord_acompanha_ids` e viram `Participation(role=COORD_ACOMPANHA)`:

- cada um precisa do papel COORDENADOR vigente na gerência do projeto (como o responsável; quem cria
  com alcance global tem a mesma exceção); não repete o responsável nem se repete;
- SEMPRE ocupam a agenda e contam horas, como formador: conferidos em RD-01..RD-04 (criar, lote,
  editar, aprovar, prévia), ocupando nos eventos aprovados, na contagem de horas e na Grade
  (aba Coordenadores); recebem o convite do Google;
- na edição a lista é reconciliada; na SUPER aprovada, mudar a lista volta para aprovação.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

import itertools
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, EquipeGerencia, Participation, Solicitacao
from apps.core.services.availability_service import check_conflicts_uncached
from apps.core.services.config_service import bust_cfg
from apps.core.services.gcal.payload import build_attendees_for_solicitacao, build_event_payload
from apps.core.services.horas_formacao import horas_formacao
from apps.core.services.monthly_grid_service import build_monthly_grid
from apps.core.services.solicitacao_approval import EDITED_BY_APPROVER_CODE, mensagem_impedida
from apps.core.services.solicitacao_availability import collect_participants
from apps.core.tests.conftest import get_field_errors
from apps.core.tests.factories import (
    GerenciaFactory,
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
    com_pacote_do_dat,
    com_papel,
    liberar_par,
)

pytestmark = pytest.mark.django_db

_TZ = ZoneInfo("America/Fortaleza")
_DIA = date(2031, 5, 12)
_N = itertools.count(1)


def _hora(h: int, dia: date = _DIA) -> datetime:
    return datetime(dia.year, dia.month, dia.day, h, tzinfo=_TZ)


def _pessoa(papel: str, gerencia, nome: str):
    n = next(_N)
    u = UsuarioFactory(
        username=f"varios_coord_{n}",
        email=f"varios_coord_{n}@example.invalid",
        first_name=nome,
        last_name="Ficticia",
    )
    com_papel(u, papel, gerencia)
    return u


@pytest.fixture(autouse=True)
def _parametros(settings):
    settings.AVAILABILITY_DAILY_LIMIT_HOURS = 8
    bust_cfg("availability")


@pytest.fixture
def c():
    gerencia = GerenciaFactory(pergunta_avaliar_formador=False)
    outra = GerenciaFactory(pergunta_avaliar_formador=False)
    municipio = MunicipioFactory(nome="Municipio Varios Coord", uf="CE")
    nao_super = ProjetoFactory(nome="Projeto Varios Coord", gerencia=gerencia)
    super_ = ProjetoFactory(nome="Projeto SUPER Varios Coord", fluxo="SUPER", gerencia=gerencia)
    for projeto in (nao_super, super_):
        liberar_par(municipio, projeto)
    return {
        "municipio": municipio,
        "tipo": TipoEventoFactory(nome="Formacao Varios Coord"),
        "projeto": nao_super,
        "super": super_,
        "coord": _pessoa("COORDENADOR", gerencia, "Ana"),
        "c2": _pessoa("COORDENADOR", gerencia, "Bia"),
        "c3": _pessoa("COORDENADOR", gerencia, "Caio"),
        "formador": _pessoa("FORMADOR", gerencia, "Davi"),
        "coord_fora": _pessoa("COORDENADOR", outra, "Edu"),
    }


def _client(user):
    cl = APIClient()
    cl.force_authenticate(user)
    return cl


def _payload(c, *, extras=(), projeto=None, inicio=None, fim=None, **campos: Any) -> dict[str, Any]:
    p: dict[str, Any] = {
        "municipio": c["municipio"].id,
        "projeto": (projeto or c["projeto"]).id,
        "tipo_evento": c["tipo"].id,
        "inicio": (inicio or _hora(9)).isoformat(),
        "fim": (fim or _hora(11)).isoformat(),
        "coordenador_acompanha": False,
        "extra_participants": {
            "formador_ids": [c["formador"].id],
            "coord_acompanha_ids": [u.id for u in extras],
        },
    }
    p.update(campos)
    return p


def _post(user, payload):
    return _client(user).post("/api/solicitacoes/", payload, format="json")


def _extras(sol_id) -> set[int]:
    return set(
        Participation.objects.filter(solicitacao_id=sol_id, role="COORD_ACOMPANHA").values_list("usuario_id", flat=True)
    )


def _evento_aprovado(*, criador, extras=(), formadores=(), inicio=None, fim=None, projeto=None):
    sol = SolicitacaoFactory(
        usuario=criador,
        coordenador=criador,
        coordenador_acompanha=False,
        status=Solicitacao.Status.APROVADO,
        projeto=projeto or ProjetoFactory(),
        inicio=inicio or _hora(9),
        fim=fim or _hora(11),
    )
    Participation.objects.create(solicitacao=sol, usuario=criador, role="COORDENADOR")
    for f in formadores:
        Participation.objects.create(solicitacao=sol, usuario=f, role="FORMADOR")
    for e in extras:
        Participation.objects.create(solicitacao=sol, usuario=e, role="COORD_ACOMPANHA")
    return sol


# ---------------------------------------------------------------- criação e validação


class TestCriacao:
    def test_grava_os_coordenadores_alem_do_responsavel(self, c):
        r = _post(c["coord"], _payload(c, extras=[c["c2"], c["c3"]]))
        assert r.status_code == 201, r.data
        sol = Solicitacao.objects.get(pk=r.data["id"])
        assert sol.coordenador_id == c["coord"].id
        assert _extras(sol.pk) == {c["c2"].id, c["c3"].id}

    def test_sem_a_lista_continua_como_hoje(self, c):
        payload = _payload(c)
        del payload["extra_participants"]["coord_acompanha_ids"]
        r = _post(c["coord"], payload)
        assert r.status_code == 201, r.data
        assert _extras(r.data["id"]) == set()

    def test_de_outra_gerencia_recusa_no_campo(self, c):
        r = _post(c["coord"], _payload(c, extras=[c["coord_fora"]]))
        assert r.status_code == 400, r.data
        assert "coord_acompanha_ids" in get_field_errors(r)
        assert not Solicitacao.objects.exists()

    def test_sem_papel_coordenador_recusa_no_campo(self, c):
        r = _post(c["coord"], _payload(c, extras=[c["formador"]]))
        assert r.status_code == 400, r.data
        assert "coord_acompanha_ids" in get_field_errors(r)

    def test_id_que_nao_existe_recusa_no_campo(self, c):
        payload = _payload(c)
        payload["extra_participants"]["coord_acompanha_ids"] = [987654]
        r = _post(c["coord"], payload)
        assert r.status_code == 400, r.data
        assert "coord_acompanha_ids" in get_field_errors(r)

    def test_nao_repete_o_responsavel(self, c):
        # Sem `coordenador`, a responsável é quem cria (coordenadora da gerência).
        r = _post(c["coord"], _payload(c, extras=[c["coord"]]))
        assert r.status_code == 400, r.data
        assert get_field_errors(r)["coord_acompanha_ids"] == [
            "O coordenador responsável já está no evento; não o repita entre os demais."
        ]
        assert not Solicitacao.objects.exists()

    def test_mesma_pessoa_formador_e_coordenador_extra_e_aceita(self, c):
        """Decisão do dono (03/11/2026, revisão): pode estar nos dois papéis; conta uma vez por evento."""
        payload = _payload(c, extras=[c["c2"]])
        payload["extra_participants"]["formador_ids"] = [c["formador"].id, c["c2"].id]
        r = _post(c["coord"], payload)
        assert r.status_code == 201, r.data
        assert _extras(r.data["id"]) == {c["c2"].id}
        assert Participation.objects.filter(solicitacao_id=r.data["id"], usuario=c["c2"], role="FORMADOR").exists()

    def test_nao_repete_o_responsavel_escolhido(self, c):
        r = _post(c["coord"], _payload(c, extras=[c["c2"]], coordenador=c["c2"].id))
        assert r.status_code == 400, r.data
        assert "coord_acompanha_ids" in get_field_errors(r)

    def test_nao_repete_entre_si(self, c):
        r = _post(c["coord"], _payload(c, extras=[c["c2"], c["c2"]]))
        assert r.status_code == 400, r.data
        assert "coord_acompanha_ids" in get_field_errors(r)

    def test_por_email_continua_recusado(self, c):
        payload = _payload(c)
        payload["extra_participants"]["coord_acompanha_emails"] = [c["c2"].email]
        r = _post(c["coord"], payload)
        assert r.status_code == 400, r.data
        assert "coord_acompanha_emails" in get_field_errors(r)

    def test_quem_cria_com_alcance_global_aceita_coordenador_de_outra_gerencia(self, c):
        admin = UsuarioFactory(superuser=True, first_name="Super", last_name="Ficticio")
        r = _post(admin, _payload(c, extras=[c["coord_fora"]], coordenador=c["c2"].id))
        assert r.status_code == 201, r.data
        assert _extras(r.data["id"]) == {c["coord_fora"].id}

    @pytest.mark.parametrize("quem", ["formador", "sem_papel"])
    def test_quem_cria_com_alcance_global_nao_poe_quem_nao_coordena_em_lugar_nenhum(self, c, quem):
        """Revisão de 03/11/2026: o isento escapa da gerência do projeto, não do papel COORDENADOR."""
        admin = UsuarioFactory(superuser=True, first_name="Super", last_name="Ficticio")
        pessoa = c["formador"] if quem == "formador" else UsuarioFactory(first_name="Sem", last_name="Papel")
        r = _post(admin, _payload(c, extras=[pessoa], coordenador=c["c2"].id))
        assert r.status_code == 400, r.data
        assert get_field_errors(r)["coord_acompanha_ids"] == [
            "Cada coordenador precisa ser coordenador da gerência do projeto."
        ]
        assert not Solicitacao.objects.exists()

    def test_quem_cria_com_alcance_global_nao_conta_papel_em_gerencia_inativa(self, c):
        inativa = GerenciaFactory(ativo=False)
        so_na_inativa = _pessoa("COORDENADOR", inativa, "Gil")
        admin = UsuarioFactory(superuser=True)
        r = _post(admin, _payload(c, extras=[so_na_inativa], coordenador=c["c2"].id))
        assert r.status_code == 400, r.data
        assert "coord_acompanha_ids" in get_field_errors(r)

    def test_dat_nao_poe_formador_puro_como_coordenador_extra(self, c):
        dat = UsuarioFactory(first_name="Dat", last_name="Ficticio")
        com_pacote_do_dat(dat)
        r = _post(dat, _payload(c, extras=[c["formador"]], coordenador=c["c2"].id))
        assert r.status_code == 400, r.data
        assert "coord_acompanha_ids" in get_field_errors(r)


class TestLote:
    def test_lote_grava_os_coordenadores_de_cada_evento(self, c):
        eventos = [
            _payload(c, extras=[c["c2"]]),
            _payload(c, extras=[c["c3"]], inicio=_hora(14), fim=_hora(16)),
        ]
        r = _client(c["coord"]).post("/api/solicitacoes/lote/", {"eventos": eventos}, format="json")
        assert r.status_code == 201, r.data
        ids = [e["id"] for e in r.data["eventos"]]
        assert [_extras(i) for i in ids] == [{c["c2"].id}, {c["c3"].id}]

    def test_lote_recusa_o_mesmo_coordenador_extra_em_dois_eventos_no_mesmo_horario(self, c):
        eventos = [_payload(c, extras=[c["c2"]]), _payload(c, extras=[c["c2"]])]
        # Formadores diferentes: o choque é só do coordenador extra.
        outro = _pessoa("FORMADOR", c["projeto"].gerencia, "Fabi")
        eventos[1]["extra_participants"]["formador_ids"] = [outro.id]
        r = _client(c["coord"]).post("/api/solicitacoes/lote/", {"eventos": eventos}, format="json")
        assert r.status_code == 400, r.data
        assert "Bia Ficticia" in str(r.data)
        assert not Solicitacao.objects.exists()

    def test_lote_aceita_formador_que_tambem_e_coordenador_extra(self, c):
        evento = _payload(c, extras=[c["c2"]])
        evento["extra_participants"]["formador_ids"] = [c["c2"].id]
        r = _client(c["coord"]).post("/api/solicitacoes/lote/", {"eventos": [evento]}, format="json")
        assert r.status_code == 201, r.data

    def test_lote_recusa_fora_da_gerencia_no_campo_do_evento(self, c):
        r = _client(c["coord"]).post(
            "/api/solicitacoes/lote/", {"eventos": [_payload(c, extras=[c["coord_fora"]])]}, format="json"
        )
        assert r.status_code == 400, r.data
        assert "coord_acompanha_ids" in str(r.data)


# ---------------------------------------------------------------- agenda (RD-01..RD-04)


class TestAgenda:
    def test_evento_aprovado_ocupa_a_agenda_do_coordenador_extra(self, c):
        _evento_aprovado(criador=c["coord"], extras=[c["c2"]], formadores=[c["formador"]])
        assert not check_conflicts_uncached(usuario=c["c2"], inicio=_hora(9), fim=_hora(11)).ok

    def test_collect_participants_inclui_o_coordenador_extra(self, c):
        sol = SolicitacaoFactory(
            usuario=c["coord"], coordenador=c["coord"], coordenador_acompanha=False, inicio=_hora(9), fim=_hora(11)
        )
        Participation.objects.create(solicitacao=sol, usuario=c["c2"], role="COORD_ACOMPANHA")
        usuarios, _ = collect_participants(sol)
        assert c["c2"] in usuarios
        assert c["coord"] not in usuarios, "o responsável que não acompanha segue de fora"

    def test_choque_do_coordenador_extra_barra_a_criacao_com_o_nome(self, c):
        _evento_aprovado(criador=c["c3"], formadores=[c["c2"]])
        r = _post(c["coord"], _payload(c, extras=[c["c2"]]))
        assert r.status_code == 400, r.data
        assert r.data["code"] == "availability_conflict"
        assert "Bia Ficticia" in r.data["detail"]
        assert not Solicitacao.objects.filter(usuario=c["coord"]).exists()

    def test_choque_entre_dois_eventos_com_o_mesmo_coordenador_extra(self, c):
        _evento_aprovado(criador=c["c3"], extras=[c["c2"]])
        r = _post(c["coord"], _payload(c, extras=[c["c2"]]))
        assert r.status_code == 400, r.data
        assert r.data["code"] == "availability_conflict"

    def test_aprovar_confere_o_coordenador_extra(self, c):
        r = _post(c["coord"], _payload(c, extras=[c["c2"]], projeto=c["super"]))
        assert r.status_code == 201, r.data
        assert r.data["status"] == "pendente"
        _evento_aprovado(criador=c["c3"], formadores=[c["c2"]])

        admin = UsuarioFactory(superuser=True)
        resp = _client(admin).patch(f"/api/solicitacoes/{r.data['id']}/approve/", {}, format="json")
        assert resp.status_code == 400, resp.data
        assert resp.data["code"] == "availability_conflict"
        assert "Bia Ficticia" in resp.data["detail"]

    def test_editar_para_horario_ocupado_do_coordenador_extra_barra(self, c):
        r = _post(c["coord"], _payload(c, extras=[c["c2"]], inicio=_hora(14), fim=_hora(16)))
        assert r.status_code == 201, r.data
        _evento_aprovado(criador=c["c3"], formadores=[c["c2"]])
        resp = _client(c["coord"]).patch(
            f"/api/solicitacoes/{r.data['id']}/",
            {"inicio": _hora(9).isoformat(), "fim": _hora(11).isoformat()},
            format="json",
        )
        assert resp.status_code == 400, resp.data
        assert resp.data["code"] == "availability_conflict"

    def test_previa_check_many_mostra_o_evento_do_coordenador_extra(self, c):
        _evento_aprovado(criador=c["c3"], extras=[c["c2"]])
        resp = _client(c["coord"]).post(
            "/api/availability/check-many/",
            {"usuarios_ids": [c["c2"].id], "inicio": _hora(9).isoformat(), "fim": _hora(11).isoformat()},
            format="json",
        )
        assert resp.status_code == 200, resp.data
        assert resp.data["results"][0]["ok"] is False


# ---------------------------------------------------------------- horas, Grade e convite


class TestHorasGradeConvite:
    def test_horas_de_formacao_contam_o_coordenador_extra(self, c):
        _evento_aprovado(criador=c["coord"], extras=[c["c2"]], inicio=_hora(8), fim=_hora(12))
        assert horas_formacao([c["c2"].id], de=_DIA, ate=_DIA)[c["c2"].id].total == 4.0

    def test_grade_mostra_o_coordenador_extra_na_aba_coordenadores(self, c):
        _evento_aprovado(criador=c["coord"], extras=[c["c2"]], inicio=_hora(8), fim=_hora(12), projeto=c["super"])
        grade = build_monthly_grid(year=_DIA.year, month=_DIA.month, role="COORDENADOR")
        linha = {p["id"]: i for i, p in enumerate(grade["people"])}
        assert c["c2"].id in linha
        assert grade["people"][linha[c["c2"].id]]["ch_month"] == 4.0
        assert grade["cells"][linha[c["c2"].id]][_DIA.day - 1] == "E"

    def test_grade_conta_uma_vez_quem_ficou_com_os_dois_papeis(self, c):
        """Dado antigo/importado com a pessoa FORMADOR e COORD_ACOMPANHA no mesmo evento: um evento só."""
        _evento_aprovado(
            criador=c["coord"],
            extras=[c["c2"]],
            formadores=[c["c2"]],
            inicio=_hora(8),
            fim=_hora(12),
            projeto=c["super"],
        )
        grade = build_monthly_grid(year=_DIA.year, month=_DIA.month, role="COORDENADOR")
        linha = {p["id"]: i for i, p in enumerate(grade["people"])}
        assert grade["cells"][linha[c["c2"].id]][_DIA.day - 1] == "E"
        assert len(grade["details_index"][f"{linha[c['c2'].id]}:{_DIA.day - 1}"]) == 1

    def test_horas_contam_uma_vez_quem_e_formador_e_coordenador_extra(self, c):
        _evento_aprovado(criador=c["coord"], extras=[c["c2"]], formadores=[c["c2"]], inicio=_hora(8), fim=_hora(12))
        assert horas_formacao([c["c2"].id], de=_DIA, ate=_DIA)[c["c2"].id].total == 4.0

    def test_agenda_e_convite_tratam_uma_vez_quem_e_formador_e_coordenador_extra(self, c):
        payload = _payload(c, extras=[c["c2"]])
        payload["extra_participants"]["formador_ids"] = [c["c2"].id]
        r = _post(c["coord"], payload)
        assert r.status_code == 201, r.data
        sol = Solicitacao.objects.get(pk=r.data["id"])
        usuarios, _ = collect_participants(sol)
        assert [u.id for u in usuarios].count(c["c2"].id) == 1
        emails = [a["email"] for a in build_attendees_for_solicitacao(sol)]
        assert emails.count(c["c2"].email) == 1

    def test_choque_de_quem_e_formador_e_coordenador_extra_aparece_uma_vez(self, c):
        _evento_aprovado(criador=c["c3"], formadores=[c["c2"]])
        payload = _payload(c, extras=[c["c2"]])
        payload["extra_participants"]["formador_ids"] = [c["c2"].id]
        r = _post(c["coord"], payload)
        assert r.status_code == 400, r.data
        assert [p["usuario_id"] for p in r.data["errors"]["blocked_participants"]] == [c["c2"].id]

    def test_aba_formadores_marca_o_dia_em_que_a_pessoa_e_coordenadora_extra(self, c):
        """Formadora que é coordenadora extra de outro evento: o dia fica ocupado e a CH bate."""
        _evento_aprovado(criador=c["coord"], formadores=[c["c2"]], inicio=_hora(8), fim=_hora(10), projeto=c["super"])
        outro_dia = date(_DIA.year, _DIA.month, _DIA.day + 1)
        _evento_aprovado(
            criador=c["coord"],
            extras=[c["c2"]],
            inicio=_hora(8, outro_dia),
            fim=_hora(12, outro_dia),
            projeto=c["super"],
        )
        grade = build_monthly_grid(year=_DIA.year, month=_DIA.month, role="FORMADOR")
        linha = {p["id"]: i for i, p in enumerate(grade["people"])}
        assert grade["cells"][linha[c["c2"].id]][outro_dia.day - 1] == "E"
        assert grade["people"][linha[c["c2"].id]]["ch_month"] == 6.0

    def test_aba_formadores_marca_o_dia_em_que_a_pessoa_e_responsavel_que_acompanha(self, c):
        _evento_aprovado(criador=c["coord"], formadores=[c["c2"]], inicio=_hora(8), fim=_hora(10), projeto=c["super"])
        outro_dia = date(_DIA.year, _DIA.month, _DIA.day + 1)
        SolicitacaoFactory(
            usuario=c["coord"],
            coordenador=c["c2"],
            coordenador_acompanha=True,
            status=Solicitacao.Status.APROVADO,
            projeto=c["super"],
            inicio=_hora(8, outro_dia),
            fim=_hora(12, outro_dia),
        )
        grade = build_monthly_grid(year=_DIA.year, month=_DIA.month, role="FORMADOR")
        linha = {p["id"]: i for i, p in enumerate(grade["people"])}
        assert grade["cells"][linha[c["c2"].id]][outro_dia.day - 1] == "E"
        assert grade["people"][linha[c["c2"].id]]["ch_month"] == 6.0

    def test_grade_por_gerencia_mostra_o_coordenador_extra(self, c):
        _evento_aprovado(criador=c["coord"], extras=[c["c2"]], inicio=_hora(8), fim=_hora(12))
        grade = build_monthly_grid(
            year=_DIA.year, month=_DIA.month, role="COORDENADOR", gerencia_id=c["projeto"].gerencia_id
        )
        linha = {p["id"]: i for i, p in enumerate(grade["people"])}
        assert grade["cells"][linha[c["c2"].id]][_DIA.day - 1] == "E"

    def test_convite_e_descricao_incluem_o_coordenador_extra(self, c):
        r = _post(c["coord"], _payload(c, extras=[c["c2"], c["c3"]]))
        assert r.status_code == 201, r.data
        sol = Solicitacao.objects.get(pk=r.data["id"])
        emails = {a["email"] for a in build_attendees_for_solicitacao(sol)}
        assert {c["c2"].email, c["c3"].email} <= emails
        descricao = build_event_payload(sol)["description"]
        assert "Coordenador(es): Ana Ficticia, Bia Ficticia, Caio Ficticia" in descricao

    def test_descricao_com_um_so_coordenador_continua_igual(self, c):
        r = _post(c["coord"], _payload(c))
        sol = Solicitacao.objects.get(pk=r.data["id"])
        assert "Coordenador(a): Ana Ficticia" in build_event_payload(sol)["description"]


# ---------------------------------------------------------------- edição


class TestEdicao:
    def _criar(self, c, extras, projeto=None):
        r = _post(c["coord"], _payload(c, extras=extras, projeto=projeto))
        assert r.status_code == 201, r.data
        return r.data["id"]

    def _patch(self, c, sol_id, ids, user=None):
        return _client(user or c["coord"]).patch(
            f"/api/solicitacoes/{sol_id}/", {"extra_participants": {"coord_acompanha_ids": ids}}, format="json"
        )

    def test_reconcilia_a_lista(self, c):
        sol_id = self._criar(c, [c["c2"]])
        resp = self._patch(c, sol_id, [c["c3"].id])
        assert resp.status_code == 200, resp.data
        assert _extras(sol_id) == {c["c3"].id}

    def test_lista_vazia_tira_os_coordenadores_extras(self, c):
        sol_id = self._criar(c, [c["c2"]])
        resp = self._patch(c, sol_id, [])
        assert resp.status_code == 200, resp.data
        assert _extras(sol_id) == set()

    def test_campo_ausente_nao_mexe(self, c):
        sol_id = self._criar(c, [c["c2"]])
        resp = _client(c["coord"]).patch(
            f"/api/solicitacoes/{sol_id}/", {"extra_participants": {"formador_ids": [c["formador"].id]}}, format="json"
        )
        assert resp.status_code == 200, resp.data
        assert _extras(sol_id) == {c["c2"].id}

    def test_adicionar_de_outra_gerencia_recusa_no_campo(self, c):
        sol_id = self._criar(c, [c["c2"]])
        resp = self._patch(c, sol_id, [c["c2"].id, c["coord_fora"].id])
        assert resp.status_code == 400, resp.data
        assert "coord_acompanha_ids" in get_field_errors(resp)
        assert _extras(sol_id) == {c["c2"].id}

    def test_nao_repete_o_responsavel_na_edicao(self, c):
        sol_id = self._criar(c, [c["c2"]])
        resp = self._patch(c, sol_id, [c["coord"].id])
        assert resp.status_code == 400, resp.data
        assert "coord_acompanha_ids" in get_field_errors(resp)

    def test_trocar_o_responsavel_por_um_coordenador_extra_recusa(self, c):
        sol_id = self._criar(c, [c["c2"]])
        resp = _client(c["coord"]).patch(f"/api/solicitacoes/{sol_id}/", {"coordenador": c["c2"].id}, format="json")
        assert resp.status_code == 400, resp.data
        assert "coord_acompanha_ids" in get_field_errors(resp)

    def test_super_aprovada_volta_para_aprovacao_ao_mudar_a_lista(self, c):
        sol_id = self._criar(c, [c["c2"]], projeto=c["super"])
        Solicitacao.objects.filter(pk=sol_id).update(status="aprovado")
        resp = self._patch(c, sol_id, [c["c2"].id, c["c3"].id])
        assert resp.status_code == 200, resp.data
        assert Solicitacao.objects.get(pk=sol_id).status == "pendente"
        log = AuditLog.objects.filter(action="UPDATE", details__solicitacao_id=sol_id).latest("created_at")
        assert "coordenadores" in log.details["reaprovacao"]["campos"]

    def test_coordenador_extra_que_ja_e_formador_entra_na_edicao(self, c):
        r = _post(c["coord"], {**_payload(c), "extra_participants": {"formador_ids": [c["formador"].id, c["c3"].id]}})
        assert r.status_code == 201, r.data
        resp = self._patch(c, r.data["id"], [c["c3"].id])
        assert resp.status_code == 200, resp.data
        assert _extras(r.data["id"]) == {c["c3"].id}

    def _mover_para_outra_gerencia(self, c, *, extra_coordena_na_nova: bool):
        nova = GerenciaFactory(pergunta_avaliar_formador=False)
        projeto_novo = ProjetoFactory(nome="Projeto Outra Gerencia", gerencia=nova)
        liberar_par(c["municipio"], projeto_novo)
        com_papel(c["coord"], "COORDENADOR", nova)
        com_papel(c["formador"], "FORMADOR", nova)
        com_papel(c["c2"], "COORDENADOR" if extra_coordena_na_nova else "FORMADOR", nova)
        sol_id = self._criar(c, [c["c2"]])
        resp = _client(c["coord"]).patch(f"/api/solicitacoes/{sol_id}/", {"projeto": projeto_novo.id}, format="json")
        return sol_id, resp

    def test_mover_de_gerencia_exige_coordenador_extra_coordenador_na_nova(self, c):
        sol_id, resp = self._mover_para_outra_gerencia(c, extra_coordena_na_nova=False)
        assert resp.status_code == 400, resp.data
        assert get_field_errors(resp)["coord_acompanha_ids"] == [
            "Cada coordenador precisa ser coordenador da gerência do projeto."
        ]
        assert Solicitacao.objects.get(pk=sol_id).projeto_id == c["projeto"].id

    def test_mover_de_gerencia_com_coordenador_extra_coordenador_na_nova_passa(self, c):
        _sol_id, resp = self._mover_para_outra_gerencia(c, extra_coordena_na_nova=True)
        assert resp.status_code == 200, resp.data

    def test_isento_move_de_gerencia_e_o_extra_continua_precisando_coordenar(self, c):
        sol_id = self._criar(c, [c["c2"]])
        EquipeGerencia.objects.filter(usuario=c["c2"], papel="COORDENADOR").update(papel="FORMADOR")
        nova = GerenciaFactory(pergunta_avaliar_formador=False)
        projeto_novo = ProjetoFactory(nome="Projeto Outra Gerencia Isento", gerencia=nova)
        liberar_par(c["municipio"], projeto_novo)
        admin = UsuarioFactory(superuser=True)
        resp = _client(admin).patch(f"/api/solicitacoes/{sol_id}/", {"projeto": projeto_novo.id}, format="json")
        assert resp.status_code == 400, resp.data
        assert "coord_acompanha_ids" in get_field_errors(resp)

    def test_evento_antigo_sem_responsavel_com_convidado_coord_acompanha_edita(self, c):
        """Sem `coordenador` gravado, o responsável é quem criou; a linha de convidado não é ele."""
        sol = SolicitacaoFactory(
            usuario=c["coord"],
            coordenador=None,
            coordenador_acompanha=False,
            projeto=c["projeto"],
            municipio=c["municipio"],
            inicio=_hora(14),
            fim=_hora(16),
        )
        Participation.objects.create(solicitacao=sol, guest_email="convidada@example.invalid", role="COORD_ACOMPANHA")
        resp = _client(c["coord"]).patch(f"/api/solicitacoes/{sol.id}/", {"observacoes": "x"}, format="json")
        assert resp.status_code == 200, resp.data

    def test_evento_antigo_sem_responsavel_nao_repete_quem_criou(self, c):
        sol = SolicitacaoFactory(
            usuario=c["coord"],
            coordenador=None,
            coordenador_acompanha=False,
            projeto=c["projeto"],
            municipio=c["municipio"],
            inicio=_hora(14),
            fim=_hora(16),
        )
        resp = self._patch(c, sol.id, [c["coord"].id])
        assert resp.status_code == 400, resp.data
        assert "coord_acompanha_ids" in get_field_errors(resp)

    def test_mensagem_de_quem_editou_cita_coordenadores(self):
        assert "coordenadores" in mensagem_impedida(EDITED_BY_APPROVER_CODE, "aprovar")

    def test_super_aprovada_com_a_mesma_lista_continua_aprovada(self, c):
        sol_id = self._criar(c, [c["c2"]], projeto=c["super"])
        Solicitacao.objects.filter(pk=sol_id).update(status="aprovado")
        resp = self._patch(c, sol_id, [c["c2"].id])
        assert resp.status_code == 200, resp.data
        assert Solicitacao.objects.get(pk=sol_id).status == "aprovado"

"""
Testes: o limite diário (RD-05, código M) avisa e não barra.

Decisão do dono em 02/10/2026: "o evento na agenda pode ter quantas horas quiser". O motor
continua calculando o M, mas devolve em `warnings`; `conflicts` (e portanto o 400
`availability_conflict`) fica só com o que barra: sobreposição (X), bloqueio (T, P) e
deslocamento (D).

`TestOQueBarraContinuaBarrando` é a guarda contra afrouxar demais: X, T, P e D seguem dando
400 em criar, editar, aprovar e no lote.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false, reportPrivateUsage=false

from __future__ import annotations

from datetime import date, datetime
from datetime import timezone as dt_timezone
from unittest.mock import patch

from rest_framework.test import APIClient

import pytest

from apps.core.models import AvailabilityBlock, Compra, Participation, Solicitacao
from apps.core.services import solicitacao_availability as guard_module
from apps.core.services.availability_service import check_conflicts_uncached
from apps.core.services.config_service import bust_cfg
from apps.core.tests.factories import (
    GroupFactory,
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db


def _utc(hora: int, minuto: int = 0, *, dia: int = 10) -> datetime:
    """Quarta-feira fixa (10/03/2027), em UTC. Fortaleza é UTC-3."""
    return datetime(2027, 3, dia, hora, minuto, tzinfo=dt_timezone.utc)


# A pendente em teste: 15h–17h em Fortaleza.
INICIO, FIM = _utc(18), _utc(20)
# Evento sozinho de 16 horas: 07:00–23:00 em Fortaleza.
DIA_INTEIRO_INICIO, DIA_INTEIRO_FIM = _utc(10), _utc(2, dia=11)


@pytest.fixture(autouse=True)
def _parametros(settings):
    settings.AVAILABILITY_DAILY_LIMIT_HOURS = 8
    settings.TRAVEL_BUFFER_MINUTES = 120
    # O cache de Config sobrevive ao rollback do teste: um valor deixado por outro arquivo
    # (ex.: Buffer 45 em test_config_api) valeria aqui no lugar do settings.
    bust_cfg("availability")


@pytest.fixture
def municipio():
    return MunicipioFactory(nome="Municipio Aviso", uf="CE")


@pytest.fixture
def tipo_evento():
    return TipoEventoFactory(nome="Formação Aviso")


@pytest.fixture
def projeto_super(municipio):
    projeto = ProjetoFactory(nome="Projeto SUPER Aviso", fluxo="SUPER")
    Compra.objects.create(
        codigo="COMP-AVISO",
        projeto=projeto,
        municipio=municipio,
        quantidade=10,
        data=date(2026, 1, 10),
        uso="Fixture aviso",
        external_hash="compra-aviso-hash",
    )
    return projeto


@pytest.fixture
def coordenador():
    user = UsuarioFactory(username="coord_aviso", first_name="Ana", last_name="Coordenadora")
    user.groups.add(GroupFactory(name="Coordenador"))
    return user


@pytest.fixture
def formador():
    return UsuarioFactory(username="formador_aviso", first_name="Bruno", last_name="Formador")


@pytest.fixture
def aprovador():
    user = UsuarioFactory(username="gerente_aviso", first_name="Carla", last_name="Gerente")
    user.groups.add(GroupFactory(name="Superintendência"), GroupFactory(name="Gerente"))
    return user


def _client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _evento(dono, municipio, tipo_evento, inicio, fim, *, status, projeto=None, formador=None):
    sol = SolicitacaoFactory(
        usuario=dono,
        municipio=municipio,
        tipo_evento=tipo_evento,
        projeto=projeto,
        inicio=inicio,
        fim=fim,
        status=status,
    )
    if formador is not None:
        Participation.objects.create(solicitacao=sol, usuario=formador, role=Participation.Role.FORMADOR)
    return sol


def _pendente(coordenador, formador, municipio, tipo_evento, projeto_super):
    return _evento(
        coordenador, municipio, tipo_evento, INICIO, FIM, status="pendente", projeto=projeto_super, formador=formador
    )


def _oito_horas_no_dia(formador, municipio, tipo_evento):
    """8h aprovadas no mesmo município, terminando antes da pendente: 8h + 2h passa de 8h, sem X nem D."""
    return _evento(formador, municipio, tipo_evento, _utc(9), _utc(17), status="aprovado", formador=formador)


def _ocupar_agenda(code, formador, municipio, tipo_evento):
    """Monta, na agenda do formador, exatamente UM motivo que barra a janela 18h–20h UTC."""
    if code == "X":
        _evento(formador, municipio, tipo_evento, INICIO, FIM, status="aprovado", formador=formador)
    elif code in ("T", "P"):
        AvailabilityBlock.objects.create(
            usuario=formador, inicio=_utc(18, 30), fim=_utc(19), tipo=code, status="aprovado", motivo="Bloqueio"
        )
    elif code == "D":
        outra_cidade = MunicipioFactory(nome="Outra Cidade Aviso", uf="CE")
        _evento(formador, outra_cidade, tipo_evento, _utc(16), _utc(17), status="aprovado", formador=formador)


def _payload_criar(municipio, tipo_evento, formador, inicio, fim, projeto=None):
    payload = {
        "municipio": municipio.pk,
        "tipo_evento": tipo_evento.pk,
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
        "extra_participants": {"formador_ids": [formador.pk]},
    }
    if projeto is not None:
        payload["projeto"] = projeto.pk
    return payload


# ============================================================================
# Motor: M sai de `conflicts` e vai para `warnings`
# ============================================================================


class TestMotorSeparaAvisoDeConflito:
    def test_evento_sozinho_das_7_as_23_passa_com_aviso(self, formador, municipio):
        result = check_conflicts_uncached(
            usuario=formador, inicio=DIA_INTEIRO_INICIO, fim=DIA_INTEIRO_FIM, municipio=municipio
        )

        assert result.ok
        assert result.conflicts == []
        assert [w.code for w in result.warnings] == ["M"]

    def test_aviso_fala_a_lingua_de_quem_usa_e_nao_promete_contagem(self, formador, municipio):
        result = check_conflicts_uncached(
            usuario=formador, inicio=DIA_INTEIRO_INICIO, fim=DIA_INTEIRO_FIM, municipio=municipio
        )

        (aviso,) = result.warnings
        texto = f"{aviso.title} {aviso.detail}"
        assert "8 horas" in aviso.title
        assert "10/03" in aviso.detail
        assert "não impede" in aviso.detail
        # A contagem de horas com teto ainda não existe: o aviso não pode prometê-la.
        assert "contagem" not in texto.lower()
        assert "min" not in texto  # sem o texto técnico antigo ("960 min > limite 480 min")

    def test_agenda_dentro_do_limite_nao_tem_aviso(self, formador, municipio):
        result = check_conflicts_uncached(usuario=formador, inicio=INICIO, fim=FIM, municipio=municipio)

        assert result.ok
        assert result.warnings == []

    def test_sobreposicao_e_limite_juntos_barra_so_pela_sobreposicao(self, formador, municipio, tipo_evento):
        _oito_horas_no_dia(formador, municipio, tipo_evento)
        _ocupar_agenda("X", formador, municipio, tipo_evento)

        result = check_conflicts_uncached(usuario=formador, inicio=INICIO, fim=FIM, municipio=municipio)

        assert not result.ok
        assert [c.code for c in result.conflicts] == ["X"]
        assert [w.code for w in result.warnings] == ["M"]


# ============================================================================
# Criar, editar, aprovar e lote: o limite diário não barra mais
# ============================================================================


class TestLimiteDiarioNaoBarra:
    def test_criar_evento_de_10_horas_devolve_201(self, coordenador, formador, municipio, tipo_evento):
        response = _client(coordenador).post(
            "/api/solicitacoes/",
            _payload_criar(municipio, tipo_evento, formador, _utc(10), _utc(20)),
            format="json",
        )

        assert response.status_code == 201, response.data

    def test_evento_das_7_as_23_e_criado_e_aprovado_com_aviso(
        self, coordenador, formador, aprovador, municipio, tipo_evento, projeto_super
    ):
        criado = _client(coordenador).post(
            "/api/solicitacoes/",
            _payload_criar(municipio, tipo_evento, formador, DIA_INTEIRO_INICIO, DIA_INTEIRO_FIM, projeto_super),
            format="json",
        )
        assert criado.status_code == 201, criado.data
        sol_id = criado.data["id"]
        assert Solicitacao.objects.get(pk=sol_id).status == "pendente"

        with patch.object(guard_module.logger, "info") as log_info:
            aprovado = _client(aprovador).patch(f"/api/solicitacoes/{sol_id}/approve/", {}, format="json")

        assert aprovado.status_code == 200, aprovado.data
        assert Solicitacao.objects.get(pk=sol_id).status == "aprovado"
        # O aviso é registrado (só ids, sem nome de ninguém).
        avisos = [c for c in log_info.call_args_list if c.args and c.args[0] == "availability_warning"]
        assert len(avisos) == 1
        extra = avisos[0].kwargs["extra"]
        assert extra["action"] == "approve"
        assert extra["solicitacao_id"] == sol_id
        assert formador.id in extra["warned_usuario_ids"]
        assert "Bruno" not in str(extra)

    def test_editar_com_dia_acima_do_limite_devolve_200(
        self, coordenador, formador, municipio, tipo_evento, projeto_super
    ):
        sol = _pendente(coordenador, formador, municipio, tipo_evento, projeto_super)
        _oito_horas_no_dia(formador, municipio, tipo_evento)

        response = _client(coordenador).patch(
            f"/api/solicitacoes/{sol.id}/", {"observacoes": "Sala trocada"}, format="json"
        )

        assert response.status_code == 200, response.data
        assert Solicitacao.objects.get(pk=sol.pk).observacoes == "Sala trocada"

    def test_aprovar_com_formador_ja_em_8_horas_devolve_200(
        self, coordenador, formador, aprovador, municipio, tipo_evento, projeto_super
    ):
        sol = _pendente(coordenador, formador, municipio, tipo_evento, projeto_super)
        _oito_horas_no_dia(formador, municipio, tipo_evento)

        response = _client(aprovador).patch(f"/api/solicitacoes/{sol.id}/approve/", {}, format="json")

        assert response.status_code == 200, response.data
        assert Solicitacao.objects.get(pk=sol.pk).status == "aprovado"

    def test_lote_aprova_com_formador_ja_em_8_horas(
        self, coordenador, formador, aprovador, municipio, tipo_evento, projeto_super
    ):
        sol = _pendente(coordenador, formador, municipio, tipo_evento, projeto_super)
        _oito_horas_no_dia(formador, municipio, tipo_evento)

        response = _client(aprovador).post("/api/solicitacoes/batch-approve/", {"ids": [sol.id]}, format="json")

        assert response.status_code == 200, response.data
        assert response.data["approved"] == 1
        assert response.data["errors"] == []
        assert Solicitacao.objects.get(pk=sol.pk).status == "aprovado"


# ============================================================================
# Checagem prévia (assistente): ok com o aviso junto
# ============================================================================


class TestChecagemPreviaDevolveAviso:
    def test_check_many_com_limite_sozinho_devolve_ok_e_aviso(self, aprovador, formador, municipio):
        response = _client(aprovador).post(
            "/api/availability/check-many/",
            {
                "usuarios_ids": [formador.pk],
                "inicio": DIA_INTEIRO_INICIO.isoformat(),
                "fim": DIA_INTEIRO_FIM.isoformat(),
                "municipio_id": municipio.pk,
            },
            format="json",
        )

        assert response.status_code == 200, response.data
        assert response.data["ok"] is True
        (resultado,) = response.data["results"]
        assert resultado["ok"] is True
        assert resultado["conflicts"] == []
        assert [w["code"] for w in resultado["warnings"]] == ["M"]

    def test_check_individual_devolve_a_chave_warnings(self, aprovador, formador, municipio):
        response = _client(aprovador).get(
            "/api/availability/check/",
            {
                "usuario_id": formador.pk,
                "inicio": DIA_INTEIRO_INICIO.isoformat(),
                "fim": DIA_INTEIRO_FIM.isoformat(),
                "municipio_id": municipio.pk,
            },
        )

        assert response.status_code == 200, response.data
        assert response.data["ok"] is True
        assert response.data["conflicts"] == []
        assert [w["code"] for w in response.data["warnings"]] == ["M"]


# ============================================================================
# 400 por outro motivo: o aviso vai junto, separado do que barra
# ============================================================================


class TestAvisoVaiJuntoNoBloqueio:
    def test_sobreposicao_mais_limite_na_mesma_pessoa(
        self, coordenador, formador, aprovador, municipio, tipo_evento, projeto_super
    ):
        sol = _pendente(coordenador, formador, municipio, tipo_evento, projeto_super)
        _oito_horas_no_dia(formador, municipio, tipo_evento)
        _ocupar_agenda("X", formador, municipio, tipo_evento)

        response = _client(aprovador).patch(f"/api/solicitacoes/{sol.id}/approve/", {}, format="json")

        assert response.status_code == 400, response.data
        assert response.data["code"] == "availability_conflict"
        erros = response.data["errors"]
        (bloqueado,) = erros["blocked_participants"]
        assert bloqueado["usuario_id"] == formador.id
        assert [c["code"] for c in bloqueado["conflicts"]] == ["X"]
        assert [w["code"] for w in bloqueado["warnings"]] == ["M"]
        assert [c["code"] for c in erros["conflicts"]] == ["X"]
        assert [w["code"] for w in erros["warnings"]] == ["M"]
        assert "limite diário" not in response.data["detail"]
        assert response.data["detail"] == (
            "Não é possível aprovar a solicitação: Bruno Formador tem outro evento aprovado neste horário."
        )


# ============================================================================
# Guarda: X, T, P e D continuam barrando em criar, editar, aprovar e lote
# ============================================================================


@pytest.mark.parametrize("code", ["X", "T", "P", "D"])
class TestOQueBarraContinuaBarrando:
    def test_criar(self, code, coordenador, formador, municipio, tipo_evento):
        _ocupar_agenda(code, formador, municipio, tipo_evento)
        antes = Solicitacao.objects.count()

        response = _client(coordenador).post(
            "/api/solicitacoes/", _payload_criar(municipio, tipo_evento, formador, INICIO, FIM), format="json"
        )

        assert response.status_code == 400, response.data
        assert response.data["code"] == "availability_conflict"
        (bloqueado,) = response.data["errors"]["blocked_participants"]
        assert {c["code"] for c in bloqueado["conflicts"]} == {code}
        assert Solicitacao.objects.count() == antes

    def test_editar(self, code, coordenador, formador, municipio, tipo_evento, projeto_super):
        sol = _pendente(coordenador, formador, municipio, tipo_evento, projeto_super)
        _ocupar_agenda(code, formador, municipio, tipo_evento)

        response = _client(coordenador).patch(
            f"/api/solicitacoes/{sol.id}/", {"observacoes": "Sala trocada"}, format="json"
        )

        assert response.status_code == 400, response.data
        assert response.data["code"] == "availability_conflict"
        (bloqueado,) = response.data["errors"]["blocked_participants"]
        assert {c["code"] for c in bloqueado["conflicts"]} == {code}
        assert Solicitacao.objects.get(pk=sol.pk).observacoes != "Sala trocada"

    def test_aprovar(self, code, coordenador, formador, aprovador, municipio, tipo_evento, projeto_super):
        sol = _pendente(coordenador, formador, municipio, tipo_evento, projeto_super)
        _ocupar_agenda(code, formador, municipio, tipo_evento)

        response = _client(aprovador).patch(f"/api/solicitacoes/{sol.id}/approve/", {}, format="json")

        assert response.status_code == 400, response.data
        assert response.data["code"] == "availability_conflict"
        (bloqueado,) = response.data["errors"]["blocked_participants"]
        assert {c["code"] for c in bloqueado["conflicts"]} == {code}
        assert Solicitacao.objects.get(pk=sol.pk).status == "pendente"

    def test_lote(self, code, coordenador, formador, aprovador, municipio, tipo_evento, projeto_super):
        sol = _pendente(coordenador, formador, municipio, tipo_evento, projeto_super)
        _ocupar_agenda(code, formador, municipio, tipo_evento)

        response = _client(aprovador).post("/api/solicitacoes/batch-approve/", {"ids": [sol.id]}, format="json")

        assert response.status_code == 200, response.data
        assert response.data["approved"] == 0
        (item,) = response.data["errors"]
        assert item["id"] == sol.id
        assert item["code"] == "availability_conflict"
        (bloqueado,) = item["blocked_participants"]
        assert {c["code"] for c in bloqueado["conflicts"]} == {code}
        assert Solicitacao.objects.get(pk=sol.pk).status == "pendente"

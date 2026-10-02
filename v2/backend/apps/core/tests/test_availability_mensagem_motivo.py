"""
Testes: o erro de disponibilidade diz o motivo real e a ação certa (mapa de acesso 02/10, P9).

Antes, qualquer bloqueio devolvia "<pessoa> já está alocado neste horário. Não é possível
criar o evento." — mesmo quando o motivo era um bloqueio e a ação era aprovar. No lote, o
item de erro trazia só a frase.

Desde 02/10/2026 (decisão do dono) o limite diário (M) é aviso e não barra: saiu dos motivos
de bloqueio. Os casos dele estão em `test_availability_limite_diario_aviso.py`.

Só o TEXTO e o FORMATO do erro mudam. `TestDecisaoNaoMuda` prova que os mesmos casos
continuam barrados e o caso livre continua aprovado.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false, reportPrivateUsage=false

from __future__ import annotations

from datetime import date, datetime
from datetime import timezone as dt_timezone

from rest_framework.test import APIClient

import pytest

from apps.core.models import AvailabilityBlock, Compra, Participation, Solicitacao
from apps.core.services import solicitacao_availability as guard_module
from apps.core.services.availability_service import CheckResult, Conflict
from apps.core.services.config_service import bust_cfg
from apps.core.services.solicitacao_availability import GuardResult, ParticipantConflicts, _build_message
from apps.core.tests.factories import (
    GroupFactory,
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db

MOTIVOS = {
    "X": "tem outro evento aprovado neste horário",
    "T": "tem bloqueio de agenda no período",
    "P": "tem bloqueio parcial de agenda no período",
    "D": "não tem o intervalo de deslocamento entre cidades",
}


def _utc(hora: int, minuto: int = 0) -> datetime:
    """Quarta-feira fixa (10/03/2027), em UTC — Fortaleza é UTC-3, tudo no mesmo dia local."""
    return datetime(2027, 3, 10, hora, minuto, tzinfo=dt_timezone.utc)


# A pendente em teste: 15h–17h em Fortaleza.
INICIO, FIM = _utc(18), _utc(20)


@pytest.fixture(autouse=True)
def _parametros(settings):
    settings.AVAILABILITY_DAILY_LIMIT_HOURS = 8
    settings.TRAVEL_BUFFER_MINUTES = 120
    # O cache de Config sobrevive ao rollback do teste: um valor deixado por outro arquivo
    # (ex.: Buffer 45 em test_config_api) valeria aqui no lugar do settings.
    bust_cfg("availability")


@pytest.fixture
def municipio():
    return MunicipioFactory(nome="Municipio Motivo", uf="CE")


@pytest.fixture
def tipo_evento():
    return TipoEventoFactory(nome="Formação Motivo")


@pytest.fixture
def projeto_super(municipio):
    projeto = ProjetoFactory(nome="Projeto SUPER Motivo", fluxo="SUPER")
    Compra.objects.create(
        codigo="COMP-MOTIVO",
        projeto=projeto,
        municipio=municipio,
        quantidade=10,
        data=date(2026, 1, 10),
        uso="Fixture motivo",
        external_hash="compra-motivo-hash",
    )
    return projeto


@pytest.fixture
def coordenador():
    user = UsuarioFactory(username="coord_motivo", first_name="Ana", last_name="Coordenadora")
    user.groups.add(GroupFactory(name="Coordenador"))
    return user


@pytest.fixture
def formador():
    return UsuarioFactory(username="formador_motivo", first_name="Bruno", last_name="Formador")


@pytest.fixture
def aprovador():
    user = UsuarioFactory(username="gerente_motivo", first_name="Carla", last_name="Gerente")
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


def _ocupar_agenda(code, formador, municipio, tipo_evento):
    """Monta, na agenda do formador, exatamente UM motivo de bloqueio para a pendente 18h–20h UTC."""
    if code == "X":
        _evento(formador, municipio, tipo_evento, INICIO, FIM, status="aprovado", formador=formador)
    elif code in ("T", "P"):
        AvailabilityBlock.objects.create(
            usuario=formador, inicio=_utc(18, 30), fim=_utc(19), tipo=code, status="aprovado", motivo="Bloqueio"
        )
    elif code == "D":
        outra_cidade = MunicipioFactory(nome="Outra Cidade Motivo", uf="CE")
        _evento(formador, outra_cidade, tipo_evento, _utc(16), _utc(17), status="aprovado", formador=formador)


# ============================================================================
# Guarda: a decisão aprovar/barrar é a mesma de antes
# ============================================================================


class TestDecisaoNaoMuda:
    @pytest.mark.parametrize("code", ["X", "T", "P", "D"])
    def test_cada_motivo_continua_barrando_a_aprovacao(
        self, code, coordenador, formador, aprovador, municipio, tipo_evento, projeto_super
    ):
        sol = _pendente(coordenador, formador, municipio, tipo_evento, projeto_super)
        _ocupar_agenda(code, formador, municipio, tipo_evento)

        response = _client(aprovador).patch(f"/api/solicitacoes/{sol.id}/approve/", {}, format="json")

        assert response.status_code == 400, response.data
        assert response.data["code"] == "availability_conflict"
        bloqueados = response.data["errors"]["blocked_participants"]
        assert [b["usuario_id"] for b in bloqueados] == [formador.id]
        assert {c["code"] for c in bloqueados[0]["conflicts"]} == {code}
        assert Solicitacao.objects.get(pk=sol.pk).status == "pendente"

    def test_agenda_livre_continua_aprovando(
        self, coordenador, formador, aprovador, municipio, tipo_evento, projeto_super
    ):
        sol = _pendente(coordenador, formador, municipio, tipo_evento, projeto_super)

        response = _client(aprovador).patch(f"/api/solicitacoes/{sol.id}/approve/", {}, format="json")

        assert response.status_code == 200, response.data
        assert Solicitacao.objects.get(pk=sol.pk).status == "aprovado"

    def test_lote_aprova_o_livre_e_barra_o_conflitante(
        self, coordenador, formador, aprovador, municipio, tipo_evento, projeto_super
    ):
        livre = _evento(
            coordenador, municipio, tipo_evento, _utc(12), _utc(13), status="pendente", projeto=projeto_super
        )
        barrada = _pendente(coordenador, formador, municipio, tipo_evento, projeto_super)
        _ocupar_agenda("X", formador, municipio, tipo_evento)

        response = _client(aprovador).post(
            "/api/solicitacoes/batch-approve/", {"ids": [livre.id, barrada.id]}, format="json"
        )

        assert response.status_code == 200, response.data
        assert response.data["approved"] == 1
        assert [e["id"] for e in response.data["errors"]] == [barrada.id]
        assert Solicitacao.objects.get(pk=livre.pk).status == "aprovado"
        assert Solicitacao.objects.get(pk=barrada.pk).status == "pendente"

    def test_lote_itens_de_erro_que_nao_sao_de_agenda_seguem_iguais(self, aprovador):
        response = _client(aprovador).post("/api/solicitacoes/batch-approve/", {"ids": [999999]}, format="json")

        assert response.status_code == 200, response.data
        assert response.data["errors"] == [{"id": 999999, "detail": "Solicitação não encontrada"}]


# ============================================================================
# O texto: motivo real + ação certa
# ============================================================================


class TestMensagemDizMotivoEAcao:
    @pytest.mark.parametrize("code", ["X", "T", "P", "D"])
    def test_aprovar_diz_o_motivo_e_a_acao(
        self, code, coordenador, formador, aprovador, municipio, tipo_evento, projeto_super
    ):
        sol = _pendente(coordenador, formador, municipio, tipo_evento, projeto_super)
        _ocupar_agenda(code, formador, municipio, tipo_evento)

        response = _client(aprovador).patch(f"/api/solicitacoes/{sol.id}/approve/", {}, format="json")

        assert response.data["detail"] == f"Não é possível aprovar a solicitação: Bruno Formador {MOTIVOS[code]}."

    def test_criar_com_conflito_mantem_a_acao_criar(self, coordenador, formador, municipio, tipo_evento):
        _ocupar_agenda("X", formador, municipio, tipo_evento)

        response = _client(coordenador).post(
            "/api/solicitacoes/",
            {
                "municipio": municipio.pk,
                "tipo_evento": tipo_evento.pk,
                "inicio": INICIO.isoformat(),
                "fim": FIM.isoformat(),
                "extra_participants": {"formador_ids": [formador.pk]},
            },
            format="json",
        )

        assert response.status_code == 400, response.data
        assert response.data["detail"] == f"Não é possível criar o evento: Bruno Formador {MOTIVOS['X']}."

    def test_editar_com_conflito_diz_salvar_a_alteracao(
        self, coordenador, formador, municipio, tipo_evento, projeto_super
    ):
        sol = _pendente(coordenador, formador, municipio, tipo_evento, projeto_super)
        _ocupar_agenda("X", formador, municipio, tipo_evento)

        response = _client(coordenador).patch(
            f"/api/solicitacoes/{sol.id}/", {"observacoes": "Sala trocada"}, format="json"
        )

        assert response.status_code == 400, response.data
        assert response.data["code"] == "availability_conflict"
        assert response.data["detail"] == f"Não é possível salvar a alteração: Bruno Formador {MOTIVOS['X']}."
        assert Solicitacao.objects.get(pk=sol.pk).observacoes != "Sala trocada"

    def test_lote_item_de_conflito_traz_code_motivo_e_quem(
        self, coordenador, formador, aprovador, municipio, tipo_evento, projeto_super
    ):
        barrada = _pendente(coordenador, formador, municipio, tipo_evento, projeto_super)
        _ocupar_agenda("X", formador, municipio, tipo_evento)

        response = _client(aprovador).post("/api/solicitacoes/batch-approve/", {"ids": [barrada.id]}, format="json")

        assert response.data["approved"] == 0
        (item,) = response.data["errors"]
        assert item["id"] == barrada.id
        assert item["code"] == "availability_conflict"
        assert item["detail"] == f"Não é possível aprovar a solicitação: Bruno Formador {MOTIVOS['X']}."
        (bloqueado,) = item["blocked_participants"]
        assert bloqueado["usuario_id"] == formador.id
        assert [c["code"] for c in bloqueado["conflicts"]] == ["X"]


class TestMontagemDaMensagem:
    """`_build_message` direto: casos que a API não monta sozinha."""

    @staticmethod
    def _guard(*bloqueados: tuple[str, list[Conflict]]) -> GuardResult:
        return GuardResult(
            ok=False,
            blocked=[
                ParticipantConflicts(usuario_id=i, usuario_nome=nome, conflicts=conflitos)
                for i, (nome, conflitos) in enumerate(bloqueados, start=1)
            ],
            skipped_guests=[],
            checked_usuario_ids=[],
        )

    def test_acoes(self):
        guard = self._guard(("Bruno Formador", [Conflict("D", "Buffer deslocamento insuficiente", "x")]))
        esperado = {
            "create": "criar o evento",
            "update": "salvar a alteração",
            "approve": "aprovar a solicitação",
            "batch_approve": "aprovar a solicitação",
            "acao_que_nao_existe": "concluir a ação",
        }
        for action, texto in esperado.items():
            assert _build_message(guard, action=action).startswith(f"Não é possível {texto}: Bruno Formador ")

    def test_varios_motivos_e_varias_pessoas(self):
        guard = self._guard(
            (
                "Bruno Formador",
                [
                    Conflict("D", "Buffer deslocamento insuficiente", "x"),
                    Conflict("D", "Buffer deslocamento insuficiente", "y"),
                    Conflict("P", "Bloqueio parcial", "z"),
                ],
            ),
            ("Dora Formadora", [Conflict("T", "Bloqueio total", "w")]),
        )

        assert _build_message(guard, action="approve") == (
            "Não é possível aprovar a solicitação: Bruno Formador "
            + f"{MOTIVOS['D']} e {MOTIVOS['P']}; Dora Formadora {MOTIVOS['T']}."
        )

    def test_intervalo_invalido_nao_diz_outro_evento(self):
        guard = self._guard(("Bruno Formador", [Conflict("X", "Intervalo inválido", "fim deve ser > início")]))

        mensagem = _build_message(guard, action="update")

        assert "outro evento" not in mensagem
        assert (
            mensagem == "Não é possível salvar a alteração: Bruno Formador tem conflito de agenda (intervalo inválido)."
        )

    def test_codigo_desconhecido_cai_no_texto_generico(self):
        guard = self._guard(("Bruno Formador", [Conflict("Z", "", "regra nova")]))  # type: ignore[arg-type]

        assert _build_message(guard, action="approve") == (
            "Não é possível aprovar a solicitação: Bruno Formador tem conflito de agenda."
        )


class TestCodigoDesconhecidoNaoDerrubaNada:
    """Um código de conflito fora do mapa segue virando 400 / errors[] — nunca 500."""

    @pytest.fixture
    def conflito_novo_para_o_formador(self, monkeypatch, formador):
        def fake(*, usuario, **_kwargs):
            if usuario.id == formador.id:
                return CheckResult(ok=False, conflicts=[Conflict("Z", "Regra nova", "detalhe")])  # type: ignore[arg-type]
            return CheckResult(ok=True, conflicts=[])

        monkeypatch.setattr(guard_module, "check_conflicts_uncached", fake)

    def test_individual_continua_400(
        self, conflito_novo_para_o_formador, coordenador, formador, aprovador, municipio, tipo_evento, projeto_super
    ):
        sol = _pendente(coordenador, formador, municipio, tipo_evento, projeto_super)

        response = _client(aprovador).patch(f"/api/solicitacoes/{sol.id}/approve/", {}, format="json")

        assert response.status_code == 400, response.data
        assert response.data["code"] == "availability_conflict"
        assert response.data["detail"] == (
            "Não é possível aprovar a solicitação: Bruno Formador tem conflito de agenda (regra nova)."
        )
        assert Solicitacao.objects.get(pk=sol.pk).status == "pendente"

    def test_lote_barra_so_o_item_e_aprova_os_demais(
        self, conflito_novo_para_o_formador, coordenador, formador, aprovador, municipio, tipo_evento, projeto_super
    ):
        livre = _evento(
            coordenador, municipio, tipo_evento, _utc(12), _utc(13), status="pendente", projeto=projeto_super
        )
        barrada = _pendente(coordenador, formador, municipio, tipo_evento, projeto_super)

        response = _client(aprovador).post(
            "/api/solicitacoes/batch-approve/", {"ids": [livre.id, barrada.id]}, format="json"
        )

        assert response.status_code == 200, response.data
        assert response.data["approved"] == 1
        (item,) = response.data["errors"]
        assert item["id"] == barrada.id
        assert item["code"] == "availability_conflict"
        assert Solicitacao.objects.get(pk=livre.pk).status == "aprovado"

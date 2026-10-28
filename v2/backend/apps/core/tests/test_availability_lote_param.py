"""
Testes: parâmetro `lote` do motor de disponibilidade (criação de vários eventos de uma vez, 28/10).

No lote, os eventos gravados na mesma transação precisam se enxergar mesmo pendentes (SUPER):
dois eventos com a mesma pessoa no mesmo horário são erro, e o deslocamento (D) entre eles também.
`lote` é o mapa {id gravado: número do evento na lista}; o próprio evento continua excluído por
`exclude_solicitacao_id`. A mensagem cita "o evento N desta lista", porque o id some no rollback.

Sem `lote` (None) o motor é o de sempre: só evento aprovado ocupa a agenda.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false, reportPrivateUsage=false

from __future__ import annotations

import inspect
from datetime import datetime
from datetime import timezone as dt_timezone

import pytest

from apps.core.exceptions import ValidationAPIError
from apps.core.models import Participation
from apps.core.services.availability_service import check_conflicts, check_conflicts_uncached
from apps.core.services.config_service import bust_cfg
from apps.core.services.solicitacao_availability import check_solicitacao_availability, raise_if_blocked
from apps.core.tests.factories import MunicipioFactory, SolicitacaoFactory, TipoEventoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


def _utc(hora: int, minuto: int = 0) -> datetime:
    """Quarta-feira fixa (10/03/2027), em UTC — Fortaleza é UTC-3, tudo no mesmo dia local."""
    return datetime(2027, 3, 10, hora, minuto, tzinfo=dt_timezone.utc)


@pytest.fixture(autouse=True)
def _parametros(settings):
    settings.TRAVEL_BUFFER_MINUTES = 120
    bust_cfg("availability")


@pytest.fixture
def cidade_a():
    return MunicipioFactory(nome="Cidade A Lote", uf="CE")


@pytest.fixture
def cidade_b():
    return MunicipioFactory(nome="Cidade B Lote", uf="CE")


@pytest.fixture
def tipo_evento():
    return TipoEventoFactory(nome="Formação Lote")


@pytest.fixture
def formador():
    return UsuarioFactory(username="formador_lote", first_name="Bruno", last_name="Formador")


def _evento(formador, municipio, tipo_evento, inicio, fim, *, status="pendente"):
    sol = SolicitacaoFactory(
        usuario=formador, municipio=municipio, tipo_evento=tipo_evento, inicio=inicio, fim=fim, status=status
    )
    Participation.objects.create(solicitacao=sol, usuario=formador, role=Participation.Role.FORMADOR)
    return sol


def _checar(sol, lote=None):
    return check_conflicts_uncached(
        usuario=sol.participations.get(role="FORMADOR").usuario,
        inicio=sol.inicio,
        fim=sol.fim,
        municipio=sol.municipio,
        exclude_solicitacao_id=sol.pk,
        lote=lote,
    )


class TestSobreposicaoNoLote:
    def test_irmao_pendente_no_lote_gera_x_com_o_numero_do_evento(self, formador, cidade_a, tipo_evento):
        um = _evento(formador, cidade_a, tipo_evento, _utc(12), _utc(14))
        dois = _evento(formador, cidade_a, tipo_evento, _utc(13), _utc(15))

        sem_lote = _checar(dois)
        com_lote = _checar(dois, lote={um.pk: 1, dois.pk: 2})

        assert sem_lote.ok, "pendente fora do lote segue invisível (o avulso não muda)"
        assert [c.code for c in com_lote.conflicts] == ["X"]
        conflito = com_lote.conflicts[0]
        assert conflito.ref_id == um.pk
        assert "o evento 1 desta lista" in conflito.detail
        assert f"#{um.pk}" not in conflito.detail
        assert "aprovado" not in conflito.detail

    def test_o_proprio_evento_no_lote_nao_conflita_consigo(self, formador, cidade_a, tipo_evento):
        um = _evento(formador, cidade_a, tipo_evento, _utc(12), _utc(14))

        assert _checar(um, lote={um.pk: 1}).ok

    def test_irmao_que_so_tem_o_proprio_id_no_lote_fica_invisivel(self, formador, cidade_a, tipo_evento):
        """Por isso o lote é o mapa COMPLETO: com só o próprio id, o choque SUPER+SUPER passaria."""
        um = _evento(formador, cidade_a, tipo_evento, _utc(12), _utc(14))
        dois = _evento(formador, cidade_a, tipo_evento, _utc(13), _utc(15))

        assert _checar(dois, lote={dois.pk: 2}).ok
        assert not _checar(dois, lote={um.pk: 1, dois.pk: 2}).ok

    def test_aprovado_do_banco_segue_citado_pelo_id(self, formador, cidade_a, tipo_evento):
        aprovado = _evento(formador, cidade_a, tipo_evento, _utc(12), _utc(14), status="aprovado")
        novo = _evento(formador, cidade_a, tipo_evento, _utc(13), _utc(15))

        com_lote = _checar(novo, lote={novo.pk: 1})

        assert [c.detail for c in com_lote.conflicts] == [
            c.detail for c in _checar(novo).conflicts
        ], "aprovado de fora do lote: mesma mensagem de hoje"
        assert f"evento aprovado #{aprovado.pk}" in com_lote.conflicts[0].detail


class TestDeslocamentoNoLote:
    def test_irmao_em_outra_cidade_sem_intervalo_gera_d_antes_e_depois(self, formador, cidade_a, cidade_b, tipo_evento):
        antes = _evento(formador, cidade_b, tipo_evento, _utc(10), _utc(11))
        meio = _evento(formador, cidade_a, tipo_evento, _utc(12), _utc(13))
        depois = _evento(formador, cidade_b, tipo_evento, _utc(14), _utc(15))
        lote = {antes.pk: 1, meio.pk: 2, depois.pk: 3}

        resultado = _checar(meio, lote=lote)

        assert _checar(meio).ok
        assert [c.code for c in resultado.conflicts] == ["D", "D"]
        assert "após o evento 1 desta lista" in resultado.conflicts[0].detail
        assert "antes do evento 3 desta lista" in resultado.conflicts[1].detail
        assert all("#" not in c.detail for c in resultado.conflicts)

    def test_irmao_na_mesma_cidade_nao_esconde_o_d_do_aprovado(self, formador, cidade_a, cidade_b, tipo_evento):
        """O mais próximo antes do evento passa a ser o irmão (mesma cidade, sem D). O aprovado em outra
        cidade, logo antes do irmão, segue gerando o D que o evento já tinha sem o lote."""
        aprovado = _evento(formador, cidade_b, tipo_evento, _utc(9), _utc(10), status="aprovado")
        irmao = _evento(formador, cidade_a, tipo_evento, _utc(10), _utc(10, 30))
        novo = _evento(formador, cidade_a, tipo_evento, _utc(11), _utc(12))

        hoje = _checar(novo)
        com_lote = _checar(novo, lote={irmao.pk: 1, novo.pk: 2})

        assert [c.ref_id for c in hoje.conflicts] == [aprovado.pk]
        assert aprovado.pk in [c.ref_id for c in com_lote.conflicts if c.code == "D"]

    def test_depois_tambem_nao_esconde_o_d_do_aprovado(self, formador, cidade_a, cidade_b, tipo_evento):
        novo = _evento(formador, cidade_a, tipo_evento, _utc(11), _utc(12))
        irmao = _evento(formador, cidade_a, tipo_evento, _utc(12, 30), _utc(13))
        aprovado = _evento(formador, cidade_b, tipo_evento, _utc(13), _utc(14), status="aprovado")

        com_lote = _checar(novo, lote={novo.pk: 1, irmao.pk: 2})

        assert aprovado.pk in [c.ref_id for c in com_lote.conflicts if c.code == "D"]


class TestSemLoteIgualAHoje:
    def test_lote_none_da_o_mesmo_resultado(self, formador, cidade_a, cidade_b, tipo_evento):
        _evento(formador, cidade_a, tipo_evento, _utc(12), _utc(14), status="aprovado")
        _evento(formador, cidade_b, tipo_evento, _utc(15), _utc(16), status="aprovado")
        _evento(formador, cidade_a, tipo_evento, _utc(13), _utc(14))  # pendente: invisível
        novo = _evento(formador, cidade_a, tipo_evento, _utc(13), _utc(15))

        sem_parametro = check_conflicts_uncached(
            usuario=formador, inicio=novo.inicio, fim=novo.fim, municipio=cidade_a, exclude_solicitacao_id=novo.pk
        )

        assert _checar(novo, lote=None) == sem_parametro
        assert [c.code for c in sem_parametro.conflicts] == ["X", "D"]

    def test_check_conflicts_com_cache_nao_recebe_lote(self):
        """A chave de cache é uma lista fixa de campos: `lote` mudaria o resultado sem mudar a chave."""
        assert "lote" not in inspect.signature(check_conflicts).parameters


class TestMensagemDoGuard:
    def test_super_mais_super_no_lote_bloqueia_e_a_frase_nao_diz_aprovado(self, formador, cidade_a, tipo_evento):
        um = _evento(formador, cidade_a, tipo_evento, _utc(12), _utc(14))
        dois = _evento(formador, cidade_a, tipo_evento, _utc(13), _utc(15))
        lote = {um.pk: 1, dois.pk: 2}

        guard = check_solicitacao_availability(dois, lock=False, lote=lote)
        with pytest.raises(ValidationAPIError) as exc:
            raise_if_blocked(guard, action="create")

        assert not guard.ok
        assert "aprovado" not in exc.value.message
        assert "outro evento desta lista neste horário" in exc.value.message
        assert check_solicitacao_availability(dois, lock=False).ok

    def test_sem_lote_a_frase_segue_a_de_hoje(self, formador, cidade_a, tipo_evento):
        _evento(formador, cidade_a, tipo_evento, _utc(12), _utc(14), status="aprovado")
        novo = _evento(formador, cidade_a, tipo_evento, _utc(13), _utc(15))

        with pytest.raises(ValidationAPIError) as exc:
            raise_if_blocked(check_solicitacao_availability(novo, lock=False), action="create")

        assert "tem outro evento aprovado neste horário" in exc.value.message

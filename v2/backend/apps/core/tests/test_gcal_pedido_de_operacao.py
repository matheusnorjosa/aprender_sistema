"""
DEF-32 + ISS-1970 — o pedido de operação no Google (publicar, reenviar, reaplicar, cancelar).

Antes, a entrada marcava PENDING sem trava e sem transação, e a tarefa agia sobre o que achasse na linha:
um pedido antigo podia desfazer um mais novo, a marca de erro apagava o resultado de outra operação e a
fila fora do ar deixava a linha em PENDING sem tarefa. Agora cada pedido grava um identificador
(`Solicitacao.gcal_pedido`) com a linha travada, na mesma transação que enfileira a tarefa, e a tarefa só
age se o identificador dela ainda é o da linha.

O Google é sempre simulado; nada sai da máquina.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from unittest.mock import patch

from django.db import OperationalError, connection, transaction
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

import pytest

from apps.core.exceptions import ConflictError, ValidationAPIError
from apps.core.models import AuditLog, Solicitacao
from apps.core.tests.factories import SolicitacaoFactory, UsuarioFactory

_CAMPOS = ("gcal_pedido", "gcal_status", "gcal_payload_hash", "gcal_last_error", "gcal_last_sync_at")
_HASH = "a" * 40
_PENDING = Solicitacao.GCalStatus.PENDING
_DELAY_PUBLICAR = "apps.core.tasks.task_publish_solicitacao_to_gcal.delay"
_DELAY_CANCELAR = "apps.core.tasks.task_cancel_solicitacao_from_gcal.delay"


def _evento(**extra) -> Solicitacao:
    """Aprovado e futuro; nunca publicado, salvo o que `extra` trocar."""
    return SolicitacaoFactory(**{"status": "aprovado", **extra})


def _linha(sol) -> dict:
    return Solicitacao.objects.filter(pk=sol.pk).values(*_CAMPOS).get()


def _erro_do_banco(sqlstate: str) -> OperationalError:
    """OperationalError como o Django levanta: a causa (do psycopg) traz o SQLSTATE."""
    causa = Exception("erro do banco")
    causa.sqlstate = sqlstate
    erro = OperationalError("erro do banco")
    erro.__cause__ = causa
    return erro


# =============================================================================
# O campo
# =============================================================================


@pytest.mark.django_db
def test_gcal_pedido_fica_fora_dos_formularios():
    """O admin usa `fields="__all__"`: campo editável entraria no formulário, e salvar por lá regravaria o
    identificador lido antes."""
    assert Solicitacao._meta.get_field("gcal_pedido").editable is False


@pytest.mark.django_db
def test_insert_sem_a_coluna_gcal_pedido_nasce_vazio_pelo_default_do_banco():
    """Deploy: a migration roda antes da troca do container; o código antigo não conhece a coluna.

    O INSERT dele (sem `gcal_pedido`) precisa passar pelo DEFAULT do banco (`db_default`), senão falha com
    NOT NULL ao criar Solicitação durante o deploy.
    """
    base = SolicitacaoFactory()
    with connection.cursor() as cursor:
        colunas = [
            c.name
            for c in connection.introspection.get_table_description(cursor, Solicitacao._meta.db_table)
            if c.name not in {"id", "gcal_pedido"}
        ]
        lista = ", ".join(connection.ops.quote_name(c) for c in colunas)
        tabela = connection.ops.quote_name(Solicitacao._meta.db_table)
        cursor.execute(
            f"INSERT INTO {tabela} ({lista}) SELECT {lista} FROM {tabela} WHERE id = %s RETURNING id",  # noqa: S608  # nosec B608 (nomes da introspecção; valor parametrizado)
            [base.pk],
        )
        linha = cursor.fetchone()
    assert linha is not None
    assert Solicitacao.objects.get(pk=linha[0]).gcal_pedido == ""


# =============================================================================
# A função de pedido
# =============================================================================


@pytest.mark.django_db
class TestPedirOperacaoGcal:
    """`pedir_operacao_gcal` trava a linha, confere de novo sobre ela, grava o identificador e marca PENDING."""

    def test_cada_pedido_grava_um_identificador_novo_e_marca_pending(self):
        from apps.core.services.solicitacao_publish import pedir_operacao_gcal

        sol = _evento(gcal_status="ERROR", gcal_last_error="falhou antes")

        primeiro = pedir_operacao_gcal(sol.pk, "publicar")

        linha = _linha(sol)
        assert len(primeiro) == 32
        assert linha["gcal_pedido"] == primeiro
        assert linha["gcal_status"] == Solicitacao.GCalStatus.PENDING
        assert linha["gcal_last_error"] == ""
        # A cópia Google → Sistema usa este carimbo como guarda: o pedido tem de atualizá-lo.
        assert linha["gcal_last_sync_at"] is not None

        segundo = pedir_operacao_gcal(sol.pk, "reenviar")

        assert segundo != primeiro
        assert _linha(sol)["gcal_pedido"] == segundo

    @pytest.mark.parametrize(
        "operacao, gcal_status, esperado",
        [
            ("publicar", "ERROR", None),
            ("reenviar", "PUBLISHED", None),
            ("cancelar", "PUBLISHED", _HASH),
            ("reaplicar", "PUBLISHED", _HASH),
            ("reaplicar", "ERROR", None),
            ("reaplicar", "PENDING", None),
        ],
    )
    def test_o_que_cada_operacao_faz_com_o_hash(self, operacao, gcal_status, esperado):
        """Publicar e reenviar zeram (o envio é forçado); cancelar mantém; reaplicar mantém só o de linha
        PUBLISHED, que é o que deixa o envio sem mudança virar SKIP."""
        from apps.core.services.solicitacao_publish import pedir_operacao_gcal

        sol = _evento(gcal_status=gcal_status, external_event_id="evt-hash", gcal_payload_hash=_HASH)

        pedir_operacao_gcal(sol.pk, operacao)

        linha = _linha(sol)
        assert linha["gcal_payload_hash"] == esperado
        assert linha["gcal_status"] == Solicitacao.GCalStatus.PENDING

    def test_pedido_trava_a_linha_com_teto_de_espera(self):
        from apps.core.services.solicitacao_publish import pedir_operacao_gcal

        sol = _evento()

        with CaptureQueriesContext(connection) as consultas:
            pedir_operacao_gcal(sol.pk, "publicar")

        sqls = [q["sql"] for q in consultas.captured_queries]
        travas = [i for i, sql in enumerate(sqls) if "FOR UPDATE" in sql and 'FROM "core_solicitacao"' in sql]
        tetos = [i for i, sql in enumerate(sqls) if "set_config('lock_timeout'" in sql]
        assert travas, "o pedido não travou a linha"
        assert tetos and tetos[0] < travas[0], "o teto da espera tem de valer antes da trava"
        assert "'10s'" in sqls[tetos[0]]

    def test_a_conferencia_e_feita_na_linha_travada(self):
        """A aprovação é desfeita entre a leitura sem trava de quem chama e o FOR UPDATE: logo antes dele, a
        mesma conexão rebaixa a linha. Quem conferisse antes da trava marcaria PENDING num evento pendente."""
        from apps.core.services.solicitacao_publish import pedir_operacao_gcal

        sol = _evento()
        antes = _linha(sol)

        def rebaixa_antes_da_trava(execute, sql, params, many, context):
            if "FOR UPDATE" in sql and 'FROM "core_solicitacao"' in sql:
                Solicitacao.objects.filter(pk=sol.pk).update(status="pendente")
            return execute(sql, params, many, context)

        with connection.execute_wrapper(rebaixa_antes_da_trava), pytest.raises(ValidationAPIError) as erro:
            pedir_operacao_gcal(sol.pk, "publicar")

        assert erro.value.code == "not_approved"
        assert _linha(sol) == antes

    @pytest.mark.parametrize(
        "operacao, estado, code",
        [
            ("publicar", {"status": "pendente"}, "not_approved"),
            ("reenviar", {"status": "pendente", "gcal_status": "PUBLISHED"}, "not_approved"),
            ("reaplicar", {"status": "pendente", "gcal_status": "PUBLISHED"}, "not_approved"),
            ("publicar", {"gcal_status": "PUBLISHED"}, "ja_publicado"),
            ("publicar", {"gcal_status": "PENDING"}, "ja_publicado"),
            ("reenviar", {"gcal_status": "NONE"}, "nao_publicado"),
            ("reaplicar", {"gcal_status": "NONE"}, "nao_publicado"),
        ],
    )
    def test_recusa_relida_sob_a_trava_nao_muda_a_linha(self, operacao, estado, code):
        from apps.core.services.solicitacao_publish import pedir_operacao_gcal

        sol = _evento(**estado)
        antes = _linha(sol)

        with pytest.raises(ValidationAPIError) as erro:
            pedir_operacao_gcal(sol.pk, operacao)

        assert erro.value.code == code
        assert _linha(sol) == antes

    def test_cancelar_sem_evento_no_google_e_recusado_e_nao_muda_a_linha(self):
        from apps.core.services.solicitacao_publish import pedir_operacao_gcal

        sol = _evento()
        antes = _linha(sol)

        with pytest.raises(ConflictError) as erro:
            pedir_operacao_gcal(sol.pk, "cancelar")

        assert erro.value.details["code"] == "not_published"
        assert _linha(sol) == antes

    def test_trava_ocupada_alem_do_teto_vira_conflito_com_o_texto_da_edicao(self):
        """55P03 (lock_not_available): o pedido desiste com o mesmo texto da edição (DEF-30), sem tocar a linha."""
        from apps.core.services.solicitacao_publish import pedir_operacao_gcal
        from apps.core.views_solicitacao import SolicitacaoViewSet

        sol = _evento()
        antes = _linha(sol)

        with (
            patch.object(Solicitacao.objects, "select_for_update", side_effect=_erro_do_banco("55P03")),
            pytest.raises(ConflictError) as erro,
        ):
            pedir_operacao_gcal(sol.pk, "publicar")

        assert erro.value.details["code"] == "linha_ocupada"
        assert erro.value.message == SolicitacaoViewSet._MSG_EDICAO_LINHA_OCUPADA  # pyright: ignore[reportPrivateUsage]
        assert _linha(sol) == antes

    def test_outro_erro_do_banco_na_trava_sobe_como_veio(self):
        """Só a espera vencida vira "linha ocupada"; o statement cancelado (57014), por exemplo, não."""
        from apps.core.services.solicitacao_publish import pedir_operacao_gcal

        sol = _evento()

        with (
            patch.object(Solicitacao.objects, "select_for_update", side_effect=_erro_do_banco("57014")),
            pytest.raises(OperationalError),
        ):
            pedir_operacao_gcal(sol.pk, "publicar")


@pytest.mark.django_db(transaction=True)
def test_pedido_exige_a_transacao_de_quem_chama():
    """A função não abre transação: quem chama abre, e o enfileiramento entra nela. Fora de transação o
    `select_for_update` levanta, em vez de gravar PENDING sem a tarefa."""
    from apps.core.services.solicitacao_publish import pedir_operacao_gcal

    sol = _evento()
    antes = _linha(sol)

    with pytest.raises(transaction.TransactionManagementError):
        pedir_operacao_gcal(sol.pk, "publicar")

    assert _linha(sol) == antes


# =============================================================================
# As entradas de uma linha: publicar, reenviar e tirar do Google
# =============================================================================

_NO_GOOGLE = {"gcal_status": "PUBLISHED", "external_event_id": "evt-entrada", "gcal_payload_hash": _HASH}
# `mudanca`: o que outra operação grava entre a leitura sem trava da entrada e o pedido.
_ENTRADAS = {
    "publicar": {
        "rota": "publish",
        "estado": {},
        "delay": _DELAY_PUBLICAR,
        "acao": "PUBLISH_GCAL_REQUESTED",
        "mudanca": {"status": "pendente"},
        "recusa": 400,
    },
    "reenviar": {
        "rota": "resync-gcal",
        "estado": _NO_GOOGLE,
        "delay": _DELAY_PUBLICAR,
        "acao": "RESYNC_GCAL_REQUESTED",
        "mudanca": {"status": "pendente"},
        "recusa": 400,
    },
    "cancelar": {
        "rota": "cancel-gcal",
        "estado": _NO_GOOGLE,
        "delay": _DELAY_CANCELAR,
        "acao": "CANCEL_GCAL_REQUESTED",
        "mudanca": {"gcal_status": "NONE", "external_event_id": None},
        "recusa": 409,
    },
}
_TRES_ENTRADAS = pytest.mark.parametrize("entrada", list(_ENTRADAS))


def _api(**opcoes) -> APIClient:
    api = APIClient(**opcoes)
    api.force_authenticate(UsuarioFactory(superuser=True))
    return api


def _pediu(sol, acao: str) -> bool:
    return AuditLog.objects.filter(action=acao, details__solicitacao_id=sol.pk).exists()


@pytest.mark.django_db
@_TRES_ENTRADAS
def test_entrada_confere_de_novo_sob_a_trava(entrada, settings):
    """A linha muda no banco depois da leitura sem trava da entrada (a aprovação foi desfeita; o evento saiu do
    Google). O pedido relê sob a trava e recusa: nada vai para a fila e a linha não fica PENDING. A recusa é a
    mesma que a entrada dá quando já lê a linha nesse estado."""
    settings.GCAL_CLIENT = "google"
    dados = _ENTRADAS[entrada]
    sol = _evento(**dados["estado"])
    api = _api()
    url = f"/api/solicitacoes/{sol.pk}/{dados['rota']}/"

    def outra_operacao_muda_a_linha(_user):
        Solicitacao.objects.filter(pk=sol.pk).update(**dados["mudanca"])

    with (
        patch("apps.core.services.solicitacao_publish._check_google_oauth", side_effect=outra_operacao_muda_a_linha),
        patch(dados["delay"]) as delay,
    ):
        delay.return_value.id = "tarefa-indevida"
        sob_trava = api.post(url, {}, format="json")

    delay.assert_not_called()
    assert sob_trava.status_code == dados["recusa"], sob_trava.data
    linha = _linha(sol)
    assert linha["gcal_status"] != _PENDING
    assert linha["gcal_pedido"] == ""
    assert not _pediu(sol, dados["acao"])

    with patch(dados["delay"]):
        sem_trava = api.post(url, {}, format="json")

    assert (sob_trava.status_code, sob_trava.data) == (sem_trava.status_code, sem_trava.data)


@pytest.mark.django_db(transaction=True)
@_TRES_ENTRADAS
def test_fila_fora_do_ar_responde_503_e_nao_deixa_a_linha_em_pending(entrada, settings):
    """O `.delay` falha (Redis fora): a transação do pedido desfaz e a linha fica como estava, com o mesmo
    identificador. Antes, o PENDING já estava gravado e não havia tarefa para tirá-lo de lá."""
    from kombu.exceptions import OperationalError as FilaForaDoAr

    settings.GCAL_CLIENT = "google"
    dados = _ENTRADAS[entrada]
    sol = _evento(**dados["estado"])
    antes = _linha(sol)

    with patch(dados["delay"], side_effect=FilaForaDoAr("redis fora do ar")):
        resposta = _api(raise_request_exception=False).post(
            f"/api/solicitacoes/{sol.pk}/{dados['rota']}/", {}, format="json"
        )

    assert resposta.status_code == 503
    assert resposta.data["code"] == "fila_indisponivel"
    assert "Nada foi alterado" in resposta.data["detail"]
    assert _linha(sol) == antes
    assert not _pediu(sol, dados["acao"])


@pytest.mark.django_db
@_TRES_ENTRADAS
def test_tarefa_e_auditoria_levam_o_pedido_gravado_na_linha(entrada, settings):
    settings.GCAL_CLIENT = "google"
    dados = _ENTRADAS[entrada]
    sol = _evento(**dados["estado"])

    with patch(dados["delay"]) as delay:
        delay.return_value.id = "tarefa-1"
        resposta = _api().post(f"/api/solicitacoes/{sol.pk}/{dados['rota']}/", {}, format="json")

    assert resposta.status_code == 202, resposta.data
    linha = _linha(sol)
    assert linha["gcal_status"] == _PENDING
    assert len(linha["gcal_pedido"]) == 32
    delay.assert_called_once()
    assert delay.call_args.args == (sol.pk,)
    assert delay.call_args.kwargs["pedido"] == linha["gcal_pedido"]
    registro = AuditLog.objects.get(action=dados["acao"], details__solicitacao_id=sol.pk)
    assert registro.details["pedido"] == linha["gcal_pedido"]
    assert registro.details["task_id"] == "tarefa-1"


@pytest.mark.django_db
def test_previa_do_publicar_nao_faz_pedido():
    """A prévia não grava nada: a tarefa vai sem identificador e a linha fica como estava."""
    sol = _evento()
    antes = _linha(sol)

    with patch(_DELAY_PUBLICAR) as delay:
        delay.return_value.id = "previa-1"
        resposta = _api().post(f"/api/solicitacoes/{sol.pk}/publish/", {"dry_run": True}, format="json")

    assert resposta.status_code == 202, resposta.data
    delay.assert_called_once_with(sol.pk, dry_run=True, apply_blocked=False)
    assert _linha(sol) == antes

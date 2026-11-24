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

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
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


def _erro_do_banco(sqlstate: str, atributo: str = "sqlstate") -> OperationalError:
    """OperationalError como o Django levanta: a causa (do driver) traz o SQLSTATE, em `sqlstate` no psycopg 3
    (desenvolvimento e testes) e em `pgcode` no psycopg2 (produção)."""
    causa = Exception("erro do banco")
    setattr(causa, atributo, sqlstate)
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
        ],
    )
    def test_o_que_cada_operacao_faz_com_o_hash(self, operacao, gcal_status, esperado):
        """Publicar e reenviar zeram (o envio é forçado); cancelar mantém; reaplicar mantém só o de linha
        PUBLISHED, que é o que deixa o envio sem mudança virar SKIP. Reaplicar sobre linha em PENDING é recusado
        (teste de baixo)."""
        from apps.core.services.solicitacao_publish import pedir_operacao_gcal

        sol = _evento(gcal_status=gcal_status, external_event_id="evt-hash", gcal_payload_hash=_HASH)

        pedir_operacao_gcal(sol.pk, operacao)

        linha = _linha(sol)
        assert linha["gcal_payload_hash"] == esperado
        assert linha["gcal_status"] == Solicitacao.GCalStatus.PENDING

    @pytest.mark.parametrize("em_andamento", ["reaplicar", "cancelar"])
    def test_reaplicar_sobre_operacao_em_andamento_e_recusado_sem_gravar(self, em_andamento):
        """Um 2º Reaplicar antes de a tarefa do 1º rodar (duplo clique, linha "Publicando…" marcada de novo, id
        repetido no lote) ou um Reaplicar por cima de um "Tirar do Google" que ainda não rodou. Relida sob a
        trava, a linha está em PENDING: o pedido é recusado antes de gravar. Antes, ele zerava o hash, e a tarefa
        mandava o UPDATE ao Google (com e-mail aos convidados) sem mudança nenhuma, ou desfazia o cancelamento."""
        from apps.core.services.solicitacao_publish import pedir_operacao_gcal

        sol = _evento(gcal_status="PUBLISHED", external_event_id="evt-andamento", gcal_payload_hash=_HASH)
        primeiro = pedir_operacao_gcal(sol.pk, em_andamento)
        antes = _linha(sol)

        with pytest.raises(ConflictError) as erro:
            pedir_operacao_gcal(sol.pk, "reaplicar")

        assert erro.value.details == {"code": "operacao_em_andamento"}
        assert erro.value.message == (
            "Este evento já tem uma operação no Google em andamento. Espere alguns minutos; se não terminar, siga "
            "«Evento parado em Publicando…» no GUIDE_GCAL (não reenvie se foi um Tirar do Google)."
        )
        assert _linha(sol) == antes
        assert (antes["gcal_pedido"], antes["gcal_payload_hash"]) == (primeiro, _HASH)

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

    @pytest.mark.parametrize("atributo", ["sqlstate", "pgcode"], ids=["psycopg3", "psycopg2"])
    def test_trava_ocupada_alem_do_teto_vira_conflito_com_o_texto_da_edicao(self, atributo):
        """55P03 (lock_not_available): o pedido desiste com o mesmo texto da edição (DEF-30), sem tocar a linha.
        Vale para os dois drivers: a corrida real deste arquivo roda no psycopg 3, e a produção usa o psycopg2."""
        from apps.core.services.solicitacao_publish import pedir_operacao_gcal
        from apps.core.views_solicitacao import SolicitacaoViewSet

        sol = _evento()
        antes = _linha(sol)

        with (
            patch.object(Solicitacao.objects, "select_for_update", side_effect=_erro_do_banco("55P03", atributo)),
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


@pytest.mark.django_db(transaction=True)
def test_teto_de_espera_do_pedido_vale_so_na_transacao_dele():
    """O teto de 10 s é local à transação do pedido (`set_config(..., true)`). Em produção a conexão é
    reaproveitada (CONN_MAX_AGE): um teto de sessão sobraria para as próximas esperas de trava daquela thread do
    gunicorn, que desistiriam em 10 s com um 55P03 que ninguém trata."""
    from apps.core.services.solicitacao_publish import pedir_operacao_gcal

    def teto_da_conexao() -> str:
        with connection.cursor() as cursor:
            cursor.execute("SHOW lock_timeout")
            return cursor.fetchone()[0]

    sol = _evento()
    antes = teto_da_conexao()
    assert antes != "10s", "o teste só prova algo se a conexão não começar com o teto do pedido"

    with transaction.atomic():
        pedir_operacao_gcal(sol.pk, "publicar")

    assert _linha(sol)["gcal_status"] == _PENDING
    assert teto_da_conexao() == antes


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
    """O `.delay` falha porque a fila recusou a tarefa: a transação do pedido desfaz e a linha fica como estava,
    com o mesmo identificador. Antes, o PENDING já estava gravado e não havia tarefa para tirá-lo de lá."""
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


@pytest.mark.django_db(transaction=True)
def test_erro_do_delay_que_nao_e_da_fila_sobe_e_desfaz_o_pedido(settings):
    """Só erro do broker vira 503 "fila indisponível". Um erro de código no `.delay` (aqui, a assinatura da
    tarefa trocada) sobe e a resposta é 500: o atomic da entrada desfaz o pedido, e a linha fica como estava.
    Antes, ele também virava 503, e o guia mandava esperar o Redis voltar com o Redis de pé."""
    settings.GCAL_CLIENT = "google"
    sol = _evento()
    antes = _linha(sol)

    with patch(_DELAY_PUBLICAR, side_effect=TypeError("unexpected keyword argument 'pedido'")) as delay:
        resposta = _api(raise_request_exception=False).post(f"/api/solicitacoes/{sol.pk}/publish/", {}, format="json")

    delay.assert_called_once()
    assert resposta.status_code == 500
    assert _linha(sol) == antes
    assert not _pediu(sol, "PUBLISH_GCAL_REQUESTED")


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


# =============================================================================
# Só as entradas enfileiram publicar e cancelar
# =============================================================================

_APPS = Path(__file__).resolve().parents[2]
_TAREFAS_COM_PEDIDO = (
    "task_publish_solicitacao_to_gcal",
    "task_cancel_solicitacao_from_gcal",
    "task_cancelar_na_agenda",
)
_QUEM_ENFILEIRA = {"core/services/solicitacao_publish.py", "core/views_gcal/batch.py", "core/tasks.py"}


def _mencoes_fora_da_lista(apps: Path) -> list[str]:
    """Arquivos de `apps/` (fora de `tests/` e de `_QUEM_ENFILEIRA`) que citam uma das duas tarefas."""
    achados: list[str] = []
    for arquivo in sorted(apps.rglob("*.py")):
        relativo = arquivo.relative_to(apps).as_posix()
        if "tests" in relativo.split("/") or relativo in _QUEM_ENFILEIRA:
            continue
        texto = arquivo.read_text(encoding="utf-8")
        achados += [f"{relativo}: {tarefa}" for tarefa in _TAREFAS_COM_PEDIDO if tarefa in texto]
    return achados


def test_a_varredura_acha_quem_enfileira_por_fora(tmp_path):
    """Prova de que a sentinela de baixo dispara: um módulo que enfileira por conta própria é achado; os
    testes e os arquivos da lista não."""
    (tmp_path / "core" / "services").mkdir(parents=True)
    (tmp_path / "core" / "tests").mkdir()
    (tmp_path / "core" / "services" / "atalho.py").write_text(
        "from apps.core.tasks import task_publish_solicitacao_to_gcal\n\ntask_publish_solicitacao_to_gcal.delay(1)\n",
        encoding="utf-8",
    )
    (tmp_path / "core" / "tests" / "test_x.py").write_text("task_cancel_solicitacao_from_gcal.delay(1)\n")
    (tmp_path / "core" / "tasks.py").write_text("def task_cancel_solicitacao_from_gcal(): ...\n")

    assert _mencoes_fora_da_lista(tmp_path) == ["core/services/atalho.py: task_publish_solicitacao_to_gcal"]


def test_so_as_entradas_enfileiram_publicar_e_cancelar():
    """Quem enfileira uma destas tarefas por fora pula o pedido: a linha fica sem identificador novo, a
    tarefa não age (ou age sobre o pedido de outro) e o PENDING não fica preso à transação da fila. Por isso
    nenhum outro arquivo de `apps/` sequer cita as tarefas: quem precisa publicar, tirar do Google ou cancelar na
    agenda chama `publish_to_gcal`, `resync_to_gcal`, `cancel_from_gcal`, `cancelar_na_agenda` ou os lotes."""
    assert _mencoes_fora_da_lista(_APPS) == []


# =============================================================================
# Corridas reais: duas conexões, banco de verdade, sem sleep fixo
# =============================================================================


def _esperar_alguem_esperando_trava(quem: str, timeout: float = 15.0) -> None:
    """Polling em `pg_stat_activity` até outra conexão deste banco estar parada esperando uma trava."""
    limite = time.monotonic() + timeout
    with connection.cursor() as cursor:
        while time.monotonic() < limite:
            cursor.execute("""
                SELECT count(*) FROM pg_stat_activity
                WHERE datname = current_database() AND wait_event_type = 'Lock' AND pid <> pg_backend_pid()
                """)
            if cursor.fetchone()[0]:
                return
            time.sleep(0.02)
    pytest.fail(f"{quem} não chegou a esperar a trava da linha")


@pytest.mark.django_db(transaction=True)
def test_publicar_espera_a_edicao_que_segura_a_linha_e_rele_o_evento_rebaixado(settings):
    """A edição segura a linha e, ao salvar, devolve o evento para aprovação. O "Publicar" que chega nesse
    meio lê `aprovado` sem trava, espera a edição no pedido, relê `pendente` e é recusado.

    Antes: o PENDING era gravado por cima do evento rebaixado e a tarefa ia para a fila."""
    settings.GCAL_CLIENT = "google"
    sol = _evento()
    api = _api()
    travou, liberar = threading.Event(), threading.Event()

    def edicao_que_rebaixa():
        try:
            with transaction.atomic():
                linha = Solicitacao.objects.select_for_update().get(pk=sol.pk)
                travou.set()
                if not liberar.wait(timeout=30):
                    raise TimeoutError("o teste não liberou a edição")
                linha.status = "pendente"
                linha.save(update_fields=["status"])
        finally:
            connection.close()

    def publicar():
        try:
            return api.post(f"/api/solicitacoes/{sol.pk}/publish/", {}, format="json")
        finally:
            connection.close()

    with patch(_DELAY_PUBLICAR) as delay, ThreadPoolExecutor(max_workers=2) as executor:
        delay.return_value.id = "tarefa-indevida"
        futuro_edicao = executor.submit(edicao_que_rebaixa)
        futuro_publicar = None
        try:
            assert travou.wait(timeout=15), "a edição não chegou a travar a linha"
            futuro_publicar = executor.submit(publicar)
            _esperar_alguem_esperando_trava("o pedido de publicar")
        finally:
            liberar.set()
        futuro_edicao.result(timeout=30)
        assert futuro_publicar is not None
        resposta = futuro_publicar.result(timeout=30)

    assert resposta.status_code == 400, f"esperado 400, obteve {resposta.status_code}: {resposta.data}"
    assert resposta.data["code"] == "not_approved"
    delay.assert_not_called()
    linha = Solicitacao.objects.filter(pk=sol.pk).values("status", "gcal_status", "gcal_pedido").get()
    assert linha == {"status": "pendente", "gcal_status": "NONE", "gcal_pedido": ""}


@pytest.mark.django_db(transaction=True)
@_TRES_ENTRADAS
def test_pedido_que_espera_alem_do_teto_desiste_sem_tocar_a_linha(entrada, settings, monkeypatch):
    """Outra operação segura a linha por mais que o teto (encurtado aqui): o pedido desiste com 409
    `linha_ocupada` e "tente de novo", em vez de prender a thread do gunicorn até o statement_timeout."""
    from apps.core.services import solicitacao_publish

    monkeypatch.setattr(solicitacao_publish, "_PEDIDO_LOCK_TIMEOUT", "200ms")
    settings.GCAL_CLIENT = "google"
    dados = _ENTRADAS[entrada]
    sol = _evento(**dados["estado"])
    antes = _linha(sol)
    api = _api()
    travou, liberar = threading.Event(), threading.Event()

    def outra_operacao_segura_a_linha():
        try:
            with transaction.atomic():
                Solicitacao.objects.select_for_update().get(pk=sol.pk)
                travou.set()
                liberar.wait(timeout=5)
        finally:
            connection.close()

    with patch(dados["delay"]) as delay, ThreadPoolExecutor(max_workers=1) as executor:
        delay.return_value.id = "tarefa-indevida"
        futuro = executor.submit(outra_operacao_segura_a_linha)
        try:
            assert travou.wait(timeout=15), "a outra operação não chegou a travar a linha"
            resposta = api.post(f"/api/solicitacoes/{sol.pk}/{dados['rota']}/", {}, format="json")
        finally:
            liberar.set()
        futuro.result(timeout=30)

    assert resposta.status_code == 409, f"esperado 409, obteve {resposta.status_code}: {resposta.data}"
    assert resposta.data["errors"]["code"] == "linha_ocupada"
    assert "Tente de novo" in resposta.data["detail"]
    delay.assert_not_called()
    assert _linha(sol) == antes
    assert not _pediu(sol, dados["acao"])


class _EntradaDesfeita(Exception):
    """Faz a transação da entrada desfazer (como a fila fora do ar faz)."""


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("desfecho, acao", [("commit", "CREATE"), ("rollback", "SKIP")])
def test_tarefa_que_chega_antes_do_fim_do_pedido_espera_a_trava(desfecho, acao, settings, monkeypatch):
    """O worker pode pegar a mensagem antes de a entrada commitar (o `.delay` roda dentro da transação). A
    tarefa espera no FOR UPDATE: se a entrada commita, acha o pedido dela e publica; se a entrada desfaz, a
    linha volta a ser a de antes, o identificador não confere e a tarefa não faz nada."""
    from apps.core.services import gcal_client_factory
    from apps.core.services.gcal import sync as sync_mod
    from apps.core.services.gcal_fake_client import FakeCalendarClient
    from apps.core.services.solicitacao_publish import pedir_operacao_gcal
    from apps.core.tasks import task_publish_solicitacao_to_gcal

    settings.GCAL_AUTH_MODE = "service_account"
    settings.GCAL_CLIENT = "fake"
    fake = FakeCalendarClient()
    monkeypatch.setattr(gcal_client_factory, "get_gcal_client_and_calendar_id", lambda: (fake, "primary"))
    monkeypatch.setattr(sync_mod, "_retry_with_circuit_breaker", lambda f, **_: f())
    sol = _evento()
    antes = _linha(sol)
    pedido = {}
    pediu, liberar = threading.Event(), threading.Event()

    def entrada():
        try:
            with transaction.atomic():
                pedido["id"] = pedir_operacao_gcal(sol.pk, "publicar")
                pediu.set()
                if not liberar.wait(timeout=30):
                    raise TimeoutError("o teste não liberou a entrada")
                if desfecho == "rollback":
                    raise _EntradaDesfeita
        except _EntradaDesfeita:
            pass
        finally:
            connection.close()

    def tarefa():
        try:
            return task_publish_solicitacao_to_gcal(sol.pk, pedido=pedido["id"])
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futuro_entrada = executor.submit(entrada)
        futuro_tarefa = None
        try:
            assert pediu.wait(timeout=15), "a entrada não chegou a fazer o pedido"
            futuro_tarefa = executor.submit(tarefa)
            _esperar_alguem_esperando_trava("a tarefa")
        finally:
            liberar.set()
        futuro_entrada.result(timeout=30)
        assert futuro_tarefa is not None
        resultado = futuro_tarefa.result(timeout=30)

    assert resultado["action"] == acao, resultado
    if desfecho == "commit":
        assert fake.get("primary", f"asv2{sol.pk}")["status"] == "confirmed"
        linha = _linha(sol)
        assert (linha["gcal_status"], linha["gcal_pedido"]) == ("PUBLISHED", pedido["id"])
    else:
        assert fake.list_events("primary") == []
        assert _linha(sol) == antes


@pytest.mark.django_db(transaction=True)
def test_duas_entregas_do_mesmo_pedido_chamam_o_google_uma_vez(settings, monkeypatch):
    """A mesma mensagem é entregue duas vezes ao mesmo tempo (por exemplo, a conexão do worker com o Redis caiu e
    a mensagem voltou enquanto a primeira entrega rodava). A segunda espera a trava da primeira, acha a linha fora
    de PENDING e devolve SKIP: sem chamar a Agenda do Google, sem AuditLog e sem gravar. Este teste cobre a primeira
    entrega que commita; se o processo dela morresse entre o Google e o commit, a segunda escreveria de novo no
    mesmo evento."""
    from apps.core.services import gcal_client_factory
    from apps.core.services.gcal import sync as sync_mod
    from apps.core.services.gcal_fake_client import FakeCalendarClient
    from apps.core.services.solicitacao_publish import pedir_operacao_gcal
    from apps.core.tasks import task_publish_solicitacao_to_gcal

    class GoogleQuePrendeNoInsert(FakeCalendarClient):
        """Registra cada chamada; o insert avisa que chegou (`travou`) e só responde após `liberar`."""

        def __init__(self):
            super().__init__()
            self.chamadas = []
            self.travou = threading.Event()
            self.liberar = threading.Event()

        def get(self, calendar_id, event_id):
            self.chamadas.append("get")
            return super().get(calendar_id, event_id)

        def insert(self, calendar_id, event_id, payload):
            self.chamadas.append("insert")
            self.travou.set()
            if not self.liberar.wait(timeout=30):
                raise TimeoutError("o teste não liberou o insert")
            return super().insert(calendar_id, event_id, payload)

        def update(self, calendar_id, event_id, payload):
            self.chamadas.append("update")
            return super().update(calendar_id, event_id, payload)

    settings.GCAL_AUTH_MODE = "service_account"
    settings.GCAL_CLIENT = "fake"
    google = GoogleQuePrendeNoInsert()
    monkeypatch.setattr(gcal_client_factory, "get_gcal_client_and_calendar_id", lambda: (google, "primary"))
    monkeypatch.setattr(sync_mod, "_retry_with_circuit_breaker", lambda f, **_: f())
    sol = _evento()
    with transaction.atomic():
        pedido = pedir_operacao_gcal(sol.pk, "publicar")

    def entregar():
        try:
            return task_publish_solicitacao_to_gcal(sol.pk, pedido=pedido)
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        primeira = executor.submit(entregar)
        segunda = None
        try:
            assert google.travou.wait(timeout=15), "a primeira entrega não chegou ao insert do Google"
            segunda = executor.submit(entregar)
            _esperar_alguem_esperando_trava("a segunda entrega")
        finally:
            google.liberar.set()
        resultados = [primeira.result(timeout=30)]
        assert segunda is not None
        resultados.append(segunda.result(timeout=30))

    assert [r["action"] for r in resultados] == ["CREATE", "SKIP"], resultados
    assert google.chamadas == ["get", "insert"]
    assert AuditLog.objects.filter(action="PUBLISH_GCAL", details__solicitacao_id=sol.pk).count() == 1
    linha = _linha(sol)
    assert (linha["gcal_status"], linha["gcal_pedido"]) == ("PUBLISHED", pedido)

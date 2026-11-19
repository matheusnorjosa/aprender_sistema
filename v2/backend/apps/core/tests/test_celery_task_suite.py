"""
Celery task test suite — validates task execution, retry, and error handling.

Tests use celery.contrib.pytest fixtures for realistic task execution
(not CELERY_TASK_ALWAYS_EAGER which hides real issues).

Refs: Issue #846, TESTING_POLICY.md
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

import logging
from datetime import timedelta
from functools import partial
from unittest.mock import patch
from uuid import uuid4

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

import pytest

from apps.core.models import AuditLog, Solicitacao
from apps.core.tests.factories import (
    GroupFactory,
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def task_solicitacao(db):
    """Create a published solicitacao for task tests."""
    uid = uuid4().hex[:8]
    user = UsuarioFactory(
        username=f"task_user_{uid}",
        email=f"task_{uid}@test.com",
        password="testpass",
        cpf=f"888{uid.ljust(8, '0')}",
    )
    GroupFactory(name="Controle")
    municipio = MunicipioFactory(nome=f"TaskCity_{uid}", uf="CE")
    projeto = ProjetoFactory(nome=f"TaskProj_{uid}", fluxo="SUPER")
    tipo = TipoEventoFactory(nome=f"TaskType_{uid}")

    now = timezone.now()
    sol = SolicitacaoFactory(
        usuario=user,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo,
        inicio=now + timedelta(days=1),
        fim=now + timedelta(days=1, hours=2),
        status="aprovado",
        gcal_status=Solicitacao.GCalStatus.PUBLISHED,
        external_event_id=f"asv2task{uid}",
    )
    return sol


class TestPublishTask:
    """Tests for task_publish_solicitacao_to_gcal."""

    def test_publish_task_returns_outcome_dict(self, task_solicitacao):
        """Task returns dict with action, solicitation_id, etc."""
        from apps.core.tasks import task_publish_solicitacao_to_gcal

        # Reset to approved (not published) for publish test
        task_solicitacao.gcal_status = Solicitacao.GCalStatus.NONE
        task_solicitacao.external_event_id = None
        task_solicitacao.save()

        with patch("apps.core.services.gcal_sync_service.apply_one_solicitacao") as mock_apply:
            from apps.core.services.gcal.sync import SyncOutcome

            mock_apply.return_value = SyncOutcome(
                action="CREATE",
                solicitation_id=task_solicitacao.id,
                external_event_id=f"asv2{task_solicitacao.id}",
                summary=f"Solicitação #{task_solicitacao.id}",
            )

            result = task_publish_solicitacao_to_gcal(task_solicitacao.id, dry_run=True)

            assert result["action"] == "CREATE"
            assert result["solicitation_id"] == task_solicitacao.id
            assert result["error"] is None

    def test_publish_task_handles_not_found(self):
        """Task returns ERROR dict when solicitacao doesn't exist."""
        from apps.core.tasks import task_publish_solicitacao_to_gcal

        result = task_publish_solicitacao_to_gcal(999999, dry_run=True)

        assert result["action"] == "ERROR"
        assert "999999" in result["summary"]

    def test_publish_task_usa_select_for_update(self, task_solicitacao):
        """#1726: a task deve reler a Solicitacao com select_for_update() (dentro de atomic())
        antes de mutar/persistir — evita lost-update entre publish/cancel concorrentes do
        mesmo evento.

        RED: hoje a task faz `Solicitacao.objects.get(id=...)` puro (sem lock).
        """
        from apps.core.services.gcal.sync import SyncOutcome
        from apps.core.tasks import task_publish_solicitacao_to_gcal

        task_solicitacao.gcal_status = Solicitacao.GCalStatus.NONE
        task_solicitacao.external_event_id = None
        task_solicitacao.save()

        with (
            patch("apps.core.services.gcal_sync_service.apply_one_solicitacao") as mock_apply,
            patch.object(
                Solicitacao.objects, "select_for_update", wraps=Solicitacao.objects.select_for_update
            ) as spy_lock,
        ):
            mock_apply.return_value = SyncOutcome(
                action="CREATE",
                solicitation_id=task_solicitacao.id,
                external_event_id=f"asv2{task_solicitacao.id}",
                summary=f"Solicitação #{task_solicitacao.id}",
            )
            # Publicação real: é ela que persiste. A prévia não trava a linha (#2068,
            # test_so_a_publicacao_real_trava_a_linha_da_solicitacao cobre os dois lados).
            result = task_publish_solicitacao_to_gcal(task_solicitacao.id, dry_run=False)

        assert result["error"] is None
        spy_lock.assert_called()  # a task travou a linha antes de operar


class TestCancelTask:
    """Tests for task_cancel_solicitacao_from_gcal."""

    def test_cancel_task_returns_outcome(self, task_solicitacao):
        """Task returns DELETE action on success."""
        from apps.core.tasks import task_cancel_solicitacao_from_gcal

        with patch("apps.core.services.gcal_sync_service.cancel_solicitacao") as mock_cancel:
            from apps.core.services.gcal.sync import SyncOutcome

            mock_cancel.return_value = SyncOutcome(
                action="DELETE",
                solicitation_id=task_solicitacao.id,
                external_event_id=None,
                summary=f"Solicitação #{task_solicitacao.id} (cancelada)",
            )

            result = task_cancel_solicitacao_from_gcal(task_solicitacao.id)

            assert result["action"] == "DELETE"
            assert result["error"] is None

    def test_cancel_task_usa_select_for_update(self, task_solicitacao):
        """#1726: idem publish — a task de cancel deve travar a linha (select_for_update
        dentro de atomic()) antes de deletar o evento e limpar os campos de sync.

        RED: hoje faz `Solicitacao.objects.get(id=...)` puro (sem lock).
        """
        from apps.core.services.gcal.sync import SyncOutcome
        from apps.core.tasks import task_cancel_solicitacao_from_gcal

        with (
            patch("apps.core.services.gcal_sync_service.cancel_solicitacao") as mock_cancel,
            patch.object(
                Solicitacao.objects, "select_for_update", wraps=Solicitacao.objects.select_for_update
            ) as spy_lock,
        ):
            mock_cancel.return_value = SyncOutcome(
                action="DELETE",
                solicitation_id=task_solicitacao.id,
                external_event_id=None,
                summary=f"Solicitação #{task_solicitacao.id} (cancelada)",
            )
            result = task_cancel_solicitacao_from_gcal(task_solicitacao.id)

        assert result["error"] is None
        spy_lock.assert_called()

    def test_cancel_task_creates_audit_log(self, task_solicitacao):
        """Task creates AuditLog entry on success."""
        from apps.core.tasks import task_cancel_solicitacao_from_gcal

        with patch("apps.core.services.gcal_sync_service.cancel_solicitacao") as mock_cancel:
            from apps.core.services.gcal.sync import SyncOutcome

            mock_cancel.return_value = SyncOutcome(
                action="DELETE",
                solicitation_id=task_solicitacao.id,
                external_event_id=None,
                summary="cancelled",
            )

            task_cancel_solicitacao_from_gcal(task_solicitacao.id)

            audit = AuditLog.objects.filter(
                action="CANCEL_GCAL",
                details__solicitacao_id=task_solicitacao.id,
            ).first()
            assert audit is not None

    def test_cancel_task_handles_not_found(self):
        """Task returns ERROR when solicitacao doesn't exist."""
        from apps.core.tasks import task_cancel_solicitacao_from_gcal

        result = task_cancel_solicitacao_from_gcal(999999)

        assert result["action"] == "ERROR"
        assert result["error"] == "DoesNotExist"

    def test_cancel_task_handles_exception(self, task_solicitacao):
        """Task returns ERROR on unexpected exception."""
        from apps.core.tasks import task_cancel_solicitacao_from_gcal

        with patch("apps.core.services.gcal_sync_service.cancel_solicitacao") as mock_cancel:
            mock_cancel.side_effect = RuntimeError("GCal API down")

            result = task_cancel_solicitacao_from_gcal(task_solicitacao.id)

            assert result["action"] == "ERROR"
            assert "GCal API down" in result["error"]


_APPLY = "apps.core.services.gcal_sync_service.apply_one_solicitacao"
_CAMPOS_GCAL = ("gcal_status", "gcal_payload_hash", "gcal_last_error", "gcal_last_sync_at")


def _estado_gcal(sol):
    return Solicitacao.objects.filter(pk=sol.pk).values(*_CAMPOS_GCAL).get()


def _travou_a_solicitacao(consultas) -> bool:
    return any("FOR UPDATE" in q["sql"] and 'FROM "core_solicitacao"' in q["sql"] for q in consultas)


def _sincronizou(sol):
    from apps.core.services.gcal.sync import SyncOutcome

    return SyncOutcome(
        action="UPDATE",
        solicitation_id=sol.id,
        external_event_id=sol.external_event_id,
        summary=f"Solicitação #{sol.id}",
    )


def _grava_e_levanta(erro):
    """Imita o apply_one_solicitacao que falha: marca ERROR na linha e relança."""

    def aplicar(s, **_kwargs):
        s.mark_gcal(status=Solicitacao.GCalStatus.ERROR, error="gravação parcial")
        raise erro

    return aplicar


_ERRO_DO_PUBLISH = "O Google Agenda falhou várias vezes seguidas."


@pytest.fixture
def retry_solicitacao(task_solicitacao):
    """O estado em que a nova tentativa roda: o publish caiu no breaker aberto, enfileirou a tentativa e marcou ERROR
    (`_mark_gcal_error`), mantendo o external_event_id."""
    task_solicitacao.mark_gcal(status=Solicitacao.GCalStatus.ERROR, payload_hash=None, error=_ERRO_DO_PUBLISH)
    return task_solicitacao


class TestGcalSyncRetryTask:
    """ART-01: a nova tentativa depois do circuit breaker aberto (queue_gcal_sync_retry) grava como o
    publish e o cancel do #1726: linha travada dentro de atomic(), com o except fora do bloco. Sob a trava,
    ela só segue se a linha continua em ERROR, o estado que o publish deixou ao enfileirá-la."""

    @pytest.mark.parametrize("dry_run", [True, False], ids=["previa", "publicacao"])
    def test_retry_trava_a_linha_so_fora_do_dry_run(self, retry_solicitacao, dry_run):
        """A prévia não escreve na linha e não trava, como no publish.

        RED (publicacao): antes do ART-01 a task fazia `Solicitacao.objects.get(id=...)` puro, fora de atomic().
        Este teste só vê o FOR UPDATE no SQL; que a trava dura a chamada ao Google é o TestTravaDuraAChamadaAoGoogle.
        """
        from apps.core.tasks import queue_gcal_sync_retry

        with (
            patch(_APPLY, return_value=_sincronizou(retry_solicitacao)),
            CaptureQueriesContext(connection) as consultas,
        ):
            resultado = queue_gcal_sync_retry(retry_solicitacao.id, dry_run=dry_run)

        assert resultado["error"] is None
        assert _travou_a_solicitacao(consultas.captured_queries) is not dry_run

    def test_retry_confere_o_erro_na_linha_travada(self, retry_solicitacao):
        """A conferência do ERROR é feita na linha travada (revisão do DEF-16, R2T-1). Simula o cancel que termina
        entre uma leitura sem trava e o FOR UPDATE: logo antes do SELECT ... FOR UPDATE, a mesma conexão grava o
        estado que o cancel deixa. Quem conferisse antes da trava veria ERROR e traria o evento de volta ao Google.
        """
        from apps.core.tasks import queue_gcal_sync_retry

        def cancel_termina_antes_da_trava(execute, sql, params, many, context):
            if _travou_a_solicitacao([{"sql": sql}]):
                Solicitacao.objects.filter(pk=retry_solicitacao.pk).update(
                    gcal_status=Solicitacao.GCalStatus.NONE, external_event_id=None
                )
            return execute(sql, params, many, context)

        with connection.execute_wrapper(cancel_termina_antes_da_trava), patch(_APPLY) as aplicar:
            resultado = queue_gcal_sync_retry(retry_solicitacao.id)

        aplicar.assert_not_called()
        assert resultado["action"] == "SKIP"

    @pytest.mark.parametrize(
        "gcal_status, external_event_id",
        [
            (Solicitacao.GCalStatus.NONE, None),
            (Solicitacao.GCalStatus.PUBLISHED, "asv2outro"),
            (Solicitacao.GCalStatus.PENDING, "asv2outro"),
        ],
        ids=["tirado_do_google", "outro_publish_ja_fez", "publish_ou_cancel_mais_novo_na_fila"],
    )
    def test_retry_nao_age_se_a_linha_mudou_desde_a_falha(self, retry_solicitacao, gcal_status, external_event_id):
        """CT-01 da revisão: a tentativa roda 60 s ou mais depois da falha. Se, sob a trava, a linha já não está em
        ERROR, alguém agiu depois: tirou do Google, outro publish deu certo, ou há publish ou cancel mais novo na
        fila. Ela devolve SKIP sem chamar o Google e sem gravar nada.

        RED: a tentativa chamava o apply em qualquer estado e trazia de volta ao Google o evento tirado.
        """
        from apps.core.tasks import queue_gcal_sync_retry

        Solicitacao.objects.filter(pk=retry_solicitacao.pk).update(
            gcal_status=gcal_status, external_event_id=external_event_id
        )
        antes = _estado_gcal(retry_solicitacao)
        with patch(_APPLY) as aplicar:
            resultado = queue_gcal_sync_retry(retry_solicitacao.id)

        aplicar.assert_not_called()
        assert resultado["action"] == "SKIP"
        assert resultado["external_event_id"] == external_event_id
        assert resultado["error"] is None
        assert _estado_gcal(retry_solicitacao) == antes
        assert not AuditLog.objects.filter(details__solicitacao_id=retry_solicitacao.id).exists()

    def test_retry_atrasado_nao_traz_de_volta_o_evento_tirado_do_google(self, settings):
        """CT-01 de ponta a ponta, com o cliente fake: publicado → "Atualizar" cai no breaker aberto (a tentativa
        fica na fila e a linha em ERROR) → "Tirar do Google" apaga e desvincula → a tentativa roda.

        RED: a tentativa fazia ADOPT do evento apagado, que voltava a "confirmed" no Google, e a linha voltava a
        PUBLISHED. Latente em produção enquanto a tentativa não tem cliente OAuth (#2051).
        """
        from apps.core.services.gcal.circuit_breaker import gcal_breaker
        from apps.core.services.gcal_fake_client import FakeCalendarClient
        from apps.core.tasks import (
            queue_gcal_sync_retry,
            task_cancel_solicitacao_from_gcal,
            task_publish_solicitacao_to_gcal,
        )

        settings.GCAL_AUTH_MODE = "service_account"
        fabrica = "apps.core.services.gcal_client_factory.get_gcal_client_and_calendar_id"
        fake = FakeCalendarClient()
        agora = timezone.now()
        sol = SolicitacaoFactory(
            status="aprovado", inicio=agora + timedelta(days=2), fim=agora + timedelta(days=2, hours=2)
        )
        eid = f"asv2{sol.id}"

        def linha():
            return Solicitacao.objects.filter(pk=sol.pk).values("gcal_status", "external_event_id").get()

        with patch(fabrica, return_value=(fake, "primary")):
            assert task_publish_solicitacao_to_gcal(sol.id)["action"] == "CREATE"
            # "Atualizar" pela tela marca PENDING; o publish cai no breaker aberto e enfileira a tentativa.
            Solicitacao.objects.get(pk=sol.pk).mark_gcal(status=Solicitacao.GCalStatus.PENDING, error="")
            gcal_breaker.open()
            try:
                with patch.object(queue_gcal_sync_retry, "apply_async") as enfileirou:
                    assert task_publish_solicitacao_to_gcal(sol.id)["action"] == "ERROR"
            finally:
                gcal_breaker.close()
            enfileirou.assert_called_once()
            assert linha() == {"gcal_status": "ERROR", "external_event_id": eid}
            # "Tirar do Google": a tela marca PENDING; a task apaga o evento e desvincula a linha.
            Solicitacao.objects.get(pk=sol.pk).mark_gcal(status=Solicitacao.GCalStatus.PENDING, error="")
            assert task_cancel_solicitacao_from_gcal(sol.id)["action"] == "DELETE"
            assert fake.get("primary", eid)["status"] == "cancelled"

            resultado = queue_gcal_sync_retry(sol.id)

        assert resultado["action"] == "SKIP"
        assert fake.get("primary", eid)["status"] == "cancelled"
        assert linha() == {"gcal_status": "NONE", "external_event_id": None}
        assert not AuditLog.objects.filter(
            action=AuditLog.Action.GCAL_RETRY_SUCCESS, details__solicitacao_id=sol.id
        ).exists()

    def test_retry_que_da_certo_grava_o_audit_log(self, retry_solicitacao):
        from apps.core.tasks import queue_gcal_sync_retry

        with patch(_APPLY, return_value=_sincronizou(retry_solicitacao)):
            resultado = queue_gcal_sync_retry(retry_solicitacao.id)

        assert resultado == {
            "action": "UPDATE",
            "solicitation_id": retry_solicitacao.id,
            "external_event_id": retry_solicitacao.external_event_id,
            "summary": f"Solicitação #{retry_solicitacao.id}",
            "retry_attempt": 1,
            "error": None,
        }
        audit = AuditLog.objects.get(
            action=AuditLog.Action.GCAL_RETRY_SUCCESS, details__solicitacao_id=retry_solicitacao.id
        )
        assert audit.details == {
            "solicitacao_id": retry_solicitacao.id,
            "action": "UPDATE",
            "external_event_id": retry_solicitacao.external_event_id,
            "retry_attempt": 1,
        }

    def test_retry_de_solicitacao_que_sumiu_devolve_does_not_exist(self):
        from apps.core.tasks import queue_gcal_sync_retry

        assert queue_gcal_sync_retry(999_999_999) == {
            "action": "ERROR",
            "solicitation_id": 999_999_999,
            "external_event_id": None,
            "summary": "Solicitação #999999999 não encontrada",
            "error": "DoesNotExist",
        }

    def test_retry_que_falha_desfaz_a_gravacao_parcial_e_registra_o_erro(self, retry_solicitacao):
        """O except roda fora do bloco e devolve o mesmo ERROR de antes. O rollback desfaz o que o
        apply_one_solicitacao gravou antes de levantar, e a linha fica como o publish a deixou: o except não
        remarca, porque fora da trava a marca poderia apagar o PUBLISHED de um publish concorrente. O erro novo
        vai para o AuditLog `PUBLISH_GCAL_ERROR` (operation `retry`), que não toca a linha.

        RED: antes do ART-01 a gravação parcial ficava; antes deste ajuste a falha só ia para o log.
        """
        from apps.core.tasks import queue_gcal_sync_retry

        antes = _estado_gcal(retry_solicitacao)
        with patch(_APPLY, side_effect=_grava_e_levanta(RuntimeError("Google fora do ar"))):
            resultado = queue_gcal_sync_retry(retry_solicitacao.id)

        assert resultado == {
            "action": "ERROR",
            "solicitation_id": retry_solicitacao.id,
            "external_event_id": None,
            "summary": "Erro ao sincronizar: Google fora do ar",
            "error": "Google fora do ar",
        }
        assert _estado_gcal(retry_solicitacao) == antes
        assert antes["gcal_last_error"] == _ERRO_DO_PUBLISH
        registro = AuditLog.objects.get(
            action=AuditLog.Action.PUBLISH_GCAL_ERROR, details__solicitacao_id=retry_solicitacao.id
        )
        assert registro.usuario is None
        assert registro.details == {
            "solicitacao_id": retry_solicitacao.id,
            "operation": "retry",
            "error": "Google fora do ar",
            "dry_run": False,
            "apply_blocked": False,
        }

    def test_retry_que_falha_sem_conseguir_registrar_devolve_o_erro(self, retry_solicitacao, caplog):
        """Se o registro da falha também falha (banco fora do ar), a task devolve o ERROR de sempre em vez de
        levantar (revisão do DEF-16, R2C-6).

        RED: o AuditLog do except não tinha try, e o DatabaseError subia.
        """
        from django.db import DatabaseError

        from apps.core.tasks import queue_gcal_sync_retry

        with (
            caplog.at_level(logging.ERROR, logger="apps.core.tasks"),
            patch(_APPLY, side_effect=_grava_e_levanta(RuntimeError("Google fora do ar"))),
            patch.object(AuditLog.objects, "create", side_effect=DatabaseError("banco fora do ar")),
        ):
            resultado = queue_gcal_sync_retry(retry_solicitacao.id)

        assert resultado["action"] == "ERROR"
        assert resultado["error"] == "Google fora do ar"
        assert any(
            r.name == "apps.core.tasks" and r.exc_info and isinstance(r.exc_info[1], DatabaseError)
            for r in caplog.records
        ), "a falha do registro não foi para o log"

    def test_retry_com_breaker_aberto_desfaz_a_gravacao_parcial_e_pede_nova_tentativa(self, retry_solicitacao):
        """CircuitBreakerError segue pedindo nova tentativa em 60 s, sem deixar gravação parcial nem registro de
        erro (a tentativa ainda vai rodar de novo).

        RED: antes do ART-01 a task rodava fora de atomic() e a gravação parcial ficava.
        """
        from celery.exceptions import Retry

        from apps.core.services.gcal.circuit_breaker import CircuitBreakerError, gcal_breaker
        from apps.core.tasks import queue_gcal_sync_retry

        erro = CircuitBreakerError(gcal_breaker)
        antes = _estado_gcal(retry_solicitacao)
        with (
            patch(_APPLY, side_effect=_grava_e_levanta(erro)),
            patch.object(queue_gcal_sync_retry, "retry", side_effect=Retry()) as nova_tentativa,
            pytest.raises(Retry),
        ):
            queue_gcal_sync_retry(retry_solicitacao.id)

        nova_tentativa.assert_called_once_with(countdown=60, exc=erro)
        assert _estado_gcal(retry_solicitacao) == antes
        assert not AuditLog.objects.filter(
            action=AuditLog.Action.PUBLISH_GCAL_ERROR, details__solicitacao_id=retry_solicitacao.id
        ).exists()


_CANCEL = "apps.core.services.gcal_sync_service.cancel_solicitacao"


def _rodar_e_guardar_os_atomics(chamar_task, alvo, resposta):
    """Roda a task e guarda a pilha de blocos atomic em dois momentos: no SELECT ... FOR UPDATE da Solicitacao e na
    chamada ao Google (o alvo do patch). Compara por identidade: um atomic(savepoint=False) entra na pilha de
    savepoints como None e não se distinguiria de outro (revisão do DEF-16, R2T-5). Guarda também os savepoints, que
    distinguem o mesmo objeto Atomic aberto duas vezes, e se a trava veio antes da chamada (R3-codigo-testes-1)."""
    blocos = {}

    def espiar(execute, sql, params, many, context):
        if "google" not in blocos and _travou_a_solicitacao([{"sql": sql}]):
            blocos["trava"] = list(connection.atomic_blocks)
            blocos["trava_sids"] = list(connection.savepoint_ids)
        return execute(sql, params, many, context)

    def chamar_o_google(*_args, **_kwargs):
        blocos["google"] = list(connection.atomic_blocks)
        blocos["google_sids"] = list(connection.savepoint_ids)
        blocos["travou_antes"] = "trava" in blocos
        return resposta

    fora = list(connection.atomic_blocks)
    fora_sids = list(connection.savepoint_ids)
    with connection.execute_wrapper(espiar), patch(alvo, side_effect=chamar_o_google):
        resultado = chamar_task()
    return fora, fora_sids, blocos, resultado


class TestTravaDuraAChamadaAoGoogle:
    """#1726 e ART-01: as 3 tasks do Google travam a linha num atomic aberto por elas e chamam o Google ainda dentro
    dele. O teste roda dentro da transação do pytest, onde nenhum FOR UPDATE se solta e o select_for_update nunca
    levanta; por isso compara a pilha de blocos atomic. Pega o que o teste do SQL não vê (revisão do DEF-16, F1 e
    R2T-2): travar num atomic que fecha antes da chamada ao Google, e a trava cai antes dela; e travar fora de atomic,
    que em produção dá TransactionManagementError. Um atomic interno em volta da chamada continua aceito."""

    @pytest.mark.parametrize("task", ["publish", "cancel", "retry"])
    def test_a_chamada_ao_google_roda_no_atomic_que_travou_a_linha(self, task_solicitacao, task):
        from apps.core.services.gcal.sync import SyncOutcome
        from apps.core.tasks import (
            queue_gcal_sync_retry,
            task_cancel_solicitacao_from_gcal,
            task_publish_solicitacao_to_gcal,
        )

        sol = task_solicitacao
        if task == "publish":
            Solicitacao.objects.filter(pk=sol.pk).update(
                gcal_status=Solicitacao.GCalStatus.NONE, external_event_id=None
            )
            alvo = _APPLY
            resposta = SyncOutcome(
                action="CREATE", solicitation_id=sol.id, external_event_id=f"asv2{sol.id}", summary=""
            )
            chamar = partial(task_publish_solicitacao_to_gcal, sol.id, dry_run=False)
        elif task == "cancel":
            alvo = _CANCEL
            resposta = SyncOutcome(action="DELETE", solicitation_id=sol.id, external_event_id=None, summary="")
            chamar = partial(task_cancel_solicitacao_from_gcal, sol.id)
        else:
            sol.mark_gcal(status=Solicitacao.GCalStatus.ERROR, payload_hash=None, error=_ERRO_DO_PUBLISH)
            alvo = _APPLY
            resposta = _sincronizou(sol)
            chamar = partial(queue_gcal_sync_retry, sol.id)

        fora, fora_sids, blocos, resultado = _rodar_e_guardar_os_atomics(chamar, alvo, resposta)

        assert resultado["error"] is None
        assert "trava" in blocos, "a task não travou a linha"
        assert "google" in blocos, "a task não chamou o Google"
        assert len(blocos["trava"]) > len(fora), "travou fora de um atomic aberto pela task"
        ate_o_atomic_da_task = len(fora) + 1
        assert len(blocos["google"]) >= ate_o_atomic_da_task and all(
            a is b for a, b in zip(blocos["google"][:ate_o_atomic_da_task], blocos["trava"][:ate_o_atomic_da_task])
        ), "o atomic da trava fechou antes da chamada ao Google"
        assert blocos["travou_antes"], "a task chamou o Google antes de travar a linha"
        ate_o_savepoint_da_task = len(fora_sids) + 1
        assert (
            len(blocos["trava_sids"]) >= ate_o_savepoint_da_task
        ), "sem savepoint da task: a comparação não prova nada"
        assert (
            blocos["google_sids"][:ate_o_savepoint_da_task] == blocos["trava_sids"][:ate_o_savepoint_da_task]
        ), "a chamada ao Google rodou num outro bloco aberto pelo mesmo Atomic"


_PENDING = Solicitacao.GCalStatus.PENDING
_ERROR = Solicitacao.GCalStatus.ERROR
_CAMPOS_DO_GOOGLE = (
    *_CAMPOS_GCAL,
    "gcal_pedido",
    "external_event_id",
    "meet_link",
    "last_synced_at",
    "last_sync_action",
    "last_sync_error",
)
_TRES_TAREFAS = pytest.mark.parametrize("tarefa", ["publicar", "cancelar", "nova_tentativa"])


def _linha_do_google(sol):
    return Solicitacao.objects.filter(pk=sol.pk).values(*_CAMPOS_DO_GOOGLE).get()


def _com_pedido(sol, *, gcal_status=_PENDING, **campos) -> str:
    """Deixa a linha como a entrada deixa: identificador novo gravado e PENDING (ou o `gcal_status` dado)."""
    pedido = uuid4().hex
    Solicitacao.objects.filter(pk=sol.pk).update(gcal_pedido=pedido, gcal_status=gcal_status, **campos)
    return pedido


def _estado_em_que_age(tarefa: str) -> str:
    """A nova tentativa age sobre ERROR (o publish que falhou deixou assim); publicar e cancelar, sobre PENDING."""
    return _ERROR if tarefa == "nova_tentativa" else _PENDING


def _rodar(tarefa: str, sol_id: int, **kwargs):
    from apps.core.tasks import (
        queue_gcal_sync_retry,
        task_cancel_solicitacao_from_gcal,
        task_publish_solicitacao_to_gcal,
    )

    tarefas = {
        "publicar": task_publish_solicitacao_to_gcal,
        "cancelar": task_cancel_solicitacao_from_gcal,
        "nova_tentativa": queue_gcal_sync_retry,
    }
    return tarefas[tarefa](sol_id, **kwargs)


def _apagou(sol):
    from apps.core.services.gcal.sync import SyncOutcome

    return SyncOutcome(action="DELETE", solicitation_id=sol.id, external_event_id=None, summary="")


class TestGuardaDoPedido:
    """DEF-32: a tarefa só chama o Google e só grava se, sob a trava, o identificador da mensagem é o da linha e
    a linha está no estado em que o pedido a deixou (PENDING; ERROR para a nova tentativa). Fora disso devolve
    SKIP sem Google, sem AuditLog e sem tocar a linha: pedido superado por outro mais novo, pedido desfeito
    (rollback da entrada), mensagem entregue de novo depois de concluída, mensagem sem identificador."""

    @_TRES_TAREFAS
    def test_pedido_superado_nao_chama_o_google_nem_grava(self, task_solicitacao, tarefa):
        sol = task_solicitacao
        _com_pedido(sol, gcal_status=_estado_em_que_age(tarefa))  # o pedido mais novo
        antes = _linha_do_google(sol)

        with patch(_APPLY) as aplicar, patch(_CANCEL) as cancelar:
            resultado = _rodar(tarefa, sol.id, pedido=uuid4().hex)  # a mensagem do pedido antigo

        aplicar.assert_not_called()
        cancelar.assert_not_called()
        assert resultado["action"] == "SKIP"
        assert resultado["error"] is None
        assert _linha_do_google(sol) == antes
        assert not AuditLog.objects.filter(details__solicitacao_id=sol.id).exists()

    @pytest.mark.parametrize(
        "tarefa, gcal_status",
        [
            ("publicar", "PUBLISHED"),
            ("publicar", "ERROR"),
            ("publicar", "NONE"),
            ("cancelar", "PUBLISHED"),
            ("cancelar", "ERROR"),
            ("nova_tentativa", "PUBLISHED"),
            ("nova_tentativa", "PENDING"),
        ],
    )
    def test_mesmo_pedido_com_a_linha_fora_do_estado_em_que_age_nao_faz_nada(
        self, task_solicitacao, tarefa, gcal_status
    ):
        """A mensagem entregue de novo depois que o pedido terminou (ou falhou e foi marcado) não repete nada."""
        sol = task_solicitacao
        pedido = _com_pedido(sol, gcal_status=gcal_status)
        antes = _linha_do_google(sol)

        with patch(_APPLY) as aplicar, patch(_CANCEL) as cancelar:
            resultado = _rodar(tarefa, sol.id, pedido=pedido)

        aplicar.assert_not_called()
        cancelar.assert_not_called()
        assert resultado["action"] == "SKIP"
        assert _linha_do_google(sol) == antes
        assert not AuditLog.objects.filter(details__solicitacao_id=sol.id).exists()

    def test_cancelamento_entregue_de_novo_sobre_linha_ja_desvinculada_nao_vira_erro(self, task_solicitacao):
        """O cancelamento terminou (NONE, sem id) e a mensagem volta. Sem a guarda, o `cancel_solicitacao` de
        verdade levantava "não possui evento publicado" e a linha ia para ERROR."""
        sol = task_solicitacao
        pedido = _com_pedido(sol, gcal_status="NONE", external_event_id=None)
        antes = _linha_do_google(sol)

        resultado = _rodar("cancelar", sol.id, pedido=pedido)

        assert resultado["action"] == "SKIP"
        assert _linha_do_google(sol) == antes
        assert not AuditLog.objects.filter(details__solicitacao_id=sol.id).exists()

    @_TRES_TAREFAS
    def test_mesmo_pedido_no_estado_em_que_age_segue(self, task_solicitacao, tarefa):
        sol = task_solicitacao
        pedido = _com_pedido(sol, gcal_status=_estado_em_que_age(tarefa))

        with (
            patch(_APPLY, return_value=_sincronizou(sol)) as aplicar,
            patch(_CANCEL, return_value=_apagou(sol)) as cancelar,
        ):
            resultado = _rodar(tarefa, sol.id, pedido=pedido)

        assert resultado["error"] is None
        if tarefa == "cancelar":
            cancelar.assert_called_once()
            assert resultado["action"] == "DELETE"
        else:
            aplicar.assert_called_once()
            assert resultado["action"] == "UPDATE"

    @_TRES_TAREFAS
    def test_guarda_confere_o_identificador_na_linha_travada(self, task_solicitacao, tarefa):
        """Outro pedido commita entre a entrega da mensagem e o FOR UPDATE: logo antes dele, a mesma conexão
        troca o identificador. Quem conferisse antes da trava seguiria com o pedido antigo."""
        sol = task_solicitacao
        pedido = _com_pedido(sol, gcal_status=_estado_em_que_age(tarefa))

        def outro_pedido_antes_da_trava(execute, sql, params, many, context):
            if _travou_a_solicitacao([{"sql": sql}]):
                Solicitacao.objects.filter(pk=sol.pk).update(gcal_pedido=uuid4().hex)
            return execute(sql, params, many, context)

        with (
            connection.execute_wrapper(outro_pedido_antes_da_trava),
            patch(_APPLY) as aplicar,
            patch(_CANCEL) as cancelar,
        ):
            resultado = _rodar(tarefa, sol.id, pedido=pedido)

        aplicar.assert_not_called()
        cancelar.assert_not_called()
        assert resultado["action"] == "SKIP"

    @_TRES_TAREFAS
    def test_mensagem_sem_identificador_nao_age_em_linha_que_ja_teve_pedido(self, task_solicitacao, tarefa):
        """Mensagem antiga (enfileirada antes do campo existir) ou chamada direta: só vale para linha que nunca
        teve pedido, que é como as chamadas diretas dos outros testes deste arquivo seguem funcionando."""
        sol = task_solicitacao
        _com_pedido(sol, gcal_status=_estado_em_que_age(tarefa))
        antes = _linha_do_google(sol)

        with patch(_APPLY) as aplicar, patch(_CANCEL) as cancelar:
            resultado = _rodar(tarefa, sol.id)

        aplicar.assert_not_called()
        cancelar.assert_not_called()
        assert resultado["action"] == "SKIP"
        assert _linha_do_google(sol) == antes

    def test_previa_nao_passa_pela_guarda(self, task_solicitacao):
        """A prévia não grava e não leva identificador: roda mesmo em linha que tem pedido."""
        sol = task_solicitacao
        _com_pedido(sol)

        with patch(_APPLY, return_value=_sincronizou(sol)) as aplicar:
            resultado = _rodar("publicar", sol.id, dry_run=True)

        aplicar.assert_called_once()
        assert resultado["action"] == "UPDATE"

    def test_cancelamento_atrasado_nao_apaga_a_publicacao_mais_nova(self, settings):
        """De ponta a ponta, com o cliente fake: publicado → "Tirar do Google" (a tarefa fica na fila) →
        "Reenviar" (pedido mais novo) publica → a tarefa do cancelamento antigo roda.

        RED: o cancelamento atrasado apagava o evento no Google e desvinculava a linha, por cima do reenvio."""
        from django.db import transaction

        from apps.core.services.gcal_fake_client import FakeCalendarClient
        from apps.core.services.solicitacao_publish import pedir_operacao_gcal

        settings.GCAL_AUTH_MODE = "service_account"
        fabrica = "apps.core.services.gcal_client_factory.get_gcal_client_and_calendar_id"
        fake = FakeCalendarClient()
        agora = timezone.now()
        sol = SolicitacaoFactory(
            status="aprovado", inicio=agora + timedelta(days=2), fim=agora + timedelta(days=2, hours=2)
        )
        eid = f"asv2{sol.id}"

        with patch(fabrica, return_value=(fake, "primary")):
            assert _rodar("publicar", sol.id)["action"] == "CREATE"
            with transaction.atomic():
                cancelamento = pedir_operacao_gcal(sol.id, "cancelar")
            with transaction.atomic():
                reenvio = pedir_operacao_gcal(sol.id, "reenviar")
            assert _rodar("publicar", sol.id, pedido=reenvio)["action"] == "UPDATE"

            resultado = _rodar("cancelar", sol.id, pedido=cancelamento)

        assert resultado["action"] == "SKIP"
        assert fake.get("primary", eid)["status"] == "confirmed"
        linha = Solicitacao.objects.filter(pk=sol.pk).values("gcal_status", "external_event_id").get()
        assert linha == {"gcal_status": "PUBLISHED", "external_event_id": eid}


class TestNotificacoesTask:
    """Tests for processar_notificacoes_acoes_diarias."""

    def test_notificacoes_task_returns_result(self, db):
        """Task returns dict with counts."""
        from apps.core.tasks import processar_notificacoes_acoes_diarias

        result = processar_notificacoes_acoes_diarias()

        assert "notifications_created" in result or "actions_evaluated" in result


def test_limite_brando_global_abaixo_do_duro():
    """#1968: aos 25 min a task recebe SoftTimeLimitExceeded e registra a falha; aos 30 min o SIGKILL não limpa nada."""
    from django.conf import settings

    from config.celery import app

    brando = getattr(settings, "CELERY_TASK_SOFT_TIME_LIMIT", None)
    assert brando is not None
    assert brando < settings.CELERY_TASK_TIME_LIMIT
    assert app.conf.task_soft_time_limit == brando

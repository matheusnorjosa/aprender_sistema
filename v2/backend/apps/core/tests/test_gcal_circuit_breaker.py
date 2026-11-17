"""
Tests for the GCal circuit breaker integration (ASQ-006 / #779).

Covers:
- State transitions CLOSED → OPEN → HALF_OPEN → CLOSED
- Fast-fail behavior once open
- `_retry_with_circuit_breaker` wrapping `_executar_uma_vez` (no outer retry since FER-60)
- `/api/gcal/circuit-breaker/` endpoint (state + counters + RBAC)
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false, reportPrivateUsage=false

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest import mock

from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

import httplib2
import pybreaker
import pytest
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import HttpMockSequence

from apps.core.services.gcal.circuit_breaker import (
    CircuitBreakerError,
    gcal_breaker,
    get_circuit_state,
    is_circuit_open,
    reset_circuit,
)
from apps.core.services.gcal.utils import _retry_with_circuit_breaker
from apps.core.services.gcal_google_client import GoogleCalendarClient
from apps.core.tests.factories import GroupFactory, UsuarioFactory, com_pacote_do_controle


@pytest.fixture(autouse=True)
def _reset_breaker():
    """Reset breaker before and after each test — global state leaks otherwise."""
    reset_circuit()
    yield
    reset_circuit()


class FakeHttpResp:
    def __init__(self, status_code: int):
        self.status = status_code

    def get(self, _key: str, default=None):
        return default


class FakeHttpError(Exception):
    """Mimics googleapiclient.errors.HttpError's .resp.status attribute."""

    def __init__(self, status_code: int, message: str = ""):
        super().__init__(message or f"HTTP {status_code}")
        self.resp = FakeHttpResp(status_code)


class TestStateTransitions:
    """Exercise CLOSED → OPEN → HALF_OPEN → CLOSED transitions."""

    def test_starts_closed(self):
        assert get_circuit_state() == "closed"
        assert is_circuit_open() is False

    def test_opens_after_fail_max_consecutive_failures(self):
        def failing():
            raise FakeHttpError(503, "upstream down")

        fail_max = getattr(gcal_breaker, "fail_max", 5)

        # Each call counts as one breaker failure (the outer layer does not retry since FER-60).
        # The last call may already raise CircuitBreakerError if the breaker tripped
        # mid-call, so accept either flavor.
        for _ in range(fail_max):
            with pytest.raises((FakeHttpError, CircuitBreakerError)):
                _retry_with_circuit_breaker(failing, operation_name="test")

        assert is_circuit_open() is True
        assert get_circuit_state() == "open"

    def test_open_breaker_fast_fails_without_calling_func(self):
        # Force breaker open directly
        gcal_breaker.open()
        called = {"count": 0}

        def tracker():
            called["count"] += 1
            return "ok"

        with pytest.raises(CircuitBreakerError):
            _retry_with_circuit_breaker(tracker, operation_name="fast-fail")

        assert called["count"] == 0, "open breaker should skip the function entirely"

    def test_half_open_success_returns_breaker_to_closed(self):
        # Force half-open via pybreaker's public API (the lazy time-based
        # transition from open→half-open is hard to reproduce reliably).
        gcal_breaker.half_open()
        assert get_circuit_state() == "half-open"

        result = _retry_with_circuit_breaker(lambda: "recovered", operation_name="half-open-probe")
        assert result == "recovered"
        assert get_circuit_state() == "closed"

    def test_half_open_failure_reopens_breaker(self):
        gcal_breaker.half_open()
        assert get_circuit_state() == "half-open"

        def fail():
            raise FakeHttpError(503)

        with pytest.raises((FakeHttpError, CircuitBreakerError)):
            _retry_with_circuit_breaker(fail, operation_name="half-open-fail")

        assert get_circuit_state() == "open"


def _aberto_alem_do_reset_timeout():
    """Abre o circuito e recua a hora da abertura para além do reset_timeout (relógio do pybreaker: UTC ingênuo)."""
    gcal_breaker.open()
    gcal_breaker._state_storage.opened_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(
        seconds=gcal_breaker.reset_timeout + 1
    )


class TestRecuperaSozinho:
    """DEF-31 (ART-21): vencido o reset_timeout, a próxima chamada passa como teste (half-open) e fecha o circuito.

    A passagem de open para half-open só acontece dentro de `gcal_breaker.call()`. Quem lê `current_state` antes e
    desiste nunca a dispara: o processo falhava rápido até ser reiniciado.
    """

    def test_retry_with_circuit_breaker_testa_depois_do_reset_timeout(self):
        _aberto_alem_do_reset_timeout()

        assert _retry_with_circuit_breaker(lambda: "voltou", operation_name="probe") == "voltou"
        assert get_circuit_state() == "closed"

    @pytest.mark.django_db
    def test_queue_gcal_sync_retry_tenta_depois_do_reset_timeout(self):
        from apps.core.models import Solicitacao
        from apps.core.services.gcal.types import SyncOutcome
        from apps.core.tasks import queue_gcal_sync_retry
        from apps.core.tests.factories import SolicitacaoFactory

        sol = SolicitacaoFactory(status="aprovado")
        sol.mark_gcal(status=Solicitacao.GCalStatus.ERROR, error="caiu no disjuntor")
        _aberto_alem_do_reset_timeout()
        outcome = SyncOutcome(action="UPDATE", solicitation_id=sol.pk, external_event_id="asv2x", summary="ok")

        with mock.patch("apps.core.services.gcal_sync_service.apply_one_solicitacao", return_value=outcome) as aplica:
            resultado = queue_gcal_sync_retry(sol.pk)

        aplica.assert_called_once()
        assert resultado["action"] == "UPDATE"

    @pytest.mark.django_db
    def test_queue_gcal_sync_retry_espera_enquanto_o_tempo_nao_venceu(self):
        from celery.exceptions import Retry

        from apps.core.models import Solicitacao
        from apps.core.tasks import queue_gcal_sync_retry
        from apps.core.tests.factories import SolicitacaoFactory

        sol = SolicitacaoFactory(status="aprovado")
        sol.mark_gcal(status=Solicitacao.GCalStatus.ERROR, error="caiu no disjuntor")
        gcal_breaker.open()

        with (
            mock.patch("apps.core.services.gcal_sync_service.apply_one_solicitacao") as aplica,
            mock.patch.object(queue_gcal_sync_retry, "retry", side_effect=Retry()) as nova_tentativa,
            pytest.raises(Retry),
        ):
            queue_gcal_sync_retry(sol.pk)

        aplica.assert_not_called()
        nova_tentativa.assert_called_once_with(countdown=60)

    def test_bloqueado_agora_segue_o_relogio_do_pybreaker(self):
        """Lê `_state_storage.opened_at`, atributo privado do pybreaker: se uma versão nova o tirar, este teste quebra
        (AttributeError) em vez de a nova tentativa passar a ignorar a pausa em silêncio."""
        from apps.core.services.gcal.circuit_breaker import bloqueado_agora

        assert bloqueado_agora() is False

        gcal_breaker.open()
        assert gcal_breaker._state_storage.opened_at is not None
        assert bloqueado_agora() is True

        _aberto_alem_do_reset_timeout()
        assert bloqueado_agora() is False
        assert get_circuit_state() == "open", "só o `call` passa a half-open; a leitura não muda o estado"


def _erro_http(status_code: int, motivo: str | None = None, corpo: bytes | None = None) -> HttpError:
    """HttpError de verdade, com o corpo no formato do Calendar v3 (`error.errors[0].reason`)."""
    if corpo is None:
        erro: dict[str, object] = {"code": status_code, "message": "x"}
        if motivo:
            erro["errors"] = [{"reason": motivo, "domain": "usageLimits"}]
        corpo = json.dumps({"error": erro}).encode()
    return HttpError(httplib2.Response({"status": str(status_code)}), corpo)


def _contagem_depois_de(erro: BaseException) -> int:
    def falha():
        raise erro

    with pytest.raises(type(erro)):
        _retry_with_circuit_breaker(falha, operation_name="t")
    return gcal_breaker.fail_counter


class TestOQueContaComoFalha:
    """DEF-31 (ART-21): o disjuntor mede a saúde do Google, não erro do pedido nem falta de acesso."""

    @pytest.mark.parametrize(
        "motivo", ["forbidden", "requiredAccessLevel", "insufficientPermissions", "forbiddenForNonOrganizer"]
    )
    def test_403_sem_acesso_nao_conta(self, motivo):
        assert _contagem_depois_de(_erro_http(403, motivo)) == 0

    @pytest.mark.parametrize(
        "motivo", ["rateLimitExceeded", "userRateLimitExceeded", "quotaExceeded", "dailyLimitExceeded"]
    )
    def test_403_de_cota_conta(self, motivo):
        assert _contagem_depois_de(_erro_http(403, motivo)) == 1

    def test_403_de_motivo_desconhecido_conta(self):
        """Falha segura: só o 403 de acesso conhecido sai da conta; um motivo novo do Google conta."""
        assert _contagem_depois_de(_erro_http(403, "motivoQueOGoogleAindaNaoTem")) == 1

    def test_403_de_cota_diaria_nao_zera_a_contagem(self):
        """Erro excluído passa pelo `_handle_success` do pybreaker e zera o contador: cota não pode cair nele."""
        for _ in range(gcal_breaker.fail_max - 1):
            _contagem_depois_de(_erro_http(503))

        def cota_diaria():
            raise _erro_http(403, "dailyLimitExceeded")

        with pytest.raises(CircuitBreakerError):  # a 5ª falha abre o disjuntor
            _retry_with_circuit_breaker(cota_diaria, operation_name="t")
        assert get_circuit_state() == "open"

    @pytest.mark.parametrize(
        "corpo", [b"<html>nada de json</html>", b'{"error": "texto"}', b"[]", b'{"error": {"code": 403}}']
    )
    def test_403_com_motivo_ilegivel_conta(self, corpo):
        """Falha segura: sem ler o motivo, não dá para saber se é cota."""
        assert _contagem_depois_de(_erro_http(403, corpo=corpo)) == 1

    def test_403_sem_corpo_conta(self):
        assert _contagem_depois_de(FakeHttpError(403, "forbidden")) == 1

    @pytest.mark.parametrize("status_code", [400, 404, 410])
    def test_erro_do_pedido_nao_conta(self, status_code):
        assert _contagem_depois_de(_erro_http(status_code)) == 0

    @pytest.mark.parametrize("status_code", [429, 500, 502, 503])
    def test_falha_do_google_conta(self, status_code):
        assert _contagem_depois_de(_erro_http(status_code)) == 1

    @pytest.mark.parametrize("erro", [TimeoutError("timed out"), ConnectionError("reset"), RuntimeError("x")])
    def test_erro_sem_resposta_http_conta(self, erro):
        assert _contagem_depois_de(erro) == 1

    def test_cinco_403_sem_acesso_nao_abrem_o_disjuntor(self):
        for _ in range(gcal_breaker.fail_max):
            _contagem_depois_de(_erro_http(403, "forbidden"))

        assert get_circuit_state() == "closed"

    def test_401_nao_conta(self):
        """Credencial recusada de uma pessoa (o AuthorizedHttp já renovou e o Google seguiu recusando)."""
        assert _contagem_depois_de(_erro_http(401)) == 0

    def test_refresh_recusado_nao_conta(self):
        """Acesso revogado na conta Google: o AuthorizedHttp tenta renovar no 401 e o token endpoint recusa."""
        assert _contagem_depois_de(RefreshError("invalid_grant: Token has been expired or revoked.")) == 0

    def test_refresh_com_falha_temporaria_do_google_conta(self):
        """5xx/429 no token endpoint: o google-auth marca `retryable`; é o Google, não a credencial."""
        assert _contagem_depois_de(RefreshError("temporarily_unavailable", retryable=True)) == 1

    def test_cinco_acessos_revogados_nao_abrem_o_disjuntor(self):
        for _ in range(gcal_breaker.fail_max):
            _contagem_depois_de(RefreshError("invalid_grant"))

        assert get_circuit_state() == "closed"


class TestTextoDoDisjuntor:
    @pytest.mark.parametrize(
        "erro",
        [CircuitBreakerError(gcal_breaker), CircuitBreakerError("Timeout not elapsed yet, circuit breaker still open")],
        ids=["objeto", "texto-da-lib"],
    )
    def test_texto_gravado_e_acionavel_em_portugues(self, erro):
        from apps.core.tasks import _friendly_gcal_error

        texto = _friendly_gcal_error(erro)

        assert "pybreaker" not in texto
        assert "circuit breaker" not in texto.lower()
        assert texto == (
            "O Google Agenda falhou várias vezes seguidas; o sistema pausou as chamadas por alguns minutos. "
            "Tente de novo daqui a pouco."
        )


def _cliente_sobre(status_ate_o_ok: list[int]):
    """GoogleCalendarClient de verdade sobre respostas HTTP prontas: os status dados e, no fim, um 200."""
    respostas = [
        ({"status": str(st)}, json.dumps({"error": {"code": st, "message": "x"}}).encode()) for st in status_ate_o_ok
    ]
    respostas.append(({"status": "200"}, json.dumps({"id": "asv2-1"}).encode()))
    cliente = GoogleCalendarClient.__new__(GoogleCalendarClient)
    cliente.service = build(
        "calendar", "v3", http=HttpMockSequence(respostas), static_discovery=True, cache_discovery=False
    )
    return cliente


class TestRetryIntegration:
    """The breaker sees one logical operation: the client's own retries (FER-60) are invisible to it."""

    def test_transient_error_that_eventually_succeeds_does_not_open_breaker(self, monkeypatch):
        monkeypatch.setattr("time.sleep", lambda _s: None)  # skip googleapiclient's real backoff
        cliente = _cliente_sobre([503, 503])

        # O sucesso final zera o fail_counter de qualquer jeito: contar as falhas no momento em que
        # o disjuntor as registra é o que prova que as repetições do cliente não chegam a ele.
        falhas: list[BaseException] = []

        class _Ouvinte(pybreaker.CircuitBreakerListener):
            def failure(self, cb, exc):
                falhas.append(exc)

        ouvinte = _Ouvinte()
        gcal_breaker.add_listener(ouvinte)
        try:
            result = _retry_with_circuit_breaker(
                lambda: cliente.insert("cal", "asv2-1", {"summary": "x"}), operation_name="flaky-then-ok"
            )
        finally:
            gcal_breaker.remove_listener(ouvinte)

        assert result == {"id": "asv2-1"}
        assert get_circuit_state() == "closed"
        assert falhas == []

    def test_exhausted_client_retries_count_as_a_single_breaker_failure(self, monkeypatch):
        monkeypatch.setattr("time.sleep", lambda _s: None)
        cliente = _cliente_sobre([503] * 10)

        with pytest.raises(HttpError):
            _retry_with_circuit_breaker(
                lambda: cliente.insert("cal", "asv2-1", {"summary": "x"}), operation_name="down"
            )

        assert gcal_breaker.fail_counter == 1

    def test_403_sem_acesso_nao_repete_e_nao_conta_para_o_disjuntor(self):
        # DEF-31 (ART-21): contrato invertido de propósito. Antes este teste exigia que o 403 contasse 1 falha;
        # falta de acesso ao calendário não é o Google fora do ar, então não pode abrir o disjuntor.
        calls = {"n": 0}

        def forbidden():
            calls["n"] += 1
            raise _erro_http(403, "forbidden")

        with pytest.raises(HttpError):
            _retry_with_circuit_breaker(forbidden, operation_name="auth-fail")

        assert calls["n"] == 1
        assert gcal_breaker.fail_counter == 0
        assert get_circuit_state() == "closed"

    def test_403_de_cota_nao_repete_aqui_mas_conta_para_o_disjuntor(self):
        calls = {"n": 0}

        def cota():
            calls["n"] += 1
            raise _erro_http(403, "quotaExceeded")

        with pytest.raises(HttpError):
            _retry_with_circuit_breaker(cota, operation_name="quota")

        assert calls["n"] == 1
        assert gcal_breaker.fail_counter == 1
        assert get_circuit_state() == "closed"


class TestCircuitBreakerEndpoint:
    """`/api/gcal/circuit-breaker/` — state + RBAC."""

    @pytest.fixture
    def client(self):
        return APIClient()

    @pytest.fixture
    def staff_user(self, db):
        user = UsuarioFactory(username="operator", email="operator@test.com", password="x")
        group = GroupFactory(name="Controle")
        user.groups.add(group)
        com_pacote_do_controle(user)
        return user

    @pytest.fixture
    def regular_user(self, db):
        return UsuarioFactory(username="regular", email="regular@test.com", password="x")

    def test_returns_closed_state_on_fresh_breaker(self, client, staff_user):
        client.force_authenticate(user=staff_user)
        response = client.get("/api/gcal/circuit-breaker/")

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["state"] == "closed"
        assert body["fail_counter"] == 0
        assert body["fail_max"] >= 1
        assert body["reset_timeout_seconds"] >= 1

    def test_returns_open_state_when_breaker_tripped(self, client, staff_user):
        client.force_authenticate(user=staff_user)
        gcal_breaker.open()

        response = client.get("/api/gcal/circuit-breaker/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["state"] == "open"

    def test_requires_authentication(self, client):
        response = client.get("/api/gcal/circuit-breaker/")
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_regular_user_forbidden(self, client, regular_user):
        client.force_authenticate(user=regular_user)
        response = client.get("/api/gcal/circuit-breaker/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @override_settings(GCAL_CIRCUIT_BREAKER_FAIL_MAX=7, GCAL_CIRCUIT_BREAKER_RESET_TIMEOUT=90)
    def test_reports_settings_derived_thresholds(self, client, staff_user):
        client.force_authenticate(user=staff_user)
        response = client.get("/api/gcal/circuit-breaker/")
        body = response.json()
        assert body["fail_max"] == 7
        assert body["reset_timeout_seconds"] == 90


class TestCircuitBreakerSanity:
    """Safety nets for the existing helpers used elsewhere."""

    def test_pybreaker_error_is_reexported(self):
        assert issubclass(CircuitBreakerError, pybreaker.CircuitBreakerError)

    def test_reset_circuit_closes_open_breaker(self):
        gcal_breaker.open()
        assert is_circuit_open() is True
        reset_circuit()
        assert is_circuit_open() is False

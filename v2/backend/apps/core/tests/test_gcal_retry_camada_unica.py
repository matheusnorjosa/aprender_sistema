"""
Repetição das chamadas ao Google numa camada só (FER-60).

Antes: o helper de `gcal/utils.py` (4 tentativas) envolvia o laço de cada cliente (mais 4), e uma
escrita com o Google fora do ar chegava a 16 chamadas e ~30 s parados. Agora a única camada é a
repetição embutida da biblioteca do Google (`request.execute(num_retries=N)`): 5xx, 429, 403 de cota,
timeout e queda de conexão; 4 chamadas no máximo por escrita.

Os testes usam o `HttpMockSequence` do googleapiclient: respostas HTTP de verdade, sem rede, contando
quantas requisições saíram. `time.sleep` é trocado para não esperar.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownLambdaType=false

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import HttpMockSequence

from apps.core.services.gcal.utils import _retry_with_circuit_breaker
from apps.core.services.gcal_google_client import GoogleCalendarClient
from apps.core.services.gcal_oauth_client import OAuthCalendarClient

CAL = "agenda@group.calendar.google.com"
EVENTO_OK = ({"status": "200"}, json.dumps({"id": "asv2-1"}).encode())
VAZIO_OK = ({"status": "204"}, b"")


def _erro(status: int, motivo: str | None = None):
    corpo: dict[str, object] = {"error": {"code": status, "message": "x"}}
    if motivo:
        corpo["error"] = {"code": status, "message": "x", "errors": [{"reason": motivo}]}
    return ({"status": str(status)}, json.dumps(corpo).encode())


class _Contador(HttpMockSequence):
    """HttpMockSequence que conta as requisições que saíram."""

    def __init__(self, respostas):
        super().__init__(list(respostas))
        self.chamadas = 0

    def request(self, *args, **kwargs):
        self.chamadas += 1
        return super().request(*args, **kwargs)


def _cliente(tipo: str, respostas):
    http = _Contador(respostas)
    service = build("calendar", "v3", http=http, static_discovery=True, cache_discovery=False)
    if tipo == "sa":
        cliente = GoogleCalendarClient.__new__(GoogleCalendarClient)
    else:
        cliente = OAuthCalendarClient.__new__(OAuthCalendarClient)
        cliente.credential = SimpleNamespace(user_id=1, google_email="conta@aprendereditora.com.br")
    cliente.service = service
    return cliente, http


@pytest.fixture(autouse=True)
def _sem_espera(monkeypatch):
    esperas: list[float] = []
    monkeypatch.setattr("time.sleep", esperas.append)
    return esperas


@pytest.fixture(autouse=True)
def _disjuntor_fechado():
    from apps.core.services.gcal.circuit_breaker import gcal_breaker

    gcal_breaker.close()
    yield
    gcal_breaker.close()


CLIENTES = ["sa", "oauth"]


@pytest.mark.parametrize("tipo", CLIENTES)
class TestUmaCamadaSo:
    def test_escrita_com_google_fora_do_ar_faz_no_maximo_4_chamadas(self, tipo):
        cliente, http = _cliente(tipo, [_erro(503)] * 20)

        with pytest.raises(HttpError):
            _retry_with_circuit_breaker(lambda: cliente.insert(CAL, "asv2-1", {"summary": "x"}), operation_name="t")

        assert http.chamadas == 4

    def test_falha_passageira_se_resolve_na_repeticao(self, tipo):
        cliente, http = _cliente(tipo, [_erro(503), _erro(503), EVENTO_OK])

        resultado = _retry_with_circuit_breaker(
            lambda: cliente.insert(CAL, "asv2-1", {"summary": "x"}), operation_name="t"
        )

        assert resultado == {"id": "asv2-1"}
        assert http.chamadas == 3

    def test_409_no_insert_e_idempotente_sem_repetir(self, tipo):
        cliente, http = _cliente(tipo, [_erro(409)] * 5)

        resultado = _retry_with_circuit_breaker(
            lambda: cliente.insert(CAL, "asv2-1", {"summary": "x"}), operation_name="t"
        )

        assert resultado is None
        assert http.chamadas == 1

    @pytest.mark.parametrize("status", [400, 403])
    def test_erro_do_pedido_nao_repete(self, tipo, status):
        cliente, http = _cliente(tipo, [_erro(status)] * 5)

        with pytest.raises(HttpError):
            _retry_with_circuit_breaker(lambda: cliente.insert(CAL, "asv2-1", {"summary": "x"}), operation_name="t")

        assert http.chamadas == 1

    def test_403_de_cota_repete(self, tipo):
        cliente, http = _cliente(tipo, [_erro(403, "rateLimitExceeded"), EVENTO_OK])

        resultado = _retry_with_circuit_breaker(
            lambda: cliente.update(CAL, "asv2-1", {"summary": "x"}), operation_name="t"
        )

        assert resultado == {"id": "asv2-1"}
        assert http.chamadas == 2

    def test_delete_404_e_engolido_sem_repetir(self, tipo):
        cliente, http = _cliente(tipo, [_erro(404)] * 5)

        _retry_with_circuit_breaker(lambda: cliente.delete(CAL, "asv2-1"), operation_name="t")

        assert http.chamadas == 1

    def test_get_404_vira_none_sem_repetir(self, tipo):
        cliente, http = _cliente(tipo, [_erro(404)] * 5)

        assert cliente.get(CAL, "asv2-1") is None
        assert http.chamadas == 1

    def test_leitura_da_tela_usa_o_limite_curto(self, tipo, settings):
        settings.GCAL_REQUEST_MAX_RETRIES = 1
        cliente, http = _cliente(tipo, [_erro(503)] * 10)

        with pytest.raises(HttpError):
            cliente.list_calendars()

        assert http.chamadas == 2

    def test_espera_total_de_uma_escrita_fica_curta(self, tipo, _sem_espera):
        cliente, _ = _cliente(tipo, [_erro(503)] * 20)

        with pytest.raises(HttpError):
            _retry_with_circuit_breaker(lambda: cliente.delete(CAL, "asv2-1"), operation_name="t")

        # 3 esperas de no máximo 2, 4 e 8 s; antes eram 15 esperas e ~30 s.
        assert len(_sem_espera) == 3
        assert sum(_sem_espera) <= 14

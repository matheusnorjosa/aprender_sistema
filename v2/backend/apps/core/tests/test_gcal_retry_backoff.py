"""
Testes da camada de fora das chamadas ao Google Calendar (RF05 - PR19, FER-60).

Desde o FER-60 a camada de fora (`gcal/utils._executar_uma_vez`) não repete: a repetição de 429/5xx
mora no cliente, na biblioteca do Google (`execute(num_retries=...)`). Aqui fica o que a camada de fora
ainda decide:
- Sucesso devolve o resultado, com 1 chamada
- 409/412 viram sucesso (idempotência), inclusive quando o erro só traz o código no texto
- Qualquer outro erro (4xx, 429, 5xx, desconhecido) sobe na hora, sem repetir e sem esperar
- SoftTimeLimitExceeded sobe na hora (#1968)

A repetição de 429/5xx no cliente fica no fim do arquivo (respostas HTTP de verdade) e em
`test_gcal_retry_camada_unica.py` (no máximo 4 chamadas por escrita, espera total curta).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

import json
from unittest.mock import Mock

import pytest
from googleapiclient.discovery import build
from googleapiclient.http import HttpMockSequence

from apps.core.services.gcal.utils import _executar_uma_vez
from apps.core.services.gcal_google_client import GoogleCalendarClient


class MockHttpError(Exception):
    """Mock de googleapiclient.errors.HttpError"""

    def __init__(self, status_code, message="HTTP Error"):
        self.resp = Mock()
        self.resp.status = status_code
        self.resp.get = Mock(return_value=None)
        super().__init__(f"{status_code}: {message}")


@pytest.fixture(autouse=True)
def _esperas(monkeypatch):
    """Troca o `time.sleep` global: a camada de fora não pode esperar; o cliente espera sem demorar."""
    esperas: list[float] = []
    monkeypatch.setattr("time.sleep", esperas.append)
    return esperas


class TestExecutarUmaVez:
    """Testes de `_executar_uma_vez` (a camada de fora, sem laço)"""

    def test_success_first_attempt_no_retry(self):
        """RF05: Sucesso devolve o resultado com 1 chamada"""
        mock_func = Mock(return_value="success")

        result = _executar_uma_vez(mock_func, operation_name="test_op")

        assert result == "success"
        assert mock_func.call_count == 1

    @pytest.mark.parametrize(
        "erro",
        [
            MockHttpError(429, "Rate Limit"),
            MockHttpError(500, "Internal Server Error"),
            MockHttpError(503, "Service Unavailable"),
            Exception("HTTP 429 Rate Limit Exceeded"),
            Exception("HTTP 503 Service Unavailable"),
            Exception("Unknown network error"),
        ],
        ids=["429", "500", "503", "texto-429", "texto-503", "desconhecido"],
    )
    def test_erro_passageiro_sobe_sem_repetir_aqui(self, erro, _esperas):
        """FER-60: 429/5xx não repetem na camada de fora; quem repete é o cliente (num_retries)."""
        mock_func = Mock(side_effect=[erro, "success"])

        with pytest.raises(type(erro)):
            _executar_uma_vez(mock_func, operation_name="t")

        assert mock_func.call_count == 1
        assert _esperas == []

    @pytest.mark.parametrize("status", [400, 403, 404])
    def test_erro_do_pedido_sobe_sem_repetir(self, status):
        """RF05: Client error 4xx sobe na hora"""
        mock_func = Mock(side_effect=MockHttpError(status))

        with pytest.raises(MockHttpError) as exc_info:
            _executar_uma_vez(mock_func, operation_name="t")

        assert exc_info.value.resp.status == status
        assert mock_func.call_count == 1

    @pytest.mark.parametrize("status", [409, 412])
    def test_409_412_treated_as_success(self, status):
        """
        RF05: 409 Conflict / 412 Precondition Failed viram sucesso (idempotência).

        Cenário: o id determinístico já existe no Google Calendar.
        """
        mock_func = Mock(side_effect=MockHttpError(status))

        result = _executar_uma_vez(mock_func, operation_name="t")

        assert result is None
        assert mock_func.call_count == 1

    @pytest.mark.parametrize("texto", ["HTTP 409 Conflict", "HTTP 412 Precondition Failed"])
    def test_409_412_so_no_texto_tambem_sao_sucesso(self, texto):
        """Erro sem `resp` (cliente que só levanta texto): o código no texto basta."""
        mock_func = Mock(side_effect=Exception(texto))

        assert _executar_uma_vez(mock_func, operation_name="t") is None
        assert mock_func.call_count == 1


class TestLimiteBrandoNaoRetenta1968:
    """#1968: o aviso de tempo esgotado (25 min) sobe na hora; não é erro do Google para tentar de novo."""

    def test_soft_time_limit_nao_e_retentado(self, _esperas):
        from celery.exceptions import SoftTimeLimitExceeded

        func = Mock(side_effect=[SoftTimeLimitExceeded(), "success"])

        with pytest.raises(SoftTimeLimitExceeded):
            _executar_uma_vez(func, operation_name="t")

        assert func.call_count == 1
        assert _esperas == []


def _cliente_sobre(respostas):
    """GoogleCalendarClient de verdade sobre respostas HTTP prontas (sem rede)."""
    http = HttpMockSequence(list(respostas))
    cliente = GoogleCalendarClient.__new__(GoogleCalendarClient)
    cliente.service = build("calendar", "v3", http=http, static_discovery=True, cache_discovery=False)
    return cliente


class TestRepeticaoNoCliente:
    """RF05: 429/5xx repetem até dar certo, agora dentro do cliente (biblioteca do Google)."""

    @pytest.mark.parametrize("status", [429, 500, 503])
    def test_erro_passageiro_repete_ate_sucesso(self, status, _esperas):
        erro = ({"status": str(status)}, json.dumps({"error": {"code": status, "message": "x"}}).encode())
        ok = ({"status": "200"}, json.dumps({"id": "asv2-1"}).encode())
        cliente = _cliente_sobre([erro, erro, ok])

        resultado = _executar_uma_vez(lambda: cliente.insert("cal", "asv2-1", {"summary": "x"}), operation_name="t")

        assert resultado == {"id": "asv2-1"}
        assert len(_esperas) == 2, "2 esperas da biblioteca entre as 3 chamadas"

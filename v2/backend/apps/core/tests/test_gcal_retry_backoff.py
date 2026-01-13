"""
Testes para retry/backoff em chamadas Google Calendar (RF05 - PR19).

Valida:
- Retry em 429 (rate limit) até sucesso
- Retry em 5xx (server errors) até sucesso
- Não retry em 4xx (exceto 429)
- Tratamento de 409/412 como sucesso (idempotência)
- Backoff exponencial (1s, 2s, 4s)
- Respeito ao header Retry-After
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations
import pytest
from unittest.mock import Mock, patch, call
from apps.core.services.gcal_sync_service import _retry_with_backoff


class MockHttpError(Exception):
    """Mock de googleapiclient.errors.HttpError"""
    def __init__(self, status_code, message="HTTP Error"):
        self.resp = Mock()
        self.resp.status = status_code
        self.resp.get = Mock(return_value=None)
        super().__init__(f"{status_code}: {message}")


@pytest.mark.django_db
class TestRetryBackoff:
    """Testes para função _retry_with_backoff"""

    def test_success_first_attempt_no_retry(self):
        """RF05: Sucesso na primeira tentativa não deve retentar"""
        mock_func = Mock(return_value="success")

        result = _retry_with_backoff(
            mock_func,
            operation_name="test_op",
            max_retries=3
        )

        assert result == "success"
        assert mock_func.call_count == 1

    @patch('apps.core.services.gcal.utils.time.sleep')
    def test_retry_429_rate_limit_until_success(self, mock_sleep):
        """
        RF05: Rate limit (429) deve retentar até sucesso.

        Cenário:
        - Tentativa 1: 429 → retry
        - Tentativa 2: 429 → retry
        - Tentativa 3: Sucesso
        """
        mock_func = Mock()
        mock_func.side_effect = [
            MockHttpError(429, "Rate Limit"),
            MockHttpError(429, "Rate Limit"),
            "success"
        ]

        result = _retry_with_backoff(
            mock_func,
            operation_name="test_429",
            max_retries=3,
            initial_delay=0.01  # Delay baixo para testes rápidos
        )

        assert result == "success"
        assert mock_func.call_count == 3

        # Validar backoff exponencial: 0.01, 0.02
        assert mock_sleep.call_count == 2
        calls = [c[0][0] for c in mock_sleep.call_args_list]
        assert calls[0] == pytest.approx(0.01, rel=0.1)
        assert calls[1] == pytest.approx(0.02, rel=0.1)

    @patch('apps.core.services.gcal.utils.time.sleep')
    def test_retry_500_server_error_until_success(self, mock_sleep):
        """
        RF05: Server error (5xx) deve retentar até sucesso.

        Cenário:
        - Tentativa 1: 500 → retry
        - Tentativa 2: Sucesso
        """
        mock_func = Mock()
        mock_func.side_effect = [
            MockHttpError(500, "Internal Server Error"),
            "success"
        ]

        result = _retry_with_backoff(
            mock_func,
            operation_name="test_500",
            max_retries=3,
            initial_delay=0.01
        )

        assert result == "success"
        assert mock_func.call_count == 2
        assert mock_sleep.call_count == 1

    @patch('apps.core.services.gcal.utils.time.sleep')
    def test_retry_503_service_unavailable(self, mock_sleep):
        """RF05: 503 Service Unavailable deve retentar"""
        mock_func = Mock()
        mock_func.side_effect = [
            MockHttpError(503, "Service Unavailable"),
            "success"
        ]

        result = _retry_with_backoff(
            mock_func,
            operation_name="test_503",
            max_retries=3,
            initial_delay=0.01
        )

        assert result == "success"
        assert mock_func.call_count == 2

    def test_no_retry_on_400_bad_request(self):
        """
        RF05: Client error 4xx (exceto 429) não deve retentar.

        Deve abortar imediatamente em 400 Bad Request.
        """
        mock_func = Mock()
        mock_func.side_effect = MockHttpError(400, "Bad Request")

        with pytest.raises(MockHttpError) as exc_info:
            _retry_with_backoff(
                mock_func,
                operation_name="test_400",
                max_retries=3
            )

        assert exc_info.value.resp.status == 400
        assert mock_func.call_count == 1  # Apenas 1 tentativa

    def test_no_retry_on_403_forbidden(self):
        """RF05: 403 Forbidden não deve retentar"""
        mock_func = Mock()
        mock_func.side_effect = MockHttpError(403, "Forbidden")

        with pytest.raises(MockHttpError):
            _retry_with_backoff(
                mock_func,
                operation_name="test_403",
                max_retries=3
            )

        assert mock_func.call_count == 1

    def test_no_retry_on_404_not_found(self):
        """RF05: 404 Not Found não deve retentar"""
        mock_func = Mock()
        mock_func.side_effect = MockHttpError(404, "Not Found")

        with pytest.raises(MockHttpError):
            _retry_with_backoff(
                mock_func,
                operation_name="test_404",
                max_retries=3
            )

        assert mock_func.call_count == 1

    def test_409_conflict_treated_as_success(self):
        """
        RF05: 409 Conflict deve ser tratado como sucesso (idempotência).

        Cenário: Evento já existe no Google Calendar.
        """
        mock_func = Mock()
        mock_func.side_effect = MockHttpError(409, "Conflict")

        # Não deve lançar exceção
        result = _retry_with_backoff(
            mock_func,
            operation_name="test_409",
            max_retries=3
        )

        # 409 retorna None mas não falha
        assert result is None
        assert mock_func.call_count == 1

    def test_412_precondition_failed_treated_as_success(self):
        """
        RF05: 412 Precondition Failed deve ser tratado como sucesso (idempotência).

        Cenário: Condição prévia não satisfeita, mas operação já foi aplicada.
        """
        mock_func = Mock()
        mock_func.side_effect = MockHttpError(412, "Precondition Failed")

        result = _retry_with_backoff(
            mock_func,
            operation_name="test_412",
            max_retries=3
        )

        assert result is None
        assert mock_func.call_count == 1

    @patch('apps.core.services.gcal.utils.time.sleep')
    def test_max_retries_exhausted(self, mock_sleep):
        """
        RF05: Após esgotar retries, deve lançar última exceção.

        Cenário:
        - 4 tentativas (1 inicial + 3 retries)
        - Todas falham com 500
        - Deve lançar exceção após a 4ª tentativa
        """
        mock_func = Mock()
        mock_func.side_effect = MockHttpError(500, "Server Error")

        with pytest.raises(MockHttpError) as exc_info:
            _retry_with_backoff(
                mock_func,
                operation_name="test_max_retries",
                max_retries=3,
                initial_delay=0.01
            )

        assert exc_info.value.resp.status == 500
        # 1 tentativa inicial + 3 retries = 4 chamadas
        assert mock_func.call_count == 4
        # 3 sleeps (entre as tentativas)
        assert mock_sleep.call_count == 3

    @patch('apps.core.services.gcal.utils.time.sleep')
    def test_retry_after_header_respected(self, mock_sleep):
        """
        RF05: Header Retry-After deve ser respeitado.

        Cenário: API retorna Retry-After: 5 (segundos)
        """
        error = MockHttpError(429, "Rate Limit")
        error.resp.get = Mock(return_value="5")  # Retry-After: 5s

        mock_func = Mock()
        mock_func.side_effect = [error, "success"]

        result = _retry_with_backoff(
            mock_func,
            operation_name="test_retry_after",
            max_retries=3,
            initial_delay=1.0
        )

        assert result == "success"
        assert mock_sleep.call_count == 1
        # Deve usar Retry-After (5s) em vez de backoff exponencial
        assert mock_sleep.call_args[0][0] == 5.0

    @patch('apps.core.services.gcal.utils.time.sleep')
    def test_exponential_backoff_sequence(self, mock_sleep):
        """
        RF05: Backoff exponencial deve seguir sequência 1s, 2s, 4s.

        Cenário: 4 tentativas com initial_delay=1.0
        """
        mock_func = Mock()
        mock_func.side_effect = [
            MockHttpError(500, "Error 1"),
            MockHttpError(500, "Error 2"),
            MockHttpError(500, "Error 3"),
            "success"
        ]

        result = _retry_with_backoff(
            mock_func,
            operation_name="test_backoff_sequence",
            max_retries=3,
            initial_delay=1.0
        )

        assert result == "success"
        assert mock_sleep.call_count == 3

        # Validar sequência: 1s, 2s, 4s
        calls = [c[0][0] for c in mock_sleep.call_args_list]
        assert calls == [1.0, 2.0, 4.0]

    @patch('apps.core.services.gcal.utils.time.sleep')
    def test_string_error_with_429_in_message(self, mock_sleep):
        """
        RF05: Deve detectar 429 por string matching quando objeto não tem resp.status.

        Cenário: Exceção genérica com "429" no texto.
        """
        mock_func = Mock()
        mock_func.side_effect = [
            Exception("HTTP 429 Rate Limit Exceeded"),
            "success"
        ]

        result = _retry_with_backoff(
            mock_func,
            operation_name="test_string_429",
            max_retries=3,
            initial_delay=0.01
        )

        assert result == "success"
        assert mock_func.call_count == 2
        assert mock_sleep.call_count == 1

    @patch('apps.core.services.gcal.utils.time.sleep')
    def test_string_error_with_500_in_message(self, mock_sleep):
        """RF05: Deve detectar 5xx por string matching"""
        mock_func = Mock()
        mock_func.side_effect = [
            Exception("HTTP 503 Service Unavailable"),
            "success"
        ]

        result = _retry_with_backoff(
            mock_func,
            operation_name="test_string_503",
            max_retries=3,
            initial_delay=0.01
        )

        assert result == "success"
        assert mock_func.call_count == 2

    @patch('apps.core.services.gcal.utils.time.sleep')
    def test_unknown_error_retries_conservatively(self, mock_sleep):
        """
        RF05: Erro desconhecido deve retentar conservadoramente.

        Cenário: Exceção sem código de status identificável.
        """
        mock_func = Mock()
        mock_func.side_effect = [
            Exception("Unknown network error"),
            "success"
        ]

        result = _retry_with_backoff(
            mock_func,
            operation_name="test_unknown_error",
            max_retries=3,
            initial_delay=0.01
        )

        assert result == "success"
        assert mock_func.call_count == 2
        assert mock_sleep.call_count == 1

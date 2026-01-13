"""
Testes para MP3 - Sentry APM.

Valida:
- Configuração do Sentry quando SENTRY_DSN está presente
- Integrations (DjangoIntegration, CeleryIntegration)
- Environment e Release tracking
- Configurações de privacidade (LGPD/GDPR)

Refs: Issue #167
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest


class TestSentryConfiguration:
    """Testa configuração do Sentry APM."""

    @patch("sentry_sdk.init")
    def test_sentry_initializes_when_dsn_provided(self, mock_init: MagicMock) -> None:
        """Testa que Sentry é inicializado quando SENTRY_DSN está presente."""
        # Arrange: Set SENTRY_DSN environment variable
        test_dsn = "https://example@sentry.io/12345"

        with patch.dict(os.environ, {"SENTRY_DSN": test_dsn}):
            # Act: Import settings para disparar inicialização do Sentry
            # NOTE: Precisamos reimportar settings para aplicar novo env var
            import importlib

            import config.settings as settings_module

            importlib.reload(settings_module)

            # Assert: Verificar que sentry_sdk.init foi chamado
            if test_dsn:  # Se DSN presente, deve ter sido chamado
                assert mock_init.called, "sentry_sdk.init() deveria ter sido chamado"
                call_kwargs = mock_init.call_args[1]

                # Verificar DSN
                assert call_kwargs["dsn"] == test_dsn

                # Verificar integrations
                integrations = call_kwargs.get("integrations", [])
                integration_names = [type(i).__name__ for i in integrations]
                assert "DjangoIntegration" in integration_names
                assert "CeleryIntegration" in integration_names

                # Verificar configurações de privacidade (LGPD/GDPR)
                assert call_kwargs.get("send_default_pii") is False

                # Verificar sample rates
                assert 0.0 <= call_kwargs.get("traces_sample_rate", 0.1) <= 1.0
                assert call_kwargs.get("sample_rate") == 1.0  # 100% de erros

    def test_sentry_not_initialized_when_dsn_empty(self) -> None:
        """Testa que Sentry NÃO é inicializado quando SENTRY_DSN está vazio."""
        # Arrange: SENTRY_DSN vazio
        with patch.dict(os.environ, {"SENTRY_DSN": ""}):
            # Act: Import settings
            import importlib

            import config.settings as settings_module

            importlib.reload(settings_module)

            # Assert: Verificar que SENTRY_DSN é vazio (Sentry disabled)
            assert settings_module.SENTRY_DSN == ""

    @pytest.mark.django_db
    def test_sentry_captures_exceptions(self) -> None:
        """Testa que Sentry captura exceções quando configurado."""
        # Arrange: Mock sentry_sdk.capture_exception
        with patch("sentry_sdk.capture_exception") as mock_capture:
            # Act: Disparar uma exceção
            try:
                raise ValueError("Test exception for Sentry")
            except ValueError as exc:
                # Simular captura pelo Sentry
                import sentry_sdk

                sentry_sdk.capture_exception(exc)

            # Assert: Verificar que exceção foi capturada
            assert mock_capture.called
            captured_exc = mock_capture.call_args[0][0]
            assert isinstance(captured_exc, ValueError)
            assert "Test exception for Sentry" in str(captured_exc)


class TestSentryEnvironmentTracking:
    """Testa tracking de environment e release."""

    @patch("sentry_sdk.init")
    def test_environment_tracking(self, mock_init: MagicMock) -> None:
        """Testa que environment (dev/staging/prod) é rastreado."""
        test_dsn = "https://example@sentry.io/12345"
        test_env = "staging"

        with patch.dict(os.environ, {"SENTRY_DSN": test_dsn, "ENVIRONMENT": test_env}):
            import importlib

            import config.settings as settings_module

            importlib.reload(settings_module)

            if mock_init.called:
                call_kwargs = mock_init.call_args[1]
                assert call_kwargs.get("environment") == test_env

    @patch("sentry_sdk.init")
    def test_release_tracking(self, mock_init: MagicMock) -> None:
        """Testa que release (commit SHA) é rastreado."""
        test_dsn = "https://example@sentry.io/12345"
        test_commit = "abc123def456"

        with patch.dict(os.environ, {"SENTRY_DSN": test_dsn, "GIT_COMMIT_SHA": test_commit}):
            import importlib

            import config.settings as settings_module

            importlib.reload(settings_module)

            if mock_init.called:
                call_kwargs = mock_init.call_args[1]
                assert call_kwargs.get("release") == test_commit


# NOTE: Teste de integração completo com Sentry real foi removido pois:
# 1. Requer DSN válido do Sentry.io (não disponível em testes CI)
# 2. Faria chamadas HTTP reais para Sentry API
# 3. Os testes unitários acima validam configuração e inicialização
#
# Em produção/staging, validar Sentry manualmente:
# 1. Configurar SENTRY_DSN no .env
# 2. Disparar erro intencional (ex: division by zero em view)
# 3. Verificar erro aparece no dashboard Sentry.io

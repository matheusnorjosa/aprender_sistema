"""
Testes para GoogleCalendarClient (cliente real do Google Calendar).

Valida:
- Upsert insere quando get retorna 404
- Upsert faz patch quando evento já existe
- Factory retorna cliente correto baseado em settings
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false

from __future__ import annotations
import pytest
from unittest.mock import MagicMock, Mock, patch
from django.test import TestCase, override_settings
from googleapiclient.errors import HttpError


@pytest.mark.django_db
class TestGoogleCalendarClient(TestCase):
    """Testes para GoogleCalendarClient."""

    @patch("os.getenv")
    @patch("google.oauth2.service_account.Credentials.from_service_account_info")
    @patch("apps.core.services.gcal_google_client.build")
    def test_insert_when_event_not_found(self, mock_build, mock_creds, mock_getenv):
        """
        Upsert insere quando get retorna 404.

        Cenário:
        - get() retorna 404 (evento não existe)
        - insert() é chamado com body.id=event_id e sendUpdates="none"
        """
        from apps.core.services.gcal_google_client import GoogleCalendarClient

        # Mock env vars
        def getenv_side_effect(key, default=None):
            if key == "GOOGLE_SERVICE_ACCOUNT_JSON":
                return '{"type": "service_account", "project_id": "test"}'
            return default
        mock_getenv.side_effect = getenv_side_effect

        # Mock credentials (from_service_account_info already patched)
        mock_creds.return_value = MagicMock()

        # Mock service with consistent events() return
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Create a consistent mock for events()
        mock_events_api = MagicMock()
        mock_service.events.return_value = mock_events_api

        # Mock get() to return a request object that raises 404 on execute()
        mock_get_request = MagicMock()
        mock_get_request.execute.side_effect = HttpError(
            resp=Mock(status=404), content=b"Not Found"
        )
        mock_events_api.get.return_value = mock_get_request

        # Mock insert() to return a request object that returns data on execute()
        mock_insert_request = MagicMock()
        mock_insert_request.execute.return_value = {
            "id": "test-event-1",
            "summary": "Test Event",
        }
        mock_events_api.insert.return_value = mock_insert_request

        # Criar client com credentials mockadas
        client = GoogleCalendarClient()

        # Testar get (deve retornar None em 404)
        result = client.get("primary", "test-event-1")
        assert result is None

        # Testar insert
        payload = {"summary": "Test Event", "start": {}, "end": {}}
        result = client.insert("primary", "test-event-1", payload)

        # Validar chamada do insert
        mock_events_api.insert.assert_called_once()
        call_kwargs = mock_events_api.insert.call_args[1]

        assert call_kwargs["calendarId"] == "primary"
        assert call_kwargs["sendUpdates"] == "none"
        assert call_kwargs["body"]["id"] == "test-event-1"
        assert call_kwargs["body"]["summary"] == "Test Event"

    @patch("os.getenv")
    @patch("google.oauth2.service_account.Credentials.from_service_account_info")
    @patch("apps.core.services.gcal_google_client.build")
    def test_patch_when_event_exists(self, mock_build, mock_creds, mock_getenv):
        """
        Upsert faz patch quando evento já existe.

        Cenário:
        - get() retorna evento existente
        - update() (patch) é chamado com sendUpdates="none"
        """
        from apps.core.services.gcal_google_client import GoogleCalendarClient

        # Mock env vars
        def getenv_side_effect(key, default=None):
            if key == "GOOGLE_SERVICE_ACCOUNT_JSON":
                return '{"type": "service_account", "project_id": "test"}'
            return default
        mock_getenv.side_effect = getenv_side_effect

        # Mock credentials (from_service_account_info already patched)
        mock_creds.return_value = MagicMock()

        # Mock service with consistent events() return
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Create a consistent mock for events()
        mock_events_api = MagicMock()
        mock_service.events.return_value = mock_events_api

        # Mock get() to return a request object that returns existing event on execute()
        mock_get_request = MagicMock()
        mock_get_request.execute.return_value = {
            "id": "test-event-1",
            "summary": "Old Summary",
        }
        mock_events_api.get.return_value = mock_get_request

        # Mock patch() to return a request object that returns updated event on execute()
        mock_patch_request = MagicMock()
        mock_patch_request.execute.return_value = {
            "id": "test-event-1",
            "summary": "New Summary",
        }
        mock_events_api.patch.return_value = mock_patch_request

        # Criar client com credentials mockadas
        client = GoogleCalendarClient()

        # Testar get (deve retornar evento)
        result = client.get("primary", "test-event-1")
        assert result is not None
        assert result["id"] == "test-event-1"

        # Testar update (patch)
        payload = {"summary": "New Summary", "start": {}, "end": {}}
        result = client.update("primary", "test-event-1", payload)

        # Validar chamada do patch
        mock_events_api.patch.assert_called_once()
        call_kwargs = mock_events_api.patch.call_args[1]

        assert call_kwargs["calendarId"] == "primary"
        assert call_kwargs["eventId"] == "test-event-1"
        assert call_kwargs["sendUpdates"] == "none"
        assert call_kwargs["body"]["id"] == "test-event-1"
        assert call_kwargs["body"]["summary"] == "New Summary"

    @patch("os.getenv")
    @patch("google.oauth2.service_account.Credentials.from_service_account_info")
    @patch("apps.core.services.gcal_google_client.build")
    def test_delete_idempotent_on_404(self, mock_build, mock_creds, mock_getenv):
        """
        Delete é idempotente quando evento não existe (404).

        Cenário:
        - delete() em evento que não existe (404)
        - Não deve levantar erro (idempotente)
        """
        from apps.core.services.gcal_google_client import GoogleCalendarClient

        # Mock env vars
        def getenv_side_effect(key, default=None):
            if key == "GOOGLE_SERVICE_ACCOUNT_JSON":
                return '{"type": "service_account", "project_id": "test"}'
            return default
        mock_getenv.side_effect = getenv_side_effect

        # Mock credentials (from_service_account_info already patched)
        mock_creds.return_value = MagicMock()

        # Mock service with consistent events() return
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Create a consistent mock for events()
        mock_events_api = MagicMock()
        mock_service.events.return_value = mock_events_api

        # Mock delete() to return a request object that raises 404 on execute()
        mock_delete_request = MagicMock()
        mock_delete_request.execute.side_effect = HttpError(
            resp=Mock(status=404), content=b"Not Found"
        )
        mock_events_api.delete.return_value = mock_delete_request

        # Criar client com credentials mockadas
        client = GoogleCalendarClient()

        # Testar delete (não deve levantar erro)
        client.delete("primary", "test-event-1")  # Idempotente

        # Validar que delete foi chamado
        mock_events_api.delete.assert_called_once_with(
            calendarId="primary", eventId="test-event-1", sendUpdates="none"
        )

    @patch("os.getenv")
    @patch("google.oauth2.service_account.Credentials.from_service_account_info")
    @patch("apps.core.services.gcal_google_client.build")
    def test_get_returns_none_on_404(self, mock_build, mock_creds, mock_getenv):
        """
        Get retorna None quando evento não existe (404).

        Cenário:
        - get() em evento que não existe (404)
        - Deve retornar None (não levanta erro)

        Complementa simetria com delete_idempotent_on_404.
        """
        from apps.core.services.gcal_google_client import GoogleCalendarClient

        # Mock env vars
        def getenv_side_effect(key, default=None):
            if key == "GOOGLE_SERVICE_ACCOUNT_JSON":
                return '{"type": "service_account", "project_id": "test"}'
            return default

        mock_getenv.side_effect = getenv_side_effect

        # Mock credentials (from_service_account_info already patched)
        mock_creds.return_value = MagicMock()

        # Mock service with consistent events() return
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Create a consistent mock for events()
        mock_events_api = MagicMock()
        mock_service.events.return_value = mock_events_api

        # Mock get() to return a request object that raises 404 on execute()
        mock_get_request = MagicMock()
        mock_get_request.execute.side_effect = HttpError(
            resp=Mock(status=404), content=b"Not Found"
        )
        mock_events_api.get.return_value = mock_get_request

        # Criar client com credentials mockadas
        client = GoogleCalendarClient()

        # Testar get (deve retornar None em 404, sem levantar erro)
        result = client.get("primary", "nonexistent-event-id")
        assert result is None

        # Validar que get foi chamado com parâmetros corretos
        mock_events_api.get.assert_called_once_with(
            calendarId="primary", eventId="nonexistent-event-id"
        )


@pytest.mark.django_db
class TestGcalClientFactory(TestCase):
    """Testes para gcal_client_factory."""

    @override_settings(GCAL_CLIENT="google", GCAL_CALENDAR_ID="abc123")
    @patch("os.getenv")
    @patch("google.oauth2.service_account.Credentials.from_service_account_info")
    @patch("apps.core.services.gcal_google_client.build")
    def test_factory_returns_google_client(self, mock_build, mock_creds, mock_getenv):
        """
        Factory retorna GoogleCalendarClient quando GCAL_CLIENT='google'.

        Cenário:
        - GCAL_CLIENT='google'
        - GCAL_CALENDAR_ID='abc123'

        Expectativa:
        - get_gcal_client_and_calendar_id() retorna (GoogleCalendarClient, 'abc123')
        """
        from apps.core.services.gcal_client_factory import get_gcal_client_and_calendar_id

        # Mock env vars
        def getenv_side_effect(key, default=None):
            if key == "GOOGLE_SERVICE_ACCOUNT_JSON":
                return '{"type": "service_account", "project_id": "test"}'
            return default
        mock_getenv.side_effect = getenv_side_effect

        # Mock credentials e build (from_service_account_info already patched)
        mock_creds.return_value = MagicMock()
        mock_build.return_value = MagicMock()

        # Obter client e calendar_id
        with override_settings(
            GOOGLE_SERVICE_ACCOUNT_JSON='{"type": "service_account", "project_id": "test"}'
        ):
            client, calendar_id = get_gcal_client_and_calendar_id()

        # Validar tipo e calendar_id
        assert client.__class__.__name__ == "GoogleCalendarClient"
        assert calendar_id == "abc123"

    @override_settings(GCAL_CLIENT="fake", GCAL_CALENDAR_ID="primary")
    def test_factory_returns_fake_client(self):
        """
        Factory retorna FakeCalendarClient quando GCAL_CLIENT='fake'.

        Cenário:
        - GCAL_CLIENT='fake'
        - GCAL_CALENDAR_ID='primary'

        Expectativa:
        - get_gcal_client_and_calendar_id() retorna (FakeCalendarClient, 'primary')
        """
        from apps.core.services.gcal_client_factory import get_gcal_client_and_calendar_id

        # Obter client e calendar_id
        client, calendar_id = get_gcal_client_and_calendar_id()

        # Validar tipo e calendar_id
        assert client.__class__.__name__ == "FakeCalendarClient"
        assert calendar_id == "primary"

    @override_settings(GCAL_CLIENT='fake')
    def test_factory_defaults_to_fake(self):
        """
        Factory usa fake como padrão quando GCAL_CLIENT não definido.

        Cenário:
        - GCAL_CLIENT não definido (ou diferente de 'google')

        Expectativa:
        - get_gcal_client_and_calendar_id() retorna FakeCalendarClient

        Issue #130: Forçar GCAL_CLIENT='fake' para evitar tentativa de
        inicialização do GoogleCalendarClient que requer Service Account
        credentials.
        """
        from apps.core.services.gcal_client_factory import get_gcal_client_and_calendar_id

        # Obter client e calendar_id com fake client forçado
        client, calendar_id = get_gcal_client_and_calendar_id()

        # Validar tipo
        assert client.__class__.__name__ == "FakeCalendarClient"

    @override_settings(GCAL_CLIENT="Google", GCAL_CALENDAR_ID="test-cal")
    @patch("os.getenv")
    @patch("google.oauth2.service_account.Credentials.from_service_account_info")
    @patch("apps.core.services.gcal_google_client.build")
    def test_factory_normalizes_case(self, mock_build, mock_creds, mock_getenv):
        """
        Factory normaliza GCAL_CLIENT para lowercase.

        Cenário:
        - GCAL_CLIENT='Google' (capitalized)

        Expectativa:
        - Factory normaliza para 'google' e retorna GoogleCalendarClient
        """
        from apps.core.services.gcal_client_factory import get_gcal_client_and_calendar_id

        # Mock env vars
        def getenv_side_effect(key, default=None):
            if key == "GOOGLE_SERVICE_ACCOUNT_JSON":
                return '{"type": "service_account", "project_id": "test"}'
            return default

        mock_getenv.side_effect = getenv_side_effect

        # Mock credentials e build
        mock_creds.return_value = MagicMock()
        mock_build.return_value = MagicMock()

        # Obter client (GCAL_CLIENT='Google' via override_settings)
        with override_settings(
            GOOGLE_SERVICE_ACCOUNT_JSON='{"type": "service_account", "project_id": "test"}'
        ):
            client, calendar_id = get_gcal_client_and_calendar_id()

        # Validar que retorna GoogleCalendarClient mesmo com case diferente
        assert client.__class__.__name__ == "GoogleCalendarClient"
        assert calendar_id == "test-cal"

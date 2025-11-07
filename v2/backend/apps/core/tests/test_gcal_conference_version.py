"""
Testes para conferenceDataVersion=1 em chamadas Google Calendar (RF06 - PR19).

Valida:
- insert() passa conferenceDataVersion=1
- patch() passa conferenceDataVersion=1
- Funciona mesmo quando payload não tem conferenceData (campo opcional)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestConferenceDataVersion:
    """Testes para parâmetro conferenceDataVersion=1"""

    @patch('apps.core.services.gcal_google_client.build')
    @patch('apps.core.services.gcal_google_client.service_account')
    def test_insert_passes_conference_data_version(self, mock_sa, mock_build):
        """
        RF06: insert() deve passar conferenceDataVersion=1.

        Cenário:
        - Payload com conferenceData (Google Meet)
        - Chamar insert()

        Resultado esperado: conferenceDataVersion=1 passado para API
        """
        from apps.core.services.gcal_google_client import GoogleCalendarClient

        # Mock credentials e service
        mock_creds = Mock()
        mock_sa.Credentials.from_service_account_info.return_value = mock_creds

        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock events().insert() chain
        mock_events = Mock()
        mock_service.events.return_value = mock_events

        mock_insert = Mock()
        mock_events.insert.return_value = mock_insert
        mock_insert.execute.return_value = {
            "id": "test-event-123",
            "hangoutLink": "https://meet.google.com/abc-defg-hij"
        }

        # Criar cliente
        client = GoogleCalendarClient(
            credentials_json='{"type": "service_account", "project_id": "test"}'
        )

        # Payload com conferenceData
        payload = {
            "summary": "Test Event with Meet",
            "start": {"dateTime": "2025-01-01T10:00:00Z"},
            "end": {"dateTime": "2025-01-01T11:00:00Z"},
            "conferenceData": {
                "createRequest": {
                    "requestId": "meet-123-abc",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"}
                }
            }
        }

        # Chamar insert
        result = client.insert(
            calendar_id="primary",
            event_id="test-event",
            payload=payload
        )

        # Verificar que insert foi chamado com conferenceDataVersion=1
        mock_events.insert.assert_called_once()
        call_kwargs = mock_events.insert.call_args[1]

        assert "conferenceDataVersion" in call_kwargs, \
            "conferenceDataVersion deve ser passado para insert()"
        assert call_kwargs["conferenceDataVersion"] == 1, \
            f"conferenceDataVersion deve ser 1, got {call_kwargs.get('conferenceDataVersion')}"

    @patch('apps.core.services.gcal_google_client.build')
    @patch('apps.core.services.gcal_google_client.service_account')
    def test_patch_passes_conference_data_version(self, mock_sa, mock_build):
        """
        RF06: patch() deve passar conferenceDataVersion=1.

        Cenário:
        - Payload com conferenceData (Google Meet)
        - Chamar update() (que usa patch internamente)

        Resultado esperado: conferenceDataVersion=1 passado para API
        """
        from apps.core.services.gcal_google_client import GoogleCalendarClient

        # Mock credentials e service
        mock_creds = Mock()
        mock_sa.Credentials.from_service_account_info.return_value = mock_creds

        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock events().patch() chain
        mock_events = Mock()
        mock_service.events.return_value = mock_events

        mock_patch = Mock()
        mock_events.patch.return_value = mock_patch
        mock_patch.execute.return_value = {
            "id": "test-event-456",
            "hangoutLink": "https://meet.google.com/xyz-uvw-rst"
        }

        # Criar cliente
        client = GoogleCalendarClient(
            credentials_json='{"type": "service_account", "project_id": "test"}'
        )

        # Payload com conferenceData
        payload = {
            "summary": "Updated Event with Meet",
            "conferenceData": {
                "createRequest": {
                    "requestId": "meet-456-def",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"}
                }
            }
        }

        # Chamar update
        result = client.update(
            calendar_id="primary",
            event_id="test-event",
            payload=payload
        )

        # Verificar que patch foi chamado com conferenceDataVersion=1
        mock_events.patch.assert_called_once()
        call_kwargs = mock_events.patch.call_args[1]

        assert "conferenceDataVersion" in call_kwargs, \
            "conferenceDataVersion deve ser passado para patch()"
        assert call_kwargs["conferenceDataVersion"] == 1, \
            f"conferenceDataVersion deve ser 1, got {call_kwargs.get('conferenceDataVersion')}"

    @patch('apps.core.services.gcal_google_client.build')
    @patch('apps.core.services.gcal_google_client.service_account')
    def test_insert_works_without_conference_data(self, mock_sa, mock_build):
        """
        RF06: insert() funciona mesmo sem conferenceData no payload.

        Cenário:
        - Payload SEM conferenceData (evento normal sem Meet)
        - Chamar insert()

        Resultado esperado: conferenceDataVersion=1 ainda é passado (campo opcional)
        """
        from apps.core.services.gcal_google_client import GoogleCalendarClient

        # Mock credentials e service
        mock_creds = Mock()
        mock_sa.Credentials.from_service_account_info.return_value = mock_creds

        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock events().insert() chain
        mock_events = Mock()
        mock_service.events.return_value = mock_events

        mock_insert = Mock()
        mock_events.insert.return_value = mock_insert
        mock_insert.execute.return_value = {"id": "test-event-789"}

        # Criar cliente
        client = GoogleCalendarClient(
            credentials_json='{"type": "service_account", "project_id": "test"}'
        )

        # Payload SEM conferenceData
        payload = {
            "summary": "Normal Event without Meet",
            "start": {"dateTime": "2025-01-02T14:00:00Z"},
            "end": {"dateTime": "2025-01-02T15:00:00Z"},
        }

        # Chamar insert
        result = client.insert(
            calendar_id="primary",
            event_id="test-event",
            payload=payload
        )

        # Verificar que insert foi chamado com conferenceDataVersion=1
        mock_events.insert.assert_called_once()
        call_kwargs = mock_events.insert.call_args[1]

        assert "conferenceDataVersion" in call_kwargs
        assert call_kwargs["conferenceDataVersion"] == 1

        # Verificar que não causou erro
        assert result["id"] == "test-event-789"

    @patch('apps.core.services.gcal_google_client.build')
    @patch('apps.core.services.gcal_google_client.service_account')
    def test_patch_works_without_conference_data(self, mock_sa, mock_build):
        """
        RF06: patch() funciona mesmo sem conferenceData no payload.

        Cenário:
        - Payload SEM conferenceData (atualização simples)
        - Chamar update()

        Resultado esperado: conferenceDataVersion=1 ainda é passado
        """
        from apps.core.services.gcal_google_client import GoogleCalendarClient

        # Mock credentials e service
        mock_creds = Mock()
        mock_sa.Credentials.from_service_account_info.return_value = mock_creds

        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock events().patch() chain
        mock_events = Mock()
        mock_service.events.return_value = mock_events

        mock_patch = Mock()
        mock_events.patch.return_value = mock_patch
        mock_patch.execute.return_value = {"id": "test-event-012"}

        # Criar cliente
        client = GoogleCalendarClient(
            credentials_json='{"type": "service_account", "project_id": "test"}'
        )

        # Payload SEM conferenceData
        payload = {
            "summary": "Updated Event Title",
            "description": "New description"
        }

        # Chamar update
        result = client.update(
            calendar_id="primary",
            event_id="test-event",
            payload=payload
        )

        # Verificar que patch foi chamado com conferenceDataVersion=1
        mock_events.patch.assert_called_once()
        call_kwargs = mock_events.patch.call_args[1]

        assert "conferenceDataVersion" in call_kwargs
        assert call_kwargs["conferenceDataVersion"] == 1

        # Verificar que não causou erro
        assert result["id"] == "test-event-012"

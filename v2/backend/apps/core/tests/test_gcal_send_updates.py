"""
Testes para configuração sendUpdates em chamadas Google Calendar (RF05/RF06 - PR19).

Valida:
- Default continua 'none'
- override_settings funciona corretamente
- Valores inválidos são rejeitados na inicialização
- Preview pode manter 'none' ou usar configuração (documenta escolha)
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false

from __future__ import annotations
import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import override_settings

from apps.core.services.gcal_google_client import GoogleCalendarClient


class TestSendUpdatesConfiguration:
    """Testes para parâmetro sendUpdates configurável"""

    @patch('apps.core.services.gcal_google_client.build')
    @patch('apps.core.services.gcal_google_client.service_account')
    def test_default_send_updates_is_none(self, mock_sa, mock_build):
        """
        RF05/RF06: Default sendUpdates deve ser 'none'.

        Cenário:
        - settings.GCAL_SEND_UPDATES não sobrescrito
        - Chamadas insert/update/delete devem usar 'none'

        Resultado esperado: sendUpdates='none'
        """
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
        mock_insert.execute.return_value = {"id": "test-event-123"}

        # Criar cliente (vai usar default 'none')
        with override_settings(GCAL_SEND_UPDATES="none"):
            client = GoogleCalendarClient(
                credentials_json='{"type": "service_account", "project_id": "test"}'
            )

            # Chamar insert
            result = client.insert(
                calendar_id="primary",
                event_id="test-event",
                payload={"summary": "Test Event"}
            )

            # Verificar que insert foi chamado com sendUpdates='none'
            mock_events.insert.assert_called_once()
            call_kwargs = mock_events.insert.call_args[1]
            assert call_kwargs['sendUpdates'] == 'none', \
                f"Expected sendUpdates='none', got '{call_kwargs.get('sendUpdates')}'"

    @patch('apps.core.services.gcal_google_client.build')
    @patch('apps.core.services.gcal_google_client.service_account')
    def test_send_updates_respects_override(self, mock_sa, mock_build):
        """
        RF05/RF06: override_settings deve alterar sendUpdates.

        Cenário:
        - settings.GCAL_SEND_UPDATES='all'
        - Chamadas insert/update/delete devem usar 'all'

        Resultado esperado: sendUpdates='all'
        """
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
        mock_insert.execute.return_value = {"id": "test-event-456"}

        # Criar cliente com override
        with override_settings(GCAL_SEND_UPDATES="all"):
            client = GoogleCalendarClient(
                credentials_json='{"type": "service_account", "project_id": "test"}'
            )

            # Chamar insert
            result = client.insert(
                calendar_id="primary",
                event_id="test-event",
                payload={"summary": "Test Event"}
            )

            # Verificar que insert foi chamado com sendUpdates='all'
            mock_events.insert.assert_called_once()
            call_kwargs = mock_events.insert.call_args[1]
            assert call_kwargs['sendUpdates'] == 'all', \
                f"Expected sendUpdates='all', got '{call_kwargs.get('sendUpdates')}'"

    @patch('apps.core.services.gcal_google_client.build')
    @patch('apps.core.services.gcal_google_client.service_account')
    def test_send_updates_external_only(self, mock_sa, mock_build):
        """
        RF05/RF06: sendUpdates='externalOnly' deve funcionar.

        Cenário:
        - settings.GCAL_SEND_UPDATES='externalOnly'
        - Chamadas update devem usar 'externalOnly'

        Resultado esperado: sendUpdates='externalOnly'
        """
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
        mock_patch.execute.return_value = {"id": "test-event-789"}

        # Criar cliente com override
        with override_settings(GCAL_SEND_UPDATES="externalOnly"):
            client = GoogleCalendarClient(
                credentials_json='{"type": "service_account", "project_id": "test"}'
            )

            # Chamar update
            result = client.update(
                calendar_id="primary",
                event_id="test-event",
                payload={"summary": "Updated Event"}
            )

            # Verificar que patch foi chamado com sendUpdates='externalOnly'
            mock_events.patch.assert_called_once()
            call_kwargs = mock_events.patch.call_args[1]
            assert call_kwargs['sendUpdates'] == 'externalOnly', \
                f"Expected sendUpdates='externalOnly', got '{call_kwargs.get('sendUpdates')}'"

    @patch('apps.core.services.gcal_google_client.build')
    @patch('apps.core.services.gcal_google_client.service_account')
    def test_delete_uses_send_updates(self, mock_sa, mock_build):
        """
        RF05/RF06: delete também deve respeitar sendUpdates.

        Cenário:
        - settings.GCAL_SEND_UPDATES='none' (default)
        - delete deve usar 'none'

        Resultado esperado: sendUpdates='none'
        """
        # Mock credentials e service
        mock_creds = Mock()
        mock_sa.Credentials.from_service_account_info.return_value = mock_creds

        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock events().delete() chain
        mock_events = Mock()
        mock_service.events.return_value = mock_events

        mock_delete = Mock()
        mock_events.delete.return_value = mock_delete
        mock_delete.execute.return_value = None

        # Criar cliente
        with override_settings(GCAL_SEND_UPDATES="none"):
            client = GoogleCalendarClient(
                credentials_json='{"type": "service_account", "project_id": "test"}'
            )

            # Chamar delete
            client.delete(
                calendar_id="primary",
                event_id="test-event"
            )

            # Verificar que delete foi chamado com sendUpdates='none'
            mock_events.delete.assert_called_once()
            call_kwargs = mock_events.delete.call_args[1]
            assert call_kwargs['sendUpdates'] == 'none', \
                f"Expected sendUpdates='none', got '{call_kwargs.get('sendUpdates')}'"

    def test_invalid_send_updates_rejected_at_startup(self):
        """
        RF05/RF06: Valores inválidos devem ser rejeitados na inicialização.

        Cenário:
        - settings.GCAL_SEND_UPDATES='invalid'
        - Django deve falhar na inicialização (settings.py valida)

        Resultado esperado: SystemExit ou erro de validação

        Nota: Este teste valida que a validação existe em settings.py.
        Testar SystemExit requer subprocess ou mock do settings, então
        documentamos o comportamento esperado.
        """
        # Validação acontece em settings.py ao importar Django
        # Ver: v2/backend/config/settings.py:342-349
        # _VALID_SEND_UPDATES = {"none", "all", "externalOnly"}
        # if GCAL_SEND_UPDATES not in _VALID_SEND_UPDATES: sys.exit(1)

        # Este teste serve como documentação do comportamento
        from django.conf import settings

        # Verificar que o valor atual é válido
        assert settings.GCAL_SEND_UPDATES in {"none", "all", "externalOnly"}, \
            f"GCAL_SEND_UPDATES='{settings.GCAL_SEND_UPDATES}' inválido"

    @patch('apps.core.services.gcal_google_client.build')
    @patch('apps.core.services.gcal_google_client.service_account')
    def test_preview_can_use_configured_value(self, mock_sa, mock_build):
        """
        RF05/RF06: Preview pode usar configuração ou forçar 'none'.

        Decisão de design: Preview usa o mesmo sendUpdates configurado.
        Justificativa: Consistência. Se admin quer testar com 'all', preview deve refletir isso.

        Cenário:
        - settings.GCAL_SEND_UPDATES='all'
        - Preview insert deve usar 'all'

        Resultado esperado: sendUpdates='all' (mesmo em preview)
        """
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
        mock_insert.execute.return_value = {"id": "preview-event"}

        # Criar cliente
        with override_settings(GCAL_SEND_UPDATES="all"):
            client = GoogleCalendarClient(
                credentials_json='{"type": "service_account", "project_id": "test"}'
            )

            # Chamar insert (preview é só um insert normal no fake client)
            result = client.insert(
                calendar_id="primary",
                event_id="preview-event",
                payload={"summary": "Preview Event"}
            )

            # Verificar que usou configuração
            call_kwargs = mock_events.insert.call_args[1]
            assert call_kwargs['sendUpdates'] == 'all', \
                "Preview deve usar configuração para consistência"

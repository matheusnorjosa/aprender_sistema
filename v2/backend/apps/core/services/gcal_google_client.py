"""
Google Calendar Client - Real implementation (TODO)

Cliente real para Google Calendar API.
Será implementado em futuro incremento (PR 4/N).
"""

from typing import Optional
from .gcal_sync_service import CalendarClientAdapter


class GoogleCalendarClient(CalendarClientAdapter):
    """
    Cliente real de Google Calendar API.

    TODO: Implementar com google-api-python-client
    - OAuth2/Service Account authentication
    - Rate limiting e retry logic
    - Error handling robusto
    - sendUpdates='none' (não envia emails aos participantes)
    - Usar eventId determinístico as-{id}

    Referências:
    - https://developers.google.com/calendar/api/v3/reference
    - https://github.com/googleapis/google-api-python-client
    """

    def __init__(self, credentials_json: str = None):
        """
        Inicializa cliente Google Calendar.

        Args:
            credentials_json: Path para arquivo de credenciais ou JSON string
        """
        raise NotImplementedError(
            "GoogleCalendarClient ainda não implementado. "
            "Use FakeCalendarClient (--client=fake) ou aguarde PR 4/N."
        )

    def get(self, calendar_id: str, event_id: str) -> Optional[dict]:
        """
        Busca evento por ID.

        TODO: Implementar com calendarService.events().get()
        """
        raise NotImplementedError("GoogleCalendarClient.get() não implementado")

    def insert(self, calendar_id: str, event_id: str, payload: dict) -> dict:
        """
        Cria novo evento.

        TODO: Implementar com calendarService.events().insert()
        - body={**payload, 'id': event_id}
        - sendUpdates='none'
        """
        raise NotImplementedError("GoogleCalendarClient.insert() não implementado")

    def update(self, calendar_id: str, event_id: str, payload: dict) -> dict:
        """
        Atualiza evento existente.

        TODO: Implementar com calendarService.events().update()
        - body={**payload, 'id': event_id}
        - sendUpdates='none'
        """
        raise NotImplementedError("GoogleCalendarClient.update() não implementado")

    def delete(self, calendar_id: str, event_id: str) -> None:
        """
        Deleta evento.

        TODO: Implementar com calendarService.events().delete()
        - sendUpdates='none'
        """
        raise NotImplementedError("GoogleCalendarClient.delete() não implementado")

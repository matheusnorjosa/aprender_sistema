"""
Factory para selecionar cliente do Google Calendar (fake vs real).

Retorna instância do cliente apropriado baseado em settings.GCAL_CLIENT.
"""

from typing import Tuple

from django.conf import settings

from apps.core.services.gcal_fake_client import FakeCalendarClient
from apps.core.services.gcal_google_client import GoogleCalendarClient
from apps.core.services.gcal_sync_service import CalendarClientAdapter


def get_gcal_client_and_calendar_id() -> Tuple[CalendarClientAdapter, str]:
    """
    Retorna cliente e calendar_id baseado em settings.

    Lê:
    - settings.GCAL_CLIENT (default "fake")
    - settings.GCAL_CALENDAR_ID (default "primary")

    Returns:
        Tuple[CalendarClientAdapter, str]: (client, calendar_id)

    Examples:
        >>> client, calendar_id = get_gcal_client_and_calendar_id()
        >>> event = client.get(calendar_id, "event-id")
    """
    gcal_client = getattr(settings, "GCAL_CLIENT", "fake")
    calendar_id = getattr(settings, "GCAL_CALENDAR_ID", "primary")

    if gcal_client == "google":
        # Cliente real do Google Calendar
        client = GoogleCalendarClient()
    else:
        # Cliente fake (default)
        client = FakeCalendarClient()

    return client, calendar_id

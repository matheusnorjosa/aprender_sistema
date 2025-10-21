"""
Factory para selecionar cliente do Google Calendar (fake vs real).

Retorna instância do cliente apropriado baseado em settings.GCAL_CLIENT.
"""

import os
from typing import TYPE_CHECKING, Tuple

from django.conf import settings

from apps.core.services.gcal_fake_client import FakeCalendarClient
from apps.core.services.gcal_google_client import GoogleCalendarClient

if TYPE_CHECKING:
    from apps.core.services.gcal_sync_service import CalendarClientAdapter


def get_gcal_client_and_calendar_id() -> Tuple["CalendarClientAdapter", str]:
    """
    Retorna cliente e calendar_id baseado em settings.

    Lê:
    - settings.GCAL_CLIENT (default "fake", fallback para env GCAL_CLIENT)
    - settings.GCAL_CALENDAR_ID (default "primary", fallback para env GCAL_CALENDAR_ID)

    Normaliza GCAL_CLIENT para lowercase para aceitar "Google", "GOOGLE", "google".

    Returns:
        Tuple[CalendarClientAdapter, str]: (client, calendar_id)

    Examples:
        >>> client, calendar_id = get_gcal_client_and_calendar_id()
        >>> event = client.get(calendar_id, "event-id")
    """
    # Normalizar para lowercase e aceitar fallback via os.getenv
    client_name = (
        getattr(settings, "GCAL_CLIENT", None) or os.getenv("GCAL_CLIENT") or "fake"
    ).lower()
    calendar_id = (
        getattr(settings, "GCAL_CALENDAR_ID", None)
        or os.getenv("GCAL_CALENDAR_ID")
        or "primary"
    )

    if client_name == "google":
        # Cliente real do Google Calendar
        client = GoogleCalendarClient()
    else:
        # Cliente fake (default)
        client = FakeCalendarClient()

    return client, calendar_id

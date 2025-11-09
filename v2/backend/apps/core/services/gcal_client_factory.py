"""
Factory para selecionar cliente do Google Calendar (fake vs real).

Retorna instância do cliente apropriado baseado em settings.GCAL_CLIENT.
"""

import os
from typing import TYPE_CHECKING, Tuple

from django.conf import settings

from apps.core.models import GoogleOAuthCredential
from apps.core.services.gcal_fake_client import FakeCalendarClient
from apps.core.services.gcal_google_client import GoogleCalendarClient
from apps.core.services.gcal_oauth_client import OAuthCalendarClient

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


def get_oauth_client_for_user(user) -> Tuple["CalendarClientAdapter", str]:
    """
    Retorna cliente OAuth e calendar_id para um usuário específico.

    Modo OAuth: Usa credenciais OAuth do usuário (GoogleOAuthCredential)
    para autenticar no Google Calendar API.

    Args:
        user: Instância de Usuario com GoogleOAuthCredential vinculada

    Returns:
        Tuple[CalendarClientAdapter, str]: (OAuthCalendarClient, calendar_id)

    Raises:
        ValueError: Se GCAL_AUTH_MODE != 'oauth'
        ValueError: Se usuário não possui GoogleOAuthCredential

    Examples:
        >>> client, calendar_id = get_oauth_client_for_user(request.user)
        >>> event = client.get(calendar_id, "event-id")

    Refs:
        - OAuth Phase 2: Factory/Routing
        - Issue #1 Sprint 1: OAuth implementation
    """
    # Validar modo OAuth
    auth_mode = getattr(settings, "GCAL_AUTH_MODE", "service_account")
    if auth_mode != "oauth":
        raise ValueError(
            f"GCAL_AUTH_MODE must be 'oauth' (current: '{auth_mode}'). "
            f"Use get_gcal_client_and_calendar_id() for service_account mode."
        )

    # Buscar credencial OAuth do usuário
    try:
        credential = GoogleOAuthCredential.objects.get(user=user)
    except GoogleOAuthCredential.DoesNotExist:
        raise ValueError(
            f"Google OAuth credential not found for user '{user.username}' (id={user.id}). "
            f"User must connect their Google account first."
        )

    # Ler calendar_id (mesma lógica da função atual)
    calendar_id = (
        getattr(settings, "GCAL_CALENDAR_ID", None)
        or os.getenv("GCAL_CALENDAR_ID")
        or "primary"
    )

    # Instanciar cliente OAuth com credencial do usuário
    client = OAuthCalendarClient(credential)

    return client, calendar_id

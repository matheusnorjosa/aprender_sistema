"""
Google Calendar Client - Real implementation

Cliente real para Google Calendar API via Service Account.
Mantém idempotência com eventId determinístico (asv2-{id}).
"""

import json
import logging
import os
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .gcal_sync_service import CalendarClientAdapter

logger = logging.getLogger(__name__)


class GoogleCalendarClient(CalendarClientAdapter):
    """
    Cliente real de Google Calendar API.

    Autenticação via Service Account.
    Idempotência garantida via eventId determinístico (asv2-{id}).
    sendUpdates='none' para não enviar emails aos participantes.

    Referências:
    - https://developers.google.com/calendar/api/v3/reference
    - https://github.com/googleapis/google-api-python-client
    """

    # Scopes necessários para Calendar API
    SCOPES = ["https://www.googleapis.com/auth/calendar"]

    def __init__(self, credentials_path: Optional[str] = None):
        """
        Inicializa cliente Google Calendar.

        Args:
            credentials_path: Path para arquivo JSON do Service Account.
                             Se None, tenta usar GOOGLE_SERVICE_ACCOUNT_JSON do env.

        Raises:
            ValueError: Se credenciais não forem fornecidas ou inválidas
            FileNotFoundError: Se arquivo de credenciais não existir
        """
        # Resolver path das credenciais
        creds_path = credentials_path or os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

        if not creds_path:
            raise ValueError(
                "Credenciais do Service Account não fornecidas. "
                "Forneça credentials_path ou defina GOOGLE_SERVICE_ACCOUNT_JSON."
            )

        if not os.path.exists(creds_path):
            raise FileNotFoundError(
                f"Arquivo de credenciais não encontrado: {creds_path}"
            )

        # Carregar credenciais do Service Account
        try:
            self.credentials = service_account.Credentials.from_service_account_file(
                creds_path, scopes=self.SCOPES
            )
        except Exception as e:
            raise ValueError(f"Erro ao carregar credenciais: {e}") from e

        # Build Calendar API service
        try:
            self.service = build("calendar", "v3", credentials=self.credentials)
        except Exception as e:
            raise ValueError(f"Erro ao inicializar Calendar API service: {e}") from e

        logger.info(
            "GoogleCalendarClient inicializado",
            extra={
                "service_account": creds_path,
                "scopes": self.SCOPES,
            },
        )

    def get(self, calendar_id: str, event_id: str) -> Optional[dict]:
        """
        Busca evento por ID.

        Args:
            calendar_id: ID do calendário Google
            event_id: ID do evento (formato: asv2-{id})

        Returns:
            dict: Evento do Google Calendar ou None se não encontrado

        Raises:
            HttpError: Erros da API (exceto 404)
        """
        try:
            event = (
                self.service.events()
                .get(calendarId=calendar_id, eventId=event_id)
                .execute()
            )

            logger.debug(
                "Event retrieved",
                extra={
                    "calendar_id": calendar_id,
                    "event_id": event_id,
                    "summary": event.get("summary"),
                },
            )

            return event

        except HttpError as e:
            if e.resp.status == 404:
                logger.debug(
                    "Event not found",
                    extra={"calendar_id": calendar_id, "event_id": event_id},
                )
                return None

            # Re-raise para outros erros (401, 403, 500, etc.)
            logger.error(
                "Error fetching event",
                extra={
                    "calendar_id": calendar_id,
                    "event_id": event_id,
                    "error": str(e),
                    "status": e.resp.status,
                },
            )
            raise

    def insert(self, calendar_id: str, event_id: str, payload: dict) -> dict:
        """
        Cria novo evento.

        Args:
            calendar_id: ID do calendário Google
            event_id: ID do evento (formato: asv2-{id})
            payload: Dados do evento (start, end, summary, etc.)

        Returns:
            dict: Evento criado pelo Google Calendar

        Raises:
            HttpError: Erros da API
        """
        # Injetar eventId no payload
        body = {**payload, "id": event_id}

        try:
            event = (
                self.service.events()
                .insert(
                    calendarId=calendar_id,
                    body=body,
                    sendUpdates="none",  # Não enviar emails
                )
                .execute()
            )

            logger.info(
                "Event created",
                extra={
                    "calendar_id": calendar_id,
                    "event_id": event_id,
                    "summary": payload.get("summary"),
                    "start": payload.get("start", {}).get("dateTime"),
                },
            )

            return event

        except HttpError as e:
            logger.error(
                "Error creating event",
                extra={
                    "calendar_id": calendar_id,
                    "event_id": event_id,
                    "error": str(e),
                    "status": e.resp.status,
                    "payload": json.dumps(payload, default=str),
                },
            )
            raise

    def update(self, calendar_id: str, event_id: str, payload: dict) -> dict:
        """
        Atualiza evento existente.

        Args:
            calendar_id: ID do calendário Google
            event_id: ID do evento (formato: asv2-{id})
            payload: Dados do evento (start, end, summary, etc.)

        Returns:
            dict: Evento atualizado pelo Google Calendar

        Raises:
            HttpError: Erros da API
        """
        # Injetar eventId no payload
        body = {**payload, "id": event_id}

        try:
            event = (
                self.service.events()
                .update(
                    calendarId=calendar_id,
                    eventId=event_id,
                    body=body,
                    sendUpdates="none",  # Não enviar emails
                )
                .execute()
            )

            logger.info(
                "Event updated",
                extra={
                    "calendar_id": calendar_id,
                    "event_id": event_id,
                    "summary": payload.get("summary"),
                    "start": payload.get("start", {}).get("dateTime"),
                },
            )

            return event

        except HttpError as e:
            logger.error(
                "Error updating event",
                extra={
                    "calendar_id": calendar_id,
                    "event_id": event_id,
                    "error": str(e),
                    "status": e.resp.status,
                    "payload": json.dumps(payload, default=str),
                },
            )
            raise

    def delete(self, calendar_id: str, event_id: str) -> None:
        """
        Deleta evento.

        Args:
            calendar_id: ID do calendário Google
            event_id: ID do evento (formato: asv2-{id})

        Raises:
            HttpError: Erros da API (exceto 404/410 que são tratados como sucesso)
        """
        try:
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id,
                sendUpdates="none",  # Não enviar emails
            ).execute()

            logger.info(
                "Event deleted",
                extra={"calendar_id": calendar_id, "event_id": event_id},
            )

        except HttpError as e:
            # 404 (Not Found) e 410 (Gone) são esperados e considerados sucesso
            if e.resp.status in [404, 410]:
                logger.debug(
                    "Event already deleted or not found",
                    extra={
                        "calendar_id": calendar_id,
                        "event_id": event_id,
                        "status": e.resp.status,
                    },
                )
                return

            # Re-raise para outros erros
            logger.error(
                "Error deleting event",
                extra={
                    "calendar_id": calendar_id,
                    "event_id": event_id,
                    "error": str(e),
                    "status": e.resp.status,
                },
            )
            raise

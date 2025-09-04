"""
Implementação real da integração com Google Calendar API.
Substitui os stubs por chamadas reais à API do Google.
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from django.conf import settings

from .error_handling import GoogleCalendarError, safe_google_calendar_operation

logger = logging.getLogger(__name__)


@dataclass
class CalendarEventResult:
    provider_event_id: str
    html_link: str | None = None
    meet_link: str | None = None


def is_enabled() -> bool:
    """Verifica se a integração com Google Calendar está habilitada."""
    return bool(getattr(settings, "FEATURE_GOOGLE_SYNC", False))


class GoogleCalendarService:
    """
    Serviço real para integração com Google Calendar API.
    Substitui o GoogleCalendarServiceStub com implementação real.
    """

    def __init__(self, calendar_id: Optional[str] = None):
        # Por padrão, usar o calendário "Formações" ou o configurado nas settings
        # Se não especificado, usa 'primary'
        self.calendar_id = calendar_id or getattr(
            settings, "GOOGLE_CALENDAR_CALENDAR_ID", "primary"
        )
        self._service = None

    def _get_service(self):
        """Inicializa e retorna o serviço do Google Calendar."""
        if self._service is not None:
            return self._service

        try:
            import json

            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            # Tentar usar OAuth2 credentials first (working)
            oauth_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "..",
                "google_authorized_user.json",
            )
            oauth_path = os.path.abspath(oauth_path)

            if os.path.exists(oauth_path):
                with open(oauth_path, "r") as f:
                    cred_info = json.load(f)

                # Adicionar escopo calendar se não existir
                scopes = cred_info.get("scopes", [])
                if "https://www.googleapis.com/auth/calendar" not in scopes:
                    scopes.append("https://www.googleapis.com/auth/calendar")
                    cred_info["scopes"] = scopes

                credentials = Credentials.from_authorized_user_info(cred_info, scopes)

                self._service = build("calendar", "v3", credentials=credentials)
                logger.info("Google Calendar service inicializado com OAuth2")
                return self._service

            # Fallback para service account
            from google.oauth2 import service_account

            credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if credentials_path and os.path.exists(credentials_path):
                SCOPES = ["https://www.googleapis.com/auth/calendar"]
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path, scopes=SCOPES
                )

                self._service = build("calendar", "v3", credentials=credentials)
                logger.info("Google Calendar service inicializado com Service Account")
                return self._service

            raise ValueError(
                "Nenhuma credencial válida encontrada (OAuth2 ou Service Account)"
            )

        except ImportError as e:
            logger.error(f"Bibliotecas Google não instaladas: {e}")
            raise RuntimeError(
                "Instale: pip install google-api-python-client google-auth"
            )
        except Exception as e:
            logger.error(f"Erro ao inicializar Google Calendar service: {e}")
            raise

    @safe_google_calendar_operation(max_attempts=3, operation_name="create_event")
    def create_event(self, gevent) -> dict:
        """
        Cria um evento no Google Calendar.

        Args:
            gevent: Objeto GoogleEvent com dados do evento

        Returns:
            dict: Resposta da API com id, htmlLink, etc.
        """
        if not is_enabled():
            logger.warning("Google Calendar sync desabilitado - evento não criado")
            return {"status": "skipped", "reason": "FEATURE_GOOGLE_SYNC=False"}

        try:
            service = self._get_service()

            # Construir evento no formato esperado pela API
            event_data = {
                "summary": gevent.summary,  # Corrigido: usar summary em vez de title
                "description": gevent.description or "",
                "start": {
                    "dateTime": gevent.start_iso,
                    "timeZone": "America/Sao_Paulo",
                },
                "end": {
                    "dateTime": gevent.end_iso,
                    "timeZone": "America/Sao_Paulo",
                },
                "location": gevent.location or "",
            }

            # Adicionar Google Meet se solicitado
            if gevent.conference:
                event_data["conferenceData"] = {
                    "createRequest": {
                        "requestId": f"meet-{gevent.start_iso}",
                        "conferenceSolutionKey": {"type": "hangoutsMeet"},
                    }
                }

            # Adicionar participantes se houver
            if hasattr(gevent, "attendees") and gevent.attendees:
                event_data["attendees"] = [
                    {"email": email} for email in gevent.attendees
                ]

            # Criar evento via API
            event = (
                service.events()
                .insert(
                    calendarId=self.calendar_id,
                    body=event_data,
                    conferenceDataVersion=1 if gevent.conference else 0,
                )
                .execute()
            )

            logger.info(f"Evento criado com sucesso: {event.get('id')}")

            # Retornar no formato esperado pelo sistema
            return {
                "id": event.get("id"),
                "htmlLink": event.get("htmlLink", ""),
                "hangoutLink": event.get("hangoutLink", ""),
                "status": event.get("status"),
                "created": event.get("created"),
                "updated": event.get("updated"),
            }

        except Exception as e:
            logger.error(f"Erro ao criar evento no Google Calendar: {e}")
            # Re-raise para que o sistema possa tratar adequadamente
            raise

    @safe_google_calendar_operation(max_attempts=3, operation_name="update_event")
    def update_event(self, provider_event_id: str, gevent) -> dict:
        """
        Atualiza um evento existente no Google Calendar.

        Args:
            provider_event_id: ID do evento no Google Calendar
            gevent: Objeto GoogleEvent com dados atualizados

        Returns:
            dict: Resposta da API atualizada
        """
        if not is_enabled():
            logger.warning("Google Calendar sync desabilitado - evento não atualizado")
            return {"status": "skipped", "reason": "FEATURE_GOOGLE_SYNC=False"}

        try:
            service = self._get_service()

            # Buscar evento atual
            current_event = (
                service.events()
                .get(calendarId=self.calendar_id, eventId=provider_event_id)
                .execute()
            )

            # Atualizar campos
            current_event.update(
                {
                    "summary": gevent.summary,  # Corrigido: usar summary em vez de title
                    "description": gevent.description or "",
                    "start": {
                        "dateTime": gevent.start_iso,
                        "timeZone": "America/Sao_Paulo",
                    },
                    "end": {
                        "dateTime": gevent.end_iso,
                        "timeZone": "America/Sao_Paulo",
                    },
                    "location": gevent.location or "",
                }
            )

            # Atualizar evento via API
            updated_event = (
                service.events()
                .update(
                    calendarId=self.calendar_id,
                    eventId=provider_event_id,
                    body=current_event,
                )
                .execute()
            )

            logger.info(f"Evento atualizado com sucesso: {updated_event.get('id')}")

            return {
                "id": updated_event.get("id"),
                "htmlLink": updated_event.get("htmlLink", ""),
                "hangoutLink": updated_event.get("hangoutLink", ""),
                "status": updated_event.get("status"),
                "updated": updated_event.get("updated"),
            }

        except Exception as e:
            logger.error(f"Erro ao atualizar evento no Google Calendar: {e}")
            raise

    @safe_google_calendar_operation(max_attempts=2, operation_name="delete_event")
    def delete_event(self, provider_event_id: str) -> bool:
        """
        Deleta um evento do Google Calendar.

        Args:
            provider_event_id: ID do evento no Google Calendar

        Returns:
            bool: True se deletado com sucesso
        """
        if not is_enabled():
            logger.warning("Google Calendar sync desabilitado - evento não deletado")
            return True  # Retorna True para não quebrar o fluxo

        try:
            service = self._get_service()

            service.events().delete(
                calendarId=self.calendar_id, eventId=provider_event_id
            ).execute()

            logger.info(f"Evento deletado com sucesso: {provider_event_id}")
            return True

        except Exception as e:
            logger.error(f"Erro ao deletar evento do Google Calendar: {e}")
            raise

    @safe_google_calendar_operation(max_attempts=2, operation_name="list_events")
    def list_events(
        self, max_results: int = 10, time_min: Optional[datetime] = None
    ) -> list:
        """
        Lista eventos do calendário (útil para debugging e testes).

        Args:
            max_results: Número máximo de eventos a retornar
            time_min: Data/hora mínima para filtrar eventos

        Returns:
            list: Lista de eventos
        """
        if not is_enabled():
            return []

        try:
            service = self._get_service()

            params = {
                "calendarId": self.calendar_id,
                "maxResults": max_results,
                "singleEvents": True,
                "orderBy": "startTime",
            }

            if time_min:
                params["timeMin"] = time_min.isoformat() + "Z"

            events_result = service.events().list(**params).execute()
            events = events_result.get("items", [])

            logger.info(f"Listados {len(events)} eventos do calendário")
            return events

        except Exception as e:
            logger.error(f"Erro ao listar eventos do Google Calendar: {e}")
            return []


# Funções de compatibilidade com o código existente
def create_event(solicitacao) -> CalendarEventResult:
    """
    Função de compatibilidade - agora usa GoogleCalendarService real.
    """
    if not is_enabled():
        raise RuntimeError("Calendar integration disabled")

    try:
        # Importar aqui para evitar dependências circulares
        from core.services.integrations.calendar_mapper import (
            map_solicitacao_to_google_event,
        )

        # Converter solicitacao para GoogleEvent
        gevent = map_solicitacao_to_google_event(solicitacao)

        # Usar serviço real
        service = GoogleCalendarService()
        result = service.create_event(gevent)

        # Converter para CalendarEventResult
        return CalendarEventResult(
            provider_event_id=result["id"],
            html_link=result.get("htmlLink"),
            meet_link=result.get("hangoutLink"),
        )

    except Exception as e:
        logger.error(f"Erro na função create_event: {e}")
        raise


def update_event(evento_gc, solicitacao) -> None:
    """
    Função de compatibilidade - agora usa GoogleCalendarService real.
    """
    if not is_enabled():
        raise RuntimeError("Calendar integration disabled")

    try:
        from core.services.integrations.calendar_mapper import (
            map_solicitacao_to_google_event,
        )

        gevent = map_solicitacao_to_google_event(solicitacao)
        service = GoogleCalendarService()
        service.update_event(evento_gc.provider_event_id, gevent)

    except Exception as e:
        logger.error(f"Erro na função update_event: {e}")
        raise


def delete_event(evento_gc) -> None:
    """
    Função de compatibilidade - agora usa GoogleCalendarService real.
    """
    if not is_enabled():
        raise RuntimeError("Calendar integration disabled")

    try:
        service = GoogleCalendarService()
        service.delete_event(evento_gc.provider_event_id)

    except Exception as e:
        logger.error(f"Erro na função delete_event: {e}")
        raise

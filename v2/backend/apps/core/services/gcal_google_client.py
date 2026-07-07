"""
Google Calendar Client - Real implementation

Cliente real para Google Calendar API usando Service Account.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Callable
from typing import TypeVar

from django.conf import settings

import httplib2
from google.oauth2 import service_account
from google_auth_httplib2 import AuthorizedHttp
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from apps.core.services.gcal_sync_service import CalendarClientAdapter
from apps.core.types import CalendarId, EventId, JsonDict

logger = logging.getLogger(__name__)

# Type variable para retry genérico
T = TypeVar("T")


class GoogleCalendarClient(CalendarClientAdapter):
    """
    Cliente real de Google Calendar API.

    Autenticação via Service Account:
    - GOOGLE_SERVICE_ACCOUNT_FILE (path para arquivo JSON)
    - GOOGLE_SERVICE_ACCOUNT_JSON (conteúdo JSON inline)

    Características:
    - sendUpdates='none' (não envia emails aos participantes)
    - Retry exponencial para 429/5xx
    - Tratamento de 404 como None/idempotente
    - Idempotência via event.id
    """

    SCOPES = ["https://www.googleapis.com/auth/calendar"]

    def __init__(self, credentials_json: str | None = None) -> None:
        """
        Inicializa cliente Google Calendar.

        Args:
            credentials_json: Path para arquivo de credenciais ou JSON string.
                             Se None, busca de envs GOOGLE_SERVICE_ACCOUNT_FILE
                             ou GOOGLE_SERVICE_ACCOUNT_JSON.
        """
        # Obter credenciais
        if credentials_json:
            # Recebido como argumento (pode ser path ou JSON inline)
            creds_data = self._load_credentials(credentials_json)
        else:
            # Buscar de envs
            sa_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
            sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

            if sa_file:
                creds_data = self._load_credentials(sa_file)
            elif sa_json:
                creds_data = json.loads(sa_json)
            else:
                raise ValueError(
                    "Service Account credentials not found. "
                    "Set GOOGLE_SERVICE_ACCOUNT_FILE or GOOGLE_SERVICE_ACCOUNT_JSON"
                )

        # Criar credentials
        self.credentials = service_account.Credentials.from_service_account_info(creds_data, scopes=self.SCOPES)

        # Build service com timeout explicito no transporte httplib2 (GCAL_HTTP_TIMEOUT,
        # default 10s) em vez do default de 60s do googleapiclient -> num stall de rede a
        # chamada .execute() falha ~6x mais rapido e libera o worker do gunicorn (incidente
        # 2026-07-06). AuthorizedHttp reaplica as credenciais sobre o http com timeout.
        authorized_http = AuthorizedHttp(self.credentials, http=httplib2.Http(timeout=settings.GCAL_HTTP_TIMEOUT))
        self.service = build("calendar", "v3", http=authorized_http, cache_discovery=False)

        logger.info("GoogleCalendarClient initialized with Service Account")

    def _load_credentials(self, credentials_json: str) -> JsonDict:
        """
        Carrega credenciais de arquivo ou string JSON.

        Args:
            credentials_json: Path para arquivo ou JSON string

        Returns:
            dict com credenciais
        """
        # Tentar como arquivo primeiro
        if os.path.exists(credentials_json):
            with open(credentials_json, "r") as f:
                return json.load(f)

        # Senão, tentar como JSON inline
        try:
            return json.loads(credentials_json)
        except json.JSONDecodeError:
            raise ValueError("Invalid credentials: not a file or valid JSON")

    def _retry_with_backoff(self, func: Callable[[], T], max_retries: int = 3) -> T:
        """
        Executa função com retry exponencial para 429/5xx.

        Args:
            func: Função a executar
            max_retries: Número máximo de retries

        Returns:
            Resultado da função

        Raises:
            HttpError: Se todas as tentativas falharem
        """
        for attempt in range(max_retries + 1):
            try:
                return func()
            except HttpError as e:
                status = e.resp.status

                # 404 não deve fazer retry (esperado em alguns casos)
                if status == 404:
                    raise

                # 429 (rate limit) ou 5xx (server error) → retry
                if status == 429 or status >= 500:
                    if attempt < max_retries:
                        # Backoff exponencial: 1s, 2s, 4s
                        wait_time = 2**attempt
                        logger.warning(
                            f"Request failed with {status}, retrying in {wait_time}s "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(wait_time)
                        continue

                # Outros erros ou max retries atingido
                raise

    def get(self, calendar_id: CalendarId, event_id: EventId) -> JsonDict | None:
        """
        Busca evento por ID.

        Args:
            calendar_id: ID do calendário
            event_id: ID do evento

        Returns:
            dict com evento ou None se não encontrado
        """

        def _get():
            return self.service.events().get(calendarId=calendar_id, eventId=event_id).execute()

        try:
            return self._retry_with_backoff(_get)
        except HttpError as e:
            if e.resp.status == 404:
                # Evento não existe
                return None
            raise

    def insert(self, calendar_id: CalendarId, event_id: EventId, payload: JsonDict) -> JsonDict:
        """
        Cria novo evento.

        Args:
            calendar_id: ID do calendário
            event_id: ID do evento (idempotência)
            payload: Dados do evento

        Returns:
            dict com evento criado
        """
        # Garantir que o payload tenha o event_id
        body = {**payload, "id": event_id}

        # RF05/RF06: Ler sendUpdates do settings (configurável via env)
        send_updates = getattr(settings, "GCAL_SEND_UPDATES", "none")

        def _insert():
            return (
                self.service.events()
                .insert(
                    calendarId=calendar_id,
                    body=body,
                    sendUpdates=send_updates,
                    conferenceDataVersion=1,  # RF06: Necessário para criar Google Meet
                )
                .execute()
            )

        return self._retry_with_backoff(_insert)

    def update(self, calendar_id: CalendarId, event_id: EventId, payload: JsonDict) -> JsonDict:
        """
        Atualiza evento existente (usa PATCH para atualização parcial).

        Args:
            calendar_id: ID do calendário
            event_id: ID do evento
            payload: Dados do evento

        Returns:
            dict com evento atualizado
        """
        # Garantir que o payload tenha o event_id
        body = {**payload, "id": event_id}

        # RF05/RF06: Ler sendUpdates do settings (configurável via env)
        send_updates = getattr(settings, "GCAL_SEND_UPDATES", "none")

        def _update():
            return (
                self.service.events()
                .patch(
                    calendarId=calendar_id,
                    eventId=event_id,
                    body=body,
                    sendUpdates=send_updates,
                    conferenceDataVersion=1,  # RF06: Necessário para atualizar Google Meet
                )
                .execute()
            )

        return self._retry_with_backoff(_update)

    def delete(self, calendar_id: CalendarId, event_id: EventId) -> None:
        """
        Deleta evento.

        Args:
            calendar_id: ID do calendário
            event_id: ID do evento
        """
        # RF05/RF06: Ler sendUpdates do settings (configurável via env)
        send_updates = getattr(settings, "GCAL_SEND_UPDATES", "none")

        def _delete():
            return (
                self.service.events()
                .delete(calendarId=calendar_id, eventId=event_id, sendUpdates=send_updates)
                .execute()
            )

        try:
            self._retry_with_backoff(_delete)
        except HttpError as e:
            if e.resp.status == 404:
                # Evento já não existe → idempotente
                logger.debug(f"Event {event_id} already deleted (404)")
                return
            raise

    def list_calendars(self) -> list[JsonDict]:
        """
        Lista calendários disponíveis via Calendar API.

        Returns:
            Lista de dicts com informações dos calendários:
            [{"id": str, "summary": str, "primary": bool}, ...]
        """

        def _list_calendars():
            # Usando calendarList API para listar calendários do usuário
            calendar_list = self.service.calendarList().list().execute()
            items = calendar_list.get("items", [])

            # Formatar para estrutura consistente
            return [
                {
                    "id": cal.get("id"),
                    "summary": cal.get("summary", ""),
                    "primary": cal.get("primary", False),
                }
                for cal in items
            ]

        return self._retry_with_backoff(_list_calendars)

    def list_events(
        self,
        calendar_id: str,
        *,
        time_min: str | None = None,
        time_max: str | None = None,
        max_results: int = 100,
    ) -> list[JsonDict]:
        """
        Lista eventos de um calendário via Google Calendar API.

        Args:
            calendar_id: ID do calendário
            time_min: Início do intervalo (RFC3339)
            time_max: Fim do intervalo (RFC3339)
            max_results: Máximo de eventos (default 100, max 2500)

        Returns:
            Lista de eventos formatados
        """

        def _list_events():
            params: dict[str, object] = {
                "calendarId": calendar_id,
                "maxResults": min(max_results, 2500),
                "singleEvents": True,
                "orderBy": "startTime",
            }
            if time_min:
                params["timeMin"] = time_min
            if time_max:
                params["timeMax"] = time_max

            result = self.service.events().list(**params).execute()
            items = result.get("items", [])

            return [
                {
                    "id": evt.get("id", ""),
                    "summary": evt.get("summary", "(sem título)"),
                    "start": evt.get("start", {}).get("dateTime") or evt.get("start", {}).get("date", ""),
                    "end": evt.get("end", {}).get("dateTime") or evt.get("end", {}).get("date", ""),
                    "status": evt.get("status", ""),
                    "htmlLink": evt.get("htmlLink", ""),
                    "location": evt.get("location", ""),
                    "creator": evt.get("creator", {}).get("email", ""),
                }
                for evt in items
            ]

        return self._retry_with_backoff(_list_events)

    def health_check(self) -> JsonDict:
        """
        Verifica saúde da integração com Google Calendar API.

        Tenta listar calendários para validar autenticação e conectividade.

        Returns:
            dict com status: {"status": "healthy"|"unhealthy", "details": str}
        """
        try:
            # Tentar listar calendários como health check
            calendars = self.list_calendars()
            return {
                "status": "healthy",
                "client_type": "google",
                "details": f"Successfully connected to Google Calendar API. {len(calendars)} calendars found.",
            }
        except Exception as e:
            logger.error(f"Google Calendar health check failed: {e}")
            return {
                "status": "unhealthy",
                "client_type": "google",
                "details": "Health check failed.",
            }

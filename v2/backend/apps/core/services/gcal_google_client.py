"""
Google Calendar Client - Real implementation

Cliente real para Google Calendar API usando Service Account.
"""

import json
import logging
import os
import time
from typing import Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from apps.core.services.gcal_sync_service import CalendarClientAdapter

logger = logging.getLogger(__name__)


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

    def __init__(self, credentials_json: str = None):
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
        self.credentials = service_account.Credentials.from_service_account_info(
            creds_data, scopes=self.SCOPES
        )

        # Build service
        self.service = build(
            "calendar", "v3", credentials=self.credentials, cache_discovery=False
        )

        logger.info("GoogleCalendarClient initialized with Service Account")

    def _load_credentials(self, credentials_json: str) -> dict:
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
            raise ValueError(f"Invalid credentials: not a file or valid JSON")

    def _retry_with_backoff(self, func, max_retries=3):
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

    def get(self, calendar_id: str, event_id: str) -> Optional[dict]:
        """
        Busca evento por ID.

        Args:
            calendar_id: ID do calendário
            event_id: ID do evento

        Returns:
            dict com evento ou None se não encontrado
        """

        def _get():
            return (
                self.service.events()
                .get(calendarId=calendar_id, eventId=event_id)
                .execute()
            )

        try:
            return self._retry_with_backoff(_get)
        except HttpError as e:
            if e.resp.status == 404:
                # Evento não existe
                return None
            raise

    def insert(self, calendar_id: str, event_id: str, payload: dict) -> dict:
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

        def _insert():
            return (
                self.service.events()
                .insert(calendarId=calendar_id, body=body, sendUpdates="none")
                .execute()
            )

        return self._retry_with_backoff(_insert)

    def update(self, calendar_id: str, event_id: str, payload: dict) -> dict:
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

        def _update():
            return (
                self.service.events()
                .patch(
                    calendarId=calendar_id, eventId=event_id, body=body, sendUpdates="none"
                )
                .execute()
            )

        return self._retry_with_backoff(_update)

    def delete(self, calendar_id: str, event_id: str) -> None:
        """
        Deleta evento.

        Args:
            calendar_id: ID do calendário
            event_id: ID do evento
        """

        def _delete():
            return (
                self.service.events()
                .delete(calendarId=calendar_id, eventId=event_id, sendUpdates="none")
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

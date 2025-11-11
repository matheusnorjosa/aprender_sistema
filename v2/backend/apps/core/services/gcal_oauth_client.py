"""
Google Calendar Client - OAuth implementation

Cliente OAuth para Google Calendar API usando credenciais de usuário.
Permite que usuários do grupo Controle publiquem eventos usando suas próprias contas Google.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.utils import timezone
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from apps.core.services.gcal_sync_service import CalendarClientAdapter
from apps.core.types import CalendarId, EventId, JsonDict

if TYPE_CHECKING:
    from apps.core.models import GoogleOAuthCredential

logger: logging.Logger = logging.getLogger(__name__)


class OAuthCalendarClient(CalendarClientAdapter):
    """
    Cliente OAuth de Google Calendar API.

    Autenticação via OAuth 2.0 (user credentials):
    - Usa GoogleOAuthCredential (access_token, refresh_token)
    - Refresh automático antes de construir service
    - Token refresh thread-safe via refresh_access_token_safe()

    Características:
    - sendUpdates configurável via GCAL_SEND_UPDATES
    - Retry exponencial para 429/5xx
    - Tratamento de 404 como None/idempotente
    - Idempotência via event.id

    Sprint 1 (Issue #1): OAuth Phase 1 - Cliente OAuth
    """

    SCOPES = ["https://www.googleapis.com/auth/calendar"]

    def __init__(self, credential: GoogleOAuthCredential) -> None:
        """
        Inicializa cliente Google Calendar com OAuth credentials.

        Args:
            credential: Instância de GoogleOAuthCredential

        Raises:
            ValueError: Se client_id/client_secret não configurados
            Exception: Se refresh falhar
        """
        from apps.core.services.google_oauth import (
            _decrypt_token,
            refresh_access_token_safe,
        )

        # Validar que credential é uma instância de GoogleOAuthCredential
        # Importar aqui para evitar circular import
        from apps.core.models import GoogleOAuthCredential

        if not isinstance(credential, GoogleOAuthCredential):
            raise TypeError(
                f"Expected GoogleOAuthCredential instance, got {type(credential)}"
            )

        # Refresh token se expirado (thread-safe com select_for_update)
        if credential.is_expired():
            logger.info(
                f"🔄 Access token expired for {credential.google_email}, refreshing..."
            )
            credential = refresh_access_token_safe(credential)
        else:
            logger.debug(
                f"✅ Access token still valid for {credential.google_email}, "
                f"expires at {credential.token_expiry}"
            )

        # Obter client_id e client_secret do env
        client_id = os.getenv("GCAL_OAUTH_CLIENT_ID")
        client_secret = os.getenv("GCAL_OAUTH_CLIENT_SECRET")

        if not client_id or not client_secret:
            raise ValueError(
                "❌ GCAL_OAUTH_CLIENT_ID e GCAL_OAUTH_CLIENT_SECRET não configuradas"
            )

        # Descriptografar tokens
        access_token = _decrypt_token(credential.access_token_encrypted)
        refresh_token = _decrypt_token(credential.refresh_token_encrypted)

        # Criar google.oauth2.credentials.Credentials
        self.credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=self.SCOPES,
        )

        # Build service
        self.service = build(
            "calendar", "v3", credentials=self.credentials, cache_discovery=False
        )

        # Armazenar referência ao credential para logging
        self.credential = credential

        logger.info(
            f"✅ OAuthCalendarClient initialized for {credential.google_email} "
            f"(user_id={credential.user_id})"
        )

    def get_default_calendar_id(self) -> str:
        """
        Retorna calendar_id preferido do usuário OAuth.

        Ordem de preferência:
        1. default_calendar_id configurado pelo usuário
        2. google_email (calendário principal)

        Returns:
            ID do calendário a ser usado
        """
        # Preferir calendário selecionado pelo usuário
        if self.credential.default_calendar_id:
            calendar_id = self.credential.default_calendar_id
            logger.debug(
                f"📅 Using user-selected calendar: {calendar_id}"
            )
            return calendar_id

        # Fallback: usar calendário principal (email)
        calendar_id = self.credential.google_email
        logger.debug(
            f"📧 Using primary calendar (no selection): {calendar_id}"
        )
        return calendar_id

    def _resolve_calendar_id(self, calendar_id: str) -> str:
        """
        Resolve calendar_id para OAuth.

        Com OAuth, se o calendar_id for o email principal do usuário OAuth,
        devemos usar "primary" em vez do email.

        Args:
            calendar_id: ID do calendário ("primary" ou email)

        Returns:
            "primary" para calendário principal, ou calendar_id original para outros
        """
        # Se for o email principal do usuário OAuth, usar "primary"
        if calendar_id == self.credential.google_email:
            logger.debug(
                f"📧 Resolved {calendar_id} → 'primary' for OAuth user"
            )
            return "primary"
        # Caso contrário, usar o calendar_id original
        return calendar_id

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
                            f"(attempt {attempt + 1}/{max_retries}) "
                            f"[user: {self.credential.google_email}]"
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
        calendar_id = self._resolve_calendar_id(calendar_id)

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
        calendar_id = self._resolve_calendar_id(calendar_id)

        # Garantir que o payload tenha o event_id
        body = {**payload, "id": event_id}

        # DEBUG: Log body antes de enviar
        logger.debug(
            f"🔍 OAuthClient.insert() - calendar_id={calendar_id}, "
            f"event_id={event_id}, body_has_id={'id' in body}, body_id={body.get('id')}"
        )

        # RF05/RF06: Ler sendUpdates do settings (configurável via env)
        send_updates = getattr(settings, "GCAL_SEND_UPDATES", "none")

        def _insert():
            try:
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
            except Exception as e:
                logger.error(
                    f"❌ Google Calendar API error - calendar_id={calendar_id}, "
                    f"event_id={body.get('id')}, error={str(e)}"
                )
                raise

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
        calendar_id = self._resolve_calendar_id(calendar_id)

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

    def delete(self, calendar_id: str, event_id: str) -> None:
        """
        Deleta evento.

        Args:
            calendar_id: ID do calendário
            event_id: ID do evento
        """
        calendar_id = self._resolve_calendar_id(calendar_id)

        # RF05/RF06: Ler sendUpdates do settings (configurável via env)
        send_updates = getattr(settings, "GCAL_SEND_UPDATES", "none")

        def _delete():
            return (
                self.service.events()
                .delete(
                    calendarId=calendar_id, eventId=event_id, sendUpdates=send_updates
                )
                .execute()
            )

        try:
            self._retry_with_backoff(_delete)
        except HttpError as e:
            if e.resp.status == 404:
                # Evento já não existe → idempotente
                logger.debug(
                    f"Event {event_id} already deleted (404) "
                    f"[user: {self.credential.google_email}]"
                )
                return
            raise

    def list_calendars(self) -> list[JsonDict]:
        """
        Lista calendários disponíveis via Calendar API.

        Returns:
            Lista de dicts com informações dos calendários:
            [{"id": str, "summary": str, "primary": bool, "accessRole": str}, ...]
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
                    "accessRole": cal.get("accessRole", ""),  # owner, writer, reader, freeBusyReader
                }
                for cal in items
            ]

        return self._retry_with_backoff(_list_calendars)

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
                "client_type": "oauth",
                "google_email": self.credential.google_email,
                "user_id": self.credential.user_id,
                "details": f"Successfully connected to Google Calendar API. {len(calendars)} calendars found.",
            }
        except Exception as e:
            logger.error(
                f"Google Calendar OAuth health check failed for "
                f"{self.credential.google_email}: {e}"
            )
            return {
                "status": "unhealthy",
                "client_type": "oauth",
                "google_email": self.credential.google_email,
                "user_id": self.credential.user_id,
                "details": f"Error: {str(e)}",
            }

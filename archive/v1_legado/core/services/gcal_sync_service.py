"""
Google Calendar Sync Service - DAT-P04-GCAL-v2
==============================================

Serviço para sincronização idempotente de eventos do Google Calendar.
Usa extendedProperties.private.external_hash para garantir idempotência.

Stack: Python 3.13 | Django 5.2 | Google Calendar API v3
Timezone: America/Fortaleza
"""

import json
import logging
import os
import time
from typing import Dict, List, Optional, Tuple

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as SACredentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]
TIMEZONE = "America/Fortaleza"


def build_calendar_service():
    """
    Constrói o serviço do Google Calendar com autenticação.

    Suporta duas formas de autenticação (ordem de prioridade):
    1. Service Account JSON via env GOOGLE_SERVICE_ACCOUNT_JSON
    2. OAuth client via token salvo em .gcal_token.json

    Returns:
        service: Google Calendar API service resource

    Raises:
        ValueError: Se nenhuma credencial válida for encontrada
        Exception: Se houver erro na autenticação
    """
    creds = None

    # Tentar Service Account JSON primeiro (caminho ou inline)
    sa_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_PATH")
    sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

    # Prioridade: arquivo > inline JSON
    if sa_path and os.path.exists(sa_path):
        try:
            with open(sa_path, "r") as f:
                sa_data = json.load(f)
            creds = SACredentials.from_service_account_info(
                sa_data, scopes=CALENDAR_SCOPES
            )
            logger.info(
                f"✓ Google Calendar autenticado via Service Account (arquivo: {sa_path})"
            )
            return build("calendar", "v3", credentials=creds)
        except Exception as e:
            logger.warning(f"Erro ao usar Service Account de arquivo: {e}")

    elif sa_json:
        try:
            # Suporta JSON inline, base64 ou raw
            sa_data = json.loads(sa_json)
            creds = SACredentials.from_service_account_info(
                sa_data, scopes=CALENDAR_SCOPES
            )
            logger.info("✓ Google Calendar autenticado via Service Account (inline)")
            return build("calendar", "v3", credentials=creds)
        except json.JSONDecodeError as e:
            logger.warning(f"Service Account JSON inválido: {e}")
        except Exception as e:
            logger.warning(f"Erro ao usar Service Account inline: {e}")

    # Fallback para OAuth client
    token_path = ".gcal_token.json"

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, CALENDAR_SCOPES)

    # Refresh token se expirado
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            logger.info("✓ Token OAuth renovado")
        except Exception as e:
            logger.error(f"Erro ao renovar token OAuth: {e}")
            creds = None

    if creds and creds.valid:
        # Salvar credenciais atualizadas
        with open(token_path, "w") as token:
            token.write(creds.to_json())

        logger.info("✓ Google Calendar autenticado via OAuth")
        return build("calendar", "v3", credentials=creds)

    # Nenhuma credencial válida
    raise ValueError(
        "Nenhuma credencial válida encontrada. Configure GOOGLE_SERVICE_ACCOUNT_JSON "
        "ou execute o fluxo OAuth para gerar .gcal_token.json"
    )


def find_event_by_hash(
    service, calendar_id: str, external_hash: str
) -> Tuple[int, Optional[List[Dict]]]:
    """
    Busca eventos por external_hash usando privateExtendedProperty.

    Args:
        service: Google Calendar service resource
        calendar_id: ID do calendário
        external_hash: Hash SHA1 do evento

    Returns:
        Tuple (count, events):
            - count: 0, 1, ou >1
            - events: Lista de eventos encontrados (None se count=0)

    Raises:
        HttpError: Se houver erro na API
    """
    try:
        # Query por privateExtendedProperty
        # Formato: privateExtendedProperty=external_hash=<hash>
        query = f"privateExtendedProperty=external_hash={external_hash}"

        result = (
            service.events()
            .list(
                calendarId=calendar_id,
                privateExtendedProperty=query,
                maxResults=10,  # Protege contra muitos duplicados
            )
            .execute()
        )

        items = result.get("items", [])
        count = len(items)

        if count == 0:
            return (0, None)
        elif count == 1:
            return (1, items)
        else:
            # Duplicados remotos (não deveria acontecer)
            logger.warning(
                f"⚠ Encontrados {count} eventos com external_hash={external_hash}"
            )
            return (count, items)

    except HttpError as e:
        logger.error(f"Erro ao buscar evento por hash: {e}")
        raise


def create_event(service, calendar_id: str, payload: Dict) -> Dict:
    """
    Cria evento no Google Calendar com idempotência.

    Args:
        service: Google Calendar service resource
        calendar_id: ID do calendário
        payload: Dict com campos do evento (summary, start, end, etc.)

    Returns:
        Dict: Evento criado (response da API)

    Raises:
        HttpError: Se houver erro na criação (4xx/5xx)

    Example payload:
        {
            "summary": "Evento Teste",
            "location": "Fortaleza/CE",
            "description": "Descrição...",
            "start": {"dateTime": "2025-01-15T09:00:00", "timeZone": "America/Fortaleza"},
            "end": {"dateTime": "2025-01-15T12:00:00", "timeZone": "America/Fortaleza"},
            "attendees": [{"email": "test@example.com"}],
            "extendedProperties": {
                "private": {"external_hash": "abc123..."}
            }
        }
    """
    try:
        # Retry simples para 5xx e 429
        max_retries = 3
        for attempt in range(max_retries):
            try:
                event = (
                    service.events()
                    .insert(calendarId=calendar_id, body=payload)
                    .execute()
                )

                logger.info(
                    f"✓ Evento criado: {event.get('id')} | {event.get('summary')}"
                )
                return event

            except HttpError as e:
                status_code = e.resp.status

                # 429 (rate limit) ou 5xx (erro servidor) → retry com backoff
                if status_code in [429, 500, 502, 503] and attempt < max_retries - 1:
                    wait_time = (2**attempt) * 1  # Backoff exponencial: 1s, 2s, 4s
                    logger.warning(
                        f"⚠ HTTP {status_code}, tentando novamente em {wait_time}s..."
                    )
                    time.sleep(wait_time)
                    continue

                # 4xx (erro cliente) → não fazer retry
                logger.error(f"Erro ao criar evento (HTTP {status_code}): {e}")
                raise

    except Exception as e:
        logger.error(f"Erro inesperado ao criar evento: {e}")
        raise


def update_event(service, calendar_id: str, event_id: str, payload: Dict) -> Dict:
    """
    Atualiza evento existente no Google Calendar.

    Args:
        service: Google Calendar service resource
        calendar_id: ID do calendário
        event_id: ID do evento a atualizar
        payload: Dict com campos atualizados

    Returns:
        Dict: Evento atualizado (response da API)

    Raises:
        HttpError: Se houver erro na atualização
    """
    try:
        # Retry simples para 5xx e 429
        max_retries = 3
        for attempt in range(max_retries):
            try:
                event = (
                    service.events()
                    .update(calendarId=calendar_id, eventId=event_id, body=payload)
                    .execute()
                )

                logger.info(
                    f"✓ Evento atualizado: {event.get('id')} | {event.get('summary')}"
                )
                return event

            except HttpError as e:
                status_code = e.resp.status

                # 429 (rate limit) ou 5xx (erro servidor) → retry com backoff
                if status_code in [429, 500, 502, 503] and attempt < max_retries - 1:
                    wait_time = (2**attempt) * 1  # Backoff exponencial
                    logger.warning(
                        f"⚠ HTTP {status_code}, tentando novamente em {wait_time}s..."
                    )
                    time.sleep(wait_time)
                    continue

                # 4xx (erro cliente) → não fazer retry
                logger.error(f"Erro ao atualizar evento (HTTP {status_code}): {e}")
                raise

    except Exception as e:
        logger.error(f"Erro inesperado ao atualizar evento: {e}")
        raise


def build_event_payload(
    summary: str,
    location: str,
    description: str,
    start_iso: str,
    end_iso: str,
    attendees_emails: str,
    external_hash: str,
) -> Dict:
    """
    Monta payload do evento para Google Calendar API.

    Args:
        summary: Título do evento
        location: Local (município)
        description: Descrição (já contém hash e metadados)
        start_iso: Data/hora início (ISO 8601)
        end_iso: Data/hora fim (ISO 8601)
        attendees_emails: Emails separados por ';'
        external_hash: Hash SHA1 para idempotência

    Returns:
        Dict: Payload pronto para events().insert() ou events().update()
    """
    # Processar attendees (remover duplicados e vazios)
    attendees = []
    if attendees_emails:
        emails = [e.strip() for e in attendees_emails.split(";") if e.strip()]
        # Remover duplicados preservando ordem
        seen = set()
        for email in emails:
            if email.lower() not in seen:
                seen.add(email.lower())
                attendees.append({"email": email})

    payload = {
        "summary": summary,
        "location": location,
        "description": description,
        "start": {"dateTime": start_iso, "timeZone": TIMEZONE},
        "end": {"dateTime": end_iso, "timeZone": TIMEZONE},
        "attendees": attendees,
        "extendedProperties": {"private": {"external_hash": external_hash}},
        # Configurações adicionais
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "email", "minutes": 24 * 60},  # 1 dia antes
                {"method": "popup", "minutes": 60},  # 1 hora antes
            ],
        },
    }

    return payload


def sync_event_idempotent(
    service,
    calendar_id: str,
    external_hash: str,
    summary: str,
    location: str,
    description: str,
    start_iso: str,
    end_iso: str,
    attendees_emails: str,
) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Sincroniza evento de forma idempotente (create ou update).

    Fluxo:
    1. Busca por external_hash
    2. Se não existe → create
    3. Se existe 1 → update
    4. Se existe >1 → duplicado_remoto (não criar)

    Args:
        service: Google Calendar service resource
        calendar_id: ID do calendário
        external_hash: Hash SHA1 do evento
        summary, location, description, start_iso, end_iso, attendees_emails:
            Campos do evento (mesmos de build_event_payload)

    Returns:
        Tuple (action, event_id, error_msg):
            - action: "created" | "updated" | "skipped" | "duplicado_remoto"
            - event_id: ID do evento criado/atualizado (None se error)
            - error_msg: Mensagem de erro (None se sucesso)
    """
    try:
        # Buscar evento existente
        count, events = find_event_by_hash(service, calendar_id, external_hash)

        # Montar payload
        payload = build_event_payload(
            summary,
            location,
            description,
            start_iso,
            end_iso,
            attendees_emails,
            external_hash,
        )

        if count == 0:
            # Criar novo evento
            event = create_event(service, calendar_id, payload)
            return ("created", event.get("id"), None)

        elif count == 1:
            # Atualizar evento existente
            existing_event = events[0]
            event_id = existing_event.get("id")

            # Verificar se precisa atualizar (comparação simples)
            needs_update = (
                existing_event.get("summary") != summary
                or existing_event.get("location") != location
                or existing_event.get("start", {}).get("dateTime") != start_iso
                or existing_event.get("end", {}).get("dateTime") != end_iso
            )

            if needs_update:
                event = update_event(service, calendar_id, event_id, payload)
                return ("updated", event_id, None)
            else:
                # Sem mudanças, skip
                return ("skipped", event_id, None)

        else:
            # Duplicados remotos (>1)
            logger.error(
                f"✗ Encontrados {count} eventos com hash {external_hash[:8]}... (duplicado remoto)"
            )
            return ("duplicado_remoto", None, f"{count} eventos com mesmo hash")

    except HttpError as e:
        error_msg = f"HTTP {e.resp.status}: {str(e)}"
        logger.error(f"Erro ao sincronizar evento: {error_msg}")
        return ("error", None, error_msg)

    except Exception as e:
        error_msg = f"Erro inesperado: {str(e)}"
        logger.error(f"Erro ao sincronizar evento: {error_msg}")
        return ("error", None, error_msg)

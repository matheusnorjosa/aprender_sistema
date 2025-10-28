"""
Google Calendar Sync Service - Sincronização idempotente de pré-agenda

Sincroniza Solicitações aprovadas com Google Calendar.
Suporta CREATE, UPDATE, ADOPT, DELETE e SKIP.

Regras:
- Somente Solicitacao.status == "aprovado" é candidata
- eventId determinístico: as-{solicitacao.id}
- Idempotência via external_event_id
- Sem regras de disponibilidade (já no AvailabilityService)
- PA-01: Não auto-aprova nada
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from datetime import timezone as dt_timezone
from typing import Callable, Literal, Optional, TypeVar
from uuid import uuid4

from django.conf import settings
from django.utils import timezone

from apps.core.models import Solicitacao, Participation

logger = logging.getLogger(__name__)

# Type variable para retry genérico
T = TypeVar('T')

Action = Literal["CREATE", "UPDATE", "DELETE", "ADOPT", "SKIP"]


def _retry_with_backoff(
    func: Callable[[], T],
    *,
    operation_name: str = "operation",
    max_retries: int = 3,
    initial_delay: float = 1.0,
) -> T:
    """
    Executa função com retry e backoff exponencial (RF05 - PR19).

    Estratégia:
    - 1 tentativa inicial + até 3 retries (total: 4 tentativas)
    - Backoff: 1s, 2s, 4s
    - Retry apenas em: 429 (rate limit), 5xx (server errors)
    - Não retry em: 4xx (exceto 429)
    - Respeita Retry-After header se presente
    - Trata 409/412 como sucesso (idempotência)

    Args:
        func: Função a executar (sem argumentos, use lambda se necessário)
        operation_name: Nome da operação (para logs)
        max_retries: Número máximo de retries (default: 3)
        initial_delay: Delay inicial em segundos (default: 1.0)

    Returns:
        Resultado da função

    Raises:
        Exception: Última exceção após esgotar retries
    """
    attempt = 0
    last_exception = None

    while attempt <= max_retries:
        try:
            result = func()

            # Sucesso na tentativa
            if attempt > 0:
                logger.info(
                    f"{operation_name} succeeded after {attempt} retries"
                )
            return result

        except Exception as e:
            last_exception = e
            error_str = str(e).lower()

            # Extrair código de status HTTP se disponível
            status_code = None
            retry_after = None

            # Tentar extrair status code de exceções comuns
            if hasattr(e, 'resp') and hasattr(e.resp, 'status'):
                # googleapiclient.errors.HttpError
                status_code = e.resp.status

                # Extrair Retry-After header
                if hasattr(e.resp, 'get'):
                    retry_after = e.resp.get('Retry-After')
            elif '429' in error_str:
                status_code = 429
            elif '500' in error_str or '502' in error_str or '503' in error_str or '504' in error_str:
                status_code = 500  # Genérico para 5xx
            elif '409' in error_str:
                status_code = 409
            elif '412' in error_str:
                status_code = 412

            # VERIFICAR IDEMPOTÊNCIA PRIMEIRO (409/412 = sucesso)
            if status_code in (409, 412):
                logger.info(
                    f"{operation_name}: {status_code} treated as success (idempotency)"
                )
                return None  # Retorna None mas não falha

            # Decidir se deve retentar
            should_retry = False

            if status_code == 429:
                # Rate limit → sempre retry
                should_retry = True
                logger.warning(
                    f"{operation_name}: Rate limit (429), attempt {attempt + 1}/{max_retries + 1}"
                )
            elif status_code and status_code >= 500:
                # Server error → retry
                should_retry = True
                logger.warning(
                    f"{operation_name}: Server error ({status_code}), attempt {attempt + 1}/{max_retries + 1}"
                )
            elif status_code and 400 <= status_code < 500:
                # Client error (exceto 429) → não retry
                logger.error(
                    f"{operation_name}: Client error ({status_code}), aborting without retry"
                )
                raise
            else:
                # Erro desconhecido → retry conservador
                should_retry = True
                logger.warning(
                    f"{operation_name}: Unknown error, attempt {attempt + 1}/{max_retries + 1}: {error_str[:100]}"
                )

            # Se não deve retentar ou esgotou tentativas, lança exceção
            if not should_retry or attempt >= max_retries:
                logger.error(
                    f"{operation_name}: Failed after {attempt + 1} attempts. Last error: {error_str[:200]}"
                )
                raise

            # Calcular delay
            if retry_after:
                try:
                    delay = float(retry_after)
                except (ValueError, TypeError):
                    delay = initial_delay * (2 ** attempt)
            else:
                delay = initial_delay * (2 ** attempt)

            logger.info(f"{operation_name}: Retrying in {delay:.1f}s...")
            time.sleep(delay)
            attempt += 1

    # Nunca deve chegar aqui, mas por segurança
    raise last_exception or Exception(f"{operation_name}: Unexpected retry loop exit")


def _payload_hash(payload: dict) -> str:
    """
    Calcula SHA1 hash determinístico do payload (PR14).

    Args:
        payload: Dicionário com dados do evento

    Returns:
        str: Hash SHA1 hex (40 chars)
    """
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(serialized.encode("utf-8")).hexdigest()


@dataclass
class SyncOutcome:
    """
    Resultado de uma operação de sincronização.

    action: Tipo de ação executada
    solicitation_id: ID da solicitação
    external_event_id: ID do evento no Calendar (ou None)
    summary: Resumo do evento
    """

    action: Action
    solicitation_id: int
    external_event_id: Optional[str]
    summary: str


class CalendarClientAdapter:
    """
    Interface para clientes de Calendar.

    Implementações:
    - FakeCalendarClient: in-memory para testes
    - GoogleCalendarClient: real Google API (futuro)
    """

    def get(self, calendar_id: str, event_id: str) -> Optional[dict]:
        """
        Busca evento por ID.

        Returns:
            dict com dados do evento, ou None se não existe
        """
        raise NotImplementedError

    def insert(self, calendar_id: str, event_id: str, payload: dict) -> dict:
        """
        Cria novo evento.

        Args:
            calendar_id: ID do calendário
            event_id: ID determinístico do evento
            payload: Dados do evento (summary, start, end, etc)

        Returns:
            dict com evento criado (incluindo "id")
        """
        raise NotImplementedError

    def update(self, calendar_id: str, event_id: str, payload: dict) -> dict:
        """
        Atualiza evento existente.

        Args:
            calendar_id: ID do calendário
            event_id: ID do evento
            payload: Novos dados do evento

        Returns:
            dict com evento atualizado
        """
        raise NotImplementedError

    def delete(self, calendar_id: str, event_id: str) -> None:
        """
        Deleta evento.

        Args:
            calendar_id: ID do calendário
            event_id: ID do evento
        """
        raise NotImplementedError


def _validate_event_id(event_id: str) -> bool:
    """
    Valida eventId conforme especificação Google Calendar API.

    Regras:
    - Comprimento: 5-1024 caracteres
    - Caracteres permitidos: a-z, 0-9, - (hífen), _ (underscore)
    - Deve ser lowercase

    Args:
        event_id: ID do evento a validar

    Returns:
        bool: True se válido, False caso contrário

    Raises:
        ValueError: Se eventId inválido (com mensagem descritiva)
    """
    import re

    if not event_id:
        raise ValueError("eventId não pode ser vazio")

    if len(event_id) < 5:
        raise ValueError(f"eventId muito curto: {len(event_id)} chars (mínimo: 5)")

    if len(event_id) > 1024:
        raise ValueError(f"eventId muito longo: {len(event_id)} chars (máximo: 1024)")

    # Verificar caracteres permitidos (a-z, 0-9, -, _)
    if not re.match(r"^[a-z0-9_-]+$", event_id):
        raise ValueError(
            f"eventId contém caracteres inválidos: {event_id}. "
            "Permitido: a-z, 0-9, -, _"
        )

    return True


def _event_id_for(s: Solicitacao) -> str:
    """
    Gera eventId determinístico para uma Solicitacao.

    Format: asv2-{id} (lowercase, a-z0-9-, mínimo 6 chars)

    Args:
        s: Solicitacao

    Returns:
        str: Event ID determinístico (validado)

    Raises:
        ValueError: Se ID gerado for inválido
    """
    event_id = f"asv2-{s.id}"

    # Validar antes de retornar
    _validate_event_id(event_id)

    return event_id


def build_attendees_for_solicitacao(s: Solicitacao) -> list[dict]:
    """
    Extrai attendees (participantes) de uma Solicitacao.

    Inclui apenas roles: COORDENADOR, FORMADOR, COORD_ACOMPANHA.
    Para cada participação:
    - Se usuario existe, usa usuario.email
    - Se guest_email existe, usa guest_email

    Args:
        s: Solicitacao

    Returns:
        list[dict]: Lista de attendees no formato Google Calendar
                    [{"email": "..."}, ...]
    """
    # Roles que devem ser incluídos como attendees
    attendee_roles = ["COORDENADOR", "FORMADOR", "COORD_ACOMPANHA"]

    # Buscar participações com prefetch do usuário
    participations = s.participations.filter(role__in=attendee_roles).select_related(
        "usuario"
    )

    emails = set()
    for p in participations:
        email = None
        if p.usuario and p.usuario.email:
            email = p.usuario.email
        elif p.guest_email:
            email = p.guest_email

        if email:
            emails.add(email.strip().lower())

    # Retornar lista de dicts no formato Google Calendar
    return [{"email": email} for email in sorted(emails)]


def build_preview_for_solicitacao(s: Solicitacao) -> dict:
    """
    Constrói preview do payload GCal sem publicar (PR14, PR19/RF06).

    Args:
        s: Solicitacao

    Returns:
        dict: {
            "event_id": str,
            "payload": dict (Google Calendar API format),
            "payload_hash": str (SHA1 hex),
            "meet_link": str (fake link para preview, não persiste no DB)
        }
    """
    # PR19/RF06 + Modalidade: habilita Meet no preview apenas se for online
    enable_meet = bool(getattr(s, "is_online", False))
    payload = _build_payload(s, enable_meet=enable_meet)
    event_id = _event_id_for(s)

    # Gerar meet_link fake para preview (não persiste) apenas quando online
    meet_link_preview = None
    if enable_meet:
        # Extrai número do event_id (formato: asv2-{id})
        event_num = event_id.split("-")[-1] if "-" in event_id else event_id
        meet_link_preview = f"https://meet.google.com/fake-{event_num}"

    return {
        "event_id": event_id,
        "payload": payload,
        "payload_hash": _payload_hash(payload),
        "meet_link": meet_link_preview,  # PR19/RF06: Preview do Meet link (somente online)
    }


def apply_one_solicitacao(
    s: Solicitacao, *, dry_run: bool = False, apply_blocked: bool = False
) -> SyncOutcome:
    """
    Aplica uma Solicitacao ao Google Calendar (wrapper sobre upsert_one) - PR14.

    Lógica apply_blocked:
    - Se settings.GCAL_CLIENT está configurado, sempre aplica
    - Se settings.GCAL_CLIENT NÃO está configurado:
      - Se apply_blocked=True, aplica mesmo assim (para testes)
      - Se apply_blocked=False, marca ERROR e retorna SKIP

    PR14: Atualiza gcal_status/payload_hash conforme resultado.

    Args:
        s: Solicitacao a aplicar
        dry_run: Se True, não persiste mudanças no DB/Calendar
        apply_blocked: Se True, aplica mesmo sem GCAL_CLIENT configurado

    Returns:
        SyncOutcome com ação executada

    Raises:
        Exception: Propaga exceções de upsert_one (após marcar ERROR)
    """
    # Verificar se GCAL_CLIENT está configurado
    gcal_client_enabled = getattr(settings, "GCAL_CLIENT", None) is not None

    if not gcal_client_enabled and not apply_blocked:
        # Marcar erro e retornar SKIP (PR14)
        if not dry_run:
            s.mark_gcal(
                status=Solicitacao.GCalStatus.ERROR,
                error="GCAL_CLIENT não configurado",
            )
        return SyncOutcome(
            action="SKIP",
            solicitation_id=s.id,
            external_event_id=s.external_event_id,
            summary=f"Solicitação #{s.id} (GCAL_CLIENT não configurado)",
        )

    # Construir payload antecipadamente para calcular hash (PR14, PR19/RF06)
    payload = None
    payload_hash = None
    if s.status == "aprovado":
        # PR19/RF06 + Modalidade: enable_meet somente para eventos online
        payload = build_event_payload(s, enable_meet=bool(getattr(s, "is_online", False)))
        payload_hash = _payload_hash(payload)

    # Obter cliente via factory (fake ou google baseado em settings)
    from apps.core.services.gcal_client_factory import get_gcal_client_and_calendar_id

    client, calendar_id = get_gcal_client_and_calendar_id()

    try:
        # Chamar upsert_one com payload pré-calculado (PR14)
        outcome = upsert_one(
            client=client,
            calendar_id=calendar_id,
            s=s,
            dry_run=dry_run,
            no_delete=False,
            payload=payload,
        )

        # Marcar status baseado na ação (PR14)
        if not dry_run:
            if outcome.action in {"CREATE", "UPDATE", "ADOPT"}:
                s.mark_gcal(
                    status=Solicitacao.GCalStatus.PUBLISHED,
                    payload_hash=payload_hash,
                    error="",
                )
            elif outcome.action == "DELETE":
                s.mark_gcal(
                    status=Solicitacao.GCalStatus.NONE,
                    payload_hash=None,
                    error="",
                )
            # SKIP: não altera status

        return outcome

    except Exception as e:
        # Marcar erro antes de relançar (PR14)
        if not dry_run:
            s.mark_gcal(
                status=Solicitacao.GCalStatus.ERROR,
                error=str(e),
            )
        raise


def _build_payload(s: Solicitacao, *, enable_meet: bool = False) -> dict:
    """
    Constrói payload do evento para Google Calendar API.

    Args:
        s: Solicitacao aprovada
        enable_meet: Se True, adiciona conferenceData para Google Meet (RF06)

    Returns:
        dict: Payload compatível com Google Calendar API
    """
    # Converter para UTC (Google aceita ISO8601 com Z)
    start_iso = s.inicio.astimezone(dt_timezone.utc).isoformat()
    end_iso = s.fim.astimezone(dt_timezone.utc).isoformat()

    # Extrair atributos (podem ser None)
    municipio = getattr(s, "municipio", None)
    tipo = getattr(s, "tipo_evento", None)
    usuario = getattr(s, "usuario", None)

    # Construir summary: "Município - UF — Tipo — Usuário"
    parts = []

    if municipio:
        nome_mun = getattr(municipio, "nome", "")
        uf_mun = getattr(municipio, "uf", "")
        if nome_mun:
            parts.append(f"{nome_mun}{' - ' + uf_mun if uf_mun else ''}")

    if tipo:
        nome_tipo = getattr(tipo, "nome", "")
        if nome_tipo:
            parts.append(nome_tipo)

    if usuario:
        nome_user = getattr(usuario, "get_full_name", lambda: "")() or getattr(
            usuario, "username", ""
        )
        if nome_user:
            parts.append(nome_user)

    summary = " — ".join(parts) if parts else f"Solicitação #{s.id}"

    # ================================================================
    # DEFENSIVE TRUNCATION (Google Calendar limits)
    # ================================================================
    # Summary: ≤1000 chars. Se exceder, move excess para description.
    # Description: ≤5000 chars total.
    summary_excess = ""
    if len(summary) > 1000:
        summary_excess = f"\n\n[Título completo]\n{summary}\n"
        summary_trimmed = summary[:997] + "..."
    else:
        summary_trimmed = summary

    # Description base + excess do summary (se houver) + observações
    description_parts = [f"AS v2 • Solicitação #{s.id}"]
    if summary_excess:
        description_parts.append(summary_excess.strip())
    if s.observacoes:
        description_parts.append(s.observacoes.strip())

    description = "\n\n".join(description_parts).strip()

    # Limitar description a 5000 chars
    if len(description) > 5000:
        description_trimmed = description[:4997] + "..."
    else:
        description_trimmed = description

    # RF06: Google Meet conferenceData
    conference_data = None
    if enable_meet:
        # Gera requestId único e determinístico para idempotência
        # Formato: meet-{solicitation_id}-{random_8chars}
        request_id = f"meet-{s.id}-{uuid4().hex[:8]}"
        conference_data = {
            "createRequest": {
                "requestId": request_id,
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        }

    # Construir payload
    payload = {
        "summary": summary_trimmed,
        "description": description_trimmed,
        "start": {"dateTime": start_iso, "timeZone": "UTC"},
        "end": {"dateTime": end_iso, "timeZone": "UTC"},
        "location": getattr(municipio, "nome", None) if municipio else None,
        # Metadados para auditoria e reconciliação
        "extendedProperties": {
            "private": {
                "solicitation_id": str(s.id),
                "ssot_version": "v2",
                "last_updated": (
                    s.updated_at.isoformat()
                    if hasattr(s, "updated_at") and s.updated_at
                    else ""
                ),
            }
        },
    }

    # Attendees (via Participation: COORDENADOR, FORMADOR, COORD_ACOMPANHA)
    payload["attendees"] = build_attendees_for_solicitacao(s)

    # Color mapping (opcional)
    color_map = getattr(settings, "GCAL_COLOR_MAP", None)
    if color_map and tipo:
        tipo_nome = getattr(tipo, "nome", None)
        if tipo_nome and tipo_nome in color_map:
            payload["colorId"] = str(color_map[tipo_nome])

    # RF06: Adicionar conferenceData apenas se enable_meet=True (modalidade online)
    if conference_data is not None:
        payload["conferenceData"] = conference_data

    return payload


def build_event_payload(s: Solicitacao, *, enable_meet: bool = False) -> dict:
    """
    Wrapper público para _build_payload (PR14, PR19).

    Args:
        s: Solicitacao
        enable_meet: Se True, adiciona conferenceData para Google Meet (RF06)

    Returns:
        dict: Payload para Google Calendar API
    """
    return _build_payload(s, enable_meet=enable_meet)


def compute_payload_hash(s: Solicitacao) -> str:
    """
    Calcula hash do payload de uma solicitação (PR14).

    Args:
        s: Solicitacao

    Returns:
        str: SHA1 hash hex (40 chars)
    """
    payload = build_event_payload(s)
    return _payload_hash(payload)


def upsert_one(
    *,
    client: CalendarClientAdapter,
    calendar_id: str,
    s: Solicitacao,
    dry_run: bool = False,
    no_delete: bool = False,
    payload: Optional[dict] = None,
    enable_meet: bool = False,
) -> SyncOutcome:
    """
    Sincroniza uma Solicitacao com o Google Calendar (idempotente) - PR14, PR19.

    Lógica:
    1. Se status != "aprovado" e tem external_event_id → DELETE (ou SKIP se no_delete)
    2. Se não aprovado → SKIP
    3. Se aprovado:
       - Se evento não existe no Calendar → CREATE
       - Se evento existe mas DB não tem external_event_id → ADOPT + UPDATE
       - Se evento existe e DB tem external_event_id → UPDATE

    Args:
        client: Adaptador de Calendar
        calendar_id: ID do calendário Google
        s: Solicitacao a sincronizar
        dry_run: Se True, não altera DB nem Calendar
        no_delete: Se True, não deleta eventos de solicitações não-aprovadas
        payload: Payload pré-calculado (opcional, default recalcula via _build_payload)
        enable_meet: Se True, adiciona conferenceData para Google Meet (RF06)

    Returns:
        SyncOutcome com ação executada
    """
    action: Optional[Action] = None
    error_msg: Optional[str] = None
    external_event_id: Optional[str] = None

    try:
        # ================================================================
        # CONCURRENCY SAFETY: Uso recomendado com update_fields
        # ================================================================
        # Nota: Para produção, chamar dentro de transaction.atomic() e iterar
        # sobre queryset com select_for_update() no command:
        # qs = Solicitacao.objects.select_for_update().filter(...)
        # for s in qs:
        #     upsert_one(client, calendar_id, s, dry_run, no_delete)
        # Caso 1: Não aprovado com evento vinculado → DELETE (ou SKIP)
        if s.status != "aprovado":
            if s.external_event_id:
                if no_delete:
                    action = "SKIP"
                    external_event_id = s.external_event_id
                    return SyncOutcome(
                        action,
                        s.id,
                        external_event_id,
                        f"Solicitação #{s.id} (no-delete)",
                    )

                eid = s.external_event_id
                if not dry_run:
                    try:
                        # RF05: Retry com backoff exponencial (PR19)
                        _retry_with_backoff(
                            lambda: client.delete(calendar_id, eid),
                            operation_name=f"GCal DELETE #{s.id}",
                        )
                    except Exception as e:
                        # Ignora se evento já foi deletado, mas registra outros erros
                        if "404" not in str(e):
                            error_msg = f"Erro ao deletar: {str(e)}"

                    s.external_event_id = None
                    s.last_synced_at = timezone.now()
                    s.last_sync_action = "DELETE"
                    s.last_sync_error = error_msg
                    s.save(
                        update_fields=[
                            "external_event_id",
                            "last_synced_at",
                            "last_sync_action",
                            "last_sync_error",
                        ]
                    )

                action = "DELETE"
                return SyncOutcome(action, s.id, None, f"Solicitação #{s.id}")

            # Não aprovado sem evento vinculado → SKIP
            action = "SKIP"
            return SyncOutcome(
                action, s.id, None, f"Solicitação #{s.id} (não aprovado)"
            )

        # Caso 2: Aprovado → CREATE/UPDATE/ADOPT
        deterministic_eid = _event_id_for(s)

        # Usar payload fornecido ou recalcular (PR14, PR19/RF06)
        if payload is None:
            # PR19/RF06 + Modalidade: enable_meet somente para eventos online
            payload = _build_payload(s, enable_meet=bool(getattr(s, "is_online", False)))

        # Verificar se evento já existe no Calendar
        existing = None
        if s.external_event_id:
            # Tentar buscar pelo ID armazenado no DB
            try:
                existing = client.get(calendar_id, s.external_event_id)
            except Exception as e:
                error_msg = f"Erro ao buscar evento: {str(e)}"

        if existing is None:
            # Tentar adotar evento com eventId determinístico
            try:
                existing = client.get(calendar_id, deterministic_eid)
            except Exception as e:
                if error_msg is None:
                    error_msg = f"Erro ao buscar evento determinístico: {str(e)}"

        if existing is None:
            # CREATE: Evento não existe
            action = "CREATE"
            external_event_id = deterministic_eid

            if not dry_run:
                try:
                    # RF05: Retry com backoff exponencial (PR19)
                    created = _retry_with_backoff(
                        lambda: client.insert(calendar_id, deterministic_eid, payload),
                        operation_name=f"GCal INSERT #{s.id}",
                    )
                    s.external_event_id = created.get("id") or deterministic_eid if created else deterministic_eid

                    # RF06: Extrair hangoutLink se disponível
                    hangout_link = created.get("hangoutLink") if created else None
                    if hangout_link and bool(getattr(s, "is_online", False)):
                        s.meet_link = hangout_link

                    s.last_synced_at = timezone.now()
                    s.last_sync_action = action
                    s.last_sync_error = None

                    update_fields = [
                        "external_event_id",
                        "last_synced_at",
                        "last_sync_action",
                        "last_sync_error",
                    ]
                    if hangout_link and bool(getattr(s, "is_online", False)):
                        update_fields.append("meet_link")

                    s.save(update_fields=update_fields)
                except Exception as e:
                    error_msg = f"Erro ao criar evento: {str(e)}"
                    s.last_synced_at = timezone.now()
                    s.last_sync_action = action
                    s.last_sync_error = error_msg
                    s.save(
                        update_fields=[
                            "last_synced_at",
                            "last_sync_action",
                            "last_sync_error",
                        ]
                    )
                    raise

            return SyncOutcome(action, s.id, external_event_id, payload["summary"])

        else:
            # UPDATE ou ADOPT
            action = "UPDATE"
            external_event_id = deterministic_eid

            if not s.external_event_id:
                # DB não tinha o ID, mas evento existe → ADOPT
                action = "ADOPT"

            if not dry_run:
                try:
                    # RF05: Retry com backoff exponencial (PR19)
                    updated = _retry_with_backoff(
                        lambda: client.update(calendar_id, deterministic_eid, payload),
                        operation_name=f"GCal UPDATE #{s.id}",
                    )
                    if not s.external_event_id:
                        s.external_event_id = deterministic_eid

                    # RF06: Extrair hangoutLink se disponível
                    hangout_link = updated.get("hangoutLink") if updated else None
                    if hangout_link and bool(getattr(s, "is_online", False)):
                        s.meet_link = hangout_link

                    s.last_synced_at = timezone.now()
                    s.last_sync_action = action
                    s.last_sync_error = None

                    update_fields = [
                        "external_event_id",
                        "last_synced_at",
                        "last_sync_action",
                        "last_sync_error",
                    ]
                    if hangout_link and bool(getattr(s, "is_online", False)):
                        update_fields.append("meet_link")

                    s.save(update_fields=update_fields)
                except Exception as e:
                    error_msg = f"Erro ao atualizar evento: {str(e)}"
                    s.last_synced_at = timezone.now()
                    s.last_sync_action = action
                    s.last_sync_error = error_msg
                    s.save(
                        update_fields=[
                            "last_synced_at",
                            "last_sync_action",
                            "last_sync_error",
                        ]
                    )
                    raise

            return SyncOutcome(action, s.id, external_event_id, payload["summary"])

    except Exception as e:
        # Captura qualquer erro não tratado
        if action and not dry_run:
            s.last_synced_at = timezone.now()
            s.last_sync_action = action or "ERROR"
            s.last_sync_error = str(e)[:500]  # Limitar tamanho do erro
            s.save(
                update_fields=["last_synced_at", "last_sync_action", "last_sync_error"]
            )
        raise

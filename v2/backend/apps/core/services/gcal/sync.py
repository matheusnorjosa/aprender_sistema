"""
AS v2 — GCal Sync Operations

Core synchronization operations for Google Calendar.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false, reportPrivateUsage=false, reportUnusedImport=false

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.utils import timezone

from apps.core.models import Solicitacao
from apps.core.types import CalendarId, EventId, JsonDict

from .client import CalendarClientAdapter
from .payload import _build_payload, build_event_payload
from .types import Action, SyncOutcome
from .utils import _payload_hash, _retry_with_backoff
from .validation import _event_id_for

logger = logging.getLogger(__name__)


def apply_one_solicitacao(
    s: Solicitacao,
    *,
    dry_run: bool = False,
    apply_blocked: bool = False,
    client: CalendarClientAdapter | None = None,
) -> SyncOutcome:
    """
    Aplica uma Solicitacao ao Google Calendar (wrapper sobre upsert_one) - PR14.

    Lógica apply_blocked:
    - Se settings.GCAL_CLIENT está configurado, sempre aplica
    - Se settings.GCAL_CLIENT NÃO está configurado:
      - Se apply_blocked=True, aplica mesmo assim (para testes)
      - Se apply_blocked=False, marca ERROR e retorna SKIP

    PR14: Atualiza gcal_status/payload_hash conforme resultado.
    OAuth Phase 3: Aceita cliente externo (OAuth ou service account).

    Args:
        s: Solicitacao a aplicar
        dry_run: Se True, não persiste mudanças no DB/Calendar
        apply_blocked: Se True, aplica mesmo sem GCAL_CLIENT configurado
        client: Cliente opcional (OAuth ou service account). Se None, usa factory.

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

    # OAuth Phase 3: Usar cliente fornecido ou obter via factory
    if client is None:
        # Obter cliente via factory (fake ou google baseado em settings)
        from apps.core.services.gcal_client_factory import get_gcal_client_and_calendar_id

        client, calendar_id = get_gcal_client_and_calendar_id()
    else:
        # Cliente fornecido externamente (OAuth mode), usar calendário preferido
        # Verificar se cliente tem método get_default_calendar_id (OAuthCalendarClient)
        if hasattr(client, "get_default_calendar_id"):
            calendar_id = client.get_default_calendar_id()
        else:
            # Fallback para clientes antigos
            import os

            calendar_id = getattr(settings, "GCAL_CALENDAR_ID", None) or os.getenv("GCAL_CALENDAR_ID") or "primary"

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


def upsert_one(
    *,
    client: CalendarClientAdapter,
    calendar_id: CalendarId,
    s: Solicitacao,
    dry_run: bool = False,
    no_delete: bool = False,
    payload: JsonDict | None = None,
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
    action: Action | None = None
    error_msg: str | None = None
    external_event_id: EventId | None = None

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
            return SyncOutcome(action, s.id, None, f"Solicitação #{s.id} (não aprovado)")

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
                    logger.debug(
                        f"🔍 GCal INSERT #{s.id} - calendar_id={calendar_id}, "
                        f"event_id={deterministic_eid}, payload={payload}"
                    )
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
            s.save(update_fields=["last_synced_at", "last_sync_action", "last_sync_error"])
        raise


def resync_solicitacao(s: Solicitacao, *, apply_blocked: bool = False) -> SyncOutcome:
    """
    Republicar solicitação no Google Calendar (força UPDATE) - Fase 4.

    Reseta gcal_payload_hash para forçar UPDATE mesmo se já publicado.
    Reutiliza apply_one_solicitacao para lógica de sincronização.

    Args:
        s: Solicitacao aprovada
        apply_blocked: Se True, aplica mesmo sem GCAL_CLIENT configurado

    Returns:
        SyncOutcome com ação executada

    Raises:
        ValueError: Se status != 'aprovado'
    """
    if s.status != "aprovado":
        raise ValueError(f"Apenas solicitações aprovadas podem ser resincronizadas (status atual: {s.status})")

    # Resetar hash para forçar UPDATE (mesmo se já publicado)
    s.gcal_payload_hash = None
    s.save(update_fields=["gcal_payload_hash"])

    # Reutilizar apply_one_solicitacao
    return apply_one_solicitacao(s, dry_run=False, apply_blocked=apply_blocked)


def cancel_solicitacao(
    s: Solicitacao,
    *,
    client: CalendarClientAdapter | None = None,
) -> SyncOutcome:
    """
    Cancelar evento no Google Calendar e limpar campos - Fase 4.

    Deleta evento do Calendar (trata 404 como sucesso - idempotência) e limpa
    todos os campos relacionados: external_event_id, meet_link, gcal_payload_hash.

    Args:
        s: Solicitacao com evento publicado
        client: Optional pre-built client (OAuth mode). Falls back to service account.

    Returns:
        SyncOutcome com action="DELETE"

    Raises:
        ValueError: Se evento não foi publicado
    """
    if not s.external_event_id and s.gcal_status != Solicitacao.GCalStatus.PUBLISHED:
        raise ValueError("Solicitação não possui evento publicado no Google Calendar")

    if client is None:
        from apps.core.services.gcal_client_factory import get_gcal_client_and_calendar_id

        client, calendar_id = get_gcal_client_and_calendar_id()
    else:
        from django.conf import settings

        calendar_id = getattr(settings, "GCAL_CALENDAR_ID", "primary")

    # Usar external_event_id ou gerar determinístico
    event_id = s.external_event_id or _event_id_for(s)

    try:
        # Tentar deletar com retry/backoff
        _retry_with_backoff(
            lambda: client.delete(calendar_id, event_id),
            operation_name=f"GCal CANCEL #{s.id}",
        )
    except Exception as e:
        # 404 = já foi deletado (idempotência OK)
        if "404" not in str(e):
            raise

    # Limpar campos
    s.external_event_id = None
    s.meet_link = None
    s.gcal_payload_hash = None
    s.gcal_status = Solicitacao.GCalStatus.NONE
    s.last_synced_at = timezone.now()
    s.last_sync_action = "DELETE"
    s.last_sync_error = None
    s.save(
        update_fields=[
            "external_event_id",
            "meet_link",
            "gcal_payload_hash",
            "gcal_status",
            "last_synced_at",
            "last_sync_action",
            "last_sync_error",
        ]
    )

    return SyncOutcome(
        action="DELETE", solicitation_id=s.id, external_event_id=None, summary=f"Solicitação #{s.id} (cancelada)"
    )

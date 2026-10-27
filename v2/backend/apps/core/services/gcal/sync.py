"""
AS v2 — GCal Sync Operations

Core synchronization operations for Google Calendar.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false, reportPrivateUsage=false, reportUnusedImport=false

from __future__ import annotations

import logging
from typing import Any, cast

from django.conf import settings
from django.utils import timezone

from apps.core.models import Solicitacao
from apps.core.services.db_retry import retry_on_deadlock
from apps.core.types import CalendarId, EventId, JsonDict

from .client import CalendarClientAdapter
from .payload import _build_payload, build_event_payload
from .types import Action, SyncOutcome
from .utils import _payload_hash, _retry_with_circuit_breaker
from .validation import _event_id_for

logger = logging.getLogger(__name__)


class CriacaoRecusada(ValueError):
    """O sync ia CRIAR (ou adotar o `asv2{id}`) no Google e a guarda da virada recusou (`code` diz por quê).

    `evento_passado`: o evento já terminou. `publicado_fora_do_sistema`: ele já está no Google pela
    planilha e não foi adotado, então criar daria um segundo evento. Quem chama marca ERROR (tarefa)
    ou conta como SKIP (`preagenda_to_gcal`)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _motivo_para_nao_criar(s: Solicitacao) -> CriacaoRecusada | None:
    """Guarda única do CREATE e do ADOPT (Publicar, lote, Reapply, Resync e `preagenda_to_gcal` passam por aqui)."""
    if s.publicado_fora_do_sistema:
        return CriacaoRecusada(
            "publicado_fora_do_sistema",
            f"Solicitação #{s.id} já está no Google Agenda pela planilha e não foi adotada; criar daria um "
            "segundo evento.",
        )
    if s.fim < timezone.now():
        return CriacaoRecusada("evento_passado", f"Solicitação #{s.id} já terminou; o sistema não cria evento passado.")
    return None


@retry_on_deadlock(operation="gcal.apply_one_solicitacao")
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
        # A prévia só LÊ o Google, e o upsert_one engole erro de GET: sem esta checagem, uma conta
        # sem acesso ao calendário receberia "CREATE, sem erro" onde a publicação real dá 403.
        if dry_run and hasattr(client, "calendar_accessible") and not client.calendar_accessible(calendar_id):
            raise ValueError(
                "Sua conta Google não tem acesso ao calendário da organização. "
                "Peça o compartilhamento e tente de novo."
            )

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
                        _retry_with_circuit_breaker(
                            lambda: client.delete(calendar_id, eid),
                            operation_name=f"GCal DELETE #{s.id}",
                        )
                    except Exception as e:
                        # 404/410 = evento já saiu do Google (idempotência OK). Para
                        # QUALQUER outro erro, RE-LEVANTA (#1541): limpar
                        # external_event_id e retornar action="DELETE" aqui deixava o
                        # evento VIVO no Google (participantes ainda o viam) e
                        # descartava o único ponteiro para ele — evento órfão
                        # permanente, reportado como sucesso. Espelha
                        # cancel_solicitacao; o caller marca gcal_status=ERROR.
                        if not _ja_saiu_do_google(e):
                            raise

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
        # Event ID adotado (veio do Google pela planilha, não é o `asv2{id}`): se o GET por ele falha, o
        # evento não pode ser recriado pelo id determinístico, senão o Google fica com dois (virada, #1899).
        adotado = bool(s.external_event_id) and s.external_event_id != deterministic_eid
        if s.external_event_id:
            # Tentar buscar pelo ID armazenado no DB
            try:
                existing = client.get(calendar_id, s.external_event_id)
            except Exception as e:
                if adotado:
                    raise
                error_msg = f"Erro ao buscar evento: {str(e)}"
            if adotado and existing is not None and existing.get("status") == "cancelled":
                # O DELETE do Google é soft-delete: o GET acha o evento apagado, e o UPDATE (status
                # confirmed) o traria de volta. Id adotado cancelado = não achado (relay 65, ação 2).
                raise ValueError(
                    f"Solicitação #{s.id}: o evento adotado está cancelado no Google; nada foi atualizado nem criado."
                )
            if existing is None and adotado:
                raise ValueError(
                    f"Solicitação #{s.id}: o evento adotado não foi achado no Google; nada foi criado para não duplicar."
                )

        if existing is None:
            # Tentar adotar evento com eventId determinístico
            try:
                existing = client.get(calendar_id, deterministic_eid)
            except Exception as e:
                if error_msg is None:
                    error_msg = f"Erro ao buscar evento determinístico: {str(e)}"

        if existing is None or not s.external_event_id:
            # Publicar (CREATE, ou ADOPT do `asv2{id}` que o GET achou, mesmo cancelado: o DELETE do Google é
            # soft-delete e o UPDATE o traz de volta) passa pela guarda. UPDATE de evento já publicado não.
            recusa = _motivo_para_nao_criar(s)
            if recusa is not None:
                raise recusa

        if existing is None:
            # CREATE: Evento não existe
            action = "CREATE"
            external_event_id = deterministic_eid

            if not dry_run:
                try:
                    # So escalares nao-sensiveis derivados do nosso DB (id da Solicitacao +
                    # event_id deterministico) + contagem/flag. Evita inflar/floodar o log se
                    # DEBUG for ligado por engano e NAO expoe e-mails de attendee, o titulo do
                    # evento (pode conter nome de pessoa) nem o calendar_id
                    # (LGPD + CodeQL py/clear-text-logging-sensitive-data).
                    logger.debug(
                        f"🔍 GCal INSERT #{s.id} - event_id={deterministic_eid}, "
                        f"attendees={len(payload.get('attendees', []))}, online={'conferenceData' in payload}"
                    )
                    # RF05: Retry com backoff exponencial (PR19)
                    # 409/412 voltam None (idempotência em utils._retry_with_backoff), apesar do tipo.
                    created = cast(
                        "JsonDict | None",
                        _retry_with_circuit_breaker(
                            lambda: client.insert(calendar_id, deterministic_eid, payload),
                            operation_name=f"GCal INSERT #{s.id}",
                        ),
                    )
                    if created is None:
                        # 409/412 (tratado como sucesso): o id determinístico já existe no Google,
                        # talvez cancelado (o delete é soft-delete) e o GET acima falhou sem ser 404.
                        # O insert não aplicou nada; só o PATCH grava o payload e o status confirmed.
                        # Mesmo SKIP por hash do ramo UPDATE (#1722): payload igual não gera PATCH.
                        if (
                            s.external_event_id
                            and s.gcal_payload_hash
                            and s.gcal_payload_hash == _payload_hash(payload)
                        ):
                            return SyncOutcome("SKIP", s.id, s.external_event_id, payload["summary"])
                        action = "UPDATE" if s.external_event_id else "ADOPT"
                        created = _retry_with_circuit_breaker(
                            lambda: client.update(calendar_id, deterministic_eid, payload),
                            operation_name=f"GCal UPDATE #{s.id} (id já existia)",
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
            # UPDATE ou ADOPT. Alvo = o id gravado (o adotado da planilha, #1899); só sem id gravado o
            # evento achado é o `asv2{id}`. (No 409 do insert acima o alvo segue o `asv2{id}`: é o id inserido.)
            action = "UPDATE"
            external_event_id = s.external_event_id or deterministic_eid
            alvo = external_event_id

            if not s.external_event_id:
                # DB não tinha o ID, mas evento existe → ADOPT
                action = "ADOPT"

            # #1722 (RF05 idempotência): se o evento já está publicado (DB tem o ID)
            # e o payload não mudou desde a última publicação, PULA o UPDATE. Sem isto,
            # todo re-publish de um evento inalterado chama client.update() e, com
            # GCAL_SEND_UPDATES=all, reenvia e-mail a TODOS os convidados sem mudança
            # real. O resync zera gcal_payload_hash de propósito (resync_solicitacao /
            # batch resync), então o SKIP nunca bloqueia um reenvio intencional.
            if action == "UPDATE" and s.gcal_payload_hash and s.gcal_payload_hash == _payload_hash(payload):
                return SyncOutcome("SKIP", s.id, s.external_event_id, payload["summary"])

            if not dry_run:
                try:
                    # RF05: Retry com backoff exponencial (PR19)
                    updated = _retry_with_circuit_breaker(
                        lambda: client.update(calendar_id, alvo, payload),
                        operation_name=f"GCal UPDATE #{s.id}",
                    )
                    if not s.external_event_id:
                        s.external_event_id = alvo

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


def _ja_saiu_do_google(e: Exception) -> bool:
    """404 (já removido) ou 410 (apagado direto no Google) no DELETE contam como sucesso.

    Confere o status HTTP quando o erro tem um: o texto do HttpError traz a URL com o id do
    evento, e um id como ``asv21404`` faria um 500 passar por 404 (evento órfão no Google).
    Sem status (clientes falsos, erros sem resposta HTTP), cai no texto.
    """
    status = getattr(getattr(e, "resp", None), "status", None)
    if status is not None:
        return str(status) in ("404", "410")
    return "404" in str(e)


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
        # Cliente fornecido externamente (OAuth mode): usar o calendário PREFERIDO da
        # credencial, igual ao publish (apply_one_solicitacao). Sem isso o cancel caía
        # em GCAL_CALENDAR_ID/"primary" (calendário errado) -> 404 tratado como sucesso
        # e o evento sobrevivia no calendário real ("Formações").
        if hasattr(client, "get_default_calendar_id"):
            calendar_id = client.get_default_calendar_id()
        else:
            from django.conf import settings

            calendar_id = getattr(settings, "GCAL_CALENDAR_ID", None) or "primary"

    # Usar external_event_id ou gerar determinístico
    event_id = s.external_event_id or _event_id_for(s)

    # O Google devolve 404 no delete tanto para "já removido" quanto para "esta conta não vê o
    # calendário", e o 404 abaixo é tratado como sucesso. Sem acesso confirmado, NÃO apaga às cegas:
    # levanta, a task marca ERROR e mantém external_event_id (re-tentável após o compartilhamento).
    if hasattr(client, "calendar_accessible") and not client.calendar_accessible(calendar_id):
        raise ValueError(
            "Sua conta Google não tem acesso ao calendário da organização; o evento continua no Google. "
            "Peça o compartilhamento e tente de novo."
        )

    try:
        # Tentar deletar com retry/backoff
        _retry_with_circuit_breaker(
            lambda: client.delete(calendar_id, event_id),
            operation_name=f"GCal CANCEL #{s.id}",
        )
    except Exception as e:
        if not _ja_saiu_do_google(e):
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

"""
Celery Tasks — Google Calendar Sync

preview_then_apply_gcal: Task assíncrono que:
  1. Roda --dry-run --json para preview
  2. Se total > 0, roda efetivo sem --dry-run
  3. Retorna resultado final

Agendamento via CELERY_BEAT_SCHEDULE no settings.py:
  - Executar a cada 5 minutos
  - Janela padrão: 90 dias atrás até 180 dias à frente
"""

import json
from io import StringIO

from django.core.management import call_command

from celery import shared_task


@shared_task(bind=True)
def debug_task(self):
    """
    Debug task para testar o setup do Celery.

    Uso:
        from apps.core.tasks import debug_task
        debug_task.delay()

    Returns:
        str: "ok"
    """
    print(f"Request: {self.request!r}")
    return "ok"


@shared_task
def gcal_sync_task():
    """
    Tarefa stub para sincronização futura com Google Calendar.

    TODO: Implementar lógica de sincronização.

    Possíveis implementações:
    - Sincronizar eventos pendentes
    - Atualizar eventos modificados
    - Remover eventos cancelados
    - Integrar com preview_then_apply_gcal

    Returns:
        dict: Resultado da sincronização (quando implementado)
    """
    # TODO: Implementar lógica de sincronização
    pass


@shared_task(name="apps.core.tasks.task_publish_solicitacao_to_gcal")
def task_publish_solicitacao_to_gcal(
    solicitation_id: int, dry_run: bool = False, apply_blocked: bool = False
):
    """
    Publica uma Solicitacao no Google Calendar (via Celery).

    Args:
        solicitation_id: ID da Solicitacao a publicar
        dry_run: Se True, não persiste mudanças no DB/Calendar
        apply_blocked: Se True, aplica mesmo sem GCAL_CLIENT configurado

    Returns:
        dict: {
            "action": str (CREATE/UPDATE/DELETE/ADOPT/SKIP),
            "solicitation_id": int,
            "external_event_id": str | None,
            "summary": str,
            "error": str | None
        }
    """
    from apps.core.models import Solicitacao, AuditLog
    from apps.core.services.gcal_sync_service import apply_one_solicitacao

    try:
        # Buscar solicitação
        s = Solicitacao.objects.get(id=solicitation_id)

        # Aplicar publicação
        outcome = apply_one_solicitacao(s, dry_run=dry_run, apply_blocked=apply_blocked)

        # Criar AuditLog (apenas se não for dry_run)
        if not dry_run:
            AuditLog.objects.create(
                usuario=None,  # Task assíncrona, sem usuário direto
                action="PUBLISH_GCAL",
                model_name="Solicitacao",
                details={
                    "solicitacao_id": s.id,
                    "action": outcome.action,
                    "external_event_id": outcome.external_event_id,
                    "summary": outcome.summary,
                    "dry_run": dry_run,
                    "apply_blocked": apply_blocked,
                },
            )

        return {
            "action": outcome.action,
            "solicitation_id": outcome.solicitation_id,
            "external_event_id": outcome.external_event_id,
            "summary": outcome.summary,
            "error": None,
        }

    except Solicitacao.DoesNotExist:
        return {
            "action": "ERROR",
            "solicitation_id": solicitation_id,
            "external_event_id": None,
            "summary": f"Solicitação #{solicitation_id} não encontrada",
            "error": "DoesNotExist",
        }
    except Exception as e:
        return {
            "action": "ERROR",
            "solicitation_id": solicitation_id,
            "external_event_id": None,
            "summary": f"Erro ao publicar: {str(e)}",
            "error": str(e)[:500],
        }


@shared_task(name="apps.core.tasks.task_cancel_solicitacao_from_gcal")
def task_cancel_solicitacao_from_gcal(solicitation_id: int):
    """
    Cancela evento de uma Solicitacao no Google Calendar (via Celery) - Fase 4.

    Deleta evento do Calendar e limpa campos relacionados (external_event_id,
    meet_link, gcal_payload_hash). Trata 404 como sucesso (idempotência).

    Args:
        solicitation_id: ID da Solicitacao a cancelar

    Returns:
        dict: {
            "action": "DELETE" | "ERROR",
            "solicitation_id": int,
            "external_event_id": str | None,
            "summary": str,
            "error": str | None
        }
    """
    from apps.core.models import Solicitacao, AuditLog
    from apps.core.services.gcal_sync_service import cancel_solicitacao

    try:
        # Buscar solicitação
        s = Solicitacao.objects.get(id=solicitation_id)

        # Cancelar evento no Calendar e limpar campos
        outcome = cancel_solicitacao(s)

        # Criar AuditLog
        AuditLog.objects.create(
            usuario=None,  # Task assíncrona, sem usuário direto
            action="CANCEL_GCAL",
            model_name="Solicitacao",
            details={
                "solicitacao_id": s.id,
                "action": outcome.action,
                "external_event_id": outcome.external_event_id,
                "summary": outcome.summary,
            },
        )

        return {
            "action": outcome.action,
            "solicitation_id": outcome.solicitation_id,
            "external_event_id": outcome.external_event_id,
            "summary": outcome.summary,
            "error": None,
        }

    except Solicitacao.DoesNotExist:
        return {
            "action": "ERROR",
            "solicitation_id": solicitation_id,
            "external_event_id": None,
            "summary": f"Solicitação #{solicitation_id} não encontrada",
            "error": "DoesNotExist",
        }
    except Exception as e:
        return {
            "action": "ERROR",
            "solicitation_id": solicitation_id,
            "external_event_id": None,
            "summary": f"Erro ao cancelar: {str(e)}",
            "error": str(e)[:500],
        }


@shared_task(name="apps.core.tasks.preview_then_apply_gcal")
def preview_then_apply_gcal():
    """
    Preview-then-apply pattern para sync com Google Calendar.

    Workflow:
    0. Verifica FEATURE_AUTO_APPLY_ENABLED (Fase 3 - Governança GCal)
    1. Verifica feature flags (GCAL_MODE, GCAL_CALENDAR_ID)
    2. Roda dry-run (preview) com --json
    3. Se preview retornar erro, aborta sem apply
    4. Se total > 0 (há mudanças):
       - Se PREVIEW_ONLY não estiver ativo, roda efetivo (apply) com --json
       - Retorna resultado do apply
    5. Se total == 0 (sem mudanças):
       - Retorna resultado do preview (noop)
    6. Registra AuditLog em todos os fluxos

    Returns:
        dict: Resultado JSON (meta + totals + status)
    """
    from django.conf import settings
    from apps.core.models import AuditLog

    # ================================================================
    # GUARDA 0: Verificar FEATURE_AUTO_APPLY_ENABLED (Fase 3)
    # ================================================================
    # Governança GCal consolidada: publicações ocorrem SOMENTE via /pre-agenda
    # Auto-apply do Celery desativado por padrão (FEATURE_AUTO_APPLY_ENABLED=0)
    auto_apply_enabled = getattr(settings, "FEATURE_AUTO_APPLY_ENABLED", False)

    if not auto_apply_enabled:
        result = {
            "status": "SKIPPED",
            "reason": "FEATURE_AUTO_APPLY_ENABLED=False (auto-apply desativado, governança via /pre-agenda)",
        }
        AuditLog.objects.create(
            usuario=None,
            action="CELERY_GCAL_SYNC",
            model_name=None,
            details=result,
        )
        return result

    # ================================================================
    # GUARDA 1: Verificar GCAL_MODE
    # ================================================================
    feature_flags = getattr(settings, "FEATURE_FLAGS", {})
    gcal_mode = feature_flags.get("GCAL_MODE", "google")

    if gcal_mode != "google":
        result = {
            "status": "SKIPPED",
            "reason": f"GCAL_MODE={gcal_mode} (esperado: 'google')",
        }
        AuditLog.objects.create(
            usuario=None,
            action="CELERY_GCAL_SYNC",
            model_name=None,
            details=result,
        )
        return result

    # ================================================================
    # GUARDA 2: Verificar GCAL_CALENDAR_ID
    # ================================================================
    gcal_calendar_id = getattr(settings, "GCAL_CALENDAR_ID", "")

    if not gcal_calendar_id:
        result = {
            "status": "SKIPPED",
            "reason": "GCAL_CALENDAR_ID não configurado",
        }
        AuditLog.objects.create(
            usuario=None,
            action="CELERY_GCAL_SYNC",
            model_name=None,
            details=result,
        )
        return result

    # ================================================================
    # PASSO 1: PREVIEW (dry-run)
    # ================================================================
    preview_stdout = StringIO()
    call_command(
        "preagenda_to_gcal",
        "--dry-run",
        "--json",
        stdout=preview_stdout,
    )
    preview_output = preview_stdout.getvalue()
    preview_result = json.loads(preview_output)

    # Verificar se preview retornou erro
    if preview_result.get("error") is True:
        result = {
            "status": "ERROR",
            "phase": "preview",
            "error": True,
            "message": preview_result.get("message", "Erro desconhecido no preview"),
        }
        AuditLog.objects.create(
            usuario=None,
            action="CELERY_GCAL_SYNC",
            model_name=None,
            details=result,
        )
        return result

    # Verificar se há mudanças
    totals = preview_result.get("totals", {})
    total_changes = (
        totals.get("CREATE", 0)
        + totals.get("UPDATE", 0)
        + totals.get("ADOPT", 0)
        + totals.get("DELETE", 0)
    )

    # Se sem mudanças, retornar preview (noop)
    if total_changes == 0:
        result = {
            "status": "NOOP",
            "preview": preview_result,
            "applied": False,
            "reason": "No changes detected (total_changes == 0)",
        }
        AuditLog.objects.create(
            usuario=None,
            action="CELERY_GCAL_SYNC",
            model_name=None,
            details=result,
        )
        return result

    # ================================================================
    # GUARDA 3: Verificar PREVIEW_ONLY
    # ================================================================
    preview_only = feature_flags.get("PREVIEW_ONLY", False)

    if preview_only:
        result = {
            "status": "SUCCESS",
            "preview": preview_result,
            "applied": False,
            "total_changes": total_changes,
            "reason": f"{total_changes} mudanças detectadas, mas PREVIEW_ONLY bloqueou apply",
        }
        AuditLog.objects.create(
            usuario=None,
            action="CELERY_GCAL_SYNC",
            model_name=None,
            details=result,
        )
        return result

    # ================================================================
    # PASSO 2: APPLY (efetivo)
    # ================================================================
    apply_stdout = StringIO()
    call_command(
        "preagenda_to_gcal",
        "--json",
        stdout=apply_stdout,
    )
    apply_output = apply_stdout.getvalue()
    apply_result = json.loads(apply_output)

    # Verificar se apply retornou erro
    if apply_result.get("error") is True:
        result = {
            "status": "ERROR",
            "phase": "apply",
            "error": True,
            "applied": False,
            "message": apply_result.get("message", "Erro desconhecido no apply"),
            "preview": preview_result,
        }
        AuditLog.objects.create(
            usuario=None,
            action="CELERY_GCAL_SYNC",
            model_name=None,
            details=result,
        )
        return result

    result = {
        "status": "APPLIED",
        "preview": preview_result,
        "apply": apply_result,
        "applied": True,
        "total_changes": total_changes,
        "reason": f"Applied {total_changes} changes",
    }
    AuditLog.objects.create(
        usuario=None,
        action="CELERY_GCAL_SYNC",
        model_name=None,
        details=result,
    )
    return result

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
                    "solicitation_id": s.id,
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


@shared_task(name="apps.core.tasks.preview_then_apply_gcal")
def preview_then_apply_gcal():
    """
    Preview-then-apply pattern para sync com Google Calendar.

    Workflow:
    1. Roda dry-run (preview) com --json
    2. Se total > 0 (há mudanças):
       - Roda efetivo (apply) com --json
       - Retorna resultado do apply
    3. Se total == 0 (sem mudanças):
       - Retorna resultado do preview (noop)

    Returns:
        dict: Resultado JSON (meta + totals)
    """
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
        return {
            "preview": preview_result,
            "applied": False,
            "reason": "No changes detected (total_changes == 0)",
        }

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

    return {
        "preview": preview_result,
        "apply": apply_result,
        "applied": True,
        "reason": f"Applied {total_changes} changes",
    }

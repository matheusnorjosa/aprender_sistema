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

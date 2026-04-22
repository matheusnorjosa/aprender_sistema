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

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false, reportGeneralTypeIssues=false

from __future__ import annotations

import json
import logging
from datetime import date
from io import StringIO
from typing import Any

from django.core.management import call_command

from celery import shared_task  # type: ignore[attr-defined]

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def debug_task(self: Any) -> str:
    """
    Debug task para testar o setup do Celery.

    Uso:
        from apps.core.tasks import debug_task
        debug_task.delay()

    Returns:
        str: "ok"
    """
    logger.debug(f"Request: {self.request!r}")
    return "ok"


@shared_task
def gcal_sync_task() -> None:
    """
    DEPRECATED: Tarefa stub para sincronização com Google Calendar.

    Esta task não está em uso. A sincronização real é feita via:
    - preview_then_apply_gcal (Celery beat automático)
    - task_publish_solicitacao_to_gcal (publicação individual)
    - /pre-agenda UI (governança manual)

    Mantida para backwards compatibility. Não implementar lógica aqui.

    Returns:
        None
    """
    logger.warning("gcal_sync_task is deprecated and does nothing. Use preview_then_apply_gcal instead.")
    pass


@shared_task(name="apps.core.tasks.task_publish_solicitacao_to_gcal")
def task_publish_solicitacao_to_gcal(
    solicitation_id: int,
    dry_run: bool = False,
    apply_blocked: bool = False,
    operator_user_id: int | None = None,
) -> dict[str, Any]:
    """
    Publica uma Solicitacao no Google Calendar (via Celery).

    OAuth Phase 3: Aceita operator_user_id para autenticação OAuth.

    Args:
        solicitation_id: ID da Solicitacao a publicar
        dry_run: Se True, não persiste mudanças no DB/Calendar
        apply_blocked: Se True, aplica mesmo sem GCAL_CLIENT configurado
        operator_user_id: ID do usuário operador (OAuth mode)

    Returns:
        dict: {
            "action": str (CREATE/UPDATE/DELETE/ADOPT/SKIP/ERROR),
            "solicitation_id": int,
            "external_event_id": str | None,
            "summary": str,
            "error": str | None
        }
    """
    from django.conf import settings

    from apps.core.models import AuditLog, Solicitacao, Usuario
    from apps.core.services.gcal_sync_service import apply_one_solicitacao

    # OAuth Phase 3: Verificar modo OAuth e criar cliente se necessário
    auth_mode = getattr(settings, "GCAL_AUTH_MODE", "service_account")
    client = None
    operator = None
    google_email = None

    if auth_mode == "oauth" and not dry_run:
        # OAuth mode requer operator_user_id
        if operator_user_id is None:
            return {
                "action": "ERROR",
                "solicitation_id": solicitation_id,
                "external_event_id": None,
                "summary": "OAuth mode requer operator_user_id",
                "error": "missing_operator_user_id",
            }

        try:
            # Carregar usuário operador
            operator = Usuario.objects.get(id=operator_user_id)

            # Criar cliente OAuth
            from apps.core.services.gcal_client_factory import get_oauth_client_for_user

            client, _ = get_oauth_client_for_user(operator)
            google_email = client.credential.google_email

        except Usuario.DoesNotExist:
            return {
                "action": "ERROR",
                "solicitation_id": solicitation_id,
                "external_event_id": None,
                "summary": f"Usuário operador #{operator_user_id} não encontrado",
                "error": "operator_not_found",
            }
        except ValueError as e:
            # get_oauth_client_for_user pode lançar ValueError se não há credencial
            return {
                "action": "ERROR",
                "solicitation_id": solicitation_id,
                "external_event_id": None,
                "summary": str(e),
                "error": "oauth_credential_missing",
            }

    try:
        # Buscar solicitação
        s = Solicitacao.objects.get(id=solicitation_id)

        # Aplicar publicação (com cliente OAuth se disponível)
        outcome = apply_one_solicitacao(s, dry_run=dry_run, apply_blocked=apply_blocked, client=client)

        # Criar AuditLog (apenas se não for dry_run)
        if not dry_run:
            audit_details = {
                "solicitacao_id": s.id,
                "action": outcome.action,
                "external_event_id": outcome.external_event_id,
                "summary": outcome.summary,
                "dry_run": dry_run,
                "apply_blocked": apply_blocked,
            }

            # OAuth Phase 3: Incluir google_email no AuditLog se disponível
            if google_email:
                audit_details["google_email"] = google_email
                audit_details["operator_user_id"] = operator_user_id

            AuditLog.objects.create(
                usuario=operator,  # OAuth: registrar operador; service_account: None
                action="PUBLISH_GCAL",
                model_name="Solicitacao",
                details=audit_details,
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
        # Tentar registrar erro e estado se a solicitação existir
        try:
            s = Solicitacao.objects.get(id=solicitation_id)
            # Marcar status de erro
            try:
                s.mark_gcal(
                    status=Solicitacao.GCalStatus.ERROR,
                    payload_hash=None,
                    error=str(e)[:500],
                )
            except Exception:
                pass  # Falha ao marcar não deve bloquear o retorno

            # Registrar AuditLog somente quando não for dry-run
            if not dry_run:
                AuditLog.objects.create(
                    usuario=None,  # Task assíncrona
                    action="PUBLISH_GCAL_ERROR",
                    model_name="Solicitacao",
                    details={
                        "solicitacao_id": s.id,
                        "error": str(e)[:500],
                        "dry_run": dry_run,
                        "apply_blocked": apply_blocked,
                    },
                )
        except Solicitacao.DoesNotExist:
            pass  # Solicitação não existe, não há o que marcar

        return {
            "action": "ERROR",
            "solicitation_id": solicitation_id,
            "external_event_id": None,
            "summary": f"Erro ao publicar: {str(e)}",
            "error": str(e)[:500],
        }


@shared_task(name="apps.core.tasks.task_cancel_solicitacao_from_gcal")
def task_cancel_solicitacao_from_gcal(
    solicitation_id: int,
    operator_user_id: int | None = None,
) -> dict[str, Any]:
    """
    Cancela evento de uma Solicitacao no Google Calendar (via Celery) - Fase 4.

    Deleta evento do Calendar e limpa campos relacionados (external_event_id,
    meet_link, gcal_payload_hash). Trata 404 como sucesso (idempotência).

    Args:
        solicitation_id: ID da Solicitacao a cancelar
        operator_user_id: ID do usuário operador (OAuth mode, fix #572)

    Returns:
        dict: {
            "action": "DELETE" | "ERROR",
            "solicitation_id": int,
            "external_event_id": str | None,
            "summary": str,
            "error": str | None
        }
    """
    from django.conf import settings

    from apps.core.models import AuditLog, Solicitacao, Usuario
    from apps.core.services.gcal_sync_service import cancel_solicitacao

    # OAuth: create OAuth client if needed (fix #572)
    auth_mode = getattr(settings, "GCAL_AUTH_MODE", "service_account")
    client = None

    if auth_mode == "oauth" and operator_user_id is not None:
        try:
            operator = Usuario.objects.get(id=operator_user_id)
            from apps.core.services.gcal_client_factory import get_oauth_client_for_user

            client, _ = get_oauth_client_for_user(operator)
        except (Usuario.DoesNotExist, ValueError) as e:
            return {
                "action": "ERROR",
                "solicitation_id": solicitation_id,
                "external_event_id": None,
                "summary": f"OAuth credential error: {e}",
                "error": str(e)[:500],
            }

    try:
        # Buscar solicitação
        s = Solicitacao.objects.get(id=solicitation_id)

        # Cancelar evento no Calendar e limpar campos
        outcome = cancel_solicitacao(s, client=client)

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


@shared_task(name="apps.core.tasks.processar_notificacoes_acoes_diarias")
def processar_notificacoes_acoes_diarias(reference_date_iso: str | None = None) -> dict[str, Any]:
    """
    Processa notificacoes de acoes internas (D-7/D-3/D-1/D0 e D+1/D+3).

    Args:
        reference_date_iso: data de referencia no formato YYYY-MM-DD (opcional).
            Quando vazio, usa timezone.localdate().

    Returns:
        dict com metricas da execucao (acoes avaliadas/disparadas, criadas, deduplicadas, fases).
    """
    from apps.core.services.notificacoes_acoes_service import AcoesNotificacaoDailyService

    parsed_date: date | None = None
    if reference_date_iso:
        parsed_date = date.fromisoformat(reference_date_iso)
    return AcoesNotificacaoDailyService.run(reference_date=parsed_date)


@shared_task(name="apps.core.tasks.preview_then_apply_gcal")
def preview_then_apply_gcal() -> dict[str, Any]:
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
    total_changes = totals.get("CREATE", 0) + totals.get("UPDATE", 0) + totals.get("ADOPT", 0) + totals.get("DELETE", 0)

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


@shared_task(
    bind=True,
    name="apps.core.tasks.task_run_import_job",
    acks_late=True,
)
def task_run_import_job(self: Any, import_job_id: int) -> dict[str, Any]:
    """
    Executa um ImportJob assincronamente (ASQ-005 fase 1).

    Reentrance-safe via guard de status: se o job nao estiver em QUEUED,
    retorna SKIPPED sem reexecutar o service. Isso protege contra re-enqueues
    apos crash de worker (acks_late=True).

    Args:
        import_job_id: ID do ImportJob a executar

    Returns:
        dict com:
            - action: "SUCCESS" | "FAILED" | "SKIPPED" | "NOT_FOUND"
            - import_job_id: int
            - import_type: str (quando aplicavel)
            - status: str (estado final do job)
            - stats: dict (quando SUCCESS)
            - error: str | None
    """
    import traceback

    from django.db import transaction

    from apps.core.models import AuditLog, ImportJob
    from apps.core.services.bloqueios_import import import_bloqueios_from_file

    # ================================================================
    # GUARDA: Job existe?
    # ================================================================
    try:
        job = ImportJob.objects.get(id=import_job_id)
    except ImportJob.DoesNotExist:
        logger.warning(f"task_run_import_job: ImportJob #{import_job_id} nao encontrado")
        return {
            "action": "NOT_FOUND",
            "import_job_id": import_job_id,
            "error": "DoesNotExist",
        }

    # ================================================================
    # GUARDA: idempotencia (previne duplo-run apos re-enqueue)
    # ================================================================
    with transaction.atomic():
        locked = ImportJob.objects.select_for_update().get(id=import_job_id)
        if locked.status != ImportJob.Status.QUEUED:
            logger.info(f"task_run_import_job: job #{import_job_id} ja estava em status={locked.status}, skipping")
            return {
                "action": "SKIPPED",
                "import_job_id": import_job_id,
                "status": locked.status,
                "reason": f"status={locked.status}",
            }
        # Transicao QUEUED -> RUNNING atomica
        locked.mark_running(celery_task_id=self.request.id or "")
        job = locked

    # ================================================================
    # EXECUCAO: despacho por tipo
    # ================================================================
    try:
        file_path = job.file.path

        if job.import_type == ImportJob.ImportType.BLOQUEIOS:
            report = import_bloqueios_from_file(path=file_path, dry_run=job.dry_run)
        else:
            # Fase 2 adicionara: usuarios, compras, etc.
            raise NotImplementedError(f"import_type={job.import_type} nao suportado nesta fase")

        stats = report.get("stats", {})
        pendencias = report.get("pendencias", {})

        job.mark_success(stats=stats, pendencias=pendencias)

        AuditLog.objects.create(
            usuario=job.user,
            action="IMPORT_JOB_COMPLETED",
            model_name="ImportJob",
            details={
                "import_job_id": job.id,
                "import_type": job.import_type,
                "dry_run": job.dry_run,
                "stats": stats,
                "pendencias_counts": {k: len(v) for k, v in pendencias.items() if isinstance(v, list)},
            },
        )

        return {
            "action": "SUCCESS",
            "import_job_id": job.id,
            "import_type": job.import_type,
            "status": job.status,
            "stats": stats,
            "error": None,
        }

    except Exception as exc:
        tb = traceback.format_exc()
        err_msg = str(exc)
        logger.exception(f"task_run_import_job: erro ao executar job #{import_job_id}")

        try:
            job.refresh_from_db()
            job.mark_failed(error_message=err_msg, error_traceback=tb)
        except Exception:
            # Se falhar ate marcar o job, pelo menos registra no AuditLog abaixo
            logger.exception(f"task_run_import_job: falha ao marcar job #{import_job_id} como FAILED")

        try:
            AuditLog.objects.create(
                usuario=job.user if job.user_id else None,
                action="IMPORT_JOB_FAILED",
                model_name="ImportJob",
                details={
                    "import_job_id": import_job_id,
                    "import_type": job.import_type,
                    "dry_run": job.dry_run,
                    "error": err_msg[:500],
                },
            )
        except Exception:
            logger.exception(f"task_run_import_job: falha ao criar AuditLog para #{import_job_id}")

        return {
            "action": "FAILED",
            "import_job_id": import_job_id,
            "import_type": job.import_type,
            "status": ImportJob.Status.FAILED,
            "error": err_msg[:500],
        }


@shared_task(
    bind=True,
    name="apps.core.tasks.queue_gcal_sync_retry",
    max_retries=10,
    default_retry_delay=300,  # 5 minutes
)
def queue_gcal_sync_retry(
    self: Any,
    solicitation_id: int,
    *,
    dry_run: bool = False,
    apply_blocked: bool = False,
) -> dict[str, Any]:
    """
    Retry GCal sync when circuit breaker closes (Gap 6 - PLAN_maturity_gaps.md).

    This task is queued when the circuit breaker is open. It waits for the
    circuit to close before attempting to sync.

    Args:
        solicitation_id: ID of the Solicitacao to sync
        dry_run: If True, don't persist changes
        apply_blocked: If True, apply even without GCAL_CLIENT configured

    Returns:
        dict: Result with action, status, and any errors
    """
    from apps.core.models import AuditLog, Solicitacao
    from apps.core.services.gcal.circuit_breaker import gcal_breaker

    # Check circuit breaker state
    if str(gcal_breaker.current_state) == "open":
        # Circuit still open, retry later
        logger.info(
            f"Circuit breaker still open for Solicitacao #{solicitation_id}, "
            f"retrying in 60s (attempt {self.request.retries + 1}/{self.max_retries})"
        )
        raise self.retry(countdown=60)

    # Circuit is closed or half-open, attempt sync
    try:
        s = Solicitacao.objects.get(id=solicitation_id)

        from apps.core.services.gcal_sync_service import apply_one_solicitacao

        outcome = apply_one_solicitacao(s, dry_run=dry_run, apply_blocked=apply_blocked)

        # Log successful retry
        if not dry_run:
            AuditLog.objects.create(
                usuario=None,
                action="GCAL_RETRY_SUCCESS",
                model_name="Solicitacao",
                details={
                    "solicitacao_id": s.id,
                    "action": outcome.action,
                    "external_event_id": outcome.external_event_id,
                    "retry_attempt": self.request.retries + 1,
                },
            )

        return {
            "action": outcome.action,
            "solicitation_id": outcome.solicitation_id,
            "external_event_id": outcome.external_event_id,
            "summary": outcome.summary,
            "retry_attempt": self.request.retries + 1,
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
        # Check if it's a circuit breaker error
        from apps.core.services.gcal.circuit_breaker import CircuitBreakerError

        if isinstance(e, CircuitBreakerError):
            logger.warning(
                f"Circuit breaker triggered during retry for #{solicitation_id}, "
                f"requeing (attempt {self.request.retries + 1}/{self.max_retries})"
            )
            raise self.retry(countdown=60, exc=e)

        # Other errors - log and propagate
        logger.exception(f"Error during GCal retry for #{solicitation_id}")
        return {
            "action": "ERROR",
            "solicitation_id": solicitation_id,
            "external_event_id": None,
            "summary": f"Erro ao sincronizar: {str(e)}",
            "error": str(e)[:500],
        }

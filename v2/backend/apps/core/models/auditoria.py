"""
AS v2 — Auditoria Model

Model de logs de auditoria.
Clausula Petrea: PA-05 (registro de aprovacoes/reprovacoes).
Type-checked with Pyright (strict mode).
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone


class AuditLog(models.Model):
    """
    Log de auditoria para rastreamento de operacoes criticas.

    - Registra acoes como: CELERY_GCAL_SYNC, approve, reject, create, update, delete
    - Details: JSON com contexto da operacao (status, applied, reason, etc.)
    - PA-05: Obrigatorio para aprovacoes/reprovacoes
    """

    class Action(models.TextChoices):
        """Enum canonico das acoes de auditoria.

        Valores sao preservados como strings (compat retroativa com registros
        historicos). Para novos call sites, prefira o enum em vez de literal:

            AuditLog.objects.create(action=AuditLog.Action.APPROVE, ...)

        Choices NAO sao aplicadas ao field para preservar flexibilidade
        operacional e nao forcar migration; o enum serve como SSOT para call
        sites de codigo e como referencia documental. Auditoria 2026-05 (B1).
        """

        # Solicitacao approval (PA-05)
        APPROVE = "APPROVE", "Aprovar"
        REJECT = "REJECT", "Rejeitar"

        # CRUD genericos
        CREATE = "CREATE", "Criar"
        UPDATE = "UPDATE", "Atualizar"
        DELETE = "DELETE", "Deletar"

        # Auth
        LOGIN = "LOGIN", "Login"
        LOGOUT = "LOGOUT", "Logout"
        LOGIN_FAILED = "LOGIN_FAILED", "Login falhou"
        LOGIN_BLOCKED = "LOGIN_BLOCKED", "Login bloqueado"

        # GCal lifecycle
        PREVIEW_GCAL = "PREVIEW_GCAL", "Preview GCal"
        PUBLISH_GCAL_REQUESTED = "PUBLISH_GCAL_REQUESTED", "Publicacao GCal solicitada"
        PUBLISH_GCAL = "PUBLISH_GCAL", "Publicada no GCal"
        PUBLISH_GCAL_ERROR = "PUBLISH_GCAL_ERROR", "Erro publicando GCal"
        RESYNC_GCAL_REQUESTED = "RESYNC_GCAL_REQUESTED", "Resync GCal solicitado"
        CANCEL_GCAL_REQUESTED = "CANCEL_GCAL_REQUESTED", "Cancelamento GCal solicitado"
        CANCEL_GCAL = "CANCEL_GCAL", "Cancelada no GCal"
        CELERY_GCAL_SYNC = "CELERY_GCAL_SYNC", "Sync GCal via Celery"
        GCAL_RETRY_SUCCESS = "GCAL_RETRY_SUCCESS", "Retry GCal bem-sucedido"
        GCAL_ENCRYPTION_KEY_ROTATION = "GCAL_ENCRYPTION_KEY_ROTATION", "Rotacao chave GCal"

        # OAuth Google
        GOOGLE_CONNECT = "GOOGLE_CONNECT", "Conectar Google"
        GOOGLE_DISCONNECT = "GOOGLE_DISCONNECT", "Desconectar Google"
        GOOGLE_REFRESH_TOKEN = "GOOGLE_REFRESH_TOKEN", "Refresh token Google"
        GOOGLE_SELECT_CALENDAR = "GOOGLE_SELECT_CALENDAR", "Selecionar calendario Google"

        # Import jobs
        IMPORT_JOB_COMPLETED = "IMPORT_JOB_COMPLETED", "Import job concluido"
        IMPORT_JOB_FAILED = "IMPORT_JOB_FAILED", "Import job falhou"

        # Deslocamento
        CREATE_DESLOCAMENTO = "CREATE_DESLOCAMENTO", "Criar deslocamento"
        UPDATE_DESLOCAMENTO = "UPDATE_DESLOCAMENTO", "Atualizar deslocamento"
        DELETE_DESLOCAMENTO = "DELETE_DESLOCAMENTO", "Deletar deslocamento"

        # Bloqueios delegados
        DELEGATE_BLOCK_CREATE = "DELEGATE_BLOCK_CREATE", "Criar bloqueio delegado"

        # Notificacoes
        CICLO_ACOES_CREATE = "CICLO_ACOES_CREATE", "Criar ciclo de acoes"
        ACAO_REGISTRAR_ANCORA = "ACAO_REGISTRAR_ANCORA", "Registrar ancora de acao"
        ACAO_CONCLUIR = "ACAO_CONCLUIR", "Concluir acao"
        ACOES_NOTIFICACOES_DAILY = "ACOES_NOTIFICACOES_DAILY", "Notificacoes diarias"

        # Admin
        SYNC_GROUP_MEMBERS = "SYNC_GROUP_MEMBERS", "Sincronizar membros do grupo"
        GROUP_CAPABILITY_CHANGED = "GROUP_CAPABILITY_CHANGED", "Capability de grupo alterada"
        UPDATE_CONFIG = "UPDATE_CONFIG", "Atualizar configuracao"

    usuario = models.ForeignKey(  # type: ignore[misc]
        "core.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        help_text="Usuario que executou a acao (se aplicavel)",
    )
    action = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Acao executada (use AuditLog.Action enum; legacy strings preservadas)",
    )
    model_name = models.CharField(
        max_length=60,
        null=True,
        blank=True,
        db_index=True,
        help_text="Nome do modelo relacionado (opcional, ex: Solicitacao, Compra)",
    )
    details = models.JSONField(  # type: ignore[misc]
        default=dict, help_text="Detalhes da operacao (status, applied, reason, etc.)"
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:  # type: ignore[misc]
        db_table = "core_audit_log"
        verbose_name = "Log de Auditoria"
        verbose_name_plural = "Logs de Auditoria"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["usuario", "created_at"]),
        ]

    def __str__(self) -> str:
        usuario_str = self.usuario.get_full_name() if self.usuario else "Sistema"
        return f"{usuario_str} - {self.action} ({self.created_at.strftime('%d/%m/%Y %H:%M')})"

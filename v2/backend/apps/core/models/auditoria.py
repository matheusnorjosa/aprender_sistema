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

    usuario = models.ForeignKey(  # type: ignore[misc]
        "core.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        help_text="Usuario que executou a acao (se aplicavel)"
    )
    action = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Acao executada (ex: CELERY_GCAL_SYNC, approve, reject)"
    )
    model_name = models.CharField(
        max_length=60,
        null=True,
        blank=True,
        db_index=True,
        help_text="Nome do modelo relacionado (opcional, ex: Solicitacao, Compra)"
    )
    details = models.JSONField(  # type: ignore[misc]
        default=dict,
        help_text="Detalhes da operacao (status, applied, reason, etc.)"
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

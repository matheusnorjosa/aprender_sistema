"""
ImportLog - Rastreamento de imports para idempotência
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportIncompatibleMethodOverride=false


from __future__ import annotations
from django.db import models
from django.utils import timezone


class ImportLog(models.Model):
    """Log de importações ETL (idempotência via hash SHA256)"""

    file = models.CharField(
        max_length=255, help_text="Caminho completo do arquivo importado"
    )
    sha256 = models.CharField(
        max_length=64, db_index=True, help_text="Hash SHA256 do arquivo"
    )
    rows_processed = models.IntegerField(
        default=0, help_text="Número de linhas processadas"
    )
    rows_success = models.IntegerField(
        default=0, help_text="Linhas importadas com sucesso"
    )
    rows_failed = models.IntegerField(default=0, help_text="Linhas que falharam")

    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    ok = models.BooleanField(default=False, help_text="Import concluído com sucesso")

    error_message = models.TextField(
        blank=True, default="", help_text="Mensagem de erro (se houver)"
    )
    metadata = models.JSONField(
        default=dict, blank=True, help_text="Metadados adicionais"
    )

    class Meta:  # type: ignore[misc]
        db_table = "dat_import_log"
        verbose_name = "Import Log"
        verbose_name_plural = "Import Logs"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["file", "sha256"]),
            models.Index(fields=["ok", "started_at"]),
        ]

    def __str__(self):
        status = "✓" if self.ok else "✗"
        return f"{status} {self.file} ({self.rows_success}/{self.rows_processed}) - {self.started_at.strftime('%Y-%m-%d %H:%M')}"

    def mark_finished(self, success: bool = True, error: str = ""):
        """Marca o log como finalizado"""
        self.finished_at = timezone.now()
        self.ok = success
        if error:
            self.error_message = error
        self.save()

    @property
    def duration(self):
        """Duração do import em segundos"""
        if not self.finished_at:
            return None
        return (self.finished_at - self.started_at).total_seconds()

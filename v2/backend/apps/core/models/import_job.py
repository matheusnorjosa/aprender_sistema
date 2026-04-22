"""
AS v2 — ImportJob Model (ASQ-005)

Rastreamento de execucoes assincronas de ETL (imports). Cada linha representa
uma tentativa de importar um arquivo para uma entidade (bloqueios, compras,
usuarios, etc.), com estado de fila -> execucao -> conclusao/falha.

Fase 1 (#778): piloto com `bloqueios`. Fase 2 migra os demais 9 imports.

Type-checked with Pyright (strict mode).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportArgumentType=false, reportOperatorIssue=false, reportAttributeAccessIssue=false, reportUnknownArgumentType=false

from __future__ import annotations

from typing import Any

from django.db import models
from django.utils import timezone


class ImportJob(models.Model):
    """
    Job assincrono de importacao (ETL).

    Ciclo de vida:
        QUEUED -> RUNNING -> SUCCESS | FAILED

    Criado pelo endpoint de upload; transicoes governadas pela Celery task
    `apps.core.tasks.task_run_import_job`. O arquivo submetido permanece em
    `imports/<type>/%Y/%m/%d/` sob MEDIA_ROOT para auditoria.
    """

    class Status(models.TextChoices):
        QUEUED = "QUEUED", "Na fila"
        RUNNING = "RUNNING", "Executando"
        SUCCESS = "SUCCESS", "Concluido"
        FAILED = "FAILED", "Falhou"

    class ImportType(models.TextChoices):
        BLOQUEIOS = "bloqueios", "Bloqueios"
        # Fase 2 adicionara: USUARIOS, COMPRAS, ACOES, DESLOCAMENTOS,
        # EVENTOS, PRODUTOS, MUNICIPIOS, COLECOES, EQUIPE_GERENCIA

    user = models.ForeignKey(  # type: ignore[misc]
        "core.Usuario",
        on_delete=models.PROTECT,
        related_name="import_jobs",
        help_text="Usuario que disparou o import (auditoria)",
    )
    import_type = models.CharField(
        max_length=32,
        choices=ImportType.choices,
        db_index=True,
        help_text="Tipo de import (bloqueios, usuarios, etc.)",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.QUEUED,
        db_index=True,
        help_text="Estado atual do job",
    )
    file = models.FileField(  # type: ignore[misc]
        upload_to="imports/%Y/%m/%d/",
        max_length=500,
        help_text="Arquivo submetido (mantido para auditoria)",
    )
    original_filename = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="Nome original do arquivo submetido (preservado separado do FileField)",
    )
    dry_run = models.BooleanField(
        default=True,
        help_text="Se True, service roda e retorna stats mas da rollback",
    )
    stats = models.JSONField(  # type: ignore[misc]
        default=dict,
        blank=True,
        help_text="Contadores populados pelo service ao concluir",
    )
    pendencias = models.JSONField(  # type: ignore[misc]
        default=dict,
        blank=True,
        help_text="Linhas rejeitadas/pendentes por categoria (usuarios, dates, outros)",
    )
    error_message = models.TextField(
        blank=True,
        default="",
        help_text="Mensagem curta (ate 500 chars) quando status=FAILED",
    )
    error_traceback = models.TextField(
        blank=True,
        default="",
        help_text="Traceback completo do erro (nao exposto na API)",
    )
    celery_task_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
        help_text="ID da task Celery para correlacao com logs/flower",
    )
    duration_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Tempo total de execucao (finished_at - started_at) em ms",
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_import_job"
        verbose_name = "Job de Importacao"
        verbose_name_plural = "Jobs de Importacao"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["import_type", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.import_type} #{self.pk} ({self.status})"

    def mark_running(self, *, celery_task_id: str) -> None:
        """Transicao QUEUED -> RUNNING. Grava started_at e celery_task_id."""
        self.status = self.Status.RUNNING
        self.celery_task_id = celery_task_id
        self.started_at = timezone.now()
        self.save(update_fields=["status", "celery_task_id", "started_at", "updated_at"])

    def mark_success(self, *, stats: dict[str, Any], pendencias: dict[str, Any]) -> None:
        """Transicao RUNNING -> SUCCESS. Grava stats, pendencias, finished_at, duration_ms."""
        now = timezone.now()
        self.status = self.Status.SUCCESS
        self.stats = stats
        self.pendencias = pendencias
        self.finished_at = now
        if self.started_at is not None:
            self.duration_ms = int((now - self.started_at).total_seconds() * 1000)
        self.save(
            update_fields=[
                "status",
                "stats",
                "pendencias",
                "finished_at",
                "duration_ms",
                "updated_at",
            ]
        )

    def mark_failed(self, *, error_message: str, error_traceback: str = "") -> None:
        """Transicao RUNNING -> FAILED. Grava error_message (trunc 500), traceback, finished_at."""
        now = timezone.now()
        self.status = self.Status.FAILED
        self.error_message = (error_message or "")[:500]
        self.error_traceback = error_traceback or ""
        self.finished_at = now
        if self.started_at is not None:
            self.duration_ms = int((now - self.started_at).total_seconds() * 1000)
        self.save(
            update_fields=[
                "status",
                "error_message",
                "error_traceback",
                "finished_at",
                "duration_ms",
                "updated_at",
            ]
        )

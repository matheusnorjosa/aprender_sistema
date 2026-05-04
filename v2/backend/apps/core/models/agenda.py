"""
AS v2 — Agenda Models

Models de agenda e bloqueios: AvailabilityBlock.
Clausulas Petreas: RD-02, RD-03, RD-06.
Type-checked with Pyright (strict mode).
"""

from __future__ import annotations

from typing import Any

from django.db import models
from django.utils import timezone


class AvailabilityBlock(models.Model):
    """
    Bloqueio de disponibilidade (RD-02, RD-03).

    - Total (T): bloqueia qualquer evento no intervalo
    - Parcial (P): bloqueia apenas sub-janela especificada

    IMPORTANTE: Bloqueios sao auto-aprovados ao criar (informacao factual).
    O formador/coordenador sabe quando esta indisponivel, nao requer autorizacao.

    RD-06: Armazena UTC, compara em America/Fortaleza.
    """

    TIPO_CHOICES = [
        ("T", "Total"),
        ("P", "Parcial"),
    ]

    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("aprovado", "Aprovado"),
        ("reprovado", "Reprovado"),
    ]

    usuario = models.ForeignKey(  # type: ignore[misc]
        "core.Usuario", on_delete=models.PROTECT, related_name="availability_blocks"
    )
    # PR 13 hardening RBAC (2026-05-04): separa `usuario` (target) de
    # `created_by` (delegate). Quando `created_by != usuario`, indica
    # bloqueio delegado por Asst Admin Controle / DAT / Superuser.
    # Registros antigos: NULL (owner é o próprio `usuario`).
    created_by = models.ForeignKey(  # type: ignore[misc]
        "core.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="availability_blocks_created",
        help_text=("Usuario que criou o bloqueio. Quando != usuario, indica " "delegação (PR 13 hardening RBAC)."),
    )
    inicio = models.DateTimeField(help_text="Inicio do bloqueio (UTC)")
    fim = models.DateTimeField(help_text="Fim do bloqueio (UTC)")
    tipo = models.CharField(max_length=1, choices=TIPO_CHOICES, default="T")
    motivo = models.CharField(max_length=255, blank=True, help_text="Motivo do bloqueio")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="aprovado")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_availability_block"
        verbose_name = "Bloqueio de Disponibilidade"
        verbose_name_plural = "Bloqueios de Disponibilidade"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["usuario", "inicio"]),
            models.Index(fields=["usuario", "fim"]),
            models.Index(fields=["status"]),
            # #929: Indice para conflict detection (RD-02/RD-03) com filtro de status
            models.Index(fields=["usuario", "status", "inicio"], name="idx_avblock_usr_st_ini"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(fim__gt=models.F("inicio")),
                name="availability_block_fim_gt_inicio",
            ),
            # Issue #136: Check constraint for status choices
            models.CheckConstraint(
                condition=models.Q(status__in=["pendente", "aprovado", "reprovado"]),
                name="availability_block_status_valid",
            ),
            # Issue #136: Check constraint for tipo choices
            models.CheckConstraint(
                condition=models.Q(tipo__in=["T", "P"]),
                name="availability_block_tipo_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.usuario.get_full_name()} - {self.get_tipo_display()} ({self.inicio.strftime('%d/%m/%Y %H:%M')} - {self.fim.strftime('%d/%m/%Y %H:%M')})"  # type: ignore[attr-defined]

    def save(self, *args: Any, **kwargs: Any) -> None:
        """
        Override save para auto-aprovar bloqueios.

        Bloqueios sao informacoes factuais (o formador/coordenador SABE quando esta indisponivel),
        portanto nao requerem aprovacao manual da Superintendencia.

        Diferente de Solicitacoes (PA-01 a PA-07), bloqueios sao sempre status='aprovado'.
        """
        # Auto-aprovar sempre (criacao ou atualizacao)
        if self.status == "pendente":
            self.status = "aprovado"

        super().save(*args, **kwargs)

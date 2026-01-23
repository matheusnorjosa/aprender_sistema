"""
AS v2 — Acompanhamento Model

Model para acompanhamentos vinculados a um PlanoFormacoes.
Cada plano pode ter ate 2 acompanhamentos (1o e 2o).

Type-checked with Pyright (strict mode).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
    from apps.core.models.plano_formacoes import PlanoFormacoes


class Acompanhamento(models.Model):
    """
    Acompanhamento vinculado a um PlanoFormacoes.

    Cada plano pode ter ate 2 acompanhamentos:
    - primeiro: 1o Acompanhamento
    - segundo: 2o Acompanhamento

    Ref: prompt-pagina-formacoes.md
    """

    class TipoAcompanhamento(models.TextChoices):
        PRIMEIRO = "primeiro", "1o Acompanhamento"
        SEGUNDO = "segundo", "2o Acompanhamento"

    # Relacionamento com plano
    plano: models.ForeignKey[PlanoFormacoes] = models.ForeignKey(  # type: ignore[assignment]
        "core.PlanoFormacoes",
        on_delete=models.CASCADE,
        related_name="acompanhamentos",
        verbose_name="Plano de Formacoes",
    )

    # Tipo do acompanhamento
    tipo = models.CharField(max_length=20, choices=TipoAcompanhamento.choices, verbose_name="Tipo de Acompanhamento")

    # Dados
    data_acompanhamento = models.DateField(null=True, blank=True, verbose_name="Data do Acompanhamento")
    realizado = models.BooleanField(default=False, verbose_name="Realizado")
    observacoes = models.TextField(blank=True, max_length=500, verbose_name="Observacoes")

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_acompanhamento"
        verbose_name = "Acompanhamento"
        verbose_name_plural = "Acompanhamentos"
        ordering = ["plano", "tipo"]
        indexes = [
            models.Index(fields=["plano", "tipo"]),
            models.Index(fields=["data_acompanhamento"]),
            models.Index(fields=["realizado"]),
        ]
        constraints = [models.UniqueConstraint(fields=["plano", "tipo"], name="unique_acompanhamento_plano_tipo")]

    def __str__(self) -> str:
        tipo_display = "1o" if self.tipo == self.TipoAcompanhamento.PRIMEIRO else "2o"
        data_str = self.data_acompanhamento.strftime("%d/%m/%Y") if self.data_acompanhamento else "-"
        return f"{tipo_display} Acomp. - {data_str}"

    @property
    def numero(self) -> int:
        """Retorna o numero do acompanhamento (1 ou 2)."""
        return 1 if self.tipo == self.TipoAcompanhamento.PRIMEIRO else 2

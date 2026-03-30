"""
AS v2 — Prova Model

Model para provas vinculadas a um PlanoFormacoes.
Cada plano pode ter ate 3 provas.

Type-checked with Pyright (strict mode).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
    from apps.core.models.plano_formacoes import PlanoFormacoes


class Prova(models.Model):
    """
    Prova vinculada a um PlanoFormacoes.

    Cada plano pode ter ate 3 provas, numeradas de 1 a 3.

    Ref: prompt-pagina-formacoes.md
    """

    # Relacionamento com plano
    plano: models.ForeignKey[PlanoFormacoes] = models.ForeignKey(  # type: ignore[assignment]
        "core.PlanoFormacoes", on_delete=models.CASCADE, related_name="provas", verbose_name="Plano de Formacoes"
    )

    # Numero da prova (1 a 3)
    numero_prova = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(3)],
        verbose_name="Numero da Prova",
        help_text="Numero sequencial da prova (1 a 3)",
    )

    # Dados
    data_prova = models.DateField(null=True, blank=True, verbose_name="Data da Prova")
    realizada = models.BooleanField(default=False, verbose_name="Realizada")
    observacoes = models.TextField(blank=True, max_length=500, verbose_name="Observacoes")

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_prova"
        verbose_name = "Prova"
        verbose_name_plural = "Provas"
        ordering = ["plano", "numero_prova"]
        indexes = [
            models.Index(fields=["plano", "numero_prova"]),
            models.Index(fields=["data_prova"]),
            models.Index(fields=["realizada"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["plano", "numero_prova"], name="unique_prova_plano_numero"),
            models.CheckConstraint(condition=models.Q(numero_prova__gte=1, numero_prova__lte=3), name="prova_numero_range"),
        ]

    def __str__(self) -> str:
        data_str = self.data_prova.strftime("%d/%m/%Y") if self.data_prova else "-"
        return f"P{self.numero_prova} - {data_str}"

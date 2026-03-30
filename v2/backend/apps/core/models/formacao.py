"""
AS v2 — Formacao Model

Model para formacoes individuais vinculadas a um PlanoFormacoes.
Cada plano pode ter ate 15 formacoes numeradas.

Type-checked with Pyright (strict mode).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
    from apps.core.models.plano_formacoes import PlanoFormacoes


class Formacao(models.Model):
    """
    Formacao individual vinculada a um PlanoFormacoes.

    Cada plano pode ter ate 15 formacoes, numeradas de 1 a 15.
    Formacoes sem data sao consideradas nao agendadas.

    Ref: prompt-pagina-formacoes.md
    """

    class StatusFormacao(models.TextChoices):
        AGENDADA = "agendada", "Agendada"
        REALIZADA = "realizada", "Realizada"
        CANCELADA = "cancelada", "Cancelada"
        REAGENDADA = "reagendada", "Reagendada"

    class Modalidade(models.TextChoices):
        PRESENCIAL = "presencial", "Presencial"
        ONLINE = "online", "Online"

    # Relacionamento com plano
    plano: models.ForeignKey[PlanoFormacoes] = models.ForeignKey(  # type: ignore[assignment]
        "core.PlanoFormacoes", on_delete=models.CASCADE, related_name="formacoes", verbose_name="Plano de Formacoes"
    )

    # Numero da formacao (1 a 15)
    numero_formacao = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(15)],
        verbose_name="Numero da Formacao",
        help_text="Numero sequencial da formacao (1 a 15)",
    )

    # Dados da formacao
    data_formacao = models.DateField(null=True, blank=True, verbose_name="Data da Formacao")
    carga_horaria = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("4.00"),
        verbose_name="Carga Horaria",
        help_text="Carga horaria em horas",
    )
    modalidade = models.CharField(
        max_length=20, choices=Modalidade.choices, default=Modalidade.PRESENCIAL, verbose_name="Modalidade"
    )

    # Detalhes opcionais
    horario_inicio = models.TimeField(null=True, blank=True, verbose_name="Horario de Inicio")
    horario_fim = models.TimeField(null=True, blank=True, verbose_name="Horario de Termino")
    local_formacao = models.CharField(
        max_length=200, blank=True, verbose_name="Local", help_text="Endereco ou link da reuniao online"
    )
    formador_nome = models.CharField(max_length=200, blank=True, verbose_name="Nome do Formador")

    # Status
    status = models.CharField(
        max_length=30, choices=StatusFormacao.choices, default=StatusFormacao.AGENDADA, verbose_name="Status"
    )
    realizada = models.BooleanField(default=False, verbose_name="Realizada")

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_formacao"
        verbose_name = "Formacao"
        verbose_name_plural = "Formacoes"
        ordering = ["plano", "numero_formacao"]
        indexes = [
            models.Index(fields=["plano", "numero_formacao"]),
            models.Index(fields=["data_formacao", "status"]),
            models.Index(fields=["realizada"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["plano", "numero_formacao"], name="unique_formacao_plano_numero"),
            models.CheckConstraint(
                condition=models.Q(numero_formacao__gte=1, numero_formacao__lte=15), name="formacao_numero_range"
            ),
        ]

    def __str__(self) -> str:
        data_str = self.data_formacao.strftime("%d/%m/%Y") if self.data_formacao else "-"
        return f"F{self.numero_formacao} - {data_str}"

    @property
    def duracao_horas(self) -> float | None:
        """Duracao da formacao em horas (se horarios definidos)."""
        if not self.horario_inicio or not self.horario_fim:
            return None
        from datetime import date, datetime

        inicio = datetime.combine(date.today(), self.horario_inicio)
        fim = datetime.combine(date.today(), self.horario_fim)
        delta = fim - inicio
        return delta.total_seconds() / 3600

    @property
    def modalidade_abrev(self) -> str:
        """Abreviacao da modalidade para exibicao em tabela."""
        if self.modalidade == self.Modalidade.ONLINE:
            return "Onl."
        return "Pres."

"""
AS v2 — Plano de Formacoes Model

Model para gestao do plano anual de formacoes por Municipio + Projeto.
Cada linha representa uma combinacao unica de municipio/projeto com ate 15 formacoes.

Type-checked with Pyright (strict mode).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import models
from django.db.models.functions import Coalesce
from django.utils import timezone

if TYPE_CHECKING:
    from apps.core.models.organizacao import Municipio, Projeto
    from apps.core.models.usuario import Usuario


class PlanoFormacoes(models.Model):
    """
    Plano anual de formacoes por Municipio + Projeto.

    Estrutura baseada na planilha original onde cada linha representa
    uma combinacao unica de municipio/projeto, contendo:
    - Ate 15 formacoes ao longo do ano
    - 2 acompanhamentos
    - 3 provas

    Ref: prompt-pagina-formacoes.md
    """

    # Relacionamentos principais (chave unica: municipio + projeto)
    municipio: models.ForeignKey[Municipio] = models.ForeignKey(  # type: ignore[assignment]
        "core.Municipio", on_delete=models.PROTECT, related_name="planos_formacoes", verbose_name="Municipio"
    )
    projeto: models.ForeignKey[Projeto] = models.ForeignKey(  # type: ignore[assignment]
        "core.Projeto", on_delete=models.PROTECT, related_name="planos_formacoes", verbose_name="Projeto"
    )
    # Coordenador = a PESSOA que coordenou (coluna Coordenador da Agenda), resolvido por CPF → Usuario
    # (#1849). NÃO é a lista de governança DATCoordenador (essa segue em DATAcao/DATFormacao). Read-only
    # na UI (o dado é autoritativo do import); o import seta via ORM.
    coordenador: models.ForeignKey[Usuario | None] = models.ForeignKey(  # type: ignore[assignment]
        "core.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="planos_coordenados",
        verbose_name="Coordenador Responsavel",
    )

    ano = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Ano",
        help_text="Ano do ciclo anual do plano (declarado no import).",
    )

    # Totais de carga horaria (calculados/manuais)
    ch_total = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="CH Total Formacoes",
        help_text="Soma das cargas horarias das formacoes",
    )
    ch_estudo = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="CH Estudo",
        help_text="Carga horaria adicional de estudo",
    )
    ch_anual = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="CH Anual",
        help_text="CH total anual (formacoes + estudo)",
    )

    # Observacoes
    observacoes = models.TextField(blank=True, max_length=2000, verbose_name="Observacoes")

    # Controle
    ativo = models.BooleanField(default=True)

    # Auditoria
    created_by: models.ForeignKey[Usuario] = models.ForeignKey(  # type: ignore[assignment]
        "core.Usuario", on_delete=models.PROTECT, related_name="planos_formacoes_criados", verbose_name="Criado por"
    )
    updated_by: models.ForeignKey[Usuario | None] = models.ForeignKey(  # type: ignore[assignment]
        "core.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="planos_formacoes_atualizados",
        verbose_name="Atualizado por",
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_plano_formacoes"
        verbose_name = "Plano de Formacoes"
        verbose_name_plural = "Planos de Formacoes"
        ordering = ["municipio__nome", "projeto__nome"]
        indexes = [
            models.Index(fields=["municipio", "projeto"]),
            models.Index(fields=["coordenador", "ativo"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["municipio", "projeto", "ano"],
                name="unique_plano_municipio_projeto_ano",
                nulls_distinct=False,
            )
        ]

    def __str__(self) -> str:
        base = f"{self.municipio} - {self.projeto}"
        return f"{base} ({self.ano})" if self.ano else base

    def recalcular_ch(self) -> None:
        """Recalcula CH total e anual baseado nas formacoes.

        Agrega no banco (nao itera `self.formacoes.all()` em Python) para nao ler um
        cache de prefetch obsoleto: `update_formacao` carrega o prefetch em get_object()
        ANTES de gravar a formacao, entao iterar o cache deixaria a CH um PATCH atrasada
        (M19-01). `.filter().aggregate()` sempre emite SQL fresco, imune ao cache.
        """
        from decimal import Decimal

        # Coalesce -> a soma ja vem 0.00 do proprio SQL quando nao ha formacao com data,
        # dispensando guard em Python; `total` permanece o resultado do ORM (nunca None).
        total = self.formacoes.filter(data_formacao__isnull=False).aggregate(
            total=Coalesce(
                models.Sum("carga_horaria"),
                Decimal("0.00"),
                output_field=models.DecimalField(max_digits=6, decimal_places=2),
            )
        )["total"]
        self.ch_total = total
        self.ch_anual = total + self.ch_estudo

    @property
    def total_formacoes(self) -> int:
        """Numero total de formacoes com data definida."""
        return self.formacoes.filter(data_formacao__isnull=False).count()

    @property
    def formacoes_realizadas(self) -> int:
        """Numero de formacoes realizadas."""
        return self.formacoes.filter(realizada=True).count()

    @property
    def taxa_realizacao(self) -> float:
        """Taxa de realizacao (realizadas/total * 100)."""
        total = self.total_formacoes
        if total == 0:
            return 0.0
        return (self.formacoes_realizadas / total) * 100

"""
AS v2 — DAT Compra Model

Model para gestao de compras e materiais do DAT.
Rastreia quantidade, uso e disponibilidade de produtos por municipio.

Type-checked with Pyright (strict mode).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
    from apps.core.models.compra import Produto
    from apps.core.models.organizacao import Municipio, Projeto
    from apps.core.models.usuario import Usuario


class DATCompra(models.Model):
    """
    Gestao de compras e materiais do DAT.

    Rastreia:
    - Quantidade adquirida vs utilizada
    - Valor unitario e total
    - Status de uso (disponivel, em_uso, esgotado)

    Ref: ComprasPage.jsx (materiais e estoque)
    """

    class StatusUso(models.TextChoices):
        DISPONIVEL = "disponivel", "Disponível"
        EM_USO = "em_uso", "Em Uso"
        ESGOTADO = "esgotado", "Esgotado"
        DEVOLVIDO = "devolvido", "Devolvido"

    # Relacionamentos principais
    municipio: models.ForeignKey[Municipio] = models.ForeignKey(  # type: ignore[assignment]
        "core.Municipio", on_delete=models.PROTECT, related_name="dat_compras", verbose_name="Município"
    )
    projeto: models.ForeignKey[Projeto] = models.ForeignKey(  # type: ignore[assignment]
        "core.Projeto", on_delete=models.PROTECT, related_name="dat_compras", verbose_name="Projeto"
    )
    produto: models.ForeignKey[Produto | None] = models.ForeignKey(  # type: ignore[assignment]
        "core.Produto",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dat_compras",
        verbose_name="Produto",
    )

    # Descrição (caso não use FK produto)
    descricao_produto = models.CharField(
        max_length=300,
        blank=True,
        verbose_name="Descrição do Produto",
        help_text="Use quando produto não está cadastrado",
    )

    # Quantidades
    quantidade = models.PositiveIntegerField(default=0, verbose_name="Quantidade Adquirida")
    quantidade_utilizada = models.PositiveIntegerField(default=0, verbose_name="Quantidade Utilizada")

    # Valores
    valor_unitario = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), verbose_name="Valor Unitário (R$)"
    )

    # Período
    ano_uso = models.PositiveSmallIntegerField(
        verbose_name="Ano de Uso", help_text="Ano em que o material será/foi utilizado"
    )
    data_compra = models.DateField(null=True, blank=True, verbose_name="Data da Compra")

    # Status
    status_uso = models.CharField(
        max_length=20, choices=StatusUso.choices, default=StatusUso.DISPONIVEL, verbose_name="Status de Uso"
    )
    ativo = models.BooleanField(default=True)

    # Observações
    observacoes = models.TextField(blank=True, max_length=1000, verbose_name="Observações")

    # Auditoria
    created_by: models.ForeignKey[Usuario] = models.ForeignKey(  # type: ignore[assignment]
        "core.Usuario", on_delete=models.PROTECT, related_name="dat_compras_criadas", verbose_name="Criado por"
    )
    updated_by: models.ForeignKey[Usuario | None] = models.ForeignKey(  # type: ignore[assignment]
        "core.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dat_compras_atualizadas",
        verbose_name="Atualizado por",
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_dat_compra"
        verbose_name = "Compra DAT"
        verbose_name_plural = "Compras DAT"
        ordering = ["-ano_uso", "municipio__nome"]
        indexes = [
            models.Index(fields=["municipio", "projeto"]),
            models.Index(fields=["ano_uso", "status_uso"]),
            models.Index(fields=["produto"]),
        ]

    def __str__(self) -> str:
        produto_nome = self.produto.nome if self.produto else self.descricao_produto
        return f"{produto_nome} - {self.municipio} ({self.ano_uso})"

    @property
    def disponivel(self) -> int:
        """Quantidade disponível (adquirida - utilizada)."""
        return max(0, self.quantidade - self.quantidade_utilizada)

    @property
    def valor_total(self) -> Decimal:
        """Valor total da compra (quantidade * valor_unitario)."""
        return self.valor_unitario * self.quantidade

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Auto-calcula status_uso baseado nas quantidades."""
        if self.quantidade_utilizada >= self.quantidade:
            self.status_uso = self.StatusUso.ESGOTADO
        elif self.quantidade_utilizada > 0:
            self.status_uso = self.StatusUso.EM_USO
        else:
            self.status_uso = self.StatusUso.DISPONIVEL
        super().save(*args, **kwargs)

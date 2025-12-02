"""
AS v2 — Compra Model

Model de compras de materiais/produtos.
Type-checked with Pyright (strict mode).
"""
from __future__ import annotations

from django.db import models
from django.utils import timezone


class Compra(models.Model):
    """
    Registro de compras de materiais/produtos para projetos.

    - Idempotencia: external_hash (SHA256 da linha normalizada)
    - Chave natural: (codigo + municipio + projeto + data)
    - Import: Suporta CSV/XLSX via import_compras service
    """

    codigo = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Codigo da compra (ex: COMP-001) - DEPRECATED: Use produto FK"
    )
    produto = models.ForeignKey(
        "core.Produto",
        on_delete=models.PROTECT,
        related_name="compras",
        null=True,  # Temporary: Migration 0035 will populate and make NOT NULL
        blank=True,
        help_text="Produto comprado (substitui codigo string)"
    )
    projeto = models.ForeignKey(
        "core.Projeto",
        on_delete=models.PROTECT,
        related_name="compras",
        help_text="Projeto vinculado a compra"
    )
    municipio = models.ForeignKey(
        "core.Municipio",
        on_delete=models.PROTECT,
        related_name="compras",
        help_text="Municipio destino da compra"
    )
    quantidade = models.IntegerField(
        help_text="Quantidade de itens comprados"
    )
    data = models.DateField(
        help_text="Data da compra"
    )
    uso = models.TextField(
        help_text="Uso/finalidade da compra (ex: Formacao inicial)"
    )
    external_hash = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Hash SHA256 para idempotencia de import"
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_compra"
        verbose_name = "Compra"
        verbose_name_plural = "Compras"
        ordering = ["-data", "-created_at"]
        indexes = [
            models.Index(fields=["codigo", "data"]),
            models.Index(fields=["projeto", "municipio"]),
            models.Index(fields=["external_hash"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["external_hash"],
                name="core_compra_external_hash_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.codigo} - {self.projeto.nome} ({self.data.strftime('%d/%m/%Y')})"

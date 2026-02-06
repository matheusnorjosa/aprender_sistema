"""
DATCompra Serializers - §10 Epic #459

Purchase/inventory tracking serializers.
Extracted from serializers/dat_module.py.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false

from __future__ import annotations

from rest_framework import serializers  # type: ignore[attr-defined]

from apps.core.models import DATCompra


class DATCompraSerializer(serializers.ModelSerializer["DATCompra"]):
    """Full serializer for DATCompra (CRUD)."""

    # FK names
    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)
    projeto_nome = serializers.CharField(source="projeto.nome", read_only=True)
    produto_nome = serializers.CharField(source="produto.nome", read_only=True, allow_null=True)

    # Computed
    disponivel = serializers.IntegerField(read_only=True)
    valor_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    # Audit
    created_by_nome = serializers.CharField(source="created_by.get_full_name", read_only=True)

    class Meta:
        model = DATCompra
        fields = [
            "id",
            # FKs
            "municipio",
            "municipio_nome",
            "projeto",
            "projeto_nome",
            "produto",
            "produto_nome",
            "descricao_produto",
            "tipo_compra",
            # Quantidades
            "quantidade",
            "quantidade_utilizada",
            "disponivel",
            # Valores
            "valor_unitario",
            "valor_total",
            # Período
            "ano_uso",
            "data_compra",
            # Status
            "status_uso",
            "ativo",
            "observacoes",
            # Audit
            "created_by",
            "created_by_nome",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "status_uso", "created_at", "updated_at"]


class DATCompraListSerializer(serializers.ModelSerializer["DATCompra"]):
    """List serializer for DATCompra (table view)."""

    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)
    projeto_nome = serializers.CharField(source="projeto.nome", read_only=True)
    produto_nome = serializers.CharField(source="produto.nome", read_only=True, allow_null=True)
    disponivel = serializers.IntegerField(read_only=True)
    valor_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = DATCompra
        fields = [
            "id",
            "municipio_nome",
            "projeto_nome",
            "produto_nome",
            "descricao_produto",
            "tipo_compra",
            "quantidade",
            "quantidade_utilizada",
            "disponivel",
            "valor_unitario",
            "valor_total",
            "ano_uso",
            "status_uso",
            "ativo",
        ]

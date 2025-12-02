"""
AS v2 — Compra Serializers

Serializers para Compra.
Type-checked with Pyright (strict mode).
"""
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false

from __future__ import annotations

from rest_framework import serializers  # type: ignore[attr-defined]

from apps.core.models import Compra


class CompraSerializer(serializers.ModelSerializer):
    """
    Serializer for Compra model (basic CRUD).
    Includes nested fields from Produto FK.
    """

    produto_codigo = serializers.CharField(source="produto.codigo", read_only=True, allow_null=True)
    produto_nome = serializers.CharField(source="produto.nome", read_only=True, allow_null=True)

    class Meta:
        model = Compra
        fields = [
            "id",
            "codigo",  # DEPRECATED: Use produto FK
            "produto",
            "produto_codigo",
            "produto_nome",
            "projeto",
            "municipio",
            "quantidade",
            "data",
            "uso",
            "external_hash",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_quantidade(self, value: int) -> int:
        """Quantidade não pode ser negativa."""
        if value < 0:
            raise serializers.ValidationError("Quantidade não pode ser negativa.")
        return value

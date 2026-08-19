"""
AS v2 — Compra Serializers

Serializers para Compra.
Type-checked with Pyright (strict mode).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false

from __future__ import annotations

from typing import Any

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

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # M15-03 (#1633): external_hash é a chave de idempotência de import — imutável após
        # a criação. No update (PATCH/PUT) fica read-only, para um CRUD não reescrever a
        # chave de uma linha importada (quebraria a idempotência de imports futuros). No
        # create segue gravável (compatível com o path de import).
        if self.instance is not None:
            self.fields["external_hash"].read_only = True

    def validate_quantidade(self, value: int) -> int:
        """M15-03 (#1633): compra de estoque zero/negativo é inválida — quantidade=0
        habilitava solicitação com estoque zerado (gate `.exists()` sem filtro de estoque)."""
        if value <= 0:
            raise serializers.ValidationError("Quantidade deve ser maior que zero.")
        return value

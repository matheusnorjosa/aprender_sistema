"""
AS v2 — Agenda Serializers

Serializers para AvailabilityBlock.
Clausulas Petreas: RD-02, RD-03.
Type-checked with Pyright (strict mode).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false

from __future__ import annotations

from typing import Any

from rest_framework import serializers  # type: ignore[attr-defined]

from apps.core.models import AvailabilityBlock


class AvailabilityBlockSerializer(serializers.ModelSerializer):
    """
    Serializer for AvailabilityBlock model.

    Status é auto-aprovado no ViewSet.perform_create().
    Usuario é preenchido automaticamente com request.user no ViewSet.
    """

    class Meta:
        model = AvailabilityBlock
        fields = [
            "id",
            "usuario",
            "inicio",
            "fim",
            "tipo",
            "motivo",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "usuario", "status", "created_at", "updated_at"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        Aceita updates parciais sem estourar KeyError.
        """
        instance = getattr(self, "instance", None)
        inicio = attrs.get("inicio", getattr(instance, "inicio", None))
        fim = attrs.get("fim", getattr(instance, "fim", None))

        if inicio is not None and fim is not None:
            if fim <= inicio:
                raise serializers.ValidationError({"fim": "O fim do bloqueio deve ser posterior ao início."})

        return super().validate(attrs)

"""
AS v2 — Auditoria Serializers

Serializers para AuditLog.
Clausula Petrea: PA-05 (registro de aprovacoes/reprovacoes).
Type-checked with Pyright (strict mode).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false

from __future__ import annotations

from rest_framework import serializers  # type: ignore[attr-defined]

from apps.core.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    """
    Serializer for AuditLog model (read-only).
    PA-05: Usado para rastrear aprovações/reprovações.
    """

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "usuario",
            "action",
            "details",
            "created_at",
        ]
        read_only_fields = ["id", "usuario", "action", "details", "created_at"]

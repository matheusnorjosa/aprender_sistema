"""
DATArea Serializers - §10 Epic #459

Reference table serializers for DATArea.
Extracted from serializers/dat_module.py.
"""
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false

from __future__ import annotations

from rest_framework import serializers  # type: ignore[attr-defined]

from apps.core.models import DATArea


class DATAreaSerializer(serializers.ModelSerializer["DATArea"]):
    """Full serializer for DATArea (reference table)."""

    class Meta:
        model = DATArea
        fields = ["id", "nome", "cor", "ativo", "ordem"]
        read_only_fields = ["id"]


class DATAreaOptionSerializer(serializers.ModelSerializer["DATArea"]):
    """Minimal serializer for DATArea (dropdowns)."""

    class Meta:
        model = DATArea
        fields = ["id", "nome", "cor"]

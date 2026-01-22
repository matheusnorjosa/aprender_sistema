"""
DATCoordenador Serializers - §10 Epic #459

Coordinator management serializers.
Extracted from serializers/dat_module.py.
"""
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false

from __future__ import annotations

from rest_framework import serializers  # type: ignore[attr-defined]

from apps.core.models import DATCoordenador


class DATCoordenadorSerializer(serializers.ModelSerializer["DATCoordenador"]):
    """Full serializer for DATCoordenador (CRUD)."""

    # Computed fields
    total_municipios = serializers.IntegerField(read_only=True)
    total_projetos = serializers.IntegerField(read_only=True)
    total_formacoes = serializers.IntegerField(read_only=True)

    # Audit names
    created_by_nome = serializers.CharField(
        source="created_by.get_full_name", read_only=True
    )

    class Meta:
        model = DATCoordenador
        fields = [
            "id",
            "nome",
            "email",
            "email_alternativo",
            "telefone",
            "telefone_alternativo",
            "area",
            "cargo",
            "ativo",
            "data_admissao",
            "foto_url",
            "observacoes",
            # Computed
            "total_municipios",
            "total_projetos",
            "total_formacoes",
            # Audit
            "created_by",
            "created_by_nome",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class DATCoordenadorOptionSerializer(serializers.ModelSerializer["DATCoordenador"]):
    """Minimal serializer for DATCoordenador (dropdowns)."""

    class Meta:
        model = DATCoordenador
        fields = ["id", "nome", "area", "ativo"]


class DATCoordenadorListSerializer(serializers.ModelSerializer["DATCoordenador"]):
    """List serializer for DATCoordenador (table view)."""

    total_municipios = serializers.IntegerField(read_only=True)
    total_projetos = serializers.IntegerField(read_only=True)
    total_formacoes = serializers.IntegerField(read_only=True)

    class Meta:
        model = DATCoordenador
        fields = [
            "id",
            "nome",
            "email",
            "telefone",
            "area",
            "cargo",
            "ativo",
            "foto_url",
            "total_municipios",
            "total_projetos",
            "total_formacoes",
        ]

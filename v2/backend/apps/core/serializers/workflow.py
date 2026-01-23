"""
AS v2 — Workflow Serializers

Serializers para AcaoControle, AcaoDAT, Deslocamento.
Type-checked with Pyright (strict mode).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false

from __future__ import annotations

from typing import Any

from rest_framework import serializers  # type: ignore[attr-defined]

from apps.core.models import AcaoControle, AcaoDAT, Deslocamento


class AcaoControleSerializer(serializers.ModelSerializer):
    """
    Serializer for AcaoControle model (read operations).
    Uses StringRelatedField for readable FK representation.
    """

    municipio = serializers.StringRelatedField()
    projeto = serializers.StringRelatedField()
    coordenador = serializers.StringRelatedField()

    class Meta:
        model = AcaoControle
        fields = [
            "id",
            "municipio",
            "projeto",
            "coordenador",
            "data_entrega",
            "data_carta",
            "contato_inicial",
            "data_reuniao",
            "observacao",
            "external_hash",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "external_hash", "created_at", "updated_at"]


class AcaoDATSerializer(serializers.ModelSerializer):
    """
    Serializer for AcaoDAT model (read operations).
    Uses StringRelatedField for readable FK representation.
    """

    municipio = serializers.StringRelatedField()
    projeto = serializers.StringRelatedField()
    responsavel = serializers.StringRelatedField()

    class Meta:
        model = AcaoDAT
        fields = [
            "id",
            "municipio",
            "projeto",
            "tipo_acao",
            "responsavel",
            "observacao",
            "data_registro",
            "external_hash",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "external_hash", "created_at", "updated_at"]


class AcaoDATCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for AcaoDAT model (write operations).
    Uses native ForeignKey IDs for creation.
    """

    class Meta:
        model = AcaoDAT
        fields = [
            "id",
            "municipio",
            "projeto",
            "tipo_acao",
            "responsavel",
            "observacao",
            "data_registro",
            "external_hash",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "external_hash", "created_at", "updated_at"]


class DeslocamentoSerializer(serializers.ModelSerializer):
    """
    Serializer for Deslocamento model (Issue #188).

    Provides CRUD operations for travel records between municipalities.

    Fields:
        - id, usuario, origem, destino, start_date, end_date, observacao
        - usuario_nome (read-only): Nome do usuário ou username
        - external_hash (read-only): ETL idempotence hash
        - created_at, updated_at (read-only)

    Validation:
        - start_date < end_date (error: "Data fim deve ser posterior à data início")
        - origem != destino (error: "Origem e destino devem ser diferentes")

    Permissions: IsControleOrDAT (Controle, DAT, Superintendência)
    """

    usuario_nome = serializers.SerializerMethodField()

    class Meta:
        model = Deslocamento
        fields = [
            "id",
            "usuario",
            "usuario_nome",
            "origem",
            "destino",
            "start_date",
            "end_date",
            "observacao",
            "external_hash",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "external_hash", "created_at", "updated_at"]

    def get_usuario_nome(self, obj: Deslocamento) -> str:
        """Retorna nome completo do usuário ou username como fallback."""
        if obj.usuario:
            full_name = obj.usuario.get_full_name()
            return full_name.strip() if full_name.strip() else obj.usuario.username
        return ""

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        Valida regras de negócio:
        - start_date < end_date
        - origem != destino

        Suporta PATCH parcial: se apenas um campo vier no payload,
        usa valor atual da instância.
        """
        instance = getattr(self, "instance", None)

        # Obter valores (novos ou existentes)
        start_date = attrs.get("start_date", getattr(instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(instance, "end_date", None))
        origem = attrs.get("origem", getattr(instance, "origem", None))
        destino = attrs.get("destino", getattr(instance, "destino", None))

        # Validação 1: start_date < end_date
        if start_date is not None and end_date is not None:
            if end_date <= start_date:
                raise serializers.ValidationError({"end_date": "Data fim deve ser posterior à data início"})

        # Validação 2: origem != destino
        if origem is not None and destino is not None:
            if origem.strip().lower() == destino.strip().lower():
                raise serializers.ValidationError({"destino": "Origem e destino devem ser diferentes"})

        return super().validate(attrs)

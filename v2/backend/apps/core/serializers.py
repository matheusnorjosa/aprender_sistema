"""
DRF Serializers for Core models
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import (
    AvailabilityBlock,
    Participation,
    Solicitacao,
    Compra,
    AuditLog,
    AcaoControle,
    AcaoDAT,
)


class UserSlimSerializer(serializers.ModelSerializer):
    """
    Serializer slim para Usuario (usado em aninhamentos).
    Retorna apenas id, nome e email.
    """

    class Meta:
        model = get_user_model()
        fields = ("id", "first_name", "last_name", "email")


class ParticipationNestedSerializer(serializers.ModelSerializer):
    """
    Serializer aninhado para Participation (read-only).
    Usado em SolicitacaoSerializer para expor participations.
    """

    usuario = UserSlimSerializer(read_only=True)
    email = serializers.SerializerMethodField()

    class Meta:
        model = Participation
        fields = ("usuario", "guest_email", "email", "role", "ch_horas", "observacao")

    def get_email(self, obj):
        user_email = getattr(getattr(obj, "usuario", None), "email", None)
        return user_email or getattr(obj, "guest_email", None)


class SolicitacaoSerializer(serializers.ModelSerializer):
    """
    Serializer for Solicitacao model.
    PA-01: Status sempre começa pendente.

    Inclui campo participations (read-only, aninhado) para expor
    múltiplos participantes com seus papéis.
    """

    participations = ParticipationNestedSerializer(
        many=True, read_only=True
    )

    class Meta:
        model = Solicitacao
        fields = [
            "id",
            "usuario",
            "municipio",
            "projeto",
            "tipo_evento",
            "inicio",
            "fim",
            "status",
            "observacoes",
            "external_event_id",
            "created_at",
            "updated_at",
            "participations",
        ]
        read_only_fields = [
            "id",
            "status",
            "external_event_id",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        """
        Permite PATCH parcial: se apenas um dos campos vier no payload,
        usa o valor atual da instância para validar o intervalo.
        """
        instance = getattr(self, "instance", None)
        inicio = attrs.get("inicio", getattr(instance, "inicio", None))
        fim = attrs.get("fim", getattr(instance, "fim", None))

        # só valida se os dois forem conhecidos
        if inicio is not None and fim is not None:
            if fim <= inicio:
                raise serializers.ValidationError(
                    {"fim": "O fim do evento deve ser posterior ao início."}
                )

        return super().validate(attrs)


class AvailabilityBlockSerializer(serializers.ModelSerializer):
    """
    Serializer for AvailabilityBlock model.
    PA-01: Status sempre começa pendente.
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

    def validate(self, attrs):
        """
        Aceita updates parciais sem estourar KeyError.
        """
        instance = getattr(self, "instance", None)
        inicio = attrs.get("inicio", getattr(instance, "inicio", None))
        fim = attrs.get("fim", getattr(instance, "fim", None))

        if inicio is not None and fim is not None:
            if fim <= inicio:
                raise serializers.ValidationError(
                    {"fim": "O fim do bloqueio deve ser posterior ao início."}
                )

        return super().validate(attrs)


class CompraSerializer(serializers.ModelSerializer):
    """
    Serializer for Compra model (basic CRUD).
    """

    class Meta:
        model = Compra
        fields = [
            "id",
            "codigo",
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

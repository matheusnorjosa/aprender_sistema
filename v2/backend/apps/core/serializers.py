"""
DRF Serializers for Core models
"""

from rest_framework import serializers

from .models import AvailabilityBlock, Solicitacao, Compra, AuditLog


class SolicitacaoSerializer(serializers.ModelSerializer):
    """
    Serializer for Solicitacao model.
    PA-01: Status sempre começa pendente.
    """

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

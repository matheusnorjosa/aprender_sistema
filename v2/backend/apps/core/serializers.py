"""
DRF Serializers for Core models
"""

from rest_framework import serializers

from .models import AvailabilityBlock, Solicitacao


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

    def validate(self, data):
        """
        Validação: fim > inicio
        """
        if data["fim"] <= data["inicio"]:
            raise serializers.ValidationError(
                {"fim": "O fim do evento deve ser posterior ao início."}
            )
        return data


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

    def validate(self, data):
        """
        Validação: fim > inicio
        """
        if data["fim"] <= data["inicio"]:
            raise serializers.ValidationError(
                {"fim": "O fim do bloqueio deve ser posterior ao início."}
            )
        return data

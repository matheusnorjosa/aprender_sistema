"""
Serializers para Ingestão de CSVs ETL

App: dat_ingest
Stack: Python 3.13 | Django 5.2 | DRF

Serializers para validação de uploads de arquivos CSV.
"""

from rest_framework import serializers


class AgendaUploadSerializer(serializers.Serializer):
    """
    Serializer para upload de arquivos de Agenda (DAT-P01).

    Campos:
        events: arquivo events.csv
        people: arquivo event_people.csv
    """

    events = serializers.FileField(
        required=True,
        help_text="Arquivo events.csv (eventos da agenda)",
    )
    people = serializers.FileField(
        required=True,
        help_text="Arquivo event_people.csv (pessoas por evento)",
    )

    def validate_events(self, value):
        """Valida que o arquivo events tem extensão .csv"""
        if not value.name.endswith(".csv"):
            raise serializers.ValidationError("Arquivo events deve ser um CSV (.csv)")
        return value

    def validate_people(self, value):
        """Valida que o arquivo people tem extensão .csv"""
        if not value.name.endswith(".csv"):
            raise serializers.ValidationError("Arquivo people deve ser um CSV (.csv)")
        return value


class DisponibilidadeUploadSerializer(serializers.Serializer):
    """
    Serializer para upload de arquivos de Disponibilidade (DAT-P02).

    Campos:
        blocks: arquivo disp_blocks.csv
        travels: arquivo disp_travels.csv
    """

    blocks = serializers.FileField(
        required=True,
        help_text="Arquivo disp_blocks.csv (bloqueios de disponibilidade)",
    )
    travels = serializers.FileField(
        required=True,
        help_text="Arquivo disp_travels.csv (deslocamentos)",
    )

    def validate_blocks(self, value):
        """Valida que o arquivo blocks tem extensão .csv"""
        if not value.name.endswith(".csv"):
            raise serializers.ValidationError("Arquivo blocks deve ser um CSV (.csv)")
        return value

    def validate_travels(self, value):
        """Valida que o arquivo travels tem extensão .csv"""
        if not value.name.endswith(".csv"):
            raise serializers.ValidationError("Arquivo travels deve ser um CSV (.csv)")
        return value


class ControleUploadSerializer(serializers.Serializer):
    """
    Serializer para upload de arquivo de Controle Unificado (DAT-P03).

    Campos:
        unificado: arquivo controle_unificado.csv
    """

    unificado = serializers.FileField(
        required=True,
        help_text="Arquivo controle_unificado.csv (dados consolidados de controle)",
    )

    def validate_unificado(self, value):
        """Valida que o arquivo unificado tem extensão .csv"""
        if not value.name.endswith(".csv"):
            raise serializers.ValidationError(
                "Arquivo unificado deve ser um CSV (.csv)"
            )
        return value

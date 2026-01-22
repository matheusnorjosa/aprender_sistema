"""
DATAcao Serializers - §10 Epic #459

Action/task tracking serializers.
Extracted from serializers/dat_module.py.
"""
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false

from __future__ import annotations

from rest_framework import serializers  # type: ignore[attr-defined]

from apps.core.models import DATAcao


class DATAcaoSerializer(serializers.ModelSerializer["DATAcao"]):
    """Full serializer for DATAcao (CRUD)."""

    # FK names
    municipio_nome = serializers.CharField(
        source="municipio.nome", read_only=True
    )
    projeto_nome = serializers.CharField(
        source="projeto.nome", read_only=True
    )
    coordenador_nome = serializers.CharField(
        source="coordenador.nome", read_only=True, allow_null=True
    )

    # Computed
    progresso = serializers.IntegerField(read_only=True)
    etapa_atual = serializers.CharField(read_only=True)

    # Audit
    created_by_nome = serializers.CharField(
        source="created_by.get_full_name", read_only=True
    )

    class Meta:
        model = DATAcao
        fields = [
            "id",
            # FKs
            "municipio",
            "municipio_nome",
            "projeto",
            "projeto_nome",
            "coordenador",
            "coordenador_nome",
            # Etapa Carta
            "status_carta",
            "data_carta",
            "observacao_carta",
            # Etapa Contato
            "status_contato",
            "data_contato",
            "observacao_contato",
            # Etapa Reunião
            "status_reuniao",
            "data_reuniao",
            "observacao_reuniao",
            # Etapa Entrega
            "status_entrega",
            "data_entrega",
            "observacao_entrega",
            # Status geral
            "ativo",
            "prioridade",
            # Computed
            "progresso",
            "etapa_atual",
            # Audit
            "created_by",
            "created_by_nome",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class DATAcaoListSerializer(serializers.ModelSerializer["DATAcao"]):
    """List serializer for DATAcao (table view)."""

    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)
    projeto_nome = serializers.CharField(source="projeto.nome", read_only=True)
    coordenador_nome = serializers.CharField(
        source="coordenador.nome", read_only=True, allow_null=True
    )
    progresso = serializers.IntegerField(read_only=True)
    etapa_atual = serializers.CharField(read_only=True)

    class Meta:
        model = DATAcao
        fields = [
            "id",
            "municipio",
            "municipio_nome",
            "projeto",
            "projeto_nome",
            "coordenador",
            "coordenador_nome",
            "status_carta",
            "status_contato",
            "status_reuniao",
            "status_entrega",
            "progresso",
            "etapa_atual",
            "prioridade",
            "ativo",
        ]

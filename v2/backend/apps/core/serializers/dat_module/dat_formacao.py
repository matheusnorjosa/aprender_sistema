"""
DATFormacao Serializers - §10 Epic #459

Training/formation event serializers.
Extracted from serializers/dat_module.py.
"""
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false

from __future__ import annotations

from rest_framework import serializers  # type: ignore[attr-defined]

from apps.core.models import DATFormacao


class DATFormacaoSerializer(serializers.ModelSerializer["DATFormacao"]):
    """Full serializer for DATFormacao (CRUD)."""

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
    duracao_horas = serializers.FloatField(read_only=True)
    taxa_presenca = serializers.FloatField(read_only=True)
    documentacao_completa = serializers.BooleanField(read_only=True)

    # Audit
    created_by_nome = serializers.CharField(
        source="created_by.get_full_name", read_only=True
    )

    class Meta:
        model = DATFormacao
        fields = [
            "id",
            # FKs
            "municipio",
            "municipio_nome",
            "projeto",
            "projeto_nome",
            "coordenador",
            "coordenador_nome",
            # Identificação
            "titulo",
            "descricao",
            # Agendamento
            "data_formacao",
            "horario_inicio",
            "horario_fim",
            "modalidade",
            "local",
            # Participantes
            "quantidade_prevista",
            "quantidade_confirmada",
            "quantidade_presente",
            # Status
            "status",
            "motivo_cancelamento",
            # Documentação
            "material_preparado",
            "lista_presenca_enviada",
            "relatorio_enviado",
            "fotos_enviadas",
            # Links
            "link_material",
            "link_lista_presenca",
            "link_relatorio",
            "link_fotos",
            # Observações
            "observacoes",
            "ativo",
            # Computed
            "duracao_horas",
            "taxa_presenca",
            "documentacao_completa",
            # Audit
            "created_by",
            "created_by_nome",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class DATFormacaoListSerializer(serializers.ModelSerializer["DATFormacao"]):
    """List serializer for DATFormacao (table view)."""

    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)
    projeto_nome = serializers.CharField(source="projeto.nome", read_only=True)
    coordenador_nome = serializers.CharField(
        source="coordenador.nome", read_only=True, allow_null=True
    )
    duracao_horas = serializers.FloatField(read_only=True)
    taxa_presenca = serializers.FloatField(read_only=True)
    documentacao_completa = serializers.BooleanField(read_only=True)

    class Meta:
        model = DATFormacao
        fields = [
            "id",
            "titulo",
            "municipio_nome",
            "projeto_nome",
            "coordenador_nome",
            "data_formacao",
            "horario_inicio",
            "horario_fim",
            "modalidade",
            "status",
            "quantidade_prevista",
            "quantidade_presente",
            "duracao_horas",
            "taxa_presenca",
            "documentacao_completa",
            "ativo",
        ]


class DATFormacaoCalendarioSerializer(serializers.ModelSerializer["DATFormacao"]):
    """Calendar serializer for DATFormacao (calendar view)."""

    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)
    projeto_nome = serializers.CharField(source="projeto.nome", read_only=True)

    class Meta:
        model = DATFormacao
        fields = [
            "id",
            "titulo",
            "municipio_nome",
            "projeto_nome",
            "data_formacao",
            "horario_inicio",
            "horario_fim",
            "modalidade",
            "status",
            "local",
        ]

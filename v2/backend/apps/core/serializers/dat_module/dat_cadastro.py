"""
DATCadastro Serializers - §10 Epic #459

Registration/onboarding workflow serializers.
Extracted from serializers/dat_module.py.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false

from __future__ import annotations

from rest_framework import serializers  # type: ignore[attr-defined]

from apps.core.models import DATCadastro


class DATCadastroSerializer(serializers.ModelSerializer["DATCadastro"]):
    """Full serializer for DATCadastro (CRUD)."""

    # FK names
    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)
    projeto_geral_nome = serializers.CharField(source="projeto_geral.nome", read_only=True)

    # Computed
    progresso = serializers.IntegerField(read_only=True)
    progresso_formar = serializers.IntegerField(read_only=True)
    progresso_avaliar = serializers.IntegerField(read_only=True)

    # Audit
    created_by_nome = serializers.CharField(source="created_by.get_full_name", read_only=True)

    class Meta:
        model = DATCadastro
        fields = [
            "id",
            # FKs
            "municipio",
            "municipio_nome",
            "projeto_geral",
            "projeto_geral_nome",
            "plataforma",
            # FORMAR workflow
            "status_criacao_curso",
            "data_criacao_curso",
            "status_chaves",
            "data_chaves",
            "quantidade_chaves",
            "status_instrucoes",
            "data_instrucoes",
            "status_envio",
            "data_envio",
            # AVALIAR workflow
            "status_recebidos",
            "data_recebidos",
            "quantidade_recebidos",
            "status_validados",
            "data_validados",
            "quantidade_validados",
            "status_importados",
            "data_importados",
            "quantidade_importados",
            # Status geral
            "ativo",
            "observacoes",
            # Computed
            "progresso",
            "progresso_formar",
            "progresso_avaliar",
            # Audit
            "created_by",
            "created_by_nome",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class DATCadastroListSerializer(serializers.ModelSerializer["DATCadastro"]):
    """List serializer for DATCadastro (table view)."""

    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)
    projeto_geral_nome = serializers.CharField(source="projeto_geral.nome", read_only=True)
    progresso = serializers.IntegerField(read_only=True)

    class Meta:
        model = DATCadastro
        fields = [
            "id",
            "municipio_nome",
            "projeto_geral_nome",
            "plataforma",
            # Quick status view
            "status_criacao_curso",
            "status_chaves",
            "status_instrucoes",
            "status_envio",
            "status_recebidos",
            "status_validados",
            "status_importados",
            "progresso",
            "ativo",
        ]

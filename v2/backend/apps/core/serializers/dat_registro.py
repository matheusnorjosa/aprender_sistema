"""
AS v2 — DATRegistro Serializers

Serializers para modelo DATRegistro (acompanhamento de turmas).
Type-checked with Pyright (strict mode).

Ref: v2/docs/SPEC_DAT_REGISTROS.md
"""
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false, reportUnknownArgumentType=false

from __future__ import annotations

from typing import Any

from rest_framework import serializers  # type: ignore[attr-defined]

from apps.core.models import DATRegistro


class DATRegistroListSerializer(serializers.ModelSerializer["DATRegistro"]):
    """
    Serializer for listing DATRegistro records.

    Optimized for table view with nested fields.
    """

    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)
    municipio_uf = serializers.CharField(source="municipio.uf", read_only=True)
    projeto_geral_nome = serializers.CharField(source="projeto_geral.nome", read_only=True)
    projeto_nome = serializers.CharField(source="projeto.nome", read_only=True)
    created_by_nome = serializers.CharField(source="created_by.get_full_name", read_only=True)
    status_geral = serializers.CharField(read_only=True)
    turma_formar_url = serializers.CharField(read_only=True)

    class Meta:
        model = DATRegistro
        fields = [
            "id",
            # Dados Básicos
            "municipio",
            "municipio_nome",
            "municipio_uf",
            "projeto_geral",
            "projeto_geral_nome",
            "projeto",
            "projeto_nome",
            "aluno_qtde",
            "professor_qtde",
            # FORMAR
            "reuniao_dat",
            "turma_formar_id",
            "turma_formar_status",
            "turma_formar_url",
            "nr_codigos",
            "chaves_inscricao_status",
            "chaves_inscricao_data",
            "instrucoes_status",
            "instrucoes_data",
            "envio_codigos_status",
            "envio_codigos_data",
            "obs_formar",
            # AVALIAR
            "usa_avaliar",
            "alunos_recebidos_status",
            "alunos_recebidos_datas",
            "alunos_validados_status",
            "alunos_validados_datas",
            "alunos_importados_status",
            "alunos_importados_datas",
            "obs_avaliar",
            # Status
            "status_geral",
            # Auditoria
            "created_by",
            "created_by_nome",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "nr_codigos",
            "usa_avaliar",
            "status_geral",
            "turma_formar_url",
            "created_at",
            "updated_at",
        ]


class DATRegistroCreateSerializer(serializers.ModelSerializer["DATRegistro"]):
    """
    Serializer for creating DATRegistro records.

    Handles validation and auto-sets created_by from request.user.
    """

    class Meta:
        model = DATRegistro
        fields = [
            # ID (returned after create)
            "id",
            # Dados Básicos (required)
            "municipio",
            "projeto_geral",
            "projeto",
            "aluno_qtde",
            "professor_qtde",
            # FORMAR (optional on create)
            "reuniao_dat",
            "turma_formar_id",
            "turma_formar_status",
            "chaves_inscricao_status",
            "chaves_inscricao_data",
            "instrucoes_status",
            "instrucoes_data",
            "envio_codigos_status",
            "envio_codigos_data",
            "obs_formar",
            # AVALIAR (optional on create)
            "alunos_recebidos_status",
            "alunos_recebidos_datas",
            "alunos_validados_status",
            "alunos_validados_datas",
            "alunos_importados_status",
            "alunos_importados_datas",
            "obs_avaliar",
            # ETL
            "external_hash",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        Validate that projeto belongs to projeto_geral.

        Also validates that professor_qtde is provided for por_professor calculation.
        """
        projeto_geral = attrs.get("projeto_geral")
        projeto = attrs.get("projeto")

        # Check projeto belongs to projeto_geral (if projeto has projeto_geral set)
        if projeto and projeto.projeto_geral and projeto_geral:
            if projeto.projeto_geral_id != projeto_geral.id:
                raise serializers.ValidationError({
                    "projeto": f"Projeto '{projeto.nome}' não pertence ao Projeto Geral '{projeto_geral.nome}'."
                })

        # Check professor_qtde for por_professor calculation
        if projeto_geral and projeto_geral.tipo_calculo_codigos == "por_professor":
            if not attrs.get("professor_qtde"):
                raise serializers.ValidationError({
                    "professor_qtde": "Quantidade de professores é obrigatória para projetos com cálculo por professor."
                })

        return attrs

    def create(self, validated_data: dict[str, Any]) -> DATRegistro:
        """Create DATRegistro with created_by from request."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["created_by"] = request.user
        return super().create(validated_data)


class DATRegistroUpdateSerializer(serializers.ModelSerializer["DATRegistro"]):
    """
    Serializer for updating DATRegistro records.

    Excludes municipio/projeto (immutable after creation).
    """

    class Meta:
        model = DATRegistro
        fields = [
            # Dados Básicos (editable)
            "aluno_qtde",
            "professor_qtde",
            # FORMAR
            "reuniao_dat",
            "turma_formar_id",
            "turma_formar_status",
            "chaves_inscricao_status",
            "chaves_inscricao_data",
            "instrucoes_status",
            "instrucoes_data",
            "envio_codigos_status",
            "envio_codigos_data",
            "obs_formar",
            # AVALIAR
            "alunos_recebidos_status",
            "alunos_recebidos_datas",
            "alunos_validados_status",
            "alunos_validados_datas",
            "alunos_importados_status",
            "alunos_importados_datas",
            "obs_avaliar",
        ]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Validate professor_qtde for por_professor calculation."""
        instance = self.instance
        if instance and instance.projeto_geral:
            if instance.projeto_geral.tipo_calculo_codigos == "por_professor":
                professor_qtde = attrs.get("professor_qtde", instance.professor_qtde)
                if not professor_qtde:
                    raise serializers.ValidationError({
                        "professor_qtde": "Quantidade de professores é obrigatória para projetos com cálculo por professor."
                    })
        return attrs

    def update(self, instance: DATRegistro, validated_data: dict[str, Any]) -> DATRegistro:
        """Update DATRegistro with updated_by from request."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["updated_by"] = request.user
        return super().update(instance, validated_data)


class DATRegistroDetailSerializer(DATRegistroListSerializer):
    """
    Full serializer for DATRegistro detail view.

    Includes all fields from list plus additional nested data.
    """

    updated_by_nome = serializers.CharField(
        source="updated_by.get_full_name", read_only=True, allow_null=True
    )

    class Meta(DATRegistroListSerializer.Meta):
        fields = DATRegistroListSerializer.Meta.fields + [
            "updated_by",
            "updated_by_nome",
            "external_hash",
        ]

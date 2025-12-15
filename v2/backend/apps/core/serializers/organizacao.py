"""
AS v2 — Organizacao Serializers

Serializers para Municipio, ProjetoGeral, Projeto, Gerencia, TipoEvento, Produto.
Type-checked with Pyright (strict mode).
"""
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false

from __future__ import annotations

from rest_framework import serializers  # type: ignore[attr-defined]

from apps.core.models import Gerencia, Municipio, Produto, Projeto, ProjetoGeral, TipoEvento


class MunicipioSerializer(serializers.ModelSerializer):
    """
    Full serializer for Municipio model (Admin CRUD).
    """

    class Meta:
        model = Municipio
        fields = ["id", "nome", "uf", "ibge_code", "ativo"]
        read_only_fields = ["id"]


class MunicipioOptionSerializer(serializers.ModelSerializer):
    """
    Minimal serializer for Municipio (dropdowns/selects).
    """

    class Meta:
        model = Municipio
        fields = ["id", "nome", "uf"]


class ProjetoGeralSerializer(serializers.ModelSerializer["ProjetoGeral"]):
    """
    Full serializer for ProjetoGeral model (Admin CRUD).

    Ref: SPEC_DAT_REGISTROS.md seção 2.1
    """

    projetos_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = ProjetoGeral
        fields = [
            "id",
            "nome",
            "usa_avaliar",
            "tipo_calculo_codigos",
            "divisor_aluno",
            "multiplicador_professor",
            "ativo",
            "descricao",
            "projetos_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class ProjetoGeralOptionSerializer(serializers.ModelSerializer):
    """
    Minimal serializer for ProjetoGeral (dropdowns/selects).
    """

    class Meta:
        model = ProjetoGeral
        fields = ["id", "nome", "usa_avaliar", "tipo_calculo_codigos"]


class ProjetoSerializer(serializers.ModelSerializer):
    """
    Full serializer for Projeto model (Admin CRUD).
    """

    gerencia_nome = serializers.CharField(
        source="gerencia.nome_setor", read_only=True, allow_null=True
    )
    setor = serializers.SerializerMethodField()
    projeto_geral_nome = serializers.CharField(
        source="projeto_geral.nome", read_only=True, allow_null=True
    )

    def get_setor(self, obj: Projeto) -> str:
        """Retorna nome do setor (derivado de gerencia)."""
        return obj.gerencia.nome_setor if obj.gerencia else ""

    class Meta:
        model = Projeto
        fields = [
            "id",
            "nome",
            "codigo",
            "fluxo",
            "ativo",
            "gerencia",
            "gerencia_nome",
            "projeto_geral",
            "projeto_geral_nome",
            "setor",
            "is_test",
        ]
        read_only_fields = ["id"]


class ProjetoOptionSerializer(serializers.ModelSerializer):
    """
    Minimal serializer for Projeto (dropdowns/selects).
    """

    class Meta:
        model = Projeto
        fields = ["id", "nome", "codigo"]


class GerenciaSerializer(serializers.ModelSerializer["Gerencia"]):
    """
    Serializer para modelo Gerencia.

    Fields:
        - id, nome, nome_setor, gerente (nested), ativo
        - projetos_count (annotated, read-only)
    """

    gerente_nome = serializers.CharField(
        source="gerente.get_full_name", read_only=True, allow_null=True
    )
    projetos_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:  # type: ignore[misc]
        model = Gerencia
        fields = [
            "id",
            "nome",
            "nome_setor",
            "gerente",
            "gerente_nome",
            "ativo",
            "descricao",
            "projetos_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class TipoEventoOptionSerializer(serializers.ModelSerializer):
    """
    Minimal serializer for TipoEvento (dropdowns/selects).
    """

    class Meta:
        model = TipoEvento
        fields = ["id", "nome"]


class ProdutoSerializer(serializers.ModelSerializer["Produto"]):
    """
    Serializer para modelo Produto.
    """

    projeto_nome = serializers.CharField(source="projeto.nome", read_only=True)

    class Meta:
        model = Produto
        fields = [
            "id",
            "codigo",
            "nome",
            "descricao",
            "projeto",
            "projeto_nome",
            "ativo",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

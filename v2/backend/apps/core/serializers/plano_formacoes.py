"""
AS v2 — Plano Formacoes Serializers

Serializers para PlanoFormacoes, Formacao, Acompanhamento, Prova.

Type-checked with Pyright (strict mode).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false, reportUnknownArgumentType=false

from __future__ import annotations

from decimal import Decimal
from typing import Any

from rest_framework import serializers  # type: ignore[attr-defined]

from apps.core.models import (
    Acompanhamento,
    Formacao,
    PlanoFormacoes,
    Prova,
)

# ============================================================
# Nested Serializers (for inline display)
# ============================================================


class FormacaoNestedSerializer(serializers.ModelSerializer["Formacao"]):
    """Serializer inline para formacoes no plano."""

    modalidade_abrev = serializers.CharField(read_only=True)

    class Meta:
        model = Formacao
        fields = [
            "id",
            "numero_formacao",
            "data_formacao",
            "carga_horaria",
            "modalidade",
            "modalidade_abrev",
            "horario_inicio",
            "horario_fim",
            "local_formacao",
            "formador_nome",
            "status",
            "realizada",
        ]
        read_only_fields = ["id", "modalidade_abrev"]


class AcompanhamentoNestedSerializer(serializers.ModelSerializer["Acompanhamento"]):
    """Serializer inline para acompanhamentos no plano."""

    numero = serializers.IntegerField(read_only=True)

    class Meta:
        model = Acompanhamento
        fields = [
            "id",
            "tipo",
            "numero",
            "data_acompanhamento",
            "realizado",
            "observacoes",
        ]
        read_only_fields = ["id", "numero"]


class ProvaNestedSerializer(serializers.ModelSerializer["Prova"]):
    """Serializer inline para provas no plano."""

    class Meta:
        model = Prova
        fields = [
            "id",
            "numero_prova",
            "data_prova",
            "realizada",
            "observacoes",
        ]
        read_only_fields = ["id"]


# ============================================================
# PlanoFormacoes Serializers
# ============================================================


class PlanoFormacoesSerializer(serializers.ModelSerializer["PlanoFormacoes"]):
    """Full serializer for PlanoFormacoes (CRUD detail view)."""

    # Nested relationships
    formacoes = FormacaoNestedSerializer(many=True, read_only=True)
    acompanhamentos = AcompanhamentoNestedSerializer(many=True, read_only=True)
    provas = ProvaNestedSerializer(many=True, read_only=True)

    # FK names
    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)
    municipio_uf = serializers.CharField(source="municipio.uf", read_only=True)
    projeto_nome = serializers.CharField(source="projeto.nome", read_only=True)
    coordenador_nome = serializers.CharField(source="coordenador.nome", read_only=True, allow_null=True)

    # Computed
    total_formacoes = serializers.IntegerField(read_only=True)
    formacoes_realizadas = serializers.IntegerField(read_only=True)
    taxa_realizacao = serializers.FloatField(read_only=True)

    # Audit
    created_by_nome = serializers.CharField(source="created_by.get_full_name", read_only=True)

    class Meta:
        model = PlanoFormacoes
        fields = [
            "id",
            "municipio",
            "municipio_nome",
            "municipio_uf",
            "projeto",
            "projeto_nome",
            "coordenador",
            "coordenador_nome",
            "ch_total",
            "ch_estudo",
            "ch_anual",
            "observacoes",
            "ativo",
            # Nested
            "formacoes",
            "acompanhamentos",
            "provas",
            # Computed
            "total_formacoes",
            "formacoes_realizadas",
            "taxa_realizacao",
            # Audit
            "created_by",
            "created_by_nome",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "created_at",
            "updated_at",
            "municipio_nome",
            "municipio_uf",
            "projeto_nome",
            "coordenador_nome",
        ]

    def create(self, validated_data: dict[str, Any]) -> PlanoFormacoes:
        """Create plano and initialize empty formacoes, acompanhamentos, provas."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["created_by"] = request.user

        plano = super().create(validated_data)

        # Create 15 empty formacoes
        for i in range(1, 16):
            Formacao.objects.create(
                plano=plano,
                numero_formacao=i,
                carga_horaria=Decimal("4.00"),
            )

        # Create 2 acompanhamentos
        for tipo in [Acompanhamento.TipoAcompanhamento.PRIMEIRO, Acompanhamento.TipoAcompanhamento.SEGUNDO]:
            Acompanhamento.objects.create(plano=plano, tipo=tipo)

        # Create 3 provas
        for i in range(1, 4):
            Prova.objects.create(plano=plano, numero_prova=i)

        return plano


class PlanoFormacoesListSerializer(serializers.ModelSerializer["PlanoFormacoes"]):
    """List serializer for PlanoFormacoes (table view with expanded formacoes)."""

    # FK names
    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)
    municipio_uf = serializers.CharField(source="municipio.uf", read_only=True)
    projeto_nome = serializers.CharField(source="projeto.nome", read_only=True)
    coordenador_nome = serializers.CharField(source="coordenador.nome", read_only=True, allow_null=True)

    # Formacoes expandidas para exibicao em tabela (F1-F15)
    formacoes_list = serializers.SerializerMethodField()

    # Acompanhamentos e provas expandidos
    acompanhamentos_list = serializers.SerializerMethodField()
    provas_list = serializers.SerializerMethodField()

    # Computed
    total_formacoes = serializers.IntegerField(read_only=True)
    formacoes_realizadas = serializers.IntegerField(read_only=True)

    class Meta:
        model = PlanoFormacoes
        fields = [
            "id",
            "municipio",
            "municipio_nome",
            "municipio_uf",
            "projeto",
            "projeto_nome",
            "coordenador",
            "coordenador_nome",
            "ch_total",
            "ch_anual",
            "ativo",
            # Expanded arrays
            "formacoes_list",
            "acompanhamentos_list",
            "provas_list",
            # Computed
            "total_formacoes",
            "formacoes_realizadas",
        ]

    def get_formacoes_list(self, obj: PlanoFormacoes) -> list[dict[str, Any]]:
        """Return formacoes as ordered list for table display."""
        formacoes = obj.formacoes.all().order_by("numero_formacao")
        return [
            {
                "id": f.id,
                "numero": f.numero_formacao,
                "data": f.data_formacao.isoformat() if f.data_formacao else None,
                "ch": float(f.carga_horaria),
                "modalidade": f.modalidade,
                "realizada": f.realizada,
            }
            for f in formacoes
        ]

    def get_acompanhamentos_list(self, obj: PlanoFormacoes) -> list[dict[str, Any]]:
        """Return acompanhamentos as ordered list."""
        acompanhamentos = obj.acompanhamentos.all().order_by("tipo")
        return [
            {
                "id": a.id,
                "tipo": a.tipo,
                "data": a.data_acompanhamento.isoformat() if a.data_acompanhamento else None,
                "realizado": a.realizado,
            }
            for a in acompanhamentos
        ]

    def get_provas_list(self, obj: PlanoFormacoes) -> list[dict[str, Any]]:
        """Return provas as ordered list."""
        provas = obj.provas.all().order_by("numero_prova")
        return [
            {
                "id": p.id,
                "numero": p.numero_prova,
                "data": p.data_prova.isoformat() if p.data_prova else None,
                "realizada": p.realizada,
            }
            for p in provas
        ]


class PlanoFormacoesOptionSerializer(serializers.ModelSerializer["PlanoFormacoes"]):
    """Minimal serializer for PlanoFormacoes (dropdowns)."""

    label = serializers.SerializerMethodField()

    class Meta:
        model = PlanoFormacoes
        fields = ["id", "label"]

    def get_label(self, obj: PlanoFormacoes) -> str:
        return f"{obj.municipio.nome} - {obj.projeto.nome}"


# ============================================================
# Individual CRUD Serializers
# ============================================================


class FormacaoSerializer(serializers.ModelSerializer["Formacao"]):
    """Serializer for Formacao individual CRUD."""

    plano_label = serializers.SerializerMethodField()
    modalidade_abrev = serializers.CharField(read_only=True)

    class Meta:
        model = Formacao
        fields = [
            "id",
            "plano",
            "plano_label",
            "numero_formacao",
            "data_formacao",
            "carga_horaria",
            "modalidade",
            "modalidade_abrev",
            "horario_inicio",
            "horario_fim",
            "local_formacao",
            "formador_nome",
            "status",
            "realizada",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "plano_label", "modalidade_abrev", "created_at", "updated_at"]

    def get_plano_label(self, obj: Formacao) -> str:
        return str(obj.plano)


class AcompanhamentoSerializer(serializers.ModelSerializer["Acompanhamento"]):
    """Serializer for Acompanhamento individual CRUD."""

    plano_label = serializers.SerializerMethodField()
    numero = serializers.IntegerField(read_only=True)

    class Meta:
        model = Acompanhamento
        fields = [
            "id",
            "plano",
            "plano_label",
            "tipo",
            "numero",
            "data_acompanhamento",
            "realizado",
            "observacoes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "plano_label", "numero", "created_at", "updated_at"]

    def get_plano_label(self, obj: Acompanhamento) -> str:
        return str(obj.plano)


class ProvaSerializer(serializers.ModelSerializer["Prova"]):
    """Serializer for Prova individual CRUD."""

    plano_label = serializers.SerializerMethodField()

    class Meta:
        model = Prova
        fields = [
            "id",
            "plano",
            "plano_label",
            "numero_prova",
            "data_prova",
            "realizada",
            "observacoes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "plano_label", "created_at", "updated_at"]

    def get_plano_label(self, obj: Prova) -> str:
        return str(obj.plano)

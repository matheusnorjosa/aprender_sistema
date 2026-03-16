"""
Serializers for Acoes/Notificacoes API endpoints (issue #872).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from rest_framework import serializers

from apps.core.models import AcaoInstancia, CicloAcoes, Municipio, NotificacaoInterna, Projeto


class CicloAcoesSerializer(serializers.ModelSerializer):
    projeto_id = serializers.PrimaryKeyRelatedField(
        source="projeto",
        queryset=Projeto.objects.all(),
        write_only=True,
    )
    municipio_id = serializers.PrimaryKeyRelatedField(
        source="municipio",
        queryset=Municipio.objects.all(),
        write_only=True,
    )
    projeto_nome = serializers.CharField(source="projeto.nome", read_only=True)
    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)

    class Meta:
        model = CicloAcoes
        fields = [
            "id",
            "projeto_id",
            "municipio_id",
            "projeto",
            "municipio",
            "projeto_nome",
            "municipio_nome",
            "semestre",
            "ano",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "projeto",
            "municipio",
            "projeto_nome",
            "municipio_nome",
            "status",
            "created_at",
            "updated_at",
        ]


class AcaoInstanciaSerializer(serializers.ModelSerializer):
    template_nome = serializers.CharField(source="template.nome", read_only=True)
    projeto_nome = serializers.CharField(source="ciclo.projeto.nome", read_only=True)
    municipio_nome = serializers.CharField(source="ciclo.municipio.nome", read_only=True)

    class Meta:
        model = AcaoInstancia
        fields = [
            "id",
            "ciclo",
            "ordem",
            "estado",
            "template",
            "template_nome",
            "projeto_nome",
            "municipio_nome",
            "data_ancora",
            "data_vencimento",
            "data_realizacao",
            "observacao_conclusao",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class RegistrarAncoraSerializer(serializers.Serializer):
    data_ancora = serializers.DateField()
    observacao = serializers.CharField(required=False, allow_blank=True, default="")


class ConcluirAcaoSerializer(serializers.Serializer):
    data_realizacao = serializers.DateField()
    observacao = serializers.CharField(required=True, allow_blank=False)


class NotificacaoInternaSerializer(serializers.ModelSerializer):
    acao_ordem = serializers.IntegerField(source="acao_instancia.ordem", read_only=True)
    acao_nome = serializers.CharField(source="acao_instancia.template.nome", read_only=True)

    class Meta:
        model = NotificacaoInterna
        fields = [
            "id",
            "acao_instancia",
            "acao_ordem",
            "acao_nome",
            "titulo",
            "mensagem",
            "tipo",
            "nivel",
            "prioridade",
            "fase_disparo",
            "referencia_data",
            "lida",
            "lida_em",
            "created_at",
        ]
        read_only_fields = fields

"""
AS v2 — DAT Module Serializers

Serializers para DATArea, DATCoordenador, DATAcao, DATCompra, DATCadastro, DATFormacao.

Type-checked with Pyright (strict mode).
"""
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false

from __future__ import annotations

from rest_framework import serializers  # type: ignore[attr-defined]

from apps.core.models import (
    DATAcao,
    DATArea,
    DATCadastro,
    DATCompra,
    DATCoordenador,
    DATFormacao,
)


# ============================================================
# DATArea Serializers
# ============================================================


class DATAreaSerializer(serializers.ModelSerializer["DATArea"]):
    """Full serializer for DATArea (reference table)."""

    class Meta:
        model = DATArea
        fields = ["id", "nome", "cor", "ativo", "ordem"]
        read_only_fields = ["id"]


class DATAreaOptionSerializer(serializers.ModelSerializer["DATArea"]):
    """Minimal serializer for DATArea (dropdowns)."""

    class Meta:
        model = DATArea
        fields = ["id", "nome", "cor"]


# ============================================================
# DATCoordenador Serializers
# ============================================================


class DATCoordenadorSerializer(serializers.ModelSerializer["DATCoordenador"]):
    """Full serializer for DATCoordenador (CRUD)."""

    # Computed fields
    total_municipios = serializers.IntegerField(read_only=True)
    total_projetos = serializers.IntegerField(read_only=True)
    total_formacoes = serializers.IntegerField(read_only=True)

    # Audit names
    created_by_nome = serializers.CharField(
        source="created_by.get_full_name", read_only=True
    )

    class Meta:
        model = DATCoordenador
        fields = [
            "id",
            "nome",
            "email",
            "email_alternativo",
            "telefone",
            "telefone_alternativo",
            "area",
            "cargo",
            "ativo",
            "data_admissao",
            "foto_url",
            "observacoes",
            # Computed
            "total_municipios",
            "total_projetos",
            "total_formacoes",
            # Audit
            "created_by",
            "created_by_nome",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class DATCoordenadorOptionSerializer(serializers.ModelSerializer["DATCoordenador"]):
    """Minimal serializer for DATCoordenador (dropdowns)."""

    class Meta:
        model = DATCoordenador
        fields = ["id", "nome", "area", "ativo"]


class DATCoordenadorListSerializer(serializers.ModelSerializer["DATCoordenador"]):
    """List serializer for DATCoordenador (table view)."""

    total_municipios = serializers.IntegerField(read_only=True)
    total_projetos = serializers.IntegerField(read_only=True)
    total_formacoes = serializers.IntegerField(read_only=True)

    class Meta:
        model = DATCoordenador
        fields = [
            "id",
            "nome",
            "email",
            "telefone",
            "area",
            "cargo",
            "ativo",
            "foto_url",
            "total_municipios",
            "total_projetos",
            "total_formacoes",
        ]


# ============================================================
# DATAcao Serializers
# ============================================================


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


# ============================================================
# DATCompra Serializers
# ============================================================


class DATCompraSerializer(serializers.ModelSerializer["DATCompra"]):
    """Full serializer for DATCompra (CRUD)."""

    # FK names
    municipio_nome = serializers.CharField(
        source="municipio.nome", read_only=True
    )
    projeto_nome = serializers.CharField(
        source="projeto.nome", read_only=True
    )
    produto_nome = serializers.CharField(
        source="produto.nome", read_only=True, allow_null=True
    )

    # Computed
    disponivel = serializers.IntegerField(read_only=True)
    valor_total = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    # Audit
    created_by_nome = serializers.CharField(
        source="created_by.get_full_name", read_only=True
    )

    class Meta:
        model = DATCompra
        fields = [
            "id",
            # FKs
            "municipio",
            "municipio_nome",
            "projeto",
            "projeto_nome",
            "produto",
            "produto_nome",
            "descricao_produto",
            # Quantidades
            "quantidade",
            "quantidade_utilizada",
            "disponivel",
            # Valores
            "valor_unitario",
            "valor_total",
            # Período
            "ano_uso",
            "data_compra",
            # Status
            "status_uso",
            "ativo",
            "observacoes",
            # Audit
            "created_by",
            "created_by_nome",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "status_uso", "created_at", "updated_at"]


class DATCompraListSerializer(serializers.ModelSerializer["DATCompra"]):
    """List serializer for DATCompra (table view)."""

    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)
    projeto_nome = serializers.CharField(source="projeto.nome", read_only=True)
    produto_nome = serializers.CharField(
        source="produto.nome", read_only=True, allow_null=True
    )
    disponivel = serializers.IntegerField(read_only=True)
    valor_total = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = DATCompra
        fields = [
            "id",
            "municipio_nome",
            "projeto_nome",
            "produto_nome",
            "descricao_produto",
            "quantidade",
            "quantidade_utilizada",
            "disponivel",
            "valor_unitario",
            "valor_total",
            "ano_uso",
            "status_uso",
            "ativo",
        ]


# ============================================================
# DATCadastro Serializers
# ============================================================


class DATCadastroSerializer(serializers.ModelSerializer["DATCadastro"]):
    """Full serializer for DATCadastro (CRUD)."""

    # FK names
    municipio_nome = serializers.CharField(
        source="municipio.nome", read_only=True
    )
    projeto_geral_nome = serializers.CharField(
        source="projeto_geral.nome", read_only=True
    )

    # Computed
    progresso = serializers.IntegerField(read_only=True)
    progresso_formar = serializers.IntegerField(read_only=True)
    progresso_avaliar = serializers.IntegerField(read_only=True)

    # Audit
    created_by_nome = serializers.CharField(
        source="created_by.get_full_name", read_only=True
    )

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


# ============================================================
# DATFormacao Serializers
# ============================================================


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

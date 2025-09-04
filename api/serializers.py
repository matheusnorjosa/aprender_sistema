"""
Django REST Framework serializers para o Aprender Sistema.
Serializa todos os modelos core para exposição via API.
"""

from django.contrib.auth import get_user_model

from rest_framework import serializers

from core.models import (
    Aprovacao,
    Deslocamento,
    DisponibilidadeFormadores,
    EventoGoogleCalendar,
    Formador,
    FormadoresSolicitacao,
    LogAuditoria,
    Municipio,
    Projeto,
    Solicitacao,
    TipoEvento,
)

User = get_user_model()


# =========================
# SERIALIZERS DE USUÁRIOS
# =========================


class UsuarioListSerializer(serializers.ModelSerializer):
    """Serializer básico para listagem de usuários"""

    role_names = serializers.ReadOnlyField()
    primary_role = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "date_joined",
            "role_names",
            "primary_role",
        ]
        read_only_fields = ["id", "date_joined"]


class UsuarioDetailSerializer(UsuarioListSerializer):
    """Serializer detalhado para usuário individual"""

    groups = serializers.StringRelatedField(many=True, read_only=True)

    class Meta(UsuarioListSerializer.Meta):
        fields = UsuarioListSerializer.Meta.fields + [
            "groups",
            "last_login",
            "is_staff",
        ]


# =========================
# SERIALIZERS DE REFERÊNCIA
# =========================


class ProjetoSerializer(serializers.ModelSerializer):
    """Serializer para projetos"""

    class Meta:
        model = Projeto
        fields = ["id", "nome", "descricao", "ativo", "vinculado_superintendencia"]
        read_only_fields = ["id"]


class MunicipioSerializer(serializers.ModelSerializer):
    """Serializer para municípios"""

    class Meta:
        model = Municipio
        fields = ["id", "nome", "uf", "regiao", "populacao"]
        read_only_fields = ["id"]


class TipoEventoSerializer(serializers.ModelSerializer):
    """Serializer para tipos de evento"""

    class Meta:
        model = TipoEvento
        fields = ["id", "nome", "descricao", "duracao", "online", "requer_deslocamento"]
        read_only_fields = ["id"]


# =========================
# SERIALIZERS DE FORMADORES
# =========================


class FormadorListSerializer(serializers.ModelSerializer):
    """Serializer básico para listagem de formadores"""

    areas_atuacao_display = serializers.CharField(
        source="get_areas_atuacao_display", read_only=True
    )

    class Meta:
        model = Formador
        fields = ["id", "nome", "email", "telefone", "areas_atuacao_display", "ativo"]
        read_only_fields = ["id"]


class FormadorDetailSerializer(FormadorListSerializer):
    """Serializer detalhado para formador individual"""

    municipios = MunicipioSerializer(many=True, read_only=True)
    tipos_evento = TipoEventoSerializer(many=True, read_only=True)

    class Meta(FormadorListSerializer.Meta):
        fields = FormadorListSerializer.Meta.fields + [
            "areas_atuacao",
            "observacoes",
            "data_cadastro",
            "municipios",
            "tipos_evento",
        ]


# =========================
# SERIALIZERS DE SOLICITAÇÕES
# =========================


class FormadoresSolicitacaoSerializer(serializers.ModelSerializer):
    """Serializer para relação formador-solicitação"""

    formador_nome = serializers.CharField(source="formador.nome", read_only=True)

    class Meta:
        model = FormadoresSolicitacao
        fields = ["formador", "formador_nome"]


class SolicitacaoListSerializer(serializers.ModelSerializer):
    """Serializer básico para listagem de solicitações"""

    projeto_nome = serializers.CharField(source="projeto.nome", read_only=True)
    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)
    tipo_evento_nome = serializers.CharField(source="tipo_evento.nome", read_only=True)
    usuario_solicitante_nome = serializers.CharField(
        source="usuario_solicitante.get_full_name", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Solicitacao
        fields = [
            "id",
            "titulo_evento",
            "data_inicio",
            "data_fim",
            "status",
            "status_display",
            "data_solicitacao",
            "projeto_nome",
            "municipio_nome",
            "tipo_evento_nome",
            "usuario_solicitante_nome",
        ]
        read_only_fields = ["id", "data_solicitacao", "usuario_solicitante"]


class SolicitacaoDetailSerializer(SolicitacaoListSerializer):
    """Serializer detalhado para solicitação individual"""

    projeto = ProjetoSerializer(read_only=True)
    municipio = MunicipioSerializer(read_only=True)
    tipo_evento = TipoEventoSerializer(read_only=True)
    usuario_solicitante = UsuarioListSerializer(read_only=True)
    usuario_aprovador = UsuarioListSerializer(read_only=True)
    formadores_detail = FormadoresSolicitacaoSerializer(
        source="formadoressolicitacao_set", many=True, read_only=True
    )

    class Meta(SolicitacaoListSerializer.Meta):
        fields = SolicitacaoListSerializer.Meta.fields + [
            "descricao_evento",
            "publico_alvo",
            "observacoes",
            "data_aprovacao_rejeicao",
            "justificativa_rejeicao",
            "projeto",
            "municipio",
            "tipo_evento",
            "usuario_solicitante",
            "usuario_aprovador",
            "formadores_detail",
        ]


class SolicitacaoCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer para criar/atualizar solicitações"""

    class Meta:
        model = Solicitacao
        fields = [
            "titulo_evento",
            "descricao_evento",
            "data_inicio",
            "data_fim",
            "projeto",
            "municipio",
            "tipo_evento",
            "publico_alvo",
            "observacoes",
        ]

    def validate(self, data):
        """Validações customizadas"""
        if data["data_fim"] <= data["data_inicio"]:
            raise serializers.ValidationError(
                "Data de fim deve ser posterior à data de início"
            )

        # Validar duração máxima (12 horas)
        duracao = data["data_fim"] - data["data_inicio"]
        if duracao.total_seconds() > 12 * 3600:
            raise serializers.ValidationError("Duração máxima de evento é 12 horas")

        return data


# =========================
# SERIALIZERS DE APROVAÇÕES
# =========================


class AprovacaoSerializer(serializers.ModelSerializer):
    """Serializer para aprovações"""

    solicitacao_titulo = serializers.CharField(
        source="solicitacao.titulo_evento", read_only=True
    )
    usuario_aprovador_nome = serializers.CharField(
        source="usuario_aprovador.get_full_name", read_only=True
    )
    status_display = serializers.CharField(
        source="get_status_decisao_display", read_only=True
    )

    class Meta:
        model = Aprovacao
        fields = [
            "id",
            "solicitacao",
            "solicitacao_titulo",
            "usuario_aprovador",
            "usuario_aprovador_nome",
            "status_decisao",
            "status_display",
            "justificativa",
            "data_decisao",
        ]
        read_only_fields = ["id", "data_decisao"]


# =========================
# SERIALIZERS DE EVENTOS GOOGLE
# =========================


class EventoGoogleCalendarSerializer(serializers.ModelSerializer):
    """Serializer para eventos do Google Calendar"""

    solicitacao_titulo = serializers.CharField(
        source="solicitacao.titulo_evento", read_only=True
    )

    class Meta:
        model = EventoGoogleCalendar
        fields = [
            "id",
            "google_event_id",
            "solicitacao",
            "solicitacao_titulo",
            "titulo",
            "data_inicio_google",
            "data_fim_google",
            "link_meet",
            "data_criacao",
            "data_atualizacao",
        ]
        read_only_fields = ["id", "data_criacao", "data_atualizacao"]


# =========================
# SERIALIZERS DE DISPONIBILIDADE
# =========================


class DisponibilidadeFormadoresSerializer(serializers.ModelSerializer):
    """Serializer para disponibilidade de formadores"""

    formador_nome = serializers.CharField(source="formador.nome", read_only=True)
    codigo_display = serializers.CharField(source="get_codigo_display", read_only=True)

    class Meta:
        model = DisponibilidadeFormadores
        fields = [
            "id",
            "formador",
            "formador_nome",
            "data",
            "codigo",
            "codigo_display",
            "observacoes",
            "data_atualizacao",
        ]
        read_only_fields = ["id", "data_atualizacao"]


# =========================
# SERIALIZERS DE AUDITORIA
# =========================


class LogAuditoriaSerializer(serializers.ModelSerializer):
    """Serializer para logs de auditoria"""

    usuario_nome = serializers.CharField(source="usuario.get_full_name", read_only=True)

    class Meta:
        model = LogAuditoria
        fields = [
            "id",
            "usuario",
            "usuario_nome",
            "acao",
            "entidade_afetada_id",
            "detalhes",
            "data_hora",
        ]
        read_only_fields = ["id", "data_hora"]


# =========================
# SERIALIZERS DE DESLOCAMENTO
# =========================


class DeslocamentoSerializer(serializers.ModelSerializer):
    """Serializer para deslocamentos"""

    formador_nome = serializers.CharField(source="formador.nome", read_only=True)
    municipio_origem_nome = serializers.CharField(
        source="municipio_origem.nome", read_only=True
    )
    municipio_destino_nome = serializers.CharField(
        source="municipio_destino.nome", read_only=True
    )

    class Meta:
        model = Deslocamento
        fields = [
            "id",
            "formador",
            "formador_nome",
            "municipio_origem",
            "municipio_origem_nome",
            "municipio_destino",
            "municipio_destino_nome",
            "data_saida",
            "data_chegada",
            "tempo_estimado",
            "observacoes",
            "data_criacao",
        ]
        read_only_fields = ["id", "data_criacao"]


# =========================
# SERIALIZERS DE ESTATÍSTICAS
# =========================


class EstatisticasSerializer(serializers.Serializer):
    """Serializer para dados estatísticos do sistema"""

    total_solicitacoes = serializers.IntegerField(read_only=True)
    solicitacoes_pendentes = serializers.IntegerField(read_only=True)
    solicitacoes_aprovadas = serializers.IntegerField(read_only=True)
    solicitacoes_reprovadas = serializers.IntegerField(read_only=True)
    eventos_criados = serializers.IntegerField(read_only=True)
    formadores_ativos = serializers.IntegerField(read_only=True)
    projetos_ativos = serializers.IntegerField(read_only=True)
    taxa_aprovacao = serializers.FloatField(read_only=True)
    taxa_sincronizacao = serializers.FloatField(read_only=True)


# =========================
# SERIALIZERS DE MAPA MENSAL
# =========================


class MapaMensalSerializer(serializers.Serializer):
    """Serializer para dados do mapa mensal de disponibilidade"""

    formador_id = serializers.UUIDField(read_only=True)
    formador_nome = serializers.CharField(read_only=True)
    ano = serializers.IntegerField(read_only=True)
    mes = serializers.IntegerField(read_only=True)
    disponibilidades = serializers.DictField(read_only=True)
    eventos = serializers.DictField(read_only=True)
    total_dias_mes = serializers.IntegerField(read_only=True)

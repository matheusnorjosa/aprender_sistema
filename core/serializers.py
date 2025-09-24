"""
API Serializers for Aprender Sistema
===================================

Serializers para transformar modelos Django em representações JSON
para as APIs REST do sistema.

Author: Claude Code
Date: Janeiro 2025
"""

try:
    from rest_framework import serializers
    from .models import Usuario, Formador, Solicitacao, Aprovacao, Municipio, Projeto, TipoEvento

    # ===============================
    # SERIALIZERS BÁSICOS
    # ===============================

    class MunicipioSerializer(serializers.ModelSerializer):
        """Serializer para Município"""

        class Meta:
            model = Municipio
            fields = ['id', 'nome', 'uf', 'ativo']
            read_only_fields = ['id']

    class ProjetoSerializer(serializers.ModelSerializer):
        """Serializer para Projeto"""

        class Meta:
            model = Projeto
            fields = ['id', 'nome', 'descricao', 'ativo']
            read_only_fields = ['id']

    class TipoEventoSerializer(serializers.ModelSerializer):
        """Serializer para Tipo de Evento"""

        class Meta:
            model = TipoEvento
            fields = ['id', 'nome', 'descricao', 'duracao_padrao_horas', 'online', 'presencial']
            read_only_fields = ['id']

    # ===============================
    # SERIALIZERS DE USUÁRIO
    # ===============================

    class UsuarioBasicSerializer(serializers.ModelSerializer):
        """Serializer básico para Usuario (sem informações sensíveis)"""

        municipio_nome = serializers.CharField(source='municipio.nome', read_only=True)
        setor_nome = serializers.CharField(source='setor.nome', read_only=True)

        class Meta:
            model = Usuario
            fields = [
                'id', 'username', 'first_name', 'last_name', 'email',
                'cargo', 'area_especializacao', 'formador_ativo',
                'municipio_nome', 'setor_nome', 'is_active'
            ]
            read_only_fields = ['id', 'username']

    class FormadorSerializer(serializers.ModelSerializer):
        """Serializer para Formador com dados do usuário"""

        usuario = UsuarioBasicSerializer(read_only=True)

        class Meta:
            model = Formador
            fields = [
                'id', 'usuario', 'nome', 'especialidade',
                'anos_experiencia', 'observacoes'
            ]
            read_only_fields = ['id']

    # ===============================
    # SERIALIZERS DE SOLICITAÇÃO
    # ===============================

    class SolicitacaoListSerializer(serializers.ModelSerializer):
        """Serializer para listagem de solicitações"""

        coordenador_nome = serializers.CharField(source='coordenador.get_full_name', read_only=True)
        formador_nome = serializers.CharField(source='formador.nome', read_only=True)
        projeto_nome = serializers.CharField(source='projeto.nome', read_only=True)
        municipio_nome = serializers.CharField(source='municipio.nome', read_only=True)
        tipo_evento_nome = serializers.CharField(source='tipo_evento.nome', read_only=True)
        status_display = serializers.CharField(source='get_status_display', read_only=True)

        class Meta:
            model = Solicitacao
            fields = [
                'id', 'titulo', 'data_inicio', 'data_fim', 'status', 'status_display',
                'coordenador_nome', 'formador_nome', 'projeto_nome',
                'municipio_nome', 'tipo_evento_nome', 'data_criacao'
            ]

    class SolicitacaoDetailSerializer(serializers.ModelSerializer):
        """Serializer detalhado para solicitação"""

        coordenador = UsuarioBasicSerializer(read_only=True)
        formador = FormadorSerializer(read_only=True)
        projeto = ProjetoSerializer(read_only=True)
        municipio = MunicipioSerializer(read_only=True)
        tipo_evento = TipoEventoSerializer(read_only=True)

        class Meta:
            model = Solicitacao
            fields = [
                'id', 'titulo', 'descricao', 'data_inicio', 'data_fim',
                'status', 'coordenador', 'formador', 'projeto', 'municipio',
                'tipo_evento', 'observacoes', 'data_criacao', 'data_atualizacao',
                'evento_google_calendar_id', 'link_meet'
            ]
            read_only_fields = ['id', 'data_criacao', 'data_atualizacao']

    class SolicitacaoCreateSerializer(serializers.ModelSerializer):
        """Serializer para criação de solicitação"""

        class Meta:
            model = Solicitacao
            fields = [
                'titulo', 'descricao', 'data_inicio', 'data_fim',
                'formador', 'projeto', 'municipio', 'tipo_evento', 'observacoes'
            ]

        def validate(self, data):
            """Validações customizadas"""
            # Verificar se data_fim > data_inicio
            if data['data_fim'] <= data['data_inicio']:
                raise serializers.ValidationError(
                    "Data de fim deve ser posterior à data de início"
                )

            # Verificar se não é data passada
            from django.utils import timezone
            if data['data_inicio'] <= timezone.now():
                raise serializers.ValidationError(
                    "Não é possível criar eventos no passado"
                )

            return data

    # ===============================
    # SERIALIZERS DE APROVAÇÃO
    # ===============================

    class AprovacaoSerializer(serializers.ModelSerializer):
        """Serializer para aprovações"""

        solicitacao = SolicitacaoListSerializer(read_only=True)
        aprovador_nome = serializers.CharField(source='aprovador.get_full_name', read_only=True)

        class Meta:
            model = Aprovacao
            fields = [
                'id', 'solicitacao', 'aprovador_nome', 'status',
                'observacoes', 'data_aprovacao'
            ]

    # ===============================
    # SERIALIZERS PARA HEALTH CHECK
    # ===============================

    class HealthCheckSerializer(serializers.Serializer):
        """Serializer para response do health check"""

        status = serializers.CharField(help_text="Status geral do sistema (healthy/unhealthy)")
        timestamp = serializers.DateTimeField(help_text="Timestamp da verificação")
        environment = serializers.CharField(help_text="Ambiente (development/staging/production)")
        checks = serializers.DictField(help_text="Detalhes dos checks individuais")

    class DatabaseCheckSerializer(serializers.Serializer):
        """Serializer para check de database"""

        status = serializers.CharField(help_text="Status do database (healthy/unhealthy)")
        response_time_ms = serializers.IntegerField(help_text="Tempo de resposta em ms", required=False)
        error = serializers.CharField(help_text="Mensagem de erro se houver", required=False)

    class SystemMetricsSerializer(serializers.Serializer):
        """Serializer para métricas do sistema"""

        cpu_percent = serializers.FloatField(help_text="Uso de CPU em %", required=False)
        memory_percent = serializers.FloatField(help_text="Uso de memória em %", required=False)
        disk_usage_percent = serializers.FloatField(help_text="Uso de disco em %", required=False)
        load_average = serializers.ListField(help_text="Load average do sistema", required=False)
        note = serializers.CharField(help_text="Nota sobre métricas", required=False)

    class ApplicationMetricsSerializer(serializers.Serializer):
        """Serializer para métricas da aplicação"""

        total_users = serializers.IntegerField(help_text="Total de usuários")
        active_users = serializers.IntegerField(help_text="Usuários ativos")
        total_solicitacoes = serializers.IntegerField(help_text="Total de solicitações")
        solicitacoes_pendentes = serializers.IntegerField(help_text="Solicitações pendentes")
        recent_audit_logs = serializers.IntegerField(help_text="Logs de auditoria recentes")

except ImportError:
    # DRF não disponível - criar classes vazias para evitar erros
    class BaseSerializer:
        pass

    HealthCheckSerializer = BaseSerializer
    SolicitacaoListSerializer = BaseSerializer
    # ... outras classes vazias conforme necessário
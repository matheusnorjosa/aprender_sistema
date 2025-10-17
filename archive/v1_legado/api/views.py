"""
Django REST Framework ViewSets para o Aprender Sistema.
Implementa todas as operações CRUD via API RESTful.
"""

from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Q

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from core.models import (
    Aprovacao,
    Deslocamento,
    DisponibilidadeFormadores,
    EventoGoogleCalendar,
    Formador,
    LogAuditoria,
    Municipio,
    Projeto,
    Solicitacao,
    TipoEvento,
)

from .serializers import *

User = get_user_model()


# =========================
# PERMISSÕES CUSTOMIZADAS
# =========================


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Permite edição apenas para o dono do objeto"""

    def has_object_permission(self, request, view, obj):
        # Read permissions para todos
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions apenas para o dono
        if hasattr(obj, "usuario_solicitante"):
            return obj.usuario_solicitante == request.user

        return obj.usuario == request.user


class IsSuperintendenciaOrReadOnly(permissions.BasePermission):
    """Permite aprovação apenas para superintendência"""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated

        return request.user.has_role("superintendencia")


# =========================
# VIEWSETS DE USUÁRIOS
# =========================


class UsuarioViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para usuários (apenas leitura)"""

    queryset = User.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter, DjangoFilterBackend]
    search_fields = ["username", "first_name", "last_name", "email"]
    ordering_fields = ["username", "date_joined", "last_login"]
    ordering = ["username"]
    filterset_fields = ["is_active", "groups__name"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return UsuarioDetailSerializer
        return UsuarioListSerializer

    @action(detail=False, methods=["get"])
    def me(self, request):
        """Retorna dados do usuário atual"""
        serializer = UsuarioDetailSerializer(request.user)
        return Response(serializer.data)


# =========================
# VIEWSETS DE REFERÊNCIA
# =========================


class ProjetoViewSet(viewsets.ModelViewSet):
    """ViewSet para projetos"""

    queryset = Projeto.objects.filter(ativo=True)
    serializer_class = ProjetoSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter, DjangoFilterBackend]
    search_fields = ["nome", "descricao"]
    ordering_fields = ["nome"]
    ordering = ["nome"]
    filterset_fields = ["ativo", "vinculado_superintendencia"]


class MunicipioViewSet(viewsets.ModelViewSet):
    """ViewSet para municípios"""

    queryset = Municipio.objects.all()
    serializer_class = MunicipioSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter, DjangoFilterBackend]
    search_fields = ["nome", "uf"]
    ordering_fields = ["nome", "uf", "populacao"]
    ordering = ["nome"]
    filterset_fields = ["uf", "regiao"]


class TipoEventoViewSet(viewsets.ModelViewSet):
    """ViewSet para tipos de evento"""

    queryset = TipoEvento.objects.all()
    serializer_class = TipoEventoSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter, DjangoFilterBackend]
    search_fields = ["nome", "descricao"]
    ordering_fields = ["nome", "duracao"]
    ordering = ["nome"]
    filterset_fields = ["online", "requer_deslocamento"]


# =========================
# VIEWSETS DE FORMADORES
# =========================


class FormadorViewSet(viewsets.ModelViewSet):
    """ViewSet para formadores"""

    queryset = Formador.objects.filter(ativo=True)
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter, DjangoFilterBackend]
    search_fields = ["nome", "email", "areas_atuacao"]
    ordering_fields = ["nome", "data_cadastro"]
    ordering = ["nome"]
    filterset_fields = ["ativo", "municipios", "tipos_evento"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return FormadorDetailSerializer
        return FormadorListSerializer

    @action(detail=True, methods=["get"])
    def disponibilidade(self, request, pk=None):
        """Retorna disponibilidade do formador para um período"""
        formador = self.get_object()
        ano = request.query_params.get("ano", datetime.now().year)
        mes = request.query_params.get("mes", datetime.now().month)

        disponibilidades = DisponibilidadeFormadores.objects.filter(
            formador=formador, data__year=ano, data__month=mes
        )

        serializer = DisponibilidadeFormadoresSerializer(disponibilidades, many=True)
        return Response(serializer.data)


# =========================
# VIEWSETS DE SOLICITAÇÕES
# =========================


class SolicitacaoViewSet(viewsets.ModelViewSet):
    """ViewSet para solicitações"""

    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [SearchFilter, OrderingFilter, DjangoFilterBackend]
    search_fields = ["titulo_evento", "descricao_evento"]
    ordering_fields = ["data_solicitacao", "data_inicio", "data_fim"]
    ordering = ["-data_solicitacao"]
    filterset_fields = [
        "status",
        "projeto",
        "municipio",
        "tipo_evento",
        "usuario_solicitante",
        "usuario_aprovador",
    ]

    def get_queryset(self):
        """Filtrar solicitações baseado no perfil do usuário"""
        user = self.request.user

        if user.has_role("superintendencia") or user.has_role("admin"):
            # Superintendência e admin veem tudo
            return Solicitacao.objects.all().select_related(
                "projeto",
                "municipio",
                "tipo_evento",
                "usuario_solicitante",
                "usuario_aprovador",
            )
        elif user.has_role("coordenador"):
            # Coordenadores veem apenas suas próprias
            return Solicitacao.objects.filter(usuario_solicitante=user).select_related(
                "projeto",
                "municipio",
                "tipo_evento",
                "usuario_solicitante",
                "usuario_aprovador",
            )
        else:
            # Outros papéis veem apenas aprovadas
            return Solicitacao.objects.filter(
                status__in=["PRE_AGENDA", "APROVADO"]
            ).select_related(
                "projeto",
                "municipio",
                "tipo_evento",
                "usuario_solicitante",
                "usuario_aprovador",
            )

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return SolicitacaoCreateUpdateSerializer
        elif self.action == "retrieve":
            return SolicitacaoDetailSerializer
        return SolicitacaoListSerializer

    def perform_create(self, serializer):
        """Definir usuário solicitante automaticamente"""
        serializer.save(usuario_solicitante=self.request.user)

    @action(detail=False, methods=["get"])
    def pendentes(self, request):
        """Retorna solicitações pendentes (apenas para superintendência)"""
        if not request.user.has_role("superintendencia"):
            return Response(
                {"detail": "Acesso negado"}, status=status.HTTP_403_FORBIDDEN
            )

        pendentes = (
            self.get_queryset().filter(status="PENDENTE").order_by("data_inicio")
        )

        page = self.paginate_queryset(pendentes)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(pendentes, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def minhas(self, request):
        """Retorna solicitações do usuário atual"""
        minhas = (
            Solicitacao.objects.filter(usuario_solicitante=request.user)
            .select_related("projeto", "municipio", "tipo_evento")
            .order_by("-data_solicitacao")
        )

        page = self.paginate_queryset(minhas)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(minhas, many=True)
        return Response(serializer.data)


# =========================
# VIEWSETS DE APROVAÇÕES
# =========================


class AprovacaoViewSet(viewsets.ModelViewSet):
    """ViewSet para aprovações"""

    queryset = Aprovacao.objects.all().select_related(
        "solicitacao", "usuario_aprovador"
    )
    serializer_class = AprovacaoSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperintendenciaOrReadOnly]
    filter_backends = [SearchFilter, OrderingFilter, DjangoFilterBackend]
    ordering_fields = ["data_decisao"]
    ordering = ["-data_decisao"]
    filterset_fields = ["status_decisao", "usuario_aprovador"]

    def perform_create(self, serializer):
        """Definir usuário aprovador automaticamente"""
        serializer.save(usuario_aprovador=self.request.user)


# =========================
# VIEWSETS DE EVENTOS GOOGLE
# =========================


class EventoGoogleCalendarViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para eventos do Google Calendar (apenas leitura)"""

    queryset = EventoGoogleCalendar.objects.all().select_related("solicitacao")
    serializer_class = EventoGoogleCalendarSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter, DjangoFilterBackend]
    search_fields = ["titulo", "google_event_id"]
    ordering_fields = ["data_criacao", "data_inicio_google"]
    ordering = ["-data_criacao"]
    filterset_fields = ["solicitacao"]


# =========================
# VIEWSETS DE DISPONIBILIDADE
# =========================


class DisponibilidadeFormadoresViewSet(viewsets.ModelViewSet):
    """ViewSet para disponibilidade de formadores"""

    queryset = DisponibilidadeFormadores.objects.all().select_related("formador")
    serializer_class = DisponibilidadeFormadoresSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [OrderingFilter, DjangoFilterBackend]
    ordering_fields = ["data", "data_atualizacao"]
    ordering = ["-data"]
    filterset_fields = ["formador", "codigo", "data"]

    @action(detail=False, methods=["get"])
    def mapa_mensal(self, request):
        """Retorna mapa de disponibilidade mensal"""
        ano = int(request.query_params.get("ano", datetime.now().year))
        mes = int(request.query_params.get("mes", datetime.now().month))

        # Usar lógica similar à view original
        from core.views.formador_views import MapaMensalView

        view = MapaMensalView()
        data = view.get_dados_mapa_mensal(ano, mes)

        serializer = MapaMensalSerializer(data, many=True)
        return Response(serializer.data)


# =========================
# VIEWSETS DE AUDITORIA
# =========================


class LogAuditoriaViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para logs de auditoria (apenas leitura)"""

    queryset = LogAuditoria.objects.all().select_related("usuario")
    serializer_class = LogAuditoriaSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter, DjangoFilterBackend]
    search_fields = ["acao", "detalhes"]
    ordering_fields = ["data_hora"]
    ordering = ["-data_hora"]
    filterset_fields = ["usuario", "acao"]

    def get_queryset(self):
        """Filtrar logs baseado no perfil do usuário"""
        user = self.request.user

        if user.has_role("admin") or user.has_role("superintendencia"):
            return LogAuditoria.objects.all()
        else:
            # Usuários normais veem apenas seus próprios logs
            return LogAuditoria.objects.filter(usuario=user)


# =========================
# VIEWSETS DE ESTATÍSTICAS
# =========================


class EstatisticasViewSet(viewsets.ViewSet):
    """ViewSet para estatísticas do sistema"""

    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        """Retorna estatísticas gerais do sistema"""
        # Calcular estatísticas
        total_solicitacoes = Solicitacao.objects.count()
        pendentes = Solicitacao.objects.filter(status="PENDENTE").count()
        aprovadas = Solicitacao.objects.filter(status="PRE_AGENDA").count()
        reprovadas = Solicitacao.objects.filter(status="REPROVADO").count()
        eventos_criados = EventoGoogleCalendar.objects.count()
        formadores_ativos = Formador.objects.filter(ativo=True).count()
        projetos_ativos = Projeto.objects.filter(ativo=True).count()

        # Calcular taxas
        taxa_aprovacao = (
            (aprovadas / total_solicitacoes * 100) if total_solicitacoes > 0 else 0
        )
        taxa_sincronizacao = (eventos_criados / aprovadas * 100) if aprovadas > 0 else 0

        data = {
            "total_solicitacoes": total_solicitacoes,
            "solicitacoes_pendentes": pendentes,
            "solicitacoes_aprovadas": aprovadas,
            "solicitacoes_reprovadas": reprovadas,
            "eventos_criados": eventos_criados,
            "formadores_ativos": formadores_ativos,
            "projetos_ativos": projetos_ativos,
            "taxa_aprovacao": round(taxa_aprovacao, 1),
            "taxa_sincronizacao": round(taxa_sincronizacao, 1),
        }

        serializer = EstatisticasSerializer(data)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def por_periodo(self, request):
        """Estatísticas por período"""
        dias = int(request.query_params.get("dias", 30))
        data_inicio = datetime.now() - timedelta(days=dias)

        # Filtrar por período
        solicitacoes_periodo = Solicitacao.objects.filter(
            data_solicitacao__gte=data_inicio
        )
        aprovacoes_periodo = Aprovacao.objects.filter(data_decisao__gte=data_inicio)

        data = {
            "periodo_dias": dias,
            "solicitacoes_periodo": solicitacoes_periodo.count(),
            "aprovacoes_periodo": aprovacoes_periodo.count(),
            "solicitacoes_por_status": dict(
                solicitacoes_periodo.values_list("status").annotate(
                    count=Count("status")
                )
            ),
            "aprovacoes_por_decisao": dict(
                aprovacoes_periodo.values_list("status_decisao").annotate(
                    count=Count("status_decisao")
                )
            ),
        }

        return Response(data)

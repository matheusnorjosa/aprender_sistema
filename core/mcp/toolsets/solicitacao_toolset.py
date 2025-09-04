"""
MCP Toolset for Solicitacao and Aprovacao Models - Aprender Sistema

Specialized toolset for managing event requests and approvals.
"""

from django.db.models import Q
from django.utils import timezone

from django_mcp_server.toolsets import ModelQueryToolset

from core.models import (
    Aprovacao,
    EventoGoogleCalendar,
    FormadoresSolicitacao,
    Solicitacao,
    SolicitacaoStatus,
)


class SolicitacaoToolset(ModelQueryToolset):
    """
    MCP toolset for managing solicitações (event requests) and approvals
    """

    name = "solicitacao_management"
    description = "Manage event requests, approvals, and related operations"

    models = [
        Solicitacao,
        Aprovacao,
        FormadoresSolicitacao,
        EventoGoogleCalendar,
    ]

    accessible_fields = {
        "Solicitacao": [
            "id",
            "titulo_evento",
            "data_inicio",
            "data_fim",
            "status",
            "projeto",
            "municipio",
            "tipo_evento",
            "usuario_solicitante",
            "formadores",
            "data_solicitacao",
            "coordenador_acompanha",
            "observacoes",
            "numero_encontro_formativo",
        ],
        "Aprovacao": [
            "id",
            "solicitacao",
            "usuario_aprovador",
            "data_aprovacao",
            "status_decisao",
            "justificativa",
        ],
        "FormadoresSolicitacao": ["id", "solicitacao", "formador"],
        "EventoGoogleCalendar": [
            "id",
            "solicitacao",
            "provider_event_id",
            "html_link",
            "meet_link",
            "status_sincronizacao",
            "data_criacao",
        ],
    }

    readonly_fields = {
        "Solicitacao": ["id", "data_solicitacao"],
        "Aprovacao": ["id", "data_aprovacao"],
        "FormadoresSolicitacao": ["id"],
        "EventoGoogleCalendar": ["id", "data_criacao", "provider_event_id"],
    }

    def get_queryset(self, model):
        """
        Customize querysets with optimized queries
        """
        if model == Solicitacao:
            return model.objects.select_related(
                "projeto", "municipio", "tipo_evento", "usuario_solicitante"
            ).prefetch_related("formadores", "aprovacoes")
        elif model == Aprovacao:
            return model.objects.select_related("solicitacao", "usuario_aprovador")
        elif model == FormadoresSolicitacao:
            return model.objects.select_related("solicitacao", "formador")
        elif model == EventoGoogleCalendar:
            return model.objects.select_related("solicitacao")
        else:
            return model.objects.all()

    def can_query(self, model, user=None):
        """
        Permission check for querying
        """
        if not user or not user.is_authenticated:
            return False

        # Everyone can query (with filtered results)
        return True

    def filter_queryset_by_user(self, queryset, model, user):
        """
        Filter querysets based on user permissions
        """
        if not user or not user.is_authenticated:
            return queryset.none()

        # Superuser sees everything
        if user.is_superuser:
            return queryset

        # Superintendencia and Admin see all
        if user.groups.filter(name__in=["superintendencia", "admin"]).exists():
            return queryset

        # Controle sees all for monitoring
        if user.groups.filter(name="controle").exists():
            return queryset

        # Coordenadores see their own solicitações
        if model == Solicitacao and user.groups.filter(name="coordenador").exists():
            return queryset.filter(usuario_solicitante=user)

        # Formadores see solicitações they're involved in
        if model == Solicitacao and hasattr(user, "formador_profile"):
            return queryset.filter(formadores=user.formador_profile)

        # For other models, apply same logic through solicitacao relationship
        if hasattr(model, "solicitacao"):
            # Get allowed solicitações first
            allowed_solicitacoes = self.filter_queryset_by_user(
                Solicitacao.objects.all(), Solicitacao, user
            )
            return queryset.filter(solicitacao__in=allowed_solicitacoes)

        return queryset.none()

    def can_create(self, model, user=None):
        """
        Permission check for creating objects
        """
        if not user or not user.is_authenticated:
            return False

        if model == Solicitacao:
            # Coordenadores can create solicitações
            return user.groups.filter(
                name__in=["coordenador", "superintendencia", "admin"]
            ).exists()

        elif model == Aprovacao:
            # Only superintendencia can create approvals
            return user.groups.filter(name__in=["superintendencia", "admin"]).exists()

        elif model == FormadoresSolicitacao:
            # Can add formadores to solicitação if can edit the solicitação
            return user.groups.filter(
                name__in=["coordenador", "superintendencia", "admin"]
            ).exists()

        elif model == EventoGoogleCalendar:
            # Only control and admin can create calendar events
            return user.groups.filter(name__in=["controle", "admin"]).exists()

        return False

    def can_update(self, model, obj, user=None):
        """
        Permission check for updating objects
        """
        if not user or not user.is_authenticated:
            return False

        if model == Solicitacao:
            # Owner can edit if still pending
            if (
                obj.usuario_solicitante == user
                and obj.status == SolicitacaoStatus.PENDENTE
            ):
                return True

            # Superintendencia can edit approved/rejected ones
            if user.groups.filter(name__in=["superintendencia", "admin"]).exists():
                return True

        elif model == Aprovacao:
            # Only superintendencia can update approvals
            return user.groups.filter(name__in=["superintendencia", "admin"]).exists()

        elif model == EventoGoogleCalendar:
            # Only control and admin can update calendar events
            return user.groups.filter(name__in=["controle", "admin"]).exists()

        return False

    def can_delete(self, model, obj, user=None):
        """
        Permission check for deleting objects
        """
        if not user or not user.is_authenticated:
            return False

        # Very restrictive - only admin can delete
        if user.is_superuser:
            return True

        # Coordenador can delete their own pending solicitações
        if (
            model == Solicitacao
            and obj.usuario_solicitante == user
            and obj.status == SolicitacaoStatus.PENDENTE
            and user.groups.filter(name="coordenador").exists()
        ):
            return True

        return False

    # Custom MCP tools
    def get_pending_solicitacoes_count(self, user=None):
        """
        Custom tool to get count of pending solicitações
        """
        queryset = Solicitacao.objects.filter(status=SolicitacaoStatus.PENDENTE)
        queryset = self.filter_queryset_by_user(queryset, Solicitacao, user)
        return queryset.count()

    def get_solicitacoes_by_status(self, status, user=None):
        """
        Get solicitações filtered by status
        """
        queryset = Solicitacao.objects.filter(status=status)
        queryset = self.filter_queryset_by_user(queryset, Solicitacao, user)
        return list(
            queryset.values(
                "id",
                "titulo_evento",
                "data_inicio",
                "data_fim",
                "projeto__nome",
                "municipio__nome",
                "usuario_solicitante__username",
            )
        )

    def get_monthly_statistics(self, year, month, user=None):
        """
        Get monthly statistics for solicitações
        """
        start_date = timezone.datetime(year, month, 1).date()
        if month == 12:
            end_date = timezone.datetime(year + 1, 1, 1).date()
        else:
            end_date = timezone.datetime(year, month + 1, 1).date()

        queryset = Solicitacao.objects.filter(
            data_inicio__date__gte=start_date, data_inicio__date__lt=end_date
        )
        queryset = self.filter_queryset_by_user(queryset, Solicitacao, user)

        return {
            "total": queryset.count(),
            "pendentes": queryset.filter(status=SolicitacaoStatus.PENDENTE).count(),
            "pre_agenda": queryset.filter(status=SolicitacaoStatus.PRE_AGENDA).count(),
            "aprovadas": queryset.filter(status=SolicitacaoStatus.APROVADO).count(),
            "reprovadas": queryset.filter(status=SolicitacaoStatus.REPROVADO).count(),
        }

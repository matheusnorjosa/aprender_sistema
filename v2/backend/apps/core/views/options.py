"""
AS v2 — Options API ViewSets

Read-only ViewSets for dropdown options (PR 8/N).
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

from django.db.models import QuerySet

from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated

from apps.core.models import Municipio, Projeto, TipoEvento, Usuario
from apps.core.serializers import (
    MunicipioOptionSerializer,
    ProjetoOptionSerializer,
    TipoEventoOptionSerializer,
    UsuarioOptionSerializer,
)


class MunicipioOptionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet read-only para dropdown de municípios.

    GET /api/options/municipios/?search=<termo>
    Retorna: [{id, nome, uf}]

    Permissões: IsAuthenticated (todos usuários logados)
    Busca: Server-side por nome e UF
    """

    queryset = Municipio.objects.filter(ativo=True).order_by("nome")
    serializer_class = MunicipioOptionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Sem paginação para dropdowns
    filter_backends = [SearchFilter]
    search_fields = ["nome", "uf"]


class ProjetoOptionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet read-only para dropdown de projetos.

    GET /api/options/projetos/?search=<termo>
    Retorna: [{id, nome, codigo}]

    Permissões: IsAuthenticated (todos usuários logados)
    Busca: Server-side por nome e código

    Issue #153: Filtra is_test=False por padrão (oculta projetos de teste)
    Para incluir projetos de teste, use query param ?include_test=true
    """

    queryset = Projeto.objects.filter(ativo=True).order_by("nome")
    serializer_class = ProjetoOptionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Sem paginação para dropdowns
    filter_backends = [SearchFilter]
    search_fields = ["nome", "codigo"]

    def filter_queryset(self, queryset: QuerySet[Projeto]) -> QuerySet[Projeto]:
        """
        Apply filters to the queryset, including is_test filter.

        This is called AFTER get_queryset() but BEFORE serialization.

        Issue #153: Filter out test projects by default
        """
        # First apply standard filter backends (Search, etc.)
        queryset = super().filter_queryset(queryset)

        # Then apply is_test filter
        param_val = self.request.query_params.get("include_test", "false")
        include_test = param_val.lower() == "true"

        if not include_test:
            queryset = queryset.filter(is_test=False)

        return queryset


class CoordenadorOptionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet read-only para dropdown de coordenadores.

    GET /api/options/coordenadores/?search=<termo>
    Retorna: [{id, username, nome_completo, email}]

    Permissões: IsAuthenticated (todos usuários logados)
    Filtro: Usuários dos grupos "Coordenador" ou "Apoio de Coordenação"
    Busca: Server-side por username, nome, sobrenome e email

    Nota: Apoio de Coordenação tem as mesmas permissões de Coordenador.
    """

    serializer_class = UsuarioOptionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Sem paginação para dropdowns
    filter_backends = [SearchFilter]
    search_fields = ["username", "first_name", "last_name", "email"]

    def get_queryset(self) -> QuerySet:
        """Retorna usuários coordenadores e apoio de coordenação ativos."""
        return (
            Usuario.objects.filter(
                is_active=True,
                groups__name__in=["Coordenador", "Apoio de Coordenação"],
            )
            .distinct()
            .order_by("first_name", "last_name")
        )


class FormadorOptionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet read-only para dropdown de formadores.

    GET /api/options/formadores/?search=<termo>
    Retorna: [{id, username, nome_completo, email}]

    Permissões: IsAuthenticated (todos usuários logados)
    Filtro: Apenas usuários do grupo "Formador" ou superusers
    Busca: Server-side por username, nome, sobrenome e email
    """

    serializer_class = UsuarioOptionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Sem paginação para dropdowns
    filter_backends = [SearchFilter]
    search_fields = ["username", "first_name", "last_name", "email"]

    def get_queryset(self) -> QuerySet:
        """Retorna apenas usuários formadores ativos"""
        return (
            Usuario.objects.filter(is_active=True, groups__name="Formador")
            .distinct()
            .order_by("first_name", "last_name")
        )


class TipoEventoOptionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet read-only para dropdown de tipos de evento.

    GET /api/options/tipos-evento/?search=<termo>
    Retorna: [{id, nome, descricao}]

    Permissões: IsAuthenticated (todos usuários logados)
    Busca: Server-side por nome e descrição
    """

    queryset = TipoEvento.objects.all().order_by("nome")
    serializer_class = TipoEventoOptionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Sem paginação para dropdowns
    filter_backends = [SearchFilter]
    search_fields = ["nome", "descricao"]

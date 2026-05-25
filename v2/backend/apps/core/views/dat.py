"""
AS v2 — DAT Registros ViewSets

ViewSets para DATRegistro e ProjetoGeral (acompanhamento de turmas).

Ref: v2/docs/SPEC_DAT_REGISTROS.md
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Count, Q, QuerySet
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend

from apps.core.models import DATRegistro, ProjetoGeral
from apps.core.permissions import HasPerm
from apps.core.serializers import (
    DATRegistroCreateSerializer,
    DATRegistroDetailSerializer,
    DATRegistroListSerializer,
    DATRegistroUpdateSerializer,
    ProjetoGeralOptionSerializer,
    ProjetoGeralSerializer,
)

if TYPE_CHECKING:
    from rest_framework.request import Request


# Canonical Brazilian region → UF tuple mapping. Must match frontend
# constant at v2/frontend/src/pages/DATModule/DATRegistros/constants.tsx
# (REGIAO_UFS) — divergence breaks the regiao filter on /dat/registros.
REGIAO_UFS: dict[str, tuple[str, ...]] = {
    "Norte": ("AC", "AP", "AM", "PA", "RO", "RR", "TO"),
    "Nordeste": ("AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"),
    "Centro-Oeste": ("DF", "GO", "MT", "MS"),
    "Sudeste": ("ES", "MG", "RJ", "SP"),
    "Sul": ("PR", "RS", "SC"),
}
_REGIAO_UFS_CI: dict[str, tuple[str, ...]] = {k.lower(): v for k, v in REGIAO_UFS.items()}


class DATRegistroFilter(filters.FilterSet):
    """
    FilterSet for DATRegistro.

    Supports filtering by:
    - regiao: Brazilian region (Norte, Nordeste, Centro-Oeste, Sudeste, Sul)
    - uf: Município UF (e.g., CE, BA)
    - municipio: Município ID
    - projeto_geral: ProjetoGeral ID
    - projeto: Projeto ID
    - usa_avaliar: Boolean
    - status: Status fields (chaves, instrucoes, envio)
    """

    uf = filters.CharFilter(field_name="municipio__uf", lookup_expr="iexact")
    regiao = filters.CharFilter(method="filter_regiao")
    status_formar = filters.CharFilter(method="filter_status_formar")

    def filter_regiao(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        """Filter by Brazilian region → set of UFs (case-insensitive)."""
        ufs = _REGIAO_UFS_CI.get(value.lower())
        if not ufs:
            return queryset.none()
        return queryset.filter(municipio__uf__in=ufs)

    def filter_status_formar(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        """Filter by FORMAR completion status."""
        if value == "completo":
            return queryset.filter(
                chaves_inscricao_status="concluido",
                instrucoes_status="concluido",
                envio_codigos_status="concluido",
            )
        elif value == "pendente":
            return queryset.exclude(
                chaves_inscricao_status="concluido",
                instrucoes_status="concluido",
                envio_codigos_status="concluido",
            )
        return queryset

    class Meta:
        model = DATRegistro
        fields = [
            "municipio",
            "projeto_geral",
            "projeto",
            "usa_avaliar",
            "uf",
            "turma_formar_status",
            "chaves_inscricao_status",
            "instrucoes_status",
            "envio_codigos_status",
        ]


class DATRegistroViewSet(viewsets.ModelViewSet):
    """
    ViewSet para CRUD de Registros DAT.

    Endpoints:
        - GET /api/dat/registros/ - Listar registros (paginado)
        - POST /api/dat/registros/ - Criar registro (DAT only)
        - GET /api/dat/registros/{id}/ - Detalhe
        - PATCH /api/dat/registros/{id}/ - Atualizar (DAT only)
        - DELETE /api/dat/registros/{id}/ - Excluir (Superintendência only)

    Filtros:
        - municipio (FK)
        - projeto_geral (FK)
        - projeto (FK)
        - uf (CharField via municipio)
        - usa_avaliar (bool)
        - status_formar (completo/pendente)
        - search: busca em municipio, projeto

    Permissões (SPEC_DAT_REGISTROS.md seção 4.3):
        - Visualizar: qualquer autenticado
        - Criar/Editar: DAT ou Superintendência
        - Excluir: apenas Superintendência
        - Importar: DAT ou Superintendência
        - Exportar: qualquer autenticado

    Ref: SPEC_DAT_REGISTROS.md seção 4
    """

    queryset = DATRegistro.objects.select_related(
        "municipio",
        "projeto_geral",
        "projeto",
        "created_by",
        "updated_by",
    ).order_by("-created_at")

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = DATRegistroFilter
    search_fields = [
        "municipio__nome",
        "projeto_geral__nome",
        "projeto__nome",
        "obs_formar",
        "obs_avaliar",
    ]
    ordering_fields = [
        "created_at",
        "municipio__nome",
        "projeto_geral__nome",
        "aluno_qtde",
    ]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == "create":
            return DATRegistroCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return DATRegistroUpdateSerializer
        elif self.action == "retrieve":
            return DATRegistroDetailSerializer
        return DATRegistroListSerializer

    def get_permissions(self):
        """
        Permissões baseadas na ação:
        Apenas DAT (e Superintendência/Superusers) têm acesso.

        - list, retrieve, export, stats: DAT ou Superintendência
        - create, update, partial_update: DAT ou Superintendência
        - destroy: apenas Superintendência (SPEC_DAT_REGISTROS.md seção 4.3)
        """
        if self.action == "destroy":
            return [HasPerm("execute_restricted_operations")()]
        return [HasPerm("manage_admin_registries")()]

    @action(detail=False, methods=["get"], permission_classes=[HasPerm("manage_admin_registries")])
    def export(self, request: Request) -> Response:
        """
        Exporta registros para CSV.

        GET /api/dat/registros/export/
        Query params: mesmos filtros de list

        Returns: CSV file
        """
        import csv
        from io import StringIO

        from django.http import HttpResponse

        from apps.core.utils.csv_sanitize import sanitize_csv_value

        # Apply filters
        queryset = self.filter_queryset(self.get_queryset())

        # Create CSV
        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(
            [
                "Município",
                "UF",
                "Projeto Geral",
                "Projeto",
                "Qtde Alunos",
                "Qtde Professores",
                "Reunião DAT",
                "Turma FORMAR ID",
                "Nº Códigos",
                "Chaves Inscrição",
                "Instruções",
                "Envio Códigos",
                "Usa AVALIAR",
                "Alunos Recebidos",
                "Alunos Validados",
                "Alunos Importados",
            ]
        )

        # SEC-007: Rows sanitized against CSV injection
        for r in queryset:
            writer.writerow(
                [
                    sanitize_csv_value(r.municipio.nome),
                    sanitize_csv_value(r.municipio.uf),
                    sanitize_csv_value(r.projeto_geral.nome),
                    sanitize_csv_value(r.projeto.nome),
                    r.aluno_qtde,
                    r.professor_qtde or "",
                    sanitize_csv_value(r.reuniao_dat or ""),
                    sanitize_csv_value(r.turma_formar_id or ""),
                    r.nr_codigos or "",
                    sanitize_csv_value(r.chaves_inscricao_status),
                    sanitize_csv_value(r.instrucoes_status),
                    sanitize_csv_value(r.envio_codigos_status),
                    "Sim" if r.usa_avaliar else "Não",
                    sanitize_csv_value(r.alunos_recebidos_status),
                    sanitize_csv_value(r.alunos_validados_status),
                    sanitize_csv_value(r.alunos_importados_status),
                ]
            )

        # Response
        response = HttpResponse(output.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="dat_registros.csv"'
        return response

    @action(detail=False, methods=["get"], permission_classes=[HasPerm("manage_admin_registries")])
    def stats(self, request: Request) -> Response:
        """
        Retorna estatísticas agregadas dos registros.

        GET /api/dat/registros/stats/

        Returns: {
            "total": int,
            "completos_formar": int,
            "completos_avaliar": int,
            "usa_avaliar": int,
            "por_uf": [{uf, count}]
        }
        """
        qs = self.filter_queryset(self.get_queryset())

        # Agregação em uma única query (Issue #308: fix N+1)
        stats = qs.aggregate(
            total=Count("id"),
            completos_formar=Count(
                "id",
                filter=Q(
                    chaves_inscricao_status="concluido",
                    instrucoes_status="concluido",
                    envio_codigos_status="concluido",
                ),
            ),
            usa_avaliar_count=Count("id", filter=Q(usa_avaliar=True)),
            completos_avaliar=Count(
                "id",
                filter=Q(
                    usa_avaliar=True,
                    alunos_recebidos_status="concluido",
                    alunos_validados_status="concluido",
                    alunos_importados_status="concluido",
                ),
            ),
        )

        por_uf = qs.values("municipio__uf").annotate(count=Count("id")).order_by("-count")

        return Response(
            {
                "total": stats["total"],
                "completos_formar": stats["completos_formar"],
                "completos_avaliar": stats["completos_avaliar"],
                "usa_avaliar": stats["usa_avaliar_count"],
                "por_uf": list(por_uf),
            }
        )


class ProjetoGeralViewSet(viewsets.ModelViewSet):
    """
    ViewSet para CRUD de Projetos Gerais.

    Endpoints:
        - GET /api/projetos-gerais/ - Listar
        - POST /api/projetos-gerais/ - Criar (DAT only)
        - GET /api/projetos-gerais/{id}/ - Detalhe
        - PATCH /api/projetos-gerais/{id}/ - Atualizar (DAT only)
        - DELETE /api/projetos-gerais/{id}/ - Excluir (Superintendência only)
        - GET /api/projetos-gerais/{id}/projetos/ - Projetos vinculados

    Filtros:
        - usa_avaliar (bool)
        - ativo (bool)
        - tipo_calculo_codigos (choice)
        - search: nome, descricao

    Ref: SPEC_DAT_REGISTROS.md seção 4.1
    """

    queryset = ProjetoGeral.objects.annotate(
        projetos_count=Count("projetos_especificos", filter=Q(projetos_especificos__ativo=True))
    ).order_by("nome")

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["usa_avaliar", "ativo", "tipo_calculo_codigos"]
    search_fields = ["nome", "descricao"]
    ordering_fields = ["nome", "created_at"]
    ordering = ["nome"]

    def get_serializer_class(self):
        """Return appropriate serializer."""
        if self.action == "list" and self.request.query_params.get("minimal") == "true":
            return ProjetoGeralOptionSerializer
        return ProjetoGeralSerializer

    def get_permissions(self):
        """
        Permissões baseadas na ação:
        - list, retrieve: qualquer autenticado
        - create, update, partial_update: DAT ou Superintendência
        - destroy: apenas Superintendência
        """
        if self.action in ["list", "retrieve", "projetos"]:
            return [IsAuthenticated()]
        elif self.action == "destroy":
            return [HasPerm("execute_restricted_operations")()]
        return [HasPerm("manage_admin_registries")()]

    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated])
    def projetos(self, request: Request, pk=None) -> Response:
        """
        Lista projetos específicos vinculados ao Projeto Geral.

        GET /api/projetos-gerais/{id}/projetos/

        Returns: [{id, nome, codigo, fluxo, ativo}]
        """
        from apps.core.serializers import ProjetoOptionSerializer

        projeto_geral = self.get_object()
        projetos = projeto_geral.projetos_especificos.filter(ativo=True).order_by("nome")

        serializer = ProjetoOptionSerializer(projetos, many=True)
        return Response(serializer.data)

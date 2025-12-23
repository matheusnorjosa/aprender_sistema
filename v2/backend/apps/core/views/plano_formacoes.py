"""
AS v2 — Plano Formacoes ViewSets

ViewSets para PlanoFormacoes, Formacao, Acompanhamento, Prova.

Endpoints:
    - /api/dat/plano-formacoes/ (CRUD + stats + calendario + resumo-projeto)
    - /api/dat/plano-formacoes/{id}/formacoes/{numero}/ (update formacao inline)

Type-checked with Pyright (strict mode).
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false, reportUnknownLambdaType=false

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.db.models import Count, Sum

from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from apps.core.models import (
    Acompanhamento,
    Formacao,
    PlanoFormacoes,
    Prova,
)
from apps.core.permissions import IsDATOrSuper, IsSuperintendenciaOnly
from apps.core.serializers import (
    AcompanhamentoSerializer,
    FormacaoSerializer,
    PlanoFormacoesListSerializer,
    PlanoFormacoesOptionSerializer,
    PlanoFormacoesSerializer,
    ProvaSerializer,
)

if TYPE_CHECKING:
    from rest_framework.request import Request


# ============================================================
# PlanoFormacoes FilterSet
# ============================================================


class PlanoFormacoesFilter(filters.FilterSet):
    """FilterSet para PlanoFormacoes."""

    uf = filters.CharFilter(field_name="municipio__uf", lookup_expr="iexact")

    class Meta:
        model = PlanoFormacoes
        fields = [
            "municipio",
            "projeto",
            "coordenador",
            "ativo",
            "uf",
        ]


# ============================================================
# PlanoFormacoes ViewSet
# ============================================================


class PlanoFormacoesViewSet(viewsets.ModelViewSet):
    """
    ViewSet para CRUD de Planos de Formacoes.

    Endpoints:
        - GET /api/dat/plano-formacoes/ - Listar
        - POST /api/dat/plano-formacoes/ - Criar
        - GET /api/dat/plano-formacoes/{id}/ - Detalhe
        - PATCH /api/dat/plano-formacoes/{id}/ - Atualizar
        - DELETE /api/dat/plano-formacoes/{id}/ - Excluir (Superintendencia only)
        - GET /api/dat/plano-formacoes/stats/ - Estatisticas
        - GET /api/dat/plano-formacoes/calendario/ - Dados para calendario
        - GET /api/dat/plano-formacoes/resumo-projeto/ - Resumo por projeto
        - PATCH /api/dat/plano-formacoes/{id}/formacao/{numero}/ - Atualizar formacao inline

    Permissoes:
        - list, retrieve: DAT ou Superintendencia
        - create, update: DAT ou Superintendencia
        - destroy: apenas Superintendencia
    """

    queryset = PlanoFormacoes.objects.select_related(
        "municipio", "projeto", "coordenador", "created_by", "updated_by"
    ).prefetch_related(
        "formacoes", "acompanhamentos", "provas"
    ).order_by("municipio__nome", "projeto__nome")

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = PlanoFormacoesFilter
    search_fields = ["municipio__nome", "projeto__nome", "coordenador__nome"]
    ordering_fields = ["municipio__nome", "projeto__nome", "ch_anual", "created_at"]
    ordering = ["municipio__nome", "projeto__nome"]

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == "list":
            if self.request.query_params.get("minimal") == "true":
                return PlanoFormacoesOptionSerializer
            return PlanoFormacoesListSerializer
        return PlanoFormacoesSerializer

    def get_permissions(self):
        """Permissoes baseadas na acao."""
        if self.action == "destroy":
            return [IsSuperintendenciaOnly()]
        return [IsDATOrSuper()]

    def perform_create(self, serializer: Any) -> None:
        """Set created_by on create."""
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer: Any) -> None:
        """Set updated_by on update."""
        serializer.save(updated_by=self.request.user)

    @action(detail=False, methods=["get"], permission_classes=[IsDATOrSuper])
    def stats(self, request: Request) -> Response:
        """
        Estatisticas agregadas dos planos de formacoes.

        GET /api/dat/plano-formacoes/stats/

        Returns: {
            total_planos, total_formacoes, total_realizadas,
            ch_total, por_projeto, por_uf, por_coordenador
        }
        """
        qs = self.filter_queryset(self.get_queryset())

        # Contagens basicas
        total_planos = qs.count()

        # Formacoes (via subquery)
        total_formacoes = Formacao.objects.filter(
            plano__in=qs,
            data_formacao__isnull=False
        ).count()

        total_realizadas = Formacao.objects.filter(
            plano__in=qs,
            realizada=True
        ).count()

        # CH total
        ch_total = qs.aggregate(total=Sum("ch_anual"))["total"] or 0

        # Por projeto (top 10)
        por_projeto = list(
            qs.values("projeto__nome")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        # Por UF
        por_uf = list(
            qs.values("municipio__uf")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # Por coordenador (top 10)
        por_coordenador = list(
            qs.exclude(coordenador__isnull=True)
            .values("coordenador__nome")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        # Municipios distintos
        total_municipios = qs.values("municipio").distinct().count()

        return Response({
            "total_planos": total_planos,
            "total_formacoes": total_formacoes,
            "total_realizadas": total_realizadas,
            "taxa_realizacao": round(
                (total_realizadas / total_formacoes * 100) if total_formacoes > 0 else 0, 1
            ),
            "ch_total": float(ch_total),
            "total_municipios": total_municipios,
            "por_projeto": por_projeto,
            "por_uf": por_uf,
            "por_coordenador": por_coordenador,
        })

    @action(detail=False, methods=["get"], permission_classes=[IsDATOrSuper])
    def calendario(self, request: Request) -> Response:
        """
        Dados para visualizacao de calendario.

        GET /api/dat/plano-formacoes/calendario/?data_inicio=2025-01-01&data_fim=2025-12-31

        Returns: Lista de formacoes com data agendada
        """
        qs = self.filter_queryset(self.get_queryset())

        data_inicio = request.query_params.get("data_inicio")
        data_fim = request.query_params.get("data_fim")

        formacoes_qs = Formacao.objects.filter(
            plano__in=qs,
            data_formacao__isnull=False
        ).select_related("plano__municipio", "plano__projeto")

        if data_inicio:
            formacoes_qs = formacoes_qs.filter(data_formacao__gte=data_inicio)
        if data_fim:
            formacoes_qs = formacoes_qs.filter(data_formacao__lte=data_fim)

        formacoes_qs = formacoes_qs.order_by("data_formacao")

        eventos = [
            {
                "id": f.id,
                "plano_id": f.plano_id,
                "municipio": f.plano.municipio.nome,
                "projeto": f.plano.projeto.nome,
                "numero": f.numero_formacao,
                "data": f.data_formacao.isoformat(),
                "ch": float(f.carga_horaria),
                "modalidade": f.modalidade,
                "realizada": f.realizada,
                "status": f.status,
            }
            for f in formacoes_qs
        ]

        return Response(eventos)

    @action(detail=False, methods=["get"], permission_classes=[IsDATOrSuper], url_path="resumo-projeto")
    def resumo_projeto(self, request: Request) -> Response:
        """
        Resumo agregado por projeto.

        GET /api/dat/plano-formacoes/resumo-projeto/

        Returns: Lista de projetos com totais
        """
        qs = self.filter_queryset(self.get_queryset())

        resumo = []
        projetos = qs.values("projeto__id", "projeto__nome").distinct()

        for proj in projetos:
            planos_projeto = qs.filter(projeto_id=proj["projeto__id"])
            total_planos = planos_projeto.count()

            formacoes = Formacao.objects.filter(
                plano__in=planos_projeto,
                data_formacao__isnull=False
            )
            total_formacoes = formacoes.count()
            realizadas = formacoes.filter(realizada=True).count()

            ch_total = planos_projeto.aggregate(total=Sum("ch_anual"))["total"] or 0

            coordenadores = list(
                planos_projeto.exclude(coordenador__isnull=True)
                .values_list("coordenador__nome", flat=True)
                .distinct()
            )

            resumo.append({
                "projeto_id": proj["projeto__id"],
                "projeto_nome": proj["projeto__nome"],
                "total_planos": total_planos,
                "total_municipios": planos_projeto.values("municipio").distinct().count(),
                "total_formacoes": total_formacoes,
                "formacoes_realizadas": realizadas,
                "taxa_realizacao": round(
                    (realizadas / total_formacoes * 100) if total_formacoes > 0 else 0, 1
                ),
                "ch_total": float(ch_total),
                "coordenadores": coordenadores,
            })

        resumo.sort(key=lambda x: x["projeto_nome"])
        return Response(resumo)

    @action(
        detail=True,
        methods=["patch"],
        url_path=r"formacao/(?P<numero>\d+)",
        permission_classes=[IsDATOrSuper]
    )
    def update_formacao(
        self, request: Request, pk: int | None = None, numero: str | None = None
    ) -> Response:
        """
        Atualiza uma formacao especifica inline.

        PATCH /api/dat/plano-formacoes/{id}/formacao/{numero}/

        Body: { data_formacao, carga_horaria, modalidade, realizada, ... }
        """
        plano = self.get_object()

        try:
            formacao = plano.formacoes.get(numero_formacao=int(numero))
        except Formacao.DoesNotExist:
            return Response(
                {"detail": f"Formacao {numero} nao encontrada."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = FormacaoSerializer(formacao, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Recalcular CH do plano
        plano.recalcular_ch()
        plano.save()

        return Response(serializer.data)

    @action(
        detail=True,
        methods=["patch"],
        url_path=r"acompanhamento/(?P<tipo>\w+)",
        permission_classes=[IsDATOrSuper]
    )
    def update_acompanhamento(
        self, request: Request, pk: int | None = None, tipo: str | None = None
    ) -> Response:
        """
        Atualiza um acompanhamento especifico inline.

        PATCH /api/dat/plano-formacoes/{id}/acompanhamento/{tipo}/
        tipo: 'primeiro' ou 'segundo'

        Body: { data_acompanhamento, realizado, observacoes }
        """
        plano = self.get_object()

        try:
            acompanhamento = plano.acompanhamentos.get(tipo=tipo)
        except Acompanhamento.DoesNotExist:
            return Response(
                {"detail": f"Acompanhamento '{tipo}' nao encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = AcompanhamentoSerializer(acompanhamento, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    @action(
        detail=True,
        methods=["patch"],
        url_path=r"prova/(?P<numero>\d+)",
        permission_classes=[IsDATOrSuper]
    )
    def update_prova(
        self, request: Request, pk: int | None = None, numero: str | None = None
    ) -> Response:
        """
        Atualiza uma prova especifica inline.

        PATCH /api/dat/plano-formacoes/{id}/prova/{numero}/

        Body: { data_prova, realizada, observacoes }
        """
        plano = self.get_object()

        try:
            prova = plano.provas.get(numero_prova=int(numero))
        except Prova.DoesNotExist:
            return Response(
                {"detail": f"Prova {numero} nao encontrada."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ProvaSerializer(prova, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

"""
AS v2 — DAT Module ViewSets

ViewSets para DATArea, DATCoordenador, DATAcao, DATCompra, DATCadastro, DATFormacao.

Endpoints:
    - /api/dat/areas/ (ReadOnly)
    - /api/dat/coordenadores/ (CRUD + alocacoes)
    - /api/dat/acoes/ (CRUD + stats)
    - /api/dat/compras/ (CRUD + stats)
    - /api/dat/cadastros/ (CRUD + stats + etapa)
    - /api/dat/formacoes/ (CRUD + stats + calendario)

Type-checked with Pyright (strict mode).
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.db.models import Count, Exists, F, Max, OuterRef, Q, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend

from apps.core.models import (
    Compra,
    DATAcao,
    DATArea,
    DATCadastro,
    DATCompra,
    DATCoordenador,
    DATFormacao,
    MunicipioReferencia,
    Solicitacao,
)
from apps.core.permissions import IsComprasDashboardAccess, IsDATOrSuper, IsSuperintendenciaOnly
from apps.core.serializers import (
    DATAcaoListSerializer,
    DATAcaoSerializer,
    DATAreaOptionSerializer,
    DATAreaSerializer,
    DATCadastroListSerializer,
    DATCadastroSerializer,
    DATCompraListSerializer,
    DATCompraSerializer,
    DATCoordenadorListSerializer,
    DATCoordenadorOptionSerializer,
    DATCoordenadorSerializer,
    DATFormacaoCalendarioSerializer,
    DATFormacaoListSerializer,
    DATFormacaoSerializer,
)

if TYPE_CHECKING:
    from rest_framework.request import Request


# ============================================================
# DATArea ViewSet
# ============================================================


class DATAreaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet ReadOnly para DATArea (tabela de referência).

    Endpoints:
        - GET /api/dat/areas/ - Listar áreas
        - GET /api/dat/areas/{id}/ - Detalhe

    Permissões: Qualquer usuário autenticado
    """

    queryset = DATArea.objects.filter(ativo=True).order_by("ordem", "nome")
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Return appropriate serializer."""
        if self.request.query_params.get("minimal") == "true":
            return DATAreaOptionSerializer
        return DATAreaSerializer


# ============================================================
# DATCoordenador ViewSet
# ============================================================


class DATCoordenadorFilter(filters.FilterSet):
    """FilterSet para DATCoordenador."""

    area = filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = DATCoordenador
        fields = ["area", "ativo"]


class DATCoordenadorViewSet(viewsets.ModelViewSet):
    """
    ViewSet para CRUD de Coordenadores DAT.

    Endpoints:
        - GET /api/dat/coordenadores/ - Listar
        - POST /api/dat/coordenadores/ - Criar
        - GET /api/dat/coordenadores/{id}/ - Detalhe
        - PATCH /api/dat/coordenadores/{id}/ - Atualizar
        - DELETE /api/dat/coordenadores/{id}/ - Excluir (Superintendência only)
        - GET /api/dat/coordenadores/{id}/alocacoes/ - Ver alocações

    Permissões:
        - list, retrieve: DAT ou Superintendência
        - create, update: DAT ou Superintendência
        - destroy: apenas Superintendência
    """

    queryset = DATCoordenador.objects.select_related("created_by", "updated_by").order_by("nome")

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = DATCoordenadorFilter
    search_fields = ["nome", "email", "area", "cargo"]
    ordering_fields = ["nome", "area", "created_at"]
    ordering = ["nome"]

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == "list":
            if self.request.query_params.get("minimal") == "true":
                return DATCoordenadorOptionSerializer
            return DATCoordenadorListSerializer
        return DATCoordenadorSerializer

    def get_permissions(self):
        """Permissões baseadas na ação."""
        if self.action == "destroy":
            return [IsSuperintendenciaOnly()]
        if self.action in {"dashboard", "pendencias"}:
            return [IsComprasDashboardAccess()]
        return [IsDATOrSuper()]

    def perform_create(self, serializer: Any) -> None:
        """Set created_by on create."""
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer: Any) -> None:
        """Set updated_by on update."""
        serializer.save(updated_by=self.request.user)

    @action(detail=True, methods=["get"], permission_classes=[IsDATOrSuper])
    def alocacoes(self, request: Request, pk: int | None = None) -> Response:
        """
        Lista alocações (ações e formações) do coordenador.

        GET /api/dat/coordenadores/{id}/alocacoes/

        Returns: {acoes: [...], formacoes: [...]}
        """
        coordenador = self.get_object()

        acoes = DATAcaoListSerializer(coordenador.dat_acoes.filter(ativo=True)[:10], many=True).data

        formacoes = DATFormacaoListSerializer(coordenador.dat_formacoes.filter(ativo=True)[:10], many=True).data

        return Response(
            {
                "acoes": acoes,
                "formacoes": formacoes,
                "total_acoes": coordenador.dat_acoes.filter(ativo=True).count(),
                "total_formacoes": coordenador.dat_formacoes.filter(ativo=True).count(),
            }
        )


# ============================================================
# DATAcao ViewSet
# ============================================================


class DATAcaoFilter(filters.FilterSet):
    """FilterSet para DATAcao."""

    uf = filters.CharFilter(field_name="municipio__uf", lookup_expr="iexact")

    class Meta:
        model = DATAcao
        fields = [
            "municipio",
            "projeto",
            "coordenador",
            "status_carta",
            "status_contato",
            "status_reuniao",
            "status_entrega",
            "ativo",
            "uf",
        ]


class DATAcaoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para CRUD de Ações DAT.

    Endpoints:
        - GET /api/dat/acoes/ - Listar
        - POST /api/dat/acoes/ - Criar
        - GET /api/dat/acoes/{id}/ - Detalhe
        - PATCH /api/dat/acoes/{id}/ - Atualizar
        - DELETE /api/dat/acoes/{id}/ - Excluir (Superintendência only)
        - GET /api/dat/acoes/stats/ - Estatísticas

    Permissões:
        - list, retrieve, stats: DAT ou Superintendência
        - create, update: DAT ou Superintendência
        - destroy: apenas Superintendência
    """

    queryset = DATAcao.objects.select_related("municipio", "projeto", "coordenador", "created_by").order_by(
        "-prioridade", "municipio__nome"
    )

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = DATAcaoFilter
    search_fields = ["municipio__nome", "projeto__nome", "coordenador__nome"]
    ordering_fields = ["municipio__nome", "projeto__nome", "prioridade", "created_at"]
    ordering = ["-prioridade", "municipio__nome"]

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == "list":
            return DATAcaoListSerializer
        return DATAcaoSerializer

    def get_permissions(self):
        """Permissões baseadas na ação."""
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
        Estatísticas agregadas das ações.

        GET /api/dat/acoes/stats/

        Returns: {
            total, por_etapa, por_projeto, por_coordenador
        }
        """
        qs = self.filter_queryset(self.get_queryset())

        total = qs.count()

        # Por status de cada etapa
        por_etapa = {
            "carta": dict(qs.values_list("status_carta").annotate(c=Count("id"))),
            "contato": dict(qs.values_list("status_contato").annotate(c=Count("id"))),
            "reuniao": dict(qs.values_list("status_reuniao").annotate(c=Count("id"))),
            "entrega": dict(qs.values_list("status_entrega").annotate(c=Count("id"))),
        }

        # Por projeto (top 10)
        por_projeto = list(qs.values("projeto__nome").annotate(count=Count("id")).order_by("-count")[:10])

        # Por coordenador (top 10)
        por_coordenador = list(
            qs.filter(coordenador__isnull=False)
            .values("coordenador__nome")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        return Response(
            {
                "total": total,
                "por_etapa": por_etapa,
                "por_projeto": por_projeto,
                "por_coordenador": por_coordenador,
            }
        )


# ============================================================
# DATCompra ViewSet
# ============================================================


class DATCompraFilter(filters.FilterSet):
    """FilterSet para DATCompra."""

    uf = filters.CharFilter(field_name="municipio__uf", lookup_expr="iexact")
    ano_min = filters.NumberFilter(field_name="ano_uso", lookup_expr="gte")
    ano_max = filters.NumberFilter(field_name="ano_uso", lookup_expr="lte")
    municipio_id = filters.NumberFilter(field_name="municipio_id")
    projeto_id = filters.NumberFilter(field_name="projeto_id")
    produto_id = filters.NumberFilter(field_name="produto_id")

    class Meta:
        model = DATCompra
        fields = [
            "municipio",
            "projeto",
            "produto",
            "ano_uso",
            "status_uso",
            "tipo_compra",
            "ativo",
            "uf",
        ]


class DATCompraViewSet(viewsets.ModelViewSet):
    """
    ViewSet para CRUD de Compras DAT.

    Endpoints:
        - GET /api/dat/compras/ - Listar
        - POST /api/dat/compras/ - Criar
        - GET /api/dat/compras/{id}/ - Detalhe
        - PATCH /api/dat/compras/{id}/ - Atualizar
        - DELETE /api/dat/compras/{id}/ - Excluir (Superintendência only)
        - GET /api/dat/compras/stats/ - Estatísticas

    Permissões:
        - list, retrieve, stats: DAT ou Superintendência
        - create, update: DAT ou Superintendência
        - destroy: apenas Superintendência
    """

    queryset = DATCompra.objects.select_related("municipio", "projeto", "produto", "created_by").order_by(
        "-ano_uso", "municipio__nome"
    )

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = DATCompraFilter
    search_fields = [
        "municipio__nome",
        "projeto__nome",
        "produto__nome",
        "descricao_produto",
    ]
    ordering_fields = ["municipio__nome", "ano_uso", "valor_unitario", "created_at"]
    ordering = ["-ano_uso", "municipio__nome"]

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == "list":
            return DATCompraListSerializer
        return DATCompraSerializer

    def get_permissions(self):
        """Permissões baseadas na ação."""
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
        Estatísticas agregadas das compras.

        GET /api/dat/compras/stats/

        Returns: {
            total, valor_total, por_status, por_ano, por_projeto
        }
        """
        qs = self.filter_queryset(self.get_queryset())

        total = qs.count()
        valor_total = qs.aggregate(total=Sum(F("valor_unitario") * F("quantidade")))["total"] or 0

        # Por status de uso
        por_status = dict(qs.values_list("status_uso").annotate(c=Count("id")))

        # Por ano (últimos 5)
        por_ano = list(qs.values("ano_uso").annotate(count=Count("id")).order_by("-ano_uso")[:5])

        # Por projeto (top 10)
        por_projeto = list(qs.values("projeto__nome").annotate(count=Count("id")).order_by("-count")[:10])

        return Response(
            {
                "total": total,
                "valor_total": valor_total,
                "por_status": por_status,
                "por_ano": por_ano,
                "por_projeto": por_projeto,
            }
        )

    @action(detail=False, methods=["get"], permission_classes=[IsComprasDashboardAccess])
    def dashboard(self, request: Request) -> Response:
        """
        Dashboard de compras com métricas agregadas.

        GET /api/dat/compras-materiais/dashboard/

        Returns:
            {
                "kpis": {...},
                "por_colecao": [...],
                "top_produtos": [...],
                "top_municipios": [...],
                "top_frequencia": [...],
                "por_ano": [...],
                "por_tipo_compra": [...]
            }
        """
        qs = self.filter_queryset(self.get_queryset())

        total_itens = qs.aggregate(total=Sum("quantidade"))["total"] or 0
        total_entregue = qs.aggregate(total=Sum("quantidade_utilizada"))["total"] or 0
        total_disponivel = (
            qs.aggregate(total=Sum(F("quantidade") - Coalesce(F("quantidade_utilizada"), 0)))["total"] or 0
        )

        municipios_atendidos = qs.values("municipio_id").distinct().count()
        total_municipios_referencia = MunicipioReferencia.objects.filter(ativo=True).count()
        cobertura_percentual = (
            round((municipios_atendidos / total_municipios_referencia) * 100, 1)
            if total_municipios_referencia > 0
            else 0
        )
        produtos_diferentes = qs.values("produto_id").distinct().count()
        colecoes_diferentes = qs.exclude(produto__colecao__isnull=True).values("produto__colecao_id").distinct().count()
        valor_total = qs.aggregate(total=Sum(F("valor_unitario") * F("quantidade")))["total"] or 0

        colecao_raw = (
            qs.annotate(colecao_nome=Coalesce("produto__colecao__nome", Value("Sem coleção")))
            .values("colecao_nome")
            .annotate(quantidade=Sum("quantidade"))
            .order_by("-quantidade")
        )
        por_colecao = []
        for item in colecao_raw[:10]:
            quantidade = item["quantidade"] or 0
            por_colecao.append(
                {
                    "colecao": item["colecao_nome"],
                    "quantidade": quantidade,
                    "percentual": round((quantidade / total_itens * 100) if total_itens > 0 else 0, 1),
                }
            )

        produtos_raw = (
            qs.annotate(produto_nome=Coalesce("produto__nome", "descricao_produto", Value("Sem produto")))
            .values("produto_nome")
            .annotate(quantidade=Sum("quantidade"))
            .order_by("-quantidade")
        )
        top_produtos = []
        for item in produtos_raw[:10]:
            quantidade = item["quantidade"] or 0
            top_produtos.append(
                {
                    "produto": item["produto_nome"],
                    "quantidade": quantidade,
                    "percentual": round((quantidade / total_itens * 100) if total_itens > 0 else 0, 1),
                }
            )

        municipios_raw = (
            qs.values("municipio__nome", "municipio__uf")
            .annotate(quantidade=Sum("quantidade"), compras=Count("id"), entregues=Sum("quantidade_utilizada"))
            .order_by("-quantidade", "-compras")
        )
        top_municipios = [
            {
                "municipio": item["municipio__nome"],
                "uf": item["municipio__uf"],
                "quantidade": item["quantidade"] or 0,
                "compras": item["compras"],
                "entregues": item["entregues"] or 0,
            }
            for item in municipios_raw[:10]
        ]

        frequencia_raw = (
            qs.values("municipio__nome", "municipio__uf")
            .annotate(compras=Count("id"), quantidade=Sum("quantidade"))
            .order_by("-compras", "-quantidade")
        )
        top_frequencia = [
            {
                "municipio": item["municipio__nome"],
                "uf": item["municipio__uf"],
                "compras": item["compras"],
                "quantidade": item["quantidade"] or 0,
            }
            for item in frequencia_raw[:10]
        ]

        por_ano = list(qs.values("ano_uso").annotate(quantidade=Sum("quantidade")).order_by("-ano_uso")[:6])

        tipo_labels = {
            "primeira": "Primeira compra",
            "adicional_1": "Compra adicional 1",
            "adicional_2": "Compra adicional 2",
            "adicional_3": "Compra adicional 3",
            None: "Não informado",
        }
        tipo_raw = qs.values("tipo_compra").annotate(quantidade=Sum("quantidade")).order_by("-quantidade")
        por_tipo_compra = [
            {
                "tipo_compra": tipo_labels.get(item["tipo_compra"], item["tipo_compra"] or "Não informado"),
                "quantidade": item["quantidade"] or 0,
            }
            for item in tipo_raw
        ]

        return Response(
            {
                "kpis": {
                    "municipios_atendidos": municipios_atendidos,
                    "total_municipios_referencia": total_municipios_referencia,
                    "cobertura_percentual": cobertura_percentual,
                    "total_itens": total_itens,
                    "total_entregue": total_entregue,
                    "total_disponivel": total_disponivel,
                    "produtos_diferentes": produtos_diferentes,
                    "colecoes_diferentes": colecoes_diferentes,
                    "valor_total": valor_total,
                },
                "por_colecao": por_colecao,
                "top_produtos": top_produtos,
                "top_municipios": top_municipios,
                "top_frequencia": top_frequencia,
                "por_ano": por_ano,
                "por_tipo_compra": por_tipo_compra,
            }
        )

    @action(detail=False, methods=["get"], permission_classes=[IsComprasDashboardAccess])
    def pendencias(self, request: Request) -> Response:
        """
        Municípios com compra no domínio core_compra e sem solicitação ativa.

        A pendência é calculada por par (município + projeto) para refletir
        a regra de negócio da operação.

        GET /api/dat/compras-materiais/pendencias/
        Query params opcionais:
            - uf: filtra por UF
            - projeto_id: filtra por projeto
        """
        compras_qs = Compra.objects.select_related("municipio", "projeto")

        uf = request.query_params.get("uf")
        projeto_id = request.query_params.get("projeto_id")

        if uf:
            compras_qs = compras_qs.filter(municipio__uf__iexact=uf)
        if projeto_id:
            compras_qs = compras_qs.filter(projeto_id=projeto_id)

        solicitacoes_ativas = Solicitacao.objects.filter(
            municipio_id=OuterRef("municipio_id"),
            projeto_id=OuterRef("projeto_id"),
            status__in=["pendente", "aprovado"],
        )

        base_pairs = (
            compras_qs.values(
                "municipio_id",
                "municipio__nome",
                "municipio__uf",
                "projeto_id",
                "projeto__nome",
            )
            .annotate(
                total_itens=Sum("quantidade"),
                total_compras=Count("id"),
                ultima_compra=Max("data"),
                possui_evento=Exists(solicitacoes_ativas),
            )
            .order_by("municipio__nome", "projeto__nome")
        )

        total_com_compra = base_pairs.count()
        total_com_evento = base_pairs.filter(possui_evento=True).count()
        pendentes_pairs = base_pairs.filter(possui_evento=False)
        total_pendentes = pendentes_pairs.count()
        percentual_pendentes = round((total_pendentes / total_com_compra) * 100, 1) if total_com_compra > 0 else 0

        pendentes = [
            {
                "municipio_id": item["municipio_id"],
                "municipio": item["municipio__nome"],
                "uf": item["municipio__uf"],
                "projeto_id": item["projeto_id"],
                "projeto": item["projeto__nome"],
                "total_itens": item["total_itens"] or 0,
                "total_compras": item["total_compras"],
                "ultima_compra": item["ultima_compra"],
            }
            for item in pendentes_pairs
        ]

        return Response(
            {
                "total_com_compra": total_com_compra,
                "total_com_evento": total_com_evento,
                "total_pendentes": total_pendentes,
                "percentual_pendentes": percentual_pendentes,
                "pendentes": pendentes,
            }
        )


# ============================================================
# DATCadastro ViewSet
# ============================================================


class DATCadastroFilter(filters.FilterSet):
    """FilterSet para DATCadastro."""

    uf = filters.CharFilter(field_name="municipio__uf", lookup_expr="iexact")

    class Meta:
        model = DATCadastro
        fields = [
            "municipio",
            "projeto_geral",
            "plataforma",
            "status_criacao_curso",
            "status_chaves",
            "status_instrucoes",
            "status_envio",
            "status_recebidos",
            "status_validados",
            "status_importados",
            "ativo",
            "uf",
        ]


class DATCadastroViewSet(viewsets.ModelViewSet):
    """
    ViewSet para CRUD de Cadastros DAT (FORMAR/AVALIAR).

    Endpoints:
        - GET /api/dat/cadastros/ - Listar
        - POST /api/dat/cadastros/ - Criar
        - GET /api/dat/cadastros/{id}/ - Detalhe
        - PATCH /api/dat/cadastros/{id}/ - Atualizar
        - DELETE /api/dat/cadastros/{id}/ - Excluir (Superintendência only)
        - GET /api/dat/cadastros/stats/ - Estatísticas
        - POST /api/dat/cadastros/{id}/etapa/ - Atualizar etapa específica

    Permissões:
        - list, retrieve, stats: DAT ou Superintendência
        - create, update, etapa: DAT ou Superintendência
        - destroy: apenas Superintendência
    """

    queryset = DATCadastro.objects.select_related("municipio", "projeto_geral", "created_by").order_by(
        "plataforma", "municipio__nome"
    )

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = DATCadastroFilter
    search_fields = ["municipio__nome", "projeto_geral__nome"]
    ordering_fields = ["municipio__nome", "projeto_geral__nome", "plataforma", "created_at"]
    ordering = ["plataforma", "municipio__nome"]

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == "list":
            return DATCadastroListSerializer
        return DATCadastroSerializer

    def get_permissions(self):
        """Permissões baseadas na ação."""
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
        Estatísticas agregadas dos cadastros.

        GET /api/dat/cadastros/stats/

        Returns: {
            total, por_plataforma, formar_completos, avaliar_completos
        }
        """
        qs = self.filter_queryset(self.get_queryset())

        total = qs.count()

        # Por plataforma
        por_plataforma = dict(qs.values_list("plataforma").annotate(c=Count("id")))

        # FORMAR completos
        formar_completos = qs.filter(
            plataforma="FORMAR",
            status_criacao_curso="concluido",
            status_chaves="concluido",
            status_instrucoes="concluido",
            status_envio="concluido",
        ).count()

        # AVALIAR completos
        avaliar_completos = qs.filter(
            plataforma="AVALIAR",
            status_recebidos="concluido",
            status_validados="concluido",
            status_importados="concluido",
        ).count()

        # Por projeto geral (top 10)
        por_projeto = list(qs.values("projeto_geral__nome").annotate(count=Count("id")).order_by("-count")[:10])

        return Response(
            {
                "total": total,
                "por_plataforma": por_plataforma,
                "formar_completos": formar_completos,
                "avaliar_completos": avaliar_completos,
                "por_projeto": por_projeto,
            }
        )

    @action(detail=True, methods=["post"], permission_classes=[IsDATOrSuper])
    def etapa(self, request: Request, pk: int | None = None) -> Response:
        """
        Atualiza uma etapa específica do cadastro.

        POST /api/dat/cadastros/{id}/etapa/
        Body: {etapa: "chaves", status: "concluido", data: "2025-01-15"}

        Etapas FORMAR: criacao_curso, chaves, instrucoes, envio
        Etapas AVALIAR: recebidos, validados, importados
        """
        cadastro = self.get_object()
        etapa = request.data.get("etapa")
        novo_status = request.data.get("status")
        data = request.data.get("data")

        etapas_validas = {
            "criacao_curso": ("status_criacao_curso", "data_criacao_curso"),
            "chaves": ("status_chaves", "data_chaves"),
            "instrucoes": ("status_instrucoes", "data_instrucoes"),
            "envio": ("status_envio", "data_envio"),
            "recebidos": ("status_recebidos", "data_recebidos"),
            "validados": ("status_validados", "data_validados"),
            "importados": ("status_importados", "data_importados"),
        }

        if etapa not in etapas_validas:
            return Response(
                {"error": f"Etapa inválida. Válidas: {list(etapas_validas.keys())}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        campo_status, campo_data = etapas_validas[etapa]

        if novo_status:
            setattr(cadastro, campo_status, novo_status)
        if data:
            setattr(cadastro, campo_data, data)

        cadastro.updated_by = request.user
        cadastro.save()

        return Response(DATCadastroSerializer(cadastro).data)


# ============================================================
# DATFormacao ViewSet
# ============================================================


class DATFormacaoFilter(filters.FilterSet):
    """FilterSet para DATFormacao."""

    uf = filters.CharFilter(field_name="municipio__uf", lookup_expr="iexact")
    data_inicio = filters.DateFilter(field_name="data_formacao", lookup_expr="gte")
    data_fim = filters.DateFilter(field_name="data_formacao", lookup_expr="lte")

    class Meta:
        model = DATFormacao
        fields = [
            "municipio",
            "projeto",
            "coordenador",
            "modalidade",
            "status",
            "ativo",
            "uf",
        ]


class DATFormacaoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para CRUD de Formações DAT.

    Endpoints:
        - GET /api/dat/formacoes/ - Listar
        - POST /api/dat/formacoes/ - Criar
        - GET /api/dat/formacoes/{id}/ - Detalhe
        - PATCH /api/dat/formacoes/{id}/ - Atualizar
        - DELETE /api/dat/formacoes/{id}/ - Excluir (Superintendência only)
        - GET /api/dat/formacoes/stats/ - Estatísticas
        - GET /api/dat/formacoes/calendario/ - Dados para calendário

    Permissões:
        - list, retrieve, stats, calendario: DAT ou Superintendência
        - create, update: DAT ou Superintendência
        - destroy: apenas Superintendência
    """

    queryset = DATFormacao.objects.select_related("municipio", "projeto", "coordenador", "created_by").order_by(
        "-data_formacao", "horario_inicio"
    )

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = DATFormacaoFilter
    search_fields = ["titulo", "municipio__nome", "projeto__nome", "coordenador__nome"]
    ordering_fields = ["data_formacao", "titulo", "municipio__nome", "created_at"]
    ordering = ["-data_formacao", "horario_inicio"]

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == "list":
            return DATFormacaoListSerializer
        elif self.action == "calendario":
            return DATFormacaoCalendarioSerializer
        return DATFormacaoSerializer

    def get_permissions(self):
        """Permissões baseadas na ação."""
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
        Estatísticas agregadas das formações.

        GET /api/dat/formacoes/stats/

        Returns: {
            total, por_status, por_modalidade, por_projeto, por_coordenador
        }
        """
        qs = self.filter_queryset(self.get_queryset())

        total = qs.count()

        # Por status
        por_status = dict(qs.values_list("status").annotate(c=Count("id")))

        # Por modalidade
        por_modalidade = dict(qs.values_list("modalidade").annotate(c=Count("id")))

        # Por projeto (top 10)
        por_projeto = list(qs.values("projeto__nome").annotate(count=Count("id")).order_by("-count")[:10])

        # Por coordenador (top 10)
        por_coordenador = list(
            qs.filter(coordenador__isnull=False)
            .values("coordenador__nome")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        # Participantes totais
        participantes = qs.aggregate(
            previstos=Sum("quantidade_prevista"),
            presentes=Sum("quantidade_presente"),
        )

        return Response(
            {
                "total": total,
                "por_status": por_status,
                "por_modalidade": por_modalidade,
                "por_projeto": por_projeto,
                "por_coordenador": por_coordenador,
                "participantes_previstos": participantes["previstos"] or 0,
                "participantes_presentes": participantes["presentes"] or 0,
            }
        )

    @action(detail=False, methods=["get"], permission_classes=[IsDATOrSuper])
    def calendario(self, request: Request) -> Response:
        """
        Dados otimizados para visualização em calendário.

        GET /api/dat/formacoes/calendario/
        Query params: data_inicio, data_fim (obrigatórios)

        Returns: Lista de eventos para calendário
        """
        data_inicio = request.query_params.get("data_inicio")
        data_fim = request.query_params.get("data_fim")

        if not data_inicio or not data_fim:
            return Response(
                {"error": "Parâmetros data_inicio e data_fim são obrigatórios"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = self.get_queryset().filter(
            data_formacao__gte=data_inicio,
            data_formacao__lte=data_fim,
            ativo=True,
        )

        serializer = DATFormacaoCalendarioSerializer(qs, many=True)
        return Response(serializer.data)

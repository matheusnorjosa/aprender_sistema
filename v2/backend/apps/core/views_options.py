"""
Options API Views

Provides minimal dropdown/select options for frontend forms.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db.models import Exists, OuterRef, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from drf_spectacular.utils import OpenApiParameter, extend_schema

from apps.core.services.compra_elegibilidade import isento_da_regra_da_compra, projetos_liberados

from .models import (
    DATArea,
    DATCoordenador,
    Municipio,
    PlanoFormacoes,
    Produto,
    Projeto,
    TipoEvento,
    Usuario,
)
from .serializers import (
    MunicipioOptionSerializer,
    ProdutoOptionSerializer,
    ProjetoOptionSerializer,
    TipoEventoOptionSerializer,
    UsuarioOptionSerializer,
)
from .serializers.dat_module import DATAreaOptionSerializer, DATCoordenadorOptionSerializer


@extend_schema(
    methods=["GET"],
    summary="Listar municípios para opções",
    responses=MunicipioOptionSerializer(many=True),
    tags=["options"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def municipios_options(request: Request) -> Response:
    """
    GET /api/options/municipios/

    Retorna lista de municípios ativos para dropdowns/selects.

    Response:
    [
        {"id": 1, "nome": "Fortaleza", "uf": "CE"},
        {"id": 2, "nome": "Sobral", "uf": "CE"},
        ...
    ]

    Permissions: IsAuthenticated
    Cache: 5 minutos (CP3)
    """
    # CP3: Cache manual (não usar decorator com DRF views)
    cache_key = "static_endpoint:municipios_options"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return Response(cached_data)

    # Cache miss: buscar do banco
    municipios = Municipio.objects.filter(ativo=True).order_by("nome")
    serializer = MunicipioOptionSerializer(municipios, many=True)
    data = serializer.data

    # Salvar no cache
    cache.set(cache_key, data, timeout=settings.CACHE_DEFAULT_TIMEOUT)  # 5 min

    return Response(data)


@extend_schema(
    methods=["GET"],
    summary="Listar projetos para opções",
    parameters=[
        OpenApiParameter(
            name="include_test",
            location=OpenApiParameter.QUERY,
            required=False,
            type=bool,
            description="Quando true, inclui projetos de teste.",
        ),
        OpenApiParameter(
            name="com_compra",
            location=OpenApiParameter.QUERY,
            required=False,
            type=bool,
            description='Quando true, esconde o projeto "em espera" (sem compra que o libere), salvo para quem é isento.',
        ),
    ],
    responses=ProjetoOptionSerializer(many=True),
    tags=["options"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def projetos_options(request: Request) -> Response:
    """
    GET /api/options/projetos/

    Retorna lista de projetos ativos para dropdowns/selects.

    Issue #153: Filtra is_test=False por padrão (oculta projetos de teste)
    Para incluir projetos de teste, use query param ?include_test=true

    Response:
    [
        {"id": 1, "nome": "Alfabetização", "codigo": "ALF"},
        {"id": 2, "nome": "Matemática", "codigo": "MAT"},
        ...
    ]

    `com_compra=true` (Plano Anual): esconde o projeto "em espera" pela regra única da compra
    (`services/compra_elegibilidade`), salvo para quem é isento. O filtro roda DEPOIS do cache, por
    usuário e sem cache: o projeto volta assim que a compra entra.

    Permissions: IsAuthenticated
    Cache: 5 minutos (CP3)
    """
    com_compra = request.query_params.get("com_compra", "false").lower() == "true"
    # CP3: Cache manual (não usar decorator com DRF views)
    include_test = request.query_params.get("include_test", "false").lower() == "true"
    # #1976: exclui variantes-por-série (famílias + série que já tem plano) — Plano Anual.
    exclude_kits = request.query_params.get("exclude_kits", "false").lower() == "true"
    cache_key = f"static_endpoint:projetos_options:include_test={include_test}:exclude_kits={exclude_kits}"
    data = cache.get(cache_key)
    if data is None:
        data = _projetos_options_data(include_test=include_test, exclude_kits=exclude_kits)
        cache.set(cache_key, data, timeout=settings.CACHE_DEFAULT_TIMEOUT)  # 5 min

    if com_compra and not isento_da_regra_da_compra(request.user):
        liberados = set(
            projetos_liberados(Projeto.objects.filter(pk__in=[p["id"] for p in data])).values_list("pk", flat=True)
        )
        data = [p for p in data if p["id"] in liberados]

    return Response(data)


def _projetos_options_data(*, include_test: bool, exclude_kits: bool) -> Any:
    # Filter active projects
    projetos = Projeto.objects.filter(ativo=True)

    # Issue #153: Filter out test projects by default
    if not include_test:
        projetos = projetos.filter(is_test=False)

    # #1976: exclui as séries (marca `Projeto.eh_serie`). Default off (Compras/DAT precisam das
    # variantes). Quem usa `exclude_kits=true` é o Plano Anual, então a série que JÁ TEM plano fica
    # (decisão do dono, 02/10/2026: "Projeto Catavento 2/3" seguem série e os planos deles não
    # podem sumir do filtro). O ProjetoLookup (Nova Solicitação) não tem essa exceção.
    if exclude_kits:
        tem_plano = Exists(PlanoFormacoes.objects.filter(projeto=OuterRef("pk")))
        projetos = projetos.filter(Q(eh_serie=False) | tem_plano)

    projetos = projetos.order_by("nome")

    return ProjetoOptionSerializer(projetos, many=True).data


@extend_schema(
    methods=["GET"],
    summary="Listar tipos de evento para opções",
    responses=TipoEventoOptionSerializer(many=True),
    tags=["options"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tipos_evento_options(request: Request) -> Response:
    """
    GET /api/options/tipos-evento/

    Retorna lista de tipos de evento para dropdowns/selects.

    Response:
    [
        {"id": 1, "nome": "Formação Inicial"},
        {"id": 2, "nome": "Acompanhamento"},
        ...
    ]

    Permissions: IsAuthenticated
    Cache: 5 minutos (CP3)
    """
    # CP3: Cache manual (não usar decorator com DRF views)
    cache_key = "static_endpoint:tipos_evento_options"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return Response(cached_data)

    # Cache miss: buscar do banco
    tipos = TipoEvento.objects.all().order_by("nome")
    serializer = TipoEventoOptionSerializer(tipos, many=True)
    data = serializer.data

    # Salvar no cache
    cache.set(cache_key, data, timeout=settings.CACHE_DEFAULT_TIMEOUT)  # 5 min

    return Response(data)


@extend_schema(
    methods=["GET"],
    summary="Listar usuários para opções",
    responses=UsuarioOptionSerializer(many=True),
    tags=["options"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def usuarios_options(request: Request) -> Response:
    """
    GET /api/options/usuarios/

    Retorna lista de usuários ativos para dropdowns/selects (coordenadores, formadores).

    Response:
    [
        {"id": 1, "first_name": "João", "last_name": "Silva", "email": "joao@example.com"},
        ...
    ]

    Permissions: IsAuthenticated
    Cache: 5 minutos (CP5 - Issue #164)
    """
    # CP5: Cache manual (otimização autocomplete)
    cache_key = "static_endpoint:usuarios_options"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return Response(cached_data)

    # Cache miss: buscar do banco
    usuarios = Usuario.objects.filter(is_active=True).order_by("first_name", "last_name")
    serializer = UsuarioOptionSerializer(usuarios, many=True)
    data = serializer.data

    # Salvar no cache
    cache.set(cache_key, data, timeout=settings.CACHE_DEFAULT_TIMEOUT)  # 5 min

    return Response(data)


@extend_schema(
    methods=["GET"],
    summary="Listar produtos para opções",
    responses=ProdutoOptionSerializer(many=True),
    tags=["options"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def produtos_options(request: Request) -> Response:
    """
    GET /api/options/produtos/

    Retorna lista de produtos ativos para dropdowns/selects.

    Response:
    [
        {"id": 1, "nome": "Kit Alfabetização", "codigo": "KIT-ALF"},
        ...
    ]

    Permissions: IsAuthenticated
    Cache: 5 minutos
    """
    cache_key = "static_endpoint:produtos_options"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return Response(cached_data)

    produtos = Produto.objects.filter(ativo=True).order_by("nome")
    serializer = ProdutoOptionSerializer(produtos, many=True)
    data = serializer.data

    cache.set(cache_key, data, timeout=settings.CACHE_DEFAULT_TIMEOUT)
    return Response(data)


@extend_schema(
    methods=["GET"],
    summary="Listar coordenadores para opções",
    responses=DATCoordenadorOptionSerializer(many=True),
    tags=["options"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def coordenadores_options(request: Request) -> Response:
    """
    GET /api/options/coordenadores/

    Retorna lista de coordenadores DAT para dropdowns/selects.

    Response:
    [
        {"id": 1, "nome": "Maria Silva", "area_nome": "Formação"},
        ...
    ]

    Permissions: IsAuthenticated
    Cache: 5 minutos
    """
    cache_key = "static_endpoint:coordenadores_options"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return Response(cached_data)

    coordenadores = DATCoordenador.objects.all().order_by("nome")
    serializer = DATCoordenadorOptionSerializer(coordenadores, many=True)
    data = serializer.data

    cache.set(cache_key, data, timeout=settings.CACHE_DEFAULT_TIMEOUT)
    return Response(data)


@extend_schema(
    methods=["GET"],
    summary="Listar áreas DAT para opções",
    responses=DATAreaOptionSerializer(many=True),
    tags=["options"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def areas_options(request: Request) -> Response:
    """
    GET /api/options/areas/

    Retorna lista de áreas DAT para dropdowns/selects.

    Response:
    [
        {"id": 1, "nome": "Formação", "cor": "#FF5733"},
        ...
    ]

    Permissions: IsAuthenticated
    Cache: 5 minutos
    """
    cache_key = "static_endpoint:areas_options"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return Response(cached_data)

    areas = DATArea.objects.all().order_by("ordem", "nome")
    serializer = DATAreaOptionSerializer(areas, many=True)
    data = serializer.data

    cache.set(cache_key, data, timeout=settings.CACHE_DEFAULT_TIMEOUT)
    return Response(data)


@extend_schema(
    methods=["GET"],
    summary="Listar formadores do setor para opções",
    responses=UsuarioOptionSerializer(many=True),
    tags=["options"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def formadores_do_setor_options(request: Request) -> Response:
    """
    GET /api/options/formadores-do-setor/

    Retorna os formadores que o usuário logado pode escolher (regra em `formadores_do_setor`).

    Lógica:
    - Superusers: veem todos os formadores e coordenadores
    - Controle, DAT e Superintendência: formadores de todas as gerências ativas
    - Demais: formadores das gerências onde têm papel G/C/A vigente (PR 9)

    Response:
    [
        {"id": 1, "first_name": "João", "last_name": "Silva", "email": "joao@example.com"},
        ...
    ]

    Permissions: IsAuthenticated
    Cache: Não aplicável (resultado varia por usuário)
    """
    serializer = UsuarioOptionSerializer(formadores_do_setor(request.user), many=True)
    return Response(serializer.data)


def formadores_do_setor(user: Any) -> Any:
    """Usuários ativos de `/api/options/formadores-do-setor/` (também a lista de quem delega deslocamento
    de qualquer um, `DeslocamentoViewSet.alvos`).

    Superuser: formadores e coordenadores vigentes. Controle, DAT e Superintendência
    (`tem_capacidade_global`): os formadores de todas as gerências ativas (PR 9). Demais: os formadores
    das gerências onde a pessoa tem papel G/C/A vigente (`gerencias_de_atuacao`); formadora sem papel
    de gestão recebe a lista vazia.
    """
    from .models import EquipeGerencia
    from .services.solicitacao_scope import tem_capacidade_global

    # Superusers veem todos os formadores e coordenadores
    if user.is_superuser:
        user_ids = (
            EquipeGerencia.vigentes_com_escopo_em()
            .filter(papel__in=["FORMADOR", "COORDENADOR"])
            .values_list("usuario_id", flat=True)
            .distinct()
        )
        return Usuario.objects.filter(id__in=user_ids, is_active=True).order_by("first_name", "last_name")

    formadores = EquipeGerencia.vigentes_em().filter(papel="FORMADOR", gerencia__ativo=True)
    if not tem_capacidade_global(user):
        formadores = formadores.filter(gerencia_id__in=EquipeGerencia.gerencias_de_atuacao(user))
    return Usuario.objects.filter(id__in=formadores.values("usuario_id"), is_active=True).order_by(
        "first_name", "last_name"
    )

"""
Options API Views

Provides minimal dropdown/select options for frontend forms.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.cache import cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from .models import DATArea, DATCoordenador, Municipio, Produto, Projeto, TipoEvento, Usuario
from .serializers import (
    MunicipioOptionSerializer,
    ProdutoOptionSerializer,
    ProjetoOptionSerializer,
    TipoEventoOptionSerializer,
    UsuarioOptionSerializer,
)
from .serializers.dat_module import DATAreaOptionSerializer, DATCoordenadorOptionSerializer


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

    Permissions: IsAuthenticated
    Cache: 5 minutos (CP3)
    """
    # CP3: Cache manual (não usar decorator com DRF views)
    include_test = request.query_params.get("include_test", "false").lower() == "true"
    cache_key = f"static_endpoint:projetos_options:include_test={include_test}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return Response(cached_data)

    # Cache miss: buscar do banco
    # Filter active projects
    projetos = Projeto.objects.filter(ativo=True)

    # Issue #153: Filter out test projects by default
    if not include_test:
        projetos = projetos.filter(is_test=False)

    projetos = projetos.order_by("nome")

    serializer = ProjetoOptionSerializer(projetos, many=True)
    data = serializer.data

    # Salvar no cache
    cache.set(cache_key, data, timeout=settings.CACHE_DEFAULT_TIMEOUT)  # 5 min

    return Response(data)


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

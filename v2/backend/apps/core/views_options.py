"""
Options API Views

Provides minimal dropdown/select options for frontend forms.
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations
from typing import Any
from rest_framework.request import Request
from rest_framework.response import Response

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Municipio, Projeto, TipoEvento, Usuario
from .serializers import (
    MunicipioOptionSerializer,
    ProjetoOptionSerializer,
    TipoEventoOptionSerializer,
    UsuarioOptionSerializer,
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
    """
    municipios = Municipio.objects.filter(ativo=True).order_by("nome")
    serializer = MunicipioOptionSerializer(municipios, many=True)
    return Response(serializer.data)


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
    """
    # Filter active projects
    projetos = Projeto.objects.filter(ativo=True)

    # Issue #153: Filter out test projects by default
    include_test = request.query_params.get("include_test", "false").lower() == "true"
    if not include_test:
        projetos = projetos.filter(is_test=False)

    projetos = projetos.order_by("nome")

    serializer = ProjetoOptionSerializer(projetos, many=True)
    return Response(serializer.data)


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
    """
    tipos = TipoEvento.objects.filter(ativo=True).order_by("nome")
    serializer = TipoEventoOptionSerializer(tipos, many=True)
    return Response(serializer.data)


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
    """
    usuarios = Usuario.objects.filter(is_active=True).order_by("first_name", "last_name")
    serializer = UsuarioOptionSerializer(usuarios, many=True)
    return Response(serializer.data)

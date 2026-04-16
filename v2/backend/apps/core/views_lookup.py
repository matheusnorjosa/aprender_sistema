"""
PR16: Views de Autocomplete/Lookup para frontend

Endpoints:
- /api/lookup/municipios/?q=...
- /api/lookup/projetos/?q=...
- /api/lookup/tipos-evento/?q=...
- /api/lookup/usuarios/?q=...

Retorna: [{id, label, kind, alias?}]
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

from typing import Any

from django.db.models import Q, QuerySet
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.services.normalize import norm_text

from .models import Municipio, Projeto, TipoEvento, Usuario


def dedup_by_id(items):
    """Remove duplicatas mantendo primeiro elemento por ID"""
    seen = set()
    result = []
    for item in items:
        if item["id"] not in seen:
            seen.add(item["id"])
            result.append(item)
    return result


class MunicipioLookup(APIView):
    """
    GET /api/lookup/municipios/?q=fortaleza

    Query params adicionais:
    - com_compra=true|false: filtra apenas municípios com compra registrada
    - projeto_id=<id>: restringe municípios com compra no projeto informado

    Retorna: [{id, label, kind: "municipio"}]
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        q = request.GET.get("q", "").strip()
        com_compra = request.GET.get("com_compra", "false").lower() in {"1", "true", "t", "yes", "y"}
        projeto_id_raw = request.GET.get("projeto_id", "").strip()

        projeto_id: int | None = None
        try:
            if projeto_id_raw:
                projeto_id = int(projeto_id_raw)
        except ValueError:
            projeto_id = None

        qs: QuerySet[Municipio] = Municipio.objects.filter(ativo=True)
        if com_compra or projeto_id is not None:
            qs = qs.filter(compras__isnull=False)
        if projeto_id is not None:
            qs = qs.filter(compras__projeto_id=projeto_id)
        qs = qs.distinct()

        if not q:
            # Retornar municípios (max 100)
            qs = qs.order_by("nome")[:100]
        else:
            # Normalizar query
            _q_norm = norm_text(q)  # noqa: F841 - reserved for future normalized search

            # Buscar por nome ou UF
            qs = qs.filter(Q(nome__icontains=q) | Q(uf__icontains=q)).order_by("nome")[:50]

        results = []
        for mun in qs:
            results.append(
                {
                    "id": mun.id,
                    "label": f"{mun.nome}-{mun.uf}",
                    "kind": "municipio",
                }
            )

        return Response(dedup_by_id(results))


class ProjetoLookup(APIView):
    """
    GET /api/lookup/projetos/?q=acerta

    Query params adicionais:
    - com_compra=true|false: filtra apenas projetos com compra registrada
    - municipio_id=<id>: restringe projetos com compra no município informado

    Retorna: [{id, label, kind: "projeto"}]
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        q = request.GET.get("q", "").strip()
        com_compra = request.GET.get("com_compra", "false").lower() in {"1", "true", "t", "yes", "y"}
        municipio_id_raw = request.GET.get("municipio_id", "").strip()

        municipio_id: int | None = None
        try:
            if municipio_id_raw:
                municipio_id = int(municipio_id_raw)
        except ValueError:
            municipio_id = None

        qs: QuerySet[Projeto] = Projeto.objects.filter(ativo=True)
        if com_compra or municipio_id is not None:
            qs = qs.filter(compras__isnull=False)
        if municipio_id is not None:
            qs = qs.filter(compras__municipio_id=municipio_id)
        qs = qs.distinct()

        if not q:
            qs = qs.order_by("nome")[:50]
        else:
            _q_norm = norm_text(q)  # noqa: F841 - reserved for future normalized search
            qs = qs.filter(Q(nome__icontains=q) | Q(codigo__icontains=q)).order_by("nome")[:50]

        results = []
        for proj in qs:
            label = proj.nome
            if proj.codigo:
                label = f"{proj.codigo} - {proj.nome}"

            results.append(
                {
                    "id": proj.id,
                    "label": label,
                    "kind": "projeto",
                    "fluxo": proj.fluxo,
                }
            )

        return Response(dedup_by_id(results))


class TipoEventoLookup(APIView):
    """
    GET /api/lookup/tipos-evento/?q=formacao
    Retorna: [{id, label, kind: "tipo_evento"}]
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        q = request.GET.get("q", "").strip()

        if not q:
            qs = TipoEvento.objects.all().order_by("nome")[:50]
        else:
            qs = TipoEvento.objects.filter(nome__icontains=q)[:50]

        results = []
        for tipo in qs:
            results.append(
                {
                    "id": tipo.id,
                    "label": tipo.nome,
                    "kind": "tipo_evento",
                }
            )

        return Response(dedup_by_id(results))


class UsuarioLookup(APIView):
    """
    GET /api/lookup/usuarios/?q=maria&role=formador
    Retorna: [{id, label, kind: "usuario"}]

    SEC-ENUM-01: email removed from response to prevent user enumeration.
    SEC-ENUM-02: email search restricted to Coordenador+ roles.
    """

    permission_classes = [IsAuthenticated]

    # Roles allowed to search by email (SEC-ENUM-02)
    _EMAIL_SEARCH_ROLES = {"Coordenador", "Gerente", "Superintendência", "Apoio"}

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        q = request.GET.get("q", "").strip()
        role = request.GET.get("role", "").strip()

        # Começar com queryset base
        qs = Usuario.objects.filter(is_active=True)

        # SEC-ENUM-02: only Coordenador+ can search by email/username
        user_groups = set(request.user.groups.values_list("name", flat=True))
        can_search_email = bool(request.user.is_superuser or user_groups & self._EMAIL_SEARCH_ROLES)

        # Aplicar filtro de busca
        if q:
            if can_search_email:
                qs = qs.filter(
                    Q(first_name__icontains=q)
                    | Q(last_name__icontains=q)
                    | Q(email__icontains=q)
                    | Q(username__icontains=q)
                )
            else:
                qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q))

        # Filtrar por role/group ANTES do slice
        if role:
            qs = qs.filter(groups__name__iexact=role)

        # Aplicar ordenação e limite
        qs = qs.order_by("-id")[: 50 if q else 20]

        results = []
        for user in qs:
            label = user.get_full_name() or user.username
            results.append(
                {
                    "id": user.id,
                    "label": label,
                    "kind": "usuario",
                }
            )

        return Response(dedup_by_id(results))

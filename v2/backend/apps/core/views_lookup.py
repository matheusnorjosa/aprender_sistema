"""
PR16: Views de Autocomplete/Lookup para frontend

Endpoints:
- /api/lookup/municipios/?q=...
- /api/lookup/projetos/?q=...
- /api/lookup/tipos-evento/?q=...
- /api/lookup/usuarios/?q=...

Retorna: [{id, label, kind, alias?}]
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from .models import Municipio, Projeto, TipoEvento, Usuario
from apps.dat_ingest.services.acompanhamento_normalize import norm_text


def dedup_by_id(items):
    """Remove duplicatas mantendo primeiro elemento por ID"""
    seen = set()
    result = []
    for item in items:
        if item['id'] not in seen:
            seen.add(item['id'])
            result.append(item)
    return result


class MunicipioLookup(APIView):
    """
    GET /api/lookup/municipios/?q=fortaleza
    Retorna: [{id, label, kind: "municipio"}]
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        q = request.GET.get('q', '').strip()

        if not q:
            # Retornar top 20 municípios mais recentes
            qs = Municipio.objects.filter(ativo=True).order_by('-id')[:20]
        else:
            # Normalizar query
            q_norm = norm_text(q)

            # Buscar por nome ou UF
            qs = Municipio.objects.filter(
                Q(nome__icontains=q) | Q(uf__icontains=q),
                ativo=True
            )[:50]

        results = []
        for mun in qs:
            results.append({
                'id': mun.id,
                'label': f"{mun.nome}-{mun.uf}",
                'kind': 'municipio',
            })

        return Response(dedup_by_id(results))


class ProjetoLookup(APIView):
    """
    GET /api/lookup/projetos/?q=acerta
    Retorna: [{id, label, kind: "projeto"}]
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        q = request.GET.get('q', '').strip()

        if not q:
            qs = Projeto.objects.filter(ativo=True).order_by('-id')[:20]
        else:
            q_norm = norm_text(q)
            qs = Projeto.objects.filter(
                Q(nome__icontains=q) | Q(codigo__icontains=q),
                ativo=True
            )[:50]

        results = []
        for proj in qs:
            label = proj.nome
            if proj.codigo:
                label = f"{proj.codigo} - {proj.nome}"

            results.append({
                'id': proj.id,
                'label': label,
                'kind': 'projeto',
            })

        return Response(dedup_by_id(results))


class TipoEventoLookup(APIView):
    """
    GET /api/lookup/tipos-evento/?q=formacao
    Retorna: [{id, label, kind: "tipo_evento"}]
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        q = request.GET.get('q', '').strip()

        if not q:
            qs = TipoEvento.objects.all().order_by('-id')[:20]
        else:
            qs = TipoEvento.objects.filter(
                nome__icontains=q
            )[:50]

        results = []
        for tipo in qs:
            results.append({
                'id': tipo.id,
                'label': tipo.nome,
                'kind': 'tipo_evento',
            })

        return Response(dedup_by_id(results))


class UsuarioLookup(APIView):
    """
    GET /api/lookup/usuarios/?q=maria&role=formador
    Retorna: [{id, label, kind: "usuario", email}]
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        q = request.GET.get('q', '').strip()
        role = request.GET.get('role', '').strip()

        # Começar com queryset base
        qs = Usuario.objects.filter(is_active=True)

        # Aplicar filtro de busca
        if q:
            qs = qs.filter(
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(email__icontains=q) |
                Q(username__icontains=q)
            )

        # Filtrar por role/group ANTES do slice
        if role:
            qs = qs.filter(groups__name__iexact=role)

        # Aplicar ordenação e limite
        qs = qs.order_by('-id')[:50 if q else 20]

        results = []
        for user in qs:
            label = user.get_full_name() or user.username
            if user.email:
                label = f"{label} <{user.email}>"

            results.append({
                'id': user.id,
                'label': label,
                'kind': 'usuario',
                'email': user.email or '',
            })

        return Response(dedup_by_id(results))

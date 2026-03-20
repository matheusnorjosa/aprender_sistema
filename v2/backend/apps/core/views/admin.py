"""
AS v2 — Admin ViewSets

CRUD ViewSets for admin entities (DAT permissions).
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

from django.contrib.auth.models import Group
from django.db.models import Count, Q, QuerySet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from django_filters.rest_framework import DjangoFilterBackend

from apps.core.constants import FUNCAO_GROUPS, RESERVED_GROUPS, SETOR_GROUPS
from apps.core.models import AuditLog, Compra, Gerencia, Municipio, PermissaoFuncional, Produto, Projeto, Usuario
from apps.core.permissions import IsControleOrDAT, IsDAT
from apps.core.serializers import (
    AuditLogSerializer,
    CompraSerializer,
    GerenciaSerializer,
    GroupSerializer,
    MunicipioSerializer,
    PermissaoFuncionalSerializer,
    ProdutoSerializer,
    ProjetoSerializer,
    UsuarioAdminSerializer,
)


class MunicipioViewSet(viewsets.ModelViewSet):
    """
    ViewSet para CRUD de Municípios (apenas DAT).

    Filtros disponíveis:
    - uf: exato (BA, CE, PE, etc.)
    - ativo: booleano (true/false)
    - search: busca textual em nome
    - ordering: nome, uf, id
    """

    queryset = Municipio.objects.all()
    serializer_class = MunicipioSerializer
    permission_classes = [IsDAT]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["uf", "ativo"]
    search_fields = ["nome", "ibge_code"]
    ordering_fields = ["nome", "uf", "id"]
    ordering = ["nome"]


class ProjetoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para CRUD de Projetos (apenas DAT).

    Filtros disponíveis:
    - ativo: booleano (true/false)
    - is_test: booleano (oculto por padrão, use ?include_test=true para exibir)
    - search: busca textual em nome, codigo, descricao
    - ordering: nome, id

    Issue #153: Projetos de teste (is_test=True) são ocultos por padrão.
    Para incluir projetos de teste, use query param ?include_test=true
    """

    queryset = Projeto.objects.all()
    serializer_class = ProjetoSerializer
    permission_classes = [IsDAT]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["ativo"]
    search_fields = ["nome", "codigo", "descricao"]
    ordering_fields = ["nome", "id"]
    ordering = ["nome"]

    def get_queryset(self) -> QuerySet[Projeto]:
        """
        Filtra projetos.

        Default: exclude is_test=True (produção)
        Query param ?include_test=true: mostra todos (incluindo projetos de teste)

        Issue #153: Isolamento de projetos de teste da visualização padrão
        """
        qs = super().get_queryset()
        include_test = self.request.query_params.get("include_test", "false").lower() == "true"
        if not include_test:
            qs = qs.filter(is_test=False)
        return qs


class ProdutoViewSet(viewsets.ModelViewSet):  # type: ignore[misc]
    """
    ViewSet para CRUD de Produtos (Issue #146).

    Endpoints:
        - GET /api/produtos/ - Listar produtos
        - POST /api/produtos/ - Criar produto (DAT only)
        - GET /api/produtos/{id}/ - Detalhe
        - PUT/PATCH /api/produtos/{id}/ - Atualizar (DAT only)
        - DELETE /api/produtos/{id}/ - Deletar (DAT only)

    Filtros:
        - ativo (bool)
        - projeto (FK)
        - codigo (icontains via search)
    """

    queryset = Produto.objects.select_related("projeto").order_by("codigo")
    serializer_class = ProdutoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["ativo", "projeto"]
    search_fields = ["codigo", "nome"]
    ordering_fields = ["codigo", "nome"]
    ordering = ["codigo"]

    def get_permissions(self) -> list:  # type: ignore[type-arg]
        """DAT pode criar/editar/deletar. Outros apenas leitura."""
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAuthenticated(), IsDAT()]
        return [IsAuthenticated()]


class GerenciaViewSet(viewsets.ModelViewSet):  # type: ignore[misc]
    """
    ViewSet para CRUD de Gerências (Issue #145).

    Endpoints:
        - GET /api/gerencias/ - Listar gerências
        - POST /api/gerencias/ - Criar gerência (DAT only)
        - GET /api/gerencias/{id}/ - Detalhe de gerência
        - PUT/PATCH /api/gerencias/{id}/ - Atualizar (DAT only)
        - DELETE /api/gerencias/{id}/ - Deletar (DAT only)

    Filtros:
        - ativo (bool)
        - nome_setor (search)
    """

    queryset = Gerencia.objects.annotate(projetos_count=Count("projetos", filter=Q(projetos__ativo=True))).order_by(
        "nome"
    )
    serializer_class = GerenciaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["ativo"]
    search_fields = ["nome", "nome_setor"]
    ordering_fields = ["nome", "nome_setor"]
    ordering = ["nome"]

    def get_permissions(self) -> list:  # type: ignore[type-arg]
        """DAT pode criar/editar/deletar. Outros apenas leitura."""
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAuthenticated(), IsDAT()]
        return [IsAuthenticated()]


class CompraViewSet(viewsets.ModelViewSet):
    """
    ViewSet para CRUD de Compras.

    Permissões:
    - DAT: CRUD completo
    - Controle: read-only + import via endpoint separado

    Filtros disponíveis:
    - projeto: FK (ID do projeto)
    - municipio: FK (ID do município)
    - search: busca textual em codigo, uso
    - ordering: data, codigo, id
    """

    queryset = Compra.objects.select_related("projeto", "municipio").all()
    serializer_class = CompraSerializer

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["projeto", "municipio"]
    search_fields = ["codigo", "uso", "municipio__nome", "projeto__nome"]
    ordering_fields = ["data", "codigo", "id"]
    ordering = ["-data"]

    def get_permissions(self):
        """
        DAT: full CRUD
        Controle: apenas leitura (list, retrieve)
        """
        if self.action in ["list", "retrieve"]:
            return [IsControleOrDAT()]
        return [IsDAT()]


class UsuarioAdminViewSet(viewsets.ModelViewSet):
    """
    ViewSet para CRUD de Usuários (apenas DAT).

    Permite criar/atualizar usuários, atribuir grupos, setar senhas.

    Filtros disponíveis:
    - is_active: booleano
    - is_staff: booleano
    - search: busca em username, email, first_name, last_name, cpf
    - ordering: username, email, date_joined, id

    GAP-001 (resolvido): Endpoint reativado em Fase 1 Iteração 2.
    """

    queryset = Usuario.objects.prefetch_related("groups").all()
    serializer_class = UsuarioAdminSerializer
    permission_classes = [IsDAT]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["is_active", "is_staff", "is_superuser"]
    search_fields = ["username", "email", "first_name", "last_name", "cpf"]
    ordering_fields = ["username", "email", "date_joined", "id"]
    ordering = ["username"]

    @action(detail=True, methods=["post"], permission_classes=[IsDAT])
    def assign_groups(self, request, pk=None):
        """
        Atribui grupos a um usuário.

        Endpoint: POST /api/usuarios-admin/{id}/assign_groups/
        Payload: {"group_ids": [1, 2, 3]}

        Security (Issue #561 C-04):
        - Users cannot modify their own groups (self-modification blocked)
        - Only groups in ALLOWED_USER_GROUPS whitelist can be assigned
        - Reuses validation logic from UsuarioAdminSerializer (P1.1)

        GAP-003 (resolvido): Endpoint para vincular usuários a grupos.
        Iteração 3 - Fase 1 Plano DAT/GCal.
        """
        from django.conf import settings as django_settings

        usuario = self.get_object()
        group_ids = request.data.get("group_ids", [])

        # Security (C-04): Block self-modification of groups
        if usuario.id == request.user.id:
            return Response(
                {"error": "Você não pode modificar seus próprios grupos."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Validar tipo de dados
        if not isinstance(group_ids, list):
            return Response(
                {"error": "group_ids must be a list of integers"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validar que são inteiros
        try:
            group_ids = [int(gid) for gid in group_ids]
        except (ValueError, TypeError):
            return Response(
                {"error": "group_ids must contain only integers"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Remover duplicados
        group_ids = list(set(group_ids))

        # Verificar se todos os grupos existem
        groups = Group.objects.filter(id__in=group_ids)
        if groups.count() != len(group_ids):
            found_ids = set(groups.values_list("id", flat=True))
            missing_ids = set(group_ids) - found_ids
            return Response(
                {"error": f"Groups not found with IDs: {sorted(missing_ids)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Security (C-04): Validate groups against whitelist (P1.1)
        allowed_groups: set[str] = getattr(django_settings, "ALLOWED_USER_GROUPS", set())
        for group in groups:
            if group.name not in allowed_groups:
                allowed_list = ", ".join(sorted(allowed_groups))
                return Response(
                    {"error": f"Grupo '{group.name}' não permitido. Grupos válidos: {allowed_list}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Atribuir grupos (substitui grupos existentes)
        usuario.groups.set(groups)

        # Retornar usuário atualizado com grupos
        serializer = self.get_serializer(usuario)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GroupViewSet(viewsets.ModelViewSet):
    """
    ViewSet para CRUD de Grupos Django (apenas DAT).

    Gerencia grupos/setores do sistema (Superintendência, Coordenador, Formador, etc.).

    Filtros disponíveis:
    - search: busca textual em name
    - ordering: name, id

    GAP-002 (resolvido): Endpoint criado em Fase 1 Iteração 2.
    """

    queryset = Group.objects.prefetch_related("permissions", "permissoes_funcionais").all()
    serializer_class = GroupSerializer
    permission_classes = [IsDAT]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name", "id"]
    ordering = ["name"]

    def perform_destroy(self, instance: Group) -> None:
        is_reserved = instance.name in RESERVED_GROUPS
        confirmed = str(self.request.query_params.get("confirm_reserved", "")).lower() == "true"
        if is_reserved and not confirmed:
            raise ValidationError(
                {"detail": "Grupo reservado. Para excluir, use ?confirm_reserved=true na requisição."}
            )
        super().perform_destroy(instance)


class PermissaoFuncionalViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Endpoint read-only para listar permissões funcionais de negócio.
    """

    queryset = PermissaoFuncional.objects.prefetch_related("groups").all()
    serializer_class = PermissaoFuncionalSerializer
    permission_classes = [IsDAT]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["category", "is_system"]
    search_fields = ["codename", "label", "description"]
    ordering_fields = ["category", "label", "codename"]
    ordering = ["category", "label"]


class RBACMetaView(APIView):
    """
    Metadados de RBAC para telas admin.
    """

    permission_classes = [IsDAT]

    def get(self, request: Request, *args: object, **kwargs: object) -> Response:
        categories = list(PermissaoFuncional.objects.values_list("category", flat=True).distinct().order_by("category"))
        return Response(
            {
                "setor_groups": SETOR_GROUPS,
                "funcao_groups": FUNCAO_GROUPS,
                "categories": categories,
            },
            status=status.HTTP_200_OK,
        )


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para consulta de Logs de Auditoria (read-only).

    PA-05: Apenas leitura, para rastreamento de ações críticas.

    Filtros disponíveis:
    - action: tipo de ação (CREATE, UPDATE, DELETE, APPROVE, REJECT, IMPORT, etc.)
    - usuario: FK (ID do usuário)
    - model_name: nome do modelo afetado
    - search: busca em justificativa, details
    - ordering: timestamp, action, id
    """

    queryset = AuditLog.objects.select_related("usuario").all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsControleOrDAT]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["action", "usuario", "model_name"]
    search_fields = ["action", "model_name"]
    ordering_fields = ["created_at", "action", "id"]
    ordering = ["-created_at"]

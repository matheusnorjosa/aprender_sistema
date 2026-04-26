"""
AS v2 — Admin ViewSets

CRUD ViewSets for admin entities (DAT permissions).
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

from django.contrib.auth.models import Group
from django.db import transaction
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
from apps.core.models import (
    AuditLog,
    Compra,
    Gerencia,
    GroupClassificacao,
    Municipio,
    MunicipioReferencia,
    PermissaoFuncional,
    Produto,
    Projeto,
    Usuario,
)
from apps.core.permissions import HasPerm
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
from apps.core.services.rbac_service import get_assignable_group_names


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
    # Issue #1222 (Epic 1): cadastro admin DAT puro
    permission_classes = [HasPerm("manage_admin_registries")]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["uf", "ativo"]
    search_fields = ["nome", "ibge_code"]
    ordering_fields = ["nome", "uf", "id"]
    ordering = ["nome"]

    @action(detail=False, methods=["get"], url_path="autocomplete")
    def autocomplete(self, request: Request) -> Response:
        """
        Autocomplete assistido para Admin DAT (nome + UF + IBGE).

        Query params:
        - q: termo de busca (mínimo 2 chars)
        - uf: filtro opcional de UF
        - limit: quantidade máxima (default=20, max=50)
        """

        q = str(request.query_params.get("q", "")).strip()
        uf = str(request.query_params.get("uf", "")).strip().upper()
        raw_limit = str(request.query_params.get("limit", "20")).strip()

        try:
            limit = int(raw_limit)
        except ValueError as exc:
            raise ValidationError({"limit": "limit deve ser um inteiro válido."}) from exc

        limit = max(1, min(limit, 50))
        if uf and len(uf) != 2:
            raise ValidationError({"uf": "UF deve ter exatamente 2 caracteres."})

        if len(q) < 2:
            return Response({"results": []}, status=status.HTTP_200_OK)

        ref_qs = MunicipioReferencia.objects.filter(ativo=True, nome__icontains=q)
        cad_qs = Municipio.objects.filter(ativo=True, nome__icontains=q)
        if uf:
            ref_qs = ref_qs.filter(uf__iexact=uf)
            cad_qs = cad_qs.filter(uf__iexact=uf)

        # Fallback de IBGE para referências sem código confiável.
        fallback_ibge: dict[tuple[str, str], str] = {}
        for nome, municipio_uf, ibge_code in cad_qs.filter(ibge_code__isnull=False).values_list(
            "nome", "uf", "ibge_code"
        ):
            if not ibge_code:
                continue
            fallback_ibge[(nome.casefold(), municipio_uf.upper())] = ibge_code

        by_key: dict[tuple[str, str], dict[str, str | None]] = {}

        def upsert(item: dict[str, str | None]) -> None:
            key = (str(item["nome"]).casefold(), str(item["uf"]).upper())
            current = by_key.get(key)
            if current is None:
                by_key[key] = item
                return

            current_score = (
                1 if current.get("ibge_code") else 0,
                1 if current.get("source") == "referencia" else 0,
            )
            new_score = (
                1 if item.get("ibge_code") else 0,
                1 if item.get("source") == "referencia" else 0,
            )
            if new_score > current_score:
                by_key[key] = item

        for ref in ref_qs.order_by("nome", "uf")[: limit * 2]:
            ref_code = (ref.codigo_externo or "").strip()
            ibge_code = ref_code if ref_code.isdigit() and len(ref_code) == 7 else None
            if ibge_code is None:
                ibge_code = fallback_ibge.get((ref.nome.casefold(), ref.uf.upper()))

            upsert(
                {
                    "nome": ref.nome,
                    "uf": ref.uf.upper(),
                    "ibge_code": ibge_code,
                    "source": "referencia",
                    "confidence": "high" if ibge_code else "low",
                }
            )

        for municipio in cad_qs.order_by("nome", "uf")[: limit * 2]:
            upsert(
                {
                    "nome": municipio.nome,
                    "uf": municipio.uf.upper(),
                    "ibge_code": municipio.ibge_code,
                    "source": "cadastro",
                    "confidence": "high" if municipio.ibge_code else "low",
                }
            )

        results = sorted(by_key.values(), key=lambda item: (str(item["nome"]), str(item["uf"])))[:limit]
        return Response({"results": results}, status=status.HTTP_200_OK)


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
    # Issue #1222 (Epic 1): cadastro admin DAT puro
    permission_classes = [HasPerm("manage_admin_registries")]

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
            return [IsAuthenticated(), HasPerm("manage_purchases_and_materials")()]
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
        "nome_setor"
    )
    serializer_class = GerenciaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["ativo"]
    search_fields = ["nome", "nome_setor"]
    ordering_fields = ["nome", "nome_setor"]
    ordering = ["nome_setor"]

    def get_permissions(self) -> list:  # type: ignore[type-arg]
        """DAT pode criar/editar/deletar. Outros apenas leitura."""
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAuthenticated(), HasPerm("manage_purchases_and_materials")()]
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
        # Issue #1222 (Epic 1): list/retrieve aberto pra DAT (manage_purchases)
        # ou Controle (operate_preagenda); CUD restrito a quem gerencia compras.
        if self.action in ["list", "retrieve"]:
            return [(HasPerm("manage_purchases_and_materials") | HasPerm("operate_preagenda"))()]
        return [HasPerm("manage_purchases_and_materials")()]


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
    # Issue #1222 (Epic 1): admin usuários é cadastro admin DAT puro
    permission_classes = [HasPerm("manage_admin_registries")]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["is_active", "is_staff", "is_superuser"]
    search_fields = ["username", "email", "first_name", "last_name", "cpf"]
    ordering_fields = ["username", "email", "date_joined", "id"]
    ordering = ["username"]

    @action(detail=True, methods=["post"], permission_classes=[HasPerm("manage_purchases_and_materials")])
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

        # PERF-SQL-05: single query instead of count() + values_list()
        groups = Group.objects.filter(id__in=group_ids)
        found_ids = set(groups.values_list("id", flat=True))
        if len(found_ids) != len(group_ids):
            missing_ids = set(group_ids) - found_ids
            return Response(
                {"error": f"Groups not found with IDs: {sorted(missing_ids)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Security (C-04): Validate groups against dynamic whitelist (P1.1/#832)
        allowed_groups = get_assignable_group_names()
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
    permission_classes = [HasPerm("manage_purchases_and_materials")]

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

    @action(
        detail=True,
        methods=["post"],
        url_path="sync-members",
        permission_classes=[HasPerm("manage_purchases_and_materials")],
    )
    def sync_members(self, request: Request, pk: str | None = None) -> Response:
        """
        Sincroniza membros de um grupo em lote.

        Endpoint: POST /api/grupos/{id}/sync-members/
        Payload: {"user_ids": [1, 2, 3]}
        """

        group = self.get_object()
        user_ids = request.data.get("user_ids", [])

        if not isinstance(user_ids, list):
            return Response(
                {"error": "user_ids must be a list of integers"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user_ids = [int(user_id) for user_id in user_ids]
        except (TypeError, ValueError):
            return Response(
                {"error": "user_ids must contain only integers"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dedup_user_ids = sorted(set(user_ids))
        users = Usuario.objects.filter(id__in=dedup_user_ids)
        found_ids = set(users.values_list("id", flat=True))
        missing_ids = sorted(set(dedup_user_ids) - found_ids)
        if missing_ids:
            return Response(
                {"error": f"Users not found with IDs: {missing_ids}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        current_member_ids = set(group.user_set.values_list("id", flat=True))
        target_member_ids = set(dedup_user_ids)
        added_ids = sorted(target_member_ids - current_member_ids)
        removed_ids = sorted(current_member_ids - target_member_ids)

        with transaction.atomic():
            group.user_set.set(users)

            AuditLog.objects.create(
                usuario=request.user if request.user.is_authenticated else None,
                action="SYNC_GROUP_MEMBERS",
                model_name="Group",
                details={
                    "group_id": group.id,
                    "group_name": group.name,
                    "target_user_ids": dedup_user_ids,
                    "added_user_ids": added_ids,
                    "removed_user_ids": removed_ids,
                },
            )

        return Response(
            {
                "group_id": group.id,
                "members_count": len(dedup_user_ids),
                "member_ids": dedup_user_ids,
                "added": len(added_ids),
                "removed": len(removed_ids),
            },
            status=status.HTTP_200_OK,
        )


class PermissaoFuncionalViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Endpoint read-only para listar permissões funcionais de negócio.
    """

    queryset = PermissaoFuncional.objects.prefetch_related("groups").all()
    serializer_class = PermissaoFuncionalSerializer
    # Issue #1222 (Epic 1): admin de permissões funcionais é DAT puro
    permission_classes = [HasPerm("manage_admin_registries")]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["category", "is_system"]
    search_fields = ["codename", "label", "description"]
    ordering_fields = ["category", "label", "codename"]
    ordering = ["category", "label"]


class RBACMetaView(APIView):
    """
    Metadados de RBAC para telas admin.
    """

    # Issue #1222 (Epic 1): admin RBAC é DAT puro
    permission_classes = [HasPerm("manage_admin_registries")]

    def get(self, request: Request, *args: object, **kwargs: object) -> Response:
        classificacoes = list(GroupClassificacao.objects.select_related("group").values_list("group__name", "tipo"))
        dynamic_setor_groups = {
            group_name for group_name, tipo in classificacoes if tipo == GroupClassificacao.Tipo.SETOR
        }
        dynamic_funcao_groups = {
            group_name for group_name, tipo in classificacoes if tipo == GroupClassificacao.Tipo.FUNCAO
        }

        categories = list(PermissaoFuncional.objects.values_list("category", flat=True).distinct().order_by("category"))
        return Response(
            {
                "setor_groups": sorted(set(SETOR_GROUPS) | dynamic_setor_groups),
                "funcao_groups": sorted(set(FUNCAO_GROUPS) | dynamic_funcao_groups),
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
    # Issue #1237 (Epic 1.6): logs visíveis por motivo legítimo de acesso —
    # DAT (suporte/admin transversal), Controle (operação diária),
    # Superintendência (auditar próprias aprovações/reprovações),
    # Gerente (auditar batch). PA-05 audit precisa ser legível por quem
    # executa o fluxo de aprovação. Refactor estrutural pra Policy
    # `access_audit_logs` em Epic 4 (Issue #1232).
    permission_classes = [
        HasPerm("manage_admin_registries")
        | HasPerm("operate_preagenda")
        | HasPerm("approve_solicitation")
        | HasPerm("approve_solicitation_batch")
    ]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["action", "usuario", "model_name"]
    search_fields = ["action", "model_name"]
    ordering_fields = ["created_at", "action", "id"]
    ordering = ["-created_at"]

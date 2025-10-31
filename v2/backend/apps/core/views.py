"""
Core views

PA-01: Nenhuma solicitação é auto-aprovada.
PA-02: Apenas Superintendência pode aprovar/reprovar.
PA-05: Registrar usuário, data/hora e justificativa em AuditLog.
"""

import logging

from django.contrib.auth.models import Group
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    AuditLog,
    AvailabilityBlock,
    Compra,
    Municipio,
    Projeto,
    Solicitacao,
    TipoEvento,
    Usuario,
)
from .permissions import IsControleOrDAT, IsCoordenadorOrDAT, IsDAT, IsSuperintendencia
from .serializers import (
    AuditLogSerializer,
    AvailabilityBlockSerializer,
    CompraSerializer,
    GroupSerializer,
    MunicipioOptionSerializer,
    MunicipioSerializer,
    ProjetoOptionSerializer,
    ProjetoSerializer,
    SolicitacaoSerializer,
    TipoEventoOptionSerializer,
    UsuarioAdminSerializer,
    UsuarioOptionSerializer,
)
from .services.availability_service import check_conflicts
# from .services.import_compras import import_compras_from_file  # TODO: service depende de modelo Compra (GAP-004)

# Logger estruturado para auditoria
logger = logging.getLogger(__name__)


def _get_client_ip(request):
    """
    Extrai o IP real do cliente, considerando proxies reversos.

    Prioridade:
    1. HTTP_X_FORWARDED_FOR (primeiro IP da lista)
    2. HTTP_X_REAL_IP
    3. REMOTE_ADDR

    Returns:
        str: IP do cliente
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        # X-Forwarded-For pode conter múltiplos IPs: "client, proxy1, proxy2"
        # O primeiro é o IP real do cliente
        return x_forwarded_for.split(",")[0].strip()

    x_real_ip = request.META.get("HTTP_X_REAL_IP")
    if x_real_ip:
        return x_real_ip.strip()

    return request.META.get("REMOTE_ADDR", "unknown")


def api_root(request):
    """API root endpoint"""
    return JsonResponse(
        {
            "message": "AS v2 API",
            "version": "2.0.0",
            "endpoints": {
                "admin": "/admin/",
                "healthz": "/healthz/",
                "api": "/api/",
            },
        }
    )


class SolicitacaoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para Solicitações de Evento.

    PA-01: Status sempre começa pendente.
    PA-02: Apenas Superintendência pode aprovar/reprovar.
    PR 8/N: Apenas Coordenador ou DAT podem criar solicitações.

    Filtros disponíveis:
    - status: exato (pendente/aprovado/reprovado)
    - search: busca textual em usuario, municipio, motivo, observacoes
    - ordering: inicio, fim, id
    """

    queryset = Solicitacao.objects.select_related(
        "usuario", "municipio", "tipo_evento", "projeto"
    )
    serializer_class = SolicitacaoSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status"]
    search_fields = [
        "usuario__username",
        "usuario__first_name",
        "usuario__last_name",
        "municipio__nome",
        "observacoes",
    ]
    ordering_fields = ["inicio", "fim", "id"]
    ordering = ["-inicio"]  # default ordering

    def get_permissions(self):
        """
        PR 8/N: Apenas Coordenador ou DAT podem criar solicitações.
        Outras ações: IsAuthenticated.
        """
        if self.action == "create":
            return [IsCoordenadorOrDAT()]
        return [IsAuthenticated()]

    def get_queryset(self):
        """
        Filtrar solicitações por usuário (exceto Superintendência/superuser que vê todas).
        """
        if (
            self.request.user.is_superuser
            or self.request.user.groups.filter(name="Superintendência").exists()
        ):
            return Solicitacao.objects.select_related(
                "usuario", "municipio", "tipo_evento", "projeto"
            ).prefetch_related("participations__usuario")
        return (
            Solicitacao.objects.filter(usuario=self.request.user)
            .select_related("usuario", "municipio", "tipo_evento", "projeto")
            .prefetch_related("participations__usuario")
        )

    def perform_create(self, serializer):
        """
        PR 8/N: Preenche usuario automaticamente com request.user ao criar solicitação.
        PA-01: Status sempre começa pendente (garantido pelo modelo).
        """
        serializer.save(usuario=self.request.user)

    @action(
        detail=True,
        methods=["patch"],
        permission_classes=[IsSuperintendencia],
        url_path="approve",
    )
    def approve(self, request, pk=None):
        """
        Aprovar solicitação (PA-02: apenas Superintendência).

        POST /api/solicitacoes/<id>/approve/
        Body: {"justificativa": "..."}  # opcional
        """
        solicitacao = self.get_object()

        if solicitacao.status == "aprovado":
            return Response(
                {"detail": "Solicitação já está aprovada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        prev_status = solicitacao.status
        solicitacao.status = "aprovado"
        solicitacao.save()

        # ================================================================
        # PA-05: Log estruturado de auditoria + AuditLog persistente
        # ================================================================
        client_ip = _get_client_ip(request)
        justificativa = request.data.get("justificativa", "")

        # Logger estruturado (para monitoramento em tempo real)
        logger.info(
            "solicitacao_approved",
            extra={
                "event": "solicitacao_approved",
                "user_id": request.user.id,
                "username": request.user.username,
                "solicitation_id": solicitacao.id,
                "action": "approve",
                "ip_address": client_ip,
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
                "justificativa": justificativa,
                "timestamp": timezone.now().isoformat(),
            },
        )

        # AuditLog persistente (para rastreabilidade e compliance)
        AuditLog.objects.create(
            usuario=request.user,
            action="APPROVE",
            model_name="Solicitacao",
            details={
                "solicitacao_id": solicitacao.id,
                "prev_status": prev_status,
                "new_status": "aprovado",
                "justificativa": justificativa,
                "ip_address": client_ip,
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
            },
        )

        return Response(
            {
                "detail": "Solicitação aprovada com sucesso.",
                "solicitacao": SolicitacaoSerializer(solicitacao).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["patch"],
        permission_classes=[IsSuperintendencia],
        url_path="reject",
    )
    def reject(self, request, pk=None):
        """
        Reprovar solicitação (PA-02: apenas Superintendência).

        POST /api/solicitacoes/<id>/reject/
        Body: {"justificativa": "..."} # opcional
        """
        solicitacao = self.get_object()
        justificativa = request.data.get("justificativa", "")

        if solicitacao.status == "reprovado":
            return Response(
                {"detail": "Solicitação já está reprovada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        prev_status = solicitacao.status
        solicitacao.status = "reprovado"
        solicitacao.save()

        # ================================================================
        # PA-05: Log estruturado de auditoria + AuditLog persistente
        # ================================================================
        client_ip = _get_client_ip(request)

        # Logger estruturado (para monitoramento em tempo real)
        logger.info(
            "solicitacao_rejected",
            extra={
                "event": "solicitacao_rejected",
                "user_id": request.user.id,
                "username": request.user.username,
                "solicitation_id": solicitacao.id,
                "action": "reject",
                "ip_address": client_ip,
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
                "justificativa": justificativa,
                "timestamp": timezone.now().isoformat(),
            },
        )

        # AuditLog persistente (para rastreabilidade e compliance)
        AuditLog.objects.create(
            usuario=request.user,
            action="REJECT",
            model_name="Solicitacao",
            details={
                "solicitacao_id": solicitacao.id,
                "prev_status": prev_status,
                "new_status": "reprovado",
                "justificativa": justificativa,
                "ip_address": client_ip,
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
            },
        )

        return Response(
            {
                "detail": "Solicitação reprovada.",
                "solicitacao": SolicitacaoSerializer(solicitacao).data,
            },
            status=status.HTTP_200_OK,
        )


class AvailabilityBlockViewSet(viewsets.ModelViewSet):
    """
    ViewSet para Bloqueios de Disponibilidade.

    Formadores podem criar bloqueios para si mesmos.
    Usuario é preenchido automaticamente com request.user.
    """

    queryset = AvailabilityBlock.objects.all()
    serializer_class = AvailabilityBlockSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filtrar bloqueios por usuário (exceto Superintendência/superuser que vê todos).
        """
        if (
            self.request.user.is_superuser
            or self.request.user.groups.filter(name="Superintendência").exists()
        ):
            return AvailabilityBlock.objects.all()
        return AvailabilityBlock.objects.filter(usuario=self.request.user)

    def perform_create(self, serializer):
        """
        Preenche usuario automaticamente com request.user ao criar bloqueio.
        """
        serializer.save(usuario=self.request.user)


class CurrentUserView(APIView):
    """
    Endpoint que retorna informações do usuário autenticado.

    GET /api/me/
    Retorna:
        {
            "id": int,
            "username": str,
            "email": str,
            "first_name": str,
            "last_name": str,
            "groups": list[str],
            "is_superintendencia": bool
        }
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        groups = list(user.groups.values_list("name", flat=True))
        # Superusers sempre têm acesso completo
        is_superintendencia = user.is_superuser or ("Superintendência" in groups)

        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "groups": groups,
                "is_superuser": user.is_superuser,
                "is_superintendencia": is_superintendencia,
            },
            status=status.HTTP_200_OK,
        )


class AvailabilityCheckView(APIView):
    """
    Endpoint de checagem de disponibilidade (RD-01 a RD-08).

    GET /api/availability/check/
    Query params:
        - usuario_id (obrigatório): ID do usuário
        - inicio (obrigatório): ISO8601 datetime
        - fim (obrigatório): ISO8601 datetime
        - municipio_id (opcional): ID do município

    Retorna:
        {
            "ok": bool,
            "conflicts": [
                {"code": "X"|"T"|"P"|"D"|"M", "title": str, "detail": str, "ref_id": int|null}
            ]
        }

    Nota: Checagem consultiva. NÃO altera estado, NÃO aprova nada.

    Rate Limit: 60 requisições por minuto (ScopedRateThrottle)
    """

    permission_classes = [IsAuthenticated]
    throttle_scope = "availability_check"

    def get(self, request):
        # Extrair e validar usuario_id
        usuario_id_raw = request.query_params.get("usuario_id")
        if not usuario_id_raw:
            return Response(
                {"detail": "usuario_id é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            usuario_id = int(usuario_id_raw)
        except (TypeError, ValueError):
            return Response(
                {"detail": "usuario_id inválido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            usuario = Usuario.objects.get(pk=usuario_id)
        except Usuario.DoesNotExist:
            return Response(
                {"detail": "Usuário não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # municipio_id é opcional
        municipio_id_raw = request.query_params.get("municipio_id")
        municipio = None
        if municipio_id_raw:
            try:
                municipio_id = int(municipio_id_raw)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "municipio_id inválido."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            municipio = Municipio.objects.filter(pk=municipio_id).first()

        # datas
        inicio_raw = request.query_params.get("inicio")
        fim_raw = request.query_params.get("fim")
        if not inicio_raw or not fim_raw:
            return Response(
                {"detail": "inicio e fim são obrigatórios."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        inicio = parse_datetime(inicio_raw)
        fim = parse_datetime(fim_raw)
        if not inicio or not fim:
            return Response(
                {"detail": "Datas inválidas. Use ISO8601."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if fim <= inicio:
            return Response(
                {"detail": "fim deve ser posterior a inicio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Garantir timezone-aware (RD-06)
        if timezone.is_naive(inicio):
            inicio = timezone.make_aware(inicio, timezone.utc)
        if timezone.is_naive(fim):
            fim = timezone.make_aware(fim, timezone.utc)

        # Executar checagem
        result = check_conflicts(
            usuario=usuario, inicio=inicio, fim=fim, municipio=municipio
        )

        # Retornar resultado
        return Response(
            {
                "ok": result.ok,
                "conflicts": [c.__dict__ for c in result.conflicts],
            },
            status=status.HTTP_200_OK,
        )


class AvailabilityCheckManyView(APIView):
    """
    Endpoint de checagem de disponibilidade em lote (PR 8/N).

    POST /api/availability/check-many/
    Body:
        {
            "usuarios_ids": [1, 2, 3],
            "inicio": "2025-10-15T08:00:00Z",
            "fim": "2025-10-15T12:00:00Z",
            "municipio_id": 1
        }

    Retorna:
        {
            "ok": bool,  # true se TODOS usuários estão disponíveis
            "results": [
                {
                    "usuario_id": int,
                    "ok": bool,
                    "conflicts": [
                        {"code": "X"|"T"|"P"|"D"|"M", "title": str, "detail": str, "ref_id": int|null}
                    ]
                }
            ]
        }

    Nota: Checagem consultiva. NÃO altera estado, NÃO aprova nada.
    """

    permission_classes = [IsAuthenticated]
    throttle_scope = "availability_check"

    def post(self, request):
        # Validar payload
        usuarios_ids = request.data.get("usuarios_ids", [])
        if not usuarios_ids or not isinstance(usuarios_ids, list):
            return Response(
                {"detail": "usuarios_ids deve ser uma lista não-vazia."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validar datas
        inicio_raw = request.data.get("inicio")
        fim_raw = request.data.get("fim")
        if not inicio_raw or not fim_raw:
            return Response(
                {"detail": "inicio e fim são obrigatórios."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        inicio = parse_datetime(inicio_raw)
        fim = parse_datetime(fim_raw)
        if not inicio or not fim:
            return Response(
                {"detail": "Datas inválidas. Use ISO8601."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if fim <= inicio:
            return Response(
                {"detail": "fim deve ser posterior a inicio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Garantir timezone-aware (RD-06)
        if timezone.is_naive(inicio):
            inicio = timezone.make_aware(inicio, timezone.utc)
        if timezone.is_naive(fim):
            fim = timezone.make_aware(fim, timezone.utc)

        # Validar municipio_id (opcional)
        municipio_id = request.data.get("municipio_id")
        municipio = None
        if municipio_id:
            try:
                municipio = Municipio.objects.get(pk=municipio_id)
            except Municipio.DoesNotExist:
                return Response(
                    {"detail": f"Município {municipio_id} não encontrado."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        # Executar checagem para cada usuário
        results = []
        all_ok = True

        for usuario_id in usuarios_ids:
            try:
                usuario = Usuario.objects.get(pk=usuario_id)
            except Usuario.DoesNotExist:
                results.append(
                    {
                        "usuario_id": usuario_id,
                        "ok": False,
                        "conflicts": [
                            {
                                "code": "X",
                                "title": "Usuário não encontrado",
                                "detail": f"Usuário {usuario_id} não existe.",
                                "ref_id": None,
                            }
                        ],
                    }
                )
                all_ok = False
                continue

            # Executar checagem
            result = check_conflicts(
                usuario=usuario, inicio=inicio, fim=fim, municipio=municipio
            )

            results.append(
                {
                    "usuario_id": usuario_id,
                    "ok": result.ok,
                    "conflicts": [c.__dict__ for c in result.conflicts],
                }
            )

            if not result.ok:
                all_ok = False

        # Retornar resultado agregado
        return Response(
            {
                "ok": all_ok,
                "results": results,
            },
            status=status.HTTP_200_OK,
        )


# ==========================
# Admin ViewSets (PR 7/N)
# ==========================


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
    - search: busca textual em nome, codigo, descricao
    - ordering: nome, id
    """

    queryset = Projeto.objects.all()
    serializer_class = ProjetoSerializer
    permission_classes = [IsDAT]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["ativo"]
    search_fields = ["nome", "codigo", "descricao"]
    ordering_fields = ["nome", "id"]
    ordering = ["nome"]


# ==========================
# TODO(GAP-004): Views comentadas até modelos serem implementados
# ==========================

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


# TODO(GAP-004): UsuarioAdminViewSet requer UsuarioAdminSerializer não implementado
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

        GAP-003 (resolvido): Endpoint para vincular usuários a grupos.
        Iteração 3 - Fase 1 Plano DAT/GCal.
        """
        usuario = self.get_object()
        group_ids = request.data.get("group_ids", [])

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

    queryset = Group.objects.prefetch_related("permissions").all()
    serializer_class = GroupSerializer
    permission_classes = [IsDAT]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name", "id"]
    ordering = ["name"]


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


# TODO(GAP-004): ImportComprasView requer import_compras_from_file não implementado
class ImportComprasView(APIView):
    """
    Endpoint de importação de Compras via CSV/XLSX.

    POST /api/import/compras/
    Content-Type: multipart/form-data
    Body: file (CSV ou XLSX)
    Query params: dry_run=true (opcional, para validação sem salvar)

    Permissões: Controle ou DAT

    Retorna:
        {
            "success": true,
            "result": {
                "inserted": int,
                "updated": int,
                "skipped": int,
                "rejected": int,
                "errors": [str]
            }
        }

    Observações:
    - Idempotência via external_hash (SHA256)
    - Auto-cria Município e Projeto se não existirem
    - Transacional: rollback em caso de erro crítico
    - Salva resultado em out/etl/last_run.json
    - Cria entrada em AuditLog

    NOTA: Temporariamente desabilitado até implementação de import_compras_from_file
    """

    permission_classes = [IsControleOrDAT]

    def post(self, request):
        # TODO(GAP-004): Implementar import_compras_from_file antes de habilitar
        return Response(
            {"detail": "Import de compras temporariamente desabilitado (GAP-004)"},
            status=status.HTTP_501_NOT_IMPLEMENTED
        )


# ==========================
# Options API ViewSets (PR 8/N)
# ==========================


class MunicipioOptionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet read-only para dropdown de municípios.

    GET /api/options/municipios/?search=<termo>
    Retorna: [{id, nome, uf}]

    Permissões: IsAuthenticated (todos usuários logados)
    Busca: Server-side por nome e UF
    """

    queryset = Municipio.objects.filter(ativo=True).order_by("nome")
    serializer_class = MunicipioOptionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Sem paginação para dropdowns
    filter_backends = [SearchFilter]
    search_fields = ["nome", "uf"]


class ProjetoOptionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet read-only para dropdown de projetos.

    GET /api/options/projetos/?search=<termo>
    Retorna: [{id, nome, codigo}]

    Permissões: IsAuthenticated (todos usuários logados)
    Busca: Server-side por nome e código
    """

    queryset = Projeto.objects.filter(ativo=True).order_by("nome")
    serializer_class = ProjetoOptionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Sem paginação para dropdowns
    filter_backends = [SearchFilter]
    search_fields = ["nome", "codigo"]


class CoordenadorOptionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet read-only para dropdown de coordenadores.

    GET /api/options/coordenadores/?search=<termo>
    Retorna: [{id, username, nome_completo, email}]

    Permissões: IsAuthenticated (todos usuários logados)
    Filtro: Apenas usuários do grupo "Coordenador" ou superusers
    Busca: Server-side por username, nome, sobrenome e email
    """

    serializer_class = UsuarioOptionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Sem paginação para dropdowns
    filter_backends = [SearchFilter]
    search_fields = ["username", "first_name", "last_name", "email"]

    def get_queryset(self):
        """Retorna apenas usuários coordenadores ativos"""
        return (
            Usuario.objects.filter(is_active=True, groups__name="Coordenador")
            .distinct()
            .order_by("first_name", "last_name")
        )


class FormadorOptionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet read-only para dropdown de formadores.

    GET /api/options/formadores/?search=<termo>
    Retorna: [{id, username, nome_completo, email}]

    Permissões: IsAuthenticated (todos usuários logados)
    Filtro: Apenas usuários do grupo "Formador" ou superusers
    Busca: Server-side por username, nome, sobrenome e email
    """

    serializer_class = UsuarioOptionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Sem paginação para dropdowns
    filter_backends = [SearchFilter]
    search_fields = ["username", "first_name", "last_name", "email"]

    def get_queryset(self):
        """Retorna apenas usuários formadores ativos"""
        return (
            Usuario.objects.filter(is_active=True, groups__name="Formador")
            .distinct()
            .order_by("first_name", "last_name")
        )


class TipoEventoOptionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet read-only para dropdown de tipos de evento.

    GET /api/options/tipos-evento/?search=<termo>
    Retorna: [{id, nome, descricao}]

    Permissões: IsAuthenticated (todos usuários logados)
    Busca: Server-side por nome e descrição
    """

    queryset = TipoEvento.objects.all().order_by("nome")
    serializer_class = TipoEventoOptionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Sem paginação para dropdowns
    filter_backends = [SearchFilter]
    search_fields = ["nome", "descricao"]

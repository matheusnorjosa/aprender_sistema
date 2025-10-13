"""
Core views

PA-01: Nenhuma solicitação é auto-aprovada.
PA-02: Apenas Superintendência pode aprovar/reprovar.
PA-05: Registrar usuário, data/hora e justificativa em LogAuditoria.
"""

import logging

from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AvailabilityBlock, Municipio, Solicitacao, Usuario
from .permissions import IsSuperintendencia
from .serializers import AvailabilityBlockSerializer, SolicitacaoSerializer
from .services.availability_service import check_conflicts

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
    """

    queryset = Solicitacao.objects.all()
    serializer_class = SolicitacaoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filtrar solicitações por usuário (exceto Superintendência que vê todas).
        """
        if self.request.user.groups.filter(name="Superintendência").exists():
            return Solicitacao.objects.all()
        return Solicitacao.objects.filter(usuario=self.request.user)

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

        solicitacao.status = "aprovado"
        solicitacao.save()

        # ================================================================
        # PA-05: Log estruturado de auditoria
        # ================================================================
        client_ip = _get_client_ip(request)
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
                "justificativa": request.data.get("justificativa", ""),
                "timestamp": timezone.now().isoformat(),
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
        Body: {"justificativa": "..."} # obrigatório
        """
        solicitacao = self.get_object()
        justificativa = request.data.get("justificativa", "")

        if not justificativa:
            return Response(
                {"detail": "Justificativa é obrigatória para reprovar."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if solicitacao.status == "reprovado":
            return Response(
                {"detail": "Solicitação já está reprovada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        solicitacao.status = "reprovado"
        solicitacao.save()

        # ================================================================
        # PA-05: Log estruturado de auditoria
        # ================================================================
        client_ip = _get_client_ip(request)
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
        Filtrar bloqueios por usuário (exceto Superintendência que vê todos).
        """
        if self.request.user.groups.filter(name="Superintendência").exists():
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
            "last_name": str
        }
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
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
        # Extrair parâmetros
        usuario_id = request.query_params.get("usuario_id")
        inicio_s = request.query_params.get("inicio")
        fim_s = request.query_params.get("fim")
        municipio_id = request.query_params.get("municipio_id")

        # Validar parâmetros obrigatórios
        if not (usuario_id and inicio_s and fim_s):
            return Response(
                {"detail": "usuario_id, inicio, fim são obrigatórios."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Buscar usuário
        try:
            usuario = Usuario.objects.get(id=usuario_id)
        except Usuario.DoesNotExist:
            return Response(
                {"detail": f"Usuário {usuario_id} não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Parsear datas
        inicio = parse_datetime(inicio_s)
        fim = parse_datetime(fim_s)

        if not inicio or not fim:
            return Response(
                {"detail": "inicio e fim devem estar em formato ISO8601."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Garantir timezone-aware (RD-06)
        if timezone.is_naive(inicio):
            inicio = timezone.make_aware(inicio, timezone.utc)
        if timezone.is_naive(fim):
            fim = timezone.make_aware(fim, timezone.utc)

        # Buscar município (opcional)
        municipio = None
        if municipio_id:
            try:
                municipio = Municipio.objects.get(id=municipio_id)
            except Municipio.DoesNotExist:
                return Response(
                    {"detail": f"Município {municipio_id} não encontrado."},
                    status=status.HTTP_404_NOT_FOUND,
                )

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

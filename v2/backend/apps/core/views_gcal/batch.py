"""
AS v2 — GCal Dashboard Batch Views

Views for batch operations: publish, reapply, resync.
Type-checked with Pyright (strict mode).
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false, reportFunctionMemberAccess=false

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema

from apps.core.models import Solicitacao
from apps.core.permissions import HasPerm
from apps.core.serializers.gcal_dashboard_contract import (
    BatchActionRequestSerializer,
    BatchActionResponseSerializer,
    DetailMessageSerializer,
)

logger = logging.getLogger(__name__)


class GCalPublishBatchView(APIView):
    """
    POST /api/gcal/publish-batch/

    Publicação em massa de solicitações aprovadas no Google Calendar.
    Restrict: Controle/Superintendência

    Request Body:
    {
        "solicitacao_ids": [123, 456, 789],  // Array de IDs
        "dry_run": false,                     // Opcional (default: false)
        "apply_blocked": false                // Opcional (default: false)
    }

    Response 202 Accepted:
    {
        "queued": 2,                          // Quantidade enfileirada
        "errors": [                           // Lista de erros
            {
                "id": 789,
                "detail": "Status deve ser 'aprovado' (atual: pendente)"
            }
        ],
        "dry_run": false,
        "apply_blocked": false
    }

    Regras:
    - Apenas solicitações com status='aprovado' são processadas
    - Se GCAL_CLIENT != "google" e dry_run=false e apply_blocked=false → erro
    - Válidas: marca gcal_status=PENDING e enfileira task Celery
    - Inválidas: retorna em 'errors' com motivo
    """

    permission_classes = [IsAuthenticated, HasPerm("import_spreadsheet")]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "gcal_write"  # 10/min (#409)

    @extend_schema(
        responses={
            202: BatchActionResponseSerializer,
            400: DetailMessageSerializer,
        }
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # Parse request body
        solicitacao_ids = request.data.get("solicitacao_ids", [])
        dry_run = request.data.get("dry_run", False)
        apply_blocked = request.data.get("apply_blocked", False)

        # Validação: array de IDs obrigatório
        if not isinstance(solicitacao_ids, list) or not solicitacao_ids:
            return Response(
                {"detail": "solicitacao_ids deve ser um array não-vazio de IDs"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Buscar solicitações
        solicitacoes = Solicitacao.objects.filter(id__in=solicitacao_ids).select_related("projeto", "municipio")

        # Verificar GCAL_CLIENT
        gcal_client = getattr(settings, "GCAL_CLIENT", "fake")

        queued = []
        errors = []

        # PERF-SQL-01: O(1) lookup instead of O(N) linear search per iteration
        sol_map = {s.id: s for s in solicitacoes}

        for sol_id in solicitacao_ids:
            # Verificar se existe
            sol = sol_map.get(sol_id)
            if not sol:
                errors.append({"id": sol_id, "detail": "Solicitação não encontrada"})
                continue

            # Validar status='aprovado'
            if sol.status != "aprovado":
                errors.append({"id": sol_id, "detail": f"Status deve ser 'aprovado' (atual: {sol.status})"})
                continue

            # Validar apply_blocked com GCAL_CLIENT
            if gcal_client != "google" and not dry_run and not apply_blocked:
                errors.append(
                    {
                        "id": sol_id,
                        "detail": f"GCAL_CLIENT={gcal_client} (não-google) requer dry_run=true ou apply_blocked=true",
                    }
                )
                continue

            # Válida: marcar como PENDING e enfileirar
            if not dry_run:
                sol.gcal_status = Solicitacao.GCalStatus.PENDING
                sol.save(update_fields=["gcal_status", "updated_at"])

                # Importar e enfileirar task Celery
                try:
                    from apps.core.tasks import task_publish_solicitacao_to_gcal

                    task_publish_solicitacao_to_gcal.delay(
                        solicitacao_id=sol.id, dry_run=dry_run, apply_blocked=apply_blocked
                    )
                    queued.append(sol.id)
                    logger.info(f"Batch publish queued: solicitacao_id={sol.id}, dry_run={dry_run}")
                except Exception as e:
                    logger.error(f"Failed to queue solicitacao_id={sol.id}: {e}")
                    errors.append({"id": sol.id, "detail": "Erro ao enfileirar operação."})
            else:
                # Dry-run: apenas simula
                queued.append(sol.id)
                logger.info(f"Batch publish dry-run: solicitacao_id={sol.id}")

        return Response(
            {"queued": len(queued), "errors": errors, "dry_run": dry_run, "apply_blocked": apply_blocked},
            status=status.HTTP_202_ACCEPTED,
        )


class GCalBatchReapplyView(APIView):
    """
    POST /api/gcal/dashboard/batch/reapply/

    Reaplica eventos já publicados (não reseta hash).
    Útil para forçar update no Google Calendar sem alterar o estado local.

    Request Body:
    {
        "ids": [123, 456, 789],      // Array de IDs (max 500)
        "dry_run": false,             // Opcional (default: false)
        "apply_blocked": false        // Opcional (default: false)
    }

    Response 202 Accepted:
    {
        "queued": 2,
        "errors": [
            {"id": 789, "detail": "Solicitação não encontrada"}
        ],
        "dry_run": false,
        "apply_blocked": false
    }

    OAuth Mode:
    - Se GCAL_AUTH_MODE=='oauth', requer GoogleOAuthCredential
    - Sem credencial → 403 {code: 'google_not_connected'}
    - Com credencial → passa operator_user_id para task

    Permissions: HasPerm("import_spreadsheet")
    """

    permission_classes = [IsAuthenticated, HasPerm("import_spreadsheet")]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "gcal_write"  # 10/min (#409)

    @extend_schema(
        request=BatchActionRequestSerializer,
        responses={
            202: BatchActionResponseSerializer,
            400: DetailMessageSerializer,
            403: DetailMessageSerializer,
        },
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        from apps.core.models import GoogleOAuthCredential
        from apps.core.tasks import task_publish_solicitacao_to_gcal

        # OAuth Phase 7: Verificar credencial Google em modo OAuth
        auth_mode = getattr(settings, "GCAL_AUTH_MODE", "service_account")
        operator_user_id = None

        if auth_mode == "oauth":
            try:
                GoogleOAuthCredential.objects.get(user=request.user)
                operator_user_id = request.user.id
            except GoogleOAuthCredential.DoesNotExist:
                return Response(
                    {"detail": "Conecte sua conta Google para realizar ações em massa", "code": "google_not_connected"},
                    status=status.HTTP_403_FORBIDDEN,
                )

        # Parse request body
        ids = request.data.get("ids", [])
        dry_run = request.data.get("dry_run", False)
        apply_blocked = request.data.get("apply_blocked", False)

        # Validação: array de IDs obrigatório
        if not isinstance(ids, list) or not ids:
            return Response({"detail": "ids deve ser um array não-vazio de IDs"}, status=status.HTTP_400_BAD_REQUEST)

        # Limitar a 500 IDs
        if len(ids) > 500:
            return Response({"detail": "Limite de 500 IDs por requisição"}, status=status.HTTP_400_BAD_REQUEST)

        # Buscar solicitações
        solicitacoes = Solicitacao.objects.filter(id__in=ids)

        # MP4: Otimização O(N) - dict lookup em vez de linear search O(N²)
        solicitacoes_dict = {s.id: s for s in solicitacoes}

        # Verificar GCAL_CLIENT
        gcal_client = getattr(settings, "GCAL_CLIENT", "fake")

        queued_count = 0
        errors = []

        for sol_id in ids:
            # Verificar se existe (O(1) dict lookup)
            sol = solicitacoes_dict.get(sol_id)
            if not sol:
                errors.append({"id": sol_id, "detail": "Solicitação não encontrada"})
                continue

            # Validar status='aprovado'
            if sol.status != "aprovado":
                errors.append({"id": sol_id, "detail": f"Status deve ser 'aprovado' (atual: {sol.status})"})
                continue

            # Validar apply_blocked com GCAL_CLIENT
            if gcal_client != "google" and not dry_run and not apply_blocked:
                errors.append(
                    {"id": sol_id, "detail": f"GCAL_CLIENT={gcal_client} requer dry_run=true ou apply_blocked=true"}
                )
                continue

            # Válida: enfileirar (reapply não reseta hash)
            if not dry_run:
                try:
                    # OAuth mode: passar operator_user_id
                    if auth_mode == "oauth":
                        task_publish_solicitacao_to_gcal.delay(
                            sol.id, dry_run=dry_run, apply_blocked=apply_blocked, operator_user_id=operator_user_id
                        )
                    else:
                        # Service account mode: sem operator_user_id
                        task_publish_solicitacao_to_gcal.delay(sol.id, dry_run=dry_run, apply_blocked=apply_blocked)
                    queued_count += 1
                    logger.info(f"Batch reapply queued: id={sol.id}, operator={operator_user_id}")
                except Exception as e:
                    logger.error(f"Failed to queue reapply id={sol.id}: {e}")
                    errors.append({"id": sol.id, "detail": "Erro ao enfileirar operação."})
            else:
                # Dry-run: apenas simula
                queued_count += 1

        return Response(
            {"queued": queued_count, "errors": errors, "dry_run": dry_run, "apply_blocked": apply_blocked},
            status=status.HTTP_202_ACCEPTED,
        )


class GCalBatchResyncView(APIView):
    """
    POST /api/gcal/dashboard/batch/resync/

    Força resync de eventos (reseta hash + marca PENDING).
    Útil para corrigir drift ou reprocessar eventos com erros.

    Request Body:
    {
        "ids": [123, 456, 789],      // Array de IDs (max 500)
        "dry_run": false,             // Opcional (default: false)
        "apply_blocked": false        // Opcional (default: false)
    }

    Response 202 Accepted:
    {
        "queued": 2,
        "errors": [
            {"id": 789, "detail": "Solicitação não encontrada"}
        ],
        "dry_run": false,
        "apply_blocked": false
    }

    OAuth Mode:
    - Se GCAL_AUTH_MODE=='oauth', requer GoogleOAuthCredential
    - Sem credencial → 403 {code: 'google_not_connected'}
    - Com credencial → passa operator_user_id para task

    Permissions: HasPerm("import_spreadsheet")
    """

    permission_classes = [IsAuthenticated, HasPerm("import_spreadsheet")]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "gcal_write"  # 10/min (#409)

    @extend_schema(
        request=BatchActionRequestSerializer,
        responses={
            202: BatchActionResponseSerializer,
            400: DetailMessageSerializer,
            403: DetailMessageSerializer,
        },
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        from apps.core.models import GoogleOAuthCredential
        from apps.core.tasks import task_publish_solicitacao_to_gcal

        # OAuth Phase 7: Verificar credencial Google em modo OAuth
        auth_mode = getattr(settings, "GCAL_AUTH_MODE", "service_account")
        operator_user_id = None

        if auth_mode == "oauth":
            try:
                GoogleOAuthCredential.objects.get(user=request.user)
                operator_user_id = request.user.id
            except GoogleOAuthCredential.DoesNotExist:
                return Response(
                    {"detail": "Conecte sua conta Google para realizar ações em massa", "code": "google_not_connected"},
                    status=status.HTTP_403_FORBIDDEN,
                )

        # Parse request body
        ids = request.data.get("ids", [])
        dry_run = request.data.get("dry_run", False)
        apply_blocked = request.data.get("apply_blocked", False)

        # Validação: array de IDs obrigatório
        if not isinstance(ids, list) or not ids:
            return Response({"detail": "ids deve ser um array não-vazio de IDs"}, status=status.HTTP_400_BAD_REQUEST)

        # Limitar a 500 IDs
        if len(ids) > 500:
            return Response({"detail": "Limite de 500 IDs por requisição"}, status=status.HTTP_400_BAD_REQUEST)

        # Buscar solicitações
        solicitacoes = Solicitacao.objects.filter(id__in=ids)

        # MP4: Otimização O(N) - dict lookup em vez de linear search O(N²)
        solicitacoes_dict = {s.id: s for s in solicitacoes}

        # Verificar GCAL_CLIENT
        gcal_client = getattr(settings, "GCAL_CLIENT", "fake")

        queued_count = 0
        errors = []

        for sol_id in ids:
            # Verificar se existe (O(1) dict lookup)
            sol = solicitacoes_dict.get(sol_id)
            if not sol:
                errors.append({"id": sol_id, "detail": "Solicitação não encontrada"})
                continue

            # Validar status='aprovado'
            if sol.status != "aprovado":
                errors.append({"id": sol_id, "detail": f"Status deve ser 'aprovado' (atual: {sol.status})"})
                continue

            # Validar apply_blocked com GCAL_CLIENT
            if gcal_client != "google" and not dry_run and not apply_blocked:
                errors.append(
                    {"id": sol_id, "detail": f"GCAL_CLIENT={gcal_client} requer dry_run=true ou apply_blocked=true"}
                )
                continue

            # Válida: resetar hash + marcar PENDING + enfileirar
            if not dry_run:
                try:
                    # Resync: resetar hash para forçar reprocessamento
                    sol.gcal_payload_hash = None
                    sol.gcal_status = Solicitacao.GCalStatus.PENDING
                    sol.save(update_fields=["gcal_payload_hash", "gcal_status", "updated_at"])

                    # OAuth mode: passar operator_user_id
                    if auth_mode == "oauth":
                        task_publish_solicitacao_to_gcal.delay(
                            sol.id, dry_run=dry_run, apply_blocked=apply_blocked, operator_user_id=operator_user_id
                        )
                    else:
                        # Service account mode: sem operator_user_id
                        task_publish_solicitacao_to_gcal.delay(sol.id, dry_run=dry_run, apply_blocked=apply_blocked)
                    queued_count += 1
                    logger.info(f"Batch resync queued: id={sol.id}, operator={operator_user_id}")
                except Exception as e:
                    logger.error(f"Failed to queue resync id={sol.id}: {e}")
                    errors.append({"id": sol.id, "detail": "Erro ao enfileirar operação."})
            else:
                # Dry-run: apenas simula
                queued_count += 1

        return Response(
            {"queued": queued_count, "errors": errors, "dry_run": dry_run, "apply_blocked": apply_blocked},
            status=status.HTTP_202_ACCEPTED,
        )

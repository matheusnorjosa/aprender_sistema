"""
AS v2 — GCal Dashboard Batch Views

Views for batch operations: publish, reapply, resync.
Type-checked with Pyright (strict mode).
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false, reportFunctionMemberAccess=false

from __future__ import annotations

import logging
from typing import Any, Literal

from django.conf import settings
from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema

from apps.core.exceptions import APIError
from apps.core.models import Solicitacao
from apps.core.rbac.policies import CanUseGcal
from apps.core.serializers.gcal_dashboard_contract import (
    BatchActionRequestSerializer,
    BatchActionResponseSerializer,
    DetailMessageSerializer,
)
from apps.core.services.solicitacao_publish import (
    MENSAGENS_NAO_PUBLICAVEL,
    enfileirar_tarefa_gcal,
    motivo_nao_publicavel,
    pedir_operacao_gcal,
)

logger = logging.getLogger(__name__)

_FILA_INDISPONIVEL = "fila_indisponivel"


def _pedir_e_enfileirar(
    sol_id: int,
    operacao: Literal["publicar", "reaplicar", "reenviar"],
    *,
    apply_blocked: bool,
    operator_user_id: int | None,
) -> dict[str, Any] | None:
    """Pedido e tarefa de um id numa transação só (DEF-32). Devolve o item de `errors`, ou None se enfileirou.

    A recusa relida sob a trava, a linha ocupada além do teto e a fila fora do ar desfazem a transação
    deste id: a linha fica como estava. Fila fora do ar sai com `code=fila_indisponivel`, e quem chama para o laço.
    """
    from apps.core.tasks import task_publish_solicitacao_to_gcal

    kwargs: dict[str, Any] = {"dry_run": False, "apply_blocked": apply_blocked}
    if operator_user_id is not None:  # modo OAuth
        kwargs["operator_user_id"] = operator_user_id
    try:
        with transaction.atomic():
            pedido = pedir_operacao_gcal(sol_id, operacao)
            enfileirar_tarefa_gcal(task_publish_solicitacao_to_gcal, sol_id, **kwargs, pedido=pedido)
    except Solicitacao.DoesNotExist:
        return {"id": sol_id, "detail": "Solicitação não encontrada"}
    except APIError as e:
        return {"id": sol_id, "detail": e.message, "code": e.details.get("code") or e.code}
    return None


def _nao_enfileirados(ids: list[Any]) -> list[dict[str, Any]]:
    """Itens de `errors` dos ids que o lote nem tentou, porque a fila caiu antes deles."""
    return [
        {
            "id": sol_id,
            "detail": "Não enfileirado: a fila de publicação está indisponível. Tente de novo em instantes.",
            "code": _FILA_INDISPONIVEL,
        }
        for sol_id in ids
    ]


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
    - Recusa (com `code`) evento passado, já publicado e publicado fora do sistema (`motivo_nao_publicavel`)
    - Se GCAL_CLIENT != "google" e dry_run=false e apply_blocked=false → erro
    - Válidas: marca gcal_status=PENDING e enfileira task Celery (uma transação por id, com a linha travada)
    - Inválidas: retorna em 'errors' com motivo
    - Fila fora do ar: o id da vez não fica PENDING, o lote para e os restantes vão para 'errors'
      (code='fila_indisponivel')

    OAuth Mode (#2039, igual a reapply/resync):
    - Se GCAL_AUTH_MODE=='oauth', requer GoogleOAuthCredential
    - Sem credencial → 403 {code: 'google_not_connected'} (nada é alterado)
    - Com credencial → passa operator_user_id para task
    """

    permission_classes = [IsAuthenticated, CanUseGcal]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "gcal_write"  # 10/min (#409)

    @extend_schema(
        responses={
            202: BatchActionResponseSerializer,
            400: DetailMessageSerializer,
            403: DetailMessageSerializer,
        }
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        from apps.core.models import GoogleOAuthCredential

        # OAuth: verificar credencial Google ANTES de mexer em qualquer linha (#2039)
        auth_mode = getattr(settings, "GCAL_AUTH_MODE", "service_account")
        operator_user_id = None

        if auth_mode == "oauth":
            try:
                GoogleOAuthCredential.objects.get(user=request.user)
                operator_user_id = request.user.pk
            except GoogleOAuthCredential.DoesNotExist:
                return Response(
                    {"detail": "Conecte sua conta Google para realizar ações em massa", "code": "google_not_connected"},
                    status=status.HTTP_403_FORBIDDEN,
                )

        # Parse request body
        solicitacao_ids = request.data.get("solicitacao_ids", [])
        dry_run = request.data.get("dry_run", False)
        apply_blocked = request.data.get("apply_blocked", False)

        # Validação: array de IDs obrigatório
        if not isinstance(solicitacao_ids, list) or not solicitacao_ids:
            return Response(
                {"detail": "solicitacao_ids deve ser um array não-vazio de IDs"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Limitar a 500 IDs (espelha reapply/resync; evita rajada de INSERTs + logs por request)
        if len(solicitacao_ids) > 500:
            return Response({"detail": "Limite de 500 IDs por requisição"}, status=status.HTTP_400_BAD_REQUEST)

        # Buscar solicitações
        solicitacoes = Solicitacao.objects.filter(id__in=solicitacao_ids).select_related(
            "projeto", "projeto_2", "municipio"
        )

        # Verificar GCAL_CLIENT
        gcal_client = getattr(settings, "GCAL_CLIENT", "fake")

        queued = []
        errors = []

        # PERF-SQL-01: O(1) lookup instead of O(N) linear search per iteration
        sol_map = {s.id: s for s in solicitacoes}

        for posicao, sol_id in enumerate(solicitacao_ids):
            # Verificar se existe
            sol = sol_map.get(sol_id)
            if not sol:
                errors.append({"id": sol_id, "detail": "Solicitação não encontrada"})
                continue

            # Validar status='aprovado'
            if sol.status != "aprovado":
                errors.append({"id": sol_id, "detail": f"Status deve ser 'aprovado' (atual: {sol.status})"})
                continue

            # Virada: passado, já publicado ou no Google pela planilha não vai (o upsert_one também barra).
            motivo = motivo_nao_publicavel(sol)
            if motivo is not None:
                errors.append({"id": sol_id, "detail": MENSAGENS_NAO_PUBLICAVEL[motivo], "code": motivo})
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

            # Válida: pedido (PENDING sob trava) e tarefa, numa transação por id. O id vai POSICIONAL:
            # a task recebe `solicitation_id` (M24-01).
            if not dry_run:
                erro = _pedir_e_enfileirar(
                    sol.id, "publicar", apply_blocked=apply_blocked, operator_user_id=operator_user_id
                )
                if erro is None:
                    queued.append(sol.id)
                    logger.info(f"Batch publish queued: solicitacao_id={sol.id}, dry_run={dry_run}")
                    continue
                errors.append(erro)
                if erro.get("code") == _FILA_INDISPONIVEL:
                    errors.extend(_nao_enfileirados(solicitacao_ids[posicao + 1 :]))
                    break
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

    Reaplica eventos já publicados: marca PENDING e mantém o hash da linha PUBLISHED, então o evento sem
    mudança vira SKIP na tarefa e volta a PUBLISHED. Linha em ERROR ou PENDING perde o hash (o envio acontece).
    Fila fora do ar: como no publish-batch (o lote para; code='fila_indisponivel').

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

    Permissions: CanUseGcal (policy `use_gcal`)
    """

    permission_classes = [IsAuthenticated, CanUseGcal]
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

        for posicao, sol_id in enumerate(ids):
            # Verificar se existe (O(1) dict lookup)
            sol = solicitacoes_dict.get(sol_id)
            if not sol:
                errors.append({"id": sol_id, "detail": "Solicitação não encontrada"})
                continue

            # Validar status='aprovado'
            if sol.status != "aprovado":
                errors.append({"id": sol_id, "detail": f"Status deve ser 'aprovado' (atual: {sol.status})"})
                continue

            # Virada: só reenvia o que já foi ao Google e ainda não terminou. Em `NONE` o sync criaria.
            motivo = motivo_nao_publicavel(sol, reenvio=True)
            if motivo is not None:
                errors.append({"id": sol_id, "detail": MENSAGENS_NAO_PUBLICAVEL[motivo], "code": motivo})
                continue

            # Validar apply_blocked com GCAL_CLIENT
            if gcal_client != "google" and not dry_run and not apply_blocked:
                errors.append(
                    {"id": sol_id, "detail": f"GCAL_CLIENT={gcal_client} requer dry_run=true ou apply_blocked=true"}
                )
                continue

            # Válida: pedido (PENDING sob trava; o hash fica só em linha PUBLISHED) e tarefa, numa transação por id
            if not dry_run:
                erro = _pedir_e_enfileirar(
                    sol.id, "reaplicar", apply_blocked=apply_blocked, operator_user_id=operator_user_id
                )
                if erro is None:
                    queued_count += 1
                    logger.info(f"Batch reapply queued: id={sol.id}, operator={operator_user_id}")
                    continue
                errors.append(erro)
                if erro.get("code") == _FILA_INDISPONIVEL:
                    errors.extend(_nao_enfileirados(ids[posicao + 1 :]))
                    break
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
    Fila fora do ar: como no publish-batch (o lote para; code='fila_indisponivel').

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

    Permissions: CanUseGcal (policy `use_gcal`)
    """

    permission_classes = [IsAuthenticated, CanUseGcal]
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

        for posicao, sol_id in enumerate(ids):
            # Verificar se existe (O(1) dict lookup)
            sol = solicitacoes_dict.get(sol_id)
            if not sol:
                errors.append({"id": sol_id, "detail": "Solicitação não encontrada"})
                continue

            # Validar status='aprovado'
            if sol.status != "aprovado":
                errors.append({"id": sol_id, "detail": f"Status deve ser 'aprovado' (atual: {sol.status})"})
                continue

            # Virada: só reenvia o que já foi ao Google e ainda não terminou. Em `NONE` o sync criaria.
            motivo = motivo_nao_publicavel(sol, reenvio=True)
            if motivo is not None:
                errors.append({"id": sol_id, "detail": MENSAGENS_NAO_PUBLICAVEL[motivo], "code": motivo})
                continue

            # Validar apply_blocked com GCAL_CLIENT
            if gcal_client != "google" and not dry_run and not apply_blocked:
                errors.append(
                    {"id": sol_id, "detail": f"GCAL_CLIENT={gcal_client} requer dry_run=true ou apply_blocked=true"}
                )
                continue

            # Válida: pedido (PENDING sob trava, hash zerado para forçar o reenvio) e tarefa, numa transação por id
            if not dry_run:
                erro = _pedir_e_enfileirar(
                    sol.id, "reenviar", apply_blocked=apply_blocked, operator_user_id=operator_user_id
                )
                if erro is None:
                    queued_count += 1
                    logger.info(f"Batch resync queued: id={sol.id}, operator={operator_user_id}")
                    continue
                errors.append(erro)
                if erro.get("code") == _FILA_INDISPONIVEL:
                    errors.extend(_nao_enfileirados(ids[posicao + 1 :]))
                    break
            else:
                # Dry-run: apenas simula
                queued_count += 1

        return Response(
            {"queued": queued_count, "errors": errors, "dry_run": dry_run, "apply_blocked": apply_blocked},
            status=status.HTTP_202_ACCEPTED,
        )

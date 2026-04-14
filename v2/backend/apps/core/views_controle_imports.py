"""
Endpoints DRF para importação de Compras.

POST /api/controle/import-compras/
- Query param: dry_run=true|false (default: true)
- Body (multipart/form-data): {file: upload}
- Returns: Relatório com stats, pendências e IDs criados
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

import logging
import os
import tempfile
from typing import Any

from django.utils.datastructures import MultiValueDictKeyError
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import OpenApiParameter, extend_schema

from apps.core.api_schemas import COMMON_ERROR_RESPONSES
from apps.core.permissions import IsControleOrSuper
from apps.core.serializers.openapi_critical_contract import (
    ImportFileUploadRequestSerializer,
    ImportOperationErrorResponseSerializer,
    ImportOperationResponseSerializer,
)
from apps.core.services.controle_imports import import_compras_from_file

logger = logging.getLogger(__name__)

# Issue #569: Upload validation hardening (DoS/malicious file prevention)
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_CONTENT_TYPES = {
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


class ImportComprasView(APIView):
    """
    Importa Compras de CSV/XLSX.

    Requer permissão: IsControleOrSuper (grupos Controle ou Superintendência)

    Query params:
        dry_run: "true" (default) para preview, "false" para aplicar

    Body (multipart/form-data):
        file: Arquivo CSV/XLSX (upload obrigatório)

    Returns:
        {
            "path": "/tmp/xyz.csv",
            "dry_run": true,
            "stats": {"created": 10, "updated": 5, "skipped": 2, "errors": 0},
            "pendencias": {
                "municipios": [...],
                "projetos": [...],
                "linhas_invalidas": [...]
            },
            "created_ids": [...],
            "ts": "2025-10-21T..."
        }
    """

    permission_classes = [IsControleOrSuper]

    @extend_schema(
        summary="Importar compras",
        parameters=[
            OpenApiParameter(
                name="dry_run",
                location=OpenApiParameter.QUERY,
                required=False,
                type=bool,
                description="Quando true, executa validação sem persistir dados.",
            ),
        ],
        request=ImportFileUploadRequestSerializer,
        responses={
            200: ImportOperationResponseSerializer,
            400: ImportOperationErrorResponseSerializer,
            401: COMMON_ERROR_RESPONSES[401],
            403: COMMON_ERROR_RESPONSES[403],
            413: ImportOperationErrorResponseSerializer,
            500: ImportOperationErrorResponseSerializer,
        },
        tags=["imports"],
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # Parse dry_run query param
        dry_run_param = str(request.query_params.get("dry_run", "true")).lower()
        dry_run = dry_run_param in {"1", "true", "t", "yes", "y"}

        # Verificar arquivo
        try:
            upload = request.FILES["file"]
        except (KeyError, MultiValueDictKeyError):
            return Response({"detail": "Campo 'file' é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)

        if upload.size > MAX_UPLOAD_SIZE:
            return Response(
                {"detail": f"Arquivo muito grande. Máximo: {MAX_UPLOAD_SIZE / 1024 / 1024:.0f}MB"},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        if upload.content_type not in ALLOWED_CONTENT_TYPES:
            return Response(
                {"detail": f"Tipo de arquivo não permitido. Aceitos: CSV, XLS, XLSX. Recebido: {upload.content_type}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Salvar upload em /tmp via tempfile
        temp_file = None
        try:
            # Criar arquivo temporário com sufixo baseado no nome original
            suffix = os.path.splitext(upload.name)[1] or ".csv"
            temp_file = tempfile.NamedTemporaryFile(mode="wb", suffix=suffix, delete=False)

            for chunk in upload.chunks():
                temp_file.write(chunk)
            temp_file.close()

            # Executar import
            report = import_compras_from_file(path=temp_file.name, dry_run=dry_run)

            return Response(report, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("Erro ao processar arquivo de compras: %s", e)
            return Response(
                {"detail": "Erro ao processar arquivo. Verifique o formato e tente novamente."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        finally:
            # Sempre remover arquivo temporário
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                except Exception:
                    pass

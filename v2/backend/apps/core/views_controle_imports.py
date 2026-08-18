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
from typing import Any

from django.utils.datastructures import MultiValueDictKeyError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import OpenApiParameter, extend_schema

from apps.core.api_schemas import COMMON_ERROR_RESPONSES
from apps.core.permissions import HasPerm
from apps.core.serializers.openapi_critical_contract import (
    ImportFileUploadRequestSerializer,
    ImportOperationErrorResponseSerializer,
    ImportOperationResponseSerializer,
)
from apps.core.services.controle_imports import import_compras_from_file
from apps.core.upload_validators import safe_temp_upload_file, validate_upload

logger = logging.getLogger(__name__)


class ImportComprasView(APIView):
    """
    Importa Compras de CSV/XLSX.

    Requer permissão: HasPerm("import_spreadsheet") (grupo DAT, ou superuser).

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

    # PR-A1 DAT-Imports (2026-04-29): centralização. Importações de massa
    # passam a ser DAT-only via `HasPerm("import_spreadsheet")`. Controle
    # consome o dado mas não importa (D-1 do plano DAT-Imports).
    permission_classes = [IsAuthenticated, HasPerm("import_spreadsheet")]
    throttle_scope = "import"

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

        # S6 (#1742): valida tamanho + Content-Type + MAGIC BYTES (anti-spoofing),
        # igual aos ~10 outros endpoints de import (validate_upload). Antes so checava
        # size + content_type (header spoofavel). Devolve Response de erro ou None.
        upload_error = validate_upload(upload)
        if upload_error is not None:
            return upload_error

        # Salvar upload em /tmp via tempfile
        temp_file = None
        try:
            # Criar arquivo temporário com sufixo baseado no nome original
            # Issue #1343: Path-injection mitigation — sufixo sanitizado via allowlist,
            # nome original do upload nunca entra no path final (CodeQL py/path-injection).
            temp_file = safe_temp_upload_file(upload)

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

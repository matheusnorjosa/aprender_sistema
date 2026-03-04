"""
Endpoint DRF para importacao de Deslocamentos.

POST /api/deslocamentos/import/
- Permission: IsControleOrSuper
- Query param: dry_run=true|false (default: true)
- Body: {file: upload}
- Returns: Relatorio com stats, pendencias
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import os
import tempfile
from typing import Any

from django.utils.datastructures import MultiValueDictKeyError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
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
from apps.core.services.deslocamentos_import import import_deslocamentos_from_file
from apps.core.upload_validators import validate_upload


class ImportDeslocamentosView(APIView):
    """
    Importa Deslocamentos de CSV/XLSX.

    Requer permissao: IsControleOrSuper (grupos Controle ou Superintendencia)

    Query params:
        dry_run: "true" (default) para preview, "false" para aplicar

    Body (multipart/form-data):
        file: Arquivo CSV/XLSX (upload obrigatorio)

    Returns:
        {
            "stats": {"created": 10, "updated": 5, "unchanged": 2, "skipped": {...}},
            "pendencias": {
                "usuarios": [...],
                "dates": [...],
                "outros": [...]
            },
            "dry_run": true,
            "file": "/tmp/xyz.xlsx"
        }
    """

    permission_classes = [IsAuthenticated, IsControleOrSuper]

    @extend_schema(
        summary="Importar deslocamentos",
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
            return Response(
                {"detail": "Campo 'file' e obrigatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Issue #132/#747: Validar tamanho, MIME type e magic bytes
        error_response = validate_upload(upload)
        if error_response:
            return error_response

        # Salvar upload em /tmp via tempfile
        temp_file = None
        try:
            # Criar arquivo temporario com sufixo baseado no nome original
            suffix = os.path.splitext(upload.name)[1] or ".csv"
            temp_file = tempfile.NamedTemporaryFile(mode="wb", suffix=suffix, delete=False)

            for chunk in upload.chunks():
                temp_file.write(chunk)
            temp_file.close()

            # Executar import
            report = import_deslocamentos_from_file(path=temp_file.name, dry_run=dry_run)

            return Response(report, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"detail": f"Erro ao processar arquivo: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        finally:
            # Sempre remover arquivo temporario
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                except Exception:
                    pass

"""
Endpoint DRF para importacao de Usuarios.

POST /api/usuarios/import/
- Permission: HasPerm("manage_admin_registries")
- Query param: dry_run=true|false (default: true)
- Body: {file: upload}
- Returns: Relatorio com stats, pendencias
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false

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
from apps.core.services.usuarios_import import import_usuarios_from_file
from apps.core.upload_validators import safe_temp_upload_file, validate_upload

logger = logging.getLogger(__name__)


class ImportUsuariosView(APIView):
    """
    Importa Usuarios de CSV/XLSX.

    Requer permissao: HasPerm("manage_admin_registries") (grupos DAT ou Superintendencia, ou superuser)

    Query params:
        dry_run: "true" (default) para preview, "false" para aplicar

    Body (multipart/form-data):
        file: Arquivo CSV/XLSX (upload obrigatorio)

    Returns:
        {
            "stats": {"created": 10, "updated": 5, "unchanged": 2, "skipped": {...}},
            "pendencias": {
                "cpf_invalid": [...],
                "nome_missing": [...],
                "outros": [...]
            },
            "dry_run": true,
            "file": "/tmp/xyz.xlsx"
        }
    """

    permission_classes = [IsAuthenticated, HasPerm("manage_admin_registries")]

    @extend_schema(
        summary="Importar usuários",
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
            # Issue #1343: Path-injection mitigation — sufixo sanitizado via allowlist,
            # nome original do upload nunca entra no path final (CodeQL py/path-injection).
            temp_file = safe_temp_upload_file(upload)

            for chunk in upload.chunks():
                temp_file.write(chunk)
            temp_file.close()

            # Executar import
            report = import_usuarios_from_file(path=temp_file.name, dry_run=dry_run)

            return Response(report, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("Erro ao processar arquivo de usuarios: %s", e)
            return Response(
                {"detail": "Erro ao processar arquivo. Verifique o formato e tente novamente."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        finally:
            # Sempre remover arquivo temporario
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                except Exception:
                    pass

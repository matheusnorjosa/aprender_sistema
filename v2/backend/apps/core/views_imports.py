"""
Endpoints DRF para importação de Ações de Controle e Cadastros DAT.

POST /api/controle/import-acoes/
- Permission: HasPerm("import_spreadsheet")
- Query param: dry_run=true|false (default: true)
- Body: {file: upload}
- Returns: Relatório com stats, pendências

POST /api/dat/import-cadastros/
- Permission: HasPerm("manage_admin_registries")
- Query param: dry_run=true|false (default: true)
- Body: {file: upload}
- Returns: Relatório com stats, pendências
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

import logging
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
from apps.core.permissions import HasPerm
from apps.core.serializers.openapi_critical_contract import (
    ImportFileUploadRequestSerializer,
    ImportOperationErrorResponseSerializer,
    ImportOperationResponseSerializer,
)
from apps.core.services.controle_acoes_import import import_acoes_controle
from apps.core.services.dat_cadastros_import import import_dat_cadastros
from apps.core.upload_validators import validate_upload

logger = logging.getLogger(__name__)


class ControleImportAcoesView(APIView):
    """
    Importa Ações de Controle de CSV/XLSX.

    Requer permissão: HasPerm("import_spreadsheet") (grupo DAT, ou superuser).

    Query params:
        dry_run: "true" (default) para preview, "false" para aplicar

    Body (multipart/form-data):
        file: Arquivo CSV/XLSX (upload obrigatório)

    Returns:
        {
            "stats": {"created": 10, "updated": 5, "unchanged": 2, "skipped": {...}},
            "pendencias": {
                "municipios": [...],
                "projetos": [...],
                "coordenadores": [...]
            },
            "dry_run": true,
            "file": "/tmp/xyz.csv"
        }
    """

    # PR-A1 DAT-Imports (2026-04-29): centralização DAT-only via
    # `HasPerm("import_spreadsheet")`. Controle perde acesso (D-1).
    permission_classes = [IsAuthenticated, HasPerm("import_spreadsheet")]

    @extend_schema(
        summary="Importar ações de controle",
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

        # Issue #132/#747: Validar tamanho, MIME type e magic bytes
        error_response = validate_upload(upload)
        if error_response:
            return error_response

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
            report = import_acoes_controle(file_path=temp_file.name, dry_run=dry_run)

            return Response(report, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("Erro ao processar arquivo de acoes controle: %s", e)
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


class DATImportCadastrosView(APIView):
    """
    Importa Cadastros DAT de CSV/XLSX.

    Requer permissão: HasPerm("manage_admin_registries") (grupos DAT ou Superintendência)

    Query params:
        dry_run: "true" (default) para preview, "false" para aplicar

    Body (multipart/form-data):
        file: Arquivo CSV/XLSX (upload obrigatório)

    Returns:
        {
            "stats": {"created": 10, "updated": 5, "unchanged": 2, "skipped": {...}},
            "pendencias": {
                "municipios": [...],
                "projetos": [...],
                "responsaveis": [...]
            },
            "dry_run": true,
            "file": "/tmp/xyz.csv"
        }
    """

    permission_classes = [IsAuthenticated, HasPerm("manage_admin_registries")]

    @extend_schema(
        summary="Importar cadastros DAT",
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

        # Issue #132/#747: Validar tamanho, MIME type e magic bytes
        error_response = validate_upload(upload)
        if error_response:
            return error_response

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
            report = import_dat_cadastros(file_path=temp_file.name, dry_run=dry_run)

            return Response(report, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("Erro ao processar arquivo de cadastros DAT: %s", e)
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

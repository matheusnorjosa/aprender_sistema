"""
Endpoints DRF para importação de Ações de Controle e Cadastros DAT.

POST /api/controle/import-acoes/
- Permission: IsControleOrSuper
- Query param: dry_run=true|false (default: true)
- Body: {file: upload}
- Returns: Relatório com stats, pendências

POST /api/dat/import-cadastros/
- Permission: IsDATOrSuper
- Query param: dry_run=true|false (default: true)
- Body: {file: upload}
- Returns: Relatório com stats, pendências
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

import os
import tempfile
from typing import Any

from django.db.models import QuerySet
from django.utils.datastructures import MultiValueDictKeyError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsControleOrSuper, IsDATOrSuper
from apps.core.services.controle_acoes_import import import_acoes_controle
from apps.core.services.dat_cadastros_import import import_dat_cadastros

# Issue #132: Upload validation (SEC-P0)
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_CONTENT_TYPES = {
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


class ControleImportAcoesView(APIView):
    """
    Importa Ações de Controle de CSV/XLSX.

    Requer permissão: IsControleOrSuper (grupos Controle ou Superintendência)

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

    permission_classes = [IsAuthenticated, IsControleOrSuper]

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # Parse dry_run query param
        dry_run_param = str(request.query_params.get("dry_run", "true")).lower()
        dry_run = dry_run_param in {"1", "true", "t", "yes", "y"}

        # Verificar arquivo
        try:
            upload = request.FILES["file"]
        except (KeyError, MultiValueDictKeyError):
            return Response({"detail": "Campo 'file' é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)

        # Issue #132: Validar tamanho (DoS prevention)
        if upload.size > MAX_UPLOAD_SIZE:
            return Response(
                {"detail": f"Arquivo muito grande. Máximo: {MAX_UPLOAD_SIZE / 1024 / 1024:.0f}MB"},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        # Issue #132: Validar MIME type (malicious file prevention)
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
            report = import_acoes_controle(file_path=temp_file.name, dry_run=dry_run)

            return Response(report, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"detail": f"Erro ao processar arquivo: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
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

    Requer permissão: IsDATOrSuper (grupos DAT ou Superintendência)

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

    permission_classes = [IsAuthenticated, IsDATOrSuper]

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # Parse dry_run query param
        dry_run_param = str(request.query_params.get("dry_run", "true")).lower()
        dry_run = dry_run_param in {"1", "true", "t", "yes", "y"}

        # Verificar arquivo
        try:
            upload = request.FILES["file"]
        except (KeyError, MultiValueDictKeyError):
            return Response({"detail": "Campo 'file' é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)

        # Issue #132: Validar tamanho (DoS prevention)
        if upload.size > MAX_UPLOAD_SIZE:
            return Response(
                {"detail": f"Arquivo muito grande. Máximo: {MAX_UPLOAD_SIZE / 1024 / 1024:.0f}MB"},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        # Issue #132: Validar MIME type (malicious file prevention)
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
            report = import_dat_cadastros(file_path=temp_file.name, dry_run=dry_run)

            return Response(report, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"detail": f"Erro ao processar arquivo: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            # Sempre remover arquivo temporário
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                except Exception:
                    pass

"""
Endpoint DRF para importacao de Eventos (Solicitacao + Participation).

POST /api/solicitacoes/import/
- Permission: IsControleOrSuper
- Query param: dry_run=true|false (default: true)
- Body: {file: upload}
- Returns: Relatorio com stats, pendencias
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false, reportAttributeAccessIssue=false

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

from apps.core.permissions import IsControleOrSuper
from apps.core.services.eventos_import import import_eventos_from_file

# Issue #132: Upload validation (SEC-P0)
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_CONTENT_TYPES = {
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


class ImportEventosView(APIView):
    """
    Importa Eventos de CSV/XLSX.

    Requer permissao: IsControleOrSuper (grupos Controle ou Superintendencia)

    Query params:
        dry_run: "true" (default) para preview, "false" para aplicar

    Body (multipart/form-data):
        file: Arquivo CSV/XLSX (upload obrigatorio)

    Returns:
        {
            "stats": {
                "solicitacoes": {"created": 10, "updated": 5, "unchanged": 2},
                "participations": {"created": 20, "updated": 5},
                "skipped": {"municipio": 0, "projeto": 0, ...}
            },
            "pendencias": {
                "municipios": [...],
                "projetos": [...],
                "tipos_evento": [...],
                "usuarios": [...],
                "dates": [...],
                "outros": [...]
            },
            "dry_run": true,
            "file": "/tmp/xyz.xlsx"
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
            return Response(
                {"detail": "Campo 'file' e obrigatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Issue #132: Validar tamanho (DoS prevention)
        if upload.size > MAX_UPLOAD_SIZE:
            return Response(
                {"detail": f"Arquivo muito grande. Maximo: {MAX_UPLOAD_SIZE / 1024 / 1024:.0f}MB"},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        # Issue #132: Validar MIME type (malicious file prevention)
        if upload.content_type not in ALLOWED_CONTENT_TYPES:
            return Response(
                {"detail": f"Tipo de arquivo nao permitido. Aceitos: CSV, XLS, XLSX. Recebido: {upload.content_type}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
            report = import_eventos_from_file(path=temp_file.name, dry_run=dry_run)

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

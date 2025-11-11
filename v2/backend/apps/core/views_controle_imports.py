"""

from typing import Any

from rest_framework.request import Request
from __future__ import annotations
Endpoints DRF para importação de Compras.

POST /api/controle/import-compras/
- Query param: dry_run=true|false (default: true)
- Body (multipart/form-data): {file: upload}
- Returns: Relatório com stats, pendências e IDs criados
"""

from typing import Any

from rest_framework.request import Request

import tempfile
import os
from django.utils.datastructures import MultiValueDictKeyError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.core.permissions import IsControleOrSuper
from apps.core.services.controle_imports import import_compras_from_file


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

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # Parse dry_run query param
        dry_run_param = str(request.query_params.get("dry_run", "true")).lower()
        dry_run = dry_run_param in {"1", "true", "t", "yes", "y"}

        # Verificar arquivo
        try:
            upload = request.FILES["file"]
        except (KeyError, MultiValueDictKeyError):
            return Response(
                {"detail": "Campo 'file' é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST
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
            return Response(
                {"detail": f"Erro ao processar arquivo: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            # Sempre remover arquivo temporário
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                except Exception:
                    pass

"""
Endpoints DRF para importação de Compras.

POST /api/controle/import-compras/
- Query param: dry_run=true|false (default: true)
- Body: {file: upload} ou {path: "/path/to/file.csv"}
- Returns: Relatório com stats, pendências e IDs criados
"""

import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from apps.core.services.controle_imports import import_compras_from_file


DEFAULT_DIR = "/app/data/csv-import"


class ImportComprasView(APIView):
    """
    Importa Compras de CSV/XLSX.

    Query params:
        dry_run: "true" (default) para preview, "false" para aplicar

    Body (form-data):
        file: Arquivo CSV/XLSX (upload)
        OU
        path: Caminho para arquivo (default: /app/data/csv-import/compras.csv)

    Returns:
        {
            "path": "/tmp/compras.csv",
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
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Parse dry_run query param
        dry_run_param = str(request.query_params.get("dry_run", "true")).lower()
        dry_run = dry_run_param in {"1", "true", "t", "yes", "y"}

        # Obter arquivo: upload ou path
        upload = request.FILES.get("file")
        if upload:
            # Salvar upload em /tmp
            tmp_path = f"/tmp/{upload.name}"
            with open(tmp_path, "wb") as f:
                for chunk in upload.chunks():
                    f.write(chunk)
            path = tmp_path
        else:
            # Usar path fornecido ou default
            path = request.data.get("path") or os.path.join(DEFAULT_DIR, "compras.csv")

        try:
            report = import_compras_from_file(path=path, dry_run=dry_run)
            return Response(report, status=status.HTTP_200_OK)
        except FileNotFoundError as e:
            return Response(
                {"detail": f"Arquivo não encontrado: {path}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

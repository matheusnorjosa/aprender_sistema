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

import tempfile
import os
from django.utils.datastructures import MultiValueDictKeyError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from apps.core.permissions import IsControleOrSuper, IsDATOrSuper
from apps.core.services.controle_acoes_import import import_acoes_controle
from apps.core.services.dat_cadastros_import import import_dat_cadastros


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

    def post(self, request):
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
            report = import_acoes_controle(path=temp_file.name, dry_run=dry_run)

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

    def post(self, request):
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
            report = import_dat_cadastros(path=temp_file.name, dry_run=dry_run)

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

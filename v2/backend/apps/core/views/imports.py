"""
Views assincronas de importacao (ASQ-005 fase 1 — #778).

Estabelece o namespace /api/imports/ para executar imports em background via
Celery. Fase 1: piloto com bloqueios. Fase 2 migra os 9 imports restantes.

Endpoints:
    POST   /api/imports/bloqueios/   — cria ImportJob + despacha task (202 Accepted)
    GET    /api/imports/<id>/        — retorna estado do job (owner ou super)
    GET    /api/imports/             — lista jobs do usuario (filtros: type, status)

Seguranca:
    - Upload: IsAuthenticated + HasPerm("import_spreadsheet") + validate_upload (magic bytes)
    - Leitura: IsAuthenticated + filtro por owner (ou super) no queryset
    - error_traceback NAO e exposto (debug-only, fica em logs)
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false, reportGeneralTypeIssues=false, reportInvalidTypeArguments=false, reportFunctionMemberAccess=false

from __future__ import annotations

import logging
from typing import Any

from django.core.files.base import ContentFile
from django.utils.datastructures import MultiValueDictKeyError
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import OpenApiParameter, extend_schema

from apps.core.api_schemas import COMMON_ERROR_RESPONSES
from apps.core.models import ImportJob
from apps.core.rbac.policies import CanImportGenericSpreadsheet
from apps.core.serializers.import_job import ImportJobSerializer, ImportJobUploadRequestSerializer
from apps.core.serializers.openapi_critical_contract import ImportOperationErrorResponseSerializer
from apps.core.upload_validators import validate_upload

logger = logging.getLogger(__name__)


def _parse_dry_run(raw: str | None, *, default: bool = True) -> bool:
    """Parse dry_run query-param de forma permissiva (true/false/1/0/yes/no)."""
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "t", "yes", "y"}


class ImportJobBloqueiosUploadView(APIView):
    """
    POST /api/imports/bloqueios/ — cria um ImportJob para bloqueios e despacha task.

    Request (multipart/form-data):
        file: Arquivo CSV/XLSX (obrigatorio)

    Query params:
        dry_run: "true" (default) ou "false"

    Response 202 Accepted:
        ImportJobSerializer do job recem criado (status=QUEUED).
    """

    # Issue #1222 (Epic 1): import operacional aceita Controle (run_daily_operations) ou DAT (import_spreadsheet)
    permission_classes = [IsAuthenticated, CanImportGenericSpreadsheet]
    throttle_scope = "import"

    @extend_schema(
        summary="Dispara import assincrono de bloqueios",
        parameters=[
            OpenApiParameter(
                name="dry_run",
                location=OpenApiParameter.QUERY,
                required=False,
                type=bool,
                description="Quando true (default), executa validacao sem persistir dados.",
            ),
        ],
        request=ImportJobUploadRequestSerializer,
        responses={
            202: ImportJobSerializer,
            400: ImportOperationErrorResponseSerializer,
            401: COMMON_ERROR_RESPONSES[401],
            403: COMMON_ERROR_RESPONSES[403],
            413: ImportOperationErrorResponseSerializer,
        },
        tags=["imports-async"],
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        dry_run = _parse_dry_run(request.query_params.get("dry_run"), default=True)

        try:
            upload = request.FILES["file"]
        except (KeyError, MultiValueDictKeyError):
            return Response(
                {"detail": "Campo 'file' e obrigatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validacao de tamanho + MIME + magic bytes (Issue #747)
        error_response = validate_upload(upload)
        if error_response:
            return error_response

        # Persiste o job + arquivo no FileField (MEDIA_ROOT/imports/...) para auditoria
        original_name = upload.name or "upload"
        job = ImportJob.objects.create(
            user=request.user,
            import_type=ImportJob.ImportType.BLOQUEIOS,
            original_filename=original_name,
            dry_run=dry_run,
        )
        # upload.chunks() garante streaming mesmo para TemporaryUploadedFile
        content = b"".join(chunk for chunk in upload.chunks())
        job.file.save(original_name, ContentFile(content), save=True)

        # Importacao tardia evita ciclos de import no carregamento das views
        from apps.core.tasks import task_run_import_job

        async_result = task_run_import_job.delay(job.id)

        # Guarda o celery_task_id cedo (idempotente com o que a task grava ao iniciar)
        if async_result and getattr(async_result, "id", None):
            job.celery_task_id = async_result.id
            job.save(update_fields=["celery_task_id", "updated_at"])

        serializer = ImportJobSerializer(job)
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)


class ImportJobListView(generics.ListAPIView):
    """
    GET /api/imports/ — lista jobs de import do usuario autenticado.

    Query params:
        import_type: filtra por tipo (ex: bloqueios)
        status: filtra por estado (QUEUED, RUNNING, SUCCESS, FAILED)

    Superusers veem todos; demais veem apenas os proprios.
    """

    serializer_class = ImportJobSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Lista jobs de importacao",
        parameters=[
            OpenApiParameter(
                name="import_type",
                location=OpenApiParameter.QUERY,
                required=False,
                type=str,
                description="Filtra por tipo (ex: bloqueios)",
            ),
            OpenApiParameter(
                name="status",
                location=OpenApiParameter.QUERY,
                required=False,
                type=str,
                description="Filtra por status (QUEUED|RUNNING|SUCCESS|FAILED)",
            ),
        ],
        responses={200: ImportJobSerializer(many=True)},
        tags=["imports-async"],
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)

    def get_queryset(self) -> Any:
        user = self.request.user
        qs = ImportJob.objects.select_related("user").all()
        if not getattr(user, "is_superuser", False):
            qs = qs.filter(user=user)

        import_type = self.request.query_params.get("import_type")
        if import_type:
            qs = qs.filter(import_type=import_type)

        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        return qs


class ImportJobDetailView(generics.RetrieveAPIView):
    """
    GET /api/imports/<id>/ — retorna estado de um job.

    Prevencao de IDOR: queryset filtrado por owner; 404 quando nao for dono e nao
    for superuser (prefer 404 a 403 para nao vazar existencia do recurso).
    """

    serializer_class = ImportJobSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = "pk"

    @extend_schema(
        summary="Retorna estado de um job de importacao",
        responses={200: ImportJobSerializer, 404: ImportOperationErrorResponseSerializer},
        tags=["imports-async"],
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)

    def get_queryset(self) -> Any:
        user = self.request.user
        qs = ImportJob.objects.select_related("user").all()
        if not getattr(user, "is_superuser", False):
            qs = qs.filter(user=user)
        return qs

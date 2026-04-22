"""
Serializers para ImportJob (ASQ-005).

Expoe o estado de um job de importacao assincrona para o cliente (polling) sem
vazar campos sensiveis como error_traceback ou file path.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

from rest_framework import serializers

from apps.core.models import ImportJob


class ImportJobUserSerializer(serializers.Serializer):
    """Resumo do usuario que criou o job."""

    id = serializers.IntegerField()
    username = serializers.CharField()
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj: object) -> str:
        get_full = getattr(obj, "get_full_name", None)
        if callable(get_full):
            return str(get_full()).strip()
        return ""


class ImportJobSerializer(serializers.ModelSerializer):
    """
    Representacao externa de um ImportJob (polling/status).

    NAO expoe:
    - error_traceback (debug-only; fica em logs)
    - file (path/URL do arquivo; apenas auditoria interna)
    """

    user = ImportJobUserSerializer(read_only=True)

    class Meta:
        model = ImportJob
        fields = [
            "id",
            "user",
            "import_type",
            "status",
            "dry_run",
            "original_filename",
            "stats",
            "pendencias",
            "error_message",
            "celery_task_id",
            "duration_ms",
            "created_at",
            "updated_at",
            "started_at",
            "finished_at",
        ]
        read_only_fields = fields


class ImportJobUploadRequestSerializer(serializers.Serializer):
    """Request contract para POST /api/imports/<type>/ (multipart)."""

    file = serializers.FileField()

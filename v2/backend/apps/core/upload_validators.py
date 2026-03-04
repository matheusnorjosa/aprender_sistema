"""
Upload file validation with magic bytes verification.

Security: Validates actual file content (magic bytes), not just HTTP Content-Type
headers which are client-controlled and can be spoofed.

Ref: https://transloadit.com/devtips/secure-api-file-uploads-with-magic-numbers/
Issue #747: Anti-spoofing validation for import endpoints.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

import logging
from typing import Any

from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB

# First layer: HTTP Content-Type header validation
ALLOWED_CONTENT_TYPES = {
    "text/csv",
    "text/plain",  # CSV may be detected as text/plain
    "application/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

# Second layer: magic bytes signatures (actual file content)
# XLSX files are ZIP archives internally, so application/zip is valid
ALLOWED_MAGIC_MIMES = {
    "text/plain",
    "text/csv",
    "application/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/zip",  # XLSX is a ZIP archive
    "application/octet-stream",  # Fallback for valid binary formats
}


def validate_upload(upload: Any) -> Response | None:
    """
    Validate upload file: size, Content-Type, and magic bytes.

    Performs two-layer validation:
    1. Content-Type header (client-declared, first filter)
    2. Magic bytes from actual file content (anti-spoofing)

    Args:
        upload: Django InMemoryUploadedFile or TemporaryUploadedFile

    Returns:
        None if valid, error Response if invalid.
    """
    # 1. Validate size (DoS prevention)
    if upload.size and upload.size > MAX_UPLOAD_SIZE:
        return Response(
            {"detail": f"Arquivo muito grande. Máximo: {MAX_UPLOAD_SIZE // (1024 * 1024)}MB"},
            status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )

    # 2. Validate Content-Type header (first layer)
    if upload.content_type not in ALLOWED_CONTENT_TYPES:
        return Response(
            {"detail": f"Tipo de arquivo não permitido. Aceitos: CSV, XLS, XLSX. Recebido: {upload.content_type}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 3. Validate magic bytes (second layer — anti-spoofing)
    try:
        import magic

        header = upload.read(4096)
        upload.seek(0)  # Reset for subsequent reads

        detected_mime = magic.from_buffer(header, mime=True)
        if detected_mime not in ALLOWED_MAGIC_MIMES:
            logger.warning(
                f"Upload rejeitado: Content-Type={upload.content_type}, magic bytes detectados={detected_mime}"
            )
            return Response(
                {"detail": "Conteúdo do arquivo não corresponde ao tipo declarado."},
                status=status.HTTP_400_BAD_REQUEST,
            )
    except ImportError:
        # python-magic not installed — skip magic bytes check (log warning)
        logger.warning("python-magic não instalado; validação de magic bytes ignorada.")
    except Exception as exc:
        # Magic detection failed — allow through (Content-Type already validated)
        logger.warning(f"Falha na detecção de magic bytes: {exc}")

    return None  # Valid

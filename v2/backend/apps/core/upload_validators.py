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
import os
import tempfile
from pathlib import PurePath
from typing import IO, Any

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB

# Allowlist of file extensions accepted by the import endpoints.
# Aligned with ALLOWED_CONTENT_TYPES below (CSV / XLS / XLSX). Any extension
# outside this set is normalized to ".tmp" by ``_safe_upload_suffix`` —
# defense in depth against CodeQL py/path-injection on tempfile creation.
ALLOWED_UPLOAD_EXTENSIONS: frozenset[str] = frozenset({".csv", ".xls", ".xlsx"})

# First layer: HTTP Content-Type header validation
ALLOWED_CONTENT_TYPES = {
    "text/csv",
    "text/plain",  # CSV may be detected as text/plain
    "application/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

# Second layer: magic bytes signatures (actual file content)
# application/octet-stream is NOT in this set — handled separately via _octet_stream_looks_like_excel()
ALLOWED_MAGIC_MIMES = {
    "text/plain",
    "text/csv",
    "application/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/zip",  # XLSX is a ZIP archive internally
}

# OLE2 header: legacy XLS/DOC/etc. binary format (first 8 bytes)
_OLE2_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
# ZIP local file header: XLSX/DOCX/etc. (first 4 bytes)
_ZIP_SIGNATURE = b"PK\x03\x04"


def _octet_stream_looks_like_excel(header: bytes, filename: str) -> bool:
    """
    Check if an application/octet-stream payload is a plausible Excel file.

    Accepts only:
    - OLE2 binary (legacy .xls) — signature 0xD0CF11E0A1B11AE1
    - ZIP archive (.xlsx) — signature PK\\x03\\x04

    Args:
        header: First 4096 bytes of the uploaded file.
        filename: Original filename (used to check extension).

    Returns:
        True if the binary content matches a known Excel format.
    """
    ext = os.path.splitext(filename.lower())[1]
    if ext not in {".xls", ".xlsx"}:
        return False
    return header[:8] == _OLE2_SIGNATURE or header[:4] == _ZIP_SIGNATURE


def _magic_fail_open() -> bool:
    """
    Return whether magic-bytes failures should be fail-open (allow through).

    Defaults to fail-open only outside production so dev/test environments
    without libmagic installed are not blocked.
    Override via UPLOAD_MAGIC_FAIL_OPEN Django setting.
    """
    if hasattr(settings, "UPLOAD_MAGIC_FAIL_OPEN"):
        return bool(settings.UPLOAD_MAGIC_FAIL_OPEN)
    environment = getattr(settings, "ENVIRONMENT", "development")
    return environment != "production"


def validate_upload(upload: Any) -> Response | None:
    """
    Validate upload file: size, Content-Type, and magic bytes.

    Performs two-layer validation:
    1. Content-Type header (client-declared, first filter)
    2. Magic bytes from actual file content (anti-spoofing)

    Fail behavior on magic-detection errors (ImportError / Exception):
    - production (ENVIRONMENT=production or UPLOAD_MAGIC_FAIL_OPEN=False): fail-closed → 400
    - other environments (UPLOAD_MAGIC_FAIL_OPEN=True, default): fail-open → allow through

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

        if detected_mime == "application/octet-stream":
            # Narrowed check: only accept octet-stream if it looks like a real Excel binary
            if not _octet_stream_looks_like_excel(header, upload.name or ""):
                logger.warning(
                    f"Upload rejeitado: octet-stream sem assinatura Excel "
                    f"(Content-Type={upload.content_type}, file={upload.name})"
                )
                return Response(
                    {"detail": "Conteúdo do arquivo não corresponde ao tipo declarado."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        elif detected_mime not in ALLOWED_MAGIC_MIMES:
            logger.warning(
                f"Upload rejeitado: Content-Type={upload.content_type}, magic bytes detectados={detected_mime}"
            )
            return Response(
                {"detail": "Conteúdo do arquivo não corresponde ao tipo declarado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    except ImportError:
        if _magic_fail_open():
            logger.warning("python-magic não instalado; validação de magic bytes ignorada (fail-open).")
        else:
            logger.error("python-magic não instalado; bloqueando upload por política fail-closed.")
            return Response(
                {"detail": "Não foi possível validar a segurança do arquivo."},
                status=status.HTTP_400_BAD_REQUEST,
            )
    except Exception as exc:
        if _magic_fail_open():
            logger.warning(f"Falha na detecção de magic bytes; aceitando por fail-open: {exc}")
        else:
            logger.error(f"Falha na detecção de magic bytes; bloqueando por fail-closed: {exc}")
            return Response(
                {"detail": "Não foi possível validar a segurança do arquivo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    return None  # Valid


def _safe_upload_suffix(uploaded_file: Any) -> str:
    """
    Derive a sanitized suffix from an uploaded file's name.

    Returns the original extension only when it is part of
    ``ALLOWED_UPLOAD_EXTENSIONS``. Defaults to ``.tmp`` for any name that
    contains path separators, null bytes, missing extension, or extension
    outside the allowlist. The original ``uploaded_file.name`` itself is
    NEVER used as part of the final filesystem path.
    """
    original_name = str(getattr(uploaded_file, "name", "") or "")

    if "\x00" in original_name:
        return ".tmp"

    if "/" in original_name or "\\" in original_name:
        return ".tmp"

    suffix = PurePath(original_name).suffix.lower()

    if suffix in ALLOWED_UPLOAD_EXTENSIONS:
        return suffix

    return ".tmp"


def safe_temp_upload_file(uploaded_file: Any) -> "IO[bytes]":
    """
    Create a ``NamedTemporaryFile`` in ``tempfile.gettempdir()`` with a
    suffix derived strictly from the allowlist (see ``_safe_upload_suffix``).

    The user-controlled ``uploaded_file.name`` is never embedded in the
    returned path — only a server-chosen random name plus the sanitized
    suffix. This closes CodeQL ``py/path-injection`` (CWE-022/023/036/073/099)
    on the eleven import endpoints.

    Implementation note: each branch passes a *literal* string to
    ``NamedTemporaryFile`` so CodeQL's taint analysis can prove the
    ``suffix`` argument is never user-controlled (the function would
    otherwise re-flag the centralized sink with 11 sources).

    Caller is responsible for writing chunks, closing the file, and
    ``os.unlink`` in a ``finally`` block as before.
    """
    suffix = _safe_upload_suffix(uploaded_file)
    tmp_dir = tempfile.gettempdir()
    if suffix == ".csv":
        return tempfile.NamedTemporaryFile(mode="wb", suffix=".csv", delete=False, dir=tmp_dir)
    if suffix == ".xls":
        return tempfile.NamedTemporaryFile(mode="wb", suffix=".xls", delete=False, dir=tmp_dir)
    if suffix == ".xlsx":
        return tempfile.NamedTemporaryFile(mode="wb", suffix=".xlsx", delete=False, dir=tmp_dir)
    return tempfile.NamedTemporaryFile(mode="wb", suffix=".tmp", delete=False, dir=tmp_dir)

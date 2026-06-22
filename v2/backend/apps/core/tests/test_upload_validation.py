"""
Testes para validação de upload (Issue #132 - SEC-P0)

Valida que:
- Uploads >10MB são rejeitados com 413
- MIME types inválidos são rejeitados com 400
- CSV/XLS/XLSX válidos são aceitos
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

import io

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core.tests.factories import UsuarioFactory


@pytest.fixture
def dat_user(db):
    """Usuário em grupo DAT (PR-A1 DAT-Imports: detentor de import_spreadsheet
    + manage_admin_registries via seed_functional_permissions)."""
    return UsuarioFactory(username="dat1", password="test123", email="dat@example.com", groups=["DAT"])


@pytest.fixture
def authenticated_dat_client(dat_user):
    """APIClient autenticado como DAT (cobre todos os imports DAT-only)."""
    client = APIClient()
    client.force_authenticate(user=dat_user)
    return client


# ============================================================================
# Testes para ControleImportAcoesView (/api/controle/import-acoes/)
# ============================================================================


def test_controle_upload_file_too_large(authenticated_dat_client):
    """SEC-P0: Arquivo >10MB deve ser rejeitado com 413"""
    # Criar arquivo de 11MB (10MB + 1 byte)
    large_file_size = 10 * 1024 * 1024 + 1
    large_file = SimpleUploadedFile("acoes.csv", b"x" * large_file_size, content_type="text/csv")

    response = authenticated_dat_client.post("/api/controle/import-acoes/", {"file": large_file}, format="multipart")

    assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    assert "muito grande" in response.data["detail"].lower()
    assert "10MB" in response.data["detail"] or "10" in response.data["detail"]


def test_controle_upload_invalid_mime_type(authenticated_dat_client):
    """SEC-P0: MIME type inválido (.exe, .sh, etc.) deve ser rejeitado com 400"""
    malicious_file = SimpleUploadedFile(
        "malicious.exe", b"MZ\x90\x00", content_type="application/x-msdownload"  # PE header (Windows executable)
    )

    response = authenticated_dat_client.post(
        "/api/controle/import-acoes/", {"file": malicious_file}, format="multipart"
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "tipo de arquivo não permitido" in response.data["detail"].lower()


def test_controle_upload_valid_csv(authenticated_dat_client):
    """Upload de CSV válido deve ser aceito"""
    csv_content = "cod_projeto,nome_projeto,cod_municipio\n1,Projeto A,001\n"
    valid_csv = SimpleUploadedFile("acoes.csv", csv_content.encode("utf-8"), content_type="text/csv")

    response = authenticated_dat_client.post(
        "/api/controle/import-acoes/?dry_run=true", {"file": valid_csv}, format="multipart"
    )

    # Deve aceitar (200) ou retornar erro de parsing (500), não de validação (413/400)
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]

    # Se retornou 400, verificar que NÃO é erro de validação de upload
    if response.status_code == status.HTTP_400_BAD_REQUEST:
        assert "muito grande" not in response.data.get("detail", "").lower()
        assert "tipo de arquivo" not in response.data.get("detail", "").lower()


def test_controle_upload_valid_xlsx(authenticated_dat_client):
    """Upload de XLSX válido deve ser aceito"""
    # Criar arquivo XLSX mínimo (ZIP com structure correto)
    # Simplificado: apenas testar MIME type
    xlsx_file = SimpleUploadedFile(
        "acoes.xlsx",
        b"PK\x03\x04",  # ZIP header (XLSX é um ZIP)
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    response = authenticated_dat_client.post(
        "/api/controle/import-acoes/?dry_run=true", {"file": xlsx_file}, format="multipart"
    )

    # Deve aceitar (200) ou retornar erro de parsing (500), não de validação (413/400)
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]


# ============================================================================
# Testes para ImportComprasView (/api/controle/import-compras/)
# ============================================================================


def test_controle_import_compras_upload_file_too_large(authenticated_dat_client):
    """Issue #569: Arquivo >10MB deve ser rejeitado com 413 no import-compras."""
    large_file_size = 10 * 1024 * 1024 + 1
    large_file = SimpleUploadedFile("compras.csv", b"x" * large_file_size, content_type="text/csv")

    response = authenticated_dat_client.post(
        "/api/controle/import-compras/?dry_run=true", {"file": large_file}, format="multipart"
    )

    assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    assert "muito grande" in response.data["detail"].lower()


def test_controle_import_compras_upload_invalid_mime_type(authenticated_dat_client):
    """Issue #569: MIME inválido deve ser rejeitado com 400 no import-compras."""
    malicious_file = SimpleUploadedFile(
        "malicious.exe", b"MZ\x90\x00", content_type="application/x-msdownload"  # PE header (Windows executable)
    )

    response = authenticated_dat_client.post(
        "/api/controle/import-compras/?dry_run=true", {"file": malicious_file}, format="multipart"
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "tipo de arquivo não permitido" in response.data["detail"].lower()


# ============================================================================
# Testes para DATImportCadastrosView (/api/dat/import-cadastros/)
# ============================================================================


def test_dat_upload_file_too_large(authenticated_dat_client):
    """SEC-P0: Arquivo >10MB deve ser rejeitado com 413"""
    large_file_size = 10 * 1024 * 1024 + 1
    large_file = SimpleUploadedFile("cadastros.csv", b"x" * large_file_size, content_type="text/csv")

    response = authenticated_dat_client.post("/api/dat/import-cadastros/", {"file": large_file}, format="multipart")

    assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    assert "muito grande" in response.data["detail"].lower()


def test_dat_upload_invalid_mime_type(authenticated_dat_client):
    """SEC-P0: MIME type inválido deve ser rejeitado com 400"""
    malicious_file = SimpleUploadedFile("malicious.sh", b"#!/bin/bash\nrm -rf /", content_type="application/x-sh")

    response = authenticated_dat_client.post("/api/dat/import-cadastros/", {"file": malicious_file}, format="multipart")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "tipo de arquivo não permitido" in response.data["detail"].lower()


def test_dat_upload_valid_csv(authenticated_dat_client):
    """Upload de CSV válido deve ser aceito"""
    csv_content = "cod_cadastro,nome,cpf\n1,João Silva,12345678901\n"
    valid_csv = SimpleUploadedFile("cadastros.csv", csv_content.encode("utf-8"), content_type="text/csv")

    response = authenticated_dat_client.post(
        "/api/dat/import-cadastros/?dry_run=true", {"file": valid_csv}, format="multipart"
    )

    # Deve aceitar (200) ou retornar erro de parsing (500), não de validação (413/400)
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]


# ============================================================================
# Testes de Edge Cases
# ============================================================================


def test_controle_upload_exactly_10mb(authenticated_dat_client):
    """Arquivo de exatamente 10MB deve ser aceito"""
    exact_10mb = 10 * 1024 * 1024
    file_10mb = SimpleUploadedFile("acoes_10mb.csv", b"x" * exact_10mb, content_type="text/csv")

    response = authenticated_dat_client.post(
        "/api/controle/import-acoes/?dry_run=true", {"file": file_10mb}, format="multipart"
    )

    # Não deve retornar 413 (file too large)
    assert response.status_code != status.HTTP_413_REQUEST_ENTITY_TOO_LARGE


def test_controle_upload_xls_legacy_format(authenticated_dat_client):
    """Upload de XLS (formato legado) deve ser aceito"""
    xls_file = SimpleUploadedFile(
        "acoes.xls", b"\xd0\xcf\x11\xe0", content_type="application/vnd.ms-excel"  # OLE2 header (XLS legacy)
    )

    response = authenticated_dat_client.post(
        "/api/controle/import-acoes/?dry_run=true", {"file": xls_file}, format="multipart"
    )

    # Deve aceitar (200) ou retornar erro de parsing (500), não de validação (400)
    assert (
        response.status_code != status.HTTP_400_BAD_REQUEST
        or "tipo de arquivo" not in response.data.get("detail", "").lower()
    )


# ============================================================================
# Testes de Magic Bytes (Issue #747 — Anti-Spoofing)
# ============================================================================


def test_validate_upload_rejects_exe_with_csv_content_type():
    """Issue #747: Arquivo EXE com Content-Type spoofado é rejeitado via magic bytes."""
    import sys
    from types import ModuleType
    from unittest.mock import MagicMock, patch

    from django.core.files.uploadedfile import SimpleUploadedFile

    from apps.core.upload_validators import validate_upload

    # Mock magic module to simulate detection of PE executable
    mock_magic_module = ModuleType("magic")
    mock_magic_module.from_buffer = MagicMock(return_value="application/x-dosexec")

    exe_content = b"MZ" + b"\x00" * 100  # PE executable magic bytes
    fake_csv = SimpleUploadedFile("data.csv", exe_content, content_type="text/csv")

    with patch.dict(sys.modules, {"magic": mock_magic_module}):
        result = validate_upload(fake_csv)

    # Deve retornar Response de erro (não None)
    assert result is not None
    assert result.status_code == status.HTTP_400_BAD_REQUEST
    assert "não corresponde" in result.data["detail"].lower()


def test_validate_upload_accepts_real_csv():
    """Issue #747: CSV real com conteúdo válido é aceito."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    from apps.core.upload_validators import validate_upload

    csv_content = b"nome,uf\nFortaleza,CE\n"
    file = SimpleUploadedFile("data.csv", csv_content, content_type="text/csv")

    result = validate_upload(file)
    assert result is None  # None = válido


def test_validate_upload_rejects_invalid_mime():
    """Issue #747: Content-Type não permitido é rejeitado na primeira camada."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    from apps.core.upload_validators import validate_upload

    file = SimpleUploadedFile("script.sh", b"#!/bin/bash\nrm -rf /", content_type="application/x-sh")

    result = validate_upload(file)
    assert result is not None
    assert result.status_code == status.HTTP_400_BAD_REQUEST
    assert "não permitido" in result.data["detail"].lower()


def test_validate_upload_rejects_oversized_file():
    """Issue #747: Arquivo >10MB é rejeitado com 413."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    from apps.core.upload_validators import validate_upload

    large = SimpleUploadedFile("big.csv", b"x" * (10 * 1024 * 1024 + 1), content_type="text/csv")

    result = validate_upload(large)
    assert result is not None
    assert result.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE


# ============================================================================
# Testes de octet-stream e fail-closed/fail-open
# ============================================================================


def test_validate_upload_rejects_octet_stream_non_excel():
    """octet-stream sem assinatura Excel é rejeitado mesmo com extensão .csv."""
    import sys
    from types import ModuleType
    from unittest.mock import MagicMock, patch

    from django.core.files.uploadedfile import SimpleUploadedFile

    from apps.core.upload_validators import validate_upload

    mock_magic_module = ModuleType("magic")
    mock_magic_module.from_buffer = MagicMock(return_value="application/octet-stream")

    # Payload arbitrário (não é OLE2 nem ZIP)
    fake_file = SimpleUploadedFile("data.csv", b"\x00\x01\x02\x03" * 100, content_type="text/csv")

    with patch.dict(sys.modules, {"magic": mock_magic_module}):
        result = validate_upload(fake_file)

    assert result is not None
    assert result.status_code == status.HTTP_400_BAD_REQUEST
    assert "não corresponde" in result.data["detail"].lower()


def test_validate_upload_accepts_octet_stream_xls_ole2():
    """octet-stream com assinatura OLE2 e extensão .xls é aceito."""
    import sys
    from types import ModuleType
    from unittest.mock import MagicMock, patch

    from django.core.files.uploadedfile import SimpleUploadedFile

    from apps.core.upload_validators import validate_upload

    mock_magic_module = ModuleType("magic")
    mock_magic_module.from_buffer = MagicMock(return_value="application/octet-stream")

    ole2_header = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 100
    xls_file = SimpleUploadedFile("planilha.xls", ole2_header, content_type="text/csv")

    with patch.dict(sys.modules, {"magic": mock_magic_module}):
        result = validate_upload(xls_file)

    assert result is None  # Válido


def test_validate_upload_accepts_octet_stream_xlsx_zip():
    """octet-stream com assinatura ZIP e extensão .xlsx é aceito."""
    import sys
    from types import ModuleType
    from unittest.mock import MagicMock, patch

    from django.core.files.uploadedfile import SimpleUploadedFile

    from apps.core.upload_validators import validate_upload

    mock_magic_module = ModuleType("magic")
    mock_magic_module.from_buffer = MagicMock(return_value="application/octet-stream")

    zip_header = b"PK\x03\x04" + b"\x00" * 100
    xlsx_file = SimpleUploadedFile("planilha.xlsx", zip_header, content_type="text/csv")

    with patch.dict(sys.modules, {"magic": mock_magic_module}):
        result = validate_upload(xlsx_file)

    assert result is None  # Válido


def test_validate_upload_fail_closed_on_import_error():
    """Em modo fail-closed (production), ImportError de magic retorna 400."""
    import sys

    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.test import override_settings

    from apps.core.upload_validators import validate_upload

    csv_content = b"nome,uf\nFortaleza,CE\n"
    file = SimpleUploadedFile("data.csv", csv_content, content_type="text/csv")

    # sys.modules["magic"] = None faz Python lançar ImportError na próxima tentativa de import
    saved = sys.modules.get("magic", _SENTINEL := object())
    sys.modules["magic"] = None  # type: ignore[assignment]
    try:
        with override_settings(UPLOAD_MAGIC_FAIL_OPEN=False):
            result = validate_upload(file)
    finally:
        if saved is _SENTINEL:
            del sys.modules["magic"]
        else:
            sys.modules["magic"] = saved  # type: ignore[assignment]

    assert result is not None
    assert result.status_code == status.HTTP_400_BAD_REQUEST
    assert "não foi possível validar" in result.data["detail"].lower()


def test_validate_upload_fail_open_on_import_error():
    """Em modo fail-open (dev), ImportError de magic permite o upload."""
    import sys

    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.test import override_settings

    from apps.core.upload_validators import validate_upload

    csv_content = b"nome,uf\nFortaleza,CE\n"
    file = SimpleUploadedFile("data.csv", csv_content, content_type="text/csv")

    saved = sys.modules.get("magic", _SENTINEL := object())
    sys.modules["magic"] = None  # type: ignore[assignment]
    try:
        with override_settings(UPLOAD_MAGIC_FAIL_OPEN=True):
            result = validate_upload(file)
    finally:
        if saved is _SENTINEL:
            del sys.modules["magic"]
        else:
            sys.modules["magic"] = saved  # type: ignore[assignment]

    assert result is None  # Fail-open: aceita mesmo sem magic

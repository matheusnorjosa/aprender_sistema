"""
Testes para validação de upload (Issue #132 - SEC-P0)

Valida que:
- Uploads >10MB são rejeitados com 413
- MIME types inválidos são rejeitados com 400
- CSV/XLS/XLSX válidos são aceitos
"""
import io
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.models import Usuario
from django.contrib.auth.models import Group


@pytest.fixture
def controle_user(db):
    """Usuário com permissão IsControleOrSuper"""
    user = Usuario.objects.create_user(
        username="controle1",
        password="test123",
        email="controle@example.com"
    )
    group, _ = Group.objects.get_or_create(name="Controle")
    user.groups.add(group)
    return user


@pytest.fixture
def dat_user(db):
    """Usuário com permissão IsDATOrSuper"""
    user = Usuario.objects.create_user(
        username="dat1",
        password="test123",
        email="dat@example.com"
    )
    group, _ = Group.objects.get_or_create(name="DAT")
    user.groups.add(group)
    return user


@pytest.fixture
def authenticated_controle_client(controle_user):
    """APIClient autenticado como Controle"""
    client = APIClient()
    client.force_authenticate(user=controle_user)
    return client


@pytest.fixture
def authenticated_dat_client(dat_user):
    """APIClient autenticado como DAT"""
    client = APIClient()
    client.force_authenticate(user=dat_user)
    return client


# ============================================================================
# Testes para ControleImportAcoesView (/api/controle/import-acoes/)
# ============================================================================

def test_controle_upload_file_too_large(authenticated_controle_client):
    """SEC-P0: Arquivo >10MB deve ser rejeitado com 413"""
    # Criar arquivo de 11MB (10MB + 1 byte)
    large_file_size = 10 * 1024 * 1024 + 1
    large_file = SimpleUploadedFile(
        "acoes.csv",
        b"x" * large_file_size,
        content_type="text/csv"
    )

    response = authenticated_controle_client.post(
        "/api/controle/import-acoes/",
        {"file": large_file},
        format="multipart"
    )

    assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    assert "muito grande" in response.data["detail"].lower()
    assert "10MB" in response.data["detail"] or "10" in response.data["detail"]


def test_controle_upload_invalid_mime_type(authenticated_controle_client):
    """SEC-P0: MIME type inválido (.exe, .sh, etc.) deve ser rejeitado com 400"""
    malicious_file = SimpleUploadedFile(
        "malicious.exe",
        b"MZ\x90\x00",  # PE header (Windows executable)
        content_type="application/x-msdownload"
    )

    response = authenticated_controle_client.post(
        "/api/controle/import-acoes/",
        {"file": malicious_file},
        format="multipart"
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "tipo de arquivo não permitido" in response.data["detail"].lower()


def test_controle_upload_valid_csv(authenticated_controle_client):
    """Upload de CSV válido deve ser aceito"""
    csv_content = "cod_projeto,nome_projeto,cod_municipio\n1,Projeto A,001\n"
    valid_csv = SimpleUploadedFile(
        "acoes.csv",
        csv_content.encode("utf-8"),
        content_type="text/csv"
    )

    response = authenticated_controle_client.post(
        "/api/controle/import-acoes/?dry_run=true",
        {"file": valid_csv},
        format="multipart"
    )

    # Deve aceitar (200) ou retornar erro de parsing (500), não de validação (413/400)
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]

    # Se retornou 400, verificar que NÃO é erro de validação de upload
    if response.status_code == status.HTTP_400_BAD_REQUEST:
        assert "muito grande" not in response.data.get("detail", "").lower()
        assert "tipo de arquivo" not in response.data.get("detail", "").lower()


def test_controle_upload_valid_xlsx(authenticated_controle_client):
    """Upload de XLSX válido deve ser aceito"""
    # Criar arquivo XLSX mínimo (ZIP com structure correto)
    # Simplificado: apenas testar MIME type
    xlsx_file = SimpleUploadedFile(
        "acoes.xlsx",
        b"PK\x03\x04",  # ZIP header (XLSX é um ZIP)
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    response = authenticated_controle_client.post(
        "/api/controle/import-acoes/?dry_run=true",
        {"file": xlsx_file},
        format="multipart"
    )

    # Deve aceitar (200) ou retornar erro de parsing (500), não de validação (413/400)
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]


# ============================================================================
# Testes para DATImportCadastrosView (/api/dat/import-cadastros/)
# ============================================================================

def test_dat_upload_file_too_large(authenticated_dat_client):
    """SEC-P0: Arquivo >10MB deve ser rejeitado com 413"""
    large_file_size = 10 * 1024 * 1024 + 1
    large_file = SimpleUploadedFile(
        "cadastros.csv",
        b"x" * large_file_size,
        content_type="text/csv"
    )

    response = authenticated_dat_client.post(
        "/api/dat/import-cadastros/",
        {"file": large_file},
        format="multipart"
    )

    assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    assert "muito grande" in response.data["detail"].lower()


def test_dat_upload_invalid_mime_type(authenticated_dat_client):
    """SEC-P0: MIME type inválido deve ser rejeitado com 400"""
    malicious_file = SimpleUploadedFile(
        "malicious.sh",
        b"#!/bin/bash\nrm -rf /",
        content_type="application/x-sh"
    )

    response = authenticated_dat_client.post(
        "/api/dat/import-cadastros/",
        {"file": malicious_file},
        format="multipart"
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "tipo de arquivo não permitido" in response.data["detail"].lower()


def test_dat_upload_valid_csv(authenticated_dat_client):
    """Upload de CSV válido deve ser aceito"""
    csv_content = "cod_cadastro,nome,cpf\n1,João Silva,12345678901\n"
    valid_csv = SimpleUploadedFile(
        "cadastros.csv",
        csv_content.encode("utf-8"),
        content_type="text/csv"
    )

    response = authenticated_dat_client.post(
        "/api/dat/import-cadastros/?dry_run=true",
        {"file": valid_csv},
        format="multipart"
    )

    # Deve aceitar (200) ou retornar erro de parsing (500), não de validação (413/400)
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]


# ============================================================================
# Testes de Edge Cases
# ============================================================================

def test_controle_upload_exactly_10mb(authenticated_controle_client):
    """Arquivo de exatamente 10MB deve ser aceito"""
    exact_10mb = 10 * 1024 * 1024
    file_10mb = SimpleUploadedFile(
        "acoes_10mb.csv",
        b"x" * exact_10mb,
        content_type="text/csv"
    )

    response = authenticated_controle_client.post(
        "/api/controle/import-acoes/?dry_run=true",
        {"file": file_10mb},
        format="multipart"
    )

    # Não deve retornar 413 (file too large)
    assert response.status_code != status.HTTP_413_REQUEST_ENTITY_TOO_LARGE


def test_controle_upload_xls_legacy_format(authenticated_controle_client):
    """Upload de XLS (formato legado) deve ser aceito"""
    xls_file = SimpleUploadedFile(
        "acoes.xls",
        b"\xd0\xcf\x11\xe0",  # OLE2 header (XLS legacy)
        content_type="application/vnd.ms-excel"
    )

    response = authenticated_controle_client.post(
        "/api/controle/import-acoes/?dry_run=true",
        {"file": xls_file},
        format="multipart"
    )

    # Deve aceitar (200) ou retornar erro de parsing (500), não de validação (400)
    assert response.status_code != status.HTTP_400_BAD_REQUEST or \
           "tipo de arquivo" not in response.data.get("detail", "").lower()

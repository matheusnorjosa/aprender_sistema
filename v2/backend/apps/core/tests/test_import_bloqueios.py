"""
Testes para importacao de Bloqueios (AvailabilityBlock).

Cobertura:
- Service: import_bloqueios_from_file()
- View: ImportBloqueiosView
- RBAC: Permissoes HasPerm("import_spreadsheet")
- Idempotencia: Nao duplica registros
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportUnknownParameterType=false, reportMissingParameterType=false

import io
import tempfile
from pathlib import Path

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core.models import AvailabilityBlock
from apps.core.services.bloqueios_import import import_bloqueios_from_file
from apps.core.tests.factories import UsuarioFactory

# URL direta (evita problemas de cache de rotas no container)
IMPORT_BLOQUEIOS_URL = "/api/disponibilidade/import-bloqueios/"


@pytest.fixture
def dat_import_user(db):
    """Usuario do grupo DAT (PR-A1 DAT-Imports: detentor de import_spreadsheet)."""
    return UsuarioFactory(
        username="dat_import_user",
        email="dat_imports@test.com",
        password="testpass123",
        cpf="11111111111",
        first_name="DAT",
        last_name="Imports",
        groups=["DAT"],
    )


@pytest.fixture
def formador_user(db):
    """Usuario do grupo Formador (sem permissao de import)."""
    return UsuarioFactory(
        username="formador_user",
        email="formador@test.com",
        password="testpass123",
        cpf="22222222222",
        first_name="Formador",
        last_name="User",
        groups=["Formador"],
    )


@pytest.fixture
def target_user(db):
    """Usuario que sera bloqueado."""
    return UsuarioFactory(
        username="target_user",
        email="target@test.com",
        password="testpass123",
        cpf="33333333333",
        first_name="Target",
        last_name="User",
    )


@pytest.fixture
def api_client():
    """Cliente API."""
    return APIClient()


@pytest.fixture
def sample_csv(target_user):
    """Cria arquivo CSV de teste com cleanup automatico."""
    content = f"""usuario,inicio,fim,tipo,motivo
{target_user.first_name} {target_user.last_name},2026-03-01 08:00,2026-03-01 12:00,P,Consulta medica
{target_user.first_name} {target_user.last_name},2026-03-05 00:00,2026-03-05 23:59,T,Ferias
"""
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    temp.write(content)
    temp.close()
    yield temp.name
    # Cleanup
    Path(temp.name).unlink(missing_ok=True)


@pytest.fixture
def sample_csv_invalid():
    """CSV com usuario inexistente e cleanup automatico."""
    content = """usuario,inicio,fim,tipo,motivo
Usuario Inexistente,2026-03-01 08:00,2026-03-01 12:00,P,Teste
"""
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    temp.write(content)
    temp.close()
    yield temp.name
    # Cleanup
    Path(temp.name).unlink(missing_ok=True)


# =============================================================================
# TESTES DO SERVICE
# =============================================================================


@pytest.mark.django_db
class TestBloqueiosImportService:
    """Testes do service import_bloqueios_from_file."""

    def test_dry_run_returns_stats(self, sample_csv, target_user):
        """dry_run=True retorna stats sem persistir."""
        result = import_bloqueios_from_file(path=sample_csv, dry_run=True)

        assert result["dry_run"] is True
        assert result["stats"]["created"] == 2
        assert result["stats"]["unchanged"] == 0

        # Nao deve ter criado no banco
        assert AvailabilityBlock.objects.count() == 0

    def test_apply_creates_records(self, sample_csv, target_user):
        """dry_run=False persiste os registros."""
        result = import_bloqueios_from_file(path=sample_csv, dry_run=False)

        assert result["dry_run"] is False
        assert result["stats"]["created"] == 2

        # Deve ter criado no banco
        assert AvailabilityBlock.objects.count() == 2

        # Verificar dados
        blocks = AvailabilityBlock.objects.filter(usuario=target_user).order_by("inicio")
        assert len(blocks) == 2
        assert blocks[0].tipo == "P"
        assert blocks[1].tipo == "T"
        assert blocks[0].status == "aprovado"  # Auto-aprovado

    def test_idempotency_no_duplicates(self, sample_csv, target_user):
        """Rodar 2x nao duplica registros."""
        # Primeira execucao
        result1 = import_bloqueios_from_file(path=sample_csv, dry_run=False)
        assert result1["stats"]["created"] == 2

        # Segunda execucao
        result2 = import_bloqueios_from_file(path=sample_csv, dry_run=False)
        assert result2["stats"]["created"] == 0
        assert result2["stats"]["unchanged"] == 2

        # Total no banco
        assert AvailabilityBlock.objects.count() == 2

    def test_invalid_user_adds_pendencia(self, sample_csv_invalid):
        """Usuario inexistente adiciona pendencia."""
        result = import_bloqueios_from_file(path=sample_csv_invalid, dry_run=True)

        assert result["stats"]["skipped"]["usuario"] == 1
        assert len(result["pendencias"]["usuarios"]) == 1
        assert result["pendencias"]["usuarios"][0]["nome"] == "Usuario Inexistente"

    def test_invalid_dates_adds_pendencia(self, target_user):
        """Datas invalidas adicionam pendencia."""
        content = f"""usuario,inicio,fim,tipo,motivo
{target_user.first_name} {target_user.last_name},invalido,2026-03-01,T,Teste
"""
        temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
        temp.write(content)
        temp.close()

        result = import_bloqueios_from_file(path=temp.name, dry_run=True)

        assert result["stats"]["skipped"]["dates"] == 1
        assert len(result["pendencias"]["dates"]) == 1

        Path(temp.name).unlink()


# =============================================================================
# TESTES DA VIEW
# =============================================================================


@pytest.mark.django_db
class TestImportBloqueiosView:
    """Testes da view ImportBloqueiosView."""

    def test_permission_denied_for_formador(self, api_client, formador_user, sample_csv):
        """Formador nao tem permissao (403)."""
        api_client.force_authenticate(user=formador_user)

        with open(sample_csv, "rb") as f:
            response = api_client.post(
                IMPORT_BLOQUEIOS_URL,
                {"file": f},
                format="multipart",
            )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_dat_import_user_can_import(self, api_client, dat_import_user, sample_csv, target_user):
        """Usuario DAT pode importar (PR-A1 DAT-Imports 2026-04-29)."""
        api_client.force_authenticate(user=dat_import_user)

        with open(sample_csv, "rb") as f:
            response = api_client.post(
                IMPORT_BLOQUEIOS_URL + "?dry_run=true",
                {"file": f},
                format="multipart",
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["dry_run"] is True
        assert response.data["stats"]["created"] == 2

    def test_apply_mode_persists(self, api_client, dat_import_user, sample_csv, target_user):
        """dry_run=false persiste os dados."""
        api_client.force_authenticate(user=dat_import_user)

        with open(sample_csv, "rb") as f:
            response = api_client.post(
                IMPORT_BLOQUEIOS_URL + "?dry_run=false",
                {"file": f},
                format="multipart",
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["dry_run"] is False
        assert AvailabilityBlock.objects.count() == 2

    def test_missing_file_returns_400(self, api_client, dat_import_user):
        """Arquivo ausente retorna 400."""
        api_client.force_authenticate(user=dat_import_user)

        response = api_client.post(
            IMPORT_BLOQUEIOS_URL,
            {},
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "file" in response.data["detail"].lower()

    def test_invalid_mime_type_returns_400(self, api_client, dat_import_user):
        """Tipo de arquivo invalido retorna 400."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        api_client.force_authenticate(user=dat_import_user)

        # Usar MIME type explicitamente inválido (não text/plain, pois CSVs podem ser text/plain)
        fake_file = SimpleUploadedFile("malicious.exe", b"MZ\x90\x00", content_type="application/x-msdownload")

        response = api_client.post(
            IMPORT_BLOQUEIOS_URL,
            {"file": fake_file},
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "tipo" in response.data["detail"].lower() or "permitido" in response.data["detail"].lower()

    def test_unauthenticated_returns_401(self, api_client, sample_csv):
        """Usuario nao autenticado retorna 401."""
        with open(sample_csv, "rb") as f:
            response = api_client.post(
                IMPORT_BLOQUEIOS_URL,
                {"file": f},
                format="multipart",
            )

        # Pode ser 401 ou 403 dependendo da configuracao
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

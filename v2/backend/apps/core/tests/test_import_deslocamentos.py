"""
Testes para importacao de Deslocamentos.

Cobertura:
- Service: import_deslocamentos_from_file()
- View: ImportDeslocamentosView
- RBAC: Permissoes HasPerm("import_spreadsheet")
- Idempotencia: Nao duplica registros
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportUnknownParameterType=false, reportMissingParameterType=false

import io
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core.models import Deslocamento
from apps.core.services.deslocamentos_import import import_deslocamentos_from_file

# URL direta (evita problemas de cache de rotas no container)
IMPORT_DESLOCAMENTOS_URL = "/api/deslocamentos/import/"

User = get_user_model()


@pytest.fixture
def dat_import_user(db):
    """Usuario do grupo DAT (PR-A1 DAT-Imports: detentor de import_spreadsheet)."""
    user = User.objects.create_user(
        username="dat_import_user",
        email="dat_imports@test.com",
        password="testpass123",
        cpf="11111111111",
        first_name="DAT",
        last_name="Imports",
    )
    group, _ = Group.objects.get_or_create(name="DAT")
    user.groups.add(group)
    return user


@pytest.fixture
def formador_user(db):
    """Usuario do grupo Formador (sem permissao de import)."""
    user = User.objects.create_user(
        username="formador_user",
        email="formador@test.com",
        password="testpass123",
        cpf="22222222222",
        first_name="Formador",
        last_name="User",
    )
    group, _ = Group.objects.get_or_create(name="Formador")
    user.groups.add(group)
    return user


@pytest.fixture
def target_user(db):
    """Usuario que tera deslocamentos registrados."""
    return User.objects.create_user(
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
    content = f"""usuario,origem,destino,data_inicio,data_fim,observacao
{target_user.first_name} {target_user.last_name},Fortaleza,Sobral,2026-03-01,2026-03-02,Visita tecnica
{target_user.first_name} {target_user.last_name},Sobral,Fortaleza,2026-03-05,2026-03-05,Retorno
"""
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    temp.write(content)
    temp.close()
    yield temp.name
    # Cleanup
    Path(temp.name).unlink(missing_ok=True)


@pytest.fixture
def sample_csv_with_email(target_user):
    """CSV usando email para identificar usuario."""
    content = f"""email,origem,destino,data_inicio,data_fim,observacao
{target_user.email},Fortaleza,Juazeiro,2026-04-01,2026-04-02,Evento
"""
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    temp.write(content)
    temp.close()
    yield temp.name
    Path(temp.name).unlink(missing_ok=True)


@pytest.fixture
def sample_csv_invalid_user():
    """CSV com usuario inexistente."""
    content = """usuario,origem,destino,data_inicio,data_fim,observacao
Usuario Inexistente,Fortaleza,Sobral,2026-03-01,2026-03-02,Teste
"""
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    temp.write(content)
    temp.close()
    yield temp.name
    Path(temp.name).unlink(missing_ok=True)


@pytest.fixture
def sample_csv_invalid_dates(target_user):
    """CSV com datas invalidas."""
    content = f"""usuario,origem,destino,data_inicio,data_fim,observacao
{target_user.first_name} {target_user.last_name},Fortaleza,Sobral,invalido,2026-03-02,Teste
"""
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    temp.write(content)
    temp.close()
    yield temp.name
    Path(temp.name).unlink(missing_ok=True)


@pytest.fixture
def sample_csv_end_before_start(target_user):
    """CSV com data_fim < data_inicio."""
    content = f"""usuario,origem,destino,data_inicio,data_fim,observacao
{target_user.first_name} {target_user.last_name},Fortaleza,Sobral,2026-03-05,2026-03-01,Teste
"""
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    temp.write(content)
    temp.close()
    yield temp.name
    Path(temp.name).unlink(missing_ok=True)


# =============================================================================
# TESTES DO SERVICE
# =============================================================================


@pytest.mark.django_db
class TestDeslocamentosImportService:
    """Testes do service import_deslocamentos_from_file."""

    def test_dry_run_returns_stats(self, sample_csv, target_user):
        """dry_run=True retorna stats sem persistir."""
        result = import_deslocamentos_from_file(path=sample_csv, dry_run=True)

        assert result["dry_run"] is True
        assert result["stats"]["created"] == 2
        assert result["stats"]["unchanged"] == 0

        # Nao deve ter criado no banco
        assert Deslocamento.objects.count() == 0

    def test_apply_creates_records(self, sample_csv, target_user):
        """dry_run=False persiste os registros."""
        result = import_deslocamentos_from_file(path=sample_csv, dry_run=False)

        assert result["dry_run"] is False
        assert result["stats"]["created"] == 2

        # Deve ter criado no banco
        assert Deslocamento.objects.count() == 2

        # Verificar dados
        deslocamentos = Deslocamento.objects.filter(usuario=target_user).order_by("start_date")
        assert len(deslocamentos) == 2
        assert deslocamentos[0].origem == "Fortaleza"
        assert deslocamentos[0].destino == "Sobral"
        assert deslocamentos[1].origem == "Sobral"
        assert deslocamentos[1].destino == "Fortaleza"

    def test_idempotency_no_duplicates(self, sample_csv, target_user):
        """Rodar 2x nao duplica registros."""
        # Primeira execucao
        result1 = import_deslocamentos_from_file(path=sample_csv, dry_run=False)
        assert result1["stats"]["created"] == 2

        # Segunda execucao
        result2 = import_deslocamentos_from_file(path=sample_csv, dry_run=False)
        assert result2["stats"]["created"] == 0
        assert result2["stats"]["unchanged"] == 2

        # Total no banco
        assert Deslocamento.objects.count() == 2

    def test_resolve_user_by_email(self, sample_csv_with_email, target_user):
        """Resolve usuario por email."""
        result = import_deslocamentos_from_file(path=sample_csv_with_email, dry_run=False)

        assert result["stats"]["created"] == 1
        assert Deslocamento.objects.filter(usuario=target_user).count() == 1

    def test_invalid_user_adds_pendencia(self, sample_csv_invalid_user):
        """Usuario inexistente adiciona pendencia."""
        result = import_deslocamentos_from_file(path=sample_csv_invalid_user, dry_run=True)

        assert result["stats"]["skipped"]["usuario"] == 1
        assert len(result["pendencias"]["usuarios"]) == 1

    def test_invalid_dates_adds_pendencia(self, sample_csv_invalid_dates):
        """Datas invalidas adicionam pendencia."""
        result = import_deslocamentos_from_file(path=sample_csv_invalid_dates, dry_run=True)

        assert result["stats"]["skipped"]["dates"] == 1
        assert len(result["pendencias"]["dates"]) == 1

    def test_end_before_start_adds_pendencia(self, sample_csv_end_before_start):
        """data_fim < data_inicio adiciona pendencia."""
        result = import_deslocamentos_from_file(path=sample_csv_end_before_start, dry_run=True)

        assert result["stats"]["skipped"]["dates"] == 1
        assert len(result["pendencias"]["dates"]) == 1
        assert "data_fim < data_inicio" in result["pendencias"]["dates"][0].get("erro", "")

    def test_missing_origem_destino_adds_pendencia(self, target_user):
        """Origem ou destino ausente adiciona pendencia."""
        content = f"""usuario,origem,destino,data_inicio,data_fim,observacao
{target_user.first_name} {target_user.last_name},,Sobral,2026-03-01,2026-03-02,Teste
"""
        temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
        temp.write(content)
        temp.close()

        result = import_deslocamentos_from_file(path=temp.name, dry_run=True)

        assert result["stats"]["skipped"]["other"] == 1
        assert len(result["pendencias"]["outros"]) == 1

        Path(temp.name).unlink()


# =============================================================================
# TESTES DA VIEW
# =============================================================================


@pytest.mark.django_db
class TestImportDeslocamentosView:
    """Testes da view ImportDeslocamentosView."""

    def test_permission_denied_for_formador(self, api_client, formador_user, sample_csv):
        """Formador nao tem permissao (403)."""
        api_client.force_authenticate(user=formador_user)

        with open(sample_csv, "rb") as f:
            response = api_client.post(
                IMPORT_DESLOCAMENTOS_URL,
                {"file": f},
                format="multipart",
            )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_dat_import_user_can_import(self, api_client, dat_import_user, sample_csv, target_user):
        """Usuario Controle pode importar."""
        api_client.force_authenticate(user=dat_import_user)

        with open(sample_csv, "rb") as f:
            response = api_client.post(
                IMPORT_DESLOCAMENTOS_URL + "?dry_run=true",
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
                IMPORT_DESLOCAMENTOS_URL + "?dry_run=false",
                {"file": f},
                format="multipart",
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["dry_run"] is False
        assert Deslocamento.objects.count() == 2

    def test_missing_file_returns_400(self, api_client, dat_import_user):
        """Arquivo ausente retorna 400."""
        api_client.force_authenticate(user=dat_import_user)

        response = api_client.post(
            IMPORT_DESLOCAMENTOS_URL,
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
            IMPORT_DESLOCAMENTOS_URL,
            {"file": fake_file},
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "tipo" in response.data["detail"].lower() or "permitido" in response.data["detail"].lower()

    def test_unauthenticated_returns_401_or_403(self, api_client, sample_csv):
        """Usuario nao autenticado retorna 401 ou 403."""
        with open(sample_csv, "rb") as f:
            response = api_client.post(
                IMPORT_DESLOCAMENTOS_URL,
                {"file": f},
                format="multipart",
            )

        # Pode ser 401 ou 403 dependendo da configuracao
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

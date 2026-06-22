"""
Testes para importacao de EquipeGerencia (vinculos).

Cobertura:
- Service: import_equipe_gerencia_from_file()
- View: ImportEquipeGerenciaView
- RBAC: Permissoes HasPerm("manage_admin_registries")
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportUnknownParameterType=false, reportMissingParameterType=false

import tempfile
from pathlib import Path

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core.models import EquipeGerencia, Gerencia
from apps.core.services.equipe_gerencia_import import import_equipe_gerencia_from_file
from apps.core.tests.factories import UsuarioFactory

IMPORT_EQUIPE_URL = "/api/equipe-gerencia/import/"


@pytest.fixture
def dat_user(db):
    return UsuarioFactory(
        username="dat_user",
        email="dat@test.com",
        password="testpass123",
        cpf="11111111111",
        first_name="DAT",
        last_name="User",
        groups=["DAT"],
    )


@pytest.fixture
def formador_user(db):
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
def superuser(db):
    return UsuarioFactory(
        superuser=True,
        username="admin",
        email="admin@test.com",
        password="testpass123",
        cpf="99999999999",
        first_name="Admin",
        last_name="User",
    )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def usuario_formador(db):
    return UsuarioFactory(
        username="formador1",
        email="formador1@test.com",
        password="testpass123",
        cpf="33333333333",
        first_name="Formador",
        last_name="Teste",
    )


@pytest.fixture
def usuario_coordenador(db):
    return UsuarioFactory(
        username="coord1",
        email="coord1@test.com",
        password="testpass123",
        cpf="44444444444",
        first_name="Coord",
        last_name="Teste",
    )


@pytest.fixture
def sample_csv(usuario_formador):
    content = f"""setor,papel,usuario_email
Vidas,FORMADOR,{usuario_formador.email}
"""
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    temp.write(content)
    temp.close()
    yield temp.name
    Path(temp.name).unlink(missing_ok=True)


@pytest.fixture
def sample_csv_apoio(usuario_formador, usuario_coordenador):
    content = f"""setor,papel,usuario_email,coordenador_supervisor
Vidas,APOIO,{usuario_formador.email},{usuario_coordenador.email}
"""
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    temp.write(content)
    temp.close()
    yield temp.name
    Path(temp.name).unlink(missing_ok=True)


@pytest.fixture
def sample_csv_apoio_missing_supervisor(usuario_formador):
    content = f"""setor,papel,usuario_email
Vidas,APOIO,{usuario_formador.email}
"""
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    temp.write(content)
    temp.close()
    yield temp.name
    Path(temp.name).unlink(missing_ok=True)


# =============================================================================
# SERVICE
# =============================================================================


@pytest.mark.django_db
class TestEquipeGerenciaImportService:
    def test_dry_run_does_not_persist(self, sample_csv):
        initial_count = EquipeGerencia.objects.count()
        result = import_equipe_gerencia_from_file(path=sample_csv, dry_run=True)

        assert result["dry_run"] is True
        assert result["stats"]["created"] == 1
        assert EquipeGerencia.objects.count() == initial_count

    def test_apply_creates_equipes(self, sample_csv):
        result = import_equipe_gerencia_from_file(path=sample_csv, dry_run=False)
        assert result["stats"]["created"] == 1
        assert EquipeGerencia.objects.count() == 1
        assert Gerencia.objects.filter(nome_setor__iexact="Vidas").exists()

    def test_apoio_requires_supervisor(self, sample_csv_apoio_missing_supervisor):
        result = import_equipe_gerencia_from_file(path=sample_csv_apoio_missing_supervisor, dry_run=False)
        assert result["stats"]["skipped"]["apoio_supervisor_missing"] == 1
        assert EquipeGerencia.objects.count() == 0

    def test_apoio_with_supervisor(self, sample_csv_apoio):
        result = import_equipe_gerencia_from_file(path=sample_csv_apoio, dry_run=False)
        assert result["stats"]["created"] == 1
        equipe = EquipeGerencia.objects.first()
        assert equipe is not None
        assert equipe.papel == "APOIO"
        assert equipe.coordenador_supervisor is not None


# =============================================================================
# VIEW
# =============================================================================


@pytest.mark.django_db
class TestEquipeGerenciaImportView:
    def test_permission_denied_for_non_dat(self, api_client, formador_user, sample_csv):
        api_client.force_authenticate(user=formador_user)
        with open(sample_csv, "rb") as f:
            response = api_client.post(IMPORT_EQUIPE_URL, {"file": f}, format="multipart")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_permission_allowed_for_dat(self, api_client, dat_user, sample_csv):
        api_client.force_authenticate(user=dat_user)
        with open(sample_csv, "rb") as f:
            response = api_client.post(IMPORT_EQUIPE_URL, {"file": f}, format="multipart")
        assert response.status_code == status.HTTP_200_OK

    def test_permission_allowed_for_superuser(self, api_client, superuser, sample_csv):
        api_client.force_authenticate(user=superuser)
        with open(sample_csv, "rb") as f:
            response = api_client.post(IMPORT_EQUIPE_URL, {"file": f}, format="multipart")
        assert response.status_code == status.HTTP_200_OK

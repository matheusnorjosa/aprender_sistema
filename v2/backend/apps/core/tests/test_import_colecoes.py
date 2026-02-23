"""
Testes para importacao de Colecoes.

Cobertura:
- Service: import_colecoes_from_file()
- View: ImportColecoesView
- RBAC: Permissoes IsDATOrSuper
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportUnknownParameterType=false, reportMissingParameterType=false

import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core.models import Colecao, Projeto
from apps.core.services.colecoes_import import import_colecoes_from_file

IMPORT_COLECOES_URL = "/api/colecoes/import/"

User = get_user_model()


@pytest.fixture
def dat_user(db):
    user = User.objects.create_user(
        username="dat_user",
        email="dat@test.com",
        password="testpass123",
        cpf="11111111111",
        first_name="DAT",
        last_name="User",
    )
    group, _ = Group.objects.get_or_create(name="DAT")
    user.groups.add(group)
    return user


@pytest.fixture
def formador_user(db):
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
def superuser(db):
    return User.objects.create_superuser(
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
def projeto_teste(db):
    return Projeto.objects.create(
        nome="Projeto Teste",
        codigo="PROJ-TEST",
        fluxo="NAO_SUPER",
        ativo=True,
    )


@pytest.fixture
def sample_csv(projeto_teste):
    content = f"""nome,projeto,descricao,ativo
Colecao 1,{projeto_teste.nome},Descricao 1,sim
Colecao 2,{projeto_teste.codigo},Descricao 2,sim
"""
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    temp.write(content)
    temp.close()
    yield temp.name
    Path(temp.name).unlink(missing_ok=True)


@pytest.fixture
def sample_csv_projeto_not_found():
    content = """nome,projeto
Colecao Orfa,Projeto Inexistente
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
class TestColecoesImportService:
    def test_dry_run_does_not_persist(self, sample_csv, projeto_teste):
        initial_count = Colecao.objects.count()
        result = import_colecoes_from_file(path=sample_csv, dry_run=True)

        assert result["dry_run"] is True
        assert result["stats"]["created"] == 2
        assert Colecao.objects.count() == initial_count

    def test_apply_creates_records(self, sample_csv, projeto_teste):
        result = import_colecoes_from_file(path=sample_csv, dry_run=False)

        assert result["dry_run"] is False
        assert result["stats"]["created"] == 2
        assert Colecao.objects.count() == 2

    def test_projeto_not_found(self, sample_csv_projeto_not_found):
        result = import_colecoes_from_file(path=sample_csv_projeto_not_found, dry_run=False)
        assert result["stats"]["skipped"]["projeto_not_found"] == 1
        assert Colecao.objects.count() == 0


# =============================================================================
# VIEW
# =============================================================================


@pytest.mark.django_db
class TestColecoesImportView:
    def test_permission_denied_for_non_dat(self, api_client, formador_user, sample_csv):
        api_client.force_authenticate(user=formador_user)
        with open(sample_csv, "rb") as f:
            response = api_client.post(IMPORT_COLECOES_URL, {"file": f}, format="multipart")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_permission_allowed_for_dat(self, api_client, dat_user, sample_csv, projeto_teste):
        api_client.force_authenticate(user=dat_user)
        with open(sample_csv, "rb") as f:
            response = api_client.post(IMPORT_COLECOES_URL, {"file": f}, format="multipart")
        assert response.status_code == status.HTTP_200_OK

    def test_permission_allowed_for_superuser(self, api_client, superuser, sample_csv, projeto_teste):
        api_client.force_authenticate(user=superuser)
        with open(sample_csv, "rb") as f:
            response = api_client.post(IMPORT_COLECOES_URL, {"file": f}, format="multipart")
        assert response.status_code == status.HTTP_200_OK

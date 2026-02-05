"""
Testes para importacao de Usuarios.

Cobertura:
- Service: import_usuarios_from_file()
- View: ImportUsuariosView
- RBAC: Permissoes IsDATOrSuper
- Idempotencia: Nao duplica registros (CPF e chave)
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

from apps.core.services.usuarios_import import import_usuarios_from_file

# URL direta (evita problemas de cache de rotas no container)
IMPORT_USUARIOS_URL = "/api/usuarios/import/"

User = get_user_model()


@pytest.fixture
def dat_user(db):
    """Usuario do grupo DAT (com permissao de import)."""
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
def superuser(db):
    """Superusuario (sempre tem permissao)."""
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
    """Cliente API."""
    return APIClient()


@pytest.fixture
def sample_csv(db):
    """Cria arquivo CSV de teste com usuarios validos."""
    content = """cpf,nome,email,telefone,cargo
12345678901,Maria Silva Santos,maria.silva@test.com,85999990001,Formadora
98765432109,Joao Pedro Souza,joao.pedro@test.com,85999990002,Coordenador
"""
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    temp.write(content)
    temp.close()
    yield temp.name
    Path(temp.name).unlink(missing_ok=True)


@pytest.fixture
def sample_csv_with_groups(db):
    """CSV com grupos especificados."""
    # Criar grupos primeiro
    Group.objects.get_or_create(name="Formador")
    Group.objects.get_or_create(name="Coordenador")

    content = """cpf,nome,email,grupos
55555555555,Ana Costa Lima,ana.costa@test.com,Formador
66666666666,Carlos Mendes,carlos.mendes@test.com,"Formador,Coordenador"
"""
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    temp.write(content)
    temp.close()
    yield temp.name
    Path(temp.name).unlink(missing_ok=True)


@pytest.fixture
def sample_csv_invalid_cpf(db):
    """CSV com CPF invalido."""
    content = """cpf,nome,email
123,Nome Invalido,invalido@test.com
abc,Outro Invalido,outro@test.com
,Sem CPF,semcpf@test.com
"""
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    temp.write(content)
    temp.close()
    yield temp.name
    Path(temp.name).unlink(missing_ok=True)


@pytest.fixture
def sample_csv_missing_nome(db):
    """CSV com nome ausente."""
    content = """cpf,nome,email
77777777777,,semnome@test.com
88888888888,  ,espacos@test.com
"""
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    temp.write(content)
    temp.close()
    yield temp.name
    Path(temp.name).unlink(missing_ok=True)


@pytest.fixture
def sample_csv_flexible_headers(db):
    """CSV com headers alternativos."""
    content = """CPF,NOME_COMPLETO,E-MAIL,TEL,FUNCAO,ATIVO
11122233344,Pedro Alves Costa,pedro.alves@test.com,85988887777,Apoio,sim
"""
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    temp.write(content)
    temp.close()
    yield temp.name
    Path(temp.name).unlink(missing_ok=True)


@pytest.fixture
def sample_csv_update_existing(db):
    """CSV para testar atualizacao de usuario existente."""
    # Criar usuario existente
    User.objects.create_user(
        username="existing_user",
        email="old@test.com",
        password="testpass123",
        cpf="33333333333",
        first_name="Old",
        last_name="Name",
        telefone="85999990000",
        cargo="Cargo Antigo",
    )

    content = """cpf,nome,email,telefone,cargo
33333333333,New First New Last,new@test.com,85999991111,Cargo Novo
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
class TestUsuariosImportService:
    """Testes do service import_usuarios_from_file."""

    def test_dry_run_returns_stats(self, sample_csv):
        """dry_run=True retorna stats sem persistir."""
        initial_count = User.objects.count()

        result = import_usuarios_from_file(path=sample_csv, dry_run=True)

        assert result["dry_run"] is True
        assert result["stats"]["created"] == 2
        assert result["stats"]["unchanged"] == 0

        # Nao deve ter criado no banco
        assert User.objects.count() == initial_count

    def test_apply_creates_records(self, sample_csv):
        """dry_run=False persiste os registros."""
        initial_count = User.objects.count()

        result = import_usuarios_from_file(path=sample_csv, dry_run=False)

        assert result["dry_run"] is False
        assert result["stats"]["created"] == 2

        # Deve ter criado no banco
        assert User.objects.count() == initial_count + 2

        # Verificar dados
        maria = User.objects.get(cpf="12345678901")
        assert maria.first_name == "Maria"
        assert maria.last_name == "Silva Santos"
        assert maria.email == "maria.silva@test.com"
        assert maria.telefone == "85999990001"
        assert maria.cargo == "Formadora"

        joao = User.objects.get(cpf="98765432109")
        assert joao.first_name == "Joao"
        assert joao.last_name == "Pedro Souza"

    def test_idempotency_no_duplicates(self, sample_csv):
        """Rodar 2x nao duplica registros (CPF e chave)."""
        # Primeira execucao
        result1 = import_usuarios_from_file(path=sample_csv, dry_run=False)
        assert result1["stats"]["created"] == 2
        count_after_first = User.objects.count()

        # Segunda execucao
        result2 = import_usuarios_from_file(path=sample_csv, dry_run=False)
        assert result2["stats"]["created"] == 0
        assert result2["stats"]["unchanged"] == 2

        # Total no banco nao mudou
        assert User.objects.count() == count_after_first

    def test_updates_existing_user(self, sample_csv_update_existing):
        """Atualiza usuario existente com novos dados."""
        user_before = User.objects.get(cpf="33333333333")
        assert user_before.email == "old@test.com"

        result = import_usuarios_from_file(path=sample_csv_update_existing, dry_run=False)

        assert result["stats"]["updated"] == 1
        assert result["stats"]["created"] == 0

        user_after = User.objects.get(cpf="33333333333")
        assert user_after.email == "new@test.com"
        assert user_after.telefone == "85999991111"
        assert user_after.cargo == "Cargo Novo"
        assert user_after.first_name == "New"
        assert user_after.last_name == "First New Last"

    def test_invalid_cpf_adds_pendencia(self, sample_csv_invalid_cpf):
        """CPF invalido adiciona pendencia."""
        result = import_usuarios_from_file(path=sample_csv_invalid_cpf, dry_run=True)

        assert result["stats"]["skipped"]["cpf_invalid"] == 3
        assert len(result["pendencias"]["cpf_invalid"]) == 3

    def test_missing_nome_adds_pendencia(self, sample_csv_missing_nome):
        """Nome ausente adiciona pendencia."""
        result = import_usuarios_from_file(path=sample_csv_missing_nome, dry_run=True)

        assert result["stats"]["skipped"]["nome_missing"] == 2
        assert len(result["pendencias"]["nome_missing"]) == 2

    def test_header_flexibility(self, sample_csv_flexible_headers):
        """Headers alternativos sao reconhecidos."""
        result = import_usuarios_from_file(path=sample_csv_flexible_headers, dry_run=False)

        assert result["stats"]["created"] == 1

        user = User.objects.get(cpf="11122233344")
        assert user.first_name == "Pedro"
        assert user.last_name == "Alves Costa"
        assert user.email == "pedro.alves@test.com"
        assert user.telefone == "85988887777"
        assert user.cargo == "Apoio"
        assert user.is_active is True

    def test_assigns_groups(self, sample_csv_with_groups):
        """Grupos sao atribuidos corretamente."""
        result = import_usuarios_from_file(path=sample_csv_with_groups, dry_run=False)

        assert result["stats"]["created"] == 2

        ana = User.objects.get(cpf="55555555555")
        assert ana.groups.filter(name="Formador").exists()
        assert ana.groups.count() == 1

        carlos = User.objects.get(cpf="66666666666")
        assert carlos.groups.filter(name="Formador").exists()
        assert carlos.groups.filter(name="Coordenador").exists()
        assert carlos.groups.count() == 2

    def test_cpf_formatting_is_cleaned(self, db):
        """CPF com formatacao (pontos/tracos) e limpo."""
        content = """cpf,nome,email
123.456.789-01,Usuario Formatado,formatado@test.com
"""
        temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
        temp.write(content)
        temp.close()

        result = import_usuarios_from_file(path=temp.name, dry_run=False)

        assert result["stats"]["created"] == 1
        user = User.objects.get(cpf="12345678901")
        assert user.first_name == "Usuario"

        Path(temp.name).unlink()


# =============================================================================
# TESTES DA VIEW
# =============================================================================


@pytest.mark.django_db
class TestImportUsuariosView:
    """Testes da view ImportUsuariosView."""

    def test_permission_denied_for_formador(self, api_client, formador_user, sample_csv):
        """Formador nao tem permissao (403)."""
        api_client.force_authenticate(user=formador_user)

        with open(sample_csv, "rb") as f:
            response = api_client.post(
                IMPORT_USUARIOS_URL,
                {"file": f},
                format="multipart",
            )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_dat_user_can_import(self, api_client, dat_user, sample_csv):
        """Usuario DAT pode importar."""
        api_client.force_authenticate(user=dat_user)

        with open(sample_csv, "rb") as f:
            response = api_client.post(
                IMPORT_USUARIOS_URL + "?dry_run=true",
                {"file": f},
                format="multipart",
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["dry_run"] is True
        assert response.data["stats"]["created"] == 2

    def test_superuser_can_import(self, api_client, superuser, sample_csv):
        """Superusuario pode importar."""
        api_client.force_authenticate(user=superuser)

        with open(sample_csv, "rb") as f:
            response = api_client.post(
                IMPORT_USUARIOS_URL + "?dry_run=true",
                {"file": f},
                format="multipart",
            )

        assert response.status_code == status.HTTP_200_OK

    def test_apply_mode_persists(self, api_client, dat_user, sample_csv):
        """dry_run=false persiste os dados."""
        initial_count = User.objects.count()
        api_client.force_authenticate(user=dat_user)

        with open(sample_csv, "rb") as f:
            response = api_client.post(
                IMPORT_USUARIOS_URL + "?dry_run=false",
                {"file": f},
                format="multipart",
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["dry_run"] is False
        assert User.objects.count() == initial_count + 2

    def test_missing_file_returns_400(self, api_client, dat_user):
        """Arquivo ausente retorna 400."""
        api_client.force_authenticate(user=dat_user)

        response = api_client.post(
            IMPORT_USUARIOS_URL,
            {},
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "file" in str(response.data).lower()

    def test_invalid_mime_type_returns_400(self, api_client, dat_user):
        """Tipo de arquivo invalido retorna 400."""
        api_client.force_authenticate(user=dat_user)

        fake_file = io.BytesIO(b"fake content")
        fake_file.name = "test.txt"

        response = api_client.post(
            IMPORT_USUARIOS_URL,
            {"file": fake_file},
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated_returns_401_or_403(self, api_client, sample_csv):
        """Usuario nao autenticado retorna 401 ou 403."""
        with open(sample_csv, "rb") as f:
            response = api_client.post(
                IMPORT_USUARIOS_URL,
                {"file": f},
                format="multipart",
            )

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

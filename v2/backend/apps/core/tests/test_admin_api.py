"""
Testes para API Admin (PR 7/N)

Testa:
- RBAC: DAT, Controle, Superintendência, outros
- CRUD: Município, Projeto, Compra, Usuario
- Filtros DRF: search, ordering, filterset_fields
- Edge cases: validações, permissões, dados inválidos
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations
import pytest
from datetime import date
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.models import Compra, Municipio, Projeto, Usuario


@pytest.fixture
def api_client():
    """Cliente API DRF"""
    return APIClient()


@pytest.fixture
def usuario_dat(db):
    """Usuário do grupo DAT"""
    user = Usuario.objects.create_user(
        username="dat_user",
        email="dat@example.com",
        password="senha123",
        cpf="12345678901",
    )
    group_dat, _ = Group.objects.get_or_create(name="DAT")
    user.groups.add(group_dat)
    return user


@pytest.fixture
def usuario_controle(db):
    """Usuário do grupo Controle"""
    user = Usuario.objects.create_user(
        username="controle_user",
        email="controle@example.com",
        password="senha123",
        cpf="12345678902",
    )
    group_controle, _ = Group.objects.get_or_create(name="Controle")
    user.groups.add(group_controle)
    return user


@pytest.fixture
def usuario_superintendencia(db):
    """Usuário do grupo Superintendência"""
    user = Usuario.objects.create_user(
        username="super_user",
        email="super@example.com",
        password="senha123",
        cpf="12345678903",
    )
    group_super, _ = Group.objects.get_or_create(name="Superintendência")
    user.groups.add(group_super)
    return user


@pytest.fixture
def usuario_formador(db):
    """Usuário do grupo Formador (sem acesso admin)"""
    user = Usuario.objects.create_user(
        username="formador_user",
        email="formador@example.com",
        password="senha123",
        cpf="12345678904",
    )
    group_formador, _ = Group.objects.get_or_create(name="Formador")
    user.groups.add(group_formador)
    return user


@pytest.fixture
def municipio_sample(db):
    """Município de exemplo"""
    return Municipio.objects.create(nome="Fortaleza", uf="CE", ibge_code="2304400")


@pytest.fixture
def projeto_sample(db):
    """Projeto de exemplo"""
    return Projeto.objects.create(nome="Alfabetização", codigo="ALF-01")


@pytest.fixture
def compra_sample(db, municipio_sample, projeto_sample):
    """Compra de exemplo"""
    return Compra.objects.create(
        codigo="COMP-001",
        projeto=projeto_sample,
        municipio=municipio_sample,
        quantidade=10,
        data=date(2025, 1, 15),
        uso="Formação inicial",
        external_hash="abc123xyz",
    )


# ==========================
# Testes de Município
# ==========================


@pytest.mark.django_db
class TestMunicipioAPI:
    """Testes do endpoint /api/municipios/"""

    def test_dat_can_list_municipios(self, api_client, usuario_dat, municipio_sample):
        """DAT pode listar municípios"""
        api_client.force_authenticate(user=usuario_dat)
        response = api_client.get("/api/municipios/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

    def test_dat_can_create_municipio(self, api_client, usuario_dat):
        """DAT pode criar município"""
        api_client.force_authenticate(user=usuario_dat)
        payload = {"nome": "Caucaia", "uf": "CE", "ibge_code": "2303709", "ativo": True}
        response = api_client.post("/api/municipios/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert Municipio.objects.filter(nome="Caucaia").exists()

    def test_dat_can_update_municipio(
        self, api_client, usuario_dat, municipio_sample
    ):
        """DAT pode atualizar município"""
        api_client.force_authenticate(user=usuario_dat)
        payload = {"ativo": False}
        response = api_client.patch(
            f"/api/municipios/{municipio_sample.id}/", payload, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        municipio_sample.refresh_from_db()
        assert municipio_sample.ativo is False

    def test_dat_can_delete_municipio(self, api_client, usuario_dat, municipio_sample):
        """DAT pode deletar município"""
        api_client.force_authenticate(user=usuario_dat)
        response = api_client.delete(f"/api/municipios/{municipio_sample.id}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Municipio.objects.filter(id=municipio_sample.id).exists()

    def test_controle_cannot_create_municipio(self, api_client, usuario_controle):
        """Controle NÃO pode criar município (apenas DAT)"""
        api_client.force_authenticate(user=usuario_controle)
        payload = {"nome": "Caucaia", "uf": "CE", "ativo": True}
        response = api_client.post("/api/municipios/", payload, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_formador_cannot_access_municipios(
        self, api_client, usuario_formador, municipio_sample
    ):
        """Formador NÃO pode acessar endpoint de municípios"""
        api_client.force_authenticate(user=usuario_formador)
        response = api_client.get("/api/municipios/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_filter_municipios_by_uf(
        self, api_client, usuario_dat, municipio_sample, db
    ):
        """Filtrar municípios por UF"""
        Municipio.objects.create(nome="Juazeiro do Norte", uf="CE")
        Municipio.objects.create(nome="Recife", uf="PE")
        api_client.force_authenticate(user=usuario_dat)
        response = api_client.get("/api/municipios/?uf=CE")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 2

    def test_search_municipios_by_nome(
        self, api_client, usuario_dat, municipio_sample
    ):
        """Buscar municípios por nome"""
        api_client.force_authenticate(user=usuario_dat)
        response = api_client.get("/api/municipios/?search=Fortal")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1


# ==========================
# Testes de Projeto
# ==========================


@pytest.mark.django_db
class TestProjetoAPI:
    """Testes do endpoint /api/projetos/"""

    def test_dat_can_list_projetos(self, api_client, usuario_dat, projeto_sample):
        """DAT pode listar projetos"""
        api_client.force_authenticate(user=usuario_dat)
        response = api_client.get("/api/projetos/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

    def test_dat_can_create_projeto(self, api_client, usuario_dat):
        """DAT pode criar projeto"""
        api_client.force_authenticate(user=usuario_dat)
        payload = {
            "nome": "Matemática Básica",
            "codigo": "MAT-01",
            "descricao": "Projeto de matemática",
            "ativo": True,
        }
        response = api_client.post("/api/projetos/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert Projeto.objects.filter(nome="Matemática Básica").exists()

    def test_controle_cannot_create_projeto(self, api_client, usuario_controle):
        """Controle NÃO pode criar projeto"""
        api_client.force_authenticate(user=usuario_controle)
        payload = {"nome": "Projeto Teste", "ativo": True}
        response = api_client.post("/api/projetos/", payload, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_filter_projetos_by_ativo(self, api_client, usuario_dat, projeto_sample):
        """Filtrar projetos por ativo"""
        Projeto.objects.create(nome="Projeto Inativo", ativo=False)
        api_client.force_authenticate(user=usuario_dat)
        response = api_client.get("/api/projetos/?ativo=true")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

    def test_search_projetos_by_nome(self, api_client, usuario_dat, projeto_sample):
        """Buscar projetos por nome"""
        api_client.force_authenticate(user=usuario_dat)
        response = api_client.get("/api/projetos/?search=Alfabetiza")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1


# ==========================
# Testes de Compra
# ==========================


@pytest.mark.django_db
class TestCompraAPI:
    """Testes do endpoint /api/compras/"""

    def test_dat_can_list_compras(self, api_client, usuario_dat, compra_sample):
        """DAT pode listar compras"""
        api_client.force_authenticate(user=usuario_dat)
        response = api_client.get("/api/compras/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

    def test_controle_can_list_compras(
        self, api_client, usuario_controle, compra_sample
    ):
        """Controle pode listar compras (read-only)"""
        api_client.force_authenticate(user=usuario_controle)
        response = api_client.get("/api/compras/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

    def test_dat_can_create_compra(
        self, api_client, usuario_dat, municipio_sample, projeto_sample
    ):
        """DAT pode criar compra"""
        api_client.force_authenticate(user=usuario_dat)
        payload = {
            "codigo": "COMP-002",
            "projeto": projeto_sample.id,
            "municipio": municipio_sample.id,
            "quantidade": 20,
            "data": "2025-02-01",
            "uso": "Formação continuada",
            "external_hash": "xyz789abc",
        }
        response = api_client.post("/api/compras/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert Compra.objects.filter(codigo="COMP-002").exists()

    def test_controle_cannot_create_compra(
        self, api_client, usuario_controle, municipio_sample, projeto_sample
    ):
        """Controle NÃO pode criar compra (apenas importar)"""
        api_client.force_authenticate(user=usuario_controle)
        payload = {
            "codigo": "COMP-003",
            "projeto": projeto_sample.id,
            "municipio": municipio_sample.id,
            "quantidade": 5,
            "data": "2025-02-01",
            "external_hash": "hash123",
        }
        response = api_client.post("/api/compras/", payload, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_formador_cannot_access_compras(
        self, api_client, usuario_formador, compra_sample
    ):
        """Formador NÃO pode acessar compras"""
        api_client.force_authenticate(user=usuario_formador)
        response = api_client.get("/api/compras/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_filter_compras_by_projeto(
        self, api_client, usuario_dat, compra_sample, municipio_sample, db
    ):
        """Filtrar compras por projeto"""
        projeto2 = Projeto.objects.create(nome="Ciências")
        Compra.objects.create(
            codigo="COMP-004",
            projeto=projeto2,
            municipio=municipio_sample,
            quantidade=15,
            data=date(2025, 3, 1),
            external_hash="hash456",
        )
        api_client.force_authenticate(user=usuario_dat)
        response = api_client.get(f"/api/compras/?projeto={compra_sample.projeto.id}")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

    def test_search_compras_by_codigo(self, api_client, usuario_dat, compra_sample):
        """Buscar compras por código"""
        api_client.force_authenticate(user=usuario_dat)
        response = api_client.get("/api/compras/?search=COMP-001")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

    def test_compra_quantidade_validation(
        self, api_client, usuario_dat, municipio_sample, projeto_sample
    ):
        """Validação: quantidade não pode ser negativa"""
        api_client.force_authenticate(user=usuario_dat)
        payload = {
            "codigo": "COMP-005",
            "projeto": projeto_sample.id,
            "municipio": municipio_sample.id,
            "quantidade": -5,
            "data": "2025-02-01",
            "external_hash": "hash789",
        }
        response = api_client.post("/api/compras/", payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "quantidade" in str(response.data).lower()


# ==========================
# Testes de Usuario Admin
# ==========================


@pytest.mark.django_db
class TestUsuarioAdminAPI:
    """Testes do endpoint /api/usuarios-admin/"""

    def test_dat_can_list_usuarios(self, api_client, usuario_dat):
        """DAT pode listar usuários"""
        api_client.force_authenticate(user=usuario_dat)
        response = api_client.get("/api/usuarios-admin/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) > 0

    def test_dat_can_create_usuario(self, api_client, usuario_dat):
        """DAT pode criar usuário"""
        api_client.force_authenticate(user=usuario_dat)
        payload = {
            "username": "novo_usuario",
            "email": "novo@example.com",
            "password": "SecurePass123!",
            "cpf": "98765432100",
            "first_name": "Novo",
            "last_name": "Usuário",
            "is_active": True,
        }
        response = api_client.post("/api/usuarios-admin/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert Usuario.objects.filter(username="novo_usuario").exists()

    def test_usuario_password_is_hashed(self, api_client, usuario_dat):
        """Senha deve ser hasheada ao criar usuário"""
        api_client.force_authenticate(user=usuario_dat)
        payload = {
            "username": "test_hash",
            "email": "hash@example.com",
            "password": "SecurePass456!",
            "cpf": "11111111111",
        }
        response = api_client.post("/api/usuarios-admin/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED

        user = Usuario.objects.get(username="test_hash")
        assert user.password != "SecurePass456!"  # senha não em plaintext
        assert user.password.startswith("pbkdf2_")  # formato Django hash

    def test_controle_cannot_create_usuario(self, api_client, usuario_controle):
        """Controle NÃO pode criar usuário"""
        api_client.force_authenticate(user=usuario_controle)
        payload = {
            "username": "usuario_teste",
            "email": "teste@example.com",
            "password": "senha123",
            "cpf": "22222222222",
        }
        response = api_client.post("/api/usuarios-admin/", payload, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_search_usuarios_by_username(self, api_client, usuario_dat):
        """Buscar usuários por username"""
        api_client.force_authenticate(user=usuario_dat)
        response = api_client.get("/api/usuarios-admin/?search=dat_user")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

    def test_create_usuario_invalid_cpf(self, api_client, usuario_dat):
        """Validar CPF inválido (não 11 dígitos numéricos)"""
        api_client.force_authenticate(user=usuario_dat)

        # Helper to extract errors from standardized response format
        def get_errors(response):
            """Get field errors from standardized error response."""
            return response.data.get("errors", response.data)

        # Test 1: CPF com letras
        payload = {
            "username": "test_cpf_invalid1",
            "email": "test1@example.com",
            "password": "SecurePass123!",
            "cpf": "123abc78901",
        }
        response = api_client.post("/api/usuarios-admin/", payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        errors = get_errors(response)
        assert "cpf" in errors
        assert "11 dígitos numéricos" in str(errors["cpf"])

        # Test 2: CPF com menos de 11 dígitos
        payload["username"] = "test_cpf_invalid2"
        payload["email"] = "test2@example.com"
        payload["cpf"] = "123456789"
        response = api_client.post("/api/usuarios-admin/", payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        errors = get_errors(response)
        assert "cpf" in errors

        # Test 3: CPF com mais de 11 dígitos
        payload["username"] = "test_cpf_invalid3"
        payload["email"] = "test3@example.com"
        payload["cpf"] = "123456789012"
        response = api_client.post("/api/usuarios-admin/", payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        errors = get_errors(response)
        assert "cpf" in errors


# ==========================
# Testes de AuditLog
# ==========================


@pytest.mark.django_db
class TestAuditLogAPI:
    """Testes do endpoint /api/audit-logs/"""

    def test_controle_can_list_logs(self, api_client, usuario_controle, db):
        """Controle pode listar logs de auditoria"""
        from apps.core.models import AuditLog

        AuditLog.objects.create(
            usuario=usuario_controle,
            action="CREATE",
            model_name="Municipio",
            details={"nome": "Test"},
        )
        api_client.force_authenticate(user=usuario_controle)
        response = api_client.get("/api/audit-logs/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) > 0

    def test_dat_can_list_logs(self, api_client, usuario_dat):
        """DAT pode listar logs de auditoria"""
        api_client.force_authenticate(user=usuario_dat)
        response = api_client.get("/api/audit-logs/")
        assert response.status_code == status.HTTP_200_OK

    def test_formador_cannot_access_logs(self, api_client, usuario_formador):
        """Formador NÃO pode acessar logs"""
        api_client.force_authenticate(user=usuario_formador)
        response = api_client.get("/api/audit-logs/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_logs_are_readonly(self, api_client, usuario_dat):
        """Logs são somente leitura (POST não permitido)"""
        api_client.force_authenticate(user=usuario_dat)
        payload = {
            "usuario": usuario_dat.id,
            "action": "CREATE",
            "model_name": "Test",
        }
        response = api_client.post("/api/audit-logs/", payload, format="json")
        # ReadOnlyModelViewSet não aceita POST
        assert response.status_code in [
            status.HTTP_405_METHOD_NOT_ALLOWED,
            status.HTTP_403_FORBIDDEN,
        ]

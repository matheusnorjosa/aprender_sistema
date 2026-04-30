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

from datetime import date

from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core.models import (
    Compra,
    GroupClassificacao,
    Municipio,
    MunicipioReferencia,
    PermissaoFuncional,
    Projeto,
    Usuario,
)


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

    def test_dat_can_update_municipio(self, api_client, usuario_dat, municipio_sample):
        """DAT pode atualizar município"""
        api_client.force_authenticate(user=usuario_dat)
        payload = {"ativo": False}
        response = api_client.patch(f"/api/municipios/{municipio_sample.id}/", payload, format="json")
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

    def test_formador_cannot_access_municipios(self, api_client, usuario_formador, municipio_sample):
        """Formador NÃO pode acessar endpoint de municípios"""
        api_client.force_authenticate(user=usuario_formador)
        response = api_client.get("/api/municipios/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_filter_municipios_by_uf(self, api_client, usuario_dat, municipio_sample, db):
        """Filtrar municípios por UF"""
        Municipio.objects.create(nome="Juazeiro do Norte", uf="CE")
        Municipio.objects.create(nome="Recife", uf="PE")
        api_client.force_authenticate(user=usuario_dat)
        response = api_client.get("/api/municipios/?uf=CE")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 2

    def test_search_municipios_by_nome(self, api_client, usuario_dat, municipio_sample):
        """Buscar municípios por nome"""
        api_client.force_authenticate(user=usuario_dat)
        response = api_client.get("/api/municipios/?search=Fortal")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

    def test_autocomplete_municipios_prefers_reference_with_ibge(self, api_client, usuario_dat):
        """Autocomplete retorna referência interna com IBGE quando disponível."""
        MunicipioReferencia.objects.create(
            nome="Fortaleza",
            uf="CE",
            codigo_externo="2304400",
            fonte="sistemasaprender",
            ativo=True,
        )
        Municipio.objects.create(nome="Fortaleza", uf="CE", ibge_code="2304400")

        api_client.force_authenticate(user=usuario_dat)
        response = api_client.get("/api/municipios/autocomplete/?q=Fort&uf=CE")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1
        fortaleza = next(item for item in response.data["results"] if item["nome"] == "Fortaleza")
        assert fortaleza["uf"] == "CE"
        assert fortaleza["ibge_code"] == "2304400"
        assert fortaleza["source"] == "referencia"
        assert fortaleza["confidence"] == "high"

    def test_autocomplete_municipios_fallbacks_to_existing_cadastro(self, api_client, usuario_dat):
        """Sem referência confiável, endpoint usa fallback de municípios já cadastrados."""
        Municipio.objects.create(nome="Maranguape", uf="CE", ibge_code="2307705")

        api_client.force_authenticate(user=usuario_dat)
        response = api_client.get("/api/municipios/autocomplete/?q=Maran&uf=CE")

        assert response.status_code == status.HTTP_200_OK
        maranguape = next(item for item in response.data["results"] if item["nome"] == "Maranguape")
        assert maranguape["uf"] == "CE"
        assert maranguape["ibge_code"] == "2307705"
        assert maranguape["source"] == "cadastro"
        assert maranguape["confidence"] == "high"

    def test_autocomplete_municipios_no_confident_ibge_returns_low_confidence(self, api_client, usuario_dat):
        """Quando não há IBGE confiável, retorna item com confidence low e ibge_code nulo."""
        MunicipioReferencia.objects.create(
            nome="Nova Esperança",
            uf="CE",
            codigo_externo="EXT-001",
            fonte="sistemasaprender",
            ativo=True,
        )

        api_client.force_authenticate(user=usuario_dat)
        response = api_client.get("/api/municipios/autocomplete/?q=Nova&uf=CE")

        assert response.status_code == status.HTTP_200_OK
        item = next(item for item in response.data["results"] if item["nome"] == "Nova Esperança")
        assert item["ibge_code"] is None
        assert item["confidence"] == "low"

    def test_non_dat_cannot_use_municipios_autocomplete(self, api_client, usuario_formador):
        """Usuário sem DAT não pode usar autocomplete de municípios do Admin DAT."""
        api_client.force_authenticate(user=usuario_formador)
        response = api_client.get("/api/municipios/autocomplete/?q=Fort&uf=CE")
        assert response.status_code == status.HTTP_403_FORBIDDEN


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
        """DAT pode criar projeto.

        PR 7 hardening RBAC (2026-04-30): `fluxo` agora é obrigatório
        explicitamente no payload da API.
        """
        api_client.force_authenticate(user=usuario_dat)
        payload = {
            "nome": "Matemática Básica",
            "codigo": "MAT-01",
            "descricao": "Projeto de matemática",
            "fluxo": "NAO_SUPER",
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

    def test_controle_can_list_compras(self, api_client, usuario_controle, compra_sample):
        """Controle pode listar compras (read-only)"""
        api_client.force_authenticate(user=usuario_controle)
        response = api_client.get("/api/compras/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

    def test_dat_can_create_compra(self, api_client, usuario_dat, municipio_sample, projeto_sample):
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

    def test_controle_can_create_compra(self, api_client, usuario_controle, municipio_sample, projeto_sample):
        """Issue #1222 (Epic 1): Controle agora pode criar compras
        (`manage_purchases_and_materials` foi atribuído a DAT + Controle)."""
        api_client.force_authenticate(user=usuario_controle)
        payload = {
            "codigo": "COMP-003",
            "projeto": projeto_sample.id,
            "municipio": municipio_sample.id,
            "quantidade": 5,
            "data": "2025-02-01",
            "uso": "Formação continuada",
            "external_hash": "hash_controle_create_001",
        }
        response = api_client.post("/api/compras/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_formador_cannot_access_compras(self, api_client, usuario_formador, compra_sample):
        """Formador NÃO pode acessar compras"""
        api_client.force_authenticate(user=usuario_formador)
        response = api_client.get("/api/compras/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_filter_compras_by_projeto(self, api_client, usuario_dat, compra_sample, municipio_sample, db):
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

    def test_compra_quantidade_validation(self, api_client, usuario_dat, municipio_sample, projeto_sample):
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
            "telefone": "85999990000",
            "cargo": "Coordenador Operacional",
            "is_active": True,
        }
        response = api_client.post("/api/usuarios-admin/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        created = Usuario.objects.get(username="novo_usuario")
        assert created.telefone == "85999990000"
        assert created.cargo == "Coordenador Operacional"

    def test_dat_can_update_usuario_telefone_cargo_and_active(self, api_client, usuario_dat, db):
        """DAT pode atualizar telefone/cargo e status ativo de usuários comuns."""
        target = Usuario.objects.create_user(
            username="usuario_perfil",
            email="perfil@example.com",
            password="SecurePass123!",
            cpf="10987654321",
        )

        api_client.force_authenticate(user=usuario_dat)
        payload = {
            "telefone": "85911112222",
            "cargo": "Gerente Regional",
            "is_active": False,
        }
        response = api_client.patch(f"/api/usuarios-admin/{target.id}/", payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert target.telefone == "85911112222"
        assert target.cargo == "Gerente Regional"
        assert target.is_active is False

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

    def test_dat_cannot_patch_is_superuser(self, api_client, usuario_dat, db):
        """DAT não pode alterar is_superuser via endpoint de admin."""
        target = Usuario.objects.create_user(
            username="target_common_user",
            email="target_common_user@example.com",
            password="SecurePass123!",
            cpf="12312312312",
        )

        api_client.force_authenticate(user=usuario_dat)
        response = api_client.patch(
            f"/api/usuarios-admin/{target.id}/",
            {"is_superuser": True},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        target.refresh_from_db()
        assert target.is_superuser is False

    def test_superuser_can_patch_is_superuser_for_other_user(self, api_client, db):
        """Superuser pode promover outro usuário para superuser via endpoint."""
        super_admin = Usuario.objects.create_superuser(
            username="api_super_admin",
            email="api_super_admin@example.com",
            password="SecurePass123!",
            cpf="22312312312",
        )
        target = Usuario.objects.create_user(
            username="api_target_common_user",
            email="api_target_common_user@example.com",
            password="SecurePass123!",
            cpf="32312312312",
        )

        api_client.force_authenticate(user=super_admin)
        response = api_client.patch(
            f"/api/usuarios-admin/{target.id}/",
            {"is_superuser": True},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert target.is_superuser is True


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


# ==========================
# Testes de RBAC Funcional (Issue #829)
# ==========================


@pytest.mark.django_db
class TestRbacFunctionalAPI:
    """Testes de endpoints RBAC funcional para DAT."""

    def test_dat_can_list_permissoes_funcionais(self, api_client, usuario_dat):
        """DAT pode listar permissões funcionais."""
        permissao = PermissaoFuncional.objects.create(
            codename="rbac.test_list",
            label="Permissão Teste Lista",
            description="Teste de listagem RBAC",
            category="admin",
            is_system=False,
        )

        api_client.force_authenticate(user=usuario_dat)
        response = api_client.get("/api/permissoes-funcionais/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 1
        returned_ids = {item["id"] for item in response.data["results"]}
        assert permissao.id in returned_ids

    def test_non_dat_cannot_access_permissoes_funcionais(self, api_client, usuario_controle):
        """Usuário sem DAT não pode acessar permissões funcionais."""
        api_client.force_authenticate(user=usuario_controle)
        response = api_client.get("/api/permissoes-funcionais/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_dat_can_get_rbac_meta(self, api_client, usuario_dat):
        """DAT pode consultar metadados de RBAC."""
        PermissaoFuncional.objects.create(
            codename="rbac.meta_category",
            label="Permissão Categoria Meta",
            description="Valida retorno de category no meta",
            category="governanca",
            is_system=False,
        )

        api_client.force_authenticate(user=usuario_dat)
        response = api_client.get("/api/rbac/meta/")

        assert response.status_code == status.HTTP_200_OK
        assert "setor_groups" in response.data
        assert "funcao_groups" in response.data
        assert "categories" in response.data
        assert "DAT" in response.data["setor_groups"]
        assert "Gerente" in response.data["funcao_groups"]
        assert "governanca" in response.data["categories"]

    def test_dat_can_create_group_as_funcao_and_meta_reflects(self, api_client, usuario_dat):
        """Grupo criado como função aparece em funcao_groups do /rbac/meta/."""
        api_client.force_authenticate(user=usuario_dat)

        create_response = api_client.post(
            "/api/grupos/",
            {"name": "Analista de Campo", "group_type_input": "funcao"},
            format="json",
        )

        assert create_response.status_code == status.HTTP_201_CREATED
        assert create_response.data["group_type"] == "funcao"

        group = Group.objects.get(name="Analista de Campo")
        classificacao = GroupClassificacao.objects.get(group=group)
        assert classificacao.tipo == GroupClassificacao.Tipo.FUNCAO

        meta_response = api_client.get("/api/rbac/meta/")
        assert meta_response.status_code == status.HTTP_200_OK
        assert "Analista de Campo" in meta_response.data["funcao_groups"]

    def test_dat_create_group_rejects_invalid_group_type(self, api_client, usuario_dat):
        """Criação de grupo rejeita tipo inválido."""
        api_client.force_authenticate(user=usuario_dat)

        response = api_client.post(
            "/api/grupos/",
            {"name": "Grupo Invalido Tipo", "group_type_input": "perfil"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "group_type_input" in response.data["errors"]

    def test_dat_can_patch_group_permissoes_funcionais(self, api_client, usuario_dat):
        """DAT pode vincular permissões funcionais a um grupo."""
        group, _ = Group.objects.get_or_create(name="Equipe Operacional")
        permissao_a = PermissaoFuncional.objects.create(
            codename="rbac.group_patch_a",
            label="Permissão Group Patch A",
            description="Teste patch A",
            category="operacao",
            is_system=False,
        )
        permissao_b = PermissaoFuncional.objects.create(
            codename="rbac.group_patch_b",
            label="Permissão Group Patch B",
            description="Teste patch B",
            category="operacao",
            is_system=False,
        )

        api_client.force_authenticate(user=usuario_dat)
        payload = {"permissao_funcional_ids": [permissao_a.id, permissao_b.id]}
        response = api_client.patch(f"/api/grupos/{group.id}/", payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        group.refresh_from_db()
        linked_ids = set(group.permissoes_funcionais.values_list("id", flat=True))
        assert linked_ids == {permissao_a.id, permissao_b.id}
        returned_ids = {item["id"] for item in response.data["permissoes_funcionais"]}
        assert returned_ids == {permissao_a.id, permissao_b.id}

    def test_rename_reserved_group_requires_confirmation(self, api_client, usuario_dat):
        """Renomeio de grupo reservado exige ?confirm_reserved=true."""
        group, _ = Group.objects.get_or_create(name="Controle")
        api_client.force_authenticate(user=usuario_dat)

        response = api_client.patch(f"/api/grupos/{group.id}/", {"name": "Controle Novo"}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "confirm_reserved=true" in str(response.data)

    def test_delete_reserved_group_requires_confirmation(self, api_client, usuario_dat):
        """Exclusão de grupo reservado exige ?confirm_reserved=true."""
        group, _ = Group.objects.get_or_create(name="Formador")
        api_client.force_authenticate(user=usuario_dat)

        response = api_client.delete(f"/api/grupos/{group.id}/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Group.objects.filter(id=group.id).exists()

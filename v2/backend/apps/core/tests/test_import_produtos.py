"""
Testes para importacao de Produtos.

Cobertura:
- Service: import_produtos_from_file()
- View: ImportProdutosView
- RBAC: Permissoes HasPerm("import_spreadsheet")
- Idempotencia: Nao duplica registros (codigo e chave)
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

from apps.core.models import Produto, Projeto
from apps.core.services.produtos_import import import_produtos_from_file

# URL direta (evita problemas de cache de rotas no container)
IMPORT_PRODUTOS_URL = "/api/produtos/import/"

User = get_user_model()


@pytest.fixture
def controle_user(db):
    """Usuario do grupo Controle (com permissao de import)."""
    user = User.objects.create_user(
        username="controle_user",
        email="controle@test.com",
        password="testpass123",
        cpf="11111111111",
        first_name="Controle",
        last_name="User",
    )
    group, _ = Group.objects.get_or_create(name="Controle")
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
def projeto_teste(db):
    """Projeto de teste para vincular produtos."""
    return Projeto.objects.create(
        nome="Projeto Teste",
        codigo="PROJ-TEST",
        fluxo="NAO_SUPER",
        ativo=True,
    )


@pytest.fixture
def projeto_acerta(db):
    """Projeto ACerta para testes."""
    return Projeto.objects.create(
        nome="ACERTA MATEMATICA",
        codigo="ACERTA",
        fluxo="NAO_SUPER",
        ativo=True,
    )


@pytest.fixture
def sample_csv(db, projeto_teste):
    """Cria arquivo CSV de teste com produtos validos."""
    content = f"""codigo,nome,projeto,descricao
PROD-001,Produto Teste 1,{projeto_teste.nome},Descricao do produto 1
PROD-002,Produto Teste 2,{projeto_teste.codigo},Descricao do produto 2
"""
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    temp.write(content)
    temp.close()
    yield temp.name
    Path(temp.name).unlink(missing_ok=True)


@pytest.fixture
def sample_csv_missing_codigo(db, projeto_teste):
    """CSV com codigo ausente."""
    content = f"""codigo,nome,projeto
,Sem Codigo,{projeto_teste.nome}
  ,Espacos,{projeto_teste.nome}
"""
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    temp.write(content)
    temp.close()
    yield temp.name
    Path(temp.name).unlink(missing_ok=True)


@pytest.fixture
def sample_csv_missing_nome(db, projeto_teste):
    """CSV com nome ausente."""
    content = f"""codigo,nome,projeto
PROD-SEM-NOME,,{projeto_teste.nome}
PROD-ESPACOS,   ,{projeto_teste.nome}
"""
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    temp.write(content)
    temp.close()
    yield temp.name
    Path(temp.name).unlink(missing_ok=True)


@pytest.fixture
def sample_csv_projeto_not_found(db):
    """CSV com projeto inexistente."""
    content = """codigo,nome,projeto
PROD-ORFAO,Produto Orfao,Projeto Inexistente
"""
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    temp.write(content)
    temp.close()
    yield temp.name
    Path(temp.name).unlink(missing_ok=True)


@pytest.fixture
def sample_csv_flexible_headers(db, projeto_teste):
    """CSV com headers alternativos."""
    content = f"""CODE,NOME_PRODUTO,PROJECT,DESCRICAO,ATIVO
PROD-FLEX,Produto Flexivel,{projeto_teste.nome},Teste headers,sim
"""
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    temp.write(content)
    temp.close()
    yield temp.name
    Path(temp.name).unlink(missing_ok=True)


@pytest.fixture
def sample_csv_update_existing(db, projeto_teste, projeto_acerta):
    """CSV para testar atualizacao de produto existente."""
    # Criar produto existente
    Produto.objects.create(
        codigo="PROD-EXISTING",
        nome="Nome Antigo",
        descricao="Descricao antiga",
        projeto=projeto_teste,
        ativo=True,
    )

    content = f"""codigo,nome,projeto,descricao
PROD-EXISTING,Nome Novo,{projeto_acerta.nome},Descricao nova
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
class TestProdutosImportService:
    """Testes do service import_produtos_from_file."""

    def test_dry_run_returns_stats(self, sample_csv, projeto_teste):
        """dry_run=True retorna stats sem persistir."""
        initial_count = Produto.objects.count()

        result = import_produtos_from_file(path=sample_csv, dry_run=True)

        assert result["dry_run"] is True
        assert result["stats"]["created"] == 2
        assert result["stats"]["unchanged"] == 0

        # Nao deve ter criado no banco
        assert Produto.objects.count() == initial_count

    def test_apply_creates_records(self, sample_csv, projeto_teste):
        """dry_run=False persiste os registros."""
        initial_count = Produto.objects.count()

        result = import_produtos_from_file(path=sample_csv, dry_run=False)

        assert result["dry_run"] is False
        assert result["stats"]["created"] == 2

        # Deve ter criado no banco
        assert Produto.objects.count() == initial_count + 2

        # Verificar dados
        prod1 = Produto.objects.get(codigo="PROD-001")
        assert prod1.nome == "Produto Teste 1"
        assert prod1.projeto == projeto_teste
        assert prod1.descricao == "Descricao do produto 1"

        prod2 = Produto.objects.get(codigo="PROD-002")
        assert prod2.nome == "Produto Teste 2"
        assert prod2.projeto == projeto_teste

    def test_idempotency_no_duplicates(self, sample_csv, projeto_teste):
        """Rodar 2x nao duplica registros (codigo e chave)."""
        # Primeira execucao
        result1 = import_produtos_from_file(path=sample_csv, dry_run=False)
        assert result1["stats"]["created"] == 2
        count_after_first = Produto.objects.count()

        # Segunda execucao
        result2 = import_produtos_from_file(path=sample_csv, dry_run=False)
        assert result2["stats"]["created"] == 0
        assert result2["stats"]["unchanged"] == 2

        # Total no banco nao mudou
        assert Produto.objects.count() == count_after_first

    def test_updates_existing_product(self, sample_csv_update_existing, projeto_teste, projeto_acerta):
        """Atualiza produto existente com novos dados."""
        prod_before = Produto.objects.get(codigo="PROD-EXISTING")
        assert prod_before.nome == "Nome Antigo"
        assert prod_before.projeto == projeto_teste

        result = import_produtos_from_file(path=sample_csv_update_existing, dry_run=False)

        assert result["stats"]["updated"] == 1
        assert result["stats"]["created"] == 0

        prod_after = Produto.objects.get(codigo="PROD-EXISTING")
        assert prod_after.nome == "Nome Novo"
        assert prod_after.descricao == "Descricao nova"
        assert prod_after.projeto == projeto_acerta

    def test_missing_codigo_adds_pendencia(self, sample_csv_missing_codigo):
        """Codigo ausente adiciona pendencia."""
        result = import_produtos_from_file(path=sample_csv_missing_codigo, dry_run=True)

        assert result["stats"]["skipped"]["codigo_missing"] == 2
        assert len(result["pendencias"]["codigo_missing"]) == 2

    def test_missing_nome_adds_pendencia(self, sample_csv_missing_nome):
        """Nome ausente adiciona pendencia."""
        result = import_produtos_from_file(path=sample_csv_missing_nome, dry_run=True)

        assert result["stats"]["skipped"]["nome_missing"] == 2
        assert len(result["pendencias"]["nome_missing"]) == 2

    def test_projeto_not_found_adds_pendencia(self, sample_csv_projeto_not_found):
        """Projeto inexistente adiciona pendencia."""
        result = import_produtos_from_file(path=sample_csv_projeto_not_found, dry_run=True)

        assert result["stats"]["skipped"]["projeto_not_found"] == 1
        assert len(result["pendencias"]["projeto_not_found"]) == 1
        assert "Projeto Inexistente" in result["pendencias"]["projeto_not_found"][0]["projeto"]

    def test_header_flexibility(self, sample_csv_flexible_headers, projeto_teste):
        """Headers alternativos sao reconhecidos."""
        result = import_produtos_from_file(path=sample_csv_flexible_headers, dry_run=False)

        assert result["stats"]["created"] == 1

        produto = Produto.objects.get(codigo="PROD-FLEX")
        assert produto.nome == "Produto Flexivel"
        assert produto.projeto == projeto_teste
        assert produto.descricao == "Teste headers"
        assert produto.ativo is True

    def test_resolve_projeto_by_codigo(self, db, projeto_acerta):
        """Resolve projeto por codigo."""
        content = """codigo,nome,projeto
PROD-ACERTA,Kit ACERTA,ACERTA
"""
        temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
        temp.write(content)
        temp.close()

        result = import_produtos_from_file(path=temp.name, dry_run=False)

        assert result["stats"]["created"] == 1
        produto = Produto.objects.get(codigo="PROD-ACERTA")
        assert produto.projeto == projeto_acerta

        Path(temp.name).unlink()

    def test_resolve_projeto_case_insensitive(self, db, projeto_acerta):
        """Resolve projeto case-insensitive."""
        content = """codigo,nome,projeto
PROD-LOWER,Kit Lower,acerta matematica
"""
        temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
        temp.write(content)
        temp.close()

        result = import_produtos_from_file(path=temp.name, dry_run=False)

        assert result["stats"]["created"] == 1
        produto = Produto.objects.get(codigo="PROD-LOWER")
        assert produto.projeto == projeto_acerta

        Path(temp.name).unlink()


# =============================================================================
# TESTES DA VIEW
# =============================================================================


@pytest.mark.django_db
class TestImportProdutosView:
    """Testes da view ImportProdutosView."""

    def test_permission_denied_for_formador(self, api_client, formador_user, sample_csv):
        """Formador nao tem permissao (403)."""
        api_client.force_authenticate(user=formador_user)

        with open(sample_csv, "rb") as f:
            response = api_client.post(
                IMPORT_PRODUTOS_URL,
                {"file": f},
                format="multipart",
            )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_controle_user_can_import(self, api_client, controle_user, sample_csv, projeto_teste):
        """Usuario Controle pode importar."""
        api_client.force_authenticate(user=controle_user)

        with open(sample_csv, "rb") as f:
            response = api_client.post(
                IMPORT_PRODUTOS_URL + "?dry_run=true",
                {"file": f},
                format="multipart",
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["dry_run"] is True
        assert response.data["stats"]["created"] == 2

    def test_superuser_can_import(self, api_client, superuser, sample_csv, projeto_teste):
        """Superusuario pode importar."""
        api_client.force_authenticate(user=superuser)

        with open(sample_csv, "rb") as f:
            response = api_client.post(
                IMPORT_PRODUTOS_URL + "?dry_run=true",
                {"file": f},
                format="multipart",
            )

        assert response.status_code == status.HTTP_200_OK

    def test_apply_mode_persists(self, api_client, controle_user, sample_csv, projeto_teste):
        """dry_run=false persiste os dados."""
        initial_count = Produto.objects.count()
        api_client.force_authenticate(user=controle_user)

        with open(sample_csv, "rb") as f:
            response = api_client.post(
                IMPORT_PRODUTOS_URL + "?dry_run=false",
                {"file": f},
                format="multipart",
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["dry_run"] is False
        assert Produto.objects.count() == initial_count + 2

    def test_missing_file_returns_400(self, api_client, controle_user):
        """Arquivo ausente retorna 400."""
        api_client.force_authenticate(user=controle_user)

        response = api_client.post(
            IMPORT_PRODUTOS_URL,
            {},
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "file" in str(response.data).lower()

    def test_invalid_mime_type_returns_400(self, api_client, controle_user):
        """Tipo de arquivo invalido retorna 400."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        api_client.force_authenticate(user=controle_user)

        # Usar MIME type explicitamente inválido (não text/plain, pois CSVs podem ser text/plain)
        fake_file = SimpleUploadedFile("malicious.exe", b"MZ\x90\x00", content_type="application/x-msdownload")

        response = api_client.post(
            IMPORT_PRODUTOS_URL,
            {"file": fake_file},
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated_returns_401_or_403(self, api_client, sample_csv):
        """Usuario nao autenticado retorna 401 ou 403."""
        with open(sample_csv, "rb") as f:
            response = api_client.post(
                IMPORT_PRODUTOS_URL,
                {"file": f},
                format="multipart",
            )

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

"""
Testes para APIs de AcaoControle e AcaoDAT.

Endpoints testados:
- GET /api/controle/acoes/ (IsControleOrSuper)
- GET /api/dat/acoes/ (IsDATOrSuper)
- POST /api/dat/acoes/ (IsDATOrSuper)

Valida:
- RBAC (permissões corretas)
- Filtros de query params
- Serializers corretos (read vs write)
- Status codes
"""

import pytest
from datetime import date
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.models import AcaoControle, AcaoDAT, Municipio, Projeto


User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def setup_groups():
    """Cria grupos RBAC necessários."""
    controle = Group.objects.create(name="Controle")
    dat = Group.objects.create(name="DAT")
    superintendencia = Group.objects.create(name="Superintendência")
    return {"controle": controle, "dat": dat, "superintendencia": superintendencia}


@pytest.fixture
def user_controle(setup_groups):
    """Usuário do grupo Controle."""
    user = User.objects.create_user(
        username="controle1",
        email="controle@example.com",
        password="test123",
        cpf="11111111111",
    )
    user.groups.add(setup_groups["controle"])
    return user


@pytest.fixture
def user_dat(setup_groups):
    """Usuário do grupo DAT."""
    user = User.objects.create_user(
        username="dat1",
        email="dat@example.com",
        password="test123",
        cpf="22222222222",
    )
    user.groups.add(setup_groups["dat"])
    return user


@pytest.fixture
def user_regular(db):
    """Usuário sem grupos (regular)."""
    return User.objects.create_user(
        username="regular",
        email="regular@example.com",
        password="test123",
        cpf="33333333333",
    )


@pytest.fixture
def setup_data(db):
    """Cria dados de exemplo para testes."""
    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome="ACerta", ativo=True)

    coord = User.objects.create_user(
        username="coord1",
        email="coord@example.com",
        password="test123",
        cpf="44444444444",
    )

    acao_controle = AcaoControle.objects.create(
        municipio=municipio,
        projeto=projeto,
        coordenador=coord,
        data_entrega=date(2025, 1, 15),
        data_carta=date(2025, 1, 10),
        data_reuniao=date(2025, 2, 1),
        observacao="Teste controle",
    )

    acao_dat = AcaoDAT.objects.create(
        municipio=municipio,
        projeto=projeto,
        tipo_acao="Cadastro INEP",
        responsavel=coord,
        data_registro=date(2025, 1, 20),
        observacao="Teste DAT",
    )

    return {
        "municipio": municipio,
        "projeto": projeto,
        "coord": coord,
        "acao_controle": acao_controle,
        "acao_dat": acao_dat,
    }


# ════════════════════════════════════════════════════════════════════════════
# API: GET /api/controle/acoes/
# ════════════════════════════════════════════════════════════════════════════


class TestControleAcoesListAPI:
    """Testes para GET /api/controle/acoes/ (IsControleOrSuper)."""

    def test_controle_user_can_list(self, user_controle, setup_data):
        """Usuário do grupo Controle pode listar ações."""
        client = APIClient()
        client.force_authenticate(user=user_controle)

        response = client.get("/api/controle/acoes/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["observacao"] == "Teste controle"

    def test_regular_user_cannot_list(self, user_regular, setup_data):
        """Usuário sem permissão recebe 403."""
        client = APIClient()
        client.force_authenticate(user=user_regular)

        response = client.get("/api/controle/acoes/")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_cannot_list(self, setup_data):
        """Usuário não autenticado recebe 401."""
        client = APIClient()

        response = client.get("/api/controle/acoes/")

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_filter_by_date_range(self, user_controle, setup_data):
        """Filtro por data_inicio e data_fim funciona."""
        client = APIClient()
        client.force_authenticate(user=user_controle)

        # Criar segunda ação fora do intervalo
        AcaoControle.objects.create(
            municipio=setup_data["municipio"],
            projeto=setup_data["projeto"],
            data_entrega=date(2024, 12, 1),  # Fora do filtro
            observacao="Fora do intervalo",
        )

        response = client.get(
            "/api/controle/acoes/", {"data_inicio": "2025-01-01", "data_fim": "2025-12-31"}
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["observacao"] == "Teste controle"

    def test_serializer_uses_string_related_field(self, user_controle, setup_data):
        """Serializer retorna nomes legíveis (não IDs) para FKs."""
        client = APIClient()
        client.force_authenticate(user=user_controle)

        response = client.get("/api/controle/acoes/")

        assert response.status_code == status.HTTP_200_OK
        data = response.data[0]

        # StringRelatedField retorna __str__ do modelo
        assert isinstance(data["municipio"], str)
        assert isinstance(data["projeto"], str)
        # coordenador pode ser None ou string
        if data["coordenador"]:
            assert isinstance(data["coordenador"], str)


# ════════════════════════════════════════════════════════════════════════════
# API: GET /api/dat/acoes/
# ════════════════════════════════════════════════════════════════════════════


class TestDATAcoesListAPI:
    """Testes para GET /api/dat/acoes/ (IsDATOrSuper)."""

    def test_dat_user_can_list(self, user_dat, setup_data):
        """Usuário do grupo DAT pode listar ações."""
        client = APIClient()
        client.force_authenticate(user=user_dat)

        response = client.get("/api/dat/acoes/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["tipo_acao"] == "Cadastro INEP"

    def test_regular_user_cannot_list(self, user_regular, setup_data):
        """Usuário sem permissão recebe 403."""
        client = APIClient()
        client.force_authenticate(user=user_regular)

        response = client.get("/api/dat/acoes/")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_filter_by_projeto(self, user_dat, setup_data):
        """Filtro por projeto funciona."""
        client = APIClient()
        client.force_authenticate(user=user_dat)

        # Criar segunda ação em projeto diferente
        outro_projeto = Projeto.objects.create(nome="Outro Projeto", ativo=True)
        AcaoDAT.objects.create(
            municipio=setup_data["municipio"],
            projeto=outro_projeto,
            tipo_acao="Outra Ação",
        )

        response = client.get("/api/dat/acoes/", {"projeto": setup_data["projeto"].id})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["tipo_acao"] == "Cadastro INEP"

    def test_filter_by_tipo_acao(self, user_dat, setup_data):
        """Filtro parcial por tipo_acao (icontains) funciona."""
        client = APIClient()
        client.force_authenticate(user=user_dat)

        # Criar segunda ação com tipo diferente
        AcaoDAT.objects.create(
            municipio=setup_data["municipio"],
            projeto=setup_data["projeto"],
            tipo_acao="Cadastro SIGPEC",
        )

        response = client.get("/api/dat/acoes/", {"tipo_acao": "INEP"})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["tipo_acao"] == "Cadastro INEP"


# ════════════════════════════════════════════════════════════════════════════
# API: POST /api/dat/acoes/
# ════════════════════════════════════════════════════════════════════════════


class TestDATAcoesCreateAPI:
    """Testes para POST /api/dat/acoes/ (IsDATOrSuper)."""

    def test_dat_user_can_create(self, user_dat, setup_data):
        """Usuário do grupo DAT pode criar ações."""
        client = APIClient()
        client.force_authenticate(user=user_dat)

        payload = {
            "municipio": setup_data["municipio"].id,
            "projeto": setup_data["projeto"].id,
            "tipo_acao": "Novo Cadastro",
            "responsavel": setup_data["coord"].id,
            "data_registro": "2025-03-01",
            "observacao": "Criado via API",
        }

        response = client.post("/api/dat/acoes/", payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["tipo_acao"] == "Novo Cadastro"
        assert response.data["observacao"] == "Criado via API"

        # Verificar que foi criado no banco
        assert AcaoDAT.objects.filter(tipo_acao="Novo Cadastro").exists()

    def test_regular_user_cannot_create(self, user_regular, setup_data):
        """Usuário sem permissão recebe 403."""
        client = APIClient()
        client.force_authenticate(user=user_regular)

        payload = {
            "municipio": setup_data["municipio"].id,
            "projeto": setup_data["projeto"].id,
            "tipo_acao": "Tentativa bloqueada",
        }

        response = client.post("/api/dat/acoes/", payload, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_returns_read_serializer(self, user_dat, setup_data):
        """POST retorna serializer de leitura (StringRelatedField)."""
        client = APIClient()
        client.force_authenticate(user=user_dat)

        payload = {
            "municipio": setup_data["municipio"].id,
            "projeto": setup_data["projeto"].id,
            "tipo_acao": "Teste Serializer",
        }

        response = client.post("/api/dat/acoes/", payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED

        # Response usa AcaoDATSerializer (StringRelatedField)
        assert isinstance(response.data["municipio"], str)
        assert isinstance(response.data["projeto"], str)

    def test_create_without_optional_fields(self, user_dat, setup_data):
        """Criação funciona sem campos opcionais (responsavel, observacao, data_registro)."""
        client = APIClient()
        client.force_authenticate(user=user_dat)

        payload = {
            "municipio": setup_data["municipio"].id,
            "projeto": setup_data["projeto"].id,
            "tipo_acao": "Mínimo",
        }

        response = client.post("/api/dat/acoes/", payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["tipo_acao"] == "Mínimo"
        assert response.data["responsavel"] is None

    def test_create_missing_required_fields(self, user_dat, setup_data):
        """POST sem campos obrigatórios retorna 400."""
        client = APIClient()
        client.force_authenticate(user=user_dat)

        payload = {
            "municipio": setup_data["municipio"].id,
            # Falta projeto e tipo_acao
        }

        response = client.post("/api/dat/acoes/", payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

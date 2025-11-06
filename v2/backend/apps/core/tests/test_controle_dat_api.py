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


# ════════════════════════════════════════════════════════════════════════════
# API: GET /api/controle/acoes/
# ════════════════════════════════════════════════════════════════════════════


def test_controle_user_can_list():
    """Usuário do grupo Controle pode listar ações."""
    # Criar grupo e usuário
    controle_group, _ = Group.objects.get_or_create(name="Controle")
    user = User.objects.create_user(
        username="controle1",
        email="controle@example.com",
        password="test123",
        cpf="11111111111",
    )
    user.groups.add(controle_group)

    # Criar dados
    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome="ACerta", ativo=True)
    coord = User.objects.create_user(
        username="coord1",
        email="coord@example.com",
        password="test123",
        cpf="22222222222",
    )
    AcaoControle.objects.create(
        municipio=municipio,
        projeto=projeto,
        coordenador=coord,
        data_entrega=date(2025, 1, 15),
        data_reuniao=date(2025, 2, 1),
        observacao="Teste controle",
    )

    # Requisição
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/api/controle/acoes/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert len(response.data["results"]) == 1
    assert response.data["results"][0]["observacao"] == "Teste controle"


def test_regular_user_cannot_list_controle_acoes():
    """Usuário sem permissão recebe 403."""
    user = User.objects.create_user(
        username="regular",
        email="regular@example.com",
        password="test123",
        cpf="33333333333",
    )

    # Criar dados
    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome="ACerta", ativo=True)
    AcaoControle.objects.create(
        municipio=municipio,
        projeto=projeto,
        data_entrega=date(2025, 1, 15),
    )

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/api/controle/acoes/")

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_unauthenticated_cannot_list_controle_acoes():
    """Usuário não autenticado recebe 401."""
    client = APIClient()
    response = client.get("/api/controle/acoes/")

    assert response.status_code in [
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    ]


def test_filter_by_date_range():
    """Filtro por data_inicio e data_fim funciona."""
    controle_group, _ = Group.objects.get_or_create(name="Controle")
    user = User.objects.create_user(
        username="controle1",
        email="controle@example.com",
        password="test123",
        cpf="11111111111",
    )
    user.groups.add(controle_group)

    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome="ACerta", ativo=True)

    # Criar ação dentro do intervalo
    AcaoControle.objects.create(
        municipio=municipio,
        projeto=projeto,
        data_entrega=date(2025, 1, 15),
        observacao="Dentro do intervalo",
    )

    # Criar ação fora do intervalo
    AcaoControle.objects.create(
        municipio=municipio,
        projeto=projeto,
        data_entrega=date(2024, 12, 1),
        observacao="Fora do intervalo",
    )

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(
        "/api/controle/acoes/", {"data_inicio": "2025-01-01", "data_fim": "2025-12-31"}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert len(response.data["results"]) == 1
    assert response.data["results"][0]["observacao"] == "Dentro do intervalo"


def test_controle_serializer_uses_string_related_field():
    """Serializer retorna nomes legíveis (não IDs) para FKs."""
    controle_group, _ = Group.objects.get_or_create(name="Controle")
    user = User.objects.create_user(
        username="controle1",
        email="controle@example.com",
        password="test123",
        cpf="11111111111",
    )
    user.groups.add(controle_group)

    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome="ACerta", ativo=True)
    AcaoControle.objects.create(
        municipio=municipio,
        projeto=projeto,
        data_entrega=date(2025, 1, 15),
    )

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/api/controle/acoes/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    data = response.data["results"][0]

    # StringRelatedField retorna __str__ do modelo
    assert isinstance(data["municipio"], str)
    assert isinstance(data["projeto"], str)


# ════════════════════════════════════════════════════════════════════════════
# API: GET /api/dat/acoes/
# ════════════════════════════════════════════════════════════════════════════


def test_dat_user_can_list():
    """Usuário do grupo DAT pode listar ações."""
    dat_group, _ = Group.objects.get_or_create(name="DAT")
    user = User.objects.create_user(
        username="dat1",
        email="dat@example.com",
        password="test123",
        cpf="22222222222",
    )
    user.groups.add(dat_group)

    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome="ACerta", ativo=True)
    AcaoDAT.objects.create(
        municipio=municipio,
        projeto=projeto,
        tipo_acao="Cadastro INEP",
        observacao="Teste DAT",
    )

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/api/dat/acoes/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert len(response.data["results"]) == 1
    assert response.data["results"][0]["tipo_acao"] == "Cadastro INEP"


def test_regular_user_cannot_list_dat_acoes():
    """Usuário sem permissão recebe 403."""
    user = User.objects.create_user(
        username="regular",
        email="regular@example.com",
        password="test123",
        cpf="33333333333",
    )

    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome="ACerta", ativo=True)
    AcaoDAT.objects.create(
        municipio=municipio,
        projeto=projeto,
        tipo_acao="Cadastro INEP",
    )

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/api/dat/acoes/")

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_filter_by_projeto():
    """Filtro por projeto funciona."""
    dat_group, _ = Group.objects.get_or_create(name="DAT")
    user = User.objects.create_user(
        username="dat1",
        email="dat@example.com",
        password="test123",
        cpf="22222222222",
    )
    user.groups.add(dat_group)

    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto1 = Projeto.objects.create(nome="ACerta", ativo=True)
    projeto2 = Projeto.objects.create(nome="Outro Projeto", ativo=True)

    AcaoDAT.objects.create(
        municipio=municipio,
        projeto=projeto1,
        tipo_acao="Cadastro INEP",
    )
    AcaoDAT.objects.create(
        municipio=municipio,
        projeto=projeto2,
        tipo_acao="Outra Ação",
    )

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/api/dat/acoes/", {"projeto": projeto1.id})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert len(response.data["results"]) == 1
    assert response.data["results"][0]["tipo_acao"] == "Cadastro INEP"


def test_filter_by_tipo_acao():
    """Filtro parcial por tipo_acao (icontains) funciona."""
    dat_group, _ = Group.objects.get_or_create(name="DAT")
    user = User.objects.create_user(
        username="dat1",
        email="dat@example.com",
        password="test123",
        cpf="22222222222",
    )
    user.groups.add(dat_group)

    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome="ACerta", ativo=True)

    AcaoDAT.objects.create(
        municipio=municipio,
        projeto=projeto,
        tipo_acao="Cadastro INEP",
    )
    AcaoDAT.objects.create(
        municipio=municipio,
        projeto=projeto,
        tipo_acao="Cadastro SIGPEC",
    )

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/api/dat/acoes/", {"tipo_acao": "INEP"})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert len(response.data["results"]) == 1
    assert response.data["results"][0]["tipo_acao"] == "Cadastro INEP"


# ════════════════════════════════════════════════════════════════════════════
# API: POST /api/dat/acoes/
# ════════════════════════════════════════════════════════════════════════════


def test_dat_user_can_create():
    """Usuário do grupo DAT pode criar ações."""
    dat_group, _ = Group.objects.get_or_create(name="DAT")
    user = User.objects.create_user(
        username="dat1",
        email="dat@example.com",
        password="test123",
        cpf="22222222222",
    )
    user.groups.add(dat_group)

    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome="ACerta", ativo=True)
    coord = User.objects.create_user(
        username="coord1",
        email="coord@example.com",
        password="test123",
        cpf="44444444444",
    )

    payload = {
        "municipio": municipio.id,
        "projeto": projeto.id,
        "tipo_acao": "Novo Cadastro",
        "responsavel": coord.id,
        "data_registro": "2025-03-01",
        "observacao": "Criado via API",
    }

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post("/api/dat/acoes/", payload, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["tipo_acao"] == "Novo Cadastro"
    assert response.data["observacao"] == "Criado via API"

    # Verificar que foi criado no banco
    assert AcaoDAT.objects.filter(tipo_acao="Novo Cadastro").exists()


def test_regular_user_cannot_create():
    """Usuário sem permissão recebe 403."""
    user = User.objects.create_user(
        username="regular",
        email="regular@example.com",
        password="test123",
        cpf="33333333333",
    )

    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome="ACerta", ativo=True)

    payload = {
        "municipio": municipio.id,
        "projeto": projeto.id,
        "tipo_acao": "Tentativa bloqueada",
    }

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post("/api/dat/acoes/", payload, format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_create_returns_read_serializer():
    """POST retorna serializer de leitura (StringRelatedField)."""
    dat_group, _ = Group.objects.get_or_create(name="DAT")
    user = User.objects.create_user(
        username="dat1",
        email="dat@example.com",
        password="test123",
        cpf="22222222222",
    )
    user.groups.add(dat_group)

    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome="ACerta", ativo=True)

    payload = {
        "municipio": municipio.id,
        "projeto": projeto.id,
        "tipo_acao": "Teste Serializer",
    }

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post("/api/dat/acoes/", payload, format="json")

    assert response.status_code == status.HTTP_201_CREATED

    # Response usa AcaoDATSerializer (StringRelatedField)
    assert isinstance(response.data["municipio"], str)
    assert isinstance(response.data["projeto"], str)


def test_create_without_optional_fields():
    """Criação funciona sem campos opcionais (responsavel, observacao, data_registro)."""
    dat_group, _ = Group.objects.get_or_create(name="DAT")
    user = User.objects.create_user(
        username="dat1",
        email="dat@example.com",
        password="test123",
        cpf="22222222222",
    )
    user.groups.add(dat_group)

    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome="ACerta", ativo=True)

    payload = {
        "municipio": municipio.id,
        "projeto": projeto.id,
        "tipo_acao": "Mínimo",
    }

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post("/api/dat/acoes/", payload, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["tipo_acao"] == "Mínimo"
    assert response.data["responsavel"] is None


def test_create_missing_required_fields():
    """POST sem campos obrigatórios retorna 400."""
    dat_group, _ = Group.objects.get_or_create(name="DAT")
    user = User.objects.create_user(
        username="dat1",
        email="dat@example.com",
        password="test123",
        cpf="22222222222",
    )
    user.groups.add(dat_group)

    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)

    payload = {
        "municipio": municipio.id,
        # Falta projeto e tipo_acao
    }

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post("/api/dat/acoes/", payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST

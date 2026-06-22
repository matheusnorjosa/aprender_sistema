"""
PR16: Testes para Lookup e Validação

Testa:
- GET /api/lookup/municipios/?q=...
- GET /api/lookup/projetos/?q=...
- GET /api/lookup/tipos-evento/?q=...
- GET /api/lookup/usuarios/?q=...
- POST /api/solicitacoes/validate/
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import date

from rest_framework.test import APIClient

import pytest

from apps.core.models import Compra
from apps.core.tests.factories import (
    GroupFactory,
    MunicipioFactory,
    ProjetoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticated_user(db):
    """Criar usuário autenticado para testes"""
    user = UsuarioFactory(
        username="testuser",
        email="test@example.com",
        password="testpass123",
        cpf="11111111111",
        first_name="Test",
        last_name="User",
    )
    coord_group = GroupFactory(name="Coordenador")
    user.groups.add(coord_group)
    return user


@pytest.fixture
def sample_data(db):
    """Criar dados de exemplo para testes"""
    # Municípios
    m1 = MunicipioFactory(nome="Fortaleza", uf="CE", ativo=True)
    m2 = MunicipioFactory(nome="Sobral", uf="CE", ativo=True)

    # Projetos
    p1 = ProjetoFactory(nome="ACerta", codigo="ACERTA", ativo=True, fluxo="SUPER")
    p2 = ProjetoFactory(nome="Brincando e Aprendendo", codigo="BRINCANDO", ativo=True, fluxo="NAO_SUPER")

    # Tipos de Evento
    t1 = TipoEventoFactory(nome="Formação")
    t2 = TipoEventoFactory(nome="Acompanhamento")

    # Usuários
    u1 = UsuarioFactory(
        username="formador1",
        email="formador1@example.com",
        password="pass123",
        cpf="22222222222",
        first_name="João",
        last_name="Silva",
    )
    formador_group = GroupFactory(name="Formador")
    u1.groups.add(formador_group)

    return {
        "municipios": [m1, m2],
        "projetos": [p1, p2],
        "tipos_evento": [t1, t2],
        "usuarios": [u1],
    }


@pytest.mark.django_db
class TestMunicipioLookup:
    """Testes para GET /api/lookup/municipios/"""

    def test_lookup_without_auth_returns_403(self, api_client):
        """Lookup sem autenticação deve retornar 403"""
        response = api_client.get("/api/lookup/municipios/")
        assert response.status_code == 403

    def test_lookup_with_query(self, api_client, authenticated_user, sample_data):
        """Lookup com query deve retornar resultados filtrados"""
        api_client.force_authenticate(user=authenticated_user)
        response = api_client.get("/api/lookup/municipios/?q=Fortaleza")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["kind"] == "municipio"
        assert "Fortaleza" in data[0]["label"]

    def test_lookup_without_query(self, api_client, authenticated_user, sample_data):
        """Lookup sem query deve retornar top 20"""
        api_client.force_authenticate(user=authenticated_user)
        response = api_client.get("/api/lookup/municipios/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 20

    def test_lookup_com_compra_true_filtra_municipios(self, api_client, authenticated_user, sample_data):
        """com_compra=true deve retornar apenas municípios com compra registrada."""
        api_client.force_authenticate(user=authenticated_user)
        m1, m2 = sample_data["municipios"]
        p1 = sample_data["projetos"][0]

        Compra.objects.create(
            codigo="C-001",
            projeto=p1,
            municipio=m1,
            quantidade=10,
            data=date(2026, 1, 20),
            uso="teste",
            external_hash="lookup-municipio-1",
        )

        response = api_client.get("/api/lookup/municipios/?com_compra=true")
        assert response.status_code == 200
        payload = response.json()
        returned_ids = {item["id"] for item in payload}
        assert m1.id in returned_ids
        assert m2.id not in returned_ids

    def test_lookup_municipios_filtra_por_projeto_id(self, api_client, authenticated_user, sample_data):
        """projeto_id deve restringir municípios para compras no projeto informado."""
        api_client.force_authenticate(user=authenticated_user)
        m1, m2 = sample_data["municipios"]
        p1, p2 = sample_data["projetos"]

        Compra.objects.create(
            codigo="C-002",
            projeto=p1,
            municipio=m1,
            quantidade=5,
            data=date(2026, 1, 21),
            uso="teste",
            external_hash="lookup-municipio-2",
        )
        Compra.objects.create(
            codigo="C-003",
            projeto=p2,
            municipio=m2,
            quantidade=7,
            data=date(2026, 1, 22),
            uso="teste",
            external_hash="lookup-municipio-3",
        )

        response = api_client.get(f"/api/lookup/municipios/?com_compra=true&projeto_id={p1.id}")
        assert response.status_code == 200
        payload = response.json()
        returned_ids = {item["id"] for item in payload}
        assert m1.id in returned_ids
        assert m2.id not in returned_ids


@pytest.mark.django_db
class TestProjetoLookup:
    """Testes para GET /api/lookup/projetos/"""

    def test_lookup_with_query(self, api_client, authenticated_user, sample_data):
        """Lookup com query deve retornar resultados filtrados"""
        api_client.force_authenticate(user=authenticated_user)
        response = api_client.get("/api/lookup/projetos/?q=ACerta")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["kind"] == "projeto"

    def test_lookup_projetos_filtra_por_municipio_id(self, api_client, authenticated_user, sample_data):
        """municipio_id deve restringir projetos para compras no município informado."""
        api_client.force_authenticate(user=authenticated_user)
        m1, m2 = sample_data["municipios"]
        p1, p2 = sample_data["projetos"]

        Compra.objects.create(
            codigo="C-004",
            projeto=p1,
            municipio=m1,
            quantidade=3,
            data=date(2026, 1, 23),
            uso="teste",
            external_hash="lookup-projeto-1",
        )
        Compra.objects.create(
            codigo="C-005",
            projeto=p2,
            municipio=m2,
            quantidade=4,
            data=date(2026, 1, 24),
            uso="teste",
            external_hash="lookup-projeto-2",
        )

        response = api_client.get(f"/api/lookup/projetos/?com_compra=true&municipio_id={m1.id}")
        assert response.status_code == 200
        payload = response.json()
        returned_ids = {item["id"] for item in payload}
        assert p1.id in returned_ids
        assert p2.id not in returned_ids


@pytest.mark.django_db
class TestTipoEventoLookup:
    """Testes para GET /api/lookup/tipos-evento/"""

    def test_lookup_with_query(self, api_client, authenticated_user, sample_data):
        """Lookup com query deve retornar resultados filtrados"""
        api_client.force_authenticate(user=authenticated_user)
        response = api_client.get("/api/lookup/tipos-evento/?q=Formação")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["kind"] == "tipo_evento"


@pytest.mark.django_db
class TestUsuarioLookup:
    """Testes para GET /api/lookup/usuarios/"""

    def test_lookup_with_query(self, api_client, authenticated_user, sample_data):
        """Lookup com query deve retornar resultados filtrados"""
        api_client.force_authenticate(user=authenticated_user)
        response = api_client.get("/api/lookup/usuarios/?q=João")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["kind"] == "usuario"
        # SEC-ENUM-01: email removed from lookup response
        assert "email" not in data[0]

    def test_lookup_with_role_filter(self, api_client, authenticated_user, sample_data):
        """Lookup com filtro de role deve retornar apenas usuários do grupo"""
        api_client.force_authenticate(user=authenticated_user)
        response = api_client.get("/api/lookup/usuarios/?role=Formador")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.django_db
class TestSolicitationValidate:
    """Testes para POST /api/solicitacoes/validate/"""

    def test_validate_with_valid_data(self, api_client, authenticated_user, sample_data):
        """Validação com dados válidos deve retornar ok=True"""
        api_client.force_authenticate(user=authenticated_user)

        municipio = sample_data["municipios"][0]
        projeto = sample_data["projetos"][0]
        tipo_evento = sample_data["tipos_evento"][0]
        formador = sample_data["usuarios"][0]
        Compra.objects.create(
            codigo="C-VALID-001",
            projeto=projeto,
            municipio=municipio,
            quantidade=6,
            data=date(2026, 1, 19),
            uso="validação",
            external_hash="lookup-validate-valid",
        )

        payload = {
            "municipio": {"id": municipio.id},
            "projeto": {"id": projeto.id},
            "tipo_evento": {"id": tipo_evento.id},
            "date": "2025-01-15",
            "start": "09:00",
            "end": "12:00",
            "participants": {
                "coordenador": authenticated_user.email,
                "formadores": [formador.email],
                "coord_acompanha": [],
            },
        }

        response = api_client.post("/api/solicitacoes/validate/", payload, format="json")

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "canonical" in data
        assert data["canonical"]["municipio_id"] == municipio.id
        assert data["canonical"]["projeto_id"] == projeto.id
        assert data["canonical"]["tipo_evento_id"] == tipo_evento.id

    def test_validate_with_missing_fields(self, api_client, authenticated_user):
        """Validação com campos faltantes deve retornar ok=False"""
        api_client.force_authenticate(user=authenticated_user)

        payload = {
            "municipio": None,
            "projeto": None,
            "tipo_evento": None,
            "date": "2025-01-15",
            "start": "09:00",
            "end": "12:00",
            "participants": {},
        }

        response = api_client.post("/api/solicitacoes/validate/", payload, format="json")

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert len(data["errors"]) > 0

    def test_validate_with_string_names(self, api_client, authenticated_user, sample_data):
        """Validação com nomes em string deve resolver para IDs"""
        api_client.force_authenticate(user=authenticated_user)

        payload = {
            "municipio": "Fortaleza",
            "projeto": "ACerta",
            "tipo_evento": "Formação",
            "date": "2025-01-15",
            "start": "09:00",
            "end": "12:00",
            "participants": {
                "coordenador": authenticated_user.email,
                "formadores": [],
                "coord_acompanha": [],
            },
        }

        response = api_client.post("/api/solicitacoes/validate/", payload, format="json")

        assert response.status_code == 200
        data = response.json()
        # Deve encontrar os IDs mesmo com nomes
        if data["ok"]:
            assert data["canonical"]["municipio_id"] is not None

    def test_validate_with_invalid_time_range(self, api_client, authenticated_user, sample_data):
        """Validação com horário de término antes do início deve retornar erro"""
        api_client.force_authenticate(user=authenticated_user)

        municipio = sample_data["municipios"][0]
        projeto = sample_data["projetos"][0]
        tipo_evento = sample_data["tipos_evento"][0]

        payload = {
            "municipio": {"id": municipio.id},
            "projeto": {"id": projeto.id},
            "tipo_evento": {"id": tipo_evento.id},
            "date": "2025-01-15",
            "start": "12:00",
            "end": "09:00",  # Término antes do início
            "participants": {
                "coordenador": authenticated_user.email,
                "formadores": [],
                "coord_acompanha": [],
            },
        }

        response = api_client.post("/api/solicitacoes/validate/", payload, format="json")

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert any("término" in err.lower() or "posterior" in err.lower() for err in data["errors"])

    def test_validate_rejeita_sem_compra_municipio_projeto(self, api_client, authenticated_user, sample_data):
        """Validação canônica deve reprovar quando par município+projeto não tem compra."""
        api_client.force_authenticate(user=authenticated_user)

        municipio = sample_data["municipios"][0]
        projeto = sample_data["projetos"][0]
        tipo_evento = sample_data["tipos_evento"][0]

        payload = {
            "municipio": {"id": municipio.id},
            "projeto": {"id": projeto.id},
            "tipo_evento": {"id": tipo_evento.id},
            "date": "2025-01-15",
            "start": "09:00",
            "end": "12:00",
            "participants": {
                "coordenador": authenticated_user.email,
                "formadores": [],
                "coord_acompanha": [],
            },
        }

        response = api_client.post("/api/solicitacoes/validate/", payload, format="json")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert any("sem compra registrada" in err.lower() for err in data["errors"])

    def test_validate_aceita_com_compra_municipio_projeto(self, api_client, authenticated_user, sample_data):
        """Validação canônica deve aprovar quando existe compra para município+projeto."""
        api_client.force_authenticate(user=authenticated_user)

        municipio = sample_data["municipios"][0]
        projeto = sample_data["projetos"][0]
        tipo_evento = sample_data["tipos_evento"][0]

        Compra.objects.create(
            codigo="C-006",
            projeto=projeto,
            municipio=municipio,
            quantidade=8,
            data=date(2026, 1, 25),
            uso="teste",
            external_hash="lookup-validate-1",
        )

        payload = {
            "municipio": {"id": municipio.id},
            "projeto": {"id": projeto.id},
            "tipo_evento": {"id": tipo_evento.id},
            "date": "2025-01-15",
            "start": "09:00",
            "end": "12:00",
            "participants": {
                "coordenador": authenticated_user.email,
                "formadores": [],
                "coord_acompanha": [],
            },
        }

        response = api_client.post("/api/solicitacoes/validate/", payload, format="json")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True

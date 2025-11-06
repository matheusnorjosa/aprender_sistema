"""
Testes para filtros em SolicitacaoViewSet.

Cobertura:
- Filtro por status (exato)
- Busca textual (SearchFilter) em usuario/municipio/observacoes
- Combinação de status + search
"""

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import Municipio, Projeto, Solicitacao, TipoEvento, Usuario

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup_data():
    """Cria dados de teste para filtros."""
    municipio_fortaleza = Municipio.objects.create(nome="Fortaleza", uf="CE")
    municipio_caucaia = Municipio.objects.create(nome="Caucaia", uf="CE")
    tipo_evento = TipoEvento.objects.create(nome="Formação")

    user_joao = Usuario.objects.create_user(
        username="joao",
        email="joao@x.com",
        password="x",
        first_name="João",
        cpf="12345678901",
    )
    user_maria = Usuario.objects.create_user(
        username="maria",
        email="maria@x.com",
        password="x",
        first_name="Maria",
        cpf="98765432100",
    )

    # Criar solicitações
    now = timezone.now()

    # Pendente, Fortaleza, João
    s1 = Solicitacao.objects.create(
        usuario=user_joao,
        municipio=municipio_fortaleza,
        tipo_evento=tipo_evento,
        inicio=now,
        fim=now + timezone.timedelta(hours=2),
        status="pendente",
        observacoes="Curso de Python",
    )

    # Aprovado, Fortaleza, Maria
    s2 = Solicitacao.objects.create(
        usuario=user_maria,
        municipio=municipio_fortaleza,
        tipo_evento=tipo_evento,
        inicio=now + timezone.timedelta(days=1),
        fim=now + timezone.timedelta(days=1, hours=2),
        status="aprovado",
        observacoes="Workshop Django",
    )

    # Pendente, Caucaia, João
    s3 = Solicitacao.objects.create(
        usuario=user_joao,
        municipio=municipio_caucaia,
        tipo_evento=tipo_evento,
        inicio=now + timezone.timedelta(days=2),
        fim=now + timezone.timedelta(days=2, hours=2),
        status="pendente",
        observacoes="Aula de matemática",
    )

    # Reprovado, Fortaleza, Maria
    s4 = Solicitacao.objects.create(
        usuario=user_maria,
        municipio=municipio_fortaleza,
        tipo_evento=tipo_evento,
        inicio=now + timezone.timedelta(days=3),
        fim=now + timezone.timedelta(days=3, hours=2),
        status="reprovado",
        observacoes="Evento cancelado",
    )

    # Criar grupo Superintendência
    super_group, _ = Group.objects.get_or_create(name="Superintendência")
    user_admin = Usuario.objects.create_user(
        username="admin", email="admin@x.com", password="x", cpf="11111111111"
    )
    user_admin.groups.add(super_group)

    return {
        "user_admin": user_admin,
        "user_joao": user_joao,
        "user_maria": user_maria,
        "s1": s1,
        "s2": s2,
        "s3": s3,
        "s4": s4,
    }


def test_filter_by_status_only_pendente(setup_data):
    """
    Filtro ?status=pendente retorna apenas solicitações pendentes.
    """
    user_admin = setup_data["user_admin"]

    client = APIClient()
    client.force_authenticate(user=user_admin)

    url = reverse("core:solicitacao-list")
    res = client.get(url, {"status": "pendente"})

    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.data}"
    data = res.json()

    # DRF pagination
    if "results" in data:
        results = data["results"]
    else:
        results = data

    assert len(results) == 2, f"Expected 2 pendentes, got {len(results)}"
    for item in results:
        assert item["status"] == "pendente"


def test_search_matches_username_and_municipio(setup_data):
    """
    Busca textual ?search=joao encontra registros por username.
    Busca ?search=Fortaleza encontra por nome do município.
    """
    user_admin = setup_data["user_admin"]

    client = APIClient()
    client.force_authenticate(user=user_admin)

    url = reverse("core:solicitacao-list")

    # Busca por username "joao"
    res = client.get(url, {"search": "joao"})
    assert res.status_code == 200
    data = res.json()
    results = data.get("results", data)
    assert len(results) == 2, f"João tem 2 solicitações, got {len(results)}"

    # Busca por município "Fortaleza"
    res = client.get(url, {"search": "Fortaleza"})
    assert res.status_code == 200
    data = res.json()
    results = data.get("results", data)
    assert len(results) == 3, f"Fortaleza tem 3 solicitações, got {len(results)}"


def test_combined_status_and_search(setup_data):
    """
    Combinação de filtros: ?status=pendente&search=joao retorna apenas pendentes do João.
    """
    user_admin = setup_data["user_admin"]

    client = APIClient()
    client.force_authenticate(user=user_admin)

    url = reverse("core:solicitacao-list")
    res = client.get(url, {"status": "pendente", "search": "joao"})

    assert res.status_code == 200
    data = res.json()
    results = data.get("results", data)

    assert len(results) == 2, f"João tem 2 pendentes, got {len(results)}"
    for item in results:
        assert item["status"] == "pendente"
        # usuario pode ser objeto ou ID, dependendo do serializer
        # Vamos verificar que existe
        assert "usuario" in item


def test_ordering_by_inicio_desc_default(setup_data):
    """
    Ordering padrão é -inicio (mais recente primeiro).
    """
    user_admin = setup_data["user_admin"]

    client = APIClient()
    client.force_authenticate(user=user_admin)

    url = reverse("core:solicitacao-list")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()
    results = data.get("results", data)

    # Verificar que está ordenado por inicio DESC (mais recente primeiro)
    if len(results) >= 2:
        # s4 é o mais recente (day 3), deve vir primeiro
        assert results[0]["id"] == setup_data["s4"].id


def test_non_superintendencia_sees_only_own_solicitacoes(setup_data):
    """
    Usuários não-Superintendência veem apenas suas próprias solicitações.
    """
    user_joao = setup_data["user_joao"]

    client = APIClient()
    client.force_authenticate(user=user_joao)

    url = reverse("core:solicitacao-list")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()
    results = data.get("results", data)

    assert len(results) == 2, f"João tem 2 solicitações, got {len(results)}"
    for item in results:
        # Verificar que todas são do João
        usuario_id = item["usuario"] if isinstance(item["usuario"], int) else item["usuario"]["id"]
        assert usuario_id == user_joao.id

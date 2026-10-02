"""
Testes para filtros em SolicitacaoViewSet.

Cobertura:
- Filtro por status (exato)
- Busca textual (SearchFilter) em usuario/municipio/observacoes
- Combinação de status + search
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.tests.factories import (
    GroupFactory,
    MunicipioFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup_data():
    """Cria dados de teste para filtros."""
    municipio_fortaleza = MunicipioFactory(nome="Fortaleza", uf="CE")
    municipio_caucaia = MunicipioFactory(nome="Caucaia", uf="CE")
    tipo_evento = TipoEventoFactory(nome="Formação")

    user_joao = UsuarioFactory(
        username="joao",
        email="joao@x.com",
        password="x",
        first_name="João",
        cpf="12345678901",
    )
    user_maria = UsuarioFactory(
        username="maria",
        email="maria@x.com",
        password="x",
        first_name="Maria",
        cpf="98765432100",
    )

    # Criar solicitações
    now = timezone.now()

    # Pendente, Fortaleza, João
    s1 = SolicitacaoFactory(
        usuario=user_joao,
        municipio=municipio_fortaleza,
        tipo_evento=tipo_evento,
        projeto=None,
        inicio=now,
        fim=now + timezone.timedelta(hours=2),
        status="pendente",
        observacoes="Curso de Python",
    )

    # Aprovado, Fortaleza, Maria
    s2 = SolicitacaoFactory(
        usuario=user_maria,
        municipio=municipio_fortaleza,
        tipo_evento=tipo_evento,
        projeto=None,
        inicio=now + timezone.timedelta(days=1),
        fim=now + timezone.timedelta(days=1, hours=2),
        status="aprovado",
        observacoes="Workshop Django",
    )

    # Pendente, Caucaia, João
    s3 = SolicitacaoFactory(
        usuario=user_joao,
        municipio=municipio_caucaia,
        tipo_evento=tipo_evento,
        projeto=None,
        inicio=now + timezone.timedelta(days=2),
        fim=now + timezone.timedelta(days=2, hours=2),
        status="pendente",
        observacoes="Aula de matemática",
    )

    # Reprovado, Fortaleza, Maria
    s4 = SolicitacaoFactory(
        usuario=user_maria,
        municipio=municipio_fortaleza,
        tipo_evento=tipo_evento,
        projeto=None,
        inicio=now + timezone.timedelta(days=3),
        fim=now + timezone.timedelta(days=3, hours=2),
        status="reprovado",
        observacoes="Evento cancelado",
    )

    # Criar grupo Superintendência
    super_group = GroupFactory(name="Superintendência")
    user_admin = UsuarioFactory(username="admin", email="admin@x.com", password="x", cpf="11111111111")
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


# ---------------------------------------------------------------------------
# Mapa de acesso 02/10 (P6): ?ordering=proximidade — a ordem da tela de Aprovações.
# De hoje em diante, do mais próximo ao mais distante; depois os passados, do mais
# recente ao mais antigo. "Hoje" é o início do dia em America/Fortaleza.
# ---------------------------------------------------------------------------


def _admin_e_base():
    admin = UsuarioFactory(username="ordenador", email="ordenador@x.com", password="x", is_superuser=True)
    return admin, {
        "usuario": admin,
        "municipio": MunicipioFactory(nome="Municipio Ordem", uf="CE"),
        "tipo_evento": TipoEventoFactory(nome="Formação Ordem"),
        "projeto": None,
        "status": "pendente",
    }


def _sol_em(base, inicio):
    return SolicitacaoFactory(**base, inicio=inicio, fim=inicio + timezone.timedelta(hours=1))


def _ids(client, **params):
    res = client.get(reverse("core:solicitacao-list"), params)
    assert res.status_code == 200, res.data
    return [item["id"] for item in res.json()["results"]]


def test_ordering_proximidade_futuros_crescente_depois_passados_recentes():
    admin, base = _admin_e_base()
    hoje = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)  # 00:00 em Fortaleza
    daqui_30d = _sol_em(base, hoje + timezone.timedelta(days=30, hours=9))
    ha_60d = _sol_em(base, hoje - timezone.timedelta(days=60))
    amanha = _sol_em(base, hoje + timezone.timedelta(days=1, hours=9))
    # Borda do fuso: ontem 22:30 em Fortaleza já é "hoje" em UTC, e continua sendo passado.
    ontem_a_noite = _sol_em(base, hoje - timezone.timedelta(hours=1, minutes=30))
    # Hoje 00:30 em Fortaleza: já é "de hoje em diante", mesmo que a hora tenha passado.
    hoje_cedo = _sol_em(base, hoje + timezone.timedelta(minutes=30))

    client = APIClient()
    client.force_authenticate(user=admin)

    assert _ids(client, status="pendente", ordering="proximidade", page_size=20) == [
        hoje_cedo.id,
        amanha.id,
        daqui_30d.id,
        ontem_a_noite.id,
        ha_60d.id,
    ]


def test_ordering_proximidade_paginas_seguem_a_ordem_e_desempatam_por_id():
    admin, base = _admin_e_base()
    hoje = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    distante = _sol_em(base, hoje + timezone.timedelta(days=40))
    perto_1 = _sol_em(base, hoje + timezone.timedelta(days=2))
    perto_2 = _sol_em(base, hoje + timezone.timedelta(days=2))  # mesmo início: desempate por id
    passado_1 = _sol_em(base, hoje - timezone.timedelta(days=3))
    passado_2 = _sol_em(base, hoje - timezone.timedelta(days=3))

    client = APIClient()
    client.force_authenticate(user=admin)
    paginas = [_ids(client, ordering="proximidade", page_size=2, page=n) for n in (1, 2, 3)]

    assert paginas == [[perto_1.id, perto_2.id], [distante.id, passado_1.id], [passado_2.id]]

    res = client.get(reverse("core:solicitacao-list"), {"ordering": "proximidade", "page_size": 2})
    assert res.json()["count"] == 5


def test_ordering_proximidade_nao_muda_os_outros_valores_de_ordering():
    """Guarda: `inicio` e o default (-inicio) seguem como eram."""
    admin, base = _admin_e_base()
    hoje = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    passado = _sol_em(base, hoje - timezone.timedelta(days=5))
    futuro = _sol_em(base, hoje + timezone.timedelta(days=5))

    client = APIClient()
    client.force_authenticate(user=admin)

    assert _ids(client, ordering="inicio") == [passado.id, futuro.id]
    assert _ids(client, ordering="-inicio") == [futuro.id, passado.id]
    assert _ids(client) == [futuro.id, passado.id]

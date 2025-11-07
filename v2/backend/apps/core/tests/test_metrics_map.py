"""
Testes para endpoint de métricas do mapa (PR 11/N).

Cobertura:
- Permissões (IsControleOrDAT)
- Validação de parâmetros
- Agregação correta por UF
- Filtros (status + projeto_id)
- Caso zero-state

Endpoint testado:
- GET /api/metrics/map/
"""

from datetime import timedelta

from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

import pytest
from apps.core.models import Municipio, Projeto, Solicitacao, TipoEvento, Usuario
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def grupos():
    """Criar grupos necessários para os testes."""
    return {
        "controle": Group.objects.get_or_create(name="Controle")[0],
        "dat": Group.objects.get_or_create(name="DAT")[0],
        "superintendencia": Group.objects.get_or_create(name="Superintendência")[0],
        "coordenador": Group.objects.get_or_create(name="Coordenador")[0],
        "formador": Group.objects.get_or_create(name="Formador")[0],
    }


@pytest.fixture
def user_controle(grupos):
    """Usuário do grupo Controle."""
    user = Usuario.objects.create_user(
        username="controle1", email="controle@x.com", password="x", cpf="11111111111"
    )
    user.groups.add(grupos["controle"])
    return user


@pytest.fixture
def user_dat(grupos):
    """Usuário do grupo DAT."""
    user = Usuario.objects.create_user(
        username="dat1", email="dat@x.com", password="x", cpf="22222222222"
    )
    user.groups.add(grupos["dat"])
    return user


@pytest.fixture
def user_coordenador(grupos):
    """Usuário do grupo Coordenador (sem permissão)."""
    user = Usuario.objects.create_user(
        username="coord1", email="coord@x.com", password="x", cpf="33333333333"
    )
    user.groups.add(grupos["coordenador"])
    return user


@pytest.fixture
def user_formador(grupos):
    """Usuário do grupo Formador (sem permissão)."""
    user = Usuario.objects.create_user(
        username="form1", email="form@x.com", password="x", cpf="44444444444"
    )
    user.groups.add(grupos["formador"])
    return user


@pytest.fixture
def dados_basicos(grupos):
    """Criar dados básicos para os testes."""
    # Formadores (usuários)
    formador1 = Usuario.objects.create_user(
        username="ana.silva", email="ana@x.com", password="x", cpf="55555555555"
    )
    formador1.groups.add(grupos["formador"])

    # Municípios (3 UFs diferentes)
    mun_ce = Municipio.objects.create(nome="Fortaleza", uf="CE", ibge_code="2304400")
    mun_sp = Municipio.objects.create(nome="São Paulo", uf="SP", ibge_code="3550308")
    mun_ba = Municipio.objects.create(nome="Salvador", uf="BA", ibge_code="2927408")

    # Projetos (fluxo='SUPER' para permitir testar diferentes status)
    proj1 = Projeto.objects.create(nome="Vida & Matemática", codigo="P001", fluxo='SUPER')
    proj2 = Projeto.objects.create(nome="TEMA", codigo="P002", fluxo='SUPER')

    # Tipos de evento
    tipo1 = TipoEvento.objects.create(nome="Formação Inicial")

    return {
        "formador": formador1,
        "municipios": {"ce": mun_ce, "sp": mun_sp, "ba": mun_ba},
        "projetos": {"matematica": proj1, "tema": proj2},
        "tipo": tipo1,
    }


@pytest.fixture
def solicitacoes_variedade(dados_basicos):
    """Criar solicitações com variedade de status, UFs e projetos."""
    now = timezone.now()
    formador = dados_basicos["formador"]

    # Criar um usuário coordenador para ser o criador
    coordenador = Usuario.objects.create_user(
        username="coord_test", email="coord_test@x.com", password="x", cpf="88888888888"
    )

    solicitacoes = []

    # 3 aprovadas em CE, projeto Matemática
    for i in range(3):
        sol = Solicitacao.objects.create(
            usuario=coordenador,
            status="aprovado",
            inicio=now + timedelta(days=i),
            fim=now + timedelta(days=i, hours=2),
            municipio=dados_basicos["municipios"]["ce"],
            projeto=dados_basicos["projetos"]["matematica"],
            tipo_evento=dados_basicos["tipo"],
        )
        sol.formadores.add(formador)
        solicitacoes.append(sol)

    # 2 pendentes em SP, projeto TEMA
    for i in range(2):
        sol = Solicitacao.objects.create(
            usuario=coordenador,
            status="pendente",
            inicio=now + timedelta(days=10 + i),
            fim=now + timedelta(days=10 + i, hours=2),
            municipio=dados_basicos["municipios"]["sp"],
            projeto=dados_basicos["projetos"]["tema"],
            tipo_evento=dados_basicos["tipo"],
        )
        sol.formadores.add(formador)
        solicitacoes.append(sol)

    # 1 reprovada em BA, projeto Matemática
    sol = Solicitacao.objects.create(
        usuario=coordenador,
        status="reprovado",
        inicio=now + timedelta(days=20),
        fim=now + timedelta(days=20, hours=2),
        municipio=dados_basicos["municipios"]["ba"],
        projeto=dados_basicos["projetos"]["matematica"],
        tipo_evento=dados_basicos["tipo"],
    )
    sol.formadores.add(formador)
    solicitacoes.append(sol)

    return solicitacoes


# ============================================================================
# TESTES DE PERMISSÕES
# ============================================================================


def test_map_metrics_requires_authentication():
    """Endpoint metrics/map/ exige autenticação."""
    client = APIClient()
    url = reverse("core:metrics-map")
    res = client.get(url)

    # DRF retorna 403 quando a permission class rejeita
    assert res.status_code == 403, "Deve retornar 403 para não autenticado"


def test_map_metrics_controle_allowed(user_controle):
    """Usuário do grupo Controle tem acesso."""
    client = APIClient()
    client.force_authenticate(user=user_controle)

    url = reverse("core:metrics-map")
    res = client.get(url)

    assert res.status_code == 200, f"Controle deve ter acesso: {res.data}"


def test_map_metrics_dat_allowed(user_dat):
    """Usuário do grupo DAT tem acesso."""
    client = APIClient()
    client.force_authenticate(user=user_dat)

    url = reverse("core:metrics-map")
    res = client.get(url)

    assert res.status_code == 200, f"DAT deve ter acesso: {res.data}"


def test_map_metrics_coordenador_forbidden(user_coordenador):
    """Usuário do grupo Coordenador NÃO tem acesso."""
    client = APIClient()
    client.force_authenticate(user=user_coordenador)

    url = reverse("core:metrics-map")
    res = client.get(url)

    assert res.status_code == 403, "Coordenador não deve ter acesso"


def test_map_metrics_formador_forbidden(user_formador):
    """Usuário do grupo Formador NÃO tem acesso."""
    client = APIClient()
    client.force_authenticate(user=user_formador)

    url = reverse("core:metrics-map")
    res = client.get(url)

    assert res.status_code == 403, "Formador não deve ter acesso"


def test_map_metrics_superuser_allowed():
    """Superuser sempre tem acesso."""
    user = Usuario.objects.create_superuser(
        username="admin", email="admin@x.com", password="x", cpf="99999999999"
    )
    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("core:metrics-map")
    res = client.get(url)

    assert res.status_code == 200, "Superuser deve ter acesso"


# ============================================================================
# TESTES DE ESTRUTURA DA RESPOSTA
# ============================================================================


def test_map_metrics_response_structure(user_controle, solicitacoes_variedade):
    """Resposta tem estrutura esperada."""
    client = APIClient()
    client.force_authenticate(user=user_controle)

    url = reverse("core:metrics-map")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    # Verificar meta
    assert "meta" in data
    assert "generated_at" in data["meta"]
    assert "filters" in data["meta"]

    # Verificar totals
    assert "totals" in data
    assert "all" in data["totals"]
    assert "by_status" in data["totals"]

    # Verificar by_uf
    assert "by_uf" in data
    assert isinstance(data["by_uf"], list)

    # Verificar top_projetos
    assert "top_projetos" in data
    assert isinstance(data["top_projetos"], list)


# ============================================================================
# TESTES DE AGREGAÇÃO POR UF
# ============================================================================


def test_map_metrics_by_uf_aggregation(user_controle, solicitacoes_variedade):
    """Agregação por UF está correta."""
    client = APIClient()
    client.force_authenticate(user=user_controle)

    url = reverse("core:metrics-map")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    # Converter by_uf para dict para facilitar verificação
    by_uf_dict = {item["uf"]: item["count"] for item in data["by_uf"]}

    # Verificar contagens (3 CE + 2 SP + 1 BA = 6 total)
    assert by_uf_dict.get("CE", 0) == 3
    assert by_uf_dict.get("SP", 0) == 2
    assert by_uf_dict.get("BA", 0) == 1
    assert data["totals"]["all"] == 6


def test_map_metrics_by_uf_ordered_descending(user_controle, solicitacoes_variedade):
    """UFs ordenadas por contagem decrescente."""
    client = APIClient()
    client.force_authenticate(user=user_controle)

    url = reverse("core:metrics-map")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    by_uf = data["by_uf"]

    # Primeira UF deve ser CE (maior contagem = 3)
    assert by_uf[0]["uf"] == "CE"
    assert by_uf[0]["count"] == 3

    # Contagens devem estar em ordem decrescente
    for i in range(len(by_uf) - 1):
        assert by_uf[i]["count"] >= by_uf[i + 1]["count"]


# ============================================================================
# TESTES DE FILTROS
# ============================================================================


def test_map_metrics_filter_by_status(user_controle, solicitacoes_variedade):
    """Filtro por status funciona corretamente."""
    client = APIClient()
    client.force_authenticate(user=user_controle)

    url = reverse("core:metrics-map")

    # Filtrar por aprovado (3 solicitações)
    res = client.get(url, {"status": "aprovado"})
    assert res.status_code == 200
    data = res.json()

    assert data["totals"]["all"] == 3
    assert data["meta"]["filters"]["status"] == "aprovado"

    # Deve ter apenas CE (3 aprovadas estão em CE)
    by_uf_dict = {item["uf"]: item["count"] for item in data["by_uf"]}
    assert by_uf_dict.get("CE", 0) == 3
    assert "SP" not in by_uf_dict
    assert "BA" not in by_uf_dict


def test_map_metrics_filter_by_projeto(
    user_controle, solicitacoes_variedade, dados_basicos
):
    """Filtro por projeto_id funciona corretamente."""
    client = APIClient()
    client.force_authenticate(user=user_controle)

    url = reverse("core:metrics-map")
    projeto_matematica_id = dados_basicos["projetos"]["matematica"].id

    # Filtrar por projeto Matemática (4 solicitações: 3 CE + 1 BA)
    res = client.get(url, {"projeto_id": projeto_matematica_id})
    assert res.status_code == 200
    data = res.json()

    assert data["totals"]["all"] == 4
    assert data["meta"]["filters"]["projeto_id"] == projeto_matematica_id

    # Deve ter CE (3) e BA (1)
    by_uf_dict = {item["uf"]: item["count"] for item in data["by_uf"]}
    assert by_uf_dict.get("CE", 0) == 3
    assert by_uf_dict.get("BA", 0) == 1
    assert "SP" not in by_uf_dict


def test_map_metrics_filter_combined(
    user_controle, solicitacoes_variedade, dados_basicos
):
    """Filtros combinados (status + projeto_id) funcionam corretamente."""
    client = APIClient()
    client.force_authenticate(user=user_controle)

    url = reverse("core:metrics-map")
    projeto_matematica_id = dados_basicos["projetos"]["matematica"].id

    # Filtrar por aprovado + Matemática (3 solicitações em CE)
    res = client.get(url, {"status": "aprovado", "projeto_id": projeto_matematica_id})
    assert res.status_code == 200
    data = res.json()

    assert data["totals"]["all"] == 3
    assert data["meta"]["filters"]["status"] == "aprovado"
    assert data["meta"]["filters"]["projeto_id"] == projeto_matematica_id

    # Apenas CE
    by_uf_dict = {item["uf"]: item["count"] for item in data["by_uf"]}
    assert by_uf_dict.get("CE", 0) == 3


# ============================================================================
# TESTES DE VALIDAÇÃO
# ============================================================================


def test_map_metrics_invalid_status(user_controle):
    """Status inválido retorna 400."""
    client = APIClient()
    client.force_authenticate(user=user_controle)

    url = reverse("core:metrics-map")
    res = client.get(url, {"status": "invalido"})

    assert res.status_code == 400
    assert "detail" in res.json()


def test_map_metrics_invalid_projeto_id(user_controle):
    """projeto_id não numérico retorna 400."""
    client = APIClient()
    client.force_authenticate(user=user_controle)

    url = reverse("core:metrics-map")
    res = client.get(url, {"projeto_id": "nao-numero"})

    assert res.status_code == 400
    assert "detail" in res.json()


# ============================================================================
# TESTES DE CASO ZERO-STATE
# ============================================================================


def test_map_metrics_empty_database(user_controle):
    """Com banco vazio, retorna arrays vazios e counts = 0."""
    client = APIClient()
    client.force_authenticate(user=user_controle)

    url = reverse("core:metrics-map")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    assert data["totals"]["all"] == 0
    assert data["by_uf"] == []
    assert data["top_projetos"] == []


# ============================================================================
# TESTES DE TOP PROJETOS
# ============================================================================


def test_map_metrics_top_projetos(user_controle, solicitacoes_variedade, dados_basicos):
    """Top projetos ordenados por contagem."""
    client = APIClient()
    client.force_authenticate(user=user_controle)

    url = reverse("core:metrics-map")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    top_projetos = data["top_projetos"]

    # Deve ter 2 projetos
    assert len(top_projetos) == 2

    # Primeiro deve ser Matemática (4 solicitações: 3 aprovadas + 1 reprovada)
    assert top_projetos[0]["nome"] == "Vida & Matemática"
    assert top_projetos[0]["count"] == 4

    # Segundo deve ser TEMA (2 solicitações pendentes)
    assert top_projetos[1]["nome"] == "TEMA"
    assert top_projetos[1]["count"] == 2

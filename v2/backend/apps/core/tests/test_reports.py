"""
Testes para endpoints de Reports (PR 10/N - Dashboards).

Cobertura:
- Permissões (IsSuperOrControleOrDAT)
- Validação de parâmetros
- Agregação correta de dados
- Comportamento de cache
- Date ranges e edge cases

Endpoints testados:
- GET /api/reports/solicitacoes/status-counts
- GET /api/reports/solicitacoes/top-projects
- GET /api/reports/solicitacoes/weekly-approved
- GET /api/reports/solicitacoes/by-uf
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import datetime, timedelta

from django.contrib.auth.models import Group
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import Municipio, Projeto, Solicitacao, TipoEvento, Usuario

pytestmark = pytest.mark.django_db


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def clear_cache():
    """Limpar cache antes de cada teste."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def grupos():
    """Criar grupos necessários para os testes."""
    return {
        "superintendencia": Group.objects.get_or_create(name="Superintendência")[0],
        "controle": Group.objects.get_or_create(name="Controle")[0],
        "dat": Group.objects.get_or_create(name="DAT")[0],
        "coordenador": Group.objects.get_or_create(name="Coordenador")[0],
        "formador": Group.objects.get_or_create(name="Formador")[0],
    }


@pytest.fixture
def user_super(grupos):
    """Usuário do grupo Superintendência."""
    user = Usuario.objects.create_user(username="super1", email="super@x.com", password="x", cpf="11111111111")
    user.groups.add(grupos["superintendencia"])
    return user


@pytest.fixture
def user_controle(grupos):
    """Usuário do grupo Controle."""
    user = Usuario.objects.create_user(username="controle1", email="controle@x.com", password="x", cpf="22222222222")
    user.groups.add(grupos["controle"])
    return user


@pytest.fixture
def user_dat(grupos):
    """Usuário do grupo DAT."""
    user = Usuario.objects.create_user(username="dat1", email="dat@x.com", password="x", cpf="33333333333")
    user.groups.add(grupos["dat"])
    return user


@pytest.fixture
def user_coordenador(grupos):
    """Usuário do grupo Coordenador (sem permissão)."""
    user = Usuario.objects.create_user(username="coord1", email="coord@x.com", password="x", cpf="44444444444")
    user.groups.add(grupos["coordenador"])
    return user


@pytest.fixture
def user_formador(grupos):
    """Usuário do grupo Formador (sem permissão)."""
    user = Usuario.objects.create_user(username="form1", email="form@x.com", password="x", cpf="55555555555")
    user.groups.add(grupos["formador"])
    return user


@pytest.fixture
def dados_basicos(grupos):
    """Criar dados básicos para os testes."""
    # Formadores (usuários)
    formador1 = Usuario.objects.create_user(username="ana.silva", email="ana@x.com", password="x", cpf="66666666666")
    formador1.groups.add(grupos["formador"])

    formador2 = Usuario.objects.create_user(username="joao.santos", email="joao@x.com", password="x", cpf="77777777777")
    formador2.groups.add(grupos["formador"])

    # Municípios
    mun_ce = Municipio.objects.create(nome="Fortaleza", uf="CE", ibge_code="2304400")
    mun_pe = Municipio.objects.create(nome="Recife", uf="PE", ibge_code="2611606")
    mun_ba = Municipio.objects.create(nome="Salvador", uf="BA", ibge_code="2927408")

    # Projetos (fluxo='SUPER' para permitir testar diferentes status)
    proj1 = Projeto.objects.create(nome="Alfabetização Ceará", codigo="P001", fluxo="SUPER")
    proj2 = Projeto.objects.create(nome="Matemática", codigo="P002", fluxo="SUPER")
    proj3 = Projeto.objects.create(nome="Ciências", codigo="P003", fluxo="SUPER")

    # Tipos de evento
    tipo1 = TipoEvento.objects.create(nome="Formação Inicial")
    tipo2 = TipoEvento.objects.create(nome="Formação Continuada")

    return {
        "formadores": [formador1, formador2],
        "municipios": {"ce": mun_ce, "pe": mun_pe, "ba": mun_ba},
        "projetos": [proj1, proj2, proj3],
        "tipos": [tipo1, tipo2],
    }


@pytest.fixture
def solicitacoes_variedade(dados_basicos):
    """Criar solicitações com variedade de status, datas, projetos e UFs."""
    now = timezone.now()
    formador = dados_basicos["formadores"][0]
    # Criar um usuário coordenador para ser o criador das solicitações
    coordenador = Usuario.objects.create_user(
        username="coord_test", email="coord_test@x.com", password="x", cpf="88888888888"
    )

    solicitacoes = []

    # 3 aprovadas em CE, projeto Alfabetização, últimas 2 semanas
    for i in range(3):
        sol = Solicitacao.objects.create(
            usuario=coordenador,
            status="aprovado",
            inicio=now - timedelta(days=7),
            fim=now - timedelta(days=7) + timedelta(hours=2),
            municipio=dados_basicos["municipios"]["ce"],
            projeto=dados_basicos["projetos"][0],
            tipo_evento=dados_basicos["tipos"][0],
        )
        sol.formadores.add(formador)
        solicitacoes.append(sol)

    # 2 pendentes em PE, projeto Matemática, últimas 4 semanas (dentro do range de 30 dias)
    for i in range(2):
        sol = Solicitacao.objects.create(
            usuario=coordenador,
            status="pendente",
            inicio=now - timedelta(days=20),
            fim=now - timedelta(days=20) + timedelta(hours=3),
            municipio=dados_basicos["municipios"]["pe"],
            projeto=dados_basicos["projetos"][1],
            tipo_evento=dados_basicos["tipos"][1],
        )
        sol.formadores.add(formador)
        solicitacoes.append(sol)

    # 1 reprovada em BA, projeto Ciências (dentro do range de 30 dias)
    sol = Solicitacao.objects.create(
        usuario=coordenador,
        status="reprovado",
        inicio=now - timedelta(days=25),  # Mudei de 35 para 25 dias
        fim=now - timedelta(days=25) + timedelta(hours=1),
        municipio=dados_basicos["municipios"]["ba"],
        projeto=dados_basicos["projetos"][2],
        tipo_evento=dados_basicos["tipos"][0],
    )
    sol.formadores.add(formador)
    solicitacoes.append(sol)

    # 1 aprovada antiga (fora do range de 30 dias)
    sol = Solicitacao.objects.create(
        usuario=coordenador,
        status="aprovado",
        inicio=now - timedelta(days=60),
        fim=now - timedelta(days=60) + timedelta(hours=2),
        municipio=dados_basicos["municipios"]["ce"],
        projeto=dados_basicos["projetos"][0],
        tipo_evento=dados_basicos["tipos"][0],
    )
    sol.formadores.add(formador)
    solicitacoes.append(sol)

    return solicitacoes


# ============================================================================
# TESTES DE PERMISSÕES
# ============================================================================


def test_status_counts_requires_authentication(clear_cache):
    """Endpoint status-counts exige autenticação."""
    client = APIClient()
    url = reverse("core:reports-status-counts")
    res = client.get(url)

    # DRF retorna 403 quando a permission class rejeita
    assert res.status_code == 403, "Deve retornar 403 para não autenticado"


def test_status_counts_superintendencia_allowed(user_super, clear_cache):
    """Usuário do grupo Superintendência tem acesso."""
    client = APIClient()
    client.force_authenticate(user=user_super)

    url = reverse("core:reports-status-counts")
    res = client.get(url)

    assert res.status_code == 200, f"Superintendência deve ter acesso: {res.data}"


def test_status_counts_controle_allowed(user_controle, clear_cache):
    """Usuário do grupo Controle tem acesso."""
    client = APIClient()
    client.force_authenticate(user=user_controle)

    url = reverse("core:reports-status-counts")
    res = client.get(url)

    assert res.status_code == 200, f"Controle deve ter acesso: {res.data}"


def test_status_counts_dat_allowed(user_dat, clear_cache):
    """Usuário do grupo DAT tem acesso."""
    client = APIClient()
    client.force_authenticate(user=user_dat)

    url = reverse("core:reports-status-counts")
    res = client.get(url)

    assert res.status_code == 200, f"DAT deve ter acesso: {res.data}"


def test_status_counts_coordenador_forbidden(user_coordenador, clear_cache):
    """Usuário do grupo Coordenador NÃO tem acesso."""
    client = APIClient()
    client.force_authenticate(user=user_coordenador)

    url = reverse("core:reports-status-counts")
    res = client.get(url)

    assert res.status_code == 403, "Coordenador não deve ter acesso"


def test_status_counts_formador_forbidden(user_formador, clear_cache):
    """Usuário do grupo Formador NÃO tem acesso."""
    client = APIClient()
    client.force_authenticate(user=user_formador)

    url = reverse("core:reports-status-counts")
    res = client.get(url)

    assert res.status_code == 403, "Formador não deve ter acesso"


def test_superuser_always_has_access(clear_cache):
    """Superuser sempre tem acesso, mesmo sem grupo."""
    user = Usuario.objects.create_superuser(username="admin", email="admin@x.com", password="x", cpf="99999999999")
    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("core:reports-status-counts")
    res = client.get(url)

    assert res.status_code == 200, "Superuser deve ter acesso"


# ============================================================================
# TESTES DE STATUS-COUNTS
# ============================================================================


def test_status_counts_default_range(user_super, solicitacoes_variedade, clear_cache):
    """status-counts sem parâmetros retorna últimos 30 dias."""
    client = APIClient()
    client.force_authenticate(user=user_super)

    url = reverse("core:reports-status-counts")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    # Verificar estrutura padrão (#411 Response Consistency)
    assert "data" in data
    assert "meta" in data
    assert "range" in data["meta"]
    assert "counts" in data["data"]
    assert "total" in data["data"]

    # Verificar contagens (últimos 30 dias = 3 aprovadas + 2 pendentes + 1 reprovada = 6)
    assert data["data"]["counts"]["aprovado"] == 3
    assert data["data"]["counts"]["pendente"] == 2
    assert data["data"]["counts"]["reprovado"] == 1
    assert data["data"]["counts"]["publicado"] == 0  # Sempre 0 por enquanto
    assert data["data"]["total"] == 6


def test_status_counts_custom_range(user_super, solicitacoes_variedade, clear_cache):
    """status-counts com range customizado filtra corretamente."""
    client = APIClient()
    client.force_authenticate(user=user_super)

    now = timezone.now()
    start = (now - timedelta(days=10)).strftime("%Y-%m-%d")
    end = now.strftime("%Y-%m-%d")

    url = reverse("core:reports-status-counts")
    res = client.get(url, {"start": start, "end": end})

    assert res.status_code == 200
    data = res.json()

    # Últimos 10 dias = apenas as 3 aprovadas (#411 format)
    assert data["data"]["counts"]["aprovado"] == 3
    assert data["data"]["counts"]["pendente"] == 0
    assert data["data"]["counts"]["reprovado"] == 0
    assert data["data"]["total"] == 3


def test_status_counts_invalid_date_format(user_super, clear_cache):
    """status-counts com formato de data inválido retorna 400."""
    client = APIClient()
    client.force_authenticate(user=user_super)

    url = reverse("core:reports-status-counts")
    res = client.get(url, {"start": "invalid-date"})

    assert res.status_code == 400
    assert "detail" in res.json()


def test_status_counts_end_before_start(user_super, clear_cache):
    """status-counts com end < start retorna 400."""
    client = APIClient()
    client.force_authenticate(user=user_super)

    url = reverse("core:reports-status-counts")
    res = client.get(url, {"start": "2025-12-31", "end": "2025-01-01"})

    assert res.status_code == 400
    assert "detail" in res.json()


def test_status_counts_response_consistency(user_super, solicitacoes_variedade, clear_cache):
    """
    status-counts retorna respostas consistentes.

    Note: Cache foi removido em #411 (Response Consistency).
    Verifica que múltiplas chamadas retornam dados idênticos.
    """
    client = APIClient()
    client.force_authenticate(user=user_super)

    url = reverse("core:reports-status-counts")

    # Primeira chamada
    res1 = client.get(url)
    assert res1.status_code == 200
    data1 = res1.json()

    # Segunda chamada
    res2 = client.get(url)
    assert res2.status_code == 200
    data2 = res2.json()

    # #411: Data portion should be identical (timestamp may differ)
    assert data1["data"] == data2["data"]
    assert data1["meta"]["range"] == data2["meta"]["range"]


# ============================================================================
# TESTES DE TOP-PROJECTS
# ============================================================================


def test_top_projects_default_limit(user_super, solicitacoes_variedade, clear_cache):
    """top-projects sem parâmetros retorna top 5."""
    client = APIClient()
    client.force_authenticate(user=user_super)

    url = reverse("core:reports-top-projects")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    # #411 Response Consistency format
    assert "data" in data
    assert "meta" in data
    assert "range" in data["meta"]
    assert "items" in data["data"]
    assert isinstance(data["data"]["items"], list)


def test_top_projects_correct_ranking(user_super, solicitacoes_variedade, clear_cache):
    """top-projects ordena corretamente por contagem."""
    client = APIClient()
    client.force_authenticate(user=user_super)

    url = reverse("core:reports-top-projects")
    res = client.get(url, {"limit": 10})

    assert res.status_code == 200
    data = res.json()

    # #411 Response Consistency format
    items = data["data"]["items"]
    assert len(items) == 3  # Temos 3 projetos

    # Primeiro projeto deve ser Alfabetização (3 solicitações)
    assert items[0]["projeto"] == "Alfabetização Ceará"
    assert items[0]["count"] == 3

    # Segundo deve ser Matemática (2 solicitações)
    assert items[1]["projeto"] == "Matemática"
    assert items[1]["count"] == 2

    # Terceiro deve ser Ciências (1 solicitação)
    assert items[2]["projeto"] == "Ciências"
    assert items[2]["count"] == 1


def test_top_projects_limit_validation(user_super, clear_cache):
    """top-projects valida limit (1-20)."""
    client = APIClient()
    client.force_authenticate(user=user_super)

    url = reverse("core:reports-top-projects")

    # Limite muito baixo
    res = client.get(url, {"limit": 0})
    assert res.status_code == 400

    # Limite muito alto
    res = client.get(url, {"limit": 21})
    assert res.status_code == 400

    # Limites válidos
    res = client.get(url, {"limit": 1})
    assert res.status_code == 200

    res = client.get(url, {"limit": 20})
    assert res.status_code == 200


# ============================================================================
# TESTES DE WEEKLY-APPROVED
# ============================================================================


def test_weekly_approved_default_weeks(user_super, solicitacoes_variedade, clear_cache):
    """weekly-approved sem parâmetros retorna 12 semanas."""
    client = APIClient()
    client.force_authenticate(user=user_super)

    url = reverse("core:reports-weekly-approved")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    # #411 Response Consistency format
    assert "data" in data
    assert "meta" in data
    assert "weeks" in data["meta"]
    assert "items" in data["data"]
    assert data["meta"]["weeks"] == 12
    assert isinstance(data["data"]["items"], list)


def test_weekly_approved_only_approved_status(user_super, solicitacoes_variedade, clear_cache):
    """weekly-approved conta apenas solicitações com status='aprovado'."""
    client = APIClient()
    client.force_authenticate(user=user_super)

    url = reverse("core:reports-weekly-approved")
    res = client.get(url, {"weeks": 52})

    assert res.status_code == 200
    data = res.json()

    # Somar todas as contagens (#411 format: items instead of series)
    total_aprovadas = sum(item["count"] for item in data["data"]["items"])

    # Devemos ter 4 aprovadas no total (3 recentes + 1 antiga)
    assert total_aprovadas == 4


def test_weekly_approved_weeks_validation(user_super, clear_cache):
    """weekly-approved valida weeks (1-52)."""
    client = APIClient()
    client.force_authenticate(user=user_super)

    url = reverse("core:reports-weekly-approved")

    # Semanas muito baixas
    res = client.get(url, {"weeks": 0})
    assert res.status_code == 400

    # Semanas muito altas
    res = client.get(url, {"weeks": 53})
    assert res.status_code == 400

    # Semanas válidas
    res = client.get(url, {"weeks": 1})
    assert res.status_code == 200

    res = client.get(url, {"weeks": 52})
    assert res.status_code == 200


# ============================================================================
# TESTES DE BY-UF
# ============================================================================


def test_by_uf_groups_by_state(user_super, solicitacoes_variedade, clear_cache):
    """by-uf agrupa corretamente por UF."""
    client = APIClient()
    client.force_authenticate(user=user_super)

    url = reverse("core:reports-by-uf")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    # #411 Response Consistency format
    assert "data" in data
    assert "meta" in data
    assert "range" in data["meta"]
    assert "items" in data["data"]
    assert isinstance(data["data"]["items"], list)

    # Converter para dict para facilitar verificação
    uf_counts = {item["uf"]: item["count"] for item in data["data"]["items"]}

    # Últimos 30 dias: 3 em CE, 2 em PE, 1 em BA
    assert uf_counts.get("CE", 0) == 3
    assert uf_counts.get("PE", 0) == 2
    assert uf_counts.get("BA", 0) == 1


def test_by_uf_orders_by_count_desc(user_super, solicitacoes_variedade, clear_cache):
    """by-uf ordena por contagem decrescente."""
    client = APIClient()
    client.force_authenticate(user=user_super)

    url = reverse("core:reports-by-uf")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    # #411 Response Consistency format
    items = data["data"]["items"]

    # Primeira UF deve ser CE (maior contagem)
    assert items[0]["uf"] == "CE"
    assert items[0]["count"] == 3

    # Contagens devem estar em ordem decrescente
    for i in range(len(items) - 1):
        assert items[i]["count"] >= items[i + 1]["count"]


def test_by_uf_ignores_null_municipio(user_super, dados_basicos, clear_cache):
    """by-uf ignora solicitações sem município."""
    # Criar solicitação sem município
    formador = dados_basicos["formadores"][0]
    proj = dados_basicos["projetos"][0]
    tipo = dados_basicos["tipos"][0]

    # Criar um usuário para a solicitação
    coord = Usuario.objects.create_user(username="coord_mun", email="coord_mun@x.com", password="x", cpf="99888777666")

    sol = Solicitacao.objects.create(
        usuario=coord,
        status="aprovado",
        inicio=timezone.now(),
        fim=timezone.now() + timedelta(hours=2),
        municipio=None,  # Sem município
        projeto=proj,
        tipo_evento=tipo,
    )
    sol.formadores.add(formador)

    client = APIClient()
    client.force_authenticate(user=user_super)

    url = reverse("core:reports-by-uf")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    # "N/A" não deve aparecer na lista (#411 format)
    ufs = [item["uf"] for item in data["data"]["items"]]
    assert "N/A" not in ufs


# ============================================================================
# TESTES DE EDGE CASES
# ============================================================================


def test_status_counts_empty_database(user_super, clear_cache):
    """status-counts com banco vazio retorna contagens zero."""
    client = APIClient()
    client.force_authenticate(user=user_super)

    url = reverse("core:reports-status-counts")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    # #411 Response Consistency format
    assert data["data"]["counts"]["pendente"] == 0
    assert data["data"]["counts"]["aprovado"] == 0
    assert data["data"]["counts"]["reprovado"] == 0
    assert data["data"]["counts"]["publicado"] == 0
    assert data["data"]["total"] == 0


def test_top_projects_empty_database(user_super, clear_cache):
    """top-projects com banco vazio retorna lista vazia."""
    client = APIClient()
    client.force_authenticate(user=user_super)

    url = reverse("core:reports-top-projects")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    # #411 Response Consistency format
    assert data["data"]["items"] == []


def test_weekly_approved_empty_database(user_super, clear_cache):
    """weekly-approved com banco vazio retorna série vazia."""
    client = APIClient()
    client.force_authenticate(user=user_super)

    url = reverse("core:reports-weekly-approved")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    # #411 Response Consistency format (items instead of series)
    assert data["data"]["items"] == []


def test_by_uf_empty_database(user_super, clear_cache):
    """by-uf com banco vazio retorna lista vazia."""
    client = APIClient()
    client.force_authenticate(user=user_super)

    url = reverse("core:reports-by-uf")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    # #411 Response Consistency format
    assert data["data"]["items"] == []

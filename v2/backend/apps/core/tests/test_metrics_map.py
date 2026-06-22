"""
Testes para endpoint de métricas do mapa (PR 11/N).

Cobertura:
- Permissões (HasPerm("view_map_metrics"))
- Validação de parâmetros
- Agregação correta por UF
- Filtros (status + projeto_id)
- Caso zero-state

Endpoint testado:
- GET /api/metrics/map/
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import Compra, Participation, Produto
from apps.core.tests.factories import (
    GroupFactory,
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def grupos():
    """Criar grupos necessários para os testes."""
    return {
        "diretoria": GroupFactory(name="Diretoria"),
        "controle": GroupFactory(name="Controle"),
        "dat": GroupFactory(name="DAT"),
        "superintendencia": GroupFactory(name="Superintendência"),
        "coordenador": GroupFactory(name="Coordenador"),
        "formador": GroupFactory(name="Formador"),
    }


@pytest.fixture
def user_diretoria(grupos):
    """Issue #1222 (Epic 1): Diretoria tem `view_map_metrics` no seed realinhado."""
    user = UsuarioFactory(username="diretoria1", email="dir@x.com", password="x", cpf="99999999991")
    user.groups.add(grupos["diretoria"])
    return user


@pytest.fixture
def user_controle(grupos):
    """Usuário do grupo Controle (sem view_map_metrics no seed realinhado)."""
    user = UsuarioFactory(username="controle1", email="controle@x.com", password="x", cpf="11111111111")
    user.groups.add(grupos["controle"])
    return user


@pytest.fixture
def user_dat(grupos):
    """Usuário do grupo DAT."""
    user = UsuarioFactory(username="dat1", email="dat@x.com", password="x", cpf="22222222222")
    user.groups.add(grupos["dat"])
    return user


@pytest.fixture
def user_coordenador(grupos):
    """Usuário do grupo Coordenador (sem permissão)."""
    user = UsuarioFactory(username="coord1", email="coord@x.com", password="x", cpf="33333333333")
    user.groups.add(grupos["coordenador"])
    return user


@pytest.fixture
def user_formador(grupos):
    """Usuário do grupo Formador (sem permissão)."""
    user = UsuarioFactory(username="form1", email="form@x.com", password="x", cpf="44444444444")
    user.groups.add(grupos["formador"])
    return user


@pytest.fixture
def dados_basicos(grupos):
    """Criar dados básicos para os testes."""
    # Formadores (usuários)
    formador1 = UsuarioFactory(username="ana.silva", email="ana@x.com", password="x", cpf="55555555555")
    formador1.groups.add(grupos["formador"])

    # Municípios (3 UFs diferentes) com coordenadas para testes
    mun_ce = MunicipioFactory(nome="Fortaleza", uf="CE", ibge_code="2304400", latitude=-3.717200, longitude=-38.543400)
    mun_sp = MunicipioFactory(nome="São Paulo", uf="SP", ibge_code="3550308", latitude=-23.550520, longitude=-46.633308)
    mun_ba = MunicipioFactory(nome="Salvador", uf="BA", ibge_code="2927408", latitude=-12.971400, longitude=-38.510800)

    # Projetos (fluxo='SUPER' para permitir testar diferentes status)
    proj1 = ProjetoFactory(nome="Vida & Matemática", codigo="P001", fluxo="SUPER")
    proj2 = ProjetoFactory(nome="TEMA", codigo="P002", fluxo="SUPER")

    # Tipos de evento
    tipo1 = TipoEventoFactory(nome="Formação Inicial")

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
    coordenador = UsuarioFactory(username="coord_test", email="coord_test@x.com", password="x", cpf="88888888888")

    solicitacoes = []

    # 3 aprovadas em CE, projeto Matemática
    for i in range(3):
        sol = SolicitacaoFactory(
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
        sol = SolicitacaoFactory(
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
    sol = SolicitacaoFactory(
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


def test_map_metrics_diretoria_allowed(user_diretoria):
    """Issue #1222 (Epic 1): Diretoria tem view_map_metrics no seed realinhado."""
    client = APIClient()
    client.force_authenticate(user=user_diretoria)

    url = reverse("core:metrics-map")
    res = client.get(url)

    assert res.status_code == 200, f"Diretoria deve ter acesso: {res.data}"


def test_map_metrics_controle_forbidden(user_controle):
    """Issue #1222 (Epic 1): Controle não tem view_map_metrics no seed realinhado."""
    client = APIClient()
    client.force_authenticate(user=user_controle)

    url = reverse("core:metrics-map")
    res = client.get(url)

    assert res.status_code == 403


def test_map_metrics_dat_forbidden(user_dat):
    """Issue #1222 (Epic 1): DAT não tem view_map_metrics no seed realinhado."""
    client = APIClient()
    client.force_authenticate(user=user_dat)

    url = reverse("core:metrics-map")
    res = client.get(url)

    assert res.status_code == 403


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
    user = UsuarioFactory(superuser=True)
    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("core:metrics-map")
    res = client.get(url)

    assert res.status_code == 200, "Superuser deve ter acesso"


# ============================================================================
# TESTES DE ESTRUTURA DA RESPOSTA
# ============================================================================


def test_map_metrics_response_structure(user_diretoria, solicitacoes_variedade):
    """Resposta tem estrutura esperada com by_municipio e by_uf."""
    client = APIClient()
    client.force_authenticate(user=user_diretoria)

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
    assert "compras" in data["totals"]

    # Verificar by_uf
    assert "by_uf" in data
    assert isinstance(data["by_uf"], list)
    if len(data["by_uf"]) > 0:
        uf_item = data["by_uf"][0]
        assert "uf" in uf_item
        assert "eventos" in uf_item
        assert "projetos" in uf_item
        assert "municipios" in uf_item
        assert "coordenadores" in uf_item
        assert "compras" in uf_item

    # Verificar by_municipio (não mais by_uf)
    assert "by_municipio" in data
    assert isinstance(data["by_municipio"], list)

    # Verificar estrutura de cada município
    if len(data["by_municipio"]) > 0:
        mun = data["by_municipio"][0]
        assert "municipio" in mun
        assert "uf" in mun
        assert "latitude" in mun
        assert "longitude" in mun
        assert "projetos" in mun
        assert "eventos" in mun
        assert "coordenadores" in mun
        assert "compras" in mun

    # Verificar top_projetos
    assert "top_projetos" in data
    assert isinstance(data["top_projetos"], list)


# ============================================================================
# TESTES DE AGREGAÇÃO POR MUNICÍPIO
# ============================================================================


def test_map_metrics_by_municipio_aggregation(user_diretoria, solicitacoes_variedade):
    """Agregação por município está correta."""
    client = APIClient()
    client.force_authenticate(user=user_diretoria)

    url = reverse("core:metrics-map")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    # Converter by_municipio para dict para facilitar verificação
    by_mun_dict = {f"{item['municipio']}-{item['uf']}": item["eventos"] for item in data["by_municipio"]}

    # Verificar contagens (3 CE + 2 SP + 1 BA = 6 total)
    assert by_mun_dict.get("Fortaleza-CE", 0) == 3
    assert by_mun_dict.get("São Paulo-SP", 0) == 2
    assert by_mun_dict.get("Salvador-BA", 0) == 1
    assert data["totals"]["all"] == 6

    # Verificar que municípios têm coordenadas
    for mun in data["by_municipio"]:
        assert mun["latitude"] is not None
        assert mun["longitude"] is not None


def test_map_metrics_by_municipio_ordered_descending(user_diretoria, solicitacoes_variedade):
    """Municípios ordenados por eventos decrescente."""
    client = APIClient()
    client.force_authenticate(user=user_diretoria)

    url = reverse("core:metrics-map")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    by_municipio = data["by_municipio"]

    # Primeiro município deve ser Fortaleza (maior contagem = 3 eventos)
    assert by_municipio[0]["municipio"] == "Fortaleza"
    assert by_municipio[0]["uf"] == "CE"
    assert by_municipio[0]["eventos"] == 3

    # Eventos devem estar em ordem decrescente
    for i in range(len(by_municipio) - 1):
        assert by_municipio[i]["eventos"] >= by_municipio[i + 1]["eventos"]


def test_map_metrics_coordenadores_homonimos_nao_colidem_por_nome(user_diretoria):
    """Municípios homônimos em UFs diferentes não devem compartilhar contagem de coordenadores."""
    client = APIClient()
    client.force_authenticate(user=user_diretoria)

    projeto = ProjetoFactory(nome="Projeto Homônimos", codigo="PH01", fluxo="SUPER")
    tipo = TipoEventoFactory(nome="Tipo Homônimos")

    municipio_ce = MunicipioFactory(
        nome="Santa Maria",
        uf="CE",
        ibge_code="2300001",
        latitude=-3.12,
        longitude=-39.10,
    )
    municipio_sp = MunicipioFactory(
        nome="Santa Maria",
        uf="SP",
        ibge_code="3500001",
        latitude=-22.10,
        longitude=-47.10,
    )

    criador = UsuarioFactory(
        username="criador_homonimo",
        email="criador_homonimo@test.com",
        password="x",
        cpf="10101010101",
    )
    coord_ce = UsuarioFactory(username="coord_ce", email="coord_ce@test.com", password="x", cpf="20202020202")
    coord_sp = UsuarioFactory(username="coord_sp", email="coord_sp@test.com", password="x", cpf="30303030303")

    now = timezone.now()
    sol_ce = SolicitacaoFactory(
        usuario=criador,
        status="aprovado",
        inicio=now,
        fim=now + timedelta(hours=2),
        municipio=municipio_ce,
        projeto=projeto,
        tipo_evento=tipo,
    )
    sol_sp = SolicitacaoFactory(
        usuario=criador,
        status="aprovado",
        inicio=now + timedelta(days=1),
        fim=now + timedelta(days=1, hours=2),
        municipio=municipio_sp,
        projeto=projeto,
        tipo_evento=tipo,
    )

    Participation.objects.create(solicitacao=sol_ce, usuario=coord_ce, role=Participation.Role.COORDENADOR)
    Participation.objects.create(solicitacao=sol_sp, usuario=coord_sp, role=Participation.Role.COORDENADOR)

    url = reverse("core:metrics-map")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()
    by_mun = {f"{m['municipio']}-{m['uf']}": m for m in data["by_municipio"]}

    assert by_mun["Santa Maria-CE"]["coordenadores"] == 1
    assert by_mun["Santa Maria-SP"]["coordenadores"] == 1


def test_map_metrics_eventos_e_compras_separados_no_payload(user_diretoria):
    """Métrica de eventos não deve ser contaminada por compras."""
    client = APIClient()
    client.force_authenticate(user=user_diretoria)

    projeto = ProjetoFactory(nome="Projeto Compras", codigo="PC01", fluxo="SUPER")
    tipo = TipoEventoFactory(nome="Tipo Compras")
    municipio = MunicipioFactory(
        nome="Maracanaú",
        uf="CE",
        ibge_code="2307650",
        latitude=-3.88,
        longitude=-38.62,
    )

    criador = UsuarioFactory(
        username="criador_compra", email="criador_compra@test.com", password="x", cpf="40404040404"
    )
    now = timezone.now()
    SolicitacaoFactory(
        usuario=criador,
        status="aprovado",
        inicio=now,
        fim=now + timedelta(hours=2),
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo,
    )

    produto_model = Produto.objects.create(nome="Kit Didático", codigo="KIT01", projeto=projeto)
    Compra.objects.create(
        codigo="COMP-001",
        produto=produto_model,
        projeto=projeto,
        municipio=municipio,
        quantidade=10,
        data=timezone.localdate(),
        uso="Uso 1",
        external_hash="hash_compra_001",
    )
    Compra.objects.create(
        codigo="COMP-002",
        produto=produto_model,
        projeto=projeto,
        municipio=municipio,
        quantidade=20,
        data=timezone.localdate(),
        uso="Uso 2",
        external_hash="hash_compra_002",
    )

    url = reverse("core:metrics-map")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    assert data["totals"]["all"] == 1
    assert data["totals"]["compras"] == 2

    by_uf = next(item for item in data["by_uf"] if item["uf"] == "CE")
    assert by_uf["eventos"] == 1
    assert by_uf["compras"] == 2

    by_mun = next(item for item in data["by_municipio"] if item["municipio"] == "Maracanaú")
    assert by_mun["eventos"] == 1
    assert by_mun["compras"] == 2


# ============================================================================
# TESTES DE FILTROS
# ============================================================================


def test_map_metrics_filter_by_status(user_diretoria, solicitacoes_variedade):
    """Filtro por status funciona corretamente."""
    client = APIClient()
    client.force_authenticate(user=user_diretoria)

    url = reverse("core:metrics-map")

    # Filtrar por aprovado (3 solicitações)
    res = client.get(url, {"status": "aprovado"})
    assert res.status_code == 200
    data = res.json()

    assert data["totals"]["all"] == 3
    assert data["meta"]["filters"]["status"] == "aprovado"

    # Deve ter apenas Fortaleza-CE (3 aprovadas estão em CE)
    by_mun_list = [f"{m['municipio']}-{m['uf']}" for m in data["by_municipio"]]
    assert "Fortaleza-CE" in by_mun_list
    assert "São Paulo-SP" not in by_mun_list
    assert "Salvador-BA" not in by_mun_list

    # Verificar que retornou exatamente 1 município
    assert len(data["by_municipio"]) == 1
    assert data["by_municipio"][0]["eventos"] == 3


def test_map_metrics_filter_by_projeto(user_diretoria, solicitacoes_variedade, dados_basicos):
    """Filtro por projeto_id funciona corretamente."""
    client = APIClient()
    client.force_authenticate(user=user_diretoria)

    url = reverse("core:metrics-map")
    projeto_matematica_id = dados_basicos["projetos"]["matematica"].id

    # Filtrar por projeto Matemática (4 solicitações: 3 CE + 1 BA)
    res = client.get(url, {"projeto_id": projeto_matematica_id})
    assert res.status_code == 200
    data = res.json()

    assert data["totals"]["all"] == 4
    assert data["meta"]["filters"]["projeto_id"] == projeto_matematica_id

    # Deve ter Fortaleza-CE (3) e Salvador-BA (1)
    by_mun_dict = {f"{m['municipio']}-{m['uf']}": m["eventos"] for m in data["by_municipio"]}
    assert by_mun_dict.get("Fortaleza-CE", 0) == 3
    assert by_mun_dict.get("Salvador-BA", 0) == 1
    assert "São Paulo-SP" not in by_mun_dict

    # Verificar que retornou 2 municípios
    assert len(data["by_municipio"]) == 2


def test_map_metrics_filter_combined(user_diretoria, solicitacoes_variedade, dados_basicos):
    """Filtros combinados (status + projeto_id) funcionam corretamente."""
    client = APIClient()
    client.force_authenticate(user=user_diretoria)

    url = reverse("core:metrics-map")
    projeto_matematica_id = dados_basicos["projetos"]["matematica"].id

    # Filtrar por aprovado + Matemática (3 solicitações em CE)
    res = client.get(url, {"status": "aprovado", "projeto_id": projeto_matematica_id})
    assert res.status_code == 200
    data = res.json()

    assert data["totals"]["all"] == 3
    assert data["meta"]["filters"]["status"] == "aprovado"
    assert data["meta"]["filters"]["projeto_id"] == projeto_matematica_id

    # Apenas Fortaleza-CE
    assert len(data["by_municipio"]) == 1
    assert data["by_municipio"][0]["municipio"] == "Fortaleza"
    assert data["by_municipio"][0]["uf"] == "CE"
    assert data["by_municipio"][0]["eventos"] == 3


def test_map_metrics_filter_by_date_range(user_diretoria, solicitacoes_variedade):
    """Filtro por data_inicio/data_fim deve alterar resultado de forma verificável."""
    client = APIClient()
    client.force_authenticate(user=user_diretoria)

    url = reverse("core:metrics-map")
    today = timezone.localdate()

    # Janela que deve capturar somente as 2 solicitações de São Paulo (+10 e +11 dias).
    res = client.get(
        url,
        {
            "data_inicio": (today + timedelta(days=9)).isoformat(),
            "data_fim": (today + timedelta(days=11)).isoformat(),
        },
    )
    assert res.status_code == 200
    data = res.json()

    assert data["meta"]["filters"]["data_inicio"] == (today + timedelta(days=9)).isoformat()
    assert data["meta"]["filters"]["data_fim"] == (today + timedelta(days=11)).isoformat()
    assert data["totals"]["all"] == 2
    assert len(data["by_municipio"]) == 1
    assert data["by_municipio"][0]["municipio"] == "São Paulo"
    assert data["by_municipio"][0]["uf"] == "SP"
    assert data["by_municipio"][0]["eventos"] == 2


# ============================================================================
# TESTES DE VALIDAÇÃO
# ============================================================================


def test_map_metrics_invalid_status(user_diretoria):
    """Status inválido retorna 400."""
    client = APIClient()
    client.force_authenticate(user=user_diretoria)

    url = reverse("core:metrics-map")
    res = client.get(url, {"status": "invalido"})

    assert res.status_code == 400
    assert "detail" in res.json()


def test_map_metrics_invalid_projeto_id(user_diretoria):
    """projeto_id não numérico retorna 400."""
    client = APIClient()
    client.force_authenticate(user=user_diretoria)

    url = reverse("core:metrics-map")
    res = client.get(url, {"projeto_id": "nao-numero"})

    assert res.status_code == 400
    assert "detail" in res.json()


def test_map_metrics_invalid_data_inicio(user_diretoria):
    """data_inicio inválida retorna 400."""
    client = APIClient()
    client.force_authenticate(user=user_diretoria)

    url = reverse("core:metrics-map")
    res = client.get(url, {"data_inicio": "2026/01/01"})

    assert res.status_code == 400
    assert "detail" in res.json()


def test_map_metrics_invalid_date_range(user_diretoria):
    """data_inicio > data_fim retorna 400."""
    client = APIClient()
    client.force_authenticate(user=user_diretoria)

    url = reverse("core:metrics-map")
    res = client.get(url, {"data_inicio": "2026-02-10", "data_fim": "2026-02-01"})

    assert res.status_code == 400
    assert "detail" in res.json()


def test_map_metrics_invalid_limit(user_diretoria):
    """limit inválido retorna 400."""
    client = APIClient()
    client.force_authenticate(user=user_diretoria)

    url = reverse("core:metrics-map")
    res = client.get(url, {"limit": "invalido"})

    assert res.status_code == 400
    assert "detail" in res.json()


# ============================================================================
# TESTES DE CASO ZERO-STATE
# ============================================================================


def test_map_metrics_empty_database(user_diretoria):
    """Com banco vazio, retorna arrays vazios e counts = 0."""
    client = APIClient()
    client.force_authenticate(user=user_diretoria)

    url = reverse("core:metrics-map")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    assert data["totals"]["all"] == 0
    assert data["totals"]["compras"] == 0
    assert data["by_uf"] == []
    assert data["by_municipio"] == []
    assert data["top_projetos"] == []


# ============================================================================
# TESTES DE TOP PROJETOS
# ============================================================================


def test_map_metrics_top_projetos(user_diretoria, solicitacoes_variedade, dados_basicos):
    """Top projetos ordenados por contagem."""
    client = APIClient()
    client.force_authenticate(user=user_diretoria)

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

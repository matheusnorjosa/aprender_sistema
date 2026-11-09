"""
#2036, PR 3 — evento de dois projetos: as leituras.

Decisões do dono (08/11/2026): não há projeto principal. Busca e filtro acham o evento pelos dois projetos,
uma vez só; a contagem por projeto conta o evento nos dois, e os totais (eventos, gerência, fluxo) contam
uma vez; o rótulo é "A + B". Regra da compra: o evento só sai sem a marca "sem compra" com os DOIS projetos
cobertos (cada um pela compra própria, da coleção ou de nome geral, ou por uma compra `COMBOS` que cubra os
dois); NULL nunca casa. A pendência de Compras de um projeto fecha com o evento combo que o contém.
Helpers em `services/solicitacao_projetos.py`. O poder (escopo, aprovação) segue lendo `projeto`.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import Gerencia, Participation, Projeto, ProjetoGeral, Solicitacao
from apps.core.services.compra_elegibilidade import solicitacoes_com_par_liberado
from apps.core.services.gcal_sync_service import build_event_payload
from apps.core.services.lgpd_export_service import build_lgpd_export_data
from apps.core.services.monthly_grid_service import build_monthly_grid
from apps.core.tests.factories import (
    GerenciaFactory,
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
    com_papel,
    liberar_par,
)

pytestmark = pytest.mark.django_db

FORTALEZA = ZoneInfo("America/Fortaleza")
ROTULO = "Cataventos Teste + Uni Duni Teste"


@pytest.fixture
def gerencia() -> Gerencia:
    return GerenciaFactory()


@pytest.fixture
def par(gerencia) -> tuple[Projeto, Projeto]:
    """Dois projetos SUPER da mesma gerência (par válido). Vaga 1 = Uni Duni; vaga 2 = Cataventos."""
    return (
        ProjetoFactory(nome="Uni Duni Teste", codigo="UDT", gerencia=gerencia, super=True),
        ProjetoFactory(nome="Cataventos Teste", codigo="CTV", gerencia=gerencia, super=True),
    )


@pytest.fixture
def admin() -> APIClient:
    client = APIClient()
    client.force_authenticate(user=UsuarioFactory(superuser=True))
    return client


@pytest.fixture
def combo(par) -> Solicitacao:
    a, b = par
    return SolicitacaoFactory(
        projeto=a,
        projeto_2=b,
        status="aprovado",
        municipio=MunicipioFactory(nome="Vila Combo", uf="PE"),
        inicio=timezone.now() - timedelta(days=1),
        fim=timezone.now() - timedelta(days=1) + timedelta(hours=2),
    )


def _ids(resp) -> list[int]:
    data = resp.json()
    linhas = data["results"] if isinstance(data, dict) and "results" in data else data
    return [linha["id"] for linha in linhas]


# =============================================================================
# Rótulo e projetos[] nos serializers
# =============================================================================


def test_solicitacao_combo_expoe_rotulo_projeto_2_e_projetos(admin, par, combo):
    a, b = par

    data = admin.get(f"/api/solicitacoes/{combo.pk}/").json()

    assert data["projeto_nome"] == ROTULO
    assert data["projeto"] == a.pk
    assert data["projeto_2"] == b.pk
    assert data["projetos"] == [{"id": a.pk, "nome": a.nome}, {"id": b.pk, "nome": b.nome}]


def test_solicitacao_de_projeto_unico_fica_igual(admin, par):
    a, _ = par
    s = SolicitacaoFactory(projeto=a)

    data = admin.get(f"/api/solicitacoes/{s.pk}/").json()

    assert data["projeto_nome"] == a.nome
    assert data["projeto_2"] is None
    assert data["projetos"] == [{"id": a.pk, "nome": a.nome}]


def test_projeto_2_nao_se_grava_por_este_pr(admin, par):
    """A escrita do 2º projeto é do PR 4 (regra 2, reaprovação, compra): aqui ele só se lê."""
    a, b = par
    s = SolicitacaoFactory(projeto=a, usuario=UsuarioFactory())

    admin.patch(f"/api/solicitacoes/{s.pk}/", {"projeto_2": b.pk}, format="json")

    s.refresh_from_db()
    assert s.projeto_2_id is None


def test_detalhe_gcal_e_meus_eventos_usam_o_rotulo(admin, par, combo):
    pessoa = UsuarioFactory()
    Participation.objects.create(solicitacao=combo, usuario=pessoa, role="FORMADOR")

    detalhe = admin.get(f"/api/gcal/dashboard/events/{combo.pk}/detail/").json()
    meus = APIClient()
    meus.force_authenticate(user=pessoa)
    linha = next(e for e in meus.get("/api/me/events/").json()["results"] if e["id"] == combo.pk)

    assert detalhe["projeto_nome"] == ROTULO
    assert linha["projeto_nome"] == ROTULO


def test_csv_do_painel_do_google_usa_o_rotulo(admin, combo):
    resp = admin.get("/api/gcal/dashboard/events/export/", {"export_format": "csv"})

    assert ROTULO in resp.content.decode("utf-8-sig")


def test_resumo_de_erros_do_google_usa_o_rotulo(admin, combo):
    Solicitacao.objects.filter(pk=combo.pk).update(gcal_status=Solicitacao.GCalStatus.ERROR)

    data = admin.get("/api/gcal/dashboard/metrics/").json()
    erros = data.get("data", data)["recent_errors"]

    assert [e["summary"] for e in erros] == [f"Vila Combo - PE {ROTULO}"]


def test_drift_do_google_acha_pelo_2o_e_usa_o_rotulo(admin, combo):
    Solicitacao.objects.filter(pk=combo.pk).update(
        gcal_status=Solicitacao.GCalStatus.PUBLISHED, gcal_payload_hash="velho"
    )

    por_setor = admin.get("/api/gcal/drift/", {"sector": "Catav"}).json()
    por_busca = admin.get("/api/gcal/drift/", {"q": "Catav"}).json()

    assert [i["id"] for i in por_setor["items"]] == [combo.pk]
    assert [i["id"] for i in por_busca["items"]] == [combo.pk]
    assert por_setor["items"][0]["projeto"] == ROTULO


def test_lgpd_export_leva_o_2o_projeto(par):
    a, b = par
    titular = UsuarioFactory()
    SolicitacaoFactory(usuario=titular, projeto=a, projeto_2=b)

    linha = build_lgpd_export_data(titular, include_audit=False)["solicitations_created"][0]

    assert linha["projeto__nome"] == a.nome
    assert linha["projeto_2__nome"] == b.nome


# =============================================================================
# Busca e filtros: acham pelo 2º, uma vez só (sem quebrar paginação)
# =============================================================================


def test_busca_da_lista_de_solicitacoes_acha_pelo_2o_uma_vez(admin, combo):
    SolicitacaoFactory(projeto=ProjetoFactory(nome="Sem Relacao"))

    resp = admin.get("/api/solicitacoes/", {"q": "Catav"})

    assert _ids(resp) == [combo.pk]


def test_lista_do_google_filtra_setor_e_busca_pelo_2o_uma_vez(admin, combo):
    SolicitacaoFactory(projeto=ProjetoFactory(nome="Sem Relacao"), status="aprovado")

    por_setor = admin.get("/api/gcal/list/", {"sector": "Catav"})
    por_busca = admin.get("/api/gcal/list/", {"q": "Catav"})

    assert _ids(por_setor) == [combo.pk]
    assert _ids(por_busca) == [combo.pk]
    assert por_setor.json()["count"] == 1


def test_grade_mensal_filtra_pelo_2o_projeto(par):
    a, b = par
    pessoa = UsuarioFactory()
    s = SolicitacaoFactory(
        projeto=a,
        projeto_2=b,
        status="aprovado",
        inicio=datetime(2026, 3, 10, 8, tzinfo=FORTALEZA),
        fim=datetime(2026, 3, 10, 12, tzinfo=FORTALEZA),
    )
    Participation.objects.create(solicitacao=s, usuario=pessoa, role="FORMADOR")

    def dia_10(setor: str) -> str:
        """O código da célula do dia 10 (o filtro `sector` marca o dia; a CH não segue o filtro)."""
        grade = build_monthly_grid(year=2026, month=3, role="FORMADOR", sector=setor)
        linha = next(i for i, p in enumerate(grade["people"]) if p["id"] == pessoa.pk)
        return grade["cells"][linha][9]

    assert dia_10(b.nome) == "E"
    assert dia_10(a.nome) == "E"
    assert dia_10("Outro Projeto") == ""


def test_mapa_filtra_pelo_2o_projeto(admin, par, combo):
    _, b = par

    data = admin.get("/api/metrics/map/", {"projeto_id": b.pk}).json()

    assert data["totals"]["all"] == 1


# =============================================================================
# Contagem por projeto (conta nos dois) x totais (contam uma vez)
# =============================================================================


def test_mapa_top_projetos_conta_nos_dois_e_totais_uma_vez(admin, par, combo):
    a, b = par
    SolicitacaoFactory(projeto=a, status="aprovado", municipio=combo.municipio)

    data = admin.get("/api/metrics/map/").json()

    assert data["totals"]["all"] == 2
    assert data["top_projetos"] == [{"nome": a.nome, "count": 2}, {"nome": b.nome, "count": 1}]
    uf = next(u for u in data["by_uf"] if u["uf"] == "PE")
    assert (uf["eventos"], uf["projetos"]) == (2, 2)


def test_mapa_projetos_distintos_por_municipio_une_as_duas_vagas(admin, par, combo):
    """B está na vaga 2 do combo e na vaga 1 do outro evento: a união dá 2 ({A, B}); a soma por vaga daria 3."""
    _, b = par
    combo.municipio.latitude, combo.municipio.longitude = -8.0, -35.0
    combo.municipio.save()
    SolicitacaoFactory(projeto=b, municipio=combo.municipio)

    data = admin.get("/api/metrics/map/").json()

    linha = next(m for m in data["by_municipio"] if m["municipio"] == "Vila Combo")
    assert (linha["eventos"], linha["projetos"]) == (2, 2)
    uf = next(u for u in data["by_uf"] if u["uf"] == "PE")
    assert (uf["eventos"], uf["projetos"]) == (2, 2)


def test_mapa_filtrado_por_projeto_conta_so_o_projeto_filtrado(admin, par, combo):
    """Com `projeto_id=A`, o combo entra no filtro, mas o parceiro B não aparece nas contagens por projeto
    (top, coordenadores) e "projetos distintos" conta só A. Sem o filtro, o combo conta nos dois."""
    a, b = par
    combo.municipio.latitude, combo.municipio.longitude = -8.0, -35.0
    combo.municipio.save()
    SolicitacaoFactory(projeto=b, municipio=combo.municipio)

    data = admin.get("/api/metrics/map/", {"projeto_id": a.pk}).json()
    coords = admin.get("/api/metrics/map/coordinators/", {"uf": "PE", "projeto_id": a.pk}).json()

    assert data["totals"]["all"] == 1
    assert data["top_projetos"] == [{"nome": a.nome, "count": 1}]
    linha = next(m for m in data["by_municipio"] if m["municipio"] == "Vila Combo")
    assert (linha["eventos"], linha["projetos"]) == (1, 1)
    uf = next(u for u in data["by_uf"] if u["uf"] == "PE")
    assert (uf["eventos"], uf["projetos"]) == (1, 1)
    (coord,) = coords["coordenadores"]
    assert [(p["nome"], p["eventos"]) for p in coord["projetos"]] == [(a.nome, 1)]


def test_mapa_coordenadores_conta_o_evento_nos_dois_projetos(admin, par, combo):
    a, b = par

    data = admin.get("/api/metrics/map/coordinators/", {"uf": "PE"}).json()

    (coord,) = data["coordenadores"]
    assert coord["eventos"] == 1
    assert sorted((p["nome"], p["eventos"]) for p in coord["projetos"]) == [(b.nome, 1), (a.nome, 1)]


def test_relatorio_top_projetos_conta_nos_dois(admin, par, combo):
    a, b = par

    data = admin.get("/api/reports/top-projects/").json()

    itens = data["data"]["items"] if "data" in data else data["items"]
    assert sorted((i["projeto"], i["count"]) for i in itens) == [(b.nome, 1), (a.nome, 1)]


def test_insights_do_google_conta_nos_dois_sem_balde_vazio(admin, par, combo):
    a, b = par
    Solicitacao.objects.filter(pk=combo.pk).update(gcal_status=Solicitacao.GCalStatus.ERROR)
    SolicitacaoFactory(projeto=a, status="aprovado", gcal_status=Solicitacao.GCalStatus.PUBLISHED)

    itens = admin.get("/api/gcal/dashboard/insights/top/", {"metric": "projetos", "limit": 5}).json()["items"]

    assert [(i["name"], i["count"], i["published"], i["error"]) for i in itens] == [
        (a.nome, 2, 1, 1),
        (b.nome, 1, 0, 1),
    ]


def test_painel_geral_conta_o_combo_uma_vez_por_fluxo_e_gerencia(admin, combo):
    data = admin.get("/api/dashboard/overview/").json()
    corpo = data.get("data", data)

    assert corpo["kpis"]["eventos_aprovados"] == 1
    assert [f["quantidade"] for f in corpo["por_fluxo"]] == [1]
    assert [g["quantidade"] for g in corpo["por_gerencia"]] == [1]


# =============================================================================
# Regra da compra na marca da lista (`solicitacoes_com_par_liberado`)
# =============================================================================


def _liberado(s: Solicitacao) -> bool:
    return solicitacoes_com_par_liberado(Solicitacao.objects.filter(pk=s.pk)).exists()


def test_combo_sem_compra_do_2o_nao_esta_liberado(par, combo):
    a, b = par
    liberar_par(combo.municipio, a)

    assert not _liberado(combo)

    liberar_par(combo.municipio, b)
    assert _liberado(combo)


def test_combo_coberto_so_pelo_2o_nao_esta_liberado(par, combo):
    _, b = par
    liberar_par(combo.municipio, b)

    assert not _liberado(combo)


def test_null_da_colecao_do_2o_nao_casa_com_compra_sem_colecao(par, combo):
    """Os dois projetos sem coleção: a compra de outro projeto sem coleção não libera o 2º."""
    a, _ = par
    liberar_par(combo.municipio, a)
    liberar_par(combo.municipio, ProjetoFactory(nome="Solto Sem Colecao"))

    assert not _liberado(combo)


def test_compra_combos_que_cobre_os_dois_libera(gerencia):
    nl, _ = ProjetoGeral.objects.get_or_create(nome="NOVO LENDO")
    amma, _ = ProjetoGeral.objects.get_or_create(nome="PROJETO AMMA")
    kit, _ = ProjetoGeral.objects.get_or_create(nome="NL E AMMA PORT E MAT")
    a = ProjetoFactory(nome="Livro NL Teste", projeto_geral=nl, gerencia=gerencia)
    b = ProjetoFactory(nome="Livro AMMA Teste", projeto_geral=amma, gerencia=gerencia)
    s = SolicitacaoFactory(projeto=a, projeto_2=b)
    liberar_par(s.municipio, ProjetoFactory(nome="Kit NL AMMA Teste", projeto_geral=kit))

    assert _liberado(s)


def test_lista_marca_sem_compra_quando_so_o_2o_nao_tem_compra(admin, par, combo):
    a, _ = par
    liberar_par(combo.municipio, a)

    data = admin.get(f"/api/solicitacoes/{combo.pk}/").json()

    assert data["sem_compra"] is True


def test_edicao_do_combo_por_quem_nao_e_isento_confere_os_dois_projetos(par, combo):
    """Trocar o município de um combo para onde só o 1º tem compra marca `sem_compra` e volta para aprovação.

    Sem isso a edição gravava a marca `sem_compra=false` (só a vaga 1 conferida), e a marca vence o par de
    hoje na lista: o combo seguia sem aviso com o 2º sem compra.
    """
    a, b = par
    dono = UsuarioFactory()
    com_papel(dono, "COORDENADOR", a.gerencia)
    combo.usuario = dono
    combo.save(update_fields=["usuario"])
    liberar_par(combo.municipio, a)
    liberar_par(combo.municipio, b)
    m2 = MunicipioFactory(nome="Vila Sem Cataventos", uf="PE")
    liberar_par(m2, a)
    client = APIClient()
    client.force_authenticate(user=dono)

    resp = client.patch(f"/api/solicitacoes/{combo.pk}/", {"municipio": m2.pk}, format="json")

    assert resp.status_code == 200, resp.json()
    assert resp.json()["sem_compra"] is True
    combo.refresh_from_db()
    assert combo.status == "pendente"


# =============================================================================
# Pendências de Compras do DAT: o evento combo fecha a pendência dos dois projetos
# =============================================================================


def test_pendencia_do_2o_projeto_fecha_com_o_evento_combo(admin, par, combo):
    _, b = par
    liberar_par(combo.municipio, b)

    data = admin.get("/api/dat/compras-materiais/pendencias/").json()

    assert (data["total_com_compra"], data["total_com_evento"], data["total_pendentes"]) == (1, 1, 0)


def test_pendencia_da_colecao_do_2o_fecha_com_o_evento_combo(admin, gerencia):
    colecao = ProjetoGeral.objects.create(nome="Colecao Cataventos Teste")
    a = ProjetoFactory(nome="Uni Duni Teste", gerencia=gerencia)
    b = ProjetoFactory(nome="Cataventos Teste 1", gerencia=gerencia, projeto_geral=colecao)
    s = SolicitacaoFactory(projeto=a, projeto_2=b, status="pendente")
    liberar_par(s.municipio, ProjetoFactory(nome="Cataventos Teste 2", projeto_geral=colecao))

    data = admin.get("/api/dat/compras-materiais/pendencias/").json()

    assert data["total_pendentes"] == 0


# =============================================================================
# Google: descrição "Projetos: A + B"; projeto único igual byte a byte; título fica (PR 6)
# =============================================================================


def _evento_fixo(projeto: Projeto, projeto_2: Projeto | None = None) -> Solicitacao:
    return SolicitacaoFactory(
        projeto=projeto,
        projeto_2=projeto_2,
        municipio=MunicipioFactory(nome="Curvelo", uf="MG"),
        tipo_evento=TipoEventoFactory(nome="Presencial"),
        encontro="4",
        inicio=datetime(2026, 3, 10, 8, tzinfo=FORTALEZA),
        fim=datetime(2026, 3, 10, 12, tzinfo=FORTALEZA),
    )


def test_descricao_do_google_de_projeto_unico_fica_igual(par):
    a, _ = par
    s = _evento_fixo(a)

    payload = build_event_payload(s, enable_meet=False)

    assert payload["description"] == (
        f"📋 Solicitação #{s.pk} — AS v2\n\n"
        "📍 Município: Curvelo - MG\n"
        "📂 Projeto: Uni Duni Teste (UDT)\n"
        "🎯 Tipo: Presencial\n"
        "🔢 Nº da formação: 4\n"
        "📅 Data: 10/03/2026 08:00 a 10/03/2026 12:00\n"
        "🌐 Modalidade: Presencial"
    )
    assert payload["summary"] == "CURVELO - MG 4º EF - Presencial [UNI DUNI TESTE]"


def test_descricao_do_google_do_combo_lista_os_dois_e_o_titulo_fica(par):
    a, b = par
    s = _evento_fixo(a, b)

    payload = build_event_payload(s, enable_meet=False)

    assert "📂 Projetos: Cataventos Teste (CTV) + Uni Duni Teste (UDT)\n" in payload["description"]
    assert "📂 Projeto:" not in payload["description"]
    assert payload["summary"] == "CURVELO - MG 4º EF - Presencial [UNI DUNI TESTE]"


# =============================================================================
# Sem N+1: 3 combos custam as mesmas consultas que 3 eventos de projeto único
# =============================================================================


@pytest.mark.parametrize(
    "url",
    ["/api/solicitacoes/", "/api/pre-agenda/", "/api/me/events/", "/api/gcal/list/", "/api/gcal/dashboard/events/"],
)
def test_listas_com_combo_sem_n_mais_1(url, gerencia):
    usuario = UsuarioFactory(superuser=True)
    client = APIClient()
    client.force_authenticate(user=usuario)
    eventos = [
        SolicitacaoFactory(projeto=ProjetoFactory(gerencia=gerencia), status="aprovado", usuario=usuario)
        for _ in range(3)
    ]
    for s in eventos:
        Participation.objects.create(solicitacao=s, usuario=usuario, role="FORMADOR")
    client.get(url)  # aquece caches de sessão e de permissão

    with CaptureQueriesContext(connection) as unico:
        assert client.get(url).status_code == 200
    for s in eventos:
        s.projeto_2 = ProjetoFactory(gerencia=gerencia)
        s.save(update_fields=["projeto_2"])
    with CaptureQueriesContext(connection) as com_combo:
        assert client.get(url).status_code == 200

    assert len(com_combo) == len(unico)

"""
#2036, PR 4 — evento de dois projetos: a escrita pela API, a reaprovação e a compra.

Decisões do dono (07/11 e 08/11/2026):
- o evento tem até 2 projetos iguais (sem principal), da mesma gerência e do mesmo fluxo. A API recusa com 400
  em `projeto_2` o par de outra gerência, de outro fluxo, o mesmo projeto e o 2º "em espera"; o 2º sem o 1º
  também é 400;
- pela tela, pôr, trocar ou tirar o 2º de um SUPER aprovado o faz voltar para aprovação (PA-04). Inverter as
  vagas não muda nada (o conjunto é o mesmo);
- quem editou só o 2º não decide o evento depois (PA-02);
- regra da compra: o evento só segue sem a marca "sem compra" com os DOIS projetos cobertos;
- o poder (escopo, quem aprova) segue lendo `projeto`. A gerência e o alcance da aprovadora também são
  conferidos no 2º, quando ele existe e muda (defesa em profundidade); o 2º vazio nunca dá 400 (furo 1 do
  cético).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false, reportUnusedFunction=false

from __future__ import annotations

import itertools
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from django.core.cache import cache
from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, EquipeGerencia, Gerencia, Municipio, Projeto, Solicitacao, Usuario
from apps.core.services.compra_elegibilidade import MSG_PROJETO_EM_ESPERA
from apps.core.services.solicitacao_projetos import (
    MSG_FLUXO_DIFERENTE,
    MSG_GERENCIA_DIFERENTE,
    MSG_MESMO_PROJETO,
    MSG_SEGUNDO_SEM_PRIMEIRO,
)
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

_TZ = ZoneInfo("America/Fortaleza")
_SEMANA = itertools.count(1)
EDITED = "edited_by_approver_forbidden"


@pytest.fixture(autouse=True)
def _cache_limpo(db):
    cache.clear()
    yield
    cache.clear()


def _horario() -> tuple[datetime, datetime]:
    """Uma segunda-feira por evento (07/04/2031 é segunda): nada conflita na agenda."""
    inicio = datetime(2031, 4, 7, 9, tzinfo=_TZ) + timedelta(weeks=next(_SEMANA))
    return inicio, inicio.replace(hour=11)


@pytest.fixture
def g() -> Gerencia:
    return GerenciaFactory(pergunta_avaliar_formador=False)


@pytest.fixture
def m() -> Municipio:
    return MunicipioFactory(nome="Vila Escrita Combo", uf="CE")


@pytest.fixture
def tipo():
    return TipoEventoFactory(nome="Formação Combo Escrita")


@pytest.fixture
def coord(g) -> Usuario:
    """Quem cria e edita: COORDENADOR na gerência (não é isento da regra da compra)."""
    user = UsuarioFactory(first_name="Coord", last_name="Combo")
    com_papel(user, "COORDENADOR", g)
    return user


def _projeto(g: Gerencia | None, fluxo: str, *liberados: Municipio) -> Projeto:
    projeto = ProjetoFactory(gerencia=g, fluxo=fluxo)
    for municipio in liberados:
        liberar_par(municipio, projeto)
    return projeto


@pytest.fixture
def super_(g, m) -> tuple[Projeto, Projeto, Projeto]:
    """Três projetos SUPER da mesma gerência, com compra em `m`."""
    return (_projeto(g, "SUPER", m), _projeto(g, "SUPER", m), _projeto(g, "SUPER", m))


@pytest.fixture
def nao_super(g, m) -> tuple[Projeto, Projeto]:
    """Dois projetos NAO_SUPER da mesma gerência, com compra em `m`."""
    return (_projeto(g, "NAO_SUPER", m), _projeto(g, "NAO_SUPER", m))


def _client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _payload(m, tipo, projeto, projeto_2: Any = "ausente", **extra) -> dict[str, Any]:
    inicio, fim = _horario()
    payload: dict[str, Any] = {
        "municipio": m.id,
        "projeto": projeto.id if projeto is not None else None,
        "tipo_evento": tipo.id,
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
        "coordenador_acompanha": False,
    }
    if projeto_2 != "ausente":
        payload["projeto_2"] = projeto_2.id if projeto_2 is not None else None
    payload.update(extra)
    return payload


def _evento(coord, m, tipo, projeto, projeto_2=None, status="aprovado") -> Solicitacao:
    inicio, fim = _horario()
    return SolicitacaoFactory(
        usuario=coord,
        coordenador=coord,
        municipio=m,
        projeto=projeto,
        projeto_2=projeto_2,
        tipo_evento=tipo,
        inicio=inicio,
        fim=fim,
        status=status,
        gcal_status="NONE",
    )


def _patch(user, sol, dados):
    return _client(user).patch(f"/api/solicitacoes/{sol.id}/", dados, format="json")


def _ultimo_update(sol) -> AuditLog:
    return AuditLog.objects.filter(action="UPDATE", model_name="Solicitacao", details__solicitacao_id=sol.id).latest(
        "created_at", "pk"
    )


def _erros(resp) -> dict[str, Any]:
    return resp.json()["errors"]


# =============================================================================
# Criação: o par válido entra, o inválido dá 400 em pt-BR
# =============================================================================


class TestCriacao:
    def test_cria_evento_com_dois_projetos(self, coord, m, tipo, super_):
        a, b, _ = super_
        resp = _client(coord).post("/api/solicitacoes/", _payload(m, tipo, a, b), format="json")

        assert resp.status_code == 201, resp.content
        sol = Solicitacao.objects.get(pk=resp.data["id"])
        assert (sol.projeto_id, sol.projeto_2_id) == (a.id, b.id)
        assert sol.status == "pendente"  # PA-01: SUPER nunca nasce aprovado
        assert resp.data["projetos"] == [{"id": a.id, "nome": a.nome}, {"id": b.id, "nome": b.nome}]

    def test_projeto_2_nulo_cria_como_hoje(self, coord, m, tipo, super_):
        a, _, _ = super_
        resp = _client(coord).post("/api/solicitacoes/", _payload(m, tipo, a, None), format="json")

        assert resp.status_code == 201, resp.content
        assert Solicitacao.objects.get(pk=resp.data["id"]).projeto_2_id is None

    def test_gerencia_diferente_da_400(self, coord, m, tipo, super_):
        a, _, _ = super_
        de_fora = _projeto(GerenciaFactory(), "SUPER", m)

        resp = _client(coord).post("/api/solicitacoes/", _payload(m, tipo, a, de_fora), format="json")

        assert resp.status_code == 400, resp.content
        assert MSG_GERENCIA_DIFERENTE in str(_erros(resp)["projeto_2"])

    def test_fluxo_diferente_da_400(self, coord, m, tipo, super_, nao_super):
        resp = _client(coord).post("/api/solicitacoes/", _payload(m, tipo, super_[0], nao_super[0]), format="json")

        assert resp.status_code == 400, resp.content
        assert MSG_FLUXO_DIFERENTE in str(_erros(resp)["projeto_2"])

    def test_mesmo_projeto_da_400(self, coord, m, tipo, super_):
        a, _, _ = super_
        antes = Solicitacao.objects.count()

        resp = _client(coord).post("/api/solicitacoes/", _payload(m, tipo, a, a), format="json")

        assert resp.status_code == 400, resp.content
        assert MSG_MESMO_PROJETO in str(_erros(resp)["projeto_2"])
        assert Solicitacao.objects.count() == antes

    def test_segundo_em_espera_da_400(self, coord, g, m, tipo, super_):
        a, _, _ = super_
        em_espera = _projeto(g, "SUPER")  # sem compra em município nenhum

        resp = _client(coord).post("/api/solicitacoes/", _payload(m, tipo, a, em_espera), format="json")

        assert resp.status_code == 400, resp.content
        assert MSG_PROJETO_EM_ESPERA in str(_erros(resp)["projeto_2"])

    def test_projeto_nulo_com_segundo_da_400(self, coord, m, tipo, super_):
        _, b, _ = super_
        antes = Solicitacao.objects.count()

        resp = _client(coord).post("/api/solicitacoes/", _payload(m, tipo, None, b), format="json")

        assert resp.status_code == 400, resp.content
        assert "projeto" in _erros(resp)
        assert Solicitacao.objects.count() == antes

    def test_isento_da_compra_tambem_passa_pela_regra_do_par(self, m, tipo, super_):
        """Cético, 13: a regra 2 roda fora do bloco da compra (o superusuário é isento só da compra)."""
        a, _, _ = super_
        de_fora = _projeto(GerenciaFactory(), "SUPER", m)
        root = UsuarioFactory(superuser=True)

        resp = _client(root).post(
            "/api/solicitacoes/", _payload(m, tipo, a, de_fora, coordenador=root.id), format="json"
        )

        assert resp.status_code == 400, resp.content
        assert MSG_GERENCIA_DIFERENTE in str(_erros(resp)["projeto_2"])

    def test_auditlog_da_criacao_leva_o_segundo(self, coord, m, tipo, nao_super):
        a, b = nao_super
        resp = _client(coord).post("/api/solicitacoes/", _payload(m, tipo, a, b), format="json")

        assert resp.status_code == 201, resp.content
        assert resp.data["status"] == "aprovado"
        log = AuditLog.objects.get(action="CREATE", model_name="Solicitacao", details__solicitacao_id=resp.data["id"])
        assert log.details["projeto_2_id"] == b.id
        assert log.details["sem_compra"] is False


# =============================================================================
# Edição: a regra do par, o 2º sem o 1º e o PATCH que não menciona o 2º
# =============================================================================


class TestEdicao:
    def test_patch_so_com_projeto_igual_preserva_o_segundo(self, coord, m, tipo, super_):
        a, b, _ = super_
        sol = _evento(coord, m, tipo, a, b)

        resp = _patch(coord, sol, {"projeto": a.id, "observacoes": "recado"})

        assert resp.status_code == 200, resp.content
        sol.refresh_from_db()
        assert (sol.projeto_id, sol.projeto_2_id, sol.status) == (a.id, b.id, "aprovado")

    def test_patch_do_segundo_de_outra_gerencia_da_400(self, coord, m, tipo, super_):
        a, _, _ = super_
        sol = _evento(coord, m, tipo, a)
        de_fora = _projeto(GerenciaFactory(), "SUPER", m)

        resp = _patch(coord, sol, {"projeto_2": de_fora.id})

        assert resp.status_code == 400, resp.content
        assert MSG_GERENCIA_DIFERENTE in str(_erros(resp)["projeto_2"])
        sol.refresh_from_db()
        assert sol.projeto_2_id is None

    def test_trocar_o_primeiro_pelo_segundo_da_400_sem_integrity_error(self, coord, m, tipo, super_):
        """(A, B) e PATCH `projeto=B` só: as duas vagas ficariam iguais. 400, não 500."""
        a, b, _ = super_
        sol = _evento(coord, m, tipo, a, b)

        resp = _patch(coord, sol, {"projeto": b.id})

        assert resp.status_code == 400, resp.content
        assert MSG_MESMO_PROJETO in str(_erros(resp)["projeto_2"])

    def test_segundo_no_evento_sem_projeto_da_400(self, m, tipo, super_):
        """Evento legado sem projeto (gravado pelo ORM): o 2º não entra sozinho."""
        root = UsuarioFactory(superuser=True)
        sol = _evento(root, m, tipo, None)

        resp = _patch(root, sol, {"projeto_2": super_[0].id})

        assert resp.status_code == 400, resp.content
        assert MSG_SEGUNDO_SEM_PRIMEIRO in str(_erros(resp)["projeto_2"])

    def test_par_ja_gravado_nao_e_reconferido_sem_mudar_vaga(self, coord, m, tipo, super_):
        """A regra do par só roda quando o valor de alguma vaga muda: editar outro campo de um par que um
        data-fix deixou inválido não trava a edição."""
        a, _, _ = super_
        torto = _projeto(GerenciaFactory(), "SUPER", m)
        sol = _evento(coord, m, tipo, a, torto, status="pendente")

        resp = _patch(coord, sol, {"observacoes": "só um recado"})

        assert resp.status_code == 200, resp.content


# =============================================================================
# Reaprovação (PA-04): o conjunto de projetos é campo material
# =============================================================================


class TestReaprovacao:
    def test_super_aprovada_que_ganha_o_segundo_volta_para_pendente(self, coord, m, tipo, super_):
        a, b, _ = super_
        sol = _evento(coord, m, tipo, a)

        resp = _patch(coord, sol, {"projeto_2": b.id})

        assert resp.status_code == 200, resp.content
        sol.refresh_from_db()
        assert (sol.projeto_2_id, sol.status) == (b.id, "pendente")
        log = _ultimo_update(sol)
        assert log.details["reaprovacao"]["campos"] == ["projetos"]
        assert log.details["changed_fields"]["projeto_2_id"] == {"old": None, "new": b.id}

    def test_super_aprovada_que_troca_o_segundo_volta_para_pendente(self, coord, m, tipo, super_):
        a, b, c = super_
        sol = _evento(coord, m, tipo, a, b)

        resp = _patch(coord, sol, {"projeto_2": c.id})

        assert resp.status_code == 200, resp.content
        sol.refresh_from_db()
        assert (sol.projeto_2_id, sol.status) == (c.id, "pendente")

    def test_super_aprovada_que_perde_o_segundo_volta_para_pendente(self, coord, m, tipo, super_):
        a, b, _ = super_
        sol = _evento(coord, m, tipo, a, b)

        resp = _patch(coord, sol, {"projeto_2": None})

        assert resp.status_code == 200, resp.content
        sol.refresh_from_db()
        assert (sol.projeto_2_id, sol.status) == (None, "pendente")

    def test_tirar_o_primeiro_sobe_o_segundo_e_volta_para_pendente(self, coord, m, tipo, super_):
        a, b, _ = super_
        sol = _evento(coord, m, tipo, a, b)

        resp = _patch(coord, sol, {"projeto": b.id, "projeto_2": None})

        assert resp.status_code == 200, resp.content
        sol.refresh_from_db()
        assert (sol.projeto_id, sol.projeto_2_id, sol.status) == (b.id, None, "pendente")

    def test_inverter_as_vagas_nao_muda_nada(self, coord, m, tipo, super_):
        a, b, _ = super_
        sol = _evento(coord, m, tipo, a, b)

        resp = _patch(coord, sol, {"projeto": b.id, "projeto_2": a.id})

        assert resp.status_code == 200, resp.content
        sol.refresh_from_db()
        assert (sol.projeto_id, sol.projeto_2_id, sol.status) == (a.id, b.id, "aprovado")
        assert not AuditLog.objects.filter(action="UPDATE", details__solicitacao_id=sol.id).exists()

    def test_nao_super_aprovada_que_ganha_o_segundo_com_compra_segue_aprovada(self, coord, m, tipo, nao_super):
        a, b = nao_super
        sol = _evento(coord, m, tipo, a)

        resp = _patch(coord, sol, {"projeto_2": b.id})

        assert resp.status_code == 200, resp.content
        sol.refresh_from_db()
        assert (sol.projeto_2_id, sol.status) == (b.id, "aprovado")
        assert _ultimo_update(sol).details["sem_compra"] is False


# =============================================================================
# PA-02: quem editou só o 2º não decide
# =============================================================================


@pytest.fixture
def g1() -> Gerencia:
    gerencia, _ = Gerencia.objects.get_or_create(
        nome="SUPERINTENDENCIA", defaults={"nome_setor": "Superintendência", "ativo": True}
    )
    return gerencia


def _dat() -> Usuario:
    """Pessoa do DAT como em produção: grupo DAT + vínculo EQUIPE na gerência DAT (o pacote aprova)."""
    g19, _ = Gerencia.objects.get_or_create(nome="GERENCIA DAT", defaults={"nome_setor": "DAT"})
    g19.perfil = Gerencia.Perfil.ADMIN_OPERACIONAL
    g19.save()
    user = UsuarioFactory(groups=["DAT"], groups__vinculo=False)
    com_papel(user, "EQUIPE", g19)
    cache.clear()
    return user


def test_editou_so_o_segundo_grava_changed_fields_e_nao_decide(g1, m, tipo):
    a, b = _projeto(g1, "SUPER", m), _projeto(g1, "SUPER", m)
    sol = _evento(UsuarioFactory(), m, tipo, a, status="pendente")
    dat = _dat()

    resp = _patch(dat, sol, {"projeto_2": b.id})

    assert resp.status_code == 200, resp.content
    changed = _ultimo_update(sol).details["changed_fields"]
    assert set(changed) == {"projeto_2_id"}
    resp = _client(dat).patch(f"/api/solicitacoes/{sol.id}/approve/", {}, format="json")
    assert resp.status_code == 403 and resp.data["code"] == EDITED
    # Outra aprovadora decide.
    assert _client(_dat()).patch(f"/api/solicitacoes/{sol.id}/approve/", {}, format="json").status_code == 200


# =============================================================================
# Defesa em profundidade: gerência e alcance da aprovadora também no 2º
# =============================================================================


def _aprovadora(g1: Gerencia) -> Usuario:
    """GERENTE vigente na Superintendência + só o grupo "Gerente": a aprovadora restrita de produção."""
    user = UsuarioFactory(groups=["Gerente"])
    EquipeGerencia.objects.create(usuario=user, gerencia=g1, papel="GERENTE")
    return user


class TestDefesaEmProfundidade:
    def test_aprovadora_restrita_cria_projeto_unico_com_segundo_nulo(self, g1, m, tipo):
        """Furo 1 do cético: o 2º vazio não passa pelo alcance (que trata None como fora)."""
        aprovadora = _aprovadora(g1)
        projeto = _projeto(g1, "SUPER", m)
        payload = _payload(m, tipo, projeto, None, coordenador=UsuarioFactory(groups=["Coordenador"]).id)

        resp = _client(aprovadora).post("/api/solicitacoes/", payload, format="json")

        assert resp.status_code == 201, resp.content

    def test_aprovadora_restrita_edita_projeto_unico_com_segundo_nulo(self, g1, m, tipo):
        aprovadora = _aprovadora(g1)
        sol = _evento(UsuarioFactory(), m, tipo, _projeto(g1, "SUPER", m), status="pendente")

        resp = _patch(aprovadora, sol, {"projeto_2": None, "observacoes": "recado"})

        assert resp.status_code == 200, resp.content

    def test_aprovadora_restrita_cria_combo_no_alcance(self, g1, m, tipo):
        aprovadora = _aprovadora(g1)
        a, b = _projeto(g1, "SUPER", m), _projeto(g1, "SUPER", m)
        payload = _payload(m, tipo, a, b, coordenador=UsuarioFactory(groups=["Coordenador"]).id)

        resp = _client(aprovadora).post("/api/solicitacoes/", payload, format="json")

        assert resp.status_code == 201, resp.content
        assert Solicitacao.objects.get(pk=resp.data["id"]).projeto_2_id == b.id

    def test_quem_perdeu_o_papel_na_gerencia_nao_poe_o_segundo(self, m, tipo):
        """O evento próprio segue editável, mas o 2º projeto passa pelo escopo da gerência como o 1º."""
        g = GerenciaFactory(pergunta_avaliar_formador=False)
        a, b = _projeto(g, "NAO_SUPER", m), _projeto(g, "NAO_SUPER", m)
        ex_coord = UsuarioFactory()
        com_papel(ex_coord, "COORDENADOR", GerenciaFactory())  # coordena em outra gerência
        sol = _evento(ex_coord, m, tipo, a, status="pendente")

        resp = _patch(ex_coord, sol, {"projeto_2": b.id})

        assert resp.status_code == 400, resp.content
        assert "projeto_2" in _erros(resp)
        sol.refresh_from_db()
        assert sol.projeto_2_id is None


# =============================================================================
# Compra: sem a marca só com os DOIS cobertos
# =============================================================================


class TestCompra:
    def test_nao_super_com_o_segundo_sem_compra_vai_para_aprovacao(self, coord, g, m, tipo, nao_super):
        a, _ = nao_super
        sem_compra_aqui = _projeto(g, "NAO_SUPER", MunicipioFactory(nome="Outra Cidade Combo", uf="CE"))

        resp = _client(coord).post("/api/solicitacoes/", _payload(m, tipo, a, sem_compra_aqui), format="json")

        assert resp.status_code == 201, resp.content
        assert resp.data["status"] == "pendente"
        assert resp.data["sem_compra"] is True
        log = AuditLog.objects.get(action="CREATE", model_name="Solicitacao", details__solicitacao_id=resp.data["id"])
        assert log.details["sem_compra"] is True

    def test_nao_super_aprovada_que_ganha_o_segundo_sem_compra_volta_com_a_marca(self, coord, g, m, tipo, nao_super):
        a, _ = nao_super
        sem_compra_aqui = _projeto(g, "NAO_SUPER", MunicipioFactory(nome="Outra Cidade Combo 2", uf="CE"))
        sol = _evento(coord, m, tipo, a)

        resp = _patch(coord, sol, {"projeto_2": sem_compra_aqui.id})

        assert resp.status_code == 200, resp.content
        sol.refresh_from_db()
        assert sol.status == "pendente"
        log = _ultimo_update(sol)
        assert log.details["sem_compra"] is True
        assert log.details["reaprovacao"]["campos"] == ["projetos"]
        assert resp.data["sem_compra"] is True


# =============================================================================
# /lote
# =============================================================================


class TestLote:
    def test_lote_com_combo(self, coord, m, tipo, super_):
        a, b, _ = super_
        resp = _client(coord).post(
            "/api/solicitacoes/lote/",
            {"eventos": [_payload(m, tipo, a, b), _payload(m, tipo, a)]},
            format="json",
        )

        assert resp.status_code == 201, resp.content
        ids = [e["id"] for e in resp.data["eventos"]]
        assert [Solicitacao.objects.get(pk=i).projeto_2_id for i in ids] == [b.id, None]

    def test_lote_com_par_invalido_nao_cria_nada(self, coord, m, tipo, super_, nao_super):
        a, b, _ = super_
        antes = Solicitacao.objects.count()

        resp = _client(coord).post(
            "/api/solicitacoes/lote/",
            {"eventos": [_payload(m, tipo, a, b), _payload(m, tipo, a, nao_super[0])]},
            format="json",
        )

        assert resp.status_code == 400, resp.content
        (item,) = resp.data["errors"]["itens"]
        assert item["indice"] == 1
        assert MSG_FLUXO_DIFERENTE in str(item["errors"]["projeto_2"])
        assert Solicitacao.objects.count() == antes


# =============================================================================
# Lookups e /validate
# =============================================================================


class TestLookups:
    def test_projetos_mesmo_grupo_de(self, coord, g, m, super_, nao_super):
        a, b, c = super_
        _projeto(GerenciaFactory(), "SUPER", m)  # outra gerência

        itens = _client(coord).get("/api/lookup/projetos/", {"mesmo_grupo_de": a.id}).json()

        assert {i["id"] for i in itens} == {b.id, c.id}

    @pytest.mark.parametrize("valor", ["sem_gerencia", "inexistente", "lixo"])
    def test_projetos_mesmo_grupo_de_invalido_devolve_vazio(self, valor, m):
        root = UsuarioFactory(superuser=True)
        _projeto(None, "NAO_SUPER", m)
        parametro = {
            "sem_gerencia": lambda: str(_projeto(None, "NAO_SUPER", m).id),
            "inexistente": lambda: "999999",
            "lixo": lambda: "abc",
        }[valor]()

        assert _client(root).get("/api/lookup/projetos/", {"mesmo_grupo_de": parametro}).json() == []

    def test_municipios_marcam_sem_compra_se_faltar_o_segundo(self, coord, g, m, nao_super):
        a, b = nao_super
        so_a = MunicipioFactory(nome="Cidade So A Combo", uf="CE")
        liberar_par(so_a, a)
        params = {"projeto_id": a.id, "projeto_2_id": b.id, "marcar_sem_compra": "true", "q": "Combo"}

        itens = _client(coord).get("/api/lookup/municipios/", params).json()

        marcas = {i["id"]: i["sem_compra"] for i in itens}
        assert marcas[m.id] is False
        assert marcas[so_a.id] is True
        assert all(i["projeto_em_espera"] is False for i in itens)

    def test_municipios_avisam_segundo_em_espera(self, coord, g, m, nao_super):
        a, _ = nao_super
        em_espera = _projeto(g, "NAO_SUPER")
        params = {"projeto_id": a.id, "projeto_2_id": em_espera.id, "marcar_sem_compra": "true", "q": "Combo"}

        itens = _client(coord).get("/api/lookup/municipios/", params).json()

        assert itens and all(i["projeto_em_espera"] is True and i["sem_compra"] is True for i in itens)

    def test_municipios_filtro_com_os_dois(self, coord, m, nao_super):
        a, b = nao_super
        so_a = MunicipioFactory(nome="Cidade So A Filtro Combo", uf="CE")
        liberar_par(so_a, a)
        params = {"projeto_id": a.id, "projeto_2_id": b.id, "q": "Combo"}

        ids = {i["id"] for i in _client(coord).get("/api/lookup/municipios/", params).json()}

        assert m.id in ids and so_a.id not in ids


class TestValidate:
    def _validate(self, user, m, tipo, projeto, projeto_2) -> dict[str, Any]:
        payload = {
            "municipio": {"id": m.id},
            "projeto": {"id": projeto.id},
            "projeto_2": {"id": projeto_2.id},
            "tipo_evento": {"id": tipo.id},
            "date": "2031-04-07",
            "start": "09:00",
            "end": "11:00",
            "participants": {},
        }
        return _client(user).post("/api/solicitacoes/validate/", payload, format="json").json()

    def test_combo_coberto_sem_aviso(self, coord, m, tipo, nao_super):
        corpo = self._validate(coord, m, tipo, *nao_super)

        assert corpo["ok"] is True, corpo
        assert corpo["warnings"] == []
        assert corpo["canonical"]["projeto_2_id"] == nao_super[1].id

    def test_segundo_sem_compra_avisa(self, coord, g, m, tipo, nao_super):
        sem_compra_aqui = _projeto(g, "NAO_SUPER", MunicipioFactory(nome="Outra Cidade Validate", uf="CE"))

        corpo = self._validate(coord, m, tipo, nao_super[0], sem_compra_aqui)

        assert corpo["ok"] is True, corpo
        assert any("Sem compra neste município" in w for w in corpo["warnings"])

    def test_segundo_em_espera_e_erro(self, coord, g, m, tipo, nao_super):
        corpo = self._validate(coord, m, tipo, nao_super[0], _projeto(g, "NAO_SUPER"))

        assert corpo["ok"] is False
        assert MSG_PROJETO_EM_ESPERA in corpo["errors"]

    def test_par_invalido_e_erro(self, coord, m, tipo, super_, nao_super):
        corpo = self._validate(coord, m, tipo, super_[0], nao_super[0])

        assert corpo["ok"] is False
        assert MSG_FLUXO_DIFERENTE in corpo["errors"]

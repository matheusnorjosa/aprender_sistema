"""
Evento sem compra vai para aprovação (pedido do dono, 03/11/2026).

"Às vezes é necessário criar eventos em municípios sem compra." Decisões:
- todos os que criam evento podem escolher um município sem compra para o projeto (a tela avisa);
- esse evento SEMPRE nasce `pendente`, mesmo em projeto NAO_SUPER (que sem isso nasce aprovado);
- aprova quem já aprova hoje (`solicitation_approval_basis`, PA-02): DAT, Controle e o superusuário
  decidem qualquer projeto; a gerente da Superintendência segue só no fluxo SUPER da g1.

Defaults levados ao dono:
1. quem é isento da regra da compra (superusuário e a capacidade, hoje u1 + DAT) cria como antes;
2. o projeto "em espera" (sem compra em município nenhum) segue fora das listas;
3. na edição, mudar o VALOR do par para um sem compra rebaixa a aprovada para pendente (o registro das
   outras edições materiais); a pendente segue pendente; salvar com o mesmo par não rebaixa.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

import itertools
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, EquipeGerencia, Gerencia, Municipio, Solicitacao
from apps.core.tests.factories import (
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
    com_pacote_do_controle,
    com_pacote_do_dat,
    com_papel,
    liberar_par,
)

pytestmark = pytest.mark.django_db

_TZ = ZoneInfo("America/Fortaleza")
_DIA = itertools.count(1)
_N = itertools.count(1)
_AVISO = "Sem compra neste município para este projeto"


@pytest.fixture(autouse=True)
def _cache_limpo(db):
    cache.clear()
    yield
    cache.clear()


def _horario() -> tuple[datetime, datetime]:
    """Uma segunda-feira por evento (07/04/2031 é segunda): nada conflita na agenda."""
    inicio = datetime(2031, 4, 7, 9, tzinfo=_TZ) + timedelta(weeks=next(_DIA))
    return inicio, inicio.replace(hour=11)


def _pessoa(**kwargs):
    n = next(_N)
    return UsuarioFactory(
        username=f"sem_compra_{n}", email=f"sem_compra_{n}@example.invalid", first_name=f"Pessoa{n}", **kwargs
    )


@pytest.fixture
def c():
    g = Gerencia.objects.create(nome="G-SEM-COMPRA", nome_setor="Setor Sem Compra", pergunta_avaliar_formador=False)
    coord = _pessoa()
    com_papel(coord, "COORDENADOR", g)
    formador = _pessoa()
    com_papel(formador, "FORMADOR", g)
    dados = {
        "g": g,
        "com_compra": MunicipioFactory(nome="Municipio Com Compra", uf="CE"),
        "sem_compra": MunicipioFactory(nome="Municipio Sem Compra", uf="CE"),
        "tipo": TipoEventoFactory(nome="Formacao Sem Compra"),
        "nao_super": ProjetoFactory(nome="Ficticio Nao Super", gerencia=g),
        "super": ProjetoFactory(nome="Ficticio Super", gerencia=g, fluxo="SUPER"),
        "coord": coord,
        "formador": formador,
    }
    liberar_par(dados["com_compra"], dados["nao_super"])
    liberar_par(dados["com_compra"], dados["super"])
    return dados


def _client(user) -> APIClient:
    cl = APIClient()
    cl.force_authenticate(user)
    return cl


def _payload(c, municipio, projeto) -> dict[str, Any]:
    inicio, fim = _horario()
    return {
        "municipio": municipio.id,
        "projeto": projeto.id,
        "tipo_evento": c["tipo"].id,
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
        "extra_participants": {"formador_ids": [c["formador"].id]},
        "coordenador": c["coord"].id,
        "coordenador_acompanha": False,
    }


def _post(c, user, municipio, projeto):
    return _client(user).post("/api/solicitacoes/", _payload(c, municipio, projeto), format="json")


def _logs(sol_id: int, action: str) -> list[AuditLog]:
    return list(AuditLog.objects.filter(model_name="Solicitacao", action=action, details__solicitacao_id=sol_id))


def _existente(c, municipio, projeto, status: str) -> Solicitacao:
    inicio, fim = _horario()
    sol = SolicitacaoFactory(
        usuario=c["coord"],
        coordenador=c["coord"],
        municipio=municipio,
        projeto=projeto,
        tipo_evento=c["tipo"],
        inicio=inicio,
        fim=fim,
        status=status,
        gcal_status="NONE",
    )
    return sol


# ============================================================================ criação


class TestCriacao:
    def test_nao_super_sem_compra_nasce_pendente(self, c):
        r = _post(c, c["coord"], c["sem_compra"], c["nao_super"])
        assert r.status_code == 201, r.data
        assert r.data["status"] == "pendente"
        assert r.data["sem_compra"] is True
        (log,) = _logs(r.data["id"], AuditLog.Action.CREATE)
        assert log.details["sem_compra"] is True

    def test_nao_super_com_compra_segue_aprovado(self, c):
        r = _post(c, c["coord"], c["com_compra"], c["nao_super"])
        assert r.status_code == 201, r.data
        assert r.data["status"] == "aprovado"
        assert r.data["sem_compra"] is False
        (log,) = _logs(r.data["id"], AuditLog.Action.CREATE)
        assert log.details["sem_compra"] is False

    def test_super_sem_compra_nasce_pendente_com_marcador(self, c):
        r = _post(c, c["coord"], c["sem_compra"], c["super"])
        assert r.status_code == 201, r.data
        assert r.data["status"] == "pendente"
        (log,) = _logs(r.data["id"], AuditLog.Action.CREATE)
        assert log.details["sem_compra"] is True

    @pytest.mark.parametrize("isento", ["superuser", "dat"])
    def test_isento_sem_compra_cria_como_antes(self, c, isento):
        user = UsuarioFactory(superuser=True) if isento == "superuser" else _pessoa()
        if isento == "dat":
            com_pacote_do_dat(user)
        r = _post(c, user, c["sem_compra"], c["nao_super"])
        assert r.status_code == 201, r.data
        assert r.data["status"] == "aprovado"
        assert all(log.details["sem_compra"] is False for log in _logs(r.data["id"], AuditLog.Action.CREATE))

    def test_lote_sem_compra_nasce_pendente(self, c):
        eventos = [_payload(c, c["sem_compra"], c["nao_super"]), _payload(c, c["com_compra"], c["nao_super"])]
        r = _client(c["coord"]).post("/api/solicitacoes/lote/", {"eventos": eventos}, format="json")
        assert r.status_code == 201, r.data
        sem, com = r.data["eventos"]
        assert sem["status"] == "pendente"
        assert com["status"] == "aprovado"
        (log,) = _logs(sem["id"], AuditLog.Action.CREATE)
        assert log.details == {
            "solicitacao_id": sem["id"],
            "projeto_id": c["nao_super"].id,
            "sem_compra": True,
            "lote": True,
        }

    def test_municipio_segue_obrigatorio(self, c):
        payload = _payload(c, c["sem_compra"], c["nao_super"])
        del payload["municipio"]
        r = _client(c["coord"]).post("/api/solicitacoes/", payload, format="json")
        assert r.status_code == 400, r.data


# ============================================================================ edição


class TestEdicao:
    def test_aprovada_que_passa_a_par_sem_compra_volta_para_pendente(self, c):
        sol = _existente(c, c["com_compra"], c["nao_super"], "aprovado")
        r = _client(c["coord"]).patch(f"/api/solicitacoes/{sol.id}/", {"municipio": c["sem_compra"].id}, format="json")
        assert r.status_code == 200, r.data
        sol.refresh_from_db()
        assert sol.status == "pendente"
        (log,) = _logs(sol.id, AuditLog.Action.UPDATE)
        assert log.details["sem_compra"] is True
        assert log.details["reaprovacao"] == {"campos": ["municipio"]}

    def test_pendente_que_passa_a_par_sem_compra_segue_pendente(self, c):
        sol = _existente(c, c["com_compra"], c["nao_super"], "pendente")
        r = _client(c["coord"]).patch(f"/api/solicitacoes/{sol.id}/", {"municipio": c["sem_compra"].id}, format="json")
        assert r.status_code == 200, r.data
        sol.refresh_from_db()
        assert sol.status == "pendente"
        (log,) = _logs(sol.id, AuditLog.Action.UPDATE)
        assert log.details["sem_compra"] is True

    def test_salvar_sem_mudar_o_par_sem_compra_nao_rebaixa(self, c):
        sol = _existente(c, c["sem_compra"], c["nao_super"], "aprovado")
        r = _client(c["coord"]).patch(
            f"/api/solicitacoes/{sol.id}/",
            {"municipio": c["sem_compra"].id, "projeto": c["nao_super"].id, "observacoes": "mesmo par"},
            format="json",
        )
        assert r.status_code == 200, r.data
        sol.refresh_from_db()
        assert sol.status == "aprovado"
        (log,) = _logs(sol.id, AuditLog.Action.UPDATE)
        assert "sem_compra" not in log.details
        assert "reaprovacao" not in log.details

    def test_isento_muda_para_par_sem_compra_sem_rebaixar(self, c):
        sol = _existente(c, c["com_compra"], c["nao_super"], "aprovado")
        admin = UsuarioFactory(superuser=True)
        r = _client(admin).patch(f"/api/solicitacoes/{sol.id}/", {"municipio": c["sem_compra"].id}, format="json")
        assert r.status_code == 200, r.data
        sol.refresh_from_db()
        assert sol.status == "aprovado"


# ============================================================================ validate e lookup


class TestValidateELookup:
    def _validate(self, c, user, municipio, projeto):
        payload = {
            "municipio": {"id": municipio.id},
            "projeto": {"id": projeto.id},
            "tipo_evento": {"id": c["tipo"].id},
            "date": "2031-04-07",
            "start": "09:00",
            "end": "11:00",
            "participants": {},
        }
        return _client(user).post("/api/solicitacoes/validate/", payload, format="json").json()

    def test_validate_avisa_sem_bloquear(self, c):
        corpo = self._validate(c, c["coord"], c["sem_compra"], c["nao_super"])
        assert corpo["ok"] is True, corpo
        assert corpo["errors"] == []
        assert any(_AVISO in w for w in corpo["warnings"])

    def test_validate_com_compra_sem_aviso(self, c):
        corpo = self._validate(c, c["coord"], c["com_compra"], c["nao_super"])
        assert corpo["ok"] is True, corpo
        assert corpo["warnings"] == []

    def test_validate_isento_sem_aviso(self, c):
        corpo = self._validate(c, UsuarioFactory(superuser=True), c["sem_compra"], c["nao_super"])
        assert corpo["warnings"] == []

    def test_lookup_marcar_sem_compra_devolve_todos_marcados(self, c):
        params = {"projeto_id": c["nao_super"].id, "marcar_sem_compra": "true", "q": "Municipio"}
        itens = _client(c["coord"]).get("/api/lookup/municipios/", params).json()
        marcas = {i["id"]: i["sem_compra"] for i in itens}
        assert marcas[c["com_compra"].id] is False
        assert marcas[c["sem_compra"].id] is True
        # com compra primeiro: a lista sem busca (teto de 100) não esconde o município com compra
        ids = [i["id"] for i in itens]
        assert ids.index(c["com_compra"].id) < ids.index(c["sem_compra"].id)

    def test_lookup_sem_o_parametro_nao_muda(self, c):
        params = {"projeto_id": c["nao_super"].id, "com_compra": "true", "q": "Municipio"}
        itens = _client(c["coord"]).get("/api/lookup/municipios/", params).json()
        assert [i["id"] for i in itens] == [c["com_compra"].id]
        assert all("sem_compra" not in i for i in itens)

    def test_lookup_isento_marcado_nao_ve_aviso(self, c):
        """O isento cria sem compra sem aprovação: a marca seria aviso falso."""
        params = {"projeto_id": c["nao_super"].id, "marcar_sem_compra": "true", "q": "Municipio"}
        itens = _client(UsuarioFactory(superuser=True)).get("/api/lookup/municipios/", params).json()
        assert {c["com_compra"].id, c["sem_compra"].id} <= {i["id"] for i in itens}
        assert all(i["sem_compra"] is False for i in itens)

    def test_lookup_projetos_em_espera_segue_fora(self, c):
        em_espera = ProjetoFactory(nome="Ficticio Em Espera", gerencia=c["g"])
        ids = {i["id"] for i in _client(c["coord"]).get("/api/lookup/projetos/", {"com_compra": "true"}).json()}
        assert c["nao_super"].id in ids
        assert em_espera.id not in ids


# ============================================================================ aprovação


_G1 = "SUPERINTENDENCIA"


def _gerente_super():
    g1, _ = Gerencia.objects.get_or_create(nome=_G1, defaults={"nome_setor": "Super"})
    user = _pessoa(groups=["Gerente"])
    EquipeGerencia.objects.create(usuario=user, gerencia=g1, papel="GERENTE")
    return user


def _controle():
    user = _pessoa()
    com_pacote_do_controle(user)
    return user


def _dat():
    user = _pessoa()
    com_pacote_do_dat(user)
    return user


@pytest.fixture
def pendente_sem_compra(c) -> int:
    r = _post(c, c["coord"], c["sem_compra"], c["nao_super"])
    assert r.status_code == 201 and r.data["status"] == "pendente", r.data
    return r.data["id"]


class TestAprovacao:
    @pytest.mark.parametrize("quem", [_controle, _dat, lambda: UsuarioFactory(superuser=True)])
    def test_quem_aprova_qualquer_projeto_aprova(self, pendente_sem_compra, quem):
        r = _client(quem()).patch(f"/api/solicitacoes/{pendente_sem_compra}/approve/", format="json")
        assert r.status_code == 200, r.content
        assert Solicitacao.objects.get(pk=pendente_sem_compra).status == "aprovado"

    def test_gerente_da_superintendencia_fica_fora(self, pendente_sem_compra):
        r = _client(_gerente_super()).patch(f"/api/solicitacoes/{pendente_sem_compra}/approve/", format="json")
        assert r.status_code == 403, r.content
        assert r.json()["code"] == "out_of_approval_scope"

    def test_quem_criou_nao_aprova(self, c):
        criadora = _controle()
        com_papel(criadora, "COORDENADOR", c["g"])
        r = _post(c, criadora, c["sem_compra"], c["nao_super"])
        assert r.status_code == 201 and r.data["status"] == "pendente", r.data
        r = _client(criadora).patch(f"/api/solicitacoes/{r.data['id']}/approve/", format="json")
        assert r.status_code == 403, r.content
        assert r.json()["code"] == "self_approval_forbidden"

    def test_fila_de_aprovacoes_mostra_o_nao_super_sem_compra(self, c, pendente_sem_compra):
        params = {"flow": "SUPER,NAO_SUPER", "status": "pendente"}
        corpo = _client(_controle()).get("/api/solicitacoes/", params).json()
        linhas = {s["id"]: s for s in corpo["results"]}
        assert linhas[pendente_sem_compra]["sem_compra"] is True
        # o filtro de um fluxo só não muda
        so_super = _client(_controle()).get("/api/solicitacoes/", {"flow": "SUPER", "status": "pendente"}).json()
        assert pendente_sem_compra not in {s["id"] for s in so_super["results"]}

    def test_home_conta_o_nao_super_sem_compra_para_quem_decide(self, pendente_sem_compra):
        assert _client(_controle()).get("/api/stats/home/").json()["pending_approvals"] == 1
        assert _client(_gerente_super()).get("/api/stats/home/").json()["pending_approvals"] == 0

    def test_sem_compra_na_lista_em_numero_constante_de_consultas(self, c):
        """`sem_compra` sai para a página inteira numa consulta (sem N+1)."""
        for _ in range(3):
            _post(c, c["coord"], c["sem_compra"], c["nao_super"])
        admin = UsuarioFactory(superuser=True)
        cl = _client(admin)
        cl.get("/api/solicitacoes/", {"status": "pendente"})  # aquece caches de RBAC
        with CaptureQueriesContext(connection) as tres:
            cl.get("/api/solicitacoes/", {"status": "pendente"})
        for _ in range(3):
            _post(c, c["coord"], c["sem_compra"], c["nao_super"])
        with CaptureQueriesContext(connection) as seis:
            corpo = cl.get("/api/solicitacoes/", {"status": "pendente"}).json()
        assert len(corpo["results"]) == 6
        assert all(s["sem_compra"] for s in corpo["results"])
        assert len(seis.captured_queries) == len(tres.captured_queries)


# ============================================================================ revisão, rodada 1


def _g1_super_pendente(c) -> Solicitacao:
    """Pendente SUPER da g1: o escopo da gerente da Superintendência."""
    g1, _ = Gerencia.objects.get_or_create(nome=_G1, defaults={"nome_setor": "Super"})
    projeto = ProjetoFactory(nome="Ficticio Super G1", gerencia=g1, fluxo="SUPER")
    return _existente(c, c["com_compra"], projeto, "pendente")


class TestRevisaoRodada1:
    def test_a_gerente_da_superintendencia_ve_o_nao_super_como_fora_do_que_decide(self, c, pendente_sem_compra):
        no_escopo = _g1_super_pendente(c)
        params = {"flow": "SUPER,NAO_SUPER", "status": "pendente"}
        linhas = {s["id"]: s for s in _client(_gerente_super()).get("/api/solicitacoes/", params).json()["results"]}
        assert linhas[pendente_sem_compra]["decisao_impedida"] == "fora_do_escopo"
        assert linhas[no_escopo.id]["decisao_impedida"] is None
        # quem decide qualquer projeto não ganha o impedimento
        linhas = {s["id"]: s for s in _client(_controle()).get("/api/solicitacoes/", params).json()["results"]}
        assert linhas[pendente_sem_compra]["decisao_impedida"] is None

    def test_d_projeto_em_espera_segue_sem_evento(self, c):
        em_espera = ProjetoFactory(nome="Ficticio Em Espera Dois", gerencia=c["g"])
        r = _post(c, c["coord"], c["sem_compra"], em_espera)
        assert r.status_code == 400, r.data
        assert "projeto" in r.data["errors"]
        assert not Solicitacao.objects.filter(projeto=em_espera).exists()

    def test_d_projeto_em_espera_no_lote(self, c):
        em_espera = ProjetoFactory(nome="Ficticio Em Espera Tres", gerencia=c["g"])
        eventos = [_payload(c, c["com_compra"], c["nao_super"]), _payload(c, c["sem_compra"], em_espera)]
        r = _client(c["coord"]).post("/api/solicitacoes/lote/", {"eventos": eventos}, format="json")
        assert r.status_code == 400, r.data
        (item,) = r.data["errors"]["itens"]
        assert item["indice"] == 1
        assert "projeto" in item["errors"]

    def test_d_isento_segue_criando_em_projeto_em_espera(self, c):
        em_espera = ProjetoFactory(nome="Ficticio Em Espera Quatro", gerencia=c["g"])
        r = _post(c, UsuarioFactory(superuser=True), c["sem_compra"], em_espera)
        assert r.status_code == 201, r.data

    def test_d_edicao_para_projeto_em_espera_400(self, c):
        em_espera = ProjetoFactory(nome="Ficticio Em Espera Cinco", gerencia=c["g"])
        sol = _existente(c, c["com_compra"], c["nao_super"], "aprovado")
        r = _client(c["coord"]).patch(f"/api/solicitacoes/{sol.id}/", {"projeto": em_espera.id}, format="json")
        assert r.status_code == 400, r.data
        assert "projeto" in r.data["errors"]

    def test_e_reprovada_nao_se_exclui_por_quem_criou(self, c, pendente_sem_compra):
        r = _client(_controle()).patch(
            f"/api/solicitacoes/{pendente_sem_compra}/reject/", {"reason": "sem compra"}, format="json"
        )
        assert r.status_code == 200, r.content
        r = _client(c["coord"]).delete(f"/api/solicitacoes/{pendente_sem_compra}/")
        assert r.status_code == 400, r.content
        assert Solicitacao.objects.filter(pk=pendente_sem_compra).exists()

    def test_e_aprovada_nao_se_exclui_e_a_lista_diz(self, c, pendente_sem_compra):
        r = _client(_controle()).patch(f"/api/solicitacoes/{pendente_sem_compra}/approve/", format="json")
        assert r.status_code == 200, r.content
        linha = _client(c["coord"]).get(f"/api/solicitacoes/{pendente_sem_compra}/").json()
        assert linha["pode_excluir"] is False
        assert _client(c["coord"]).delete(f"/api/solicitacoes/{pendente_sem_compra}/").status_code == 400

    def test_e_nao_super_auto_aprovado_sem_decisao_segue_excluivel(self, c):
        r = _post(c, c["coord"], c["com_compra"], c["nao_super"])
        assert r.status_code == 201 and r.data["status"] == "aprovado", r.data
        assert r.data["pode_excluir"] is True
        assert _client(c["coord"]).delete(f"/api/solicitacoes/{r.data['id']}/").status_code == 204

    def test_f_marca_sem_compra_fica_pela_origem(self, c, pendente_sem_compra):
        liberar_par(c["sem_compra"], c["nao_super"])  # a compra entrou antes da decisão
        linha = _client(_controle()).get(f"/api/solicitacoes/{pendente_sem_compra}/").json()
        assert linha["sem_compra"] is True
        # pendente com compra e sem marca de origem: sem a Tag
        outra = _existente(c, c["com_compra"], c["nao_super"], "pendente")
        assert _client(_controle()).get(f"/api/solicitacoes/{outra.id}/").json()["sem_compra"] is False

    def test_c_lookup_confere_um_municipio_pelo_id(self, c):
        params = {"projeto_id": c["nao_super"].id, "marcar_sem_compra": "true", "municipio_id": c["sem_compra"].id}
        itens = _client(c["coord"]).get("/api/lookup/municipios/", params).json()
        assert [(i["id"], i["sem_compra"]) for i in itens] == [(c["sem_compra"].id, True)]


# ============================================================================ revisão, rodada 2


def _reprovada_automatica(c, details: dict[str, Any]) -> Solicitacao:
    """NAO_SUPER reprovada por automação (cópia do Google ou carga da planilha), sem decisão de pessoa."""
    sol = _existente(c, c["com_compra"], c["nao_super"], "reprovado")
    AuditLog.objects.create(
        usuario=None,
        action=AuditLog.Action.REJECT,
        model_name="Solicitacao",
        details={"solicitacao_id": sol.id, **details},
    )
    return sol


class TestRevisaoRodada2:
    def test_m1_editar_para_par_com_compra_tira_a_marca(self, c, pendente_sem_compra):
        r = _client(c["coord"]).patch(
            f"/api/solicitacoes/{pendente_sem_compra}/", {"municipio": c["com_compra"].id}, format="json"
        )
        assert r.status_code == 200, r.data
        assert r.data["sem_compra"] is False
        (log,) = _logs(pendente_sem_compra, AuditLog.Action.UPDATE)
        assert log.details["sem_compra"] is False
        linha = _client(_controle()).get(f"/api/solicitacoes/{pendente_sem_compra}/").json()
        assert linha["sem_compra"] is False

    def test_m1_criado_com_compra_grava_a_marca_falsa(self, c):
        r = _post(c, c["coord"], c["com_compra"], c["nao_super"])
        assert r.status_code == 201, r.data
        (log,) = _logs(r.data["id"], AuditLog.Action.CREATE)
        assert log.details["sem_compra"] is False

    @pytest.mark.parametrize(
        "details",
        [
            {"origem": "gcal_copia", "motivo": "cancelado_no_google"},
            {"origem": "import_export_contract", "motivo": "cancelado_na_planilha"},
        ],
        ids=["copia_google", "planilha"],
    )
    def test_b2_cancelamento_automatico_segue_excluivel(self, c, details):
        sol = _reprovada_automatica(c, details)
        linha = _client(c["coord"]).get(f"/api/solicitacoes/{sol.id}/").json()
        assert linha["pode_excluir"] is True
        assert _client(c["coord"]).delete(f"/api/solicitacoes/{sol.id}/").status_code == 204

    def test_b3_lista_diz_por_que_nao_exclui(self, c, pendente_sem_compra):
        assert _client(_controle()).patch(f"/api/solicitacoes/{pendente_sem_compra}/approve/").status_code == 200
        linha = _client(c["coord"]).get(f"/api/solicitacoes/{pendente_sem_compra}/").json()
        assert linha["pode_excluir"] is False
        assert "já foi aprovada" in linha["motivo_de_nao_excluir"]
        sincronizando = _existente(c, c["com_compra"], c["nao_super"], "aprovado")
        Solicitacao.objects.filter(pk=sincronizando.pk).update(gcal_status="PENDING")
        linha = _client(c["coord"]).get(f"/api/solicitacoes/{sincronizando.id}/").json()
        assert "sincronização" in linha["motivo_de_nao_excluir"]
        livre = _existente(c, c["com_compra"], c["nao_super"], "pendente")
        assert _client(c["coord"]).get(f"/api/solicitacoes/{livre.id}/").json()["motivo_de_nao_excluir"] is None

    def test_b4_previa_recusa_projeto_em_espera_como_a_criacao(self, c):
        em_espera = ProjetoFactory(nome="Ficticio Em Espera Seis", gerencia=c["g"])
        payload = {
            "municipio": {"id": c["sem_compra"].id},
            "projeto": {"id": em_espera.id},
            "tipo_evento": {"id": c["tipo"].id},
            "date": "2031-04-07",
            "start": "09:00",
            "end": "11:00",
            "participants": {},
        }
        corpo = _client(c["coord"]).post("/api/solicitacoes/validate/", payload, format="json").json()
        assert corpo["ok"] is False
        assert "Este projeto não tem compra em município nenhum: fica em espera até a compra entrar." in corpo["errors"]

    def test_b5_historico_mostra_o_nao_super_decidido_por_pessoa(self, c, pendente_sem_compra):
        assert _client(_controle()).patch(f"/api/solicitacoes/{pendente_sem_compra}/approve/").status_code == 200
        auto = _post(c, c["coord"], c["com_compra"], c["nao_super"]).data["id"]  # auto-aprovado
        super_aprovado = _existente(c, c["com_compra"], c["super"], "aprovado")
        automatica = _reprovada_automatica(c, {"origem": "gcal_copia", "motivo": "cancelado_no_google"})
        humana = _existente(c, c["com_compra"], c["nao_super"], "pendente")
        assert _client(_controle()).patch(f"/api/solicitacoes/{humana.id}/reject/", {"reason": "x"}).status_code == 200
        cl = _client(_controle())

        def ids(**params) -> set[int]:
            return {s["id"] for s in cl.get("/api/solicitacoes/", params).json()["results"]}

        aprovadas = ids(com_decisao="true", status="aprovado")
        assert {pendente_sem_compra, super_aprovado.id} <= aprovadas
        assert auto not in aprovadas
        reprovadas = ids(com_decisao="true", status="reprovado")
        assert humana.id in reprovadas
        assert automatica.id not in reprovadas
        # sem o parâmetro, nada muda
        assert pendente_sem_compra not in ids(flow="SUPER", status="aprovado")
        assert auto in ids(status="aprovado")

    @pytest.mark.parametrize("campos", [{"ativo": False}, {"uf": ""}], ids=["inativo", "hub"])
    def test_b6_reconferir_municipio_fora_da_lista_normal(self, c, campos):
        Municipio.objects.filter(pk=c["sem_compra"].pk).update(**campos)
        params = {"projeto_id": c["nao_super"].id, "marcar_sem_compra": "true", "municipio_id": c["sem_compra"].id}
        itens = _client(c["coord"]).get("/api/lookup/municipios/", params).json()
        assert [(i["id"], i["sem_compra"]) for i in itens] == [(c["sem_compra"].id, True)]


# ============================================================================ revisão, rodada 3


class TestRevisaoRodada3:
    @pytest.mark.parametrize("quem", ["superuser", "dat"])
    def test_1_isento_que_muda_o_par_nao_apaga_a_marca(self, c, pendente_sem_compra, quem):
        isento = UsuarioFactory(superuser=True) if quem == "superuser" else _dat()
        outro_sem_compra = MunicipioFactory(nome="Municipio Sem Compra Dois", uf="CE")
        r = _client(isento).patch(
            f"/api/solicitacoes/{pendente_sem_compra}/", {"municipio": outro_sem_compra.id}, format="json"
        )
        assert r.status_code == 200, r.data
        (log,) = _logs(pendente_sem_compra, AuditLog.Action.UPDATE)
        assert "sem_compra" not in log.details
        linha = _client(_controle()).get(f"/api/solicitacoes/{pendente_sem_compra}/").json()
        assert linha["sem_compra"] is True

    def test_2_aprovada_no_google_nao_volta_para_aprovacao_por_compra(self, c):
        sol = _existente(c, c["com_compra"], c["nao_super"], "aprovado")
        Solicitacao.objects.filter(pk=sol.pk).update(gcal_status="ERROR", external_event_id="evt-sem-compra-1")
        r = _client(c["coord"]).patch(f"/api/solicitacoes/{sol.id}/", {"municipio": c["sem_compra"].id}, format="json")
        assert r.status_code == 400, r.data
        assert "Google" in str(r.data)
        sol.refresh_from_db()
        assert (sol.status, sol.municipio_id) == ("aprovado", c["com_compra"].id)
        # par com compra no Google em ERROR segue editável como antes
        outro = MunicipioFactory(nome="Municipio Com Compra Dois", uf="CE")
        liberar_par(outro, c["nao_super"])
        r = _client(c["coord"]).patch(f"/api/solicitacoes/{sol.id}/", {"municipio": outro.id}, format="json")
        assert r.status_code == 200, r.data

    def test_3_lookup_avisa_projeto_em_espera(self, c):
        em_espera = ProjetoFactory(nome="Ficticio Em Espera Sete", gerencia=c["g"])
        params = {"projeto_id": em_espera.id, "marcar_sem_compra": "true", "municipio_id": c["com_compra"].id}
        (item,) = _client(c["coord"]).get("/api/lookup/municipios/", params).json()
        assert item["projeto_em_espera"] is True
        params["projeto_id"] = c["nao_super"].id
        (item,) = _client(c["coord"]).get("/api/lookup/municipios/", params).json()
        assert item["projeto_em_espera"] is False

"""
Regra do dono (30/09) — escopo da aprovadora por vínculo.

A base `gerente_superintendencia` (vínculo GERENTE vigente na gerência `nome == "SUPERINTENDENCIA"`,
g1) só aprova/reprova (individual e lote), edita, exclui e cria solicitação cujo projeto é do fluxo
SUPER da g1. VER não muda (lista, detalhe e prévia do Google seguem globais). As PRÓPRIAS continuam
editáveis/excluíveis como para qualquer coordenador. Quem tem base AMPLA (superuser, par Controle +
Assistente Administrativo, par legado Superintendência + Gerente, ou alcance global por capability)
não é restringido, mesmo sendo gerente de g1.

Predicado único, fail-closed: `projeto_no_escopo_da_superintendencia` (projeto None, fluxo ≠ SUPER,
sem gerência ou nome parecido → fora). `Gerencia.ativo` não entra.

A aprovadora dos testes imita produção: vínculo GERENTE em g1 + só o grupo "Gerente" (é o grupo que
dá a capability de edição).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false, reportUnusedFunction=false

from __future__ import annotations

import itertools
import logging
from datetime import date, timedelta

from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, Compra, EquipeGerencia, Gerencia, Projeto, Solicitacao, Usuario
from apps.core.tests.factories import (
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db

_G1_NOME = "SUPERINTENDENCIA"
_SERVICE_LOGGER = "apps.core.services.solicitacao_approval"
_HASH = itertools.count(1)
_NOME = itertools.count(1)

_MSG_EDITAR = "A gerência da Superintendência só edita ou exclui solicitações do fluxo SUPER da Superintendência."


@pytest.fixture(autouse=True)
def _clear_rbac_cache(db):
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def g1() -> Gerencia:
    gerencia, _ = Gerencia.objects.get_or_create(nome=_G1_NOME, defaults={"nome_setor": "Super", "ativo": True})
    return gerencia


@pytest.fixture
def outra_gerencia() -> Gerencia:
    return Gerencia.objects.create(nome="GERENCIA ESCOPO VIDAS", nome_setor="Vidas", ativo=True)


@pytest.fixture
def aprovadora(g1) -> Usuario:
    return _aprovadora(g1)


def _aprovadora(g1: Gerencia, groups: tuple[str, ...] = ("Gerente",), **kwargs) -> Usuario:
    """GERENTE vigente em g1 + grupos (default: só "Gerente", como as 5 de produção)."""
    user = UsuarioFactory(groups=list(groups), **kwargs)
    EquipeGerencia.objects.create(usuario=user, gerencia=g1, papel="GERENTE")
    return user


def _projeto(fluxo: str, gerencia: Gerencia | None) -> Projeto:
    # O " x" no fim vem de quando o /lookup/projetos/ escondia nome terminado em número. Hoje quem
    # esconde é a marca `Projeto.eh_serie`; o nome ficou.
    return ProjetoFactory(nome=f"Projeto escopo {next(_NOME)} x", fluxo=fluxo, gerencia=gerencia)


def _sol(
    fluxo: str | None = "SUPER",
    gerencia: Gerencia | None = None,
    dono: Usuario | None = None,
    status: str = "pendente",
) -> Solicitacao:
    """`fluxo=None` → solicitação SEM projeto. Um dia entre eventos: nada conflita na agenda.

    Com 3 h de espaço, dois eventos do mesmo dono em municípios diferentes ficavam a 1 h um do outro e o
    PATCH esbarrava no buffer de deslocamento (RD-04, 120 min) — falhou na CI.
    """
    inicio = timezone.now() + timedelta(days=4 + next(_HASH))
    return SolicitacaoFactory(
        usuario=dono or UsuarioFactory(groups=["Coordenador"]),
        projeto=_projeto(fluxo, gerencia) if fluxo else None,
        municipio=MunicipioFactory(),
        tipo_evento=TipoEventoFactory(nome="Formação escopo"),
        inicio=inicio,
        fim=inicio + timedelta(hours=2),
        status=status,
    )


def _compra(municipio, projeto) -> None:
    Compra.objects.create(
        codigo=f"C-ESC-{next(_HASH)}",
        projeto=projeto,
        municipio=municipio,
        quantidade=1,
        data=date(2026, 3, 1),
        uso="teste escopo",
        external_hash=f"escopo-{next(_HASH):057d}",
    )


def _client(user: Usuario) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _audit(sol: Solicitacao) -> list[AuditLog]:
    return list(AuditLog.objects.filter(model_name="Solicitacao", details__solicitacao_id=sol.id))


def _fora_do_escopo(caso: str, g1: Gerencia, outra: Gerencia) -> Solicitacao:
    return {
        "super_outra_gerencia": lambda: _sol("SUPER", outra),
        "nao_super_g1": lambda: _sol("NAO_SUPER", g1),
        "nao_super_outra_gerencia": lambda: _sol("NAO_SUPER", outra),
        "super_sem_gerencia": lambda: _sol("SUPER", None),
        "sem_projeto": lambda: _sol(None),
    }[caso]()


_CASOS_FORA = [
    "super_outra_gerencia",
    "nao_super_g1",
    "nao_super_outra_gerencia",
    "super_sem_gerencia",
    "sem_projeto",
]


# =============================================================================
# SSOT (unidade)
# =============================================================================


@pytest.mark.parametrize(
    ("fluxo", "gerencia_nome", "esperado"),
    [
        pytest.param("SUPER", _G1_NOME, True, id="super_g1"),
        pytest.param("SUPER", "GERENCIA 2 ESC", False, id="super_outra"),
        pytest.param("NAO_SUPER", _G1_NOME, False, id="nao_super_g1"),
        pytest.param("SUPER", None, False, id="super_sem_gerencia"),
        pytest.param("SUPER", "Superintendencia", False, id="parecida_caixa"),
        pytest.param("SUPER", "SUPERINTENDENCIA 2", False, id="parecida_sufixo"),
        pytest.param("SUPER", "SUPERINTENDÊNCIA", False, id="parecida_acento"),
    ],
)
def test_projeto_no_escopo_da_superintendencia(fluxo, gerencia_nome, esperado):
    from apps.core.rbac.policies import (
        ESCOPO_SUPERINTENDENCIA_PROJETO_Q,
        ESCOPO_SUPERINTENDENCIA_Q,
        projeto_no_escopo_da_superintendencia,
    )

    gerencia = Gerencia.objects.create(nome=gerencia_nome, nome_setor="X") if gerencia_nome else None
    projeto = _projeto(fluxo, gerencia)
    sol = SolicitacaoFactory(projeto=projeto)

    assert projeto_no_escopo_da_superintendencia(projeto) is esperado
    # Paridade Python × SQL: o lote e a Home usam o Q; editar/excluir, o predicado.
    assert Projeto.objects.filter(ESCOPO_SUPERINTENDENCIA_PROJETO_Q, pk=projeto.pk).exists() is esperado
    assert Solicitacao.objects.filter(ESCOPO_SUPERINTENDENCIA_Q, pk=sol.pk).exists() is esperado


def test_projeto_none_esta_fora_do_escopo():
    from apps.core.rbac.policies import projeto_no_escopo_da_superintendencia

    assert projeto_no_escopo_da_superintendencia(None) is False


def test_g1_inativa_continua_no_escopo(g1):
    from apps.core.rbac.policies import projeto_no_escopo_da_superintendencia

    g1.ativo = False
    g1.save(update_fields=["ativo"])

    assert projeto_no_escopo_da_superintendencia(_projeto("SUPER", g1)) is True


def test_aprovadora_restrita_por_persona(g1):
    from apps.core.rbac.policies import aprovadora_restrita_a_superintendencia

    assert aprovadora_restrita_a_superintendencia(_aprovadora(g1)) is True
    assert aprovadora_restrita_a_superintendencia(_aprovadora(g1, groups=())) is True
    # Controle puro não aprova: a única base de aprovação continua sendo o vínculo.
    assert aprovadora_restrita_a_superintendencia(_aprovadora(g1, groups=("Gerente", "Controle"))) is True
    assert aprovadora_restrita_a_superintendencia(_aprovadora(g1, superuser=True)) is False
    assert (
        aprovadora_restrita_a_superintendencia(_aprovadora(g1, groups=("Controle", "Assistente Administrativo")))
        is False
    )
    assert aprovadora_restrita_a_superintendencia(_aprovadora(g1, groups=("Superintendência", "Gerente"))) is False
    assert aprovadora_restrita_a_superintendencia(UsuarioFactory(groups=["Gerente"])) is False
    assert aprovadora_restrita_a_superintendencia(UsuarioFactory(groups=["Controle", "Assistente Administrativo"])) is (
        False
    )


def test_solicitation_approval_basis_for_por_persona(g1, outra_gerencia):
    from apps.core.rbac.policies import solicitation_approval_basis_for

    dentro = _sol("SUPER", g1)
    fora = _sol("SUPER", outra_gerencia)
    asst = ("Controle", "Assistente Administrativo")
    # (persona, base dentro do escopo, base fora do escopo)
    casos = [
        ("aprovadora", _aprovadora(g1), "gerente_superintendencia", None),
        ("asst", UsuarioFactory(groups=list(asst)), "asst_admin_controle", "asst_admin_controle"),
        ("superuser", UsuarioFactory(superuser=True), "superuser", "superuser"),
        (
            "legado",
            UsuarioFactory(groups=["Superintendência", "Gerente"]),
            "grupo_superintendencia_gerente",
            "grupo_superintendencia_gerente",
        ),
        ("aprovadora_com_asst", _aprovadora(g1, groups=asst), "gerente_superintendencia", "asst_admin_controle"),
        ("dat", UsuarioFactory(groups=["DAT"]), None, None),
    ]

    for nome, user, esperado_dentro, esperado_fora in casos:
        assert solicitation_approval_basis_for(user, dentro) == esperado_dentro, nome
        assert solicitation_approval_basis_for(user, fora) == esperado_fora, nome


# =============================================================================
# Aprovar / reprovar individual
# =============================================================================


@pytest.mark.parametrize(("acao", "verbo"), [("approve", "aprovar"), ("reject", "reprovar")])
@pytest.mark.parametrize("caso", _CASOS_FORA)
def test_aprovadora_nao_decide_fora_do_escopo(aprovadora, g1, outra_gerencia, caso, acao, verbo):
    sol = _fora_do_escopo(caso, g1, outra_gerencia)

    resp = _client(aprovadora).patch(f"/api/solicitacoes/{sol.id}/{acao}/", {"reason": "x"}, format="json")

    assert resp.status_code == 403, resp.content
    body = resp.json()
    assert body["code"] == "out_of_approval_scope"
    assert body["detail"] == f"Você só pode {verbo} solicitações do fluxo SUPER da Superintendência."
    sol.refresh_from_db()
    assert sol.status == "pendente"
    assert _audit(sol) == []


def test_bloqueio_fora_do_escopo_emite_warning_sem_username(aprovadora, outra_gerencia, caplog):
    sol = _sol("SUPER", outra_gerencia)

    with caplog.at_level(logging.WARNING, logger=_SERVICE_LOGGER):
        _client(aprovadora).patch(f"/api/solicitacoes/{sol.id}/approve/", format="json")

    registros = [r for r in caplog.records if r.getMessage() == "solicitacao_out_of_scope_blocked"]
    assert len(registros) == 1
    assert registros[0].user_id == aprovadora.pk
    assert registros[0].solicitacao_id == sol.id
    assert not hasattr(registros[0], "username")


@pytest.mark.parametrize(("acao", "status_final"), [("approve", "aprovado"), ("reject", "reprovado")])
def test_aprovadora_decide_super_da_g1_alheia(aprovadora, g1, acao, status_final):
    sol = _sol("SUPER", g1)

    resp = _client(aprovadora).patch(f"/api/solicitacoes/{sol.id}/{acao}/", {"reason": "x"}, format="json")

    assert resp.status_code == 200, resp.content
    sol.refresh_from_db()
    assert sol.status == status_final
    (log,) = _audit(sol)
    assert log.details["autoridade"] == "gerente_superintendencia"


@pytest.mark.parametrize(
    ("kwargs", "autoridade"),
    [
        pytest.param({"groups": ["Controle", "Assistente Administrativo"]}, "asst_admin_controle", id="asst"),
        pytest.param({"superuser": True}, "superuser", id="superuser"),
    ],
)
@pytest.mark.parametrize("caso", ["super_outra_gerencia", "nao_super_outra_gerencia", "super_sem_gerencia"])
def test_base_ampla_decide_fora_do_escopo(g1, outra_gerencia, kwargs, autoridade, caso):
    """Pin: a regra não toca Controle (par) nem superuser."""
    user = UsuarioFactory(**kwargs)
    sol = _fora_do_escopo(caso, g1, outra_gerencia)

    resp = _client(user).patch(f"/api/solicitacoes/{sol.id}/approve/", format="json")

    assert resp.status_code == 200, resp.content
    (log,) = _audit(sol)
    assert log.details["autoridade"] == autoridade


@pytest.mark.parametrize("acao", ["approve", "reject"])
def test_propria_fora_do_escopo_para_na_autoaprovacao(aprovadora, outra_gerencia, acao):
    """Ordem do service (as 3 specs): autoaprovação → escopo → status. A própria fora do escopo
    responde pela autoaprovação."""
    sol = _sol("SUPER", outra_gerencia, dono=aprovadora)

    resp = _client(aprovadora).patch(f"/api/solicitacoes/{sol.id}/{acao}/", {"reason": "x"}, format="json")

    assert resp.status_code == 403, resp.content
    assert resp.json()["code"] == "self_approval_forbidden"


@pytest.mark.parametrize("acao", ["approve", "reject"])
@pytest.mark.parametrize("status", ["aprovado", "reprovado"])
def test_alheia_fora_do_escopo_ja_decidida_para_no_escopo(aprovadora, outra_gerencia, acao, status):
    """Escopo antes do status: fora do escopo e já decidida → 403 de escopo, não 400 de status."""
    sol = _sol("NAO_SUPER", outra_gerencia, status=status)

    resp = _client(aprovadora).patch(f"/api/solicitacoes/{sol.id}/{acao}/", {"reason": "x"}, format="json")

    assert resp.status_code == 403, resp.content
    assert resp.json()["code"] == "out_of_approval_scope"


@pytest.mark.parametrize("url", ["/api/solicitacoes/batch-approve/", "/api/solicitacoes/batch-reject/"])
def test_lote_propria_fora_do_escopo_para_na_autoaprovacao(aprovadora, outra_gerencia, url):
    sol = _sol("SUPER", outra_gerencia, dono=aprovadora)

    resp = _client(aprovadora).post(url, {"ids": [sol.id]}, format="json")

    assert resp.status_code == 200, resp.content
    assert [e["code"] for e in resp.json()["errors"]] == ["self_approval_forbidden"]


def test_gerente_de_g1_com_o_par_controle_decide_fora_com_autoridade_do_par(g1, outra_gerencia):
    """Quem também tem base ampla não é restringido; o AuditLog grava a base que valeu."""
    user = _aprovadora(g1, groups=("Controle", "Assistente Administrativo"))
    fora = _sol("SUPER", outra_gerencia)
    dentro = _sol("SUPER", g1)

    assert _client(user).patch(f"/api/solicitacoes/{fora.id}/approve/", format="json").status_code == 200
    assert _client(user).patch(f"/api/solicitacoes/{dentro.id}/approve/", format="json").status_code == 200

    assert _audit(fora)[0].details["autoridade"] == "asst_admin_controle"
    assert _audit(dentro)[0].details["autoridade"] == "gerente_superintendencia"


# =============================================================================
# Lote
# =============================================================================


_LOTES = [
    ("/api/solicitacoes/batch-approve/", "approved", "aprovado", "aprovar"),
    ("/api/solicitacoes/batch-reject/", "rejected", "reprovado", "reprovar"),
]


@pytest.mark.parametrize(("url", "contador", "status_final", "verbo"), _LOTES)
def test_lote_so_decide_o_escopo(aprovadora, g1, outra_gerencia, caplog, url, contador, status_final, verbo):
    dentro = _sol("SUPER", g1)
    fora = [_sol("SUPER", outra_gerencia), _sol("NAO_SUPER", outra_gerencia), _sol("SUPER", None)]
    propria = _sol("SUPER", g1, dono=aprovadora)

    with caplog.at_level(logging.WARNING, logger=_SERVICE_LOGGER):
        resp = _client(aprovadora).post(url, {"ids": [dentro.id, *(s.id for s in fora), propria.id]}, format="json")

    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert body[contador] == 1
    erros = {e["id"]: e for e in body["errors"]}
    for sol in fora:
        assert erros[sol.id]["code"] == "out_of_approval_scope"
        assert erros[sol.id]["detail"] == f"Você só pode {verbo} solicitações do fluxo SUPER da Superintendência."
        sol.refresh_from_db()
        assert sol.status == "pendente"
        assert _audit(sol) == []
    assert erros[propria.id]["code"] == "self_approval_forbidden"
    dentro.refresh_from_db()
    assert dentro.status == status_final
    (log,) = _audit(dentro)
    assert log.details["autoridade"] == "gerente_superintendencia"
    bloqueios = [r for r in caplog.records if r.getMessage() == "solicitacao_out_of_scope_blocked"]
    assert sorted(r.solicitacao_id for r in bloqueios) == sorted(s.id for s in fora)


@pytest.mark.parametrize(("url", "contador", "status_final", "verbo"), _LOTES)
def test_lote_fora_do_escopo_nao_faz_query_por_item(aprovadora, outra_gerencia, url, contador, status_final, verbo):
    um = [_sol("SUPER", outra_gerencia).id]
    vinte = [_sol("SUPER", outra_gerencia).id for _ in range(20)]
    client = _client(aprovadora)
    client.post(url, {"ids": um}, format="json")  # aquece caches de RBAC fora da medição

    with CaptureQueriesContext(connection) as com_um:
        client.post(url, {"ids": um}, format="json")
    with CaptureQueriesContext(connection) as com_vinte:
        resp = client.post(url, {"ids": vinte}, format="json")

    assert resp.json()[contador] == 0
    assert len(com_vinte.captured_queries) == len(com_um.captured_queries)


@pytest.mark.parametrize(("url", "contador", "status_final", "verbo"), _LOTES)
def test_lote_da_gerente_de_g1_com_o_par_controle_grava_autoridade_por_item(
    g1, outra_gerencia, url, contador, status_final, verbo
):
    """Persona mista: dentro do escopo vale o vínculo; fora, o par Controle. A medição pós-deploy
    ("gerente_superintendencia fora do escopo = 0") depende disso também no lote."""
    user = _aprovadora(g1, groups=("Controle", "Assistente Administrativo"))
    dentro = _sol("SUPER", g1)
    fora = _sol("SUPER", outra_gerencia)

    resp = _client(user).post(url, {"ids": [dentro.id, fora.id]}, format="json")

    assert resp.status_code == 200, resp.content
    assert resp.json()[contador] == 2
    assert _audit(dentro)[0].details["autoridade"] == "gerente_superintendencia"
    assert _audit(fora)[0].details["autoridade"] == "asst_admin_controle"


@pytest.mark.parametrize(
    "kwargs",
    [
        pytest.param({"groups": ["Controle", "Assistente Administrativo"]}, id="asst"),
        pytest.param({"superuser": True}, id="superuser"),
    ],
)
def test_base_ampla_decide_fora_do_escopo_em_lote(g1, outra_gerencia, kwargs):
    user = UsuarioFactory(**kwargs)
    fora = [_sol("SUPER", outra_gerencia), _sol("NAO_SUPER", outra_gerencia), _sol("SUPER", None)]

    resp = _client(user).post("/api/solicitacoes/batch-approve/", {"ids": [s.id for s in fora]}, format="json")

    assert resp.status_code == 200, resp.content
    assert resp.json()["approved"] == 3


# =============================================================================
# Editar / excluir (IsOwnerOrPrivileged)
# =============================================================================


@pytest.mark.parametrize(
    ("fluxo", "onde", "status"),
    [
        pytest.param("SUPER", "outra", "pendente", id="super_outra_pendente"),
        pytest.param("NAO_SUPER", "outra", "aprovado", id="nao_super_outra_aprovada"),
        pytest.param("NAO_SUPER", "g1", "aprovado", id="nao_super_g1_aprovada"),
    ],
)
def test_aprovadora_nao_edita_fora_do_escopo(aprovadora, g1, outra_gerencia, fluxo, onde, status):
    sol = _sol(fluxo, g1 if onde == "g1" else outra_gerencia, status=status)

    resp = _client(aprovadora).patch(f"/api/solicitacoes/{sol.id}/", {"observacoes": "x"}, format="json")

    assert resp.status_code == 403, resp.content
    assert resp.json()["detail"] == _MSG_EDITAR
    sol.refresh_from_db()
    assert sol.observacoes != "x"


@pytest.mark.parametrize("status", ["pendente", "aprovado"])
def test_aprovadora_edita_super_da_g1_alheia(aprovadora, g1, status):
    sol = _sol("SUPER", g1, status=status)

    resp = _client(aprovadora).patch(f"/api/solicitacoes/{sol.id}/", {"observacoes": "x"}, format="json")

    assert resp.status_code == 200, resp.content
    sol.refresh_from_db()
    assert sol.observacoes == "x"


@pytest.mark.parametrize(
    ("fluxo", "status"),
    [
        pytest.param("NAO_SUPER", "aprovado", id="nao_super_outra"),
        pytest.param("SUPER", "pendente", id="super_outra_pendente"),
    ],
)
def test_aprovadora_nao_exclui_fora_do_escopo(aprovadora, outra_gerencia, fluxo, status):
    sol = _sol(fluxo, outra_gerencia, status=status)

    resp = _client(aprovadora).delete(f"/api/solicitacoes/{sol.id}/")

    assert resp.status_code == 403, resp.content
    assert resp.json()["detail"] == _MSG_EDITAR
    assert Solicitacao.objects.filter(pk=sol.pk).exists()


def test_aprovadora_exclui_super_pendente_da_g1_alheia(aprovadora, g1):
    sol = _sol("SUPER", g1)

    resp = _client(aprovadora).delete(f"/api/solicitacoes/{sol.id}/")

    assert resp.status_code == 204, resp.content
    assert not Solicitacao.objects.filter(pk=sol.pk).exists()


def test_aprovadora_edita_e_exclui_a_propria_fora_do_escopo(aprovadora, outra_gerencia):
    """Caminho de dona: como qualquer coordenador (a regra não mexe nas próprias)."""
    editar = _sol("NAO_SUPER", outra_gerencia, dono=aprovadora, status="aprovado")
    excluir = _sol("NAO_SUPER", outra_gerencia, dono=aprovadora, status="aprovado")
    _compra(editar.municipio, editar.projeto)  # mandar `projeto` reaplica a Regra 4 (compra do par)
    client = _client(aprovadora)

    # O EditSolicitacaoPage manda `projeto` em todo save: o mesmo projeto não é "mover".
    patch = client.patch(
        f"/api/solicitacoes/{editar.id}/", {"observacoes": "x", "projeto": editar.projeto_id}, format="json"
    )
    delete = client.delete(f"/api/solicitacoes/{excluir.id}/")

    assert patch.status_code == 200, patch.content
    assert delete.status_code == 204, delete.content


@pytest.mark.parametrize(
    "groups",
    [
        pytest.param(("Gerente", "Controle", "Assistente Administrativo"), id="par_controle"),
        pytest.param(("Gerente", "Controle"), id="controle_por_capability"),
        pytest.param(("Gerente", "DAT"), id="dat_por_capability"),
    ],
)
def test_gerente_de_g1_com_base_ampla_edita_fora_do_escopo(g1, outra_gerencia, groups):
    """Alcance global que vem de OUTRA base (par Controle, operate_preagenda, manage_admin_registries)
    não é tirado pelo vínculo em g1."""
    user = _aprovadora(g1, groups=groups)
    sol = _sol("NAO_SUPER", outra_gerencia, status="aprovado")

    resp = _client(user).patch(f"/api/solicitacoes/{sol.id}/", {"observacoes": "x"}, format="json")

    assert resp.status_code == 200, resp.content


def test_gerente_de_g1_com_controle_puro_so_decide_o_escopo(g1, outra_gerencia):
    """Controle puro não aprova: a decisão fica no escopo, mesmo com a edição global."""
    user = _aprovadora(g1, groups=("Gerente", "Controle"))
    sol = _sol("SUPER", outra_gerencia)

    resp = _client(user).patch(f"/api/solicitacoes/{sol.id}/approve/", format="json")

    assert resp.status_code == 403, resp.content
    assert resp.json()["code"] == "out_of_approval_scope"


def test_segundo_vinculo_de_gestor_continua_valendo(aprovadora, g1, outra_gerencia):
    """Vínculo GERENTE em outra gerência segue no tier de gestor (sem reabrir o NAO_SUPER de g1)."""
    EquipeGerencia.objects.create(usuario=aprovadora, gerencia=outra_gerencia, papel="GERENTE")
    da_outra = _sol("NAO_SUPER", outra_gerencia, status="aprovado")
    nao_super_g1 = _sol("NAO_SUPER", g1, status="aprovado")
    client = _client(aprovadora)

    assert client.patch(f"/api/solicitacoes/{da_outra.id}/", {"observacoes": "x"}, format="json").status_code == 200
    assert client.patch(f"/api/solicitacoes/{nao_super_g1.id}/", {"observacoes": "x"}, format="json").status_code == 403


@pytest.mark.parametrize(
    ("papel", "alcanca"),
    [("GERENTE", True), ("COORDENADOR", False), ("APOIO", False), ("FORMADOR", False)],
)
def test_segundo_vinculo_so_da_tier_com_papel_de_gestao(aprovadora, g1, outra_gerencia, papel, alcanca):
    """Tier do 2º vínculo: só GERENTE. Coordenadora ou apoio comum não mexe em solicitação alheia da
    gerência, então COORDENADOR/APOIO/FORMADOR em outra gerência não dão criar/editar/excluir/mover lá."""
    EquipeGerencia.objects.create(usuario=aprovadora, gerencia=outra_gerencia, papel=papel)
    editar = _sol("NAO_SUPER", outra_gerencia, status="aprovado")
    excluir = _sol("NAO_SUPER", outra_gerencia, status="aprovado")
    mover = _sol("SUPER", g1)
    destino = _projeto("NAO_SUPER", outra_gerencia)
    _compra(mover.municipio, destino)
    municipio = MunicipioFactory()
    _compra(municipio, destino)
    client = _client(aprovadora)

    patch = client.patch(f"/api/solicitacoes/{editar.id}/", {"observacoes": "x"}, format="json")
    delete = client.delete(f"/api/solicitacoes/{excluir.id}/")
    move = client.patch(f"/api/solicitacoes/{mover.id}/", {"projeto": destino.id}, format="json")
    create = client.post(
        "/api/solicitacoes/", _payload(municipio, destino, TipoEventoFactory(nome="Formação escopo")), format="json"
    )
    lookup = {item["id"] for item in client.get("/api/lookup/projetos/").json()}

    esperado = (200, 204, 200, 201) if alcanca else (403, 403, 400, 400)
    assert (patch.status_code, delete.status_code, move.status_code, create.status_code) == esperado, (
        patch.content,
        delete.content,
        move.content,
        create.content,
    )
    assert (destino.id in lookup) is alcanca


# =============================================================================
# Trocar o projeto na edição (destino também no escopo)
# =============================================================================


@pytest.mark.parametrize("destino", ["nao_super_outra", "super_outra", "nenhum"])
def test_aprovadora_nao_move_para_fora_do_escopo(aprovadora, g1, outra_gerencia, destino):
    sol = _sol("SUPER", g1)
    novo = {
        "nao_super_outra": lambda: _projeto("NAO_SUPER", outra_gerencia),
        "super_outra": lambda: _projeto("SUPER", outra_gerencia),
        "nenhum": lambda: None,
    }[destino]()
    if novo is not None:
        _compra(sol.municipio, novo)  # sem a Compra, a Regra 4 do serializer mascararia o teste
    projeto_antes = sol.projeto_id

    resp = _client(aprovadora).patch(
        f"/api/solicitacoes/{sol.id}/", {"projeto": novo.id if novo else None}, format="json"
    )

    assert resp.status_code == 400, resp.content
    assert "projeto" in resp.json()["errors"]
    sol.refresh_from_db()
    assert sol.projeto_id == projeto_antes
    assert sol.status == "pendente"


def test_aprovadora_move_para_outro_projeto_do_escopo(aprovadora, g1):
    sol = _sol("SUPER", g1)
    novo = _projeto("SUPER", g1)
    _compra(sol.municipio, novo)

    resp = _client(aprovadora).patch(f"/api/solicitacoes/{sol.id}/", {"projeto": novo.id}, format="json")

    assert resp.status_code == 200, resp.content
    sol.refresh_from_db()
    assert sol.projeto_id == novo.id


def test_aprovadora_nao_move_a_propria_para_fora_do_escopo(aprovadora, g1, outra_gerencia):
    """Criar só no escopo: mover a própria para fora seria criar fora por outro caminho."""
    sol = _sol("SUPER", g1, dono=aprovadora)
    novo = _projeto("NAO_SUPER", outra_gerencia)
    _compra(sol.municipio, novo)

    resp = _client(aprovadora).patch(f"/api/solicitacoes/{sol.id}/", {"projeto": novo.id}, format="json")

    assert resp.status_code == 400, resp.content
    assert "projeto" in resp.json()["errors"]


# =============================================================================
# Criar
# =============================================================================


def _payload(municipio, projeto, tipo_evento) -> dict:
    inicio = timezone.now() + timedelta(days=6)
    return {
        "municipio": municipio.id,
        "projeto": projeto.id if projeto else None,
        "tipo_evento": tipo_evento.id,
        "tipo": "PRESENCIAL",
        "inicio": inicio.isoformat(),
        "fim": (inicio + timedelta(hours=2)).isoformat(),
    }


@pytest.mark.parametrize("destino", ["nao_super_outra", "super_outra", "nao_super_g1", "nenhum"])
def test_aprovadora_so_cria_no_escopo(aprovadora, g1, outra_gerencia, destino):
    municipio = MunicipioFactory()
    projeto = {
        "nao_super_outra": lambda: _projeto("NAO_SUPER", outra_gerencia),
        "super_outra": lambda: _projeto("SUPER", outra_gerencia),
        "nao_super_g1": lambda: _projeto("NAO_SUPER", g1),
        "nenhum": lambda: None,
    }[destino]()
    if projeto is not None:
        _compra(municipio, projeto)
    antes = Solicitacao.objects.count()

    resp = _client(aprovadora).post(
        "/api/solicitacoes/", _payload(municipio, projeto, TipoEventoFactory(nome="Formação escopo")), format="json"
    )

    assert resp.status_code == 400, resp.content
    assert "projeto" in resp.json()["errors"]
    assert Solicitacao.objects.count() == antes


def test_aprovadora_cria_no_escopo(aprovadora, g1):
    municipio = MunicipioFactory()
    projeto = _projeto("SUPER", g1)
    _compra(municipio, projeto)

    resp = _client(aprovadora).post(
        "/api/solicitacoes/", _payload(municipio, projeto, TipoEventoFactory(nome="Formação escopo")), format="json"
    )

    assert resp.status_code == 201, resp.content


def test_lookup_de_projetos_da_aprovadora_so_oferece_o_escopo(aprovadora, g1, outra_gerencia):
    """O wizard e a edição usam `/lookup/projetos/`: a tela só oferece o que o backend aceita."""
    no_escopo = _projeto("SUPER", g1)
    fora = [_projeto("NAO_SUPER", g1), _projeto("SUPER", outra_gerencia), _projeto("NAO_SUPER", outra_gerencia)]

    resp = _client(aprovadora).get("/api/lookup/projetos/")

    assert resp.status_code == 200, resp.content
    ids = {item["id"] for item in resp.json()}
    assert no_escopo.id in ids
    assert not ids & {p.id for p in fora}


def test_lookup_do_asst_admin_controle_nao_muda(g1, outra_gerencia):
    user = _aprovadora(g1, groups=("Gerente", "Controle", "Assistente Administrativo"))
    fora = _projeto("NAO_SUPER", outra_gerencia)

    resp = _client(user).get("/api/lookup/projetos/")

    assert fora.id in {item["id"] for item in resp.json()}


# =============================================================================
# VER não muda (pins)
# =============================================================================


def test_aprovadora_continua_vendo_tudo(aprovadora, g1, outra_gerencia):
    fora = [_sol("SUPER", outra_gerencia), _sol("NAO_SUPER", outra_gerencia, status="aprovado")]
    client = _client(aprovadora)

    lista = client.get("/api/solicitacoes/")
    detalhe = client.get(f"/api/solicitacoes/{fora[1].id}/")

    assert lista.status_code == 200
    assert {s.id for s in fora} <= {row["id"] for row in lista.json()["results"]}
    assert detalhe.status_code == 200, detalhe.content


# =============================================================================
# Card "Aprovações pendentes" da Home
# =============================================================================


def test_home_da_aprovadora_conta_so_o_que_ela_decide(aprovadora, g1, outra_gerencia):
    _sol("SUPER", g1)
    _sol("SUPER", outra_gerencia)
    _sol("SUPER", None)

    resp = _client(aprovadora).get("/api/stats/home/")

    assert resp.status_code == 200
    assert resp.json()["pending_approvals"] == 1


def test_home_do_asst_admin_controle_conta_tudo(g1, outra_gerencia):
    _sol("SUPER", g1)
    _sol("SUPER", outra_gerencia)

    resp = _client(UsuarioFactory(groups=["Controle", "Assistente Administrativo"])).get("/api/stats/home/")

    assert resp.json()["pending_approvals"] == 2

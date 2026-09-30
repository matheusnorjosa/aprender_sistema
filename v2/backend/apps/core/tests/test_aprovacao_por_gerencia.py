"""
PR B1 — aprovação pela gerência (PLANOS_LIBERACAO_2026-09-29 §3).

Aprova quem tem vínculo `EquipeGerencia` VIGENTE com papel GERENTE na gerência cujo
`nome == "SUPERINTENDENCIA"` (g1), sem depender de grupo Django. Controle + Assistente
Administrativo e superuser continuam aprovando; o composite de grupos
(Superintendência, Gerente) segue valendo em paralelo até o B2.

A chave de g1 é `Gerencia.nome` (técnica, estável), não `nome_setor` (rótulo editável).
`Gerencia.ativo` NÃO é checado: o vínculo tem o próprio desligamento (`ativo`/vigência).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false, reportUnusedFunction=false

from __future__ import annotations

import logging
from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import EquipeGerencia, Gerencia, Solicitacao, Usuario
from apps.core.tests.factories import (
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db

# Literal de propósito: os testes de comportamento não dependem do import da constante
# (só o sentinela abaixo a importa), para o RED de cada um apontar o comportamento.
_G1_NOME = "SUPERINTENDENCIA"


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
    return Gerencia.objects.create(nome="GERENCIA 2 B1", nome_setor="Vidas", ativo=True)


def _vincular(user: Usuario, gerencia: Gerencia, papel: str, **kwargs) -> EquipeGerencia:
    if papel == "APOIO" and "coordenador_supervisor" not in kwargs:
        kwargs["coordenador_supervisor"] = UsuarioFactory()
    return EquipeGerencia.objects.create(usuario=user, gerencia=gerencia, papel=papel, **kwargs)


def _aprovadora(g1: Gerencia) -> Usuario:
    """GERENTE vigente em g1, SEM nenhum grupo Django."""
    user = UsuarioFactory()
    _vincular(user, g1, "GERENTE")
    return user


def _pendente_super(gerencia: Gerencia | None = None, dono: Usuario | None = None) -> Solicitacao:
    projeto = ProjetoFactory(fluxo="SUPER", gerencia=gerencia)
    inicio = timezone.now() + timedelta(days=3)
    return SolicitacaoFactory(
        usuario=dono or UsuarioFactory(groups=["Coordenador"]),
        projeto=projeto,
        municipio=MunicipioFactory(),
        tipo_evento=TipoEventoFactory(nome="Formação B1"),
        inicio=inicio,
        fim=inicio + timedelta(hours=2),
        status="pendente",
    )


def _client(user: Usuario) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _approve(user: Usuario, sol: Solicitacao):
    return _client(user).patch(f"/api/solicitacoes/{sol.id}/approve/", format="json")


def _negado_pela_base(resp) -> bool:
    """403 por falta de base. Os negativos usam pendente SUPER de g1 (DENTRO do escopo da regra de
    30/09): assim o 403 de escopo (`out_of_approval_scope`) não mascara uma base frouxa."""
    return resp.status_code == 403 and resp.json().get("code") != "out_of_approval_scope"


# =============================================================================
# Quem aprova
# =============================================================================


def test_gerente_vigente_em_g1_sem_grupos_aprova(g1):
    """Fora do escopo (SUPER de outra gerência) a regra do dono de 30/09 dá 403: ver
    test_escopo_aprovadora_superintendencia.py."""
    aprovadora = _aprovadora(g1)
    sol = _pendente_super(g1)

    resp = _approve(aprovadora, sol)

    assert resp.status_code == 200, resp.content
    sol.refresh_from_db()
    assert sol.status == "aprovado"


def test_aprovadora_aparece_com_a_policy_em_me_e_me_policies(g1):
    client = _client(_aprovadora(g1))

    me = client.get("/api/me/")
    policies = client.get("/api/me/policies/")

    assert me.status_code == 200
    assert me.json()["can_approve_super"] is True
    assert policies.status_code == 200
    assert "access_solicitation_approvals" in policies.json()


@pytest.mark.parametrize("papel", ["COORDENADOR", "APOIO", "FORMADOR"])
def test_outros_papeis_em_g1_nao_aprovam(g1, papel):
    user = UsuarioFactory()
    _vincular(user, g1, papel)
    sol = _pendente_super(g1)

    assert _negado_pela_base(_approve(user, sol))


def test_gerente_de_outra_gerencia_nao_aprova(g1, outra_gerencia):
    user = UsuarioFactory()
    _vincular(user, outra_gerencia, "GERENTE")
    sol = _pendente_super(g1)

    assert _negado_pela_base(_approve(user, sol))


@pytest.mark.parametrize(
    "vinculo_kwargs",
    [
        pytest.param(
            {
                "valid_from": timezone.localdate() - timedelta(days=30),
                "valid_to": timezone.localdate() - timedelta(days=1),
            },
            id="expirado",
        ),
        pytest.param({"ativo": False}, id="inativo"),
        pytest.param({"valid_from": timezone.localdate() + timedelta(days=1)}, id="futuro"),
    ],
)
def test_vinculo_nao_vigente_em_g1_nao_aprova(g1, vinculo_kwargs):
    user = UsuarioFactory()
    _vincular(user, g1, "GERENTE", **vinculo_kwargs)
    sol = _pendente_super(g1)

    assert _negado_pela_base(_approve(user, sol))


@pytest.mark.parametrize(
    "kwargs",
    [
        pytest.param({"groups": ["Controle", "Assistente Administrativo"]}, id="asst_admin_controle"),
        pytest.param({"superuser": True}, id="superuser"),
    ],
)
def test_asst_admin_controle_e_superuser_continuam_aprovando(kwargs):
    user = UsuarioFactory(**kwargs)
    sol = _pendente_super()

    assert _approve(user, sol).status_code == 200


def test_dat_nao_altera_a_conta_da_aprovadora(g1):
    aprovadora = _aprovadora(g1)
    original = aprovadora.email
    dat = UsuarioFactory(groups=["DAT"])

    resp = _client(dat).patch(f"/api/usuarios-admin/{aprovadora.id}/", {"email": "tomada@example.com"}, format="json")

    assert resp.status_code == 403
    aprovadora.refresh_from_db()
    assert aprovadora.email == original


def test_lista_super_pendente_mostra_outras_gerencias(g1, outra_gerencia):
    aprovadora = _aprovadora(g1)
    alheia = _pendente_super(outra_gerencia)
    sem_gerencia = _pendente_super(None)

    resp = _client(aprovadora).get("/api/solicitacoes/?flow=SUPER&status=pendente")

    assert resp.status_code == 200
    ids = {row["id"] for row in resp.json()["results"]}
    assert {alheia.id, sem_gerencia.id} <= ids


def test_lista_da_aprovadora_tem_teto_de_queries(g1, outra_gerencia, django_assert_max_num_queries):
    aprovadora = _aprovadora(g1)
    for _ in range(5):
        _pendente_super(outra_gerencia)
    client = _client(aprovadora)

    # Medido: 5 queries com 5 linhas (a policy soma 1 EXISTS de vínculo). Teto 8 dá folga
    # sem esconder um N+1 (1 query por linha estouraria).
    with django_assert_max_num_queries(8):
        resp = client.get("/api/solicitacoes/?flow=SUPER&status=pendente")

    assert resp.status_code == 200
    assert resp.json()["count"] == 5


# =============================================================================
# SSOT da regra
# =============================================================================


def test_solicitation_approval_basis_por_persona(g1):
    from apps.core.rbac.policies import solicitation_approval_basis

    composite = UsuarioFactory(groups=["Superintendência", "Gerente"])
    assert solicitation_approval_basis(UsuarioFactory(superuser=True)) == "superuser"
    assert solicitation_approval_basis(_aprovadora(g1)) == "gerente_superintendencia"
    assert solicitation_approval_basis(UsuarioFactory(groups=["Controle", "Assistente Administrativo"])) == (
        "asst_admin_controle"
    )
    assert solicitation_approval_basis(composite) == "grupo_superintendencia_gerente"
    assert solicitation_approval_basis(UsuarioFactory(groups=["DAT"])) is None


def test_sentinela_seed_gerencias_contem_a_gerencia_aprovadora():
    """Se o seed renomear/remover g1, a regra falha fechada em silêncio — este teste acusa."""
    from apps.core.management.commands.seed_gerencias import GERENCIAS
    from apps.core.rbac.helpers import GERENCIA_APROVADORA_NOME

    assert GERENCIA_APROVADORA_NOME == _G1_NOME
    assert GERENCIA_APROVADORA_NOME in {g["nome"] for g in GERENCIAS}


# =============================================================================
# Anti-escalada: a chave `Gerencia.nome` da gerência aprovadora é imutável pela API
# =============================================================================


def test_patch_no_nome_de_g1_devolve_400(g1):
    resp = _client(UsuarioFactory(superuser=True)).patch(
        f"/api/gerencias/{g1.id}/", {"nome": "SUPERINTENDENCIA ANTIGA"}, format="json"
    )

    assert resp.status_code == 400, resp.content
    g1.refresh_from_db()
    assert g1.nome == _G1_NOME


def test_patch_em_outros_campos_de_g1_continua_permitido(g1):
    resp = _client(UsuarioFactory(superuser=True)).patch(
        f"/api/gerencias/{g1.id}/", {"nome": _G1_NOME, "descricao": "nova"}, format="json"
    )

    assert resp.status_code == 200, resp.content


@pytest.mark.parametrize(
    "nome",
    ["Superintendencia", "SUPERINTENDENCIA 2", "SUPERINTENDÊNCIA"],
    ids=["caixa", "sufixo", "acento"],
)
def test_chave_e_o_nome_exato_da_gerencia(nome, g1):
    """Só `nome == "SUPERINTENDENCIA"` aprova. Rótulo (`nome_setor`) e setor iguais aos de g1 não
    dão poder de aprovar: esses campos são editáveis e não são a chave."""
    parecida = Gerencia.objects.create(nome=nome, nome_setor="Super", setor_canonico="Superintendência", ativo=True)
    gerente = UsuarioFactory()
    _vincular(gerente, parecida, "GERENTE")

    assert _negado_pela_base(_approve(gerente, _pendente_super(g1)))


def test_g1_desativada_continua_aprovando(g1):
    """`Gerencia.ativo` não entra na regra: DAT/Controle editam esse campo e desligar g1 pararia
    todas as aprovações. O desligamento é pelo vínculo (ativo/vigência)."""
    aprovadora = _aprovadora(g1)
    g1.ativo = False
    g1.save(update_fields=["ativo"])

    assert _approve(aprovadora, _pendente_super(g1)).status_code == 200


def test_criar_gerencia_com_o_nome_aprovador_devolve_400():
    """Sem g1 no banco, a unicidade de `nome` não barra: só `validate_nome` impede criar a chave."""
    assert not Gerencia.objects.filter(nome=_G1_NOME).exists()

    resp = _client(UsuarioFactory(superuser=True)).post(
        "/api/gerencias/", {"nome": _G1_NOME, "nome_setor": "Super"}, format="json"
    )

    assert resp.status_code == 400, resp.content
    assert not Gerencia.objects.filter(nome=_G1_NOME).exists()


def test_outra_gerencia_nao_pode_assumir_o_nome_aprovador(outra_gerencia):
    """Sem g1 no banco (regra falha fechada), renomear outra para a chave abriria aprovação."""
    resp = _client(UsuarioFactory(superuser=True)).patch(
        f"/api/gerencias/{outra_gerencia.id}/", {"nome": _G1_NOME}, format="json"
    )

    assert resp.status_code == 400, resp.content
    outra_gerencia.refresh_from_db()
    assert outra_gerencia.nome != _G1_NOME


# =============================================================================
# Prévia do Google na tela de Aprovações (decisão 5 do dono): leitura liberada
# pela policy de aprovação; publicar continua exigindo `use_gcal`.
# =============================================================================


def test_aprovadora_ve_a_previa_do_google(g1, outra_gerencia):
    aprovadora = _aprovadora(g1)
    sol = _pendente_super(outra_gerencia)

    resp = _client(aprovadora).post(f"/api/solicitacoes/{sol.id}/preview-gcal/", format="json")

    assert resp.status_code == 200, resp.content
    assert "preview" in resp.json()


def test_log_da_previa_nao_leva_username(g1, outra_gerencia, caplog):
    """Username é o CPF em produção (29/09): a prévia, agora aberta às aprovadoras, loga só o id."""
    aprovadora = _aprovadora(g1)
    sol = _pendente_super(outra_gerencia)

    with caplog.at_level(logging.INFO, logger="apps.core.services.solicitacao_publish"):
        resp = _client(aprovadora).post(f"/api/solicitacoes/{sol.id}/preview-gcal/", format="json")

    assert resp.status_code == 200, resp.content
    registros = [r for r in caplog.records if r.getMessage() == "preview_gcal"]
    assert len(registros) == 1
    assert not hasattr(registros[0], "username")
    assert registros[0].user_id == aprovadora.pk


def test_aprovadora_sem_use_gcal_nao_publica(g1, outra_gerencia):
    aprovadora = _aprovadora(g1)
    sol = _pendente_super(outra_gerencia)

    resp = _client(aprovadora).post(f"/api/solicitacoes/{sol.id}/publish/", {"dry_run": True}, format="json")

    assert resp.status_code == 403

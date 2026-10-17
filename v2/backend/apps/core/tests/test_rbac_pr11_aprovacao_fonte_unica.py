"""
PR 11 das permissões (17/10/2026): uma fonte só para "quem aprova".

Decisões que estes testes travam (plano `plano_PR11_aprovacao_fonte_unica_2026-10-16.md`):

- D1 (06/10): todo o Controle aprova, pelo pacote do perfil CONTROLE (vínculo EQUIPE ou GERENTE na
  gerência CONTROLE). Decide qualquer evento, como o DAT (dúvida 1 do PR 11 = a);
- D3 (06/10): só EQUIPE e GERENTE recebem o pacote;
- saem as duas bases por grupo: o par Controle + Assistente Administrativo e o par Superintendência +
  Gerente. Ficam 3 bases: superuser, gerente da Superintendência por vínculo e a capacidade de aprovar;
- nenhum grupo tem `approve_solicitation` (guarda até o PR 12).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportIndexIssue=false, reportOptionalSubscript=false, reportCallIssue=false

from __future__ import annotations

import json
import typing
from datetime import timedelta
from io import StringIO
from typing import Any

from django.core.cache import cache
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, Gerencia, Solicitacao, Usuario
from apps.core.rbac.policies import (
    CanAccessSolicitationApprovals,
    SolicitationApprovalBasis,
    aprovadora_restrita_a_superintendencia,
    solicitation_approval_basis,
    solicitation_approval_basis_for,
)
from apps.core.services.equipe_gerencia import setor_group_for
from apps.core.services.functional_permissions_seed import FUNCTIONAL_PERMISSIONS_SEED
from apps.core.services.rbac_pacotes import PACOTE
from apps.core.tests.factories import (
    GroupFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    UsuarioFactory,
    com_pacote_do_controle,
    com_pacote_do_dat,
    com_papel,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _cache_limpo():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def g1() -> Gerencia:
    g, _ = Gerencia.objects.get_or_create(nome="SUPERINTENDENCIA", defaults={"nome_setor": "Superintendência"})
    return g


@pytest.fixture
def g27() -> Gerencia:
    g, _ = Gerencia.objects.get_or_create(nome="CONTROLE", defaults={"nome_setor": "Controle"})
    g.perfil = Gerencia.Perfil.CONTROLE
    g.save()
    return g


@pytest.fixture
def root() -> Usuario:
    return UsuarioFactory(superuser=True)


@pytest.fixture(params=["lotacao", "uniao"])
def nos_dois_modos(request, settings) -> str:
    """PR 12: grupo não aprova no corte nem na volta (`RBAC_FONTE=uniao`). No corte o grupo não dá nada de
    qualquer jeito; a prova que importa é a da volta, que soma os grupos de novo."""
    settings.RBAC_FONTE = request.param
    return request.param


def _client(user: Usuario) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _approve(user: Usuario, sol: Solicitacao):
    return _client(user).patch(f"/api/solicitacoes/{sol.id}/approve/", {}, format="json")


def _super_de_outra_gerencia(**extra: Any) -> Solicitacao:
    """SUPER antiga de projeto fora da Superintendência (o caso da dúvida 1)."""
    outra = Gerencia.objects.create(nome=f"GERENCIA VIDAS PR11 {Gerencia.objects.count()}", nome_setor="Vidas")
    return SolicitacaoFactory(projeto=ProjetoFactory(super=True, gerencia=outra), **extra)


def _controle(papel: str = "EQUIPE") -> Usuario:
    user = UsuarioFactory()
    com_pacote_do_controle(user, papel)
    cache.clear()
    return user


def _logs_autoridade(alvo: Usuario) -> list[str]:
    return list(
        AuditLog.objects.filter(
            model_name="Usuario", details__target_user_id=alvo.id, details__has_key="autoridade_aprovacao"
        )
        .order_by("id")
        .values_list("details__autoridade_aprovacao", flat=True)
    )


# ============================================================================
# 5.1 — o Controle aprova pelo vínculo
# ============================================================================


@pytest.mark.parametrize("papel", ["EQUIPE", "GERENTE"])
def test_controle_aprova_pelo_vinculo_qualquer_gerencia(g27, papel):
    """Testes 1 e 2: EQUIPE ou GERENTE no Controle, sem grupo de setor → capacidade_aprovar."""
    user = _controle(papel)
    assert not user.groups.filter(name__in=["Controle", "Assistente Administrativo"]).exists()
    assert solicitation_approval_basis(user) == "capacidade_aprovar"

    sol = _super_de_outra_gerencia()
    resp = _approve(user, sol)
    assert resp.status_code == 200, resp.content
    log = AuditLog.objects.get(model_name="Solicitacao", usuario=user, action=AuditLog.Action.APPROVE)
    assert log.details["autoridade"] == "capacidade_aprovar"


def test_perfil_da_u7_aprova_pela_capacidade(g27):
    """Teste 3: grupos Controle + Assistente Administrativo + EQUIPE no Controle → capacidade_aprovar."""
    user = UsuarioFactory(groups=["Controle", "Assistente Administrativo"], groups__vinculo=False)
    com_pacote_do_controle(user)
    cache.clear()
    assert solicitation_approval_basis(user) == "capacidade_aprovar"


@pytest.mark.usefixtures("nos_dois_modos")
def test_par_controle_sem_vinculo_nao_aprova():
    """Teste 4: o par de grupos sem o vínculo não aprova (PR 11: grupo não aprova)."""
    user = UsuarioFactory(groups=["Controle", "Assistente Administrativo"], groups__vinculo=False)
    assert solicitation_approval_basis(user) is None
    assert _approve(user, _super_de_outra_gerencia()).status_code == 403
    policies = _client(user).get("/api/me/policies/")
    assert policies.status_code == 200
    assert "access_solicitation_approvals" not in policies.json()


@pytest.mark.usefixtures("nos_dois_modos")
def test_par_superintendencia_gerente_sem_vinculo_nao_aprova(g1):
    """Teste 5: o par legado sem GERENTE na g1 não aprova (PR 11: grupo não aprova)."""
    user = UsuarioFactory(groups=["Superintendência", "Gerente"], groups__vinculo=False)
    assert solicitation_approval_basis(user) is None
    sol = SolicitacaoFactory(projeto=ProjetoFactory(super=True, gerencia=g1))
    assert _approve(user, sol).status_code == 403


def test_tres_bases():
    """Teste 6."""
    assert typing.get_args(SolicitationApprovalBasis) == ("superuser", "gerente_superintendencia", "capacidade_aprovar")


def test_pacote_controle_aprova_e_nenhum_grupo_do_seed_aprova():
    """Teste 7 (seed): o guarda até o PR 12."""
    assert "approve_solicitation" in PACOTE["CONTROLE"]
    seed = {item.codename: item.group_names for item in FUNCTIONAL_PERMISSIONS_SEED}
    assert tuple(seed["approve_solicitation"]) == ()


@pytest.mark.migrations
def test_nenhum_grupo_do_banco_aprova(request, grupos_que_aprovam_pos_migrate):
    """Teste 7 (banco): no job migrate-integrity o banco vem da cadeia de migrations.

    Lê os grupos guardados pela fixture de sessão ANTES do seed, que faz `groups.set(())` em
    `approve_solicitation` e apagaria o que uma migration tivesse posto ali.
    """
    if request.config.getoption("nomigrations"):
        pytest.skip("sob --no-migrations o banco não vem da cadeia de migrations")
    assert grupos_que_aprovam_pos_migrate == []


def test_lotar_e_encerrar_equipe_no_controle_audita_a_autoridade(root, g27):
    """Teste 8: pelo form do superusuário, lotar no Controle concede; encerrar revoga."""
    alvo = UsuarioFactory()
    client = _client(root)

    resp = client.patch(
        f"/api/usuarios-admin/{alvo.id}/", {"equipe_administrativa": True, "gerencia_id": g27.id}, format="json"
    )
    assert resp.status_code == 200, resp.content
    assert _logs_autoridade(alvo) == ["concedida"]

    resp = client.patch(f"/api/usuarios-admin/{alvo.id}/", {"equipe_administrativa": False}, format="json")
    assert resp.status_code == 200, resp.content
    assert _logs_autoridade(alvo) == ["concedida", "revogada"]


def test_form_salva_par_superintendencia_gerente_sem_erro_e_sem_conceder(root, django_capture_on_commit_callbacks):
    """Teste 9: inversão do #2071. O par legado já não aprova, então salvar com ele não concede nada."""
    coord, gerente = GroupFactory(name="Coordenador"), GroupFactory(name="Gerente")
    alvo = UsuarioFactory()
    alvo.groups.add(coord, GroupFactory(name="Superintendência"))

    with django_capture_on_commit_callbacks(execute=True):
        resp = _client(root).patch(
            f"/api/usuarios-admin/{alvo.id}/",
            {"first_name": "Novo", "group_ids": [coord.id, gerente.id], "gerencia_id": None},
            format="json",
        )

    assert resp.status_code == 200, resp.content
    cache.clear()
    assert solicitation_approval_basis(alvo) is None
    assert _logs_autoridade(alvo) == []


def test_home_do_controle_conta_super_de_qualquer_gerencia_e_eventos_de_todas(g27, g1):
    """Teste 10."""
    user = _controle()
    _super_de_outra_gerencia()
    SolicitacaoFactory(projeto=ProjetoFactory(super=True, gerencia=g1))
    outra = Gerencia.objects.create(nome="GERENCIA FLUIR PR11", nome_setor="Fluir")
    SolicitacaoFactory(
        projeto=ProjetoFactory(gerencia=outra), status="aprovado", inicio=timezone.now() + timedelta(days=3)
    )

    resp = _client(user).get("/api/stats/home/")
    assert resp.status_code == 200, resp.content
    assert resp.data["pending_approvals"] == 2
    assert resp.data["upcoming_events"] == 1


def test_relatorio_aprovadores_lista_por_base_sem_nomes(g1, g27, root):
    """Teste 11: o retrato "quem aprova" por base, com o DAT e o Controle, só com ids."""
    gerente = UsuarioFactory(first_name="Gina", last_name="Gerente")
    com_papel(gerente, "GERENTE", g1)
    dat = UsuarioFactory(first_name="Dora", last_name="Dat")
    com_pacote_do_dat(dat)
    controle = UsuarioFactory(first_name="Cora", last_name="Controle")
    com_pacote_do_controle(controle)
    inativa = UsuarioFactory(first_name="Ina", is_active=False)
    com_pacote_do_controle(inativa)
    UsuarioFactory(groups=["Controle", "Assistente Administrativo"], groups__vinculo=False)

    out = StringIO()
    call_command("relatorio_aprovadores", "--json", stdout=out)
    dados = json.loads(out.getvalue())

    assert dados["aprovadores_por_base"] == {
        "superuser": [root.id],
        "gerente_superintendencia": [gerente.id],
        "capacidade_aprovar": sorted([dat.id, controle.id]),
    }
    assert dados["inativas_que_aprovariam_se_reativadas"] == [inativa.id]

    texto = StringIO()
    call_command("relatorio_aprovadores", stdout=texto)
    for saida in (out.getvalue(), texto.getvalue()):
        for nome in ("Gina", "Dora", "Cora", "Ina"):
            assert nome not in saida


def test_mensagem_do_403_cita_controle_e_superintendencia():
    """Teste 12 (PA-07)."""
    message = str(CanAccessSolicitationApprovals.message)
    assert "Controle" in message
    assert "Superintendência" in message
    assert "Assistente Administrativo" not in message


# ============================================================================
# 5.2 — regressão
# ============================================================================


@pytest.mark.parametrize("papel", ["COORDENADOR", "APOIO", "FORMADOR"])
def test_coordenador_apoio_formador_no_controle_nao_aprovam(g27, papel):
    user = UsuarioFactory()
    com_papel(user, papel, g27)
    cache.clear()
    assert solicitation_approval_basis(user) is None
    assert _approve(user, _super_de_outra_gerencia()).status_code == 403


def test_controle_nao_aprova_a_propria(g27):
    user = _controle()
    propria = _super_de_outra_gerencia(usuario=user)
    resp = _approve(user, propria)
    assert resp.status_code == 403 and resp.data["code"] == "self_approval_forbidden"
    resp = _client(user).post("/api/solicitacoes/batch-approve/", {"ids": [propria.id]}, format="json")
    assert resp.data["errors"][0]["code"] == "self_approval_forbidden"


@pytest.mark.usefixtures("nos_dois_modos")
def test_grupo_controle_sozinho_nao_aprova():
    user = UsuarioFactory(groups=["Controle"], groups__vinculo=False)
    assert solicitation_approval_basis(user) is None


def test_gerente_g1_e_equipe_no_controle_fora_do_escopo_decide_como_capacidade(g1, g27):
    user = UsuarioFactory()
    com_papel(user, "GERENTE", g1)
    com_pacote_do_controle(user)
    cache.clear()
    fora = _super_de_outra_gerencia()
    assert solicitation_approval_basis(user) == "gerente_superintendencia"
    assert solicitation_approval_basis_for(user, fora) == "capacidade_aprovar"
    assert aprovadora_restrita_a_superintendencia(user) is False


@pytest.mark.parametrize("com_capacidade", [False, True])
@pytest.mark.parametrize("setor", ["Superintendência", "Controle"])
def test_setor_group_for_recusa_setor_reservado(setor, com_capacidade):
    """Guarda `SETORES_RESERVADOS` (1.4): sem ela, o grupo Controle sairia de quem é transferido de gerência."""
    GroupFactory(name=setor)
    gerencia = Gerencia.objects.create(nome=f"RESERVADO {setor} PR11", nome_setor=setor, setor_canonico=setor)
    assert setor_group_for(gerencia, com_capacidade=com_capacidade) is None

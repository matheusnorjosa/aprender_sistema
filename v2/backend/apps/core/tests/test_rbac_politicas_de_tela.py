"""
PR 7 das permissões (15/10/2026): o front decide menu, rotas e botões só por `/api/me/policies/`.

Cinco policies entram em `PUBLIC_POLICY_KEYS` sem mudar poder:

- três COMPOSTAS, cópia da fórmula que o front aplicava em `usePermissions.ts` sobre o payload
  de `/api/me/`: `access_monthly_availability` (Grade), `access_availability_blocks` (Bloqueios)
  e `access_travel` (Deslocamentos). Cada uma = `view_all_availability` OU grupo listado OU
  vínculo de gestão (GERENTE/COORDENADOR/APOIO) vigente em gerência ativa;
- duas SIMPLES, a capacidade de mesmo nome: `execute_restricted_operations` (excluir plano) e
  `create_solicitation_without_purchase` (Nova Solicitação sem compra).

O teste central compara, pessoa a pessoa, a policy com a fórmula antiga do front avaliada sobre
as respostas REAIS de `/api/me/` e `/api/me/policies/`. Pessoas: os 10 atores de `matrix.py`
(com os vínculos da matriz viva), os mesmos grupos sem vínculo, só vínculo (cada papel) e as duas
personas por pacote do perfil da gerência ("Ana" ≡ DAT, "Bruno" ≡ Controle).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import Any

from django.core.cache import cache
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APIClient

import pytest

from apps.core.models import EquipeGerencia, Gerencia, Usuario
from apps.core.rbac import policies as modulo_policies
from apps.core.rbac.matrix import ACTOR_GROUPS, ACTORS, SUPERUSER
from apps.core.rbac.policies import PUBLIC_POLICY_KEYS, resolve_public_policies
from apps.core.services.rbac_snapshot import diff_snapshots, snapshot_de_poder
from apps.core.tests.factories import UsuarioFactory
from apps.core.tests.test_rbac_matrix_living import _make_user_for_actor

pytestmark = pytest.mark.django_db

COMPOSTAS = ("access_monthly_availability", "access_availability_blocks", "access_travel")
SIMPLES = ("execute_restricted_operations", "create_solicitation_without_purchase")
NOVAS = COMPOSTAS + SIMPLES

# Policies que o menu, as rotas e a Página Inicial leem (AppSidebar, AppRoutes, HomePage).
CHAVES_DE_TELA = frozenset(
    {
        "access_availability_blocks",
        "access_controle_section",
        "access_monthly_availability",
        "access_solicitation_approvals",
        "access_travel",
        "create_solicitation",
        "manage_admin_registries",
        "manage_internal_actions",
        "publish_setor_solicitacao",
        "view_compras_dashboard",
        "view_compras_stats",
        "view_gcal_dashboard",
        "view_map_metrics",
        "view_overview_dashboard",
        "view_team_dashboard",
    }
)

_PAPEIS_DE_GESTAO = {"GERENTE", "COORDENADOR", "APOIO"}


@pytest.fixture(autouse=True)
def _cache_limpo():
    cache.clear()
    yield
    cache.clear()


def _me(usuario: Usuario) -> tuple[dict[str, Any], list[str]]:
    """As duas respostas que o front recebe."""
    cache.clear()
    client = APIClient()
    client.force_authenticate(user=usuario)
    me = client.get(reverse("core:current-user")).json()
    policies = client.get(reverse("core:me-policies")).json()
    return me, policies


def _formula_antiga_do_front(me: dict[str, Any], policies: list[str]) -> dict[str, bool]:
    """`usePermissions.ts` + `useCanAccess.ts` + gates de AppRoutes/AppSidebar/páginas, antes do PR 7."""
    su = me["is_superuser"] is True
    setores = set(me["setores"])
    funcoes = set(me["funcoes"])
    gestor_por_vinculo = any(p in _PAPEIS_DE_GESTAO for g in me["gerencias"] for p in g["papeis"])
    vaa = "view_all_availability" in policies

    is_coordenador = "Coordenador" in funcoes or "Apoio de Coordenação" in funcoes
    can_coordenador = su or is_coordenador or "DAT" in setores
    can_controle = su or "Controle" in setores
    can_dat = su or "DAT" in setores
    can_disponibilidade = (
        su or "Controle" in setores or "DAT" in setores or "Gerente" in funcoes or is_coordenador or gestor_por_vinculo
    )
    return {
        "access_monthly_availability": vaa or can_disponibilidade,
        "access_availability_blocks": vaa
        or can_controle
        or can_coordenador
        or "Formador" in funcoes
        or gestor_por_vinculo,
        "access_travel": vaa or can_controle or can_coordenador or can_dat or gestor_por_vinculo,
        # PlanoFormacoesPage: isAdmin || inSuperintendencia.
        "execute_restricted_operations": su or "Superintendência" in setores,
        # NewSolicitacaoWizard: isAdmin.
        "create_solicitation_without_purchase": su,
    }


# ----------------------------------------------------------------------------
# Pessoas
# ----------------------------------------------------------------------------


def _gerencia(nome: str, perfil: str = Gerencia.Perfil.PADRAO, ativo: bool = True) -> Gerencia:
    g, _ = Gerencia.objects.get_or_create(nome=nome, defaults={"nome_setor": nome.title()})
    g.perfil = perfil
    g.ativo = ativo
    g.save()
    return g


def _vincula(usuario: Usuario, gerencia: Gerencia, papel: str, **extra: Any) -> None:
    extra.setdefault("ativo", True)
    if papel == "APOIO":
        supervisor = UsuarioFactory()
        EquipeGerencia.objects.create(usuario=supervisor, gerencia=gerencia, papel="COORDENADOR", ativo=True)
        extra["coordenador_supervisor"] = supervisor
    EquipeGerencia.objects.create(usuario=usuario, gerencia=gerencia, papel=papel, **extra)


def _so_vinculo(papel: str, **gerencia: Any) -> Callable[[], Usuario]:
    def criar() -> Usuario:
        usuario = UsuarioFactory()
        _vincula(usuario, _gerencia(f"GERENCIA TELA {papel}", **gerencia), papel)
        return usuario

    return criar


def _vinculo_gerente_fora_de_vigencia(**vinculo: Any) -> Callable[[], Usuario]:
    """Vínculo GERENTE em gerência ativa, mas vencido ou desligado: não dá escopo nem tela."""

    def criar() -> Usuario:
        usuario = UsuarioFactory()
        _vincula(usuario, _gerencia("GERENCIA TELA VIGENCIA"), "GERENTE", **vinculo)
        return usuario

    return criar


def _ana() -> Usuario:
    """EQUIPE na gerência do DAT (perfil ADMIN_OPERACIONAL), sem grupo."""
    usuario = UsuarioFactory()
    _vincula(usuario, _gerencia("GERENCIA DAT", Gerencia.Perfil.ADMIN_OPERACIONAL), "EQUIPE")
    return usuario


def _bruno() -> Usuario:
    """EQUIPE na gerência do Controle (perfil CONTROLE), sem grupo."""
    usuario = UsuarioFactory()
    _vincula(usuario, _gerencia("CONTROLE", Gerencia.Perfil.CONTROLE), "EQUIPE")
    return usuario


def _so_grupos(ator: str) -> Callable[[], Usuario]:
    return lambda: UsuarioFactory(groups=ACTOR_GROUPS[ator])


PESSOAS: dict[str, Callable[[], Usuario]] = {
    **{f"matriz: {ator}": (lambda a=ator: _make_user_for_actor(a)) for ator in ACTORS},
    **{f"só grupos: {ator}": _so_grupos(ator) for ator in ACTORS if ator != SUPERUSER},
    "só vínculo GERENTE": _so_vinculo("GERENTE"),
    "só vínculo COORDENADOR": _so_vinculo("COORDENADOR"),
    "só vínculo APOIO": _so_vinculo("APOIO"),
    "só vínculo FORMADOR": _so_vinculo("FORMADOR"),
    "só vínculo EQUIPE": _so_vinculo("EQUIPE"),
    "vínculo GERENTE em gerência inativa": _so_vinculo("GERENTE", ativo=False),
    "vínculo GERENTE vencido": _vinculo_gerente_fora_de_vigencia(
        valid_from=timezone.localdate() - timedelta(days=60), valid_to=timezone.localdate() - timedelta(days=1)
    ),
    "vínculo GERENTE desligado (ativo=False)": _vinculo_gerente_fora_de_vigencia(ativo=False),
    "só setor Vidas": lambda: UsuarioFactory(groups=["Vidas"]),
    "só setor Superintendência": lambda: UsuarioFactory(groups=["Superintendência"]),
    "só função Assistente Administrativo": lambda: UsuarioFactory(groups=["Assistente Administrativo"]),
    "Vidas + Assistente Administrativo": lambda: UsuarioFactory(groups=["Vidas", "Assistente Administrativo"]),
    "Ana (EQUIPE no ADMIN_OPERACIONAL)": _ana,
    "Bruno (EQUIPE no CONTROLE)": _bruno,
    "sem nada": lambda: UsuarioFactory(),
}


# ----------------------------------------------------------------------------
# Testes
# ----------------------------------------------------------------------------


class TestPoliciesNovas:
    def test_as_cinco_sao_publicas(self):
        assert set(NOVAS) <= PUBLIC_POLICY_KEYS

    @pytest.mark.parametrize("pessoa", list(PESSOAS))
    def test_cada_policy_vale_sse_a_formula_antiga_do_front_vale(self, pessoa):
        me, policies = _me(PESSOAS[pessoa]())
        esperado = _formula_antiga_do_front(me, policies)
        obtido = {chave: chave in policies for chave in NOVAS}
        assert obtido == esperado, f"{pessoa}: /me={me['setores']}/{me['funcoes']}/{me['gerencias']}"

    def test_superusuario_recebe_todas(self):
        _, policies = _me(UsuarioFactory(superuser=True))
        assert policies == sorted(PUBLIC_POLICY_KEYS)
        assert set(NOVAS) <= set(policies)

    def test_cada_composta_tem_quem_ganha_e_quem_perde(self):
        """Anti-vacuidade: a comparação acima não pode passar com tudo True ou tudo False."""
        resultados = {pessoa: set(_me(criar())[1]) for pessoa, criar in PESSOAS.items()}
        for chave in NOVAS:
            com = [p for p, pol in resultados.items() if chave in pol]
            sem = [p for p, pol in resultados.items() if chave not in pol]
            assert com and sem, f"{chave}: com={com} sem={sem}"


class TestRbacDiffDoDeploy:
    """O que `rbac_diff --comparar` mostra depois do deploy deste PR (DEPLOY_CHECKLIST §8, D22)."""

    def test_so_ganha_policies_das_cinco_chaves(self, monkeypatch):
        for criar in PESSOAS.values():
            criar()
        monkeypatch.setattr(modulo_policies, "PUBLIC_POLICY_KEYS", PUBLIC_POLICY_KEYS - set(NOVAS))
        antes = snapshot_de_poder()
        monkeypatch.undo()
        diff = diff_snapshots(antes, snapshot_de_poder())

        assert diff["resumo"]["perdas"] == 0
        assert diff["resumo"]["ganhos"] > 0
        assert not diff["entram"] and not diff["saem"]
        for pessoa, mudancas in diff["pessoas"].items():
            assert set(mudancas) == {"policies"}, f"{pessoa}: {mudancas}"
            assert set(mudancas["policies"]["ganha"]) <= set(NOVAS), f"{pessoa}: {mudancas}"


class TestPersonasPorPacote:
    """Quem trabalha numa gerência com perfil vê as mesmas telas de quem tem o grupo."""

    @pytest.mark.parametrize(
        ("persona", "ator"),
        [(_ana, "DAT"), (_bruno, "Controle")],
        ids=["Ana ≡ DAT", "Bruno ≡ Controle"],
    )
    def test_mesmas_policies_de_tela_que_o_grupo(self, persona, ator):
        _, da_persona = _me(persona())
        _, do_grupo = _me(UsuarioFactory(groups=ACTOR_GROUPS[ator]))
        assert set(COMPOSTAS) <= set(da_persona), "Grade, Bloqueios e Deslocamentos vêm pela policy"
        assert set(da_persona) & CHAVES_DE_TELA == set(do_grupo) & CHAVES_DE_TELA

    def test_ana_nao_herda_o_que_e_tecnico(self):
        """O pacote do ADMIN_OPERACIONAL não tem `import_spreadsheet`: as policies de tela batem, as de import não."""
        assert "import_generic_spreadsheet" not in resolve_public_policies(_ana())


# ----------------------------------------------------------------------------
# Telas que trocaram a regra por uma policy que já existia: o delta é medido e fica escrito
# ----------------------------------------------------------------------------


def _gates_antigos(me: dict[str, Any], policies: list[str]) -> dict[str, bool]:
    """AppRoutes, PreAgendaPage e App.tsx antes do PR 7 (flags de `usePermissions.ts` sobre o /me)."""
    su = me["is_superuser"] is True
    setores = set(me["setores"])
    funcoes = set(me["funcoes"])
    can_controle = su or "Controle" in setores
    can_dat = su or "DAT" in setores
    can_coordenador = su or "Coordenador" in funcoes or "Apoio de Coordenação" in funcoes or "DAT" in setores
    can_see_all_sectors = su or me["is_superintendencia"] is True or "Superintendência" in setores
    rota_pre_agenda = "access_controle_section" in policies  # a rota não mudou
    return {
        "rota Compras": can_controle or can_dat,
        "rota Editar solicitação": can_coordenador
        or me["can_approve_super"] is True
        or "create_solicitation" in policies,
        "cartão do Google na Pré-agenda": rota_pre_agenda and (can_controle or can_see_all_sectors),
        "consulta periódica ao Google": can_controle,
    }


def _gates_novos(policies: list[str]) -> dict[str, bool]:
    """Os mesmos pontos depois do PR 7: só policy."""
    tem = set(policies)
    return {
        "rota Compras": "view_compras_stats" in tem,
        "rota Editar solicitação": bool(
            tem & {"create_solicitation", "access_solicitation_approvals", "manage_admin_registries"}
        ),
        "cartão do Google na Pré-agenda": "access_controle_section" in tem,
        "consulta periódica ao Google": "access_controle_section" in tem,
    }


# Quem passa a ver o quê (antes → depois). Fora das exceções E1–E3 da Página Inicial: vai na
# direção do backend (as APIs já autorizavam essas pessoas), mas é poder novo no front e está
# escrito na D22 para o dono aprovar. Qualquer outra diferença reprova.
_COMPRAS_E_GOOGLE: dict[str, tuple[bool, bool]] = {
    "rota Compras": (False, True),
    "cartão do Google na Pré-agenda": (False, True),
    "consulta periódica ao Google": (False, True),
}
DELTA_MEDIDO: dict[str, dict[str, tuple[bool, bool]]] = {
    # view_compras_stats e access_controle_section vêm da função, sem o setor Controle.
    "só função Assistente Administrativo": _COMPRAS_E_GOOGLE,
    "Vidas + Assistente Administrativo": _COMPRAS_E_GOOGLE,
    # O pacote do perfil CONTROLE dá as capacidades do Controle; o front lia o setor.
    "Bruno (EQUIPE no CONTROLE)": _COMPRAS_E_GOOGLE,
    # O pacote do ADMIN_OPERACIONAL dá as capacidades do DAT; o front lia o setor.
    "Ana (EQUIPE no ADMIN_OPERACIONAL)": {"rota Compras": (False, True), "rota Editar solicitação": (False, True)},
}


class TestDeltaDasTelasQueTrocaramDeRegra:
    def test_so_as_pessoas_e_telas_listadas_mudam(self):
        delta: dict[str, dict[str, tuple[bool, bool]]] = {}
        for pessoa, criar in PESSOAS.items():
            me, policies = _me(criar())
            antes, depois = _gates_antigos(me, policies), _gates_novos(policies)
            mudou = {gate: (antes[gate], depois[gate]) for gate in antes if antes[gate] != depois[gate]}
            if mudou:
                delta[pessoa] = mudou
        assert delta == DELTA_MEDIDO

    def test_os_dez_atores_da_matriz_nao_mudam(self):
        assert not [p for p in DELTA_MEDIDO if p.startswith("matriz: ")]

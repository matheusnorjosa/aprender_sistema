"""
PR 7 das permissões (15/10/2026): o front decide menu, rotas e botões só por `/api/me/policies/`.

Cinco policies entram em `PUBLIC_POLICY_KEYS` sem mudar poder:

- três COMPOSTAS, cópia da fórmula que o front aplicava em `usePermissions.ts` sobre o payload
  de `/api/me/`: `access_monthly_availability` (Grade), `access_availability_blocks` (Bloqueios)
  e `access_travel` (Deslocamentos). Cada uma = `view_all_availability` OU grupo listado OU
  vínculo de gestão (GERENTE/COORDENADOR/APOIO) vigente em gerência ativa. Desde o PR 8 das
  permissões a função saiu da fórmula: setor Controle/DAT OU papel vigente (`me.gerencias`), com
  FORMADOR também na tela Bloqueios;
- duas SIMPLES, a capacidade de mesmo nome: `execute_restricted_operations` (excluir plano) e
  `create_solicitation_without_purchase` (Nova Solicitação sem compra).

O teste central compara, pessoa a pessoa, a policy com a fórmula avaliada sobre as respostas
REAIS de `/api/me/` e `/api/me/policies/` (a do PR 8: setor ou papel, sem a função). Pessoas: os 10 atores de `matrix.py`
(com os vínculos da matriz viva), os mesmos grupos sem vínculo, só vínculo (cada papel) e as duas
personas por pacote do perfil da gerência ("Ana" ≡ DAT, "Bruno" ≡ Controle), mais o vínculo
GERENTE (o outro papel com pacote) no ADMIN_OPERACIONAL, no CONTROLE e na DIRETORIA.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import Any

from django.contrib.auth.models import Group
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import EquipeGerencia, Gerencia, PermissaoFuncional, Usuario
from apps.core.rbac import policies as modulo_policies
from apps.core.rbac.matrix import ACTOR_GROUPS, ACTORS, SUPERUSER
from apps.core.rbac.policies import PUBLIC_POLICY_KEYS, resolve_public_policies
from apps.core.services.rbac_snapshot import diff_snapshots, snapshot_de_poder
from apps.core.tests.factories import PACOTE_DO_GRUPO_DE_SETOR, UsuarioFactory
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
# PR 8: papéis que abrem cada tela composta (`policies.TELAS_DE_ESCOPO`), lidos de `me.gerencias`.
_PAPEIS_DA_TELA = {
    "access_monthly_availability": _PAPEIS_DE_GESTAO,
    "access_availability_blocks": _PAPEIS_DE_GESTAO | {"FORMADOR"},
    "access_travel": _PAPEIS_DE_GESTAO,
}


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


def _formula_do_front_sobre_o_me(me: dict[str, Any], policies: list[str]) -> dict[str, bool]:
    """Fórmula das telas sobre o `/api/me/` desde o PR 8: superusuário, `view_all_availability`,
    setor Controle/DAT ou papel vigente em `me.gerencias` (a função não entra mais)."""
    su = me["is_superuser"] is True
    setores = set(me["setores"])
    papeis = {p for g in me["gerencias"] for p in g["papeis"]}
    vaa = "view_all_availability" in policies
    base = su or vaa or bool(setores & {"Controle", "DAT"})
    compostas = {chave: base or bool(papeis & _PAPEIS_DA_TELA[chave]) for chave in COMPOSTAS}
    return {
        **compostas,
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


def _gerente_com_pacote(nome: str, perfil: str) -> Callable[[], Usuario]:
    """GERENTE (papel com pacote, como EQUIPE) numa gerência com perfil, sem grupo."""

    def criar() -> Usuario:
        usuario = UsuarioFactory()
        _vincula(usuario, _gerencia(nome, perfil), "GERENTE")
        return usuario

    return criar


def _so_grupos(ator: str) -> Callable[[], Usuario]:
    """Os grupos do ator: o de função com o papel (#2111), o de setor com pacote sem o vínculo (PR 12a)."""

    def criar() -> Usuario:
        grupos = ACTOR_GROUPS[ator]
        usuario = UsuarioFactory(groups=[g for g in grupos if g not in PACOTE_DO_GRUPO_DE_SETOR])
        for nome in grupos:
            if nome in PACOTE_DO_GRUPO_DE_SETOR:
                usuario.groups.add(Group.objects.get_or_create(name=nome)[0])
        return usuario

    return criar


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
    "GERENTE no ADMIN_OPERACIONAL": _gerente_com_pacote("GERENCIA DAT", Gerencia.Perfil.ADMIN_OPERACIONAL),
    "GERENTE no CONTROLE": _gerente_com_pacote("CONTROLE", Gerencia.Perfil.CONTROLE),
    "GERENTE na DIRETORIA": _gerente_com_pacote("DIRETORIA", Gerencia.Perfil.DIRETORIA),
    "sem nada": lambda: UsuarioFactory(),
}


# ----------------------------------------------------------------------------
# Testes
# ----------------------------------------------------------------------------


# PR 10 (16/10/2026): o pacote ADMIN_OPERACIONAL final dá ao DAT excluir e criar sem compra, e o grupo
# Superintendência perdeu as capacidades (migration 0126). As duas policies SIMPLES deixam de bater
# com a fórmula antiga do front nestas pessoas, e só nelas (decisão do dono, lista do PR 10).
DELTA_PR10: dict[str, dict[str, bool]] = {
    # O ator DAT da matriz viva tem o vínculo EQUIPE na gerência DAT desde o PR 10, como em produção.
    "matriz: DAT": {"execute_restricted_operations": True, "create_solicitation_without_purchase": True},
    "matriz: Gerente da Superintendência": {"execute_restricted_operations": False},
    "só grupos: Gerente da Superintendência": {"execute_restricted_operations": False},
    "só setor Superintendência": {"execute_restricted_operations": False},
    "Ana (EQUIPE no ADMIN_OPERACIONAL)": {
        "execute_restricted_operations": True,
        "create_solicitation_without_purchase": True,
    },
    "GERENTE no ADMIN_OPERACIONAL": {
        "execute_restricted_operations": True,
        "create_solicitation_without_purchase": True,
    },
}


@pytest.mark.usefixtures("modo_uniao")  # fórmula do front sobre grupo e vínculo (PR 7/10): modo soma (PR 12)
class TestPoliciesNovas:
    def test_as_cinco_sao_publicas(self):
        assert set(NOVAS) <= PUBLIC_POLICY_KEYS

    @pytest.mark.parametrize("pessoa", list(PESSOAS))
    def test_cada_policy_vale_sse_a_formula_sobre_o_me_vale(self, pessoa):
        me, policies = _me(PESSOAS[pessoa]())
        esperado = {**_formula_do_front_sobre_o_me(me, policies), **DELTA_PR10.get(pessoa, {})}
        obtido = {chave: chave in policies for chave in NOVAS}
        assert obtido == esperado, f"{pessoa}: /me={me['setores']}/{me['funcoes']}/{me['gerencias']}"

    @pytest.mark.parametrize("setor", ["DAT", "Controle"])
    def test_so_o_setor_abre_as_compostas_sem_view_all_availability(self, setor):
        """No seed todo DAT/Controle tem `view_all_availability`; sem ela, só o setor decide (fórmula antiga)."""
        PermissaoFuncional.objects.get(codename="view_all_availability").groups.remove(Group.objects.get(name=setor))
        usuario = UsuarioFactory(groups=[setor], groups__vinculo=False)
        me, policies = _me(usuario)
        assert "view_all_availability" not in policies, "pré-condição: o setor é o único caminho"
        assert set(COMPOSTAS) <= set(policies)
        assert {chave: chave in policies for chave in NOVAS} == _formula_do_front_sobre_o_me(me, policies)
        # O simulador `rbac_diff` (capacidades sem view_all_availability) chega ao mesmo resultado.
        assert snapshot_de_poder(Usuario.objects.filter(id=usuario.id))[f"u{usuario.id}"]["policies"] == policies

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

    @pytest.mark.parametrize("pessoa", list(PESSOAS))
    def test_policies_do_retrato_sao_as_da_api(self, pessoa):
        """O simulador calcula as policies pelas capacidades que recebe; o resultado é o de /api/me/policies/."""
        usuario = PESSOAS[pessoa]()
        _, da_api = _me(usuario)
        retrato = snapshot_de_poder(Usuario.objects.filter(id=usuario.id))[f"u{usuario.id}"]
        assert retrato["policies"] == da_api, pessoa


# Telas que o pacote final do PR 10 abre ao DAT e o grupo DAT sozinho não abre.
PR10_TELAS_DO_DAT = {"access_solicitation_approvals", "create_solicitation", "access_controle_section"}
# PR 11 (D1): o pacote CONTROLE aprova; o grupo Controle sozinho não.
PR11_TELAS_DO_CONTROLE = {"access_solicitation_approvals"}


@pytest.mark.usefixtures("modo_uniao")  # fórmula do front sobre grupo e vínculo (PR 7/10): modo soma (PR 12)
class TestPersonasPorPacote:
    """Quem trabalha numa gerência com perfil vê as mesmas telas de quem tem o grupo."""

    @pytest.mark.parametrize(
        ("persona", "ator"),
        [(_ana, "DAT"), (_bruno, "Controle")],
        ids=["Ana ≡ DAT", "Bruno ≡ Controle"],
    )
    def test_mesmas_policies_de_tela_que_o_grupo(self, persona, ator):
        _, da_persona = _me(persona())
        _, do_grupo = _me(UsuarioFactory(groups=ACTOR_GROUPS[ator], groups__vinculo=False))
        assert set(COMPOSTAS) <= set(da_persona), "Grade, Bloqueios e Deslocamentos vêm pela policy"
        # PR 10: o pacote do DAT é o final; o grupo DAT sozinho não aprova, não cria nem abre o Controle.
        # PR 11: o pacote do Controle aprova; o grupo Controle sozinho não.
        a_mais = PR10_TELAS_DO_DAT if ator == "DAT" else PR11_TELAS_DO_CONTROLE
        assert set(da_persona) & CHAVES_DE_TELA == (set(do_grupo) & CHAVES_DE_TELA) | a_mais

    def test_ana_nao_herda_o_que_e_tecnico(self):
        """O pacote do ADMIN_OPERACIONAL não tem `import_spreadsheet` (a capacidade técnica).

        PR 10: `import_generic_spreadsheet` vem agora pelo `run_daily_operations` do pacote final.
        """
        from apps.core.services.rbac_permissions import get_user_functional_permissions

        assert "import_spreadsheet" not in get_user_functional_permissions(_ana())
        assert "import_generic_spreadsheet" in resolve_public_policies(_ana())


# ----------------------------------------------------------------------------
# Telas que trocaram a regra por uma policy que já existia: o delta é medido e fica escrito
# ----------------------------------------------------------------------------


def _gates_antigos(me: dict[str, Any], policies: list[str]) -> dict[str, bool]:
    """AppRoutes, PreAgendaPage, DeslocamentosPage e App.tsx antes do PR 7 (flags de `usePermissions.ts` sobre o /me)."""
    su = me["is_superuser"] is True
    setores = set(me["setores"])
    funcoes = set(me["funcoes"])
    can_controle = su or "Controle" in setores
    can_dat = su or "DAT" in setores
    can_coordenador = su or "Coordenador" in funcoes or "Apoio de Coordenação" in funcoes or "DAT" in setores
    can_see_all_sectors = su or me["is_superintendencia"] is True or "Superintendência" in setores
    gestor_por_vinculo = any(p in _PAPEIS_DE_GESTAO for g in me["gerencias"] for p in g["papeis"])
    rota_pre_agenda = "access_controle_section" in policies  # a rota não mudou
    # A rota aceitava view_all_availability; o check da própria página não (dava "Sem permissão").
    deslocamentos = can_controle or can_coordenador or can_dat or gestor_por_vinculo
    rota_deslocamentos = "view_all_availability" in policies or deslocamentos
    pagina_deslocamentos = deslocamentos or "Superintendência" in setores
    return {
        "tela Deslocamentos (página)": rota_deslocamentos and pagina_deslocamentos,
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
        "tela Deslocamentos (página)": "access_travel" in tem,
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
    # PR 8: a função Assistente Administrativo sem o setor Controle não tem mais capacidade (O8-6),
    # então "só função Assistente Administrativo" e "Vidas + Assistente Administrativo" saíram daqui.
    # O pacote do perfil CONTROLE dá as capacidades do Controle; o front lia o setor.
    # Deslocamentos: a rota abria por view_all_availability, a página respondia "Sem permissão".
    "Bruno (EQUIPE no CONTROLE)": {**_COMPRAS_E_GOOGLE, "tela Deslocamentos (página)": (False, True)},
    # O pacote do ADMIN_OPERACIONAL dá as capacidades do DAT; o front lia o setor. Desde o PR 10 o
    # pacote final dá `create_solicitation` (o gate antigo de Editar já lia: sem delta) e
    # `operate_preagenda`, que abre a seção Controle (cartão e consulta do Google).
    "Ana (EQUIPE no ADMIN_OPERACIONAL)": {**_COMPRAS_E_GOOGLE, "tela Deslocamentos (página)": (False, True)},
    # GERENTE também está em PAPEIS_COM_PACOTE: ganha o mesmo pacote que EQUIPE. Deslocamentos
    # não muda porque o vínculo de gestão já abria a página antes. Editar solicitação também não:
    # desde o PR 8 o papel GERENTE dá `create_solicitation`, que o gate antigo já lia.
    "GERENTE no CONTROLE": _COMPRAS_E_GOOGLE,
    "GERENTE no ADMIN_OPERACIONAL": _COMPRAS_E_GOOGLE,
    # PR 10: o ator DAT (grupo + vínculo EQUIPE na gerência DAT) abre a seção Controle pelo pacote final.
    "matriz: DAT": {
        "cartão do Google na Pré-agenda": (False, True),
        "consulta periódica ao Google": (False, True),
    },
}


@pytest.mark.usefixtures("modo_uniao")  # fórmula do front sobre grupo e vínculo (PR 7/10): modo soma (PR 12)
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
        """Só o DAT muda, e pelo PR 10 (pacote final), não pela troca de regra das telas do PR 7."""
        assert [p for p in DELTA_MEDIDO if p.startswith("matriz: ")] == ["matriz: DAT"]

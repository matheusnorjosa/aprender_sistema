"""
Tests RBAC do endpoint /api/stats/home/ — Onda 2A: #1284 + #1260.

Cobre dois fixes coesos no mesmo arquivo (`apps/core/views/stats.py`):

1. **#1284 (P0) — fail-safe scope em upcoming_events**
   - Antes: `else` implícito permitia que user sem capability global, não-Formador-puro
     e sem `EquipeGerencia` visse TODOS os eventos aprovados nacionais.
   - Depois: `else: upcoming_qs.none()` explícito.

2. **#1260 — remover hardcode de strings de grupo**
   - Antes: `"DAT" in user_groups`, `"Superintendência" in user_groups`, etc.
   - Depois: `user_has_any_perm(user, "<codename>")` (capability-driven).

Capability mapping aplicado:
- `manage_admin_registries` → DAT (validar/suportar — ator transversal)
- `approve_solicitation` → Superintendência (decisão cross-org de aprovação)
- `create_solicitation` → Coordenador, Apoio de Coordenação, Gerente

Formador é a única função sem capability (acessa só /meus-eventos via
`IsAuthenticated`); detecção via grupo aqui é data-scope, whitelisted no
rbac_lint via `# noqa: RBAC-data-scope-allowed`.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false, reportPrivateUsage=false

from __future__ import annotations

from django.contrib.auth.models import Group
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import (
    EquipeGerencia,
    Gerencia,
    Municipio,
    Participation,
    Projeto,
    Solicitacao,
    TipoEvento,
    Usuario,
)

pytestmark = pytest.mark.django_db


_USER_COUNTER = {"i": 0}
_CPF_COUNTER = {"i": 0}


def _next_cpf() -> str:
    _CPF_COUNTER["i"] += 1
    return f"77766{_CPF_COUNTER['i']:06d}"


def _next_username(prefix: str) -> str:
    _USER_COUNTER["i"] += 1
    return f"{prefix}_{_USER_COUNTER['i']}"


def _make_user(prefix: str, group_names: list[str], is_superuser: bool = False) -> Usuario:
    username = _next_username(prefix)
    user = Usuario.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="testpass123",
        cpf=_next_cpf(),
    )
    if is_superuser:
        user.is_superuser = True
        user.is_staff = True
        user.save(update_fields=["is_superuser", "is_staff"])
    for gname in group_names:
        group, _ = Group.objects.get_or_create(name=gname)
        user.groups.add(group)
    return user


def _make_gerencia(nome: str, setor: str) -> Gerencia:
    return Gerencia.objects.create(nome=nome, nome_setor=setor, ativo=True)


def _link_to_gerencia(
    user: Usuario,
    gerencia: Gerencia,
    papel: str,
    supervisor: Usuario | None = None,
) -> EquipeGerencia:
    """Cria EquipeGerencia. APOIO exige `supervisor` (constraint `apoio_requires_supervisor`)."""
    kwargs = {
        "usuario": user,
        "gerencia": gerencia,
        "papel": papel,
        "ativo": True,
    }
    if papel == "APOIO":
        if supervisor is None:
            raise ValueError("APOIO requer supervisor (constraint apoio_requires_supervisor)")
        kwargs["coordenador_supervisor"] = supervisor
    return EquipeGerencia.objects.create(**kwargs)


def _make_projeto(nome: str, gerencia: Gerencia, fluxo: str = "NAO_SUPER") -> Projeto:
    return Projeto.objects.create(nome=nome, codigo=nome[:20], fluxo=fluxo, ativo=True, gerencia=gerencia)


def _make_solicitacao(
    *,
    usuario: Usuario,
    projeto: Projeto,
    municipio: Municipio,
    tipo_evento: TipoEvento,
    status: str = "aprovado",
    days_ahead: int = 7,
) -> Solicitacao:
    inicio = timezone.now() + timezone.timedelta(days=days_ahead)
    return Solicitacao.objects.create(
        usuario=usuario,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo_evento,
        inicio=inicio,
        fim=inicio + timezone.timedelta(hours=2),
        status=status,
    )


@pytest.fixture(autouse=True)
def _clear_rbac_cache(db):
    """RBAC checks cacheiam permissões por user; limpar entre testes."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def world():
    """Mundo compartilhado: 2 gerências, projetos, eventos aprovados em cada."""
    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    tipo_evento = TipoEvento.objects.create(nome="Formação")

    g1 = _make_gerencia("GERENCIA 2", "Vidas")
    g2 = _make_gerencia("GERENCIA 3", "Fluir")

    p1 = _make_projeto("Projeto Vidas A", g1)
    p2 = _make_projeto("Projeto Fluir A", g2)

    # Criador genérico (Coordenador) para ser dono das solicitações
    autor = _make_user("autor", ["Coordenador"])
    _link_to_gerencia(autor, g1, "COORDENADOR")  # autor pertence a G1

    # 2 eventos futuros aprovados em cada gerência
    sol_g1_a = _make_solicitacao(usuario=autor, projeto=p1, municipio=municipio, tipo_evento=tipo_evento, days_ahead=5)
    sol_g1_b = _make_solicitacao(usuario=autor, projeto=p1, municipio=municipio, tipo_evento=tipo_evento, days_ahead=10)
    sol_g2_a = _make_solicitacao(usuario=autor, projeto=p2, municipio=municipio, tipo_evento=tipo_evento, days_ahead=5)
    sol_g2_b = _make_solicitacao(usuario=autor, projeto=p2, municipio=municipio, tipo_evento=tipo_evento, days_ahead=10)

    return {
        "municipio": municipio,
        "tipo_evento": tipo_evento,
        "g1": g1,
        "g2": g2,
        "p1": p1,
        "p2": p2,
        "autor": autor,
        "events_g1": [sol_g1_a, sol_g1_b],
        "events_g2": [sol_g2_a, sol_g2_b],
        "total_events": 4,
    }


def _get_home_stats(user: Usuario):
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/api/stats/home/")
    return response


# ============================================================================
# #1284 (P0) — Fail-safe scope: usuário sem vínculo NÃO vaza eventos globais
# ============================================================================


class TestFailSafeScope:
    """Cenários que ANTES vazavam todos os eventos aprovados (P0)."""

    def test_apoio_sem_equipegerencia_nao_ve_eventos_globais(self, world):
        """Apoio de Coordenação SEM EquipeGerencia → fail-safe → 0 eventos."""
        user = _make_user("apoio", ["Apoio de Coordenação"])
        # NÃO vinculado a nenhuma EquipeGerencia → user_gerencias = []
        response = _get_home_stats(user)
        assert response.status_code == 200
        assert (
            response.json()["upcoming_events"] == 0
        ), "Apoio sem EquipeGerencia NÃO pode ver eventos globais — fail-safe."

    def test_gerente_sem_equipegerencia_nao_ve_eventos_globais(self, world):
        """Gerente SEM EquipeGerencia → fail-safe → 0 eventos."""
        user = _make_user("gerente", ["Gerente"])
        response = _get_home_stats(user)
        assert response.status_code == 200
        assert (
            response.json()["upcoming_events"] == 0
        ), "Gerente sem EquipeGerencia NÃO pode ver eventos globais — fail-safe."

    def test_coordenador_sem_equipegerencia_nao_ve_eventos_globais(self, world):
        """Coordenador SEM EquipeGerencia → fail-safe → 0 eventos."""
        user = _make_user("coord", ["Coordenador"])
        response = _get_home_stats(user)
        assert response.status_code == 200
        assert (
            response.json()["upcoming_events"] == 0
        ), "Coordenador sem EquipeGerencia NÃO pode ver eventos globais — fail-safe."


# ============================================================================
# Scope correto: usuário com EquipeGerencia vê apenas sua(s) gerência(s)
# ============================================================================


class TestScopedAccess:
    def test_coordenador_com_gerencia_ve_apenas_eventos_da_gerencia(self, world):
        """Coordenador vinculado a G1 → vê apenas 2 eventos de G1, não 4."""
        user = _make_user("coord_g1", ["Coordenador"])
        _link_to_gerencia(user, world["g1"], "COORDENADOR")

        response = _get_home_stats(user)
        assert response.status_code == 200
        # 2 eventos em G1 do mundo + 0 eventos em G2 (não vê)
        assert response.json()["upcoming_events"] == 2, "Coordenador G1 vê apenas eventos de G1 (2), não 4."

    def test_apoio_com_gerencia_ve_apenas_eventos_da_gerencia(self, world):
        """Apoio vinculado a G2 → vê apenas 2 eventos de G2."""
        coord_supervisor = _make_user("coord_sup", ["Coordenador"])
        _link_to_gerencia(coord_supervisor, world["g2"], "COORDENADOR")
        user = _make_user("apoio_g2", ["Apoio de Coordenação"])
        _link_to_gerencia(user, world["g2"], "APOIO", supervisor=coord_supervisor)

        response = _get_home_stats(user)
        assert response.status_code == 200
        assert response.json()["upcoming_events"] == 2

    def test_gerente_com_multiplas_gerencias_ve_eventos_de_todas(self, world):
        """Gerente vinculado a G1+G2 → vê 4 eventos."""
        user = _make_user("ger_multi", ["Gerente"])
        _link_to_gerencia(user, world["g1"], "GERENTE")
        _link_to_gerencia(user, world["g2"], "GERENTE")

        response = _get_home_stats(user)
        assert response.status_code == 200
        assert response.json()["upcoming_events"] == 4


# ============================================================================
# Formador: ownership-based (próprios + participações)
# ============================================================================


class TestFormadorOwnership:
    def test_formador_puro_ve_apenas_proprios_e_participacoes(self, world):
        """Formador sem outras funções → vê apenas onde é organizador OU participante."""
        user = _make_user("formador", ["Formador"])
        # Não vinculado a EquipeGerencia, sem outras funções

        # Formador é organizador de 1 solicitação nova
        _make_solicitacao(
            usuario=user,
            projeto=world["p1"],
            municipio=world["municipio"],
            tipo_evento=world["tipo_evento"],
            days_ahead=15,
        )

        # Formador participa de 1 solicitação existente
        sol_outro = world["events_g2"][0]
        Participation.objects.create(
            solicitacao=sol_outro,
            usuario=user,
            role=Participation.Role.FORMADOR,
        )

        response = _get_home_stats(user)
        assert response.status_code == 200
        # Próprio + 1 participação = 2 (mas não 4 nem 5)
        assert (
            response.json()["upcoming_events"] == 2
        ), f"Formador puro deve ver 2 eventos (próprio + participação), recebeu {response.json()['upcoming_events']}"


# ============================================================================
# Acesso global: capabilities cross-organização
# ============================================================================


class TestGlobalAccess:
    def test_dat_ve_todos_os_eventos(self, world):
        """DAT é ator transversal (validar/suportar) → vê todos os eventos."""
        user = _make_user("dat", ["DAT"])
        response = _get_home_stats(user)
        assert response.status_code == 200
        assert response.json()["upcoming_events"] == world["total_events"]

    def test_superuser_ve_todos_os_eventos(self, world):
        """Superuser → bypass → todos."""
        user = _make_user("admin", [], is_superuser=True)
        response = _get_home_stats(user)
        assert response.status_code == 200
        assert response.json()["upcoming_events"] == world["total_events"]

    def test_superintendencia_sem_gerencia_ve_todos(self, world):
        """Superintendência (decisão cross-org de aprovação) → vê todos mesmo sem EquipeGerencia."""
        user = _make_user("super", ["Superintendência"])
        response = _get_home_stats(user)
        assert response.status_code == 200
        # Antes do fix: dependia do else implícito (vazava). Depois do fix: explícito
        # via `approve_solicitation` capability → segue vendo todos.
        assert response.json()["upcoming_events"] == world["total_events"]


# ============================================================================
# Response shape: contrato com frontend permanece intacto
# ============================================================================


class TestResponseShape:
    def test_response_tem_3_chaves(self, world):
        """Shape da response não muda: pending_approvals, upcoming_events, my_requests."""
        user = _make_user("any", ["Coordenador"])
        _link_to_gerencia(user, world["g1"], "COORDENADOR")

        response = _get_home_stats(user)
        assert response.status_code == 200
        body = response.json()
        assert set(body.keys()) == {"pending_approvals", "upcoming_events", "my_requests"}

    def test_anonimo_recebe_401(self):
        """IsAuthenticated mantém anonymous fora."""
        client = APIClient()
        response = client.get("/api/stats/home/")
        assert response.status_code in (401, 403)


# ============================================================================
# pending_approvals e my_requests — paridade comportamental (#1260 não muda intent)
# ============================================================================


class TestParityWithLegacyBehavior:
    def test_super_pode_aprovar_apenas_fluxo_super(self, world):
        """Super (não-DAT) só conta aprovações pendentes em projetos SUPER."""
        super_user = _make_user("super_pa", ["Superintendência"])

        # 1 pendente em projeto NAO_SUPER (mundo já tem aprovados; criar pendente)
        _make_solicitacao(
            usuario=world["autor"],
            projeto=world["p1"],  # NAO_SUPER
            municipio=world["municipio"],
            tipo_evento=world["tipo_evento"],
            status="pendente",
        )
        # 1 pendente em projeto SUPER
        p_super = _make_projeto("Projeto SUPER", world["g1"], fluxo="SUPER")
        _make_solicitacao(
            usuario=world["autor"],
            projeto=p_super,
            municipio=world["municipio"],
            tipo_evento=world["tipo_evento"],
            status="pendente",
        )

        response = _get_home_stats(super_user)
        assert response.status_code == 200
        # Super conta apenas SUPER pendente = 1
        assert response.json()["pending_approvals"] == 1

    def test_dat_pode_aprovar_todos_fluxos(self, world):
        """DAT conta aprovações pendentes de todos os fluxos."""
        dat_user = _make_user("dat_pa", ["DAT"])

        _make_solicitacao(
            usuario=world["autor"],
            projeto=world["p1"],  # NAO_SUPER
            municipio=world["municipio"],
            tipo_evento=world["tipo_evento"],
            status="pendente",
        )
        p_super = _make_projeto("Projeto SUPER", world["g1"], fluxo="SUPER")
        _make_solicitacao(
            usuario=world["autor"],
            projeto=p_super,
            municipio=world["municipio"],
            tipo_evento=world["tipo_evento"],
            status="pendente",
        )

        response = _get_home_stats(dat_user)
        assert response.status_code == 200
        assert response.json()["pending_approvals"] == 2

    def test_formador_nao_pode_aprovar_nem_criar(self, world):
        """Formador puro: pending_approvals e my_requests retornam None."""
        user = _make_user("form_only", ["Formador"])
        response = _get_home_stats(user)
        assert response.status_code == 200
        body = response.json()
        assert body["pending_approvals"] is None
        assert body["my_requests"] is None

"""
PR 8 hardening RBAC (2026-04-30): testes de **escopo** discriminante na
Grade Mensal — complementa a Matriz Viva (que valida apenas ALLOW/DENY)
distinguindo o que cada subtipo de Gerente realmente vê.

Foco discriminante (não está coberto pela Matriz Viva ALLOW/DENY):
- Gerente pedagógico (Setor `Vidas` + Função `Gerente`) vê grade
  filtrada por Vidas; **não** vê dados de Fluir.
- Gerente da Superintendência vê grade filtrada por Superintendência.
- Coordenador / Apoio: scope via `EquipeGerencia` ativa.
- Controle / DAT: cap global via `view_all_availability` (D9).

Tests aqui são focados; cobertura de ALLOW/DENY por endpoint segue na
Matriz Viva (`test_rbac_matrix_living.py`).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportMissingTypeStubs=false, reportUnusedFunction=false, reportIndexIssue=false, reportOperatorIssue=false

from __future__ import annotations

import itertools

from django.contrib.auth.models import Group
from rest_framework.test import APIClient

import pytest

from apps.core.models import EquipeGerencia, Gerencia, Usuario

pytestmark = pytest.mark.django_db


_CPF_COUNTER = itertools.count(20000000000)


def _user_in_groups(*group_names: str, label: str = "user") -> Usuario:
    cpf = str(next(_CPF_COUNTER)).zfill(11)
    user = Usuario.objects.create_user(
        username=f"{label}_{cpf}",
        email=f"{label}_{cpf}@example.com",
        password="testpass",
        cpf=cpf,
    )
    for name in group_names:
        group, _ = Group.objects.get_or_create(name=name)
        user.groups.add(group)
    return user


def _attach_equipe(user: Usuario, gerencia: Gerencia, papel: str = "GERENTE") -> EquipeGerencia:
    return EquipeGerencia.objects.create(gerencia=gerencia, usuario=user, papel=papel, ativo=True)


@pytest.fixture
def gerencia_vidas() -> Gerencia:
    g, _ = Gerencia.objects.get_or_create(
        nome="VIDAS SCOPE TEST",
        defaults={"nome_setor": "Vidas"},
    )
    return g


@pytest.fixture
def gerencia_fluir() -> Gerencia:
    g, _ = Gerencia.objects.get_or_create(
        nome="FLUIR SCOPE TEST",
        defaults={"nome_setor": "Fluir"},
    )
    return g


@pytest.fixture
def gerencia_super() -> Gerencia:
    g, _ = Gerencia.objects.get_or_create(
        nome="SUP SCOPE TEST",
        defaults={"nome_setor": "Superintendência"},
    )
    return g


# =============================================================================
# Grade Mensal — scope discriminante por Gerente pedagógico vs Gerente Sup
# =============================================================================


def test_gerente_pedagogico_vidas_acessa_propria_gerencia_mas_nao_fluir(gerencia_vidas, gerencia_fluir):
    """Gerente pedagógico em Vidas: 200 com `gerencia_id=Vidas`; 403 com `gerencia_id=Fluir`.

    PR 8: Gerente pedagógico perdeu cap global em D9 — só vê via vínculo
    `EquipeGerencia` ativo. Não tem vínculo em Fluir → bloqueado.
    """
    user = _user_in_groups("Vidas", "Gerente", label="gerente_vidas_scope")
    _attach_equipe(user, gerencia_vidas, papel="GERENTE")

    client = APIClient()
    client.force_authenticate(user=user)

    # Vidas — vínculo presente → 200
    response_vidas = client.get(
        f"/api/availability/monthly/?year=2026&month=5&role=FORMADOR&gerencia_id={gerencia_vidas.id}"
    )
    assert response_vidas.status_code == 200, response_vidas.json()

    # Fluir — sem vínculo → 403
    response_fluir = client.get(
        f"/api/availability/monthly/?year=2026&month=5&role=FORMADOR&gerencia_id={gerencia_fluir.id}"
    )
    assert (
        response_fluir.status_code == 403
    ), f"Gerente pedagógico Vidas NÃO deveria ver Fluir; recebeu {response_fluir.status_code}"


def test_gerente_superintendencia_acessa_propria_gerencia(gerencia_super, gerencia_vidas):
    """Gerente da Superintendência: vê Sup, não vê Vidas (sem cap global)."""
    user = _user_in_groups("Superintendência", "Gerente", label="gerente_sup_scope")
    _attach_equipe(user, gerencia_super, papel="GERENTE")

    client = APIClient()
    client.force_authenticate(user=user)

    # Sup — vínculo presente → 200
    response_sup = client.get(
        f"/api/availability/monthly/?year=2026&month=5&role=FORMADOR&gerencia_id={gerencia_super.id}"
    )
    assert response_sup.status_code == 200, response_sup.json()

    # Vidas — sem vínculo → 403
    response_vidas = client.get(
        f"/api/availability/monthly/?year=2026&month=5&role=FORMADOR&gerencia_id={gerencia_vidas.id}"
    )
    assert (
        response_vidas.status_code == 403
    ), f"Gerente da Sup NÃO deveria ver Vidas; recebeu {response_vidas.status_code}"


def test_coordenador_scope_via_equipe_gerencia(gerencia_vidas, gerencia_fluir):
    """Coordenador vê apenas a própria EquipeGerencia ativa."""
    user = _user_in_groups("Coordenador", label="coord_scope")
    _attach_equipe(user, gerencia_vidas, papel="COORDENADOR")

    client = APIClient()
    client.force_authenticate(user=user)

    response_vidas = client.get(
        f"/api/availability/monthly/?year=2026&month=5&role=FORMADOR&gerencia_id={gerencia_vidas.id}"
    )
    assert response_vidas.status_code == 200

    response_fluir = client.get(
        f"/api/availability/monthly/?year=2026&month=5&role=FORMADOR&gerencia_id={gerencia_fluir.id}"
    )
    assert response_fluir.status_code == 403


def test_apoio_scope_via_equipe_gerencia(gerencia_vidas, gerencia_fluir):
    """Apoio de Coordenação: mesma regra do Coord."""
    coord = _user_in_groups("Coordenador", label="coord_apoio_supervisor")
    EquipeGerencia.objects.create(gerencia=gerencia_vidas, usuario=coord, papel="COORDENADOR", ativo=True)

    user = _user_in_groups("Apoio de Coordenação", label="apoio_scope")
    EquipeGerencia.objects.create(
        gerencia=gerencia_vidas,
        usuario=user,
        papel="APOIO",
        ativo=True,
        coordenador_supervisor=coord,
    )

    client = APIClient()
    client.force_authenticate(user=user)

    response_vidas = client.get(
        f"/api/availability/monthly/?year=2026&month=5&role=FORMADOR&gerencia_id={gerencia_vidas.id}"
    )
    assert response_vidas.status_code == 200

    response_fluir = client.get(
        f"/api/availability/monthly/?year=2026&month=5&role=FORMADOR&gerencia_id={gerencia_fluir.id}"
    )
    assert response_fluir.status_code == 403


def test_controle_e_dat_mantem_acesso_global(gerencia_vidas, gerencia_fluir):
    """Controle e DAT têm cap `view_all_availability` (seed 0080) — bypass scope."""
    controle = _user_in_groups("Controle", label="controle_global")
    dat = _user_in_groups("DAT", label="dat_global")

    client_c = APIClient()
    client_c.force_authenticate(user=controle)

    client_d = APIClient()
    client_d.force_authenticate(user=dat)

    # Ambos acessam Vidas e Fluir sem vínculo de gerência (cap global cobre).
    for gerencia in (gerencia_vidas, gerencia_fluir):
        for client in (client_c, client_d):
            response = client.get(
                f"/api/availability/monthly/?year=2026&month=5&role=FORMADOR&gerencia_id={gerencia.id}"
            )
            assert response.status_code == 200, (
                f"Controle/DAT deveriam acessar gerência {gerencia.nome_setor} via cap global; "
                f"got {response.status_code}"
            )

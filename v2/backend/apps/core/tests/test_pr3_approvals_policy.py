"""
PR 3 hardening RBAC (2026-04-29): matriz consolidada para a Policy
`access_solicitation_approvals`. Desde o PR 11 (17/10/2026), nenhum grupo aprova: o Controle aprova
pelo vínculo EQUIPE/GERENTE na gerência CONTROLE (pacote do perfil), como o DAT.

Endpoints cobertos:
- POST /api/solicitacoes/{id}/approve/
- POST /api/solicitacoes/{id}/reject/
- POST /api/solicitacoes/batch-approve/
- POST /api/solicitacoes/batch-reject/

Regra de negócio (PR 11):
- ✅ quem trabalha no Controle (vínculo EQUIPE na gerência CONTROLE), com ou sem os grupos
- ❌ par Controle + Assistente Administrativo sem o vínculo (PR 11: grupo não aprova)
- ❌ par Superintendência + Gerente sem GERENTE na Superintendência (PR 11: grupo não aprova)
- ❌ Gerente pedagógico (Função "Gerente" sem Setor "Superintendência")
- ❌ Controle puro (sem vínculo)
- ❌ Assistente Administrativo fora do Controle
- ❌ grupo DAT sem vínculo, Coordenador, Apoio, Formador, Diretoria (desde o PR 10 o DAT aprova pelo
  vínculo EQUIPE/GERENTE na gerência DAT, não pelo grupo: `test_rbac_pr10_dat_admin_operacional.py`)

Cobre tanto a matriz dos endpoints quanto o contrato `/api/me/policies/`.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportMissingTypeStubs=false, reportUnusedFunction=false

from __future__ import annotations

import itertools

from django.urls import reverse
from rest_framework.test import APIClient

import pytest

from apps.core.models import Solicitacao, Usuario
from apps.core.tests.factories import (
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
    com_pacote_do_controle,
)

pytestmark = pytest.mark.django_db


_CPF_COUNTER = itertools.count(70000000000)


def _user_in_groups(*group_names: str, label: str = "user") -> Usuario:
    cpf = str(next(_CPF_COUNTER)).zfill(11)
    return UsuarioFactory(
        username=f"{label}_{cpf}",
        email=f"{label}_{cpf}@example.com",
        password="testpass",
        cpf=cpf,
        groups=list(group_names),
    )


def _aprovador(*group_names: str, label: str = "user") -> Usuario:
    """PR 11: aprova pelo vínculo EQUIPE na gerência CONTROLE (os grupos, se houver, não contam)."""
    user = _user_in_groups(*group_names, label=label)
    com_pacote_do_controle(user)
    return user


@pytest.fixture
def pendente_solicitacao() -> Solicitacao:
    """Cria uma Solicitação pendente que pode ser aprovada/reprovada."""
    municipio = MunicipioFactory(nome="Fortaleza", uf="CE", ativo=True)
    projeto = ProjetoFactory(nome="Projeto Aprov", codigo="APR", fluxo="SUPER", ativo=True)
    tipo_evento = TipoEventoFactory(nome="Formação")
    requester = _user_in_groups("Coordenador", label="requester")

    from datetime import timedelta

    from django.utils import timezone

    inicio = timezone.now() + timedelta(days=2)
    fim = inicio + timedelta(hours=2)

    return SolicitacaoFactory(
        projeto=projeto,
        municipio=municipio,
        tipo_evento=tipo_evento,
        usuario=requester,
        inicio=inicio,
        fim=fim,
        status="pendente",
    )


# =============================================================================
# ✅ Allowed personas
# =============================================================================


ALLOWED_PERSONAS: list[tuple[str, tuple[str, ...]]] = [
    ("equipe_controle", ()),
    ("asst_admin_controle", ("Controle", "Assistente Administrativo")),
]


@pytest.mark.parametrize("persona", ALLOWED_PERSONAS, ids=[p[0] for p in ALLOWED_PERSONAS])
def test_allowed_personas_can_approve_individual(persona, pendente_solicitacao):
    label, group_names = persona
    user = _aprovador(*group_names, label=label)

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("core:solicitacao-approve", kwargs={"pk": pendente_solicitacao.id})
    response = client.patch(url, format="json")

    assert (
        response.status_code == 200
    ), f"{label} ({group_names}) deveria aprovar individual; recebeu {response.status_code}"


@pytest.mark.parametrize("persona", ALLOWED_PERSONAS, ids=[p[0] for p in ALLOWED_PERSONAS])
def test_allowed_personas_can_reject_individual(persona, pendente_solicitacao):
    label, group_names = persona
    user = _aprovador(*group_names, label=label)

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("core:solicitacao-reject", kwargs={"pk": pendente_solicitacao.id})
    response = client.patch(url, {"reason": "teste"}, format="json")

    assert response.status_code == 200, f"{label} deveria reprovar individual; recebeu {response.status_code}"


@pytest.mark.parametrize("persona", ALLOWED_PERSONAS, ids=[p[0] for p in ALLOWED_PERSONAS])
def test_allowed_personas_can_batch_approve(persona, pendente_solicitacao):
    label, group_names = persona
    user = _aprovador(*group_names, label=label)

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("core:solicitacao-batch-approve")
    response = client.post(url, {"ids": [pendente_solicitacao.id]}, format="json")

    assert response.status_code == 200, f"{label} deveria aprovar em lote; recebeu {response.status_code}"


@pytest.mark.parametrize("persona", ALLOWED_PERSONAS, ids=[p[0] for p in ALLOWED_PERSONAS])
def test_allowed_personas_can_batch_reject(persona, pendente_solicitacao):
    label, group_names = persona
    user = _aprovador(*group_names, label=label)

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("core:solicitacao-batch-reject")
    response = client.post(
        url,
        {"ids": [pendente_solicitacao.id], "reason": "teste"},
        format="json",
    )

    assert response.status_code == 200, f"{label} deveria reprovar em lote; recebeu {response.status_code}"


# =============================================================================
# ❌ Forbidden personas
# =============================================================================


FORBIDDEN_PERSONAS: list[tuple[str, tuple[str, ...]]] = [
    # PR 11: grupo não aprova; os pares sem o vínculo deixaram de aprovar.
    ("par_controle_sem_vinculo", ("Controle", "Assistente Administrativo")),
    ("par_legado_sem_vinculo", ("Superintendência", "Gerente")),
    ("controle_puro", ("Controle",)),
    ("asst_admin_sem_controle", ("Vidas", "Assistente Administrativo")),
    ("gerente_pedagogico", ("Vidas", "Gerente")),
    ("dat", ("DAT",)),
    ("coordenador", ("Coordenador",)),
    ("apoio", ("Apoio de Coordenação",)),
    ("formador", ("Formador",)),
    ("diretoria", ("Diretoria",)),
]


@pytest.mark.parametrize("persona", FORBIDDEN_PERSONAS, ids=[p[0] for p in FORBIDDEN_PERSONAS])
def test_forbidden_personas_get_403_on_approve(persona, pendente_solicitacao):
    label, group_names = persona
    user = _user_in_groups(*group_names, label=label)

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("core:solicitacao-approve", kwargs={"pk": pendente_solicitacao.id})
    response = client.patch(url, format="json")

    assert (
        response.status_code == 403
    ), f"{label} ({group_names}) deveria receber 403 em approve; recebeu {response.status_code}"


@pytest.mark.parametrize("persona", FORBIDDEN_PERSONAS, ids=[p[0] for p in FORBIDDEN_PERSONAS])
def test_forbidden_personas_get_403_on_reject(persona, pendente_solicitacao):
    label, group_names = persona
    user = _user_in_groups(*group_names, label=label)

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("core:solicitacao-reject", kwargs={"pk": pendente_solicitacao.id})
    response = client.patch(url, {"reason": "x"}, format="json")

    assert response.status_code == 403


@pytest.mark.parametrize("persona", FORBIDDEN_PERSONAS, ids=[p[0] for p in FORBIDDEN_PERSONAS])
def test_forbidden_personas_get_403_on_batch_approve(persona, pendente_solicitacao):
    label, group_names = persona
    user = _user_in_groups(*group_names, label=label)

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("core:solicitacao-batch-approve")
    response = client.post(url, {"ids": [pendente_solicitacao.id]}, format="json")

    assert response.status_code == 403


@pytest.mark.parametrize("persona", FORBIDDEN_PERSONAS, ids=[p[0] for p in FORBIDDEN_PERSONAS])
def test_forbidden_personas_get_403_on_batch_reject(persona, pendente_solicitacao):
    label, group_names = persona
    user = _user_in_groups(*group_names, label=label)

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("core:solicitacao-batch-reject")
    response = client.post(url, {"ids": [pendente_solicitacao.id], "reason": "x"}, format="json")

    assert response.status_code == 403


# =============================================================================
# Superuser bypass + anonymous
# =============================================================================


def test_superuser_can_approve(pendente_solicitacao):
    user = UsuarioFactory(superuser=True)
    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("core:solicitacao-approve", kwargs={"pk": pendente_solicitacao.id})
    response = client.patch(url, format="json")
    assert response.status_code == 200


def test_anonymous_blocked_on_approve(pendente_solicitacao):
    client = APIClient()
    url = reverse("core:solicitacao-approve", kwargs={"pk": pendente_solicitacao.id})
    response = client.patch(url, format="json")
    assert response.status_code in (401, 403)


# =============================================================================
# /api/me/policies — exposição da policy access_solicitation_approvals
# =============================================================================


PUBLIC_POLICY_PERSONAS_HAS: list[tuple[str, tuple[str, ...]]] = [
    ("equipe_controle_policy", ()),
    ("asst_admin_controle_policy", ("Controle", "Assistente Administrativo")),
]


PUBLIC_POLICY_PERSONAS_HAS_NOT: list[tuple[str, tuple[str, ...]]] = [
    ("par_controle_sem_vinculo_policy", ("Controle", "Assistente Administrativo")),
    ("par_legado_sem_vinculo_policy", ("Superintendência", "Gerente")),
    ("controle_puro_policy", ("Controle",)),
    ("dat_policy", ("DAT",)),
    ("gerente_pedagogico_policy", ("Vidas", "Gerente")),
]


@pytest.mark.parametrize("persona", PUBLIC_POLICY_PERSONAS_HAS, ids=[p[0] for p in PUBLIC_POLICY_PERSONAS_HAS])
def test_me_policies_exposes_access_solicitation_approvals(persona):
    label, group_names = persona
    user = _aprovador(*group_names, label=label)
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(reverse("core:me-policies"))
    assert response.status_code == 200
    body = response.json()
    assert "access_solicitation_approvals" in body, f"{label} deveria receber a policy; payload={body}"


@pytest.mark.parametrize("persona", PUBLIC_POLICY_PERSONAS_HAS_NOT, ids=[p[0] for p in PUBLIC_POLICY_PERSONAS_HAS_NOT])
def test_me_policies_does_not_expose_access_solicitation_approvals(persona):
    label, group_names = persona
    user = _user_in_groups(*group_names, label=label)
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(reverse("core:me-policies"))
    assert response.status_code == 200
    body = response.json()
    assert "access_solicitation_approvals" not in body, f"{label} NÃO deveria receber a policy; payload={body}"

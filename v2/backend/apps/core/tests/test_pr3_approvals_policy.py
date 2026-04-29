"""
PR 3 hardening RBAC (2026-04-29): matriz consolidada para a Policy
`access_solicitacao_approvals` (composite Setor × Função).

Endpoints cobertos:
- POST /api/solicitacoes/{id}/approve/
- POST /api/solicitacoes/{id}/reject/
- POST /api/solicitacoes/batch-approve/
- POST /api/solicitacoes/batch-reject/

Regra de negócio (D-1..D-4):
- ✅ Gerente da Superintendência (Setor "Superintendência" + Função "Gerente")
- ✅ Assistente Administrativo do Controle (Setor "Controle" + Função
  "Assistente Administrativo")
- ❌ Gerente pedagógico (Função "Gerente" sem Setor "Superintendência")
- ❌ Controle puro (sem Função "Assistente Administrativo")
- ❌ Assistente Administrativo fora do Controle
- ❌ DAT, Coordenador, Apoio, Formador, Diretoria

Cobre tanto a matriz dos endpoints quanto o contrato `/api/me/policies/`.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportMissingTypeStubs=false, reportUnusedFunction=false

from __future__ import annotations

import itertools

from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework.test import APIClient

import pytest

from apps.core.models import Municipio, Projeto, Solicitacao, TipoEvento, Usuario

pytestmark = pytest.mark.django_db


_CPF_COUNTER = itertools.count(70000000000)


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


@pytest.fixture
def pendente_solicitacao() -> Solicitacao:
    """Cria uma Solicitação pendente que pode ser aprovada/reprovada."""
    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome="Projeto Aprov", codigo="APR", fluxo="SUPER", ativo=True)
    tipo_evento = TipoEvento.objects.create(nome="Formação")
    requester = _user_in_groups("Coordenador", label="requester")

    from datetime import timedelta

    from django.utils import timezone

    inicio = timezone.now() + timedelta(days=2)
    fim = inicio + timedelta(hours=2)

    return Solicitacao.objects.create(
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
    ("gerente_super", ("Superintendência", "Gerente")),
    ("asst_admin_controle", ("Controle", "Assistente Administrativo")),
]


@pytest.mark.parametrize("persona", ALLOWED_PERSONAS, ids=[p[0] for p in ALLOWED_PERSONAS])
def test_allowed_personas_can_approve_individual(persona, pendente_solicitacao):
    label, group_names = persona
    user = _user_in_groups(*group_names, label=label)

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
    user = _user_in_groups(*group_names, label=label)

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("core:solicitacao-reject", kwargs={"pk": pendente_solicitacao.id})
    response = client.patch(url, {"reason": "teste"}, format="json")

    assert response.status_code == 200, f"{label} deveria reprovar individual; recebeu {response.status_code}"


@pytest.mark.parametrize("persona", ALLOWED_PERSONAS, ids=[p[0] for p in ALLOWED_PERSONAS])
def test_allowed_personas_can_batch_approve(persona, pendente_solicitacao):
    label, group_names = persona
    user = _user_in_groups(*group_names, label=label)

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("core:solicitacao-batch-approve")
    response = client.post(url, {"ids": [pendente_solicitacao.id]}, format="json")

    assert response.status_code == 200, f"{label} deveria aprovar em lote; recebeu {response.status_code}"


@pytest.mark.parametrize("persona", ALLOWED_PERSONAS, ids=[p[0] for p in ALLOWED_PERSONAS])
def test_allowed_personas_can_batch_reject(persona, pendente_solicitacao):
    label, group_names = persona
    user = _user_in_groups(*group_names, label=label)

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
    cpf = str(next(_CPF_COUNTER)).zfill(11)
    user = Usuario.objects.create_superuser(
        username=f"super_pr3_{cpf}",
        email=f"super_pr3_{cpf}@example.com",
        password="testpass",
        cpf=cpf,
    )
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
# /api/me/policies — exposição da policy access_solicitacao_approvals
# =============================================================================


PUBLIC_POLICY_PERSONAS_HAS: list[tuple[str, tuple[str, ...]]] = [
    ("gerente_super_policy", ("Superintendência", "Gerente")),
    ("asst_admin_controle_policy", ("Controle", "Assistente Administrativo")),
]


PUBLIC_POLICY_PERSONAS_HAS_NOT: list[tuple[str, tuple[str, ...]]] = [
    ("controle_puro_policy", ("Controle",)),
    ("dat_policy", ("DAT",)),
    ("gerente_pedagogico_policy", ("Vidas", "Gerente")),
]


@pytest.mark.parametrize("persona", PUBLIC_POLICY_PERSONAS_HAS, ids=[p[0] for p in PUBLIC_POLICY_PERSONAS_HAS])
def test_me_policies_exposes_access_solicitacao_approvals(persona):
    label, group_names = persona
    user = _user_in_groups(*group_names, label=label)
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(reverse("core:me-policies"))
    assert response.status_code == 200
    body = response.json()
    assert "access_solicitacao_approvals" in body, f"{label} deveria receber a policy; payload={body}"


@pytest.mark.parametrize("persona", PUBLIC_POLICY_PERSONAS_HAS_NOT, ids=[p[0] for p in PUBLIC_POLICY_PERSONAS_HAS_NOT])
def test_me_policies_does_not_expose_access_solicitacao_approvals(persona):
    label, group_names = persona
    user = _user_in_groups(*group_names, label=label)
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(reverse("core:me-policies"))
    assert response.status_code == 200
    body = response.json()
    assert "access_solicitacao_approvals" not in body, f"{label} NÃO deveria receber a policy; payload={body}"

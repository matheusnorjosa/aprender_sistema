"""
PR 5 hardening RBAC (2026-04-30): matriz consolidada para `UsuarioLookup`.

Endpoint: `GET /api/lookup/usuarios/`

Mudanças:
- Antes: `permission_classes = [IsAuthenticated]` — qualquer user autenticado.
- Depois: composite `HasPerm("create_solicitation") |
  HasPerm("manage_admin_registries")` (motivos legítimos confirmados em
  auditoria cross-stack).

Consumidores legítimos (auditoria 2026-04-30):
- `NewSolicitacaoWizard` / `EditSolicitacaoPage` → `create_solicitation`
- `AdminDAT` / suporte → `manage_admin_registries`

Aprovações, Controle/operação e dashboards executivos NÃO consomem
o endpoint — portanto `approve_solicitation_batch` e `operate_preagenda`
ficam fora do gate.

SEC-ENUM-01: email permanece fora do payload (anti-enumeração).
SEC-ENUM-02: busca por email/username é cap-gated (mesma matriz),
sem hardcode de group names.

Personas:
- ✅ DAT, Coordenador, Apoio, Gerente, superuser → 200
- ❌ Controle puro, Formador, Diretoria, Sup pura sem Função → 403
- Anonymous → 401/403
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportMissingTypeStubs=false, reportUnusedFunction=false

from __future__ import annotations

import itertools

from django.contrib.auth.models import Group
from rest_framework.test import APIClient

import pytest

from apps.core.models import Usuario

pytestmark = pytest.mark.django_db


_CPF_COUNTER = itertools.count(50000000000)


def _user_in_groups(*group_names: str, label: str = "user") -> Usuario:
    cpf = str(next(_CPF_COUNTER)).zfill(11)
    user = Usuario.objects.create_user(
        username=f"{label}_{cpf}",
        email=f"{label}_{cpf}@example.com",
        password="testpass",
        cpf=cpf,
        first_name=label.capitalize(),
        last_name="User",
    )
    for name in group_names:
        group, _ = Group.objects.get_or_create(name=name)
        user.groups.add(group)
    return user


@pytest.fixture
def target_formador():
    """Usuário-alvo para a busca."""
    cpf = str(next(_CPF_COUNTER)).zfill(11)
    user = Usuario.objects.create_user(
        username=f"target_{cpf}",
        email=f"maria_alvo_{cpf}@example.com",
        password="testpass",
        cpf=cpf,
        first_name="Maria",
        last_name="Silva",
    )
    formador, _ = Group.objects.get_or_create(name="Formador")
    user.groups.add(formador)
    return user


# =============================================================================
# Capability gate
# =============================================================================


ALLOWED_PERSONAS: list[tuple[str, tuple[str, ...]]] = [
    ("dat", ("DAT",)),
    ("coordenador", ("Coordenador",)),
    ("apoio", ("Apoio de Coordenação",)),
    ("gerente_pedagogico", ("Vidas", "Gerente")),
    ("gerente_super", ("Superintendência", "Gerente")),
]


@pytest.mark.parametrize("persona", ALLOWED_PERSONAS, ids=[p[0] for p in ALLOWED_PERSONAS])
def test_allowed_personas_can_lookup(persona, target_formador):
    label, group_names = persona
    user = _user_in_groups(*group_names, label=label)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get("/api/lookup/usuarios/?q=Maria")

    assert response.status_code == 200, f"{label} ({group_names}) deveria ter acesso; recebeu {response.status_code}"


def test_superuser_can_lookup(target_formador):
    cpf = str(next(_CPF_COUNTER)).zfill(11)
    user = Usuario.objects.create_superuser(
        username=f"super_pr5_{cpf}",
        email=f"super_pr5_{cpf}@example.com",
        password="testpass",
        cpf=cpf,
    )
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/api/lookup/usuarios/?q=Maria")
    assert response.status_code == 200


FORBIDDEN_PERSONAS: list[tuple[str, tuple[str, ...]]] = [
    ("controle_puro", ("Controle",)),
    ("formador", ("Formador",)),
    ("diretoria", ("Diretoria",)),
    ("sup_pura", ("Superintendência",)),  # Sem Função: sem create_solicitation
]


@pytest.mark.parametrize("persona", FORBIDDEN_PERSONAS, ids=[p[0] for p in FORBIDDEN_PERSONAS])
def test_forbidden_personas_get_403(persona, target_formador):
    label, group_names = persona
    user = _user_in_groups(*group_names, label=label)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get("/api/lookup/usuarios/?q=Maria")

    assert response.status_code == 403, f"{label} ({group_names}) deveria receber 403; recebeu {response.status_code}"


def test_anonymous_blocked():
    client = APIClient()
    response = client.get("/api/lookup/usuarios/?q=Maria")
    assert response.status_code in (401, 403)


# =============================================================================
# SEC-ENUM-02: busca por email é cap-gated (sem hardcode de grupo)
# =============================================================================


EMAIL_SEARCH_ALLOWED: list[tuple[str, tuple[str, ...]]] = [
    ("dat_email", ("DAT",)),
    ("coordenador_email", ("Coordenador",)),
    ("apoio_email", ("Apoio de Coordenação",)),
    ("gerente_pedagogico_email", ("Vidas", "Gerente")),
]


@pytest.mark.parametrize("persona", EMAIL_SEARCH_ALLOWED, ids=[p[0] for p in EMAIL_SEARCH_ALLOWED])
def test_email_search_finds_user_for_allowed_personas(persona, target_formador):
    label, group_names = persona
    user = _user_in_groups(*group_names, label=label)
    client = APIClient()
    client.force_authenticate(user=user)

    # Buscar pelo prefixo do email (não usa nome).
    response = client.get(f"/api/lookup/usuarios/?q=maria_alvo_{target_formador.cpf}")
    assert response.status_code == 200
    body = response.json()
    ids = [item["id"] for item in body]
    assert target_formador.id in ids, f"{label} deveria encontrar usuário por email; payload={body}"


# =============================================================================
# SEC-ENUM-01: email NUNCA aparece no payload, mesmo para perfis privilegiados
# =============================================================================


def test_payload_never_exposes_email(target_formador):
    user = _user_in_groups("DAT", label="dat_payload")
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/api/lookup/usuarios/?q=Maria")
    assert response.status_code == 200
    body = response.json()
    assert body, "Esperava ao menos 1 resultado para Maria"
    for item in body:
        assert "email" not in item, f"SEC-ENUM-01 violado: payload exposes email: {item}"


# =============================================================================
# Role filter continua funcionando (regression)
# =============================================================================


def test_role_filter_returns_only_role(target_formador):
    """Garantir que `?role=Formador` continua filtrando por grupo."""
    user = _user_in_groups("Coordenador", label="coord_role")
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get("/api/lookup/usuarios/?q=Maria&role=Formador")
    assert response.status_code == 200
    body = response.json()
    ids = [item["id"] for item in body]
    assert target_formador.id in ids

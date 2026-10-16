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
SEC-ENUM-02 / S5 (C6, 16/10): o login é o CPF, então a busca é por nome (e-mail só sem dígito); só quem
administra cadastros acha por e-mail ou CPF, e só pelo valor exato
(`test_cpf_fora_de_telas_busca_logs.py`).

Personas:
- ✅ DAT, Coordenador, Apoio, Gerente, superuser → 200
- ❌ Controle puro, Formador, Diretoria, Sup pura sem Função → 403
- Anonymous → 401/403

PR 9: o resultado só traz pessoas das gerências onde quem busca atua (G/C/A); globais (DAT,
superuser) sem filtro. Quem busca e o alvo ficam na mesma gerência (`gerencia`) nos testes que
esperam achar o alvo.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportMissingTypeStubs=false, reportUnusedFunction=false

from __future__ import annotations

import itertools

from rest_framework.test import APIClient

import pytest

from apps.core.tests.factories import GerenciaFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


_CPF_COUNTER = itertools.count(50000000000)


def _user_in_groups(*group_names: str, label: str = "user", gerencia=None):
    cpf = str(next(_CPF_COUNTER)).zfill(11)
    return UsuarioFactory(
        username=f"{label}_{cpf}",
        email=f"{label}_{cpf}@example.com",
        password="testpass",
        cpf=cpf,
        first_name=label.capitalize(),
        last_name="User",
        groups=list(group_names),
        groups__gerencia=gerencia,
    )


@pytest.fixture
def gerencia():
    """Gerência do alvo e de quem busca (o lookup é por gerência de atuação, PR 9)."""
    return GerenciaFactory()


@pytest.fixture
def target_formador(gerencia):
    """Usuário-alvo para a busca."""
    cpf = str(next(_CPF_COUNTER)).zfill(11)
    return UsuarioFactory(
        username=f"target_{cpf}",
        email=f"maria_alvo_{cpf}@example.com",
        password="testpass",
        cpf=cpf,
        first_name="Maria",
        last_name="Silva",
        groups=["Formador"],
        groups__gerencia=gerencia,
    )


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
    user = UsuarioFactory(superuser=True)
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
# SEC-ENUM-02 / S5 (C6): e-mail só exato e só para quem administra cadastros
# =============================================================================


EMAIL_SEARCH_DENIED: list[tuple[str, tuple[str, ...]]] = [
    ("coordenador_email", ("Coordenador",)),
    ("apoio_email", ("Apoio de Coordenação",)),
    ("gerente_pedagogico_email", ("Vidas", "Gerente")),
]


@pytest.mark.parametrize("persona", EMAIL_SEARCH_DENIED, ids=[p[0] for p in EMAIL_SEARCH_DENIED])
def test_email_search_finds_nobody_for_non_admin_personas(persona, target_formador, gerencia):
    label, group_names = persona
    user = _user_in_groups(*group_names, label=label, gerencia=gerencia)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(f"/api/lookup/usuarios/?q={target_formador.email}")
    assert response.status_code == 200
    assert response.json() == [], f"{label} não deveria achar ninguém por e-mail"


def test_email_search_exact_finds_user_for_dat(target_formador):
    user = _user_in_groups("DAT", label="dat_email")
    client = APIClient()
    client.force_authenticate(user=user)

    exato = client.get(f"/api/lookup/usuarios/?q={target_formador.email}")
    assert target_formador.id in [item["id"] for item in exato.json()]
    prefixo = client.get(f"/api/lookup/usuarios/?q=maria_alvo_{target_formador.cpf}")
    assert prefixo.json() == []


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


def test_role_filter_returns_only_role(target_formador, gerencia):
    """Garantir que `?role=Formador` continua filtrando por grupo."""
    user = _user_in_groups("Coordenador", label="coord_role", gerencia=gerencia)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get("/api/lookup/usuarios/?q=Maria&role=Formador")
    assert response.status_code == 200
    body = response.json()
    ids = [item["id"] for item in body]
    assert target_formador.id in ids

"""
PR 6 hardening RBAC (2026-04-30): matriz consolidada para
`access_audit_logs`. Policy reduzida a DAT (admin) + Controle (operação)
+ superuser. `approve_solicitation` e `approve_solicitation_batch`
removidos do gate para evitar liberação indevida a Gerente pedagógico,
Sup pura e Gerente da Sup.

Endpoint: `GET /api/audit-logs/`

Personas:
- ✅ DAT (`manage_admin_registries`) → 200
- ✅ Controle (`operate_preagenda`) → 200
- ✅ Superuser → 200
- ❌ Sup pura, Gerente Sup, Gerente pedagógico, Coord, Apoio, Formador, Diretoria → 403
- Anonymous → 401/403

SEC-AUDIT-01 (`_mask_email` / `_mask_ip` / `_redact_details`) preservado:
testes específicos em test_sec_enum_audit.py continuam validando para
DAT, Controle e superuser.

Cobre tanto o gate dos endpoints quanto o contrato `/api/me/policies/`.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportMissingTypeStubs=false, reportUnusedFunction=false

from __future__ import annotations

import itertools

from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog
from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db


_CPF_COUNTER = itertools.count(40000000000)


def _user_in_groups(*group_names: str, label: str = "user"):
    cpf = str(next(_CPF_COUNTER)).zfill(11)
    return UsuarioFactory(
        username=f"{label}_{cpf}",
        email=f"{label}_{cpf}@example.com",
        password="testpass",
        cpf=cpf,
        groups=list(group_names),
    )


@pytest.fixture
def audit_log_record():
    """Cria um AuditLog para o teste poder consultar via list endpoint."""
    return AuditLog.objects.create(
        usuario=None,
        action="LOGIN",
        model_name="Usuario",
        details={
            "ip_address": "203.0.113.50",
            "google_email": "user@gmail.com",
            "reason": "success",
        },
    )


# =============================================================================
# Allowed personas (DAT, Controle, superuser)
# =============================================================================


ALLOWED_PERSONAS: list[tuple[str, tuple[str, ...]]] = [
    ("dat", ("DAT",)),
    ("controle", ("Controle",)),
]


@pytest.mark.parametrize("persona", ALLOWED_PERSONAS, ids=[p[0] for p in ALLOWED_PERSONAS])
def test_allowed_personas_can_list_audit_logs(persona, audit_log_record):
    label, group_names = persona
    user = _user_in_groups(*group_names, label=label)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get("/api/audit-logs/")
    assert (
        response.status_code == 200
    ), f"{label} ({group_names}) deveria listar audit logs; recebeu {response.status_code}"


def test_superuser_can_list_audit_logs(audit_log_record):
    user = UsuarioFactory(superuser=True)
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/api/audit-logs/")
    assert response.status_code == 200


# =============================================================================
# Forbidden personas
# =============================================================================


FORBIDDEN_PERSONAS: list[tuple[str, tuple[str, ...]]] = [
    ("sup_pura", ("Superintendência",)),
    ("gerente_sup", ("Superintendência", "Gerente")),
    ("gerente_pedagogico", ("Vidas", "Gerente")),
    ("coordenador", ("Coordenador",)),
    ("apoio", ("Apoio de Coordenação",)),
    ("formador", ("Formador",)),
    ("diretoria", ("Diretoria",)),
]


@pytest.mark.parametrize("persona", FORBIDDEN_PERSONAS, ids=[p[0] for p in FORBIDDEN_PERSONAS])
def test_forbidden_personas_get_403(persona, audit_log_record):
    label, group_names = persona
    user = _user_in_groups(*group_names, label=label)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get("/api/audit-logs/")
    assert response.status_code == 403, f"{label} ({group_names}) deveria receber 403; recebeu {response.status_code}"


def test_anonymous_blocked():
    client = APIClient()
    response = client.get("/api/audit-logs/")
    assert response.status_code in (401, 403)


# =============================================================================
# SEC-AUDIT-01: masking continua funcionando para personas autorizadas
# =============================================================================


@pytest.mark.parametrize(
    "persona",
    ALLOWED_PERSONAS + [("superuser_redaction", ())],
    ids=[p[0] for p in ALLOWED_PERSONAS] + ["superuser_redaction"],
)
def test_redaction_works_for_allowed_personas(persona, audit_log_record):
    """SEC-AUDIT-01: details PII redigidos exceto para superuser."""
    label, group_names = persona

    if label == "superuser_redaction":
        user = UsuarioFactory(superuser=True)
        expected_full_payload = True
    else:
        user = _user_in_groups(*group_names, label=label)
        expected_full_payload = False

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/api/audit-logs/")
    assert response.status_code == 200

    data = response.json()
    results = data.get("results", data) if isinstance(data, dict) else data
    if isinstance(results, dict):
        results = results.get("results", [])
    assert len(results) > 0, f"{label}: esperava ao menos 1 audit log no payload"

    details = results[0]["details"]
    if expected_full_payload:
        # Superuser: vê detalhes completos (sem masking).
        assert details["ip_address"] == "203.0.113.50"
        assert details["google_email"] == "user@gmail.com"
    else:
        # Não-superuser: SEC-AUDIT-01 redige PII.
        assert details["ip_address"] == "203.0.113.***", f"{label}: ip mascarado esperado, got={details}"
        assert details["google_email"] == "u***@gmail.com", f"{label}: email mascarado esperado, got={details}"
        # Não-PII preservado.
        assert details["reason"] == "success"


# =============================================================================
# /api/me/policies — exposição de access_audit_logs
# =============================================================================


@pytest.mark.parametrize("persona", ALLOWED_PERSONAS, ids=[p[0] for p in ALLOWED_PERSONAS])
def test_me_policies_exposes_access_audit_logs_for_allowed(persona):
    label, group_names = persona
    user = _user_in_groups(*group_names, label=f"{label}_policy")
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/api/me/policies/")
    assert response.status_code == 200
    body = response.json()
    assert "access_audit_logs" in body, f"{label} deveria receber a policy access_audit_logs; payload={body}"


@pytest.mark.parametrize(
    "persona",
    [
        ("sup_pura_policy", ("Superintendência",)),
        ("gerente_sup_policy", ("Superintendência", "Gerente")),
        ("gerente_pedagogico_policy", ("Vidas", "Gerente")),
        ("formador_policy", ("Formador",)),
        ("diretoria_policy", ("Diretoria",)),
    ],
    ids=lambda p: p[0],
)
def test_me_policies_does_not_expose_access_audit_logs_for_forbidden(persona):
    label, group_names = persona
    user = _user_in_groups(*group_names, label=label)
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/api/me/policies/")
    assert response.status_code == 200
    body = response.json()
    assert "access_audit_logs" not in body, f"{label} NÃO deveria receber a policy access_audit_logs; payload={body}"

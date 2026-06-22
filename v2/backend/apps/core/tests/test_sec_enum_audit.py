"""
Tests for SEC-ENUM and SEC-AUDIT issues.

Covers:
- SEC-ENUM-01 (#1134): Email removed from options/lookup endpoints
- SEC-ENUM-02 (#1135): Email search restricted to Coordenador+ roles
- SEC-AUDIT-01 (#1137): PII redacted in AuditLog serializer
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.models import AuditLog
from apps.core.serializers.auditoria import _mask_email, _mask_ip, _redact_details
from apps.core.tests.factories import GroupFactory, UsuarioFactory

_cpf_counter = 0


def _next_cpf() -> str:
    global _cpf_counter  # noqa: PLW0603
    _cpf_counter += 1
    return str(_cpf_counter).zfill(11)


# ================================================================
# SEC-ENUM-01: Email removed from options/lookup (#1134)
# ================================================================
class TestUsuarioOptionsNoEmail(TestCase):
    """SEC-ENUM-01: /api/options/usuarios/ must not return email field."""

    def setUp(self):
        self.user = UsuarioFactory(username="enum_test", email="enum@test.com", password="pass1234", cpf=_next_cpf())
        UsuarioFactory(
            username="target_user",
            email="target@secret.com",
            password="pass1234",
            first_name="Target",
            last_name="User",
            cpf=_next_cpf(),
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_options_usuarios_no_email_field(self):
        response = self.client.get("/api/options/usuarios/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        first_item = data[0]
        assert "id" in first_item
        assert "first_name" in first_item
        assert "email" not in first_item


class TestUsuarioLookupNoEmail(TestCase):
    """SEC-ENUM-01: /api/lookup/usuarios/ must not return email field.

    PR 5 hardening RBAC (2026-04-30): endpoint deixou de ser
    `IsAuthenticated`. User precisa ter cap legítima — usamos Coordenador
    (cap `create_solicitation`) para validar SEC-ENUM-01.
    """

    def setUp(self):
        coord_group = GroupFactory(name="Coordenador")
        self.user = UsuarioFactory(
            username="lookup_test", email="lookup@test.com", password="pass1234", cpf=_next_cpf()
        )
        self.user.groups.add(coord_group)
        UsuarioFactory(
            username="lookup_target",
            email="target@secret.com",
            password="pass1234",
            first_name="Maria",
            last_name="Silva",
            cpf=_next_cpf(),
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_lookup_usuarios_no_email_field(self):
        response = self.client.get("/api/lookup/usuarios/?q=Maria")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        first_item = data[0]
        assert "id" in first_item
        assert "label" in first_item
        assert "email" not in first_item

    def test_lookup_label_no_email(self):
        """Label should not contain email in angle brackets."""
        response = self.client.get("/api/lookup/usuarios/?q=Maria")
        data = response.json()
        for item in data:
            assert "<" not in item["label"], f"Label should not contain email: {item['label']}"
            assert "@" not in item["label"], f"Label should not contain email: {item['label']}"


# ================================================================
# SEC-ENUM-02: Email search restricted to Coordenador+ (#1135)
# ================================================================
class TestEmailSearchRestriction(TestCase):
    """SEC-ENUM-02: Only Coordenador+ can search by email."""

    def setUp(self):
        # Create groups
        self.formador_group = GroupFactory(name="Formador")
        self.coord_group = GroupFactory(name="Coordenador")

        # Create formador user
        self.formador = UsuarioFactory(
            username="formador1", email="formador@test.com", password="pass1234", cpf=_next_cpf()
        )
        self.formador.groups.add(self.formador_group)

        # Create coordenador user
        self.coordenador = UsuarioFactory(
            username="coord1", email="coord@test.com", password="pass1234", cpf=_next_cpf()
        )
        self.coordenador.groups.add(self.coord_group)

        # Create target user with distinct email
        UsuarioFactory(
            username="target_email",
            email="distinct.email@example.com",
            password="pass1234",
            first_name="Ana",
            last_name="Costa",
            cpf=_next_cpf(),
        )

        self.client = APIClient()

    def test_formador_cannot_lookup_at_all(self):
        """PR 5 hardening RBAC: Formador NÃO acessa o endpoint
        (regra anterior — busca por email retornar lista vazia — foi
        substituída por capability gate; Formador recebe 403)."""
        self.client.force_authenticate(user=self.formador)
        response = self.client.get("/api/lookup/usuarios/?q=distinct.email")
        assert response.status_code == 403, f"Formador deveria receber 403 após PR 5, recebeu {response.status_code}"

    def test_coordenador_can_search_by_email(self):
        """Coordenador searching by email should find the user."""
        self.client.force_authenticate(user=self.coordenador)
        response = self.client.get("/api/lookup/usuarios/?q=distinct.email")
        data = response.json()
        assert len(data) > 0, "Coordenador should find users by email search"

    def test_formador_cannot_search_by_name_either(self):
        """PR 5 hardening RBAC: Formador também perde a busca por nome
        (gate é no endpoint inteiro, não só na coluna de email)."""
        self.client.force_authenticate(user=self.formador)
        response = self.client.get("/api/lookup/usuarios/?q=Ana")
        assert response.status_code == 403


# ================================================================
# SEC-AUDIT-01: PII redacted in AuditLog (#1137)
# ================================================================
class TestAuditLogPIIRedaction(TestCase):
    """SEC-AUDIT-01: PII fields redacted for non-superuser."""

    def test_mask_ip(self):
        assert _mask_ip("192.168.1.100") == "192.168.1.***"
        assert _mask_ip("10.0.0.1") == "10.0.0.***"

    def test_mask_email(self):
        assert _mask_email("user@example.com") == "u***@example.com"
        assert _mask_email("a@b.com") == "a***@b.com"

    def test_redact_removes_user_agent(self):
        details = {"user_agent": "Mozilla/5.0", "action": "LOGIN"}
        redacted = _redact_details(details)
        assert "user_agent" not in redacted
        assert redacted["action"] == "LOGIN"

    def test_redact_masks_ip(self):
        details = {"ip_address": "192.168.1.100"}
        redacted = _redact_details(details)
        assert redacted["ip_address"] == "192.168.1.***"

    def test_redact_masks_google_email(self):
        details = {"google_email": "user@gmail.com"}
        redacted = _redact_details(details)
        assert redacted["google_email"] == "u***@gmail.com"

    def test_redact_preserves_non_pii(self):
        details = {
            "username": "admin",
            "reason": "invalid_credentials",
            "attempts": 3,
        }
        redacted = _redact_details(details)
        assert redacted == details

    def test_redact_nested_dict(self):
        details = {
            "outer": "safe",
            "inner": {"ip_address": "10.0.0.1", "data": "ok"},
        }
        redacted = _redact_details(details)
        assert redacted["outer"] == "safe"
        assert redacted["inner"]["ip_address"] == "10.0.0.***"
        assert redacted["inner"]["data"] == "ok"


class TestAuditLogViewSetRedaction(TestCase):
    """SEC-AUDIT-01: AuditLog API returns redacted details for non-superuser."""

    def setUp(self):
        # Create groups for HasPerm("operate_preagenda") permission
        self.controle_group = GroupFactory(name="Controle")

        # Create controle user (can read audit logs but not superuser)
        self.controle_user = UsuarioFactory(
            username="controle_audit", email="c@test.com", password="pass1234", cpf=_next_cpf()
        )
        self.controle_user.groups.add(self.controle_group)

        # Create superuser
        self.superuser = UsuarioFactory(
            superuser=True, username="super_audit", email="s@test.com", password="pass1234", cpf=_next_cpf()
        )

        # Create audit log with PII
        self.audit = AuditLog.objects.create(
            usuario=self.controle_user,
            action="LOGIN",
            model_name="Usuario",
            details={
                "ip_address": "203.0.113.50",
                "user_agent": "Mozilla/5.0 (X11; Linux)",
                "google_email": "user@gmail.com",
                "reason": "success",
            },
        )

        self.client = APIClient()

    def test_controle_sees_redacted_details(self):
        self.client.force_authenticate(user=self.controle_user)
        response = self.client.get("/api/audit-logs/")
        assert response.status_code == 200
        data = response.json()
        results = data.get("results", data) if isinstance(data, dict) else data
        if isinstance(results, dict):
            results = results.get("results", [])
        assert len(results) > 0

        details = results[0]["details"]
        # IP masked
        assert details["ip_address"] == "203.0.113.***"
        # user_agent removed
        assert "user_agent" not in details
        # google_email masked
        assert details["google_email"] == "u***@gmail.com"
        # Non-PII preserved
        assert details["reason"] == "success"

    def test_superuser_sees_full_details(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get("/api/audit-logs/")
        assert response.status_code == 200
        data = response.json()
        results = data.get("results", data) if isinstance(data, dict) else data
        if isinstance(results, dict):
            results = results.get("results", [])
        assert len(results) > 0

        details = results[0]["details"]
        # Full details visible
        assert details["ip_address"] == "203.0.113.50"
        assert details["user_agent"] == "Mozilla/5.0 (X11; Linux)"
        assert details["google_email"] == "user@gmail.com"
        assert details["reason"] == "success"

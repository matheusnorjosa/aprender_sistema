"""
AS v2 — Auditoria Serializers

Serializers para AuditLog.
Clausula Petrea: PA-05 (registro de aprovacoes/reprovacoes).
Type-checked with Pyright (strict mode).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false

from __future__ import annotations

import re
from typing import Any

from rest_framework import serializers  # type: ignore[attr-defined]

from apps.core.models import AuditLog

# SEC-AUDIT-01: PII fields to redact for non-superuser access
_PII_KEYS_TO_REMOVE = {"user_agent"}
_PII_KEYS_TO_MASK = {"ip_address", "google_email"}


def _mask_ip(ip: str) -> str:
    """Mask last octet of IPv4 address: 192.168.1.100 → 192.168.1.***"""
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.***"
    return "***"


def _mask_email(email: str) -> str:
    """Mask email: user@example.com → u***@example.com"""
    match = re.match(r"^(.)", email)
    at_pos = email.find("@")
    if match and at_pos > 0:
        return f"{email[0]}***{email[at_pos:]}"
    return "***"


def _redact_details(details: Any) -> Any:
    """Recursively redact PII from details dict."""
    if not isinstance(details, dict):
        return details

    redacted = {}
    for key, value in details.items():
        if key in _PII_KEYS_TO_REMOVE:
            continue  # Remove entirely
        if key in _PII_KEYS_TO_MASK and isinstance(value, str):
            if key == "ip_address":
                redacted[key] = _mask_ip(value)
            elif key == "google_email":
                redacted[key] = _mask_email(value)
            else:
                redacted[key] = "***"
        elif isinstance(value, dict):
            redacted[key] = _redact_details(value)
        else:
            redacted[key] = value

    return redacted


class AuditLogSerializer(serializers.ModelSerializer):
    """
    Serializer for AuditLog model (read-only).
    PA-05: Usado para rastrear aprovações/reprovações.
    SEC-AUDIT-01: PII redacted for non-superuser; superuser sees full details.
    """

    details = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "usuario",
            "action",
            "details",
            "created_at",
        ]
        read_only_fields = ["id", "usuario", "action", "details", "created_at"]

    def get_details(self, obj: AuditLog) -> Any:
        """Return details with PII redacted for non-superuser."""
        raw = obj.details
        if raw is None:
            return None

        request = self.context.get("request")
        if request and hasattr(request, "user") and request.user.is_superuser:
            return raw  # Superuser sees everything

        return _redact_details(raw)

"""
Fixtures centralizados para todos os testes de apps.core.

Issue #105: Fixtures para eliminar 403 RBAC failures sem alterar endpoints.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from typing import Any

from django.conf import settings

import pytest


def get_field_errors(response) -> dict[str, Any]:
    """
    Extract field errors from standardized API error response.

    The custom exception handler wraps errors in:
    {"detail": "...", "code": "...", "errors": {"field": [...]}}

    This helper returns the 'errors' dict if present, or response.data as-is
    for backwards compatibility with tests that check field-level errors.

    Usage in tests:
        errors = get_field_errors(response)
        assert "fim" in errors
        assert "message" in str(errors["fim"])
    """
    if isinstance(response.data, dict) and "errors" in response.data:
        return response.data["errors"]
    return response.data


@pytest.fixture(autouse=True)
def force_service_account_mode():
    """
    Remove GCAL_AUTH_MODE from settings to force service_account default.

    Issue #105: Testes falhavam com 403 porque Docker tem GCAL_AUTH_MODE=oauth
    e usuários de teste não têm GoogleOAuthCredential. Esta fixture remove o
    atributo para que getattr(settings, "GCAL_AUTH_MODE", "service_account")
    retorne o default "service_account".

    Aplicado a TODOS os testes via autouse=True para garantir comportamento
    consistente em testes de publish, preview, e outros endpoints GCal.
    """
    original_value = getattr(settings, "GCAL_AUTH_MODE", None)

    # Remove o atributo para forçar uso do default
    if hasattr(settings, "GCAL_AUTH_MODE"):
        delattr(settings, "GCAL_AUTH_MODE")

    yield

    # Restore original value
    if original_value is not None:
        settings.GCAL_AUTH_MODE = original_value

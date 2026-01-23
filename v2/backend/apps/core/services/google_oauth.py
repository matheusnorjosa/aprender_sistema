"""
AS v2 — Google OAuth 2.0 Service

§7 Epic #459: Refactored to delegate to modular services.

This module re-exports all functions from:
- oauth.token_manager: Encryption, refresh, revoke, key rotation
- oauth.oauth_flow: Authorization URL, code exchange, state validation

Implementa fluxo OAuth 2.0 para Google Calendar com segurança reforçada:
- Criptografia Fernet com chave dedicada (GCAL_ENCRYPTION_KEY)
- Refresh thread-safe com select_for_update (GAP-1: Concorrência)
- Validação de domínio (@aprendereditora.com.br)
- Auditoria completa (AuditLog)
- Rotação de chave zero-downtime

Refs:
- Sprint 1 (Issue #1): Core OAuth Backend
- GAP-1: Concorrência com select_for_update
- GAP-2: Encryption key dedicada
- GAP-3: Rate limiting (aplicado nas views)
- PA-05: Auditoria obrigatória
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false, reportIndexIssue=false, reportOperatorIssue=false, reportUnknownLambdaType=false, reportMissingTypeArgument=false, reportUndefinedVariable=false, reportMissingImports=false, reportPrivateUsage=false

from __future__ import annotations

# §7 Epic #459: Re-export from modular services for backward compatibility
# Import requests at module level for test mocking (tests mock apps.core.services.google_oauth.requests)
import requests  # noqa: F401

from apps.core.services.oauth.oauth_flow import (
    _is_safe_url,
    build_authorization_url,
    exchange_code_for_tokens,
    validate_oauth_state,
)
from apps.core.services.oauth.token_manager import (
    _decrypt_token,
    _encrypt_token,
    _get_fernet_key,
    decrypt_token,
    encrypt_token,
    refresh_access_token_safe,
    revoke_token,
    rotate_encryption_key,
)

__all__ = [
    # Token management (public API)
    "encrypt_token",
    "decrypt_token",
    "refresh_access_token_safe",
    "revoke_token",
    "rotate_encryption_key",
    # OAuth flow (public API)
    "build_authorization_url",
    "exchange_code_for_tokens",
    "validate_oauth_state",
    # Internal helpers (for backward compatibility and test mocking)
    "_encrypt_token",
    "_decrypt_token",
    "_get_fernet_key",
    "_is_safe_url",
    "requests",  # For test mocking (tests mock apps.core.services.google_oauth.requests)
]

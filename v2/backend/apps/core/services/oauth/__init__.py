"""
OAuth Service Package - §7 Epic #459

Modularized OAuth services for Google Calendar integration.
Re-exports from token_manager and oauth_flow for convenience.
"""
# pyright: reportUnknownVariableType=false, reportMissingImports=false

from .oauth_flow import (
    build_authorization_url,
    exchange_code_for_tokens,
    validate_oauth_state,
)
from .token_manager import (
    _get_fernet_key,
    decrypt_token,
    encrypt_token,
    refresh_access_token_safe,
    revoke_token,
    rotate_encryption_key,
)

__all__ = [
    # Token management
    "encrypt_token",
    "decrypt_token",
    "refresh_access_token_safe",
    "revoke_token",
    "rotate_encryption_key",
    # OAuth flow
    "build_authorization_url",
    "exchange_code_for_tokens",
    "validate_oauth_state",
]

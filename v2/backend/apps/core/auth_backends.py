"""
Custom authentication backends for Aprender Sistema v2.

Implements CPF-based authentication alongside username authentication.
"""

from __future__ import annotations

from typing import Any, cast

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.http import HttpRequest

from .auth_normalize import normalize_login_identifier
from .models import Usuario

User = get_user_model()

# Um CPF só-dígitos tem 11 caracteres.
_CPF_DIGITS = 11


class CPFOrUsernameBackend(ModelBackend):
    """
    Authentication backend that accepts CPF or username.

    Login flow:
    1. Remove punctuation from input (dots, hyphens)
    2. If result is 11 digits → try CPF lookup
    3. Otherwise → try username lookup
    4. Validate password and user_can_authenticate

    Examples:
        - "123.456.789-01" → CPF lookup
        - "12345678901" → CPF lookup
        - "joao" → username lookup
        - "joao@example.com" → username lookup (not email)
    """

    def authenticate(
        self, request: HttpRequest | None, username: str | None = None, password: str | None = None, **kwargs: Any
    ) -> Usuario | None:
        """
        Authenticate user by CPF or username.

        Args:
            request: HTTP request object
            username: CPF (with/without mask) or username
            password: User password
            **kwargs: Additional authentication parameters

        Returns:
            Usuario instance if authentication succeeds, None otherwise
        """
        # None E não-string (M03-12: DRF pode passar list/dict do JSON) num só guard:
        # identificador não-string nunca deve chegar à normalização (evita
        # AttributeError/TypeError → 500). Trata como credencial inválida.
        if not isinstance(username, str) or not isinstance(password, str):
            return None

        # Canonicaliza via SSOT — o MESMO valor usado pelo contador de lockout (M03-03).
        canonical = normalize_login_identifier(username)

        # Try CPF if canonical form is 11 digits
        if len(canonical) == _CPF_DIGITS and canonical.isdigit():
            try:
                user = User.objects.get(cpf=canonical)
            except User.DoesNotExist:
                # CPF not found, return None
                return None
        else:
            # Try username lookup (canonical == input cru para não-CPF)
            try:
                user = User.objects.get(username=canonical)
            except User.DoesNotExist:
                return None

        # Validate password and user status
        if user.check_password(password) and self.user_can_authenticate(user):
            return cast(Usuario, user)

        return None

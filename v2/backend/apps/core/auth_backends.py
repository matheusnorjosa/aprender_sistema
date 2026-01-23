"""
Custom authentication backends for Aprender Sistema v2.

Implements CPF-based authentication alongside username authentication.
"""

from __future__ import annotations

import re
from typing import Any, cast

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.http import HttpRequest

from .models import Usuario

User = get_user_model()


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
        if username is None or password is None:
            return None

        # Remove punctuation (dots, hyphens, spaces)
        clean_input = re.sub(r"[.\-\s]", "", username)

        # Try CPF if input is 11 digits
        if clean_input.isdigit() and len(clean_input) == 11:
            try:
                user = User.objects.get(cpf=clean_input)
            except User.DoesNotExist:
                # CPF not found, return None
                return None
        else:
            # Try username lookup
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return None

        # Validate password and user status
        if user.check_password(password) and self.user_can_authenticate(user):
            return cast(Usuario, user)

        return None

"""
Hardening: ``google_oauth_start`` valida que ``auth_url`` aponta para
``accounts.google.com`` antes do redirect. Cobre CodeQL py/url-redirection #3
em ``views_oauth.py:245``.

Defesa em profundidade — ``build_authorization_url`` em ``services/google_oauth.py``
já é controlado, mas adicionar barreira no view garante que mudança
acidental do serviço (ex: bug, env injection, refactor) não vire
open-redirect.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportCallIssue=false

from __future__ import annotations

import pytest

from apps.core.views_oauth import GOOGLE_OAUTH_AUTHORIZED_HOSTS, _is_google_oauth_authorize_url


class TestIsGoogleOauthAuthorizeUrl:
    @pytest.mark.parametrize(
        "valid",
        [
            "https://accounts.google.com/o/oauth2/v2/auth?client_id=x",
            "https://accounts.google.com/o/oauth2/v2/auth",
            "https://accounts.google.com/",
            "https://accounts.google.com",
        ],
    )
    def test_valid_google_url_passes(self, valid):
        assert _is_google_oauth_authorize_url(valid) is True

    def test_none_rejected(self):
        assert _is_google_oauth_authorize_url(None) is False

    def test_empty_string_rejected(self):
        assert _is_google_oauth_authorize_url("") is False

    def test_non_string_rejected(self):
        assert _is_google_oauth_authorize_url(12345) is False
        assert _is_google_oauth_authorize_url(["https://accounts.google.com"]) is False

    @pytest.mark.parametrize(
        "malicious",
        [
            # Subdomain spoofing
            "https://accounts.google.com.evil.com/oauth",
            "https://evil.com/accounts.google.com",
            "https://evil.com?next=accounts.google.com",
            # Schemes proibidos
            "http://accounts.google.com/oauth",  # plain HTTP
            "javascript:alert(1)",
            "data:text/html,<script>",
            "file:///etc/passwd",
            "ftp://accounts.google.com/",
            # Protocol-relative
            "//accounts.google.com/",
            "//evil.com/",
            # Outros hosts Google que não são OAuth authorize
            "https://www.google.com/",
            "https://accounts.googleapis.com/",
            "https://oauth2.googleapis.com/",
            # Sem netloc
            "https://",
        ],
    )
    def test_malicious_url_rejected(self, malicious):
        assert _is_google_oauth_authorize_url(malicious) is False, f"Should reject: {malicious!r}"


class TestAuthorizedHostsAllowlist:
    def test_is_frozen(self):
        assert isinstance(GOOGLE_OAUTH_AUTHORIZED_HOSTS, frozenset)

    def test_contains_only_accounts_google(self):
        # Sanity: garante que ninguém ampliou a lista sem revisão de segurança.
        assert GOOGLE_OAUTH_AUTHORIZED_HOSTS == frozenset({"accounts.google.com"})

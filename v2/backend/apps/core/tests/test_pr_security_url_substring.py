"""
Hardening: validações de URL/Client ID em ``v2/infra/validate_oauth_config.py``
não usam mais ``"x" in value``. Cobre CodeQL py/incomplete-url-substring-sanitization
#7 (validate_oauth_config.py:60).

Alert #6 (test_gcal_meet_link_by_mode.py:102) é fechado no próprio arquivo de
teste, trocando ``"meet.google.com" in url`` por ``urlparse(url).hostname == "meet.google.com"``.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportCallIssue=false, reportMissingImports=false

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# ``validate_oauth_config.py`` vive em ``v2/infra/`` (script standalone fora do
# pacote Django). Adiciona ao sys.path para conseguir importar nos testes.
_INFRA_DIR = Path(__file__).resolve().parents[4] / "infra"
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

from validate_oauth_config import validate_client_id, validate_redirect_uri  # noqa: E402


class TestValidateClientId:
    @pytest.mark.parametrize(
        "valid",
        [
            "619322948464-abc123.apps.googleusercontent.com",
            "111-xyz.apps.googleusercontent.com",
            "1234567890-abcdef0123456789.apps.googleusercontent.com",
        ],
    )
    def test_valid_format_passes(self, valid):
        assert validate_client_id(valid) is True

    def test_none_rejected(self):
        assert validate_client_id(None) is False

    def test_empty_string_rejected(self):
        assert validate_client_id("") is False

    def test_non_string_rejected(self):
        assert validate_client_id(12345) is False
        assert validate_client_id([]) is False

    @pytest.mark.parametrize(
        "malicious",
        [
            # Substring bypass clássicos
            "evil.com/.apps.googleusercontent.com",
            "https://evil.com?next=.apps.googleusercontent.com",
            "evil.com#.apps.googleusercontent.com",
            "user@evil.com:1234/.apps.googleusercontent.com",
            # Sufixo errado
            "abc.apps.googleusercontent.com.evil.com",
            "abc.apps.googleusercontent.org",
            "abc.apps.googleusercontent.co",
            # Apenas o sufixo (sem prefixo)
            ".apps.googleusercontent.com",
            "apps.googleusercontent.com",
            # Whitespace embutido
            "abc .apps.googleusercontent.com",
            "abc\n.apps.googleusercontent.com",
        ],
    )
    def test_bypass_attempts_rejected(self, malicious):
        assert validate_client_id(malicious) is False, f"Should reject: {malicious!r}"


class TestValidateRedirectUri:
    @pytest.mark.parametrize(
        "valid",
        [
            "http://localhost:8000/callback",
            "https://aprendersistema.com.br/oauth/callback",
            "https://app.example.com/path",
        ],
    )
    def test_valid_passes(self, valid):
        assert validate_redirect_uri(valid) is True

    @pytest.mark.parametrize(
        "invalid",
        [
            "",
            "ftp://example.com",
            "javascript:alert(1)",
            "data:text/html,<script>",
            "file:///etc/passwd",
            "//evil.com",  # protocol-relative
            "https://",  # sem netloc
            "not-a-url",
            "http:",  # sem netloc
        ],
    )
    def test_invalid_rejected(self, invalid):
        assert validate_redirect_uri(invalid) is False, f"Should reject: {invalid!r}"

    def test_none_rejected(self):
        assert validate_redirect_uri(None) is False

    def test_non_string_rejected(self):
        assert validate_redirect_uri(42) is False

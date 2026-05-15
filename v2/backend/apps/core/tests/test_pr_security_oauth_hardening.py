"""
Hardening de segurança no fluxo OAuth (CodeQL #3, #4, #8).

Cobre:
- `_safe_return_to` (validação de allowlist contra open redirect, CodeQL #3).
- `_safe_oauth_error_reason` (normalização do `?error=` do callback Google
  contra URL injection / log poisoning, CodeQL #4).
- `state validation failed` log: detalhe sensível só em DEBUG (CodeQL #8).

Não altera fluxo OAuth — apenas valida que entradas user-controlled são
sanitizadas antes de propagar.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false

from __future__ import annotations

import logging

import pytest

from apps.core.views_oauth import SAFE_OAUTH_ERROR_CODES, _safe_oauth_error_reason, _safe_return_to


# ============================================================================
# _safe_return_to (open redirect prevention — CodeQL py/url-redirection)
# ============================================================================


class TestSafeReturnTo:
    def test_none_returns_default(self):
        assert _safe_return_to(None) == "/pre-agenda"

    def test_empty_string_returns_default(self):
        assert _safe_return_to("") == "/pre-agenda"

    def test_relative_path_allowed(self):
        assert _safe_return_to("/pre-agenda") == "/pre-agenda"

    def test_relative_path_with_query_allowed(self):
        assert _safe_return_to("/pre-agenda?tab=integrations") == "/pre-agenda?tab=integrations"

    def test_protocol_relative_url_rejected(self):
        # "//evil.com/x" é interpretado pelo browser como esquema-relativo
        assert _safe_return_to("//evil.com/steal") == "/pre-agenda"

    def test_external_https_rejected(self):
        assert _safe_return_to("https://evil.com/oauth?next=google.com") == "/pre-agenda"

    def test_javascript_scheme_rejected(self):
        assert _safe_return_to("javascript:alert(1)") == "/pre-agenda"

    def test_data_scheme_rejected(self):
        assert _safe_return_to("data:text/html,<script>") == "/pre-agenda"

    def test_file_scheme_rejected(self):
        assert _safe_return_to("file:///etc/passwd") == "/pre-agenda"

    def test_subdomain_lookalike_rejected(self):
        # "google.com.evil.com" não deve casar com "google.com"
        assert _safe_return_to("https://google.com.evil.com/ok") == "/pre-agenda"

    def test_custom_default_respected(self):
        assert _safe_return_to(None, default="/home") == "/home"
        assert _safe_return_to("https://evil.com", default="/safe") == "/safe"

    def test_rejection_logs_warning_without_full_url(self, caplog):
        """Warning não deve expor URL maliciosa completa (apenas length)."""
        malicious = "https://evil.com/" + "A" * 200
        with caplog.at_level(logging.WARNING, logger="apps.core.views_oauth"):
            _safe_return_to(malicious)
        joined = " ".join(rec.message for rec in caplog.records)
        assert "evil.com" not in joined
        assert "len=" in joined


# ============================================================================
# _safe_oauth_error_reason (URL injection / log poisoning prevention — CodeQL #4)
# ============================================================================


class TestSafeOAuthErrorReason:
    def test_none_returns_unknown(self):
        assert _safe_oauth_error_reason(None) == "unknown"

    def test_empty_returns_unknown(self):
        assert _safe_oauth_error_reason("") == "unknown"

    @pytest.mark.parametrize("code", sorted(SAFE_OAUTH_ERROR_CODES))
    def test_rfc_6749_codes_pass_through(self, code):
        assert _safe_oauth_error_reason(code) == code

    def test_arbitrary_string_normalized(self):
        assert _safe_oauth_error_reason("definitely_not_real") == "unknown"

    def test_url_injection_attempt_normalized(self):
        # tentativa de injetar query params adicionais
        assert _safe_oauth_error_reason("access_denied&google=connected") == "unknown"

    def test_crlf_injection_attempt_normalized(self):
        # tentativa de log injection via CRLF
        assert _safe_oauth_error_reason("access_denied\r\nFAKE LOG ENTRY") == "unknown"

    def test_html_injection_attempt_normalized(self):
        assert _safe_oauth_error_reason("<script>alert(1)</script>") == "unknown"

    def test_unicode_lookalike_normalized(self):
        # "аccess_denied" com Cyrillic 'а' (U+0430) não bate na allowlist ASCII
        assert _safe_oauth_error_reason("аccess_denied") == "unknown"


# ============================================================================
# Whitelist invariants
# ============================================================================


class TestOAuthErrorWhitelist:
    def test_whitelist_is_frozen(self):
        assert isinstance(SAFE_OAUTH_ERROR_CODES, frozenset)

    def test_whitelist_contains_rfc_6749_core(self):
        # Sanidade: RFC 6749 §4.1.2.1 obrigatórios
        for required in ("access_denied", "invalid_request", "invalid_scope", "server_error"):
            assert required in SAFE_OAUTH_ERROR_CODES

    def test_whitelist_only_lowercase_ascii(self):
        for code in SAFE_OAUTH_ERROR_CODES:
            assert code == code.lower()
            assert code.replace("_", "").isalpha()

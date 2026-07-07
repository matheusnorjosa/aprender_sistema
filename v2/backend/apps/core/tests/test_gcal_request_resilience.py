"""Testes de resiliencia do request-path do GCal (Onda 4 hardening).

(1) Retry cap: as operacoes de LEITURA (list_calendars/list_events), que rodam no
    request-path, usam settings.GCAL_REQUEST_MAX_RETRIES (default 1) em vez do 3 dos
    writes — para o backoff de 429/5xx nao empilhar ~7s sobre o GCAL_HTTP_TIMEOUT e
    segurar o worker do gunicorn (incidente 2026-07-06).
(2) Timeout OAuth: os requests ao endpoint de token do Google usam
    settings.GCAL_OAUTH_TOKEN_TIMEOUT (nao um literal hardcodado).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownLambdaType=false, reportOptionalMemberAccess=false

from __future__ import annotations

import re
from datetime import timedelta
from pathlib import Path

from django.conf import settings as django_settings
from django.utils import timezone


def _build_google_client(monkeypatch):
    monkeypatch.setattr(
        "apps.core.services.gcal_google_client.service_account.Credentials.from_service_account_info",
        lambda info, scopes: object(),
    )
    monkeypatch.setattr("apps.core.services.gcal_google_client.build", lambda *a, **k: object())
    from apps.core.services.gcal_google_client import GoogleCalendarClient

    return GoogleCalendarClient(credentials_json='{"type": "service_account"}')


def _build_oauth_client(monkeypatch):
    monkeypatch.setenv("GCAL_OAUTH_CLIENT_ID", "cid")
    monkeypatch.setenv("GCAL_OAUTH_CLIENT_SECRET", "secret")
    monkeypatch.setattr("apps.core.services.google_oauth._decrypt_token", lambda enc: "tok")
    monkeypatch.setattr("apps.core.services.gcal_oauth_client.build", lambda *a, **k: object())
    from apps.core.models import GoogleOAuthCredential

    cred = GoogleOAuthCredential(
        google_email="op@aprendereditora.com.br",
        token_expiry=timezone.now() + timedelta(hours=1),
        access_token_encrypted=b"x",
        refresh_token_encrypted=b"y",
    )
    from apps.core.services.gcal_oauth_client import OAuthCalendarClient

    return OAuthCalendarClient(cred)


def test_google_client_list_usa_request_max_retries(monkeypatch, settings):
    settings.GCAL_REQUEST_MAX_RETRIES = 2  # valor distintivo do default (1): prova que le do setting
    client = _build_google_client(monkeypatch)
    seen: list[int] = []
    monkeypatch.setattr(client, "_retry_with_backoff", lambda func, max_retries=3: seen.append(max_retries) or [])

    client.list_calendars()
    client.list_events("cal")

    assert seen == [2, 2]  # ambas as leituras usam o valor do setting (nao o default 3, nem um literal)


def test_oauth_client_list_usa_request_max_retries(monkeypatch, settings):
    settings.GCAL_REQUEST_MAX_RETRIES = 2  # valor distintivo do default (1): prova que le do setting
    client = _build_oauth_client(monkeypatch)
    seen: list[int] = []
    monkeypatch.setattr(client, "_retry_with_backoff", lambda func, max_retries=3: seen.append(max_retries) or [])

    client.list_calendars()
    client.list_events("cal")

    assert seen == [2, 2]  # usa o valor do setting (nao o default 3, nem um literal)


def test_writes_nao_sao_capados_seguem_no_default_3():
    """Guard: insert/update/delete (celery-path) NAO devem passar max_retries (ficam em 3)."""
    src_oauth = (Path(django_settings.BASE_DIR) / "apps" / "core" / "services" / "gcal_oauth_client.py").read_text(
        encoding="utf-8"
    )
    src_google = (Path(django_settings.BASE_DIR) / "apps" / "core" / "services" / "gcal_google_client.py").read_text(
        encoding="utf-8"
    )
    for src in (src_oauth, src_google):
        # so os _list_* devem passar max_retries; insert/update/delete/get nao.
        for fn in ("_insert", "_update", "_delete", "_get"):
            assert (
                f"_retry_with_backoff({fn}, max_retries=" not in src
            ), f"{fn} nao deve ser capado (celery-path mantem resiliencia em 3)"


def test_oauth_requests_usam_setting_de_timeout_nao_literal():
    """Os requests do fluxo OAuth (exchange/userinfo/refresh/revoke) nao hardcodam timeout."""
    base = Path(django_settings.BASE_DIR) / "apps" / "core" / "services" / "oauth"
    for name in ("oauth_flow.py", "token_manager.py"):
        src = (base / name).read_text(encoding="utf-8")
        hardcoded = re.findall(r"requests\.(?:get|post)\([^)]*timeout\s*=\s*\d", src)
        assert not hardcoded, f"{name}: requests com timeout hardcodado: {hardcoded}"
        assert "settings.GCAL_OAUTH_TOKEN_TIMEOUT" in src, f"{name} nao usa GCAL_OAUTH_TOKEN_TIMEOUT"


def test_exchange_code_passa_oauth_token_timeout_ao_requests(monkeypatch, settings):
    """Comportamental: exchange_code_for_tokens REALMENTE passa o timeout do setting ao requests.

    Complementa o source-scan acima: prova que o valor CHEGA no requests (nao so que a
    string aparece no fonte). Cobre os 2 call-sites de oauth_flow (token + userinfo).
    """
    settings.GCAL_OAUTH_TOKEN_TIMEOUT = 7  # distintivo do default 5
    monkeypatch.setenv("GCAL_OAUTH_CLIENT_ID", "cid")
    monkeypatch.setenv("GCAL_OAUTH_CLIENT_SECRET", "secret")
    monkeypatch.setenv("GCAL_OAUTH_REDIRECT_URI", "https://x/callback")
    seen: dict[str, object] = {}

    class _Resp:
        def raise_for_status(self) -> None: ...

        def json(self) -> dict[str, object]:
            return {
                "refresh_token": "r",
                "access_token": "a",
                "expires_in": 3600,
                "token_type": "Bearer",
                "scope": "https://www.googleapis.com/auth/calendar",
                "email": "op@aprendereditora.com.br",
                "id": "123",
                "verified_email": True,
                "name": "Operador",
            }

    monkeypatch.setattr(
        "apps.core.services.oauth.oauth_flow.requests.post",
        lambda url, data=None, timeout=None: seen.update(post=timeout) or _Resp(),
    )
    monkeypatch.setattr(
        "apps.core.services.oauth.oauth_flow.requests.get",
        lambda url, headers=None, timeout=None: seen.update(get=timeout) or _Resp(),
    )

    from apps.core.services.oauth.oauth_flow import exchange_code_for_tokens

    exchange_code_for_tokens("authcode")

    assert seen["post"] == 7  # troca code->token usa o setting
    assert seen["get"] == 7  # userinfo usa o setting

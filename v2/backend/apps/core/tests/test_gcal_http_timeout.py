"""Testes do timeout no transporte dos clients Google Calendar.

Regressao do incidente 2026-07-06: os clients usavam o default de 60s do googleapiclient
no transporte httplib2 (`build_http`/`DEFAULT_HTTP_TIMEOUT_SEC`), alto demais p/ o
request-path -> num stall de rede uma rajada de chamadas segurava os workers do gunicorn
por ate 60s (endpoints /api/integrations/google/calendars, /events, /api/gcal/calendars,
/api/gcal/health). Estes testes travam que AMBOS os clients (Service Account e OAuth)
constroem o service com `settings.GCAL_HTTP_TIMEOUT` (default 10s) no transporte. O
`build` do googleapiclient e mockado; a asercao checa o timeout do http subjacente.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownLambdaType=false, reportOptionalMemberAccess=false

from __future__ import annotations

from datetime import timedelta

from django.conf import settings as django_settings
from django.utils import timezone


def test_setting_gcal_http_timeout_e_inteiro_positivo():
    """O timeout tem que ser inteiro positivo (0 = socket nao-bloqueante, quebraria tudo)."""
    assert isinstance(django_settings.GCAL_HTTP_TIMEOUT, int)
    assert django_settings.GCAL_HTTP_TIMEOUT > 0


def test_google_client_aplica_timeout_no_transporte(monkeypatch, settings):
    """GoogleCalendarClient (Service Account) constroi o service com o timeout."""
    settings.GCAL_HTTP_TIMEOUT = 13
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "apps.core.services.gcal_google_client.service_account.Credentials.from_service_account_info",
        lambda info, scopes: object(),
    )
    monkeypatch.setattr(
        "apps.core.services.gcal_google_client.build",
        lambda *a, **k: captured.update(http=k.get("http"), cache_discovery=k.get("cache_discovery")) or object(),
    )

    from apps.core.services.gcal_google_client import GoogleCalendarClient

    GoogleCalendarClient(credentials_json='{"type": "service_account"}')

    # AuthorizedHttp expoe o transporte subjacente em .http; o timeout tem que estar la.
    assert captured["http"].http.timeout == 13
    assert captured["cache_discovery"] is False


def test_oauth_client_aplica_timeout_no_transporte(monkeypatch, settings):
    """OAuthCalendarClient (o client de prod, GCAL_AUTH_MODE=oauth) usa o timeout."""
    settings.GCAL_HTTP_TIMEOUT = 9
    captured: dict[str, object] = {}

    monkeypatch.setenv("GCAL_OAUTH_CLIENT_ID", "cid")
    monkeypatch.setenv("GCAL_OAUTH_CLIENT_SECRET", "secret")
    monkeypatch.setattr("apps.core.services.google_oauth._decrypt_token", lambda enc: "tok")
    monkeypatch.setattr(
        "apps.core.services.gcal_oauth_client.build",
        lambda *a, **k: captured.update(http=k.get("http")) or object(),
    )

    from apps.core.models import GoogleOAuthCredential

    # Instancia NAO-salva (sem DB): isinstance passa, is_expired()=False evita refresh.
    cred = GoogleOAuthCredential(
        google_email="op@aprendereditora.com.br",
        token_expiry=timezone.now() + timedelta(hours=1),
        access_token_encrypted=b"enc-access",
        refresh_token_encrypted=b"enc-refresh",
    )

    from apps.core.services.gcal_oauth_client import OAuthCalendarClient

    OAuthCalendarClient(cred)

    assert captured["http"].http.timeout == 9

"""Testes de resiliencia do request-path do GCal (Onda 4 hardening).

(1) Retry cap: as operacoes de LEITURA (list_calendars/list_events), que rodam no
    request-path, usam settings.GCAL_REQUEST_MAX_RETRIES (default 1) em vez do
    NUM_RETRIES_GOOGLE (3) dos writes — para o backoff de 429/5xx nao empilhar sobre o
    GCAL_HTTP_TIMEOUT e segurar o worker do gunicorn (incidente 2026-07-06). Desde o FER-60
    o retry e o da propria biblioteca do Google: o limite chega como `execute(num_retries=N)`.
(2) Timeout OAuth: os requests ao endpoint de token do Google usam
    settings.GCAL_OAUTH_TOKEN_TIMEOUT (nao um literal hardcodado).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownLambdaType=false, reportOptionalMemberAccess=false

from __future__ import annotations

import re
from datetime import timedelta
from pathlib import Path
from typing import Any

from django.conf import settings as django_settings
from django.utils import timezone

import pytest

from apps.core.services.gcal.utils import NUM_RETRIES_GOOGLE


class _Pedido:
    """Requisicao do googleapiclient em memoria: anota o `num_retries` com que foi executada."""

    def __init__(self, nome: str, anotados: list[tuple[str, int]], resposta: Any) -> None:
        self._nome = nome
        self._anotados = anotados
        self._resposta = resposta

    def execute(self, num_retries: int = 0) -> Any:
        self._anotados.append((self._nome, num_retries))
        return self._resposta


class _Recurso:
    def __init__(self, prefixo: str, anotados: list[tuple[str, int]]) -> None:
        self._prefixo = prefixo
        self._anotados = anotados

    def __getattr__(self, metodo: str):
        resposta = {"items": []} if metodo == "list" else {"id": "asv2-1"}
        return lambda **_params: _Pedido(f"{self._prefixo}.{metodo}", self._anotados, resposta)


class _ServicoQueAnota:
    def __init__(self) -> None:
        self.anotados: list[tuple[str, int]] = []

    def events(self) -> _Recurso:
        return _Recurso("events", self.anotados)

    def calendarList(self) -> _Recurso:
        return _Recurso("calendarList", self.anotados)


def _build_google_client(monkeypatch, servico: _ServicoQueAnota):
    monkeypatch.setattr(
        "apps.core.services.gcal_google_client.service_account.Credentials.from_service_account_info",
        lambda info, scopes: object(),
    )
    monkeypatch.setattr("apps.core.services.gcal_google_client.build", lambda *a, **k: servico)
    from apps.core.services.gcal_google_client import GoogleCalendarClient

    return GoogleCalendarClient(credentials_json='{"type": "service_account"}')


def _build_oauth_client(monkeypatch, servico: _ServicoQueAnota):
    monkeypatch.setenv("GCAL_OAUTH_CLIENT_ID", "cid")
    monkeypatch.setenv("GCAL_OAUTH_CLIENT_SECRET", "secret")
    monkeypatch.setattr("apps.core.services.google_oauth._decrypt_token", lambda enc: "tok")
    monkeypatch.setattr("apps.core.services.gcal_oauth_client.build", lambda *a, **k: servico)
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
    servico = _ServicoQueAnota()
    client = _build_google_client(monkeypatch, servico)

    client.list_calendars()
    client.list_events("cal")

    # ambas as leituras usam o valor do setting (nao o NUM_RETRIES_GOOGLE, nem um literal)
    assert servico.anotados == [("calendarList.list", 2), ("events.list", 2)]


def test_oauth_client_list_usa_request_max_retries(monkeypatch, settings):
    settings.GCAL_REQUEST_MAX_RETRIES = 2  # valor distintivo do default (1): prova que le do setting
    servico = _ServicoQueAnota()
    client = _build_oauth_client(monkeypatch, servico)

    client.list_calendars()
    client.list_events("cal")

    # usa o valor do setting (nao o NUM_RETRIES_GOOGLE, nem um literal)
    assert servico.anotados == [("calendarList.list", 2), ("events.list", 2)]


@pytest.mark.parametrize("tipo", ["google", "oauth"])
def test_writes_nao_sao_capados_seguem_em_num_retries_google(monkeypatch, settings, tipo):
    """Guard: get/insert/update/delete (celery-path) NAO usam o cap do request-path (ficam em 3).

    FER-60: e a unica camada de retry; o metodo `_retry_with_backoff` dos clientes nao volta.
    """
    settings.GCAL_REQUEST_MAX_RETRIES = 0  # distintivo: um write capado apareceria com 0
    servico = _ServicoQueAnota()
    client = (
        _build_google_client(monkeypatch, servico) if tipo == "google" else _build_oauth_client(monkeypatch, servico)
    )

    client.get("cal", "asv2-1")
    client.insert("cal", "asv2-1", {"summary": "x"})
    client.update("cal", "asv2-1", {"summary": "x"})
    client.delete("cal", "asv2-1")
    esperados = ["events.get", "events.insert", "events.patch", "events.delete"]  # update vai por PATCH
    if tipo == "oauth":
        client.patch_descricao("cal", "asv2-1", "nova")
        esperados.append("events.patch")

    assert NUM_RETRIES_GOOGLE == 3
    assert servico.anotados == [(nome, NUM_RETRIES_GOOGLE) for nome in esperados]
    assert not hasattr(client, "_retry_with_backoff"), "retry numa camada so (FER-60)"


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

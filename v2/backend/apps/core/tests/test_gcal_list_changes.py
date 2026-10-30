"""Leitura incremental do Google (syncToken) para a cópia Google → Sistema (PR-A).

Cobre o `list_changes` do `OAuthCalendarClient` (paginação, máscara `fields`, 410 como
`SyncTokenExpirado`, `nextSyncToken` obrigatório na última página), os logs do cliente sem
e-mail (u<id>) e o fake fiel ao Google (DELETE soft, log de mudanças, 410 programável).

Gotcha (por que handler direto e não caplog): o logger `apps` tem propagate=False, então o
registro não sobe até a raiz onde o caplog escuta (mesmo padrão de test_gcal_insert_log_lgpd.py).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownLambdaType=false, reportOptionalMemberAccess=false, reportOptionalSubscript=false

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta
from typing import Any

from django.utils import timezone

import pytest
from googleapiclient.errors import HttpError
from httplib2 import Response

from apps.core.services import gcal_oauth_client as oauth_module
from apps.core.services.gcal.client import SyncTokenExpirado
from apps.core.services.gcal_fake_client import FakeCalendarClient

EMAIL = "operador-secreto@aprendereditora.com.br"
CAMPOS = "items(id,status,start,end,updated,recurringEventId,recurrence),nextPageToken,nextSyncToken"


def _http_error(status: int) -> HttpError:
    return HttpError(Response({"status": status}), b'{"error": {"message": "x"}}')


class _Requisicao:
    def __init__(self, resposta: Any) -> None:
        self._resposta = resposta

    def execute(self) -> Any:
        resposta = self._resposta() if callable(self._resposta) else self._resposta
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


class _Eventos:
    def __init__(self, respostas: list[Any]) -> None:
        self.respostas = respostas
        self.chamadas: list[dict[str, Any]] = []

    def list(self, **params: Any) -> _Requisicao:
        self.chamadas.append(params)
        return _Requisicao(self.respostas.pop(0))


class _Servico:
    def __init__(self, respostas: list[Any]) -> None:
        self.eventos = _Eventos(respostas)

    def events(self) -> _Eventos:
        return self.eventos


def _credencial(expirada: bool = False):
    from apps.core.models import GoogleOAuthCredential

    delta = timedelta(hours=-1) if expirada else timedelta(hours=1)
    return GoogleOAuthCredential(
        user_id=7,
        google_email=EMAIL,
        token_expiry=timezone.now() + delta,
        access_token_encrypted=b"x",
        refresh_token_encrypted=b"y",
    )


def _cliente(monkeypatch, respostas: list[Any] | None = None, expirada: bool = False):
    monkeypatch.setenv("GCAL_OAUTH_CLIENT_ID", "cid")
    monkeypatch.setenv("GCAL_OAUTH_CLIENT_SECRET", "secret")
    monkeypatch.setattr("apps.core.services.google_oauth._decrypt_token", lambda enc: "tok")
    monkeypatch.setattr("apps.core.services.google_oauth.refresh_access_token_safe", lambda cred: cred)
    servico = _Servico(respostas or [])
    monkeypatch.setattr("apps.core.services.gcal_oauth_client.build", lambda *a, **k: servico)
    monkeypatch.setattr("apps.core.services.gcal_oauth_client.time.sleep", lambda s: None)
    return oauth_module.OAuthCalendarClient(_credencial(expirada)), servico.eventos


@contextmanager
def _logs() -> Iterator[list[logging.LogRecord]]:
    capturados: list[logging.LogRecord] = []

    class _Cap(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            capturados.append(record)

    handler = _Cap(level=logging.DEBUG)
    oauth_module.logger.addHandler(handler)
    nivel = oauth_module.logger.level
    oauth_module.logger.setLevel(logging.DEBUG)
    try:
        yield capturados
    finally:
        oauth_module.logger.removeHandler(handler)
        oauth_module.logger.setLevel(nivel)


# --- OAuthCalendarClient.list_changes ---


def test_paginacao_junta_paginas_e_devolve_token_da_ultima(monkeypatch):
    cliente, eventos = _cliente(
        monkeypatch,
        [
            {"items": [{"id": "a"}, {"id": "b"}], "nextPageToken": "p2"},
            {"items": [{"id": "c"}], "nextPageToken": "p3"},
            {"items": [{"id": "d", "status": "cancelled"}], "nextSyncToken": "sync-final"},
        ],
    )

    itens, token = cliente.list_changes("cal-org", "sync-antigo")

    assert [i["id"] for i in itens] == ["a", "b", "c", "d"]
    assert token == "sync-final"
    assert [c.get("pageToken") for c in eventos.chamadas] == [None, "p2", "p3"]
    assert all(c["syncToken"] == "sync-antigo" for c in eventos.chamadas)


def test_parametros_com_mascara_fields_exata_e_sem_filtros_incompativeis(monkeypatch):
    cliente, eventos = _cliente(monkeypatch, [{"items": [], "nextSyncToken": "t"}])

    cliente.list_changes("cal-org", "tok")

    params = eventos.chamadas[0]
    assert params["calendarId"] == "cal-org"
    assert params["fields"] == CAMPOS
    assert "attendees" not in params["fields"] and "summary" not in params["fields"]
    assert params["showDeleted"] is True
    assert params["maxResults"] == 2500
    for proibido in ("singleEvents", "orderBy", "timeMin", "timeMax", "updatedMin"):
        assert proibido not in params


def test_sem_token_faz_leitura_completa_sem_sync_token(monkeypatch):
    cliente, eventos = _cliente(monkeypatch, [{"items": [{"id": "a"}], "nextSyncToken": "primeiro"}])

    itens, token = cliente.list_changes("cal-org", None)

    assert itens == [{"id": "a"}]
    assert token == "primeiro"
    assert "syncToken" not in eventos.chamadas[0]


def test_410_vira_sync_token_expirado_sem_retry(monkeypatch):
    cliente, eventos = _cliente(monkeypatch, [_http_error(410), {"items": [], "nextSyncToken": "nunca"}])

    with pytest.raises(SyncTokenExpirado):
        cliente.list_changes("cal-org", "velho")

    assert len(eventos.chamadas) == 1, "410 não pode entrar em retry"


def test_5xx_repete_a_mesma_pagina(monkeypatch):
    # O retry reexecuta a mesma requisição: a 1ª execução dá 503, a 2ª devolve a página.
    tentativas = iter([_http_error(503), {"items": [{"id": "a"}], "nextSyncToken": "t"}])
    cliente, eventos = _cliente(monkeypatch, [lambda: next(tentativas)])

    itens, token = cliente.list_changes("cal-org", "tok")

    assert itens == [{"id": "a"}] and token == "t"
    assert len(eventos.chamadas) == 1, "a página não é pedida de novo, só reexecutada"


def test_ultima_pagina_sem_next_sync_token_e_erro(monkeypatch):
    cliente, _ = _cliente(monkeypatch, [{"items": [{"id": "a"}], "nextPageToken": "p2"}, {"items": []}])

    with pytest.raises(RuntimeError, match="nextSyncToken"):
        cliente.list_changes("cal-org", None)


# --- Logs sem e-mail (u<id>) ---


def test_logs_de_init_e_refresh_sem_email(monkeypatch):
    with _logs() as capturados:
        _cliente(monkeypatch, expirada=True)
        _cliente(monkeypatch, expirada=False)

    mensagens = [r.getMessage() for r in capturados]
    assert mensagens, "init/refresh deveriam logar"
    assert all(EMAIL not in m for m in mensagens), mensagens
    assert any("u7" in m for m in mensagens)


def test_log_de_retry_sem_email(monkeypatch):
    cliente, _ = _cliente(monkeypatch)
    respostas = iter([_http_error(503), "ok"])

    def _func() -> Any:
        r = next(respostas)
        if isinstance(r, Exception):
            raise r
        return r

    with _logs() as capturados:
        assert cliente._retry_with_backoff(_func) == "ok"

    mensagens = [r.getMessage() for r in capturados]
    assert any("503" in m for m in mensagens)
    assert all(EMAIL not in m for m in mensagens), mensagens
    assert any("u7" in m for m in mensagens)


# --- FakeCalendarClient fiel ao Google ---


def _payload(inicio: str = "2026-11-05T12:00:00+00:00", fim: str = "2026-11-05T15:00:00+00:00") -> dict[str, Any]:
    return {
        "summary": "Evento",
        "start": {"dateTime": inicio, "timeZone": "UTC"},
        "end": {"dateTime": fim, "timeZone": "UTC"},
    }


def test_fake_delete_e_soft_e_get_devolve_cancelado():
    fake = FakeCalendarClient()
    fake.insert("cal", "e1", _payload())

    fake.delete("cal", "e1")

    evento = fake.get("cal", "e1")
    assert evento is not None and evento["status"] == "cancelled"
    assert fake.list_events("cal") == [], "listagem padrão do Google não mostra cancelados"


def test_fake_devolve_horario_com_offset_de_fortaleza():
    fake = FakeCalendarClient()
    fake.insert("cal", "e1", _payload())

    evento = fake.get("cal", "e1")

    assert evento["start"]["dateTime"] == "2026-11-05T09:00:00-03:00"
    assert evento["end"]["dateTime"] == "2026-11-05T12:00:00-03:00"


def test_fake_list_changes_completo_e_depois_so_o_que_mudou():
    fake = FakeCalendarClient()
    fake.insert("cal", "e1", _payload())
    fake.insert("cal", "e2", _payload())
    fake.insert("outro", "x1", _payload())

    itens, token = fake.list_changes("cal", None)
    assert sorted(i["id"] for i in itens) == ["e1", "e2"]
    assert all(set(i) <= {"id", "status", "start", "end", "updated", "recurringEventId", "recurrence"} for i in itens)

    fake.update("cal", "e2", _payload(inicio="2026-11-06T12:00:00+00:00", fim="2026-11-06T13:00:00+00:00"))
    fake.delete("cal", "e1")
    fake.insert("outro", "x2", _payload())

    itens, token2 = fake.list_changes("cal", token)
    por_id = {i["id"]: i for i in itens}
    assert set(por_id) == {"e1", "e2"}
    assert por_id["e1"] == {"id": "e1", "status": "cancelled"}, "lápide: só id e status"
    assert por_id["e2"]["start"]["dateTime"] == "2026-11-06T09:00:00-03:00"
    assert token2 != token

    itens, token3 = fake.list_changes("cal", token2)
    assert itens == [] and token3 == token2


def test_fake_410_programavel():
    fake = FakeCalendarClient()
    fake.insert("cal", "e1", _payload())
    _, token = fake.list_changes("cal", None)

    fake.sync_token_expirado = True

    with pytest.raises(SyncTokenExpirado):
        fake.list_changes("cal", token)
    itens, _ = fake.list_changes("cal", None)
    assert [i["id"] for i in itens] == ["e1"], "leitura completa segue funcionando"

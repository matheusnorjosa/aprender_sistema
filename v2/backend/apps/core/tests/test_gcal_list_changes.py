"""Leitura incremental do Google (syncToken) para a cópia Google → Sistema (PR-A).

Cobre o `list_changes` do `OAuthCalendarClient` (paginação, máscara `fields`, 410 como
`SyncTokenExpirado`, `nextSyncToken` obrigatório na última página, repetição de cada página pela
biblioteca do Google desde o FER-60), os logs sem e-mail (u<id>) e o fake fiel ao Google (DELETE soft,
log de mudanças, 410 programável).

Gotcha (por que handler direto e não caplog): o logger `apps` tem propagate=False, então o
registro não sobe até a raiz onde o caplog escuta (mesmo padrão de test_gcal_insert_log_lgpd.py).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownLambdaType=false, reportOptionalMemberAccess=false, reportOptionalSubscript=false

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta
from typing import Any

from django.utils import timezone

import pytest
from googleapiclient.discovery import build
from googleapiclient.http import HttpMockSequence

from apps.core.services import gcal_oauth_client as oauth_module
from apps.core.services.gcal.client import SyncTokenExpirado
from apps.core.services.gcal.utils import NUM_RETRIES_GOOGLE
from apps.core.services.gcal_fake_client import FakeCalendarClient

EMAIL = "operador-secreto@aprendereditora.com.br"
CAMPOS = "items(id,status,start,end,updated,recurringEventId,recurrence),nextPageToken,nextSyncToken"


class _Requisicao:
    def __init__(self, resposta: Any, execucoes: list[int]) -> None:
        self._resposta = resposta
        self._execucoes = execucoes

    def execute(self, num_retries: int = 0) -> Any:
        self._execucoes.append(num_retries)
        resposta = self._resposta() if callable(self._resposta) else self._resposta
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


class _Eventos:
    def __init__(self, respostas: list[Any]) -> None:
        self.respostas = respostas
        self.chamadas: list[dict[str, Any]] = []
        self.num_retries: list[int] = []

    def list(self, **params: Any) -> _Requisicao:
        self.chamadas.append(params)
        return _Requisicao(self.respostas.pop(0), self.num_retries)


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
    return oauth_module.OAuthCalendarClient(_credencial(expirada)), servico.eventos


class _Contador(HttpMockSequence):
    """HttpMockSequence que guarda as URIs pedidas (cada requisição HTTP que saiu)."""

    def __init__(self, respostas: list[tuple[dict[str, str], bytes]]) -> None:
        super().__init__(respostas)
        self.uris: list[str] = []

    def request(self, uri: str, *args: Any, **kwargs: Any) -> Any:
        self.uris.append(uri)
        return super().request(uri, *args, **kwargs)


def _cliente_http(monkeypatch, respostas: list[tuple[dict[str, str], bytes]]):
    """Cliente com o serviço de verdade do googleapiclient sobre respostas HTTP prontas (sem rede).

    Exercita a repetição da própria biblioteca (`execute(num_retries=...)`); o `time.sleep` global não espera.
    """
    monkeypatch.setattr("time.sleep", lambda s: None)
    http = _Contador(respostas)
    servico = build("calendar", "v3", http=http, static_discovery=True, cache_discovery=False)
    monkeypatch.setenv("GCAL_OAUTH_CLIENT_ID", "cid")
    monkeypatch.setenv("GCAL_OAUTH_CLIENT_SECRET", "secret")
    monkeypatch.setattr("apps.core.services.google_oauth._decrypt_token", lambda enc: "tok")
    monkeypatch.setattr("apps.core.services.gcal_oauth_client.build", lambda *a, **k: servico)
    return oauth_module.OAuthCalendarClient(_credencial()), http


def _resp(status: int, corpo: dict[str, Any]) -> tuple[dict[str, str], bytes]:
    return ({"status": str(status)}, json.dumps(corpo).encode())


def _erro_http(status: int) -> tuple[dict[str, str], bytes]:
    return _resp(status, {"error": {"code": status, "message": "x"}})


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


def test_cada_pagina_usa_a_repeticao_da_biblioteca(monkeypatch):
    cliente, eventos = _cliente(
        monkeypatch,
        [{"items": [], "nextPageToken": "p2"}, {"items": [], "nextSyncToken": "t"}],
    )

    cliente.list_changes("cal-org", "tok")

    assert eventos.num_retries == [NUM_RETRIES_GOOGLE, NUM_RETRIES_GOOGLE]


def test_410_vira_sync_token_expirado_sem_retry(monkeypatch):
    cliente, http = _cliente_http(monkeypatch, [_erro_http(410), _resp(200, {"items": [], "nextSyncToken": "nunca"})])

    with pytest.raises(SyncTokenExpirado):
        cliente.list_changes("cal-org", "velho")

    assert len(http.uris) == 1, "410 não pode entrar em retry"


def test_5xx_repete_a_mesma_pagina(monkeypatch):
    # A biblioteca reexecuta a mesma requisição: a 1ª dá 503, a 2ª devolve a página.
    cliente, http = _cliente_http(
        monkeypatch, [_erro_http(503), _resp(200, {"items": [{"id": "a"}], "nextSyncToken": "t"})]
    )

    itens, token = cliente.list_changes("cal-org", "tok")

    assert itens == [{"id": "a"}] and token == "t"
    assert len(http.uris) == 2 and http.uris[0] == http.uris[1], "a mesma página, reexecutada"


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
    # FER-60: o aviso de repetição agora é o da biblioteca (logger googleapiclient.http), com a URI.
    # Pedir o calendário pelo e-mail da conta prova que ele vira 'primary' antes de chegar à URI.
    cliente, _ = _cliente_http(monkeypatch, [_erro_http(503), _resp(200, {"items": [], "nextSyncToken": "t"})])
    capturados: list[logging.LogRecord] = []

    class _Cap(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            capturados.append(record)

    logger_google = logging.getLogger("googleapiclient.http")
    handler = _Cap(level=logging.DEBUG)
    logger_google.addHandler(handler)
    try:
        cliente.list_changes(EMAIL, "tok")
    finally:
        logger_google.removeHandler(handler)

    mensagens = [r.getMessage() for r in capturados]
    assert any("503" in m and "retry" in m for m in mensagens), mensagens
    # Na URI o `@` sai como `%40`: procurar a parte local pega o e-mail nas duas formas.
    assert all("operador-secreto" not in m for m in mensagens), mensagens
    assert any("/calendars/primary/" in m for m in mensagens), mensagens


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

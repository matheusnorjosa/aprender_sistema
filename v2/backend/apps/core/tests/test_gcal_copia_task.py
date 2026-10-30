"""Task periódica da cópia Google → Sistema (PR-C): guardas antes do cliente, uma rodada e um log.

Gotcha (por que handler direto e não caplog): o logger `apps` tem propagate=False, então o
registro não sobe até a raiz onde o caplog escuta (mesmo padrão de test_gcal_copia.py).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownLambdaType=false, reportOptionalMemberAccess=false, reportOptionalSubscript=false, reportIndexIssue=false, reportOperatorIssue=false, reportArgumentType=false, reportCallIssue=false, reportPrivateUsage=false, reportFunctionMemberAccess=false

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta
from datetime import timezone as dt_timezone
from typing import Any
from unittest.mock import Mock

from django.utils import timezone

import pytest

from apps.core import tasks
from apps.core.models import AuditLog, GCalCopiaCursor, GoogleOAuthCredential, Solicitacao, Usuario
from apps.core.services import gcal_client_factory
from apps.core.services.gcal_fake_client import FakeCalendarClient
from apps.core.tests.factories import SolicitacaoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

PINO = "agenda-org@group.calendar.google.com"
FORTALEZA = dt_timezone(timedelta(hours=-3))
EMAIL_OPERADOR = "operadora.secreta@example.invalid"
EMAIL_GOOGLE = "conta.google.secreta@example.invalid"
TITULO_SECRETO = "Formação com Fulana Secreta"


@pytest.fixture(autouse=True)
def _pino(settings):
    settings.GCAL_OAUTH_CALENDAR_ID = PINO


@pytest.fixture
def fake() -> FakeCalendarClient:
    return FakeCalendarClient()


@pytest.fixture
def fabrica(monkeypatch, fake) -> Mock:
    """O montador do cliente OAuth trocado por um mock que devolve o fake (nada de Google)."""
    mock = Mock(return_value=(fake, "primary"))
    monkeypatch.setattr(gcal_client_factory, "get_oauth_client_for_user", mock)
    return mock


@pytest.fixture(autouse=True)
def _sem_fila(monkeypatch) -> None:
    monkeypatch.setattr(tasks.task_gcal_copia_descricao, "delay", lambda *a: None)


def _operador(com_credencial: bool = True) -> Usuario:
    u = UsuarioFactory(email=EMAIL_OPERADOR)
    if com_credencial:
        GoogleOAuthCredential.objects.create(
            user=u,
            google_email=EMAIL_GOOGLE,
            access_token_encrypted=b"x",
            refresh_token_encrypted=b"x",
            token_expiry=timezone.now() + timedelta(hours=1),
            scope="https://www.googleapis.com/auth/calendar",
            default_calendar_id="primary",
        )
    return u


def _cursor(**kw: Any) -> GCalCopiaCursor:
    dados: dict[str, Any] = {"calendar_id": PINO, "ativo": True, "modo": "copiar"}
    dados.update(kw)
    if "operador" not in dados:
        dados["operador"] = _operador()
    return GCalCopiaCursor.objects.create(**dados)


def _publicada(eid: str, dias: int = 3) -> Solicitacao:
    inicio = (timezone.now() + timedelta(days=dias)).replace(minute=0, second=0, microsecond=0)
    return SolicitacaoFactory(
        status="aprovado",
        gcal_status="PUBLISHED",
        external_event_id=eid,
        inicio=inicio,
        fim=inicio + timedelta(hours=2),
    )


def _no_google(fake: FakeCalendarClient, s: Solicitacao) -> None:
    fake.insert(
        PINO,
        s.external_event_id,
        {
            "summary": TITULO_SECRETO,
            "attendees": [{"email": EMAIL_OPERADOR}],
            "start": {"dateTime": s.inicio.isoformat()},
            "end": {"dateTime": s.fim.isoformat()},
        },
    )


@contextmanager
def _logs() -> Iterator[list[logging.LogRecord]]:
    capturados: list[logging.LogRecord] = []

    class _Cap(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            capturados.append(record)

    handler = _Cap(level=logging.DEBUG)
    tasks.logger.addHandler(handler)
    nivel = tasks.logger.level
    tasks.logger.setLevel(logging.DEBUG)
    try:
        yield capturados
    finally:
        tasks.logger.removeHandler(handler)
        tasks.logger.setLevel(nivel)


def _sem_pii(registros: list[logging.LogRecord]) -> None:
    texto = " ".join(r.getMessage() for r in registros)
    for segredo in (EMAIL_OPERADOR, EMAIL_GOOGLE, TITULO_SECRETO, "Fulana"):
        assert segredo not in texto


def _acima_de_info(registros: list[logging.LogRecord]) -> list[logging.LogRecord]:
    return [r for r in registros if r.levelno > logging.INFO]


# --- guardas: nenhuma monta o cliente --------------------------------------------------------------


def test_sem_cursor_e_skipped_sem_cliente(fabrica):
    with _logs() as registros:
        assert tasks.copiar_mudancas_do_google() == "SKIPPED"
    fabrica.assert_not_called()
    assert not [r for r in registros if r.levelno >= logging.INFO]


def test_cursor_desligado_e_skipped_sem_cliente(fabrica):
    _cursor(ativo=False)

    with _logs() as registros:
        assert tasks.copiar_mudancas_do_google() == "SKIPPED"
    fabrica.assert_not_called()
    assert not [r for r in registros if r.levelno >= logging.INFO]


def test_cursor_de_outro_calendario_e_skipped(fabrica):
    _cursor(calendar_id="outra-agenda@group.calendar.google.com")

    assert tasks.copiar_mudancas_do_google() == "SKIPPED"
    fabrica.assert_not_called()


@pytest.mark.parametrize("pino", ["", "primary"])
def test_pino_vazio_ou_primary_com_copia_ligada_e_erro_sem_cliente(fabrica, settings, pino):
    _cursor()
    settings.GCAL_OAUTH_CALENDAR_ID = pino

    with _logs() as registros:
        assert tasks.copiar_mudancas_do_google() == "ERROR"
    fabrica.assert_not_called()
    assert [r for r in registros if r.levelno == logging.ERROR]


@pytest.mark.parametrize("pino", ["", "primary"])
def test_pino_vazio_ou_primary_com_copia_desligada_e_skipped(fabrica, settings, pino):
    _cursor(ativo=False)
    settings.GCAL_OAUTH_CALENDAR_ID = pino

    assert tasks.copiar_mudancas_do_google() == "SKIPPED"
    fabrica.assert_not_called()


def test_cursor_preso_no_primary_e_erro_sem_cliente(fabrica, settings):
    _cursor(calendar_id="primary")
    settings.GCAL_OAUTH_CALENDAR_ID = "primary"

    assert tasks.copiar_mudancas_do_google() == "ERROR"
    fabrica.assert_not_called()


def test_sem_operador_e_erro_sem_cliente(fabrica):
    _cursor(operador=None)

    with _logs() as registros:
        assert tasks.copiar_mudancas_do_google() == "ERROR"
    fabrica.assert_not_called()
    assert [r for r in registros if r.levelno == logging.ERROR]


def test_operador_sem_credencial_e_erro_sem_dado_pessoal(fabrica):
    operador = _operador(com_credencial=False)
    _cursor(operador=operador)

    with _logs() as registros:
        assert tasks.copiar_mudancas_do_google() == "ERROR"
    fabrica.assert_not_called()
    erros = [r for r in registros if r.levelno == logging.ERROR]
    assert erros and f"u{operador.pk}" in erros[0].getMessage()
    _sem_pii(registros)


def test_falha_ao_montar_o_cliente_e_erro_so_com_o_tipo(fabrica):
    _cursor()
    fabrica.side_effect = ValueError(f"credencial de {EMAIL_GOOGLE} recusada")

    with _logs() as registros:
        assert tasks.copiar_mudancas_do_google() == "ERROR"
    assert "ValueError" in _acima_de_info(registros)[0].getMessage()
    _sem_pii(registros)


# --- rodada -----------------------------------------------------------------------------------------


def test_caminho_feliz_roda_uma_rodada_e_loga_so_contagens(fabrica, fake):
    s = _publicada("evt1")
    _no_google(fake, s)
    cursor = _cursor()

    with _logs() as registros:
        assert tasks.copiar_mudancas_do_google() == "OK"  # linha de base: tudo eco
        novo = s.inicio + timedelta(days=1)
        fake.update(
            PINO,
            "evt1",
            {
                "start": {"dateTime": novo.astimezone(FORTALEZA).isoformat()},
                "end": {"dateTime": (novo + timedelta(hours=1)).astimezone(FORTALEZA).isoformat()},
            },
        )
        assert tasks.copiar_mudancas_do_google() == "OK"

    assert fabrica.call_count == 2
    assert fabrica.call_args.args[0].pk == cursor.operador_id
    assert Solicitacao.objects.get(pk=s.pk).inicio == novo
    cursor.refresh_from_db()
    assert cursor.ativo is True and cursor.sync_token and cursor.ultimo_erro == ""
    linhas = [r for r in registros if r.getMessage().startswith("copiar_mudancas_do_google:")]
    assert len(linhas) == 2 and all(r.levelno == logging.INFO for r in linhas)
    assert "status=OK" in linhas[-1].getMessage() and "copiar_horario" in linhas[-1].getMessage()
    _sem_pii(registros)


def test_task_nunca_passa_liberar_freio(fabrica, monkeypatch):
    _cursor()
    chamadas: list[dict[str, Any]] = []
    from apps.core.services.gcal import copia

    def _sincronizar(cursor, client, **kw):
        chamadas.append(kw)
        return copia.Resultado("OK", {})

    monkeypatch.setattr(copia, "sincronizar", _sincronizar)

    assert tasks.copiar_mudancas_do_google() == "OK"
    assert chamadas == [{"escrever": True}]


def test_falhas_ou_choque_viram_warning(fabrica, monkeypatch):
    _cursor()
    from apps.core.services.gcal import copia

    monkeypatch.setattr(
        copia,
        "sincronizar",
        lambda *a, **kw: copia.Resultado("OK", {"falhas": [{"event_id": "e", "motivo": "IntegrityError"}]}),
    )

    with _logs() as registros:
        assert tasks.copiar_mudancas_do_google() == "OK"
    assert [r.levelno for r in registros if r.getMessage().startswith("copiar_mudancas_do_google:")] == [
        logging.WARNING
    ]


def test_choque_registrado_na_rodada_vira_warning(fabrica, monkeypatch):
    _cursor()
    from apps.core.services.gcal import copia

    def _com_choque(*a, **kw):
        AuditLog.objects.create(
            usuario=None,
            action=AuditLog.Action.GCAL_COPIA_GOOGLE,
            model_name="Solicitacao",
            details={"campo": "horario", "choque": [{"usuario_id": 1, "codigo": "RD-01"}]},
        )
        return copia.Resultado("OK", {})

    monkeypatch.setattr(copia, "sincronizar", _com_choque)

    with _logs() as registros:
        assert tasks.copiar_mudancas_do_google() == "OK"
    linha = [r for r in registros if r.getMessage().startswith("copiar_mudancas_do_google:")]
    assert [r.levelno for r in linha] == [logging.WARNING] and "choques=1" in linha[0].getMessage()


def test_freio_devolve_erro_desliga_e_a_proxima_e_skipped(fabrica, fake):
    eids = [f"c{i}" for i in range(6)]
    for eid in eids:
        _no_google(fake, _publicada(eid))
    cursor = _cursor()
    assert tasks.copiar_mudancas_do_google() == "OK"  # linha de base
    for eid in eids:
        fake.delete(PINO, eid)

    with _logs() as registros:
        assert tasks.copiar_mudancas_do_google() == "ERROR"
    cursor.refresh_from_db()
    assert cursor.ativo is False and cursor.ultimo_erro.startswith("freio: 6 cancelamentos")
    assert not AuditLog.objects.filter(action="REJECT").exists()
    linha = [r for r in registros if r.getMessage().startswith("copiar_mudancas_do_google:")]
    assert len(linha) == 1 and linha[0].levelno == logging.ERROR and "freio" in linha[0].getMessage()

    chamadas = fabrica.call_count
    assert tasks.copiar_mudancas_do_google() == "SKIPPED"
    assert fabrica.call_count == chamadas


def test_soft_time_limit_e_erro(fabrica, monkeypatch):
    from celery.exceptions import SoftTimeLimitExceeded

    from apps.core.services.gcal import copia

    _cursor()

    def _estoura(*a, **kw):
        raise SoftTimeLimitExceeded()

    monkeypatch.setattr(copia, "sincronizar", _estoura)

    with _logs() as registros:
        assert tasks.copiar_mudancas_do_google() == "ERROR"
    assert [r for r in registros if r.levelno == logging.ERROR]


def test_task_registrada_com_limite_abaixo_do_hard_limit(settings):
    t = tasks.copiar_mudancas_do_google
    assert t.name == "apps.core.tasks.copiar_mudancas_do_google"
    assert t.ignore_result is True
    assert t.soft_time_limit < settings.CELERY_TASK_TIME_LIMIT

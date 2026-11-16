"""LGPD art. 46 — redação de PII no pipeline de log (#3) + Usuario.__str__ sem CPF (#2)."""

# pyright: reportPrivateUsage=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import logging

import pytest

from apps.core.logging_filters import PIIRedactionFilter
from apps.core.tests.factories import UsuarioFactory


def _record(msg: str, *args: object) -> logging.LogRecord:
    return logging.LogRecord("t", logging.INFO, __file__, 1, msg, args, None)


# ------------------------- filtro de redação (#3) -------------------------


def test_filtro_mascara_email_mantendo_dominio():
    rec = _record("Refresh token para maria@aprendereditora.com.br ok")
    PIIRedactionFilter().filter(rec)
    out = rec.getMessage()
    assert "maria@" not in out
    assert "***@aprendereditora.com.br" in out


def test_filtro_mascara_cpf_de_11_digitos():
    rec = _record("login username=11144477735 bloqueado")
    PIIRedactionFilter().filter(rec)
    out = rec.getMessage()
    assert "11144477735" not in out
    assert "<cpf>" in out


def test_filtro_redige_apos_interpolar_args_lazy():
    # `logger.info("email %s cpf %s", email, cpf)` — a PII so aparece apos o %.
    rec = _record("email %s cpf %s", "x@y.com", "11144477735")
    PIIRedactionFilter().filter(rec)
    out = rec.getMessage()
    assert "x@y.com" not in out
    assert "11144477735" not in out
    assert "***@y.com" in out and "<cpf>" in out


def test_filtro_mascara_email_codificado_na_uri_do_google():
    # FER-60: o aviso de repetição da biblioteca do Google (e o texto do HttpError) trazem a URI,
    # onde o calendarId de e-mail sai com o `@` codificado como `%40`.
    rec = _record(
        "Sleeping %.2f seconds before retry 1 of 1 for request: GET %s, after 503",
        1.12,
        "https://www.googleapis.com/calendar/v3/calendars/fulana%40aprendereditora.com.br/events?alt=json",
    )
    PIIRedactionFilter().filter(rec)
    out = rec.getMessage()
    assert "fulana" not in out
    assert "/calendars/***@aprendereditora.com.br/events" in out


def test_filtro_mascara_email_codificado_com_mais_na_parte_local():
    # FER-60, rodada 3: na URI o `+` do endereço vira `%2B`; sem tratar, o nome antes dele vazava.
    rec = _record("POST https://www.googleapis.com/calendar/v3/calendars/joao.silva%2Bagenda%40dominio.com.br/events")
    PIIRedactionFilter().filter(rec)
    out = rec.getMessage()
    assert "joao" not in out and "silva" not in out and "agenda" not in out
    assert "/calendars/***@dominio.com.br/events" in out


def test_log_da_biblioteca_do_google_tem_destino_proprio_filtrado():
    # FER-60: no worker do Celery a raiz é trocada (worker_hijack_root_logger) e perde o filtro.
    # O aviso de repetição do googleapiclient precisa do próprio handler com o filtro de PII,
    # sem subir para a raiz.
    from django.conf import settings

    conf = settings.LOGGING["loggers"]["googleapiclient"]
    assert conf["propagate"] is False
    handlers = settings.LOGGING["handlers"]
    assert conf["handlers"]
    assert all("pii_redaction" in handlers[h]["filters"] for h in conf["handlers"])

    logger = logging.getLogger("googleapiclient.http")
    alvo = logging.getLogger("googleapiclient")
    assert logger.parent is alvo or logger.propagate
    # Só o StreamHandler do LOGGING; o pytest pendura os handlers de captura dele no mesmo logger.
    do_sistema: list[logging.Handler] = [h for h in alvo.handlers if type(h) is logging.StreamHandler]
    assert do_sistema
    assert all(any(isinstance(f, PIIRedactionFilter) for f in h.filters) for h in do_sistema)


def test_filtro_nao_altera_mensagem_sem_pii():
    rec = _record("processado 42 registros com sucesso")
    PIIRedactionFilter().filter(rec)
    assert rec.getMessage() == "processado 42 registros com sucesso"


# ------------------------- Usuario.__str__ (#2) -------------------------


@pytest.mark.django_db
def test_usuario_str_nao_vaza_cpf_nem_username():
    # Usuario importado: username == CPF, sem nome.
    u = UsuarioFactory(cpf="11144477735", username="11144477735", first_name="", last_name="")
    s = str(u)
    assert "11144477735" not in s
    assert s == f"Usuario #{u.pk}"


@pytest.mark.django_db
def test_usuario_str_usa_nome_quando_existe():
    u = UsuarioFactory(first_name="Maria", last_name="Silva", cpf="22255588846")
    s = str(u)
    assert s == "Maria Silva"
    assert "22255588846" not in s

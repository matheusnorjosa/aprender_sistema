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

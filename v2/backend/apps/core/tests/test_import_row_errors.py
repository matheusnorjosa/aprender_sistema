"""Tests para o helper de erro de linha dos importers (CodeQL py/stack-trace-exposure)."""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false

from __future__ import annotations

import logging

from apps.core.imports.row_errors import MENSAGEM_ERRO_LINHA, registrar_erro_import


def test_registrar_erro_import_devolve_mensagem_generica():
    sentinel = "segredo_interno_constraint_users_pkey_xyz"
    try:
        raise ValueError(sentinel)
    except ValueError:
        msg = registrar_erro_import(importer="teste", linha=7)

    # O valor devolvido ao cliente e' generico e nunca contem a excecao crua.
    assert msg == MENSAGEM_ERRO_LINHA
    assert sentinel not in msg


def test_registrar_erro_import_loga_traceback(caplog):
    sentinel = "detalhe_interno_para_o_log_apenas_abc"
    with caplog.at_level(logging.ERROR, logger="apps.core.imports"):
        try:
            raise RuntimeError(sentinel)
        except RuntimeError:
            registrar_erro_import(importer="usuarios", linha=42)

    # O detalhe real (traceback) vai para o log — nao para a resposta.
    assert "usuarios" in caplog.text
    assert sentinel in caplog.text

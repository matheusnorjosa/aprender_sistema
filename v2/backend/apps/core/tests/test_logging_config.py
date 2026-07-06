"""Testes da config de logging (config.settings.LOGGING).

Regressao do incidente 2026-07-06: uma rajada de respostas 4xx logadas como
WARNING pelo `django.request`, com o formatter JSON serializando o objeto
`request` inteiro por linha, saturou os workers do gunicorn em producao (504) e
ainda vazava dados de requisicao para o log (LGPD). Estes testes travam as duas
correcoes: (1) `django.request` em ERROR (4xx nao floodam; 5xx seguem); (2) o
formatter JSON nao serializa o objeto `request`.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportMissingParameterType=false, reportUnknownParameterType=false, reportIndexIssue=false

from __future__ import annotations

import json
import logging
from typing import Any

from pythonjsonlogger.jsonlogger import JsonFormatter

from config.settings import LOGGING as _RAW_LOGGING

# LOGGING e um dict heterogeneo -> pyright infere __getitem__ estrito (so slice).
# Tipar como dict[str, Any] libera o acesso por chave string nos asserts abaixo.
LOGGING: dict[str, Any] = _RAW_LOGGING


def _build_json_formatter() -> JsonFormatter:
    """Instancia o formatter JSON exatamente como o dictConfig faria."""
    conf = LOGGING["formatters"]["json"]
    return JsonFormatter(
        conf["format"],
        reserved_attrs=conf["reserved_attrs"],
        timestamp=conf.get("timestamp", False),
    )


def _record(name: str, level: int, msg: str) -> logging.LogRecord:
    record = logging.LogRecord(name=name, level=level, pathname=__file__, lineno=1, msg=msg, args=None, exc_info=None)
    # Extras injetados pelos filtros (RequestIDFilter/ContextFilter):
    record.request_id = "N/A"
    record.environment = "test"
    record.service = "web"
    return record


def test_formatter_json_nao_serializa_o_objeto_request():
    """O objeto `request` NUNCA pode ir para o log (bloat + LGPD)."""
    formatter = _build_json_formatter()
    record = _record("django.request", logging.ERROR, "Forbidden: /api/me/")
    # django.request.log_response injeta estes extras em respostas 4xx/5xx:
    record.request = {"cookies": "sessionid=SEGREDO", "META": {"HTTP_AUTHORIZATION": "Bearer TOKEN"}}
    record.status_code = 403

    out = json.loads(formatter.format(record))

    assert "request" not in out, "objeto request vazou para o log (LGPD/bloat)"
    assert "SEGREDO" not in json.dumps(out), "dados sensiveis do request vazaram para o log"
    assert "TOKEN" not in json.dumps(out)
    # status_code (escalar util) permanece sendo logado.
    assert out.get("status_code") == 403


def test_formatter_json_omite_taskname():
    """taskName (Py3.12, sempre None em contexto sync) e ruido; nao deve aparecer."""
    formatter = _build_json_formatter()
    record = _record("apps", logging.INFO, "evento ok")
    record.taskName = None

    out = json.loads(formatter.format(record))

    assert "taskName" not in out


def test_django_request_logger_em_error_nao_faz_flood_de_4xx():
    """django.request em ERROR: 4xx (WARNING) param de floodar; 5xx (ERROR) seguem."""
    logger_conf = LOGGING["loggers"]["django.request"]
    assert logger_conf["level"] == "ERROR"
    # propagate=False evita dupla emissao (nao sobe para o logger "django").
    assert logger_conf["propagate"] is False


def test_formatter_json_mantem_campos_uteis():
    """A correcao nao pode remover os campos estruturados legitimos."""
    formatter = _build_json_formatter()
    record = _record("apps", logging.INFO, "evento ok")

    out = json.loads(formatter.format(record))

    assert out["message"] == "evento ok"
    assert out["request_id"] == "N/A"
    assert out["environment"] == "test"
    assert out["service"] == "web"

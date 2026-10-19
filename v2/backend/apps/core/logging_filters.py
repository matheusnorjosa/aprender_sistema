"""
Filtros de logging customizados para AS v2.

Refs: MP2 - Structured Logging (Issue #166)
"""

from __future__ import annotations

import logging
import re
import threading
from typing import cast

from apps.core.pii import redact_cpf

# PII patterns para o PIIRedactionFilter.
# S6 (auditoria 14/10, C5): sem backtracking quadrático; mesma forma e mesma explicação de
# `services/gcal/minimize.py` (uma cadeia `a@b.c+d@e.f` casa num só match, um e-mail por `@`).
_EMAIL = r"[\w.+-]+@[\w-]+\.[\w.-]+"
_EMAIL_RE = re.compile(rf"(?<![\w.+-]){_EMAIL}(?:(?=\+){_EMAIL})*")

# Atributos que todo LogRecord tem. O resto veio do `extra=` de quem logou (ou de outro filtro).
_ATRIBUTOS_PADRAO = frozenset(vars(logging.LogRecord("", 0, "", 0, "", (), None))) | {"message", "asctime"}


class RequestIDFilter(logging.Filter):
    """
    Filtro que adiciona request_id aos logs estruturados.

    Busca request_id em thread-local storage (definido por RequestIDMiddleware)
    e adiciona ao LogRecord como atributo 'request_id'.

    Se request_id não estiver disponível (ex: worker Celery, management commands),
    usa 'N/A' como fallback.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # Buscar request_id do thread-local (definido por RequestIDMiddleware)
        request_id = getattr(threading.current_thread(), "request_id", None)

        # Fallback para 'N/A' se não houver request_id (Celery, commands, etc.)
        record.request_id = request_id or "N/A"  # type: ignore[attr-defined]

        return True


class ContextFilter(logging.Filter):
    """
    Filtro que adiciona contexto adicional aos logs estruturados.

    Adiciona:
    - environment: development/staging/production
    - service: web/worker/beat
    """

    def __init__(self, environment: str = "development", service: str = "web") -> None:
        super().__init__()
        self.environment = environment
        self.service = service

    def filter(self, record: logging.LogRecord) -> bool:
        record.environment = self.environment  # type: ignore[attr-defined]
        record.service = self.service  # type: ignore[attr-defined]
        return True


class PIIRedactionFilter(logging.Filter):
    """Mascara PII no log ANTES da formatacao (LGPD art. 46): mensagem, `extra` e traceback.

    Camada de defesa central: em vez de confiar que cada call-site nao loga PII, o
    pipeline scrubba de QUALQUER mensagem:
    - e-mail (ex.: google_email de OAuth) -> mantem o dominio, mascara o local:
      `***@dominio` (observabilidade sem identificar a pessoa).
    - CPF cru (11 digitos, tambem o username) ou formatado (000.000.000-00) -> `<cpf>`, pela
      mesma regra de `apps.core.pii.redact_cpf` (#1964: as duas copias tinham divergido).

    S5 (auditoria 14/10, C11): o JsonFormatter grava cada `extra` como campo proprio e o
    traceback inteiro, entao os valores texto dos `extra` (inclusive dentro de dict/lista) e o
    traceback passam pela mesma mascara. Com PII no traceback, o texto ja redigido vai em
    `exc_text` e `exc_info` sai (o formatter usa `exc_text` quando nao ha `exc_info`).

    Aplicado a todos os handlers em `LOGGING`. Nao substitui a disciplina de nao logar
    PII no call-site, mas garante o piso mesmo quando alguem esquece.
    """

    @staticmethod
    def _mask_email(m: re.Match[str]) -> str:
        # Cada trecho após um `@` é o domínio daquele e-mail seguido, numa cadeia, do `+local` do próximo.
        return "".join(f"***@{trecho.split('+', 1)[0]}" for trecho in m.group(0).split("@")[1:])

    @classmethod
    def _redigir(cls, valor: object) -> object:
        if isinstance(valor, str):
            return redact_cpf(_EMAIL_RE.sub(cls._mask_email, valor))
        if isinstance(valor, dict):
            return {k: cls._redigir(v) for k, v in cast(dict[object, object], valor).items()}
        if isinstance(valor, list):
            return [cls._redigir(v) for v in cast(list[object], valor)]
        if isinstance(valor, tuple):
            return tuple(cls._redigir(v) for v in cast(tuple[object, ...], valor))
        return valor

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            msg = None
        if msg is not None:
            redacted = str(self._redigir(msg))
            if redacted != msg:
                record.msg = redacted
                record.args = ()

        for nome, valor in list(vars(record).items()):
            if nome not in _ATRIBUTOS_PADRAO:
                setattr(record, nome, self._redigir(valor))

        if record.exc_info and not record.exc_text:
            record.exc_text = logging.Formatter().formatException(record.exc_info)
        if record.exc_text:
            redigido = self._redigir(record.exc_text)
            if redigido != record.exc_text:
                record.exc_text = str(redigido)
                record.exc_info = None
        if record.stack_info:
            record.stack_info = str(self._redigir(record.stack_info))
        return True

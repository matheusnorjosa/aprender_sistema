"""
Filtros de logging customizados para AS v2.

Refs: MP2 - Structured Logging (Issue #166)
"""

from __future__ import annotations

import logging
import re
import threading

# PII patterns para o PIIRedactionFilter.
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_CPF_RE = re.compile(r"\b\d{11}\b")


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
    """Mascara PII na mensagem do log ANTES da formatacao (LGPD art. 46).

    Camada de defesa central: em vez de confiar que cada call-site nao loga PII, o
    pipeline scrubba de QUALQUER mensagem:
    - e-mail (ex.: google_email de OAuth) -> mantem o dominio, mascara o local:
      `***@dominio` (observabilidade sem identificar a pessoa).
    - sequencia de 11 digitos (CPF, tambem username de usuarios importados) -> `<cpf>`.

    Aplicado a todos os handlers em `LOGGING`. Nao substitui a disciplina de nao logar
    PII no call-site, mas garante o piso mesmo quando alguem esquece.
    """

    @staticmethod
    def _mask_email(m: re.Match[str]) -> str:
        dom = m.group(0).split("@", 1)[1]
        return f"***@{dom}"

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        redacted = _EMAIL_RE.sub(self._mask_email, msg)
        redacted = _CPF_RE.sub("<cpf>", redacted)
        if redacted != msg:
            record.msg = redacted
            record.args = ()
        return True

"""
Filtros de logging customizados para AS v2.

Refs: MP2 - Structured Logging (Issue #166)
"""

from __future__ import annotations

import logging
import threading
from typing import Any


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

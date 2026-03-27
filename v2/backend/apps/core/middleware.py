"""
Middleware para AS v2.

Inclui:
- RequestIDMiddleware: Adiciona correlation ID (request_id) único por requisição
"""

from __future__ import annotations

import logging
import uuid
from typing import Callable

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)


class RequestIDMiddleware:
    """
    Middleware que adiciona um request_id único a cada requisição HTTP.

    O request_id é usado para correlacionar logs de diferentes componentes
    da mesma requisição (view, service, database, cache, etc.).

    Funcionamento:
    1. Gera UUID4 único por requisição
    2. Armazena em request.request_id
    3. Adiciona header X-Request-ID na response
    4. Disponibiliza para logging estruturado via thread-local storage

    Refs: MP2 - Structured Logging (Issue #166)
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        import threading

        # Gerar request_id único (UUID4)
        request_id = str(uuid.uuid4())

        # Armazenar no request object
        request.request_id = request_id  # type: ignore[attr-defined]

        # Sempre atualizar thread-local (fix #580: threads são reutilizadas)
        threading.current_thread().request_id = request_id  # type: ignore[attr-defined]

        try:
            # Processar request
            response = self.get_response(request)

            # Adicionar header X-Request-ID na response
            response["X-Request-ID"] = request_id

            return response
        finally:
            # Limpar thread-local para evitar vazamento entre requests
            try:
                delattr(threading.current_thread(), "request_id")
            except AttributeError:
                pass

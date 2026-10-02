"""
Middleware para AS v2.

Inclui:
- RequestIDMiddleware: Adiciona correlation ID (request_id) único por requisição
- APIv1DeprecationMiddleware: Adds deprecation headers to /api/v1/ requests (#793)
- TrocaDeSenhaObrigatoriaMiddleware: com `Usuario.deve_trocar_senha` ligado, só a troca de
  senha (e o mínimo para chegar nela e sair) é aceita
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Callable

from django.http import HttpRequest, HttpResponse, JsonResponse

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


class APIv1DeprecationMiddleware:
    """
    Adds RFC 8594 Deprecation + Sunset headers to /api/v1/ requests.

    Signals to clients that the /api/v1/ prefix is deprecated and will be
    removed. The canonical path is /api/ (#793).
    """

    # Sunset date: 60 days from deployment (2026-06-15)
    SUNSET_DATE = "Sun, 14 Jun 2026 23:59:59 GMT"

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)

        if request.path.startswith("/api/v1/"):
            response["Deprecation"] = "true"
            response["Sunset"] = self.SUNSET_DATE
            canonical = request.path.replace("/api/v1/", "/api/", 1)
            response["Link"] = f'<{canonical}>; rel="successor-version"'

        return response


# Lista FECHADA do que a pessoa pode chamar enquanto `deve_trocar_senha` está ligado:
# (nome completo da rota = `namespace:nome`, método). Comparação por igualdade, nunca por
# prefixo: o apelido antigo `/api/v1/` (namespace `core-v1`) e o Django Admin ficam de fora.
ROTAS_LIBERADAS_NA_TROCA_DE_SENHA: frozenset[tuple[str, str]] = frozenset(
    {
        ("core:current-user", "GET"),  # a tela descobre que a troca está pendente
        ("core:csrf-token", "GET"),  # sem o token nenhum POST passa
        ("core:me-change-password", "POST"),  # a troca em si
        ("core:auth-logout", "POST"),  # sair sem trocar
    }
)

CODIGO_TROCA_DE_SENHA_OBRIGATORIA = "PASSWORD_CHANGE_REQUIRED"


class TrocaDeSenhaObrigatoriaMiddleware:
    """
    Ponto ÚNICO de imposição da troca obrigatória de senha (primeiro acesso).

    Enquanto `request.user.deve_trocar_senha` está ligado, só passa o que está em
    `ROTAS_LIBERADAS_NA_TROCA_DE_SENHA`; todo o resto responde 403 com o código
    `PASSWORD_CHANGE_REQUIRED`. NEGA POR PADRÃO: rota nova nasce bloqueada.

    Por que middleware e não permission class: as views sobrescrevem `permission_classes`,
    então `DEFAULT_PERMISSION_CLASSES` não é ponto único. A única autenticação da API é a
    sessão (`SessionAuthentication`), logo o `request.user` do Django é o mesmo do DRF e a
    marca vem do usuário já carregado da sessão (sem consulta extra). Tem de ficar DEPOIS de
    `AuthenticationMiddleware` em `MIDDLEWARE`.

    Vale para superusuário também (inclusive no Django Admin, que recebe o 403 em JSON).
    Anônimo não é afetado.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        return self.get_response(request)

    def process_view(
        self,
        request: HttpRequest,
        view_func: Callable[..., HttpResponse],
        view_args: tuple[Any, ...],
        view_kwargs: dict[str, Any],
    ) -> HttpResponse | None:
        user = getattr(request, "user", None)
        if not getattr(user, "is_authenticated", False) or not getattr(user, "deve_trocar_senha", False):
            return None

        match = request.resolver_match
        view_name = match.view_name if match is not None else ""
        if (view_name, request.method) in ROTAS_LIBERADAS_NA_TROCA_DE_SENHA:
            return None

        # Sem dado pessoal: só o id da conta e o nome da rota.
        logger.info(
            "troca_de_senha_obrigatoria: rota bloqueada",
            extra={"user_id": getattr(user, "pk", None), "view_name": view_name, "method": request.method},
        )
        return JsonResponse(
            {"detail": "Defina uma senha própria para continuar.", "code": CODIGO_TROCA_DE_SENHA_OBRIGATORIA},
            status=403,
        )

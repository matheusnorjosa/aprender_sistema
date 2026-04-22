"""FreezeTimeMiddleware — congela `django.utils.timezone.now()` por request.

Habilitado APENAS quando:

1. `INCLUDE_DEV_TOOLS=true` (o app `apps.dev_tools` está instalado), E
2. `DEBUG_E2E=true` (flag exclusiva para testes E2E).

Ambas condições são verificadas em `settings.py` antes de registrar o
middleware em `MIDDLEWARE`. Em produção, `INCLUDE_DEV_TOOLS=false`
garante que este módulo nem é importado.

Uso esperado (Playwright):

    await page.setExtraHTTPHeaders({
      'X-E2E-Frozen-Time': '2026-04-21T09:00:00-03:00'
    });

Formato do header: ISO-8601 com timezone (obrigatório). Header ausente
ou inválido → request segue sem congelamento.

Implementação:

- `threading.local` mantém o instante congelado por thread do request.
- Monkey-patch one-shot em `django.utils.timezone.now()` aplica o
  congelamento quando presente; fallback para `now()` real quando ausente.
- Monkey-patch ocorre apenas quando o middleware é efetivamente carregado,
  ou seja, com `DEBUG_E2E=true + INCLUDE_DEV_TOOLS=true`.
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false
from __future__ import annotations

import threading
from datetime import datetime
from typing import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils import timezone

_frozen_state = threading.local()
_original_now: Callable[[], datetime] | None = None
_patch_applied = False


def is_time_frozen() -> datetime | None:
    """Retorna o datetime congelado para o thread atual, ou None."""
    return getattr(_frozen_state, "frozen", None)


def _patched_now() -> datetime:
    frozen = is_time_frozen()
    if frozen is not None:
        return frozen
    assert _original_now is not None
    return _original_now()


def _apply_monkey_patch() -> None:
    """Substitui timezone.now() pelo patched. Idempotente."""
    global _original_now, _patch_applied
    if _patch_applied:
        return
    _original_now = timezone.now
    timezone.now = _patched_now  # type: ignore[assignment]
    _patch_applied = True


class FreezeTimeMiddleware:
    """Congela `timezone.now()` quando header `X-E2E-Frozen-Time` está presente.

    Gate duplo (validado em settings.py):
    - `INCLUDE_DEV_TOOLS=true`
    - `DEBUG_E2E=true`

    Sem ambos, o middleware nem é registrado em `MIDDLEWARE`.
    """

    HEADER_NAME = "HTTP_X_E2E_FROZEN_TIME"

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        if not getattr(settings, "DEBUG_E2E", False):
            raise RuntimeError(
                "FreezeTimeMiddleware requires settings.DEBUG_E2E=True."
                " This middleware must not be registered in production."
            )
        if not getattr(settings, "INCLUDE_DEV_TOOLS", False):
            raise RuntimeError(
                "FreezeTimeMiddleware requires settings.INCLUDE_DEV_TOOLS=True."
            )
        _apply_monkey_patch()
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        header_value = request.META.get(self.HEADER_NAME)
        if not header_value:
            return self.get_response(request)

        try:
            frozen_dt = datetime.fromisoformat(header_value)
        except ValueError:
            return self.get_response(request)

        if frozen_dt.tzinfo is None:
            # Exigir tz explícita; evita ambiguidade UTC vs local
            return self.get_response(request)

        _frozen_state.frozen = frozen_dt
        try:
            return self.get_response(request)
        finally:
            _frozen_state.frozen = None


def reset_for_tests() -> None:
    """Desfaz o monkey-patch. Use apenas em testes/teardown."""
    global _original_now, _patch_applied
    if _patch_applied and _original_now is not None:
        timezone.now = _original_now  # type: ignore[assignment]
        _original_now = None
        _patch_applied = False
    _frozen_state.frozen = None

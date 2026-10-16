"""Client IP resolution honouring the trusted-proxy count (SEC / issue #1660).

Single source of truth for "what is the client's IP". Historically this logic
was duplicated in 8 call sites, each trusting the *first* entry of
``X-Forwarded-For`` — a value the client fully controls — so lockout, throttle
and ``AuditLog`` keys could all be forged (``X-Forwarded-For: 1.2.3.4``).

This helper mirrors DRF's ``BaseThrottle.get_ident`` so the throttle, the login
lockout and the audit log all key off the *same* value:

* ``settings.NUM_PROXIES`` — the number of trusted reverse proxies that append
  to ``X-Forwarded-For`` between the public internet and gunicorn.
* With ``N`` proxies we read the ``N``-th entry counting *from the right*, so a
  forged left-most entry is ignored.
* With ``0`` proxies (or no XFF) we trust only ``REMOTE_ADDR`` — the real TCP
  peer, which the client cannot forge.

Set ``NUM_PROXIES`` to match the real topology: too low collapses every client
onto the proxy IP (breaking per-client throttle); too high re-opens forgery.
In production the chain is NPM edge → nginx ``frontend`` container → gunicorn,
so ``NUM_PROXIES = 2``.

F7 (scan 16/10/2026): o ``X-Forwarded-For`` só vale quando quem conecta (``REMOTE_ADDR``) está em
``settings.TRUSTED_PROXY_NETWORKS`` (padrão: as faixas privadas da rede Docker, as mesmas do
``set_real_ip_from`` do nginx do frontend) e traz pelo menos ``NUM_PROXIES`` entradas. Fora disso
vale o ``REMOTE_ADDR``: quem alcança o gunicorn direto não escolhe o IP pelo cabeçalho.
``ForwardedForConfiavelMiddleware`` aplica a mesma regra ao ``request.META`` para o throttle do DRF
(``get_ident``), que lê o cabeçalho por conta própria.

Usage:
    from apps.core.utils.net import get_client_ip

    ip = get_client_ip(request)
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false

from __future__ import annotations

import ipaddress
from typing import Any

from django.conf import settings
from django.http import HttpRequest
from rest_framework.request import Request

# Preserved from the legacy helper contract: callers store this when neither a
# trusted proxy header nor REMOTE_ADDR is available (e.g. synthetic requests).
UNKNOWN_IP = "unknown"


def _proxy_confiavel(remote_addr: str) -> bool:
    """True se `remote_addr` (o par TCP) está numa das redes de proxy confiáveis."""
    try:
        addr = ipaddress.ip_address(remote_addr)
    except ValueError:
        return False
    redes: list[str] = list(getattr(settings, "TRUSTED_PROXY_NETWORKS", []))
    return any(addr in ipaddress.ip_network(rede, strict=False) for rede in redes)


def _xff_confiavel(meta: Any) -> list[str] | None:
    """Entradas do X-Forwarded-For, se ele merece confiança; None se não.

    Merece quando quem conecta é proxy confiável e há ao menos `NUM_PROXIES` entradas (com menos,
    a requisição não passou por todos os saltos confiáveis e a entrada lida seria a do cliente).
    """
    xff = meta.get("HTTP_X_FORWARDED_FOR")
    if not xff or not _proxy_confiavel(meta.get("REMOTE_ADDR") or ""):
        return None
    addrs = [addr.strip() for addr in xff.split(",") if addr.strip()]
    num_proxies = getattr(settings, "NUM_PROXIES", 0)
    if not addrs or (num_proxies is not None and len(addrs) < num_proxies):
        return None
    return addrs


def descartar_xff_nao_confiavel(meta: Any) -> None:
    """Tira de `meta` o X-Forwarded-For que `get_client_ip` não usaria (ver `_xff_confiavel`)."""
    if "HTTP_X_FORWARDED_FOR" in meta and _xff_confiavel(meta) is None:
        del meta["HTTP_X_FORWARDED_FOR"]


def get_client_ip(request: HttpRequest | Request) -> str:
    """Return the client IP, counting ``NUM_PROXIES`` trusted hops from the right.

    A forged left-most ``X-Forwarded-For`` entry is ignored because we always
    index the client position relative to the trusted proxies closest to the
    server. Falls back to ``REMOTE_ADDR`` (the unforgeable TCP peer) whenever no
    trusted proxy header applies.
    """
    remote_addr = request.META.get("REMOTE_ADDR") or UNKNOWN_IP
    num_proxies = getattr(settings, "NUM_PROXIES", 0)

    # 0 proxies, XFF ausente ou não confiável (F7) => the only trustworthy value is the TCP peer.
    addrs = None if num_proxies == 0 else _xff_confiavel(request.META)
    if addrs is None:
        return remote_addr

    # NUM_PROXIES=None => legacy "trust the whole chain" (dev only, discouraged).
    if num_proxies is None:
        return ",".join(addrs)
    return addrs[-num_proxies]

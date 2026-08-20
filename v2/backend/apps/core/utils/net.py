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

Usage:
    from apps.core.utils.net import get_client_ip

    ip = get_client_ip(request)
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false

from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest

# Preserved from the legacy helper contract: callers store this when neither a
# trusted proxy header nor REMOTE_ADDR is available (e.g. synthetic requests).
UNKNOWN_IP = "unknown"


def get_client_ip(request: HttpRequest) -> str:
    """Return the client IP, counting ``NUM_PROXIES`` trusted hops from the right.

    A forged left-most ``X-Forwarded-For`` entry is ignored because we always
    index the client position relative to the trusted proxies closest to the
    server. Falls back to ``REMOTE_ADDR`` (the unforgeable TCP peer) whenever no
    trusted proxy header applies.
    """
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    remote_addr = request.META.get("REMOTE_ADDR") or UNKNOWN_IP
    num_proxies = getattr(settings, "NUM_PROXIES", 0)

    # NUM_PROXIES=None => legacy "trust the whole chain" (dev only, discouraged).
    if num_proxies is None:
        return "".join(xff.split()) if xff else remote_addr

    # 0 proxies, or no XFF at all => the only trustworthy value is the TCP peer.
    if num_proxies == 0 or not xff:
        return remote_addr

    addrs = [addr.strip() for addr in xff.split(",") if addr.strip()]
    if not addrs:
        return remote_addr
    return addrs[-min(num_proxies, len(addrs))]

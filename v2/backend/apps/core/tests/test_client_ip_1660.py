"""Adversarial unit tests for the canonical client-IP resolver (issue #1660).

Proves that a forged ``X-Forwarded-For`` header cannot change the resolved IP
when ``NUM_PROXIES`` matches the real topology, and that with no trusted proxy
the resolver falls back to the unforgeable ``REMOTE_ADDR``.
"""

# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportMissingImports=false

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.test import Client, RequestFactory, override_settings

from apps.core.utils.net import UNKNOWN_IP, get_client_ip

_FACTORY = RequestFactory()


def _req(xff: str | None = None, remote_addr: str = "10.0.0.9"):
    extra: dict[str, Any] = {"REMOTE_ADDR": remote_addr}
    if xff is not None:
        extra["HTTP_X_FORWARDED_FOR"] = xff
    return _FACTORY.get("/", **extra)


@override_settings(NUM_PROXIES=0)
def test_num_proxies_zero_ignores_xff_entirely():
    # Attacker sends a forged XFF; with 0 trusted proxies it is worthless.
    req = _req(xff="1.2.3.4", remote_addr="203.0.113.7")
    assert get_client_ip(req) == "203.0.113.7"


@override_settings(NUM_PROXIES=0)
def test_num_proxies_zero_no_xff_uses_remote_addr():
    assert get_client_ip(_req(remote_addr="198.51.100.2")) == "198.51.100.2"


@override_settings(NUM_PROXIES=2)
def test_two_proxies_reads_client_from_the_right():
    # Legit chain: client -> proxy1 -> proxy2 -> gunicorn.
    # nginx appends, so XFF = "<client>, <proxy1>"; REMOTE_ADDR = proxy2.
    req = _req(xff="203.0.113.50, 172.16.0.1", remote_addr="172.16.0.2")
    assert get_client_ip(req) == "203.0.113.50"


@override_settings(NUM_PROXIES=2)
def test_two_proxies_forged_prefix_is_ignored():
    # Attacker prepends a fake IP. Trusted proxies append the *real* client
    # address, so the fake one is pushed left and never selected.
    req = _req(xff="1.2.3.4, 203.0.113.50, 172.16.0.1", remote_addr="172.16.0.2")
    resolved = get_client_ip(req)
    assert resolved == "203.0.113.50"
    assert resolved != "1.2.3.4"


@override_settings(NUM_PROXIES=2)
def test_two_proxies_no_xff_falls_back_to_remote_addr():
    assert get_client_ip(_req(remote_addr="172.16.0.2")) == "172.16.0.2"


@override_settings(NUM_PROXIES=1)
def test_single_proxy_reads_last_entry():
    # 1 proxy: XFF = "<client>"; a forged prefix is appended-past by the proxy.
    req = _req(xff="1.2.3.4, 203.0.113.99", remote_addr="172.16.0.2")
    assert get_client_ip(req) == "203.0.113.99"


@override_settings(NUM_PROXIES=2)
def test_whitespace_is_stripped():
    req = _req(xff="  203.0.113.50 ,  172.16.0.1  ", remote_addr="172.16.0.2")
    assert get_client_ip(req) == "203.0.113.50"


@override_settings(NUM_PROXIES=2)
def test_missing_remote_addr_returns_unknown():
    req = _FACTORY.get("/")
    # RequestFactory always sets REMOTE_ADDR=127.0.0.1; strip it to exercise
    # the defensive fallback.
    del req.META["REMOTE_ADDR"]
    assert get_client_ip(req) == UNKNOWN_IP


@override_settings(NUM_PROXIES=None)
def test_legacy_none_trusts_whole_chain():
    # Documents the insecure legacy mode: with NUM_PROXIES unset the whole
    # forwarded chain is trusted. Prod MUST set an integer.
    req = _req(xff="1.2.3.4, 203.0.113.50", remote_addr="172.16.0.2")
    assert get_client_ip(req) == "1.2.3.4,203.0.113.50"


# --- Wiring: the helper and DRF's throttle must read the SAME NUM_PROXIES -----


def test_num_proxies_wired_to_drf_and_helper():
    """settings.NUM_PROXIES (read by get_client_ip) and REST_FRAMEWORK's
    NUM_PROXIES (read by DRF's throttle get_ident) must be the same value, so
    throttle, lockout and audit all key off one client identity (#1660).
    Also a sentinel: the deployed default matches the prod proxy topology (2)."""
    from django.conf import settings
    from rest_framework.settings import api_settings

    assert settings.NUM_PROXIES == api_settings.NUM_PROXIES == 2


def test_drf_throttle_get_ident_ignores_forged_xff():
    """DRF's throttle identity uses the real client behind NUM_PROXIES hops, so a
    rotated left-most X-Forwarded-For no longer buys a fresh throttle bucket."""
    from rest_framework.throttling import AnonRateThrottle

    req = _req(xff="1.2.3.4, 203.0.113.50, 172.16.0.1", remote_addr="172.16.0.2")
    ident = AnonRateThrottle().get_ident(req)
    assert ident == "203.0.113.50"
    assert ident != "1.2.3.4"


# --- Recon gates: /metrics and /healthz/detailed must reject a forged XFF -----


@override_settings(NUM_PROXIES=2)
def test_metrics_gate_rejects_forged_xff():
    # Forged "127.0.0.1" prepended; the 2 trusted proxies append the real public
    # client (8.8.8.8, globally routable) + peer, so get_client_ip resolves the
    # public IP → not internal → 403. (Note: RFC 5737 doc ranges like 203.0.113.x
    # are classified is_private by modern ipaddress, so a real public IP is used.)
    resp = Client().get(
        "/metrics",
        HTTP_X_FORWARDED_FOR="127.0.0.1, 8.8.8.8, 172.16.0.2",
    )
    assert resp.status_code == 403


@override_settings(NUM_PROXIES=2)
def test_metrics_gate_allows_internal_direct_scrape():
    # Direct internal scrape (Prometheus → web:8000, no XFF) with a private
    # REMOTE_ADDR is still allowed through the gate.
    resp = Client().get("/metrics", REMOTE_ADDR="10.0.0.5")
    assert resp.status_code != 403


@override_settings(NUM_PROXIES=2)
def test_healthz_detailed_rejects_forged_xff():
    resp = Client().get(
        "/healthz/detailed/",
        HTTP_X_FORWARDED_FOR="127.0.0.1, 8.8.8.8, 172.16.0.2",
    )
    assert resp.status_code == 403


# --- DoD lint guard: no raw X-Forwarded-For read outside the canonical module -


def test_no_raw_xff_read_outside_net_module():
    """DoD (#1660): HTTP_X_FORWARDED_FOR may only be READ in the canonical
    resolver (apps/core/utils/net.py) and in tests. A new call site reading the
    raw header re-introduces the forgeable first-element pattern."""
    backend_root = Path(__file__).resolve().parents[3]
    offenders: list[str] = []
    for base in ("apps", "config"):
        for py in (backend_root / base).rglob("*.py"):
            rel = py.relative_to(backend_root).as_posix()
            if rel == "apps/core/utils/net.py":
                continue
            if "/tests/" in rel or py.name.startswith("test_"):
                continue
            if "HTTP_X_FORWARDED_FOR" in py.read_text(encoding="utf-8", errors="ignore"):
                offenders.append(rel)
    assert offenders == [], f"raw X-Forwarded-For read outside net.py: {offenders}"

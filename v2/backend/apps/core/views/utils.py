"""
AS v2 — Core Views Utilities

Helper functions.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false

from __future__ import annotations

from apps.core.utils.net import get_client_ip

# Backwards-compatible alias. The client-IP logic used to be copy-pasted here
# (and in 7 other places), each trusting the *first* X-Forwarded-For entry —
# which the client fully controls. It now lives in a single canonical helper
# that honours NUM_PROXIES and ignores forged entries (#1660). Kept under the
# legacy name so the views facade and views_auth imports keep working.
_get_client_ip = get_client_ip

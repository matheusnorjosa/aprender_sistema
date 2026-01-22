"""
Google Calendar Sync Service - Re-export Facade

This file provides backwards-compatible re-exports from the modular
apps.core.services.gcal package.

For new code, prefer importing directly from:
- apps.core.services.gcal.types (Action, SyncOutcome)
- apps.core.services.gcal.utils (_retry_with_backoff, _payload_hash)
- apps.core.services.gcal.client (CalendarClientAdapter)
- apps.core.services.gcal.validation (_validate_event_id, _event_id_for)
- apps.core.services.gcal.payload (build_*, compute_payload_hash)
- apps.core.services.gcal.sync (apply_one_solicitacao, upsert_one, etc.)
"""
# pyright: reportUnusedImport=false, reportPrivateUsage=false

from __future__ import annotations

from apps.core.services.gcal import (
    # Types
    Action,
    SyncOutcome,
    # Utils
    _payload_hash,
    _retry_with_backoff,
    # Client
    CalendarClientAdapter,
    # Validation
    _event_id_for,
    _validate_event_id,
    # Payload
    build_attendees_for_solicitacao,
    build_event_payload,
    build_preview_for_solicitacao,
    compute_payload_hash,
    # Sync
    apply_one_solicitacao,
    cancel_solicitacao,
    resync_solicitacao,
    upsert_one,
)

__all__ = [
    # Types
    "Action",
    "SyncOutcome",
    # Utils
    "_payload_hash",
    "_retry_with_backoff",
    # Client
    "CalendarClientAdapter",
    # Validation
    "_event_id_for",
    "_validate_event_id",
    # Payload
    "build_attendees_for_solicitacao",
    "build_event_payload",
    "build_preview_for_solicitacao",
    "compute_payload_hash",
    # Sync
    "apply_one_solicitacao",
    "cancel_solicitacao",
    "resync_solicitacao",
    "upsert_one",
]

"""
AS v2 — GCal Sync Service Package

Modular package containing all Google Calendar sync functionality:
- types: SyncOutcome dataclass, Action type alias
- utils: Retry with backoff, payload hashing
- client: CalendarClientAdapter base class
- validation: Event ID validation and generation
- payload: Event payload building functions
- sync: Core sync operations (apply, upsert, resync, cancel)

Backwards-compatible re-exports for existing imports.
"""

# pyright: reportPrivateUsage=false

from __future__ import annotations

# Client
from apps.core.services.gcal.client import CalendarClientAdapter

# Payload
from apps.core.services.gcal.payload import (
    build_attendees_for_solicitacao,
    build_event_payload,
    build_preview_for_solicitacao,
    compute_payload_hash,
)

# Sync operations
from apps.core.services.gcal.sync import apply_one_solicitacao, cancel_solicitacao, resync_solicitacao, upsert_one

# Types
from apps.core.services.gcal.types import Action, SyncOutcome

# Utils
from apps.core.services.gcal.utils import _payload_hash, _retry_with_backoff

# Validation
from apps.core.services.gcal.validation import _event_id_for, _validate_event_id

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

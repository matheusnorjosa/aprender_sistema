"""
Test backwards compatibility for modular gcal service package.

Ensures all functions and classes are importable from both:
- apps.core.services.gcal (new modular package)
- apps.core.services.gcal_sync_service (legacy facade)
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false

from __future__ import annotations
import pytest


class TestGCalServiceBackwardsCompatibility:
    """Test that all gcal_sync_service exports remain accessible."""

    def test_action_type_importable_from_legacy(self):
        """Action type alias should be importable from gcal_sync_service."""
        from apps.core.services.gcal_sync_service import Action
        assert Action is not None

    def test_sync_outcome_importable_from_legacy(self):
        """SyncOutcome should be importable from gcal_sync_service."""
        from apps.core.services.gcal_sync_service import SyncOutcome
        assert SyncOutcome is not None

    def test_retry_with_backoff_importable_from_legacy(self):
        """_retry_with_backoff should be importable from gcal_sync_service."""
        from apps.core.services.gcal_sync_service import _retry_with_backoff
        assert callable(_retry_with_backoff)

    def test_payload_hash_importable_from_legacy(self):
        """_payload_hash should be importable from gcal_sync_service."""
        from apps.core.services.gcal_sync_service import _payload_hash
        assert callable(_payload_hash)

    def test_calendar_client_adapter_importable_from_legacy(self):
        """CalendarClientAdapter should be importable from gcal_sync_service."""
        from apps.core.services.gcal_sync_service import CalendarClientAdapter
        assert CalendarClientAdapter is not None

    def test_validate_event_id_importable_from_legacy(self):
        """_validate_event_id should be importable from gcal_sync_service."""
        from apps.core.services.gcal_sync_service import _validate_event_id
        assert callable(_validate_event_id)

    def test_event_id_for_importable_from_legacy(self):
        """_event_id_for should be importable from gcal_sync_service."""
        from apps.core.services.gcal_sync_service import _event_id_for
        assert callable(_event_id_for)

    def test_build_attendees_importable_from_legacy(self):
        """build_attendees_for_solicitacao should be importable from gcal_sync_service."""
        from apps.core.services.gcal_sync_service import build_attendees_for_solicitacao
        assert callable(build_attendees_for_solicitacao)

    def test_build_event_payload_importable_from_legacy(self):
        """build_event_payload should be importable from gcal_sync_service."""
        from apps.core.services.gcal_sync_service import build_event_payload
        assert callable(build_event_payload)

    def test_build_preview_importable_from_legacy(self):
        """build_preview_for_solicitacao should be importable from gcal_sync_service."""
        from apps.core.services.gcal_sync_service import build_preview_for_solicitacao
        assert callable(build_preview_for_solicitacao)

    def test_compute_payload_hash_importable_from_legacy(self):
        """compute_payload_hash should be importable from gcal_sync_service."""
        from apps.core.services.gcal_sync_service import compute_payload_hash
        assert callable(compute_payload_hash)

    def test_apply_one_solicitacao_importable_from_legacy(self):
        """apply_one_solicitacao should be importable from gcal_sync_service."""
        from apps.core.services.gcal_sync_service import apply_one_solicitacao
        assert callable(apply_one_solicitacao)

    def test_upsert_one_importable_from_legacy(self):
        """upsert_one should be importable from gcal_sync_service."""
        from apps.core.services.gcal_sync_service import upsert_one
        assert callable(upsert_one)

    def test_resync_solicitacao_importable_from_legacy(self):
        """resync_solicitacao should be importable from gcal_sync_service."""
        from apps.core.services.gcal_sync_service import resync_solicitacao
        assert callable(resync_solicitacao)

    def test_cancel_solicitacao_importable_from_legacy(self):
        """cancel_solicitacao should be importable from gcal_sync_service."""
        from apps.core.services.gcal_sync_service import cancel_solicitacao
        assert callable(cancel_solicitacao)


class TestGCalPackageDirectImports:
    """Test that new modular package imports work correctly."""

    def test_types_module_importable(self):
        """Types module should be importable."""
        from apps.core.services.gcal.types import Action, SyncOutcome
        assert Action is not None
        assert SyncOutcome is not None

    def test_utils_module_importable(self):
        """Utils module should be importable."""
        from apps.core.services.gcal.utils import _retry_with_backoff, _payload_hash
        assert callable(_retry_with_backoff)
        assert callable(_payload_hash)

    def test_client_module_importable(self):
        """Client module should be importable."""
        from apps.core.services.gcal.client import CalendarClientAdapter
        assert CalendarClientAdapter is not None

    def test_validation_module_importable(self):
        """Validation module should be importable."""
        from apps.core.services.gcal.validation import _validate_event_id, _event_id_for
        assert callable(_validate_event_id)
        assert callable(_event_id_for)

    def test_payload_module_importable(self):
        """Payload module should be importable."""
        from apps.core.services.gcal.payload import (
            build_attendees_for_solicitacao,
            build_event_payload,
            build_preview_for_solicitacao,
            compute_payload_hash,
        )
        assert callable(build_attendees_for_solicitacao)
        assert callable(build_event_payload)
        assert callable(build_preview_for_solicitacao)
        assert callable(compute_payload_hash)

    def test_sync_module_importable(self):
        """Sync module should be importable."""
        from apps.core.services.gcal.sync import (
            apply_one_solicitacao,
            upsert_one,
            resync_solicitacao,
            cancel_solicitacao,
        )
        assert callable(apply_one_solicitacao)
        assert callable(upsert_one)
        assert callable(resync_solicitacao)
        assert callable(cancel_solicitacao)


class TestGCalPackageStructure:
    """Test that gcal package has correct structure."""

    def test_package_has_all_attribute(self):
        """gcal package should have __all__ attribute."""
        import apps.core.services.gcal as gcal
        assert hasattr(gcal, '__all__')
        assert len(gcal.__all__) == 15  # All exports

    def test_all_submodules_exist(self):
        """All submodules should be importable."""
        from apps.core.services.gcal import types
        from apps.core.services.gcal import utils
        from apps.core.services.gcal import client
        from apps.core.services.gcal import validation
        from apps.core.services.gcal import payload
        from apps.core.services.gcal import sync

        assert types is not None
        assert utils is not None
        assert client is not None
        assert validation is not None
        assert payload is not None
        assert sync is not None

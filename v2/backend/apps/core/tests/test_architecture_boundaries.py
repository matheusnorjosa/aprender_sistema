"""
Guard rails arquiteturais para apps.core.

Verifica que apps.dat_ingest foi removido (#967, #971).
"""

from __future__ import annotations

from pathlib import Path


def test_dat_ingest_module_removed() -> None:
    """apps.dat_ingest should not exist (removed in #971)."""
    dat_ingest_dir = Path(__file__).resolve().parents[2] / "dat_ingest"
    assert not dat_ingest_dir.exists(), f"apps.dat_ingest should be removed but found at {dat_ingest_dir}"

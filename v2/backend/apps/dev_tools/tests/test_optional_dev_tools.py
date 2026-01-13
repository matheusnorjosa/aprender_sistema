"""
Tests for optional dev_tools deployment (INCLUDE_DEV_TOOLS setting).

Verifies that:
- INCLUDE_DEV_TOOLS defaults to True (backward compatibility)
- dev_tools is included when INCLUDE_DEV_TOOLS=true
- Commands are available when enabled
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false

from __future__ import annotations
import pytest
from django.conf import settings
from django.core.management import get_commands


class TestIncludeDevToolsSetting:
    """Tests for INCLUDE_DEV_TOOLS configuration."""

    def test_include_dev_tools_defaults_to_true(self):
        """INCLUDE_DEV_TOOLS should default to True for backward compatibility."""
        assert hasattr(settings, "INCLUDE_DEV_TOOLS")
        assert settings.INCLUDE_DEV_TOOLS is True

    def test_dev_tools_in_installed_apps_when_enabled(self):
        """dev_tools should be in INSTALLED_APPS when INCLUDE_DEV_TOOLS=true."""
        if settings.INCLUDE_DEV_TOOLS:
            assert "apps.dev_tools" in settings.INSTALLED_APPS

    def test_core_always_in_installed_apps(self):
        """core app should always be in INSTALLED_APPS."""
        assert "apps.core" in settings.INSTALLED_APPS


class TestDevToolsCommands:
    """Tests for dev_tools management commands."""

    def test_seed_commands_available_when_enabled(self):
        """Seed commands should be available when INCLUDE_DEV_TOOLS=true."""
        if not settings.INCLUDE_DEV_TOOLS:
            pytest.skip("Dev tools not enabled")

        commands = get_commands()
        seed_commands = [
            "seed_e2e_users",
            "seed_gerencias",
            "seed_gerentes",
            "seed_produtos",
            "seed_rbac",
            "seed_tipos_evento",
            "seed_projetos_fluxo_from_csv",
            "seed_projetos_fluxo_from_sheets",
        ]

        for cmd in seed_commands:
            assert cmd in commands, f"Command {cmd} should be available"

    def test_backfill_commands_available_when_enabled(self):
        """Backfill commands should be available when INCLUDE_DEV_TOOLS=true."""
        if not settings.INCLUDE_DEV_TOOLS:
            pytest.skip("Dev tools not enabled")

        commands = get_commands()
        backfill_commands = [
            "backfill_is_online",
            "fix_projetos_gerencia",
            "migrate_rbac_groups",
            "link_projetos_gerencias",
            "populate_municipio_coords",
            "cleanup_e2e_data",
        ]

        for cmd in backfill_commands:
            assert cmd in commands, f"Command {cmd} should be available"

    def test_production_commands_always_available(self):
        """Production commands should always be in core."""
        commands = get_commands()

        # These should always exist (in core)
        assert "preagenda_to_gcal" in commands
        assert "rotate_gcal_encryption_key" in commands


class TestDevToolsExclusionDocumentation:
    """Documentation tests for dev_tools exclusion."""

    def test_include_dev_tools_env_var_documented(self):
        """Verify the expected behavior of INCLUDE_DEV_TOOLS."""
        # This test documents the expected behavior:
        #
        # INCLUDE_DEV_TOOLS=true (default):
        #   - apps.dev_tools in INSTALLED_APPS
        #   - Seed/backfill commands available
        #   - E2E test helpers available
        #
        # INCLUDE_DEV_TOOLS=false:
        #   - apps.dev_tools NOT in INSTALLED_APPS
        #   - Seed commands NOT available
        #   - Production commands (preagenda_to_gcal) still work
        #
        # To deploy without dev tools:
        #   environment:
        #     - INCLUDE_DEV_TOOLS=false
        pass

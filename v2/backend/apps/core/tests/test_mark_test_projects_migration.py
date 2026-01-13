"""
Tests for 0038_mark_test_projects data migration.

Tests:
- test_migration_marks_all_8_test_projects
- test_migration_preserves_production_projects
- test_migration_idempotent
- test_migration_skips_already_marked
- test_migration_reversible
- test_migration_handles_missing_projects
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false

from __future__ import annotations
import importlib

import pytest

from apps.core.models import Projeto


@pytest.fixture
def clean_projetos(db):
    """Clear existing projetos for clean test state."""
    Projeto.objects.all().delete()
    yield
    Projeto.objects.all().delete()


# Import migration function dynamically (module name starts with number)
migration_module = importlib.import_module(
    "apps.core.migrations.0038_mark_test_projects"
)
mark_test_projects = migration_module.mark_test_projects
unmark_test_projects = migration_module.unmark_test_projects


@pytest.mark.django_db
class TestMarkTestProjectsMigration:
    """Tests for mark_test_projects data migration."""

    def test_migration_marks_all_8_test_projects(self, clean_projetos):
        """Test that all 8 test projects are marked."""
        # Create all 8 test projects
        test_projects = [
            "SMOKE SUPER",
            "SMOKE NAO_SUPER",
            "TESTE E2E",
            "Test Detail",
            "Test Proj",
            "Test Project",
            "Teste Auto SUPER",
            "Teste Auto NAO_SUPER",
        ]

        for nome in test_projects:
            Projeto.objects.create(nome=nome, fluxo="NAO_SUPER", ativo=True, is_test=False)

        # Verify all are is_test=False before migration
        assert Projeto.objects.filter(is_test=False).count() == 8

        # Run migration
        mark_test_projects(None, None)

        # Verify all are is_test=True after migration
        assert Projeto.objects.filter(is_test=True).count() == 8
        assert Projeto.objects.filter(is_test=False).count() == 0

        # Verify each project individually
        for nome in test_projects:
            projeto = Projeto.objects.get(nome=nome)
            assert projeto.is_test is True, f"{nome} should be marked as test"

    def test_migration_preserves_production_projects(self, clean_projetos):
        """Test that production projects are not affected."""
        # Create production projects
        Projeto.objects.create(nome="ACERTA MATEMÁTICA", fluxo="NAO_SUPER", ativo=True, is_test=False)
        Projeto.objects.create(nome="CIRANDAR", fluxo="SUPER", ativo=True, is_test=False)

        # Create one test project
        Projeto.objects.create(nome="SMOKE SUPER", fluxo="SUPER", ativo=True, is_test=False)

        # Run migration
        mark_test_projects(None, None)

        # Verify production projects unchanged
        assert Projeto.objects.get(nome="ACERTA MATEMÁTICA").is_test is False
        assert Projeto.objects.get(nome="CIRANDAR").is_test is False

        # Verify test project marked
        assert Projeto.objects.get(nome="SMOKE SUPER").is_test is True

    def test_migration_idempotent(self, clean_projetos):
        """Test that running migration twice doesn't cause issues."""
        # Create test project
        Projeto.objects.create(nome="SMOKE SUPER", fluxo="SUPER", ativo=True, is_test=False)

        # Run migration twice
        mark_test_projects(None, None)
        mark_test_projects(None, None)

        # Verify still marked (not broken)
        projeto = Projeto.objects.get(nome="SMOKE SUPER")
        assert projeto.is_test is True

    def test_migration_skips_already_marked(self, clean_projetos):
        """Test that migration skips projects already marked as test."""
        # Create project already marked
        Projeto.objects.create(nome="SMOKE SUPER", fluxo="SUPER", ativo=True, is_test=True)

        # Run migration
        mark_test_projects(None, None)

        # Verify unchanged
        projeto = Projeto.objects.get(nome="SMOKE SUPER")
        assert projeto.is_test is True

    def test_migration_reversible(self, clean_projetos):
        """Test that migration can be reversed."""
        # Create test projects
        test_projects = ["SMOKE SUPER", "TESTE E2E", "Test Detail"]
        for nome in test_projects:
            Projeto.objects.create(nome=nome, fluxo="SUPER", ativo=True, is_test=False)

        # Forward migration
        mark_test_projects(None, None)

        # Verify all marked
        for nome in test_projects:
            assert Projeto.objects.get(nome=nome).is_test is True

        # Reverse migration
        unmark_test_projects(None, None)

        # Verify all unmarked
        for nome in test_projects:
            assert Projeto.objects.get(nome=nome).is_test is False

    def test_migration_handles_missing_projects(self, clean_projetos):
        """Test that migration handles missing projects gracefully."""
        # Create only 3 of 8 test projects
        Projeto.objects.create(nome="SMOKE SUPER", fluxo="SUPER", ativo=True, is_test=False)
        Projeto.objects.create(nome="TESTE E2E", fluxo="SUPER", ativo=True, is_test=False)
        Projeto.objects.create(nome="Test Detail", fluxo="SUPER", ativo=True, is_test=False)

        # Run migration (should not crash on missing projects)
        mark_test_projects(None, None)

        # Verify existing projects were marked
        assert Projeto.objects.get(nome="SMOKE SUPER").is_test is True
        assert Projeto.objects.get(nome="TESTE E2E").is_test is True
        assert Projeto.objects.get(nome="Test Detail").is_test is True

        # Verify count
        assert Projeto.objects.filter(is_test=True).count() == 3

    def test_migration_counts_correctly(self, clean_projetos):
        """Test that migration reports correct counts."""
        # Create all 8 test projects
        test_projects = [
            "SMOKE SUPER",
            "SMOKE NAO_SUPER",
            "TESTE E2E",
            "Test Detail",
            "Test Proj",
            "Test Project",
            "Teste Auto SUPER",
            "Teste Auto NAO_SUPER",
        ]

        for nome in test_projects:
            Projeto.objects.create(nome=nome, fluxo="NAO_SUPER", ativo=True, is_test=False)

        # Run migration
        mark_test_projects(None, None)

        # Verify count: all 8 should be marked
        marked_count = Projeto.objects.filter(is_test=True).count()
        assert marked_count == 8

    def test_migration_mixed_scenario(self, clean_projetos):
        """Test migration with mixed scenario: some marked, some not, some missing."""
        # Create 4 test projects, 2 already marked
        Projeto.objects.create(nome="SMOKE SUPER", fluxo="SUPER", ativo=True, is_test=True)  # Already marked
        Projeto.objects.create(nome="SMOKE NAO_SUPER", fluxo="NAO_SUPER", ativo=True, is_test=False)
        Projeto.objects.create(nome="TESTE E2E", fluxo="SUPER", ativo=True, is_test=True)  # Already marked
        Projeto.objects.create(nome="Test Detail", fluxo="SUPER", ativo=True, is_test=False)

        # Also create a production project
        Projeto.objects.create(nome="CIRANDAR", fluxo="SUPER", ativo=True, is_test=False)

        # Run migration
        mark_test_projects(None, None)

        # Verify counts
        assert Projeto.objects.filter(is_test=True).count() == 4  # 4 test projects
        assert Projeto.objects.filter(is_test=False).count() == 1  # 1 production project

        # Verify production project unchanged
        assert Projeto.objects.get(nome="CIRANDAR").is_test is False

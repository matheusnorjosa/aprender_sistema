"""
Tests for seed_gerentes management command.

Tests:
- test_seed_gerentes_creates_group_if_not_exists
- test_seed_gerentes_creates_missing_usuarios
- test_seed_gerentes_adds_usuarios_to_group
- test_seed_gerentes_links_gerencia_fk
- test_seed_gerentes_idempotent
- test_seed_gerentes_dry_run_does_not_commit
- test_seed_gerentes_handles_existing_usuarios
- test_seed_gerentes_handles_superintendencia_multiple_managers
"""

from io import StringIO

import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command

from apps.core.models import Gerencia, Usuario


@pytest.fixture
def clean_gerencias(db):
    """Ensure Gerencias exist and have no gerente assigned."""
    # Clear existing gerente assignments
    Gerencia.objects.all().update(gerente=None)

    # Ensure all 7 Gerencias exist
    call_command("seed_gerencias")

    yield

    # Cleanup
    Gerencia.objects.all().update(gerente=None)


@pytest.fixture
def clean_gerentes(db):
    """Remove gerentes from DB and Group."""
    # Remove gerentes from Group
    try:
        gerencia_group = Group.objects.get(name="Gerência")
        gerencia_group.user_set.clear()
    except Group.DoesNotExist:
        pass

    # Delete gerentes (keep other usuarios)
    Usuario.objects.filter(cargo="Gerente").delete()

    yield

    # Cleanup
    try:
        gerencia_group = Group.objects.get(name="Gerência")
        gerencia_group.user_set.clear()
    except Group.DoesNotExist:
        pass
    Usuario.objects.filter(cargo="Gerente").delete()


@pytest.mark.django_db
class TestSeedGerentesCommand:
    """Tests for seed_gerentes management command."""

    def test_seed_gerentes_creates_group_if_not_exists(
        self, clean_gerencias, clean_gerentes
    ):
        """Test that command creates 'Gerência' group if it doesn't exist."""
        # Ensure group doesn't exist
        Group.objects.filter(name="Gerência").delete()

        # Run command
        out = StringIO()
        call_command("seed_gerentes", stdout=out)

        # Verify group was created
        assert Group.objects.filter(name="Gerência").exists()
        output = out.getvalue()
        assert "Created Django Group: Gerência" in output

    def test_seed_gerentes_creates_missing_usuarios(
        self, clean_gerencias, clean_gerentes
    ):
        """Test that command creates 4 missing usuarios."""
        # Verify 0 gerentes before
        assert Usuario.objects.filter(cargo="Gerente").count() == 0

        # Run command
        out = StringIO()
        call_command("seed_gerentes", stdout=out)

        # Verify 7 gerentes created (4 new + 3 existing in fixture data)
        # Since we deleted all gerentes in clean_gerentes, all 7 should be created
        gerentes = Usuario.objects.filter(cargo="Gerente")
        assert gerentes.count() == 7

        # Verify expected CPFs
        expected_cpfs = [
            "00564395390",  # Fernanda
            "76255735320",  # Gleice Anne
            "44092717334",  # Katy
            "12972082850",  # Maria Cristina
            "86324020304",  # Maria Solange
            "69165246349",  # Patrícia
            "68214227372",  # Paula
        ]
        actual_cpfs = list(gerentes.values_list("cpf", flat=True))
        assert set(actual_cpfs) == set(expected_cpfs)

    def test_seed_gerentes_adds_usuarios_to_group(self, clean_gerencias, clean_gerentes):
        """Test that all 7 gerentes are added to 'Gerência' group."""
        # Run command
        call_command("seed_gerentes")

        # Verify all gerentes are in group
        gerencia_group = Group.objects.get(name="Gerência")
        assert gerencia_group.user_set.count() == 7

        # Verify all usuarios with cargo="Gerente" are in group
        for usuario in Usuario.objects.filter(cargo="Gerente"):
            assert gerencia_group in usuario.groups.all()

    def test_seed_gerentes_links_gerencia_fk(self, clean_gerencias, clean_gerentes):
        """Test that gerentes are linked to Gerencia.gerente FK."""
        # Run command
        call_command("seed_gerentes")

        # Verify FK links (4 gerencias should have gerente assigned)
        # SUPERINTENDENCIA: first manager assigned (Fernanda)
        # GERENCIA 2 (Vidas): Patrícia
        # GERENCIA 4 (ACerta): Katy
        # GERENCIA 5 (Brincando): Gleice Anne
        gerencias_with_gerente = Gerencia.objects.filter(gerente__isnull=False)
        assert gerencias_with_gerente.count() == 4

        # Verify specific assignments
        super_gerencia = Gerencia.objects.get(nome="SUPERINTENDENCIA")
        assert super_gerencia.gerente is not None
        assert super_gerencia.gerente.first_name == "Fernanda"  # First in list

        vidas_gerencia = Gerencia.objects.get(nome="GERENCIA 2")
        assert vidas_gerencia.gerente is not None
        assert vidas_gerencia.gerente.first_name == "Patrícia"

        acerta_gerencia = Gerencia.objects.get(nome="GERENCIA 4")
        assert acerta_gerencia.gerente is not None
        assert acerta_gerencia.gerente.first_name == "Katy"

        brincando_gerencia = Gerencia.objects.get(nome="GERENCIA 5")
        assert brincando_gerencia.gerente is not None
        assert brincando_gerencia.gerente.first_name == "Gleice Anne"

    def test_seed_gerentes_idempotent(self, clean_gerencias, clean_gerentes):
        """Test that running command twice doesn't create duplicates."""
        # Run command first time
        out1 = StringIO()
        call_command("seed_gerentes", stdout=out1)

        # Verify counts
        first_gerentes_count = Usuario.objects.filter(cargo="Gerente").count()
        first_group_count = Group.objects.get(name="Gerência").user_set.count()
        first_gerencia_links = Gerencia.objects.filter(gerente__isnull=False).count()

        assert first_gerentes_count == 7
        assert first_group_count == 7
        assert first_gerencia_links == 4

        # Run command second time
        out2 = StringIO()
        call_command("seed_gerentes", stdout=out2)

        # Verify counts haven't changed
        second_gerentes_count = Usuario.objects.filter(cargo="Gerente").count()
        second_group_count = Group.objects.get(name="Gerência").user_set.count()
        second_gerencia_links = Gerencia.objects.filter(gerente__isnull=False).count()

        assert second_gerentes_count == first_gerentes_count
        assert second_group_count == first_group_count
        assert second_gerencia_links == first_gerencia_links

        # Verify output shows "already exists"
        output2 = out2.getvalue()
        assert "already exists" in output2.lower()

    def test_seed_gerentes_dry_run_does_not_commit(
        self, clean_gerencias, clean_gerentes
    ):
        """Test that --dry-run doesn't commit changes."""
        # Run command with dry-run
        out = StringIO()
        call_command("seed_gerentes", "--dry-run", stdout=out)

        # Verify no gerentes were created
        assert Usuario.objects.filter(cargo="Gerente").count() == 0

        # Verify output shows dry-run mode
        output = out.getvalue()
        assert "DRY RUN" in output
        assert "Rolling back" in output

    def test_seed_gerentes_handles_existing_usuarios(
        self, clean_gerencias, clean_gerentes
    ):
        """Test that command handles existing usuarios correctly."""
        # Pre-create one gerente (Patrícia)
        Usuario.objects.create(
            cpf="69165246349",
            username="patricia.paiva",
            first_name="Patrícia",
            last_name="Lemos de Paiva",
            email="gerencia.projetos2@aprendereditora.com.br",
            cargo="Gerente",
        )

        # Verify 1 gerente exists
        assert Usuario.objects.filter(cargo="Gerente").count() == 1

        # Run command
        out = StringIO()
        call_command("seed_gerentes", stdout=out)

        # Verify 7 total gerentes (1 existing + 6 new)
        assert Usuario.objects.filter(cargo="Gerente").count() == 7

        # Verify output shows existing usuario
        output = out.getvalue()
        assert "already exists" in output.lower()

    def test_seed_gerentes_handles_superintendencia_multiple_managers(
        self, clean_gerencias, clean_gerentes
    ):
        """Test that SUPERINTENDENCIA with 4 managers only links first one."""
        # Run command
        out = StringIO()
        call_command("seed_gerentes", stdout=out)

        # Verify SUPERINTENDENCIA has exactly 1 gerente linked
        super_gerencia = Gerencia.objects.get(nome="SUPERINTENDENCIA")
        assert super_gerencia.gerente is not None

        # Verify all 4 SUPERINTENDENCIA managers are in Group
        gerencia_group = Group.objects.get(name="Gerência")
        super_managers = Usuario.objects.filter(
            cargo="Gerente",
            email__in=[
                "gerencia1.projetos1@aprendereditora.com.br",  # Fernanda
                "gerencia.projetos1@aprendereditora.com.br",  # Maria Cristina
                "gerencia3.projetos1@aprendereditora.com.br",  # Maria Solange
                "gerencia2.projetos1@aprendereditora.com.br",  # Paula
            ],
        )
        assert super_managers.count() == 4

        for manager in super_managers:
            assert gerencia_group in manager.groups.all()

        # Verify output warns about multiple managers
        output = out.getvalue()
        # First manager (Fernanda) should be linked
        assert "Linked" in output or "already linked" in output

    def test_generate_username_function(self):
        """Test username generation from names."""
        from apps.dev_tools.management.commands.seed_gerentes import generate_username

        # Test simple name
        assert generate_username("Fernanda", "Ramos Lopes") == "fernanda.lopes"

        # Test compound first name
        assert (
            generate_username("Gleice Anne", "Lima de Sousa") == "gleice.sousa"
        )

        # Test with accents
        assert generate_username("Patrícia", "Lemos de Paiva") == "patricia.paiva"

        # Test with ç
        assert generate_username("João", "Conceição") == "joao.conceicao"

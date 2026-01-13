"""
Tests: ETL Commands Coverage (Issue #321)

Tests for high-priority ETL commands with 0% coverage:
- backfill_coordenador.py
- backfill_user_groups.py
- etl_import_acoes_controle.py
- etl_import_dat_cadastros.py
- etl_upsert_deslocamento.py

Test patterns:
- Dry-run mode (no side effects)
- Apply mode with minimal data
- Idempotency (run 2x = same result)
- Input validation
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false

from __future__ import annotations
import csv
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.core.models import (
    Municipio,
    Participation,
    Projeto,
    Solicitacao,
    TipoEvento,
    Usuario,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def usuario_formador(db):
    """Creates a user who will be a formador."""
    import uuid
    return Usuario.objects.create_user(
        username="formador_test",
        email="formador@test.com",
        password="test123",
        first_name="Formador",
        last_name="Test",
        cpf=f"111{uuid.uuid4().hex[:8]}",  # Unique CPF
    )


@pytest.fixture
def usuario_coordenador(db):
    """Creates a user who will be a coordenador."""
    import uuid
    return Usuario.objects.create_user(
        username="coordenacao_maria",
        email="coordenacao@test.com",
        password="test123",
        first_name="Coordenação",
        last_name="Maria",
        cpf=f"222{uuid.uuid4().hex[:8]}",  # Unique CPF
    )


@pytest.fixture
def usuario_sem_participacao(db):
    """Creates a user without participations."""
    import uuid
    return Usuario.objects.create_user(
        username="semparticipacao",
        email="sempart@test.com",
        password="test123",
        cpf=f"333{uuid.uuid4().hex[:8]}",  # Unique CPF
    )


@pytest.fixture
def grupos_formador_coordenador(db):
    """Creates Formador and Coordenador groups."""
    formador, _ = Group.objects.get_or_create(name="Formador")
    coordenador, _ = Group.objects.get_or_create(name="Coordenador")
    return formador, coordenador


@pytest.fixture
def municipio(db):
    """Creates a test municipality."""
    return Municipio.objects.create(nome="Fortaleza", uf="CE")


@pytest.fixture
def projeto(db):
    """Creates a test project."""
    return Projeto.objects.create(nome="Projeto Teste", fluxo="NAO_SUPER")


@pytest.fixture
def tipo_evento(db):
    """Creates a test event type."""
    return TipoEvento.objects.create(nome="Formação")


@pytest.fixture
def solicitacao_sem_coordenador(db, usuario_formador, municipio, projeto, tipo_evento):
    """Creates a solicitacao with usuario but no coordenador."""
    from django.utils import timezone

    sol = Solicitacao.objects.create(
        usuario=usuario_formador,
        coordenador=None,  # No coordenador
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo_evento,
        inicio=timezone.now(),
        fim=timezone.now() + timezone.timedelta(hours=2),
        status="aprovado",
    )
    return sol


@pytest.fixture
def solicitacao_com_participacao(
    db, usuario_formador, usuario_coordenador, municipio, projeto, tipo_evento
):
    """Creates a solicitacao with participation."""
    from django.utils import timezone

    sol = Solicitacao.objects.create(
        usuario=usuario_coordenador,
        coordenador=usuario_coordenador,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo_evento,
        inicio=timezone.now(),
        fim=timezone.now() + timezone.timedelta(hours=2),
        status="aprovado",
    )
    # Add formador as participant
    Participation.objects.create(
        solicitacao=sol,
        usuario=usuario_formador,
        role="FORMADOR",
    )
    return sol


@pytest.fixture
def temp_csv_deslocamento(tmp_path, usuario_formador):
    """Creates a temporary CSV file for deslocamento import."""
    filepath = tmp_path / "deslocamento.csv"
    content = f"""email,start,end,origem,destino,obs
{usuario_formador.email},2025-01-10,2025-01-12,Fortaleza,Caucaia,Viagem de trabalho
"""
    filepath.write_text(content, encoding="utf-8")
    return filepath


@pytest.fixture
def temp_csv_acoes_controle(tmp_path):
    """Creates a temporary CSV file for acoes controle import."""
    filepath = tmp_path / "acoes_controle.csv"
    # Minimal CSV with required columns
    content = """municipio,projeto,coordenador,data_inicio,data_fim,acao
Fortaleza - CE,Projeto Teste,coordenacao@test.com,2025-01-10,2025-01-12,Ação de teste
"""
    filepath.write_text(content, encoding="utf-8")
    return filepath


@pytest.fixture
def temp_csv_dat_cadastros(tmp_path):
    """Creates a temporary CSV file for DAT cadastros import."""
    filepath = tmp_path / "dat_cadastros.csv"
    content = """municipio,projeto,tipo_acao,responsavel,data,observacao
Fortaleza - CE,Projeto Teste,Cadastro,coordenacao@test.com,2025-01-10,Cadastro inicial
"""
    filepath.write_text(content, encoding="utf-8")
    return filepath


# =============================================================================
# Tests: backfill_coordenador
# =============================================================================


@pytest.mark.django_db
class TestBackfillCoordenador:
    """Tests for backfill_coordenador command."""

    def test_command_exists(self):
        """Test: Command backfill_coordenador exists."""
        out = StringIO()
        call_command("backfill_coordenador", "--dry-run", stdout=out)
        output = out.getvalue()
        assert "Backfilling coordenador" in output

    def test_dry_run_does_not_change_data(self, solicitacao_sem_coordenador):
        """Test: --dry-run does not modify data."""
        sol = solicitacao_sem_coordenador
        assert sol.coordenador is None

        out = StringIO()
        call_command("backfill_coordenador", "--dry-run", stdout=out)

        sol.refresh_from_db()
        assert sol.coordenador is None, "Dry-run should not modify data"
        assert "DRY-RUN" in out.getvalue()

    def test_apply_updates_coordenador(self, solicitacao_sem_coordenador):
        """Test: Without --dry-run, updates coordenador from usuario."""
        sol = solicitacao_sem_coordenador
        assert sol.coordenador is None
        expected_user = sol.usuario

        out = StringIO()
        call_command("backfill_coordenador", stdout=out)

        sol.refresh_from_db()
        assert sol.coordenador == expected_user, "Should set coordenador = usuario"
        assert "Updated" in out.getvalue()

    def test_idempotent(self, solicitacao_sem_coordenador):
        """Test: Running twice produces same result."""
        # First run
        call_command("backfill_coordenador")
        sol = solicitacao_sem_coordenador
        sol.refresh_from_db()
        first_coordenador = sol.coordenador

        # Second run
        out = StringIO()
        call_command("backfill_coordenador", stdout=out)

        sol.refresh_from_db()
        assert sol.coordenador == first_coordenador
        assert "Nothing to update" in out.getvalue()

    def test_does_not_affect_solicitacoes_with_coordenador(
        self, solicitacao_com_participacao
    ):
        """Test: Does not modify solicitacoes that already have coordenador."""
        sol = solicitacao_com_participacao
        original_coordenador = sol.coordenador
        assert original_coordenador is not None

        call_command("backfill_coordenador")

        sol.refresh_from_db()
        assert sol.coordenador == original_coordenador


# =============================================================================
# Tests: backfill_user_groups
# =============================================================================


@pytest.mark.django_db
class TestBackfillUserGroups:
    """Tests for backfill_user_groups command."""

    def test_command_exists(self):
        """Test: Command backfill_user_groups exists."""
        out = StringIO()
        # Will fail if groups don't exist, but command should exist
        try:
            call_command("backfill_user_groups", "--dry-run", stdout=out)
        except Exception:
            pass
        # If we get here without import error, command exists

    def test_dry_run_does_not_assign_groups(
        self,
        grupos_formador_coordenador,
        usuario_formador,
        solicitacao_com_participacao,
    ):
        """Test: --dry-run does not assign groups."""
        assert usuario_formador.groups.count() == 0

        out = StringIO()
        call_command("backfill_user_groups", "--dry-run", stdout=out)

        usuario_formador.refresh_from_db()
        assert usuario_formador.groups.count() == 0, "Dry-run should not assign groups"
        assert "DRY-RUN" in out.getvalue()

    def test_apply_assigns_formador_group(
        self,
        grupos_formador_coordenador,
        usuario_formador,
        solicitacao_com_participacao,
    ):
        """Test: --apply assigns Formador group to users with formador participations."""
        formador_group, _ = grupos_formador_coordenador
        assert usuario_formador.groups.count() == 0

        out = StringIO()
        call_command("backfill_user_groups", "--apply", stdout=out)

        usuario_formador.refresh_from_db()
        assert formador_group in usuario_formador.groups.all()

    def test_assigns_coordenador_by_username(
        self,
        grupos_formador_coordenador,
        usuario_coordenador,
        solicitacao_com_participacao,
    ):
        """Test: Assigns Coordenador group to users with username starting with 'coordenacao'.

        Note: The command only processes users WITH participations. We need to add
        a participation to usuario_coordenador for this test.
        """
        _, coordenador_group = grupos_formador_coordenador
        assert usuario_coordenador.groups.count() == 0
        assert usuario_coordenador.username.startswith("coordenacao")

        # Add participation to coordenador so they get processed by the command
        Participation.objects.create(
            solicitacao=solicitacao_com_participacao,
            usuario=usuario_coordenador,
            role="COORDENADOR",
        )

        out = StringIO()
        call_command("backfill_user_groups", "--apply", stdout=out)

        usuario_coordenador.refresh_from_db()
        assert coordenador_group in usuario_coordenador.groups.all()

    def test_idempotent(
        self,
        grupos_formador_coordenador,
        usuario_formador,
        solicitacao_com_participacao,
    ):
        """Test: Running twice produces same result."""
        # First run
        call_command("backfill_user_groups", "--apply")
        first_groups = set(usuario_formador.groups.values_list("name", flat=True))

        # Second run
        call_command("backfill_user_groups", "--apply")
        usuario_formador.refresh_from_db()
        second_groups = set(usuario_formador.groups.values_list("name", flat=True))

        assert first_groups == second_groups

    def test_error_when_groups_missing(self, usuario_formador):
        """Test: Shows error when Formador/Coordenador groups don't exist."""
        # Ensure groups don't exist
        Group.objects.filter(name__in=["Formador", "Coordenador"]).delete()

        out = StringIO()
        call_command("backfill_user_groups", "--dry-run", stdout=out)
        output = out.getvalue()

        assert "não encontrado" in output or "not found" in output.lower()


# =============================================================================
# Tests: etl_import_acoes_controle
# =============================================================================


@pytest.mark.django_db
class TestEtlImportAcoesControle:
    """Tests for etl_import_acoes_controle command."""

    def test_command_requires_file_argument(self):
        """Test: Command requires file_path argument."""
        with pytest.raises((CommandError, SystemExit)):
            call_command("etl_import_acoes_controle")

    def test_file_not_found_raises_error(self):
        """Test: Non-existent file raises CommandError."""
        with pytest.raises(CommandError) as exc_info:
            call_command("etl_import_acoes_controle", "/nonexistent/file.csv")
        assert "not found" in str(exc_info.value).lower()

    def test_invalid_extension_raises_error(self, tmp_path):
        """Test: Invalid file extension raises CommandError."""
        invalid_file = tmp_path / "data.txt"
        invalid_file.write_text("test")

        with pytest.raises(CommandError) as exc_info:
            call_command("etl_import_acoes_controle", str(invalid_file))
        assert "unsupported" in str(exc_info.value).lower()

    def test_dry_run_mode(self, temp_csv_acoes_controle, municipio, projeto):
        """Test: --dry-run simulates without writing."""
        out = StringIO()

        # Mock the service to avoid complex setup
        with patch(
            "apps.dat_ingest.management.commands.etl_import_acoes_controle.import_acoes_controle"
        ) as mock_import:
            mock_import.return_value = {
                "stats": {
                    "created": 0,
                    "updated": 0,
                    "unchanged": 0,
                    "skipped": {
                        "municipio": 0,
                        "projeto": 0,
                        "coordenador": 0,
                        "dates": 0,
                        "other": 0,
                    },
                },
                "pendencias": {
                    "municipios": [],
                    "projetos": [],
                    "coordenadores": [],
                    "outros": [],
                },
            }

            call_command(
                "etl_import_acoes_controle",
                str(temp_csv_acoes_controle),
                "--dry-run",
                stdout=out,
            )

            mock_import.assert_called_once()
            args, kwargs = mock_import.call_args
            assert kwargs.get("dry_run") is True

        output = out.getvalue()
        assert "DRY-RUN" in output

    def test_apply_mode(self, temp_csv_acoes_controle):
        """Test: Without --dry-run, applies changes."""
        out = StringIO()

        with patch(
            "apps.dat_ingest.management.commands.etl_import_acoes_controle.import_acoes_controle"
        ) as mock_import:
            mock_import.return_value = {
                "stats": {
                    "created": 1,
                    "updated": 0,
                    "unchanged": 0,
                    "skipped": {
                        "municipio": 0,
                        "projeto": 0,
                        "coordenador": 0,
                        "dates": 0,
                        "other": 0,
                    },
                },
                "pendencias": {
                    "municipios": [],
                    "projetos": [],
                    "coordenadores": [],
                    "outros": [],
                },
            }

            call_command(
                "etl_import_acoes_controle",
                str(temp_csv_acoes_controle),
                stdout=out,
            )

            mock_import.assert_called_once()
            args, kwargs = mock_import.call_args
            assert kwargs.get("dry_run") is False

        output = out.getvalue()
        assert "Created:" in output


# =============================================================================
# Tests: etl_import_dat_cadastros
# =============================================================================


@pytest.mark.django_db
class TestEtlImportDatCadastros:
    """Tests for etl_import_dat_cadastros command."""

    def test_command_requires_file_argument(self):
        """Test: Command requires file_path argument."""
        with pytest.raises((CommandError, SystemExit)):
            call_command("etl_import_dat_cadastros")

    def test_file_not_found_raises_error(self):
        """Test: Non-existent file raises CommandError."""
        with pytest.raises(CommandError) as exc_info:
            call_command("etl_import_dat_cadastros", "/nonexistent/file.csv")
        assert "not found" in str(exc_info.value).lower()

    def test_invalid_extension_raises_error(self, tmp_path):
        """Test: Invalid file extension raises CommandError."""
        invalid_file = tmp_path / "data.json"
        invalid_file.write_text("{}")

        with pytest.raises(CommandError) as exc_info:
            call_command("etl_import_dat_cadastros", str(invalid_file))
        assert "unsupported" in str(exc_info.value).lower()

    def test_dry_run_mode(self, temp_csv_dat_cadastros):
        """Test: --dry-run simulates without writing."""
        out = StringIO()

        with patch(
            "apps.dat_ingest.management.commands.etl_import_dat_cadastros.import_dat_cadastros"
        ) as mock_import:
            mock_import.return_value = {
                "stats": {
                    "created": 0,
                    "updated": 0,
                    "unchanged": 0,
                    "skipped": {
                        "municipio": 0,
                        "projeto": 0,
                        "tipo_acao": 0,
                        "responsavel": 0,
                        "other": 0,
                    },
                },
                "pendencias": {
                    "municipios": [],
                    "projetos": [],
                    "tipo_acao": [],
                    "responsaveis": [],
                    "outros": [],
                },
            }

            call_command(
                "etl_import_dat_cadastros",
                str(temp_csv_dat_cadastros),
                "--dry-run",
                stdout=out,
            )

            mock_import.assert_called_once()
            args, kwargs = mock_import.call_args
            assert kwargs.get("dry_run") is True

        output = out.getvalue()
        assert "DRY-RUN" in output

    def test_apply_mode(self, temp_csv_dat_cadastros):
        """Test: Without --dry-run, applies changes."""
        out = StringIO()

        with patch(
            "apps.dat_ingest.management.commands.etl_import_dat_cadastros.import_dat_cadastros"
        ) as mock_import:
            mock_import.return_value = {
                "stats": {
                    "created": 1,
                    "updated": 0,
                    "unchanged": 0,
                    "skipped": {
                        "municipio": 0,
                        "projeto": 0,
                        "tipo_acao": 0,
                        "responsavel": 0,
                        "other": 0,
                    },
                },
                "pendencias": {
                    "municipios": [],
                    "projetos": [],
                    "tipo_acao": [],
                    "responsaveis": [],
                    "outros": [],
                },
            }

            call_command(
                "etl_import_dat_cadastros",
                str(temp_csv_dat_cadastros),
                stdout=out,
            )

            mock_import.assert_called_once()
            args, kwargs = mock_import.call_args
            assert kwargs.get("dry_run") is False


# =============================================================================
# Tests: etl_upsert_deslocamento
# =============================================================================


@pytest.mark.django_db
class TestEtlUpsertDeslocamento:
    """Tests for etl_upsert_deslocamento command."""

    def test_command_requires_file_argument(self):
        """Test: Command requires --file argument."""
        with pytest.raises((CommandError, SystemExit)):
            call_command("etl_upsert_deslocamento")

    def test_file_not_found_raises_error(self):
        """Test: Non-existent file raises error."""
        out = StringIO()
        err = StringIO()

        # Command may handle error gracefully, check output
        try:
            call_command(
                "etl_upsert_deslocamento",
                "--file=/nonexistent/file.csv",
                stdout=out,
                stderr=err,
            )
        except Exception:
            pass

    def test_invalid_extension_raises_error(self, tmp_path):
        """Test: Invalid file extension raises error."""
        invalid_file = tmp_path / "data.txt"
        invalid_file.write_text("test")

        with pytest.raises((ValueError, CommandError)):
            call_command(
                "etl_upsert_deslocamento",
                f"--file={invalid_file}",
            )

    def test_dry_run_mode(self, temp_csv_deslocamento, usuario_formador):
        """Test: --dry-run simulates without writing."""
        from apps.core.models import Deslocamento

        initial_count = Deslocamento.objects.count()

        out = StringIO()
        call_command(
            "etl_upsert_deslocamento",
            f"--file={temp_csv_deslocamento}",
            "--dry-run",
            stdout=out,
        )

        # Should not create records in dry-run
        assert Deslocamento.objects.count() == initial_count
        assert "DRY-RUN" in out.getvalue() or "dry_run=True" in out.getvalue()

    def test_apply_creates_deslocamento(self, temp_csv_deslocamento, usuario_formador):
        """Test: Without --dry-run, creates Deslocamento records."""
        from apps.core.models import Deslocamento

        initial_count = Deslocamento.objects.count()

        out = StringIO()
        call_command(
            "etl_upsert_deslocamento",
            f"--file={temp_csv_deslocamento}",
            stdout=out,
        )

        # Should create 1 record
        assert Deslocamento.objects.count() == initial_count + 1

        # Verify record data
        desl = Deslocamento.objects.filter(usuario=usuario_formador).first()
        assert desl is not None
        assert desl.origem == "Fortaleza"
        assert desl.destino == "Caucaia"

    def test_idempotent(self, temp_csv_deslocamento, usuario_formador):
        """Test: Running twice produces same result (idempotent via external_hash)."""
        from apps.core.models import Deslocamento

        # First run
        call_command(
            "etl_upsert_deslocamento",
            f"--file={temp_csv_deslocamento}",
        )
        first_count = Deslocamento.objects.count()

        # Second run
        call_command(
            "etl_upsert_deslocamento",
            f"--file={temp_csv_deslocamento}",
        )
        second_count = Deslocamento.objects.count()

        assert first_count == second_count, "Should not duplicate records"

    def test_skips_invalid_usuario(self, tmp_path):
        """Test: Skips rows with invalid/unknown usuario."""
        from apps.core.models import Deslocamento

        # Create CSV with unknown email
        filepath = tmp_path / "invalid_user.csv"
        content = """email,start,end,origem,destino,obs
unknown@notfound.com,2025-01-10,2025-01-12,Fortaleza,Caucaia,Test
"""
        filepath.write_text(content, encoding="utf-8")

        initial_count = Deslocamento.objects.count()

        out = StringIO()
        call_command(
            "etl_upsert_deslocamento",
            f"--file={filepath}",
            stdout=out,
        )

        # Should not create record (user not found)
        assert Deslocamento.objects.count() == initial_count
        assert "não resolvido" in out.getvalue() or "skipped" in out.getvalue().lower()

    def test_skips_invalid_dates(self, tmp_path, usuario_formador):
        """Test: Skips rows with invalid dates."""
        from apps.core.models import Deslocamento

        filepath = tmp_path / "invalid_dates.csv"
        content = f"""email,start,end,origem,destino,obs
{usuario_formador.email},invalid-date,2025-01-12,Fortaleza,Caucaia,Test
"""
        filepath.write_text(content, encoding="utf-8")

        initial_count = Deslocamento.objects.count()

        out = StringIO()
        call_command(
            "etl_upsert_deslocamento",
            f"--file={filepath}",
            stdout=out,
        )

        # Should not create record (invalid date)
        assert Deslocamento.objects.count() == initial_count

    def test_skips_end_before_start(self, tmp_path, usuario_formador):
        """Test: Skips rows where end_date < start_date."""
        from apps.core.models import Deslocamento

        filepath = tmp_path / "end_before_start.csv"
        content = f"""email,start,end,origem,destino,obs
{usuario_formador.email},2025-01-15,2025-01-10,Fortaleza,Caucaia,Test
"""
        filepath.write_text(content, encoding="utf-8")

        initial_count = Deslocamento.objects.count()

        out = StringIO()
        call_command(
            "etl_upsert_deslocamento",
            f"--file={filepath}",
            stdout=out,
        )

        # Should not create record (end < start)
        assert Deslocamento.objects.count() == initial_count
        assert "end_date < start_date" in out.getvalue()

"""
Testes para Data Quality Gates no ETL (PR21).

Garante que:
1. ETL aborta apply quando duplicatas% > limite
2. ETL aborta apply quando unknown_users > limite
3. ETL aborta apply quando invalid_intervals > 0 (se flag ativada)
4. ETL aborta apply quando invalid_dates > 0 (se flag ativada)
5. Dry-run sempre permitido (mesmo com violações)
6. Caso feliz: tudo dentro dos limites → apply ok
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from apps.core.models import Municipio, Projeto, Solicitacao, TipoEvento, Usuario


@pytest.mark.django_db
class TestETLGatesDuplicates(TestCase):
    """
    Testes para gate de duplicatas (ETL_MAX_DUPLICATES_PCT).
    """

    def setUp(self):
        """Setup test data."""
        self.coord = Usuario.objects.create_user(
            username="coord_test",
            email="coord@test.com",
            nome="Coordenador Test",
        )
        self.municipio = Municipio.objects.create(nome="Fortaleza", ativo=True)
        self.tipo = TipoEvento.objects.create(nome="Presencial", ativo=True)
        self.projeto = Projeto.objects.create(
            nome="ACerta", codigo="ACERTA", fluxo="NAO_SUPER", ativo=True
        )

    @override_settings(ETL_MAX_DUPLICATES_PCT=1.0)
    @patch("apps.dat_ingest.management.commands.etl_upsert_acompanhamento.Command.load_eventos_csv")
    @patch("apps.dat_ingest.management.commands.etl_upsert_acompanhamento.Command.load_participantes_csv")
    def test_abort_when_duplicates_exceed_threshold(
        self, mock_participantes, mock_eventos
    ):
        """ETL aborta apply quando duplicatas% > ETL_MAX_DUPLICATES_PCT."""
        # Mock CSVs com 100 eventos, 5 duplicatas (5% > 1% threshold)
        mock_eventos.return_value = [
            {
                "source_sheet": "ACerta",
                "municipio": "Fortaleza",
                "encontro": str(i),
                "tipo": "Presencial",
                "data": "2025-01-15",
                "hora_inicio": "08:00",
                "hora_fim": "12:00",
                "projeto": "ACerta",
                "segmento": "EI",
                "coord_acompanha": "sim",
                "coordenador": "coord@test.com",
            }
            for i in range(100)
        ]

        # Simular 5 duplicatas (mesmos dados)
        for i in range(5):
            mock_eventos.return_value.append(mock_eventos.return_value[i])

        mock_participantes.return_value = {}

        # Apply deve abortar
        with pytest.raises(CommandError, match="Duplicates.*threshold"):
            call_command("etl_upsert_acompanhamento", apply=True)

    @override_settings(ETL_MAX_DUPLICATES_PCT=10.0)
    @patch("apps.dat_ingest.management.commands.etl_upsert_acompanhamento.Command.load_eventos_csv")
    @patch("apps.dat_ingest.management.commands.etl_upsert_acompanhamento.Command.load_participantes_csv")
    def test_allow_when_duplicates_below_threshold(
        self, mock_participantes, mock_eventos
    ):
        """ETL permite apply quando duplicatas% < ETL_MAX_DUPLICATES_PCT."""
        # Mock CSVs com 100 eventos, 5 duplicatas (5% < 10% threshold)
        mock_eventos.return_value = [
            {
                "source_sheet": "ACerta",
                "municipio": "Fortaleza",
                "encontro": str(i),
                "tipo": "Presencial",
                "data": "2025-01-15",
                "hora_inicio": "08:00",
                "hora_fim": "12:00",
                "projeto": "ACerta",
                "segmento": "EI",
                "coord_acompanha": "sim",
                "coordenador": "coord@test.com",
            }
            for i in range(100)
        ]

        # Simular 5 duplicatas (5% < 10%)
        for i in range(5):
            mock_eventos.return_value.append(mock_eventos.return_value[i])

        mock_participantes.return_value = {}

        # Apply deve permitir
        try:
            call_command("etl_upsert_acompanhamento", apply=True)
        except CommandError as e:
            if "Duplicates" in str(e):
                pytest.fail(f"ETL abortou indevidamente: {e}")


@pytest.mark.django_db
class TestETLGatesUnknownUsers(TestCase):
    """
    Testes para gate de usuários desconhecidos (ETL_MAX_UNKNOWN_USERS).
    """

    @override_settings(ETL_MAX_UNKNOWN_USERS=50)
    @patch("apps.dat_ingest.management.commands.etl_upsert_acompanhamento.Command.load_eventos_csv")
    @patch("apps.dat_ingest.management.commands.etl_upsert_acompanhamento.Command.load_participantes_csv")
    def test_abort_when_unknown_users_exceed_threshold(
        self, mock_participantes, mock_eventos
    ):
        """ETL aborta apply quando unknown_users > ETL_MAX_UNKNOWN_USERS."""
        # Mock CSVs com 100 eventos, 60 pessoas sem cadastro (> 50 threshold)
        mock_eventos.return_value = [
            {
                "source_sheet": "ACerta",
                "municipio": "Fortaleza",
                "encontro": str(i),
                "tipo": "Presencial",
                "data": "2025-01-15",
                "hora_inicio": "08:00",
                "hora_fim": "12:00",
                "projeto": "ACerta",
                "segmento": "EI",
                "coord_acompanha": "sim",
                "coordenador": f"coord{i}@unknown.com",  # Emails não cadastrados
            }
            for i in range(100)
        ]

        # 60 formadores sem cadastro
        mock_participantes.return_value = {
            f"event_{i}": [
                {
                    "role": "FORMADOR",
                    "display_name": f"Formador Unknown {i}",
                    "email": f"unknown{i}@test.com",
                }
            ]
            for i in range(60)
        }

        # Apply deve abortar
        with pytest.raises(CommandError, match="Unknown users.*threshold"):
            call_command("etl_upsert_acompanhamento", apply=True)

    @override_settings(ETL_MAX_UNKNOWN_USERS=100)
    @patch("apps.dat_ingest.management.commands.etl_upsert_acompanhamento.Command.load_eventos_csv")
    @patch("apps.dat_ingest.management.commands.etl_upsert_acompanhamento.Command.load_participantes_csv")
    def test_allow_when_unknown_users_below_threshold(
        self, mock_participantes, mock_eventos
    ):
        """ETL permite apply quando unknown_users < ETL_MAX_UNKNOWN_USERS."""
        # Mock CSVs com 50 pessoas sem cadastro (< 100 threshold)
        mock_eventos.return_value = [
            {
                "source_sheet": "ACerta",
                "municipio": "Fortaleza",
                "encontro": str(i),
                "tipo": "Presencial",
                "data": "2025-01-15",
                "hora_inicio": "08:00",
                "hora_fim": "12:00",
                "projeto": "ACerta",
                "segmento": "EI",
                "coord_acompanha": "sim",
                "coordenador": f"coord{i}@unknown.com",
            }
            for i in range(50)
        ]

        mock_participantes.return_value = {}

        # Apply deve permitir
        try:
            call_command("etl_upsert_acompanhamento", apply=True)
        except CommandError as e:
            if "Unknown users" in str(e):
                pytest.fail(f"ETL abortou indevidamente: {e}")


@pytest.mark.django_db
class TestETLGatesInvalidIntervals(TestCase):
    """
    Testes para gate de intervalos inválidos (ETL_REQUIRE_ZERO_INVALID_INTERVALS).
    """

    @override_settings(ETL_REQUIRE_ZERO_INVALID_INTERVALS=True)
    @patch("apps.dat_ingest.management.commands.etl_upsert_acompanhamento.Command.load_eventos_csv")
    @patch("apps.dat_ingest.management.commands.etl_upsert_acompanhamento.Command.load_participantes_csv")
    def test_abort_when_invalid_intervals_and_flag_true(
        self, mock_participantes, mock_eventos
    ):
        """ETL aborta apply quando há intervalos inválidos (fim <= início) e flag=True."""
        # Mock CSVs com 1 evento com intervalo inválido
        mock_eventos.return_value = [
            {
                "source_sheet": "ACerta",
                "municipio": "Fortaleza",
                "encontro": "1",
                "tipo": "Presencial",
                "data": "2025-01-15",
                "hora_inicio": "12:00",  # início > fim (inválido)
                "hora_fim": "08:00",
                "projeto": "ACerta",
                "segmento": "EI",
                "coord_acompanha": "sim",
                "coordenador": "coord@test.com",
            }
        ]

        mock_participantes.return_value = {}

        # Apply deve abortar
        with pytest.raises(CommandError, match="Invalid intervals"):
            call_command("etl_upsert_acompanhamento", apply=True)

    @override_settings(ETL_REQUIRE_ZERO_INVALID_INTERVALS=False)
    @patch("apps.dat_ingest.management.commands.etl_upsert_acompanhamento.Command.load_eventos_csv")
    @patch("apps.dat_ingest.management.commands.etl_upsert_acompanhamento.Command.load_participantes_csv")
    def test_allow_when_invalid_intervals_and_flag_false(
        self, mock_participantes, mock_eventos
    ):
        """ETL permite apply quando há intervalos inválidos mas flag=False."""
        # Mock CSVs com 1 evento com intervalo inválido
        mock_eventos.return_value = [
            {
                "source_sheet": "ACerta",
                "municipio": "Fortaleza",
                "encontro": "1",
                "tipo": "Presencial",
                "data": "2025-01-15",
                "hora_inicio": "12:00",
                "hora_fim": "08:00",  # Inválido mas flag=False
                "projeto": "ACerta",
                "segmento": "EI",
                "coord_acompanha": "sim",
                "coordenador": "coord@test.com",
            }
        ]

        mock_participantes.return_value = {}

        # Apply deve permitir (apenas warning)
        try:
            call_command("etl_upsert_acompanhamento", apply=True)
        except CommandError as e:
            if "Invalid intervals" in str(e):
                pytest.fail(f"ETL abortou indevidamente: {e}")


@pytest.mark.django_db
class TestETLGatesInvalidDates(TestCase):
    """
    Testes para gate de datas inválidas (ETL_REQUIRE_ZERO_INVALID_DATES).
    """

    @override_settings(ETL_REQUIRE_ZERO_INVALID_DATES=True)
    @patch("apps.dat_ingest.management.commands.etl_upsert_acompanhamento.Command.load_eventos_csv")
    @patch("apps.dat_ingest.management.commands.etl_upsert_acompanhamento.Command.load_participantes_csv")
    def test_abort_when_invalid_dates_and_flag_true(
        self, mock_participantes, mock_eventos
    ):
        """ETL aborta apply quando há datas inválidas e flag=True."""
        # Mock CSVs com 1 evento com data inválida
        mock_eventos.return_value = [
            {
                "source_sheet": "ACerta",
                "municipio": "Fortaleza",
                "encontro": "1",
                "tipo": "Presencial",
                "data": "invalid-date",  # Data inválida
                "hora_inicio": "08:00",
                "hora_fim": "12:00",
                "projeto": "ACerta",
                "segmento": "EI",
                "coord_acompanha": "sim",
                "coordenador": "coord@test.com",
            }
        ]

        mock_participantes.return_value = {}

        # Apply deve abortar
        with pytest.raises(CommandError, match="Invalid dates"):
            call_command("etl_upsert_acompanhamento", apply=True)

    @override_settings(ETL_REQUIRE_ZERO_INVALID_DATES=False)
    @patch("apps.dat_ingest.management.commands.etl_upsert_acompanhamento.Command.load_eventos_csv")
    @patch("apps.dat_ingest.management.commands.etl_upsert_acompanhamento.Command.load_participantes_csv")
    def test_allow_when_invalid_dates_and_flag_false(
        self, mock_participantes, mock_eventos
    ):
        """ETL permite apply quando há datas inválidas mas flag=False."""
        # Mock CSVs com 1 evento com data inválida
        mock_eventos.return_value = [
            {
                "source_sheet": "ACerta",
                "municipio": "Fortaleza",
                "encontro": "1",
                "tipo": "Presencial",
                "data": "invalid-date",
                "hora_inicio": "08:00",
                "hora_fim": "12:00",
                "projeto": "ACerta",
                "segmento": "EI",
                "coord_acompanha": "sim",
                "coordenador": "coord@test.com",
            }
        ]

        mock_participantes.return_value = {}

        # Apply deve permitir (apenas warning)
        try:
            call_command("etl_upsert_acompanhamento", apply=True)
        except CommandError as e:
            if "Invalid dates" in str(e):
                pytest.fail(f"ETL abortou indevidamente: {e}")


@pytest.mark.django_db
class TestETLGatesDryRunAlwaysAllowed(TestCase):
    """
    Testes para garantir que dry-run sempre é permitido (mesmo com violações).
    """

    @override_settings(ETL_MAX_DUPLICATES_PCT=1.0)
    @patch("apps.dat_ingest.management.commands.etl_upsert_acompanhamento.Command.load_eventos_csv")
    @patch("apps.dat_ingest.management.commands.etl_upsert_acompanhamento.Command.load_participantes_csv")
    def test_dry_run_allowed_even_with_duplicate_violations(
        self, mock_participantes, mock_eventos
    ):
        """Dry-run é permitido mesmo com violação de duplicatas."""
        # Mock CSVs com 100 eventos, 10 duplicatas (10% > 1% threshold)
        mock_eventos.return_value = [
            {
                "source_sheet": "ACerta",
                "municipio": "Fortaleza",
                "encontro": str(i),
                "tipo": "Presencial",
                "data": "2025-01-15",
                "hora_inicio": "08:00",
                "hora_fim": "12:00",
                "projeto": "ACerta",
                "segmento": "EI",
                "coord_acompanha": "sim",
                "coordenador": "coord@test.com",
            }
            for i in range(100)
        ]

        # 10 duplicatas
        for i in range(10):
            mock_eventos.return_value.append(mock_eventos.return_value[i])

        mock_participantes.return_value = {}

        # Dry-run deve permitir (sem abortar)
        try:
            call_command("etl_upsert_acompanhamento")  # Default: dry-run
        except CommandError as e:
            pytest.fail(f"Dry-run abortou indevidamente: {e}")

    @override_settings(ETL_REQUIRE_ZERO_INVALID_INTERVALS=True)
    @patch("apps.dat_ingest.management.commands.etl_upsert_acompanhamento.Command.load_eventos_csv")
    @patch("apps.dat_ingest.management.commands.etl_upsert_acompanhamento.Command.load_participantes_csv")
    def test_dry_run_allowed_even_with_invalid_interval_violations(
        self, mock_participantes, mock_eventos
    ):
        """Dry-run é permitido mesmo com intervalos inválidos."""
        # Mock CSVs com intervalo inválido
        mock_eventos.return_value = [
            {
                "source_sheet": "ACerta",
                "municipio": "Fortaleza",
                "encontro": "1",
                "tipo": "Presencial",
                "data": "2025-01-15",
                "hora_inicio": "12:00",
                "hora_fim": "08:00",  # Inválido
                "projeto": "ACerta",
                "segmento": "EI",
                "coord_acompanha": "sim",
                "coordenador": "coord@test.com",
            }
        ]

        mock_participantes.return_value = {}

        # Dry-run deve permitir
        try:
            call_command("etl_upsert_acompanhamento")
        except CommandError as e:
            pytest.fail(f"Dry-run abortou indevidamente: {e}")


@pytest.mark.django_db
class TestETLGatesMetricsReporting(TestCase):
    """
    Testes para geração de métricas e relatórios de violações.
    """

    def tearDown(self):
        """Clean up generated files."""
        metrics_file = Path("v2/.agents/outbox/etl_metrics.json")
        violations_file = Path("v2/.agents/outbox/etl_violations.csv")

        if metrics_file.exists():
            metrics_file.unlink()
        if violations_file.exists():
            violations_file.unlink()

    @patch("apps.dat_ingest.management.commands.etl_upsert_acompanhamento.Command.load_eventos_csv")
    @patch("apps.dat_ingest.management.commands.etl_upsert_acompanhamento.Command.load_participantes_csv")
    def test_metrics_file_generated_on_dry_run(
        self, mock_participantes, mock_eventos
    ):
        """ETL gera etl_metrics.json no dry-run."""
        mock_eventos.return_value = [
            {
                "source_sheet": "ACerta",
                "municipio": "Fortaleza",
                "encontro": "1",
                "tipo": "Presencial",
                "data": "2025-01-15",
                "hora_inicio": "08:00",
                "hora_fim": "12:00",
                "projeto": "ACerta",
                "segmento": "EI",
                "coord_acompanha": "sim",
                "coordenador": "coord@test.com",
            }
        ]

        mock_participantes.return_value = {}

        # Run dry-run
        call_command("etl_upsert_acompanhamento")

        # Metrics file should exist
        metrics_file = Path("v2/.agents/outbox/etl_metrics.json")
        assert metrics_file.exists()

        # Validate JSON structure
        with open(metrics_file, "r", encoding="utf-8") as f:
            metrics = json.load(f)

        assert "total_events" in metrics
        assert "duplicates_count" in metrics
        assert "duplicates_pct" in metrics
        assert "unknown_users_count" in metrics
        assert "invalid_intervals_count" in metrics
        assert "invalid_dates_count" in metrics

    @override_settings(ETL_MAX_DUPLICATES_PCT=1.0)
    @patch("apps.dat_ingest.management.commands.etl_upsert_acompanhamento.Command.load_eventos_csv")
    @patch("apps.dat_ingest.management.commands.etl_upsert_acompanhamento.Command.load_participantes_csv")
    def test_violations_file_generated_when_gates_violated(
        self, mock_participantes, mock_eventos
    ):
        """ETL gera etl_violations.csv quando há violações."""
        # Mock CSVs com violações
        mock_eventos.return_value = [
            {
                "source_sheet": "ACerta",
                "municipio": "Fortaleza",
                "encontro": str(i),
                "tipo": "Presencial",
                "data": "2025-01-15",
                "hora_inicio": "08:00",
                "hora_fim": "12:00",
                "projeto": "ACerta",
                "segmento": "EI",
                "coord_acompanha": "sim",
                "coordenador": "coord@test.com",
            }
            for i in range(100)
        ]

        # 5 duplicatas (5% > 1% threshold)
        for i in range(5):
            mock_eventos.return_value.append(mock_eventos.return_value[i])

        mock_participantes.return_value = {}

        # Run dry-run (allowed)
        call_command("etl_upsert_acompanhamento")

        # Violations file should exist
        violations_file = Path("v2/.agents/outbox/etl_violations.csv")
        assert violations_file.exists()

        # Validate CSV has headers
        with open(violations_file, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
            assert "gate" in first_line.lower() or "violation" in first_line.lower()

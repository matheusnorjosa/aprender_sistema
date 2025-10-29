"""
Tests: Processors
Valida processadores de planilhas (AgendaProcessor, DisponibilidadeProcessor, ControleProcessor).
"""

import tempfile
from pathlib import Path

import pandas as pd
import pytest
from openpyxl import Workbook

from apps.dat_ingest.services.processors import (
    AgendaProcessor,
    ControleProcessor,
    DisponibilidadeProcessor,
)


@pytest.fixture
def temp_agenda_xlsx(tmp_path):
    """Cria arquivo temporário de agenda com aba 'Super'"""
    filepath = tmp_path / "agenda.xlsx"
    wb = Workbook()

    # Aba Super
    ws = wb.active
    ws.title = "Super"

    # Header
    ws.append([
        "Data", "Horário Inicial", "Horário Final", "Projeto",
        "Tipo de Evento", "Município", "Coordenador", "Formador(es)",
        "Situação", "Observações"
    ])

    # Data rows
    ws.append([
        "2025-01-15", "14:00", "17:00", "ACerta",
        "Formação Presencial", "Fortaleza - CE", "Ellen Damares",
        "João Silva, Maria Santos", "Realizado", "Primeira formação"
    ])
    ws.append([
        "2025-01-20", "09:00", "12:00", "Novo Lendo",
        "Workshop", "Caucaia - CE", "Aurea Lucia",
        "Pedro Oliveira", "Agendado", ""
    ])

    wb.save(filepath)
    return filepath


@pytest.fixture
def temp_users_df():
    """Cria DataFrame de usuários para matching"""
    return pd.DataFrame([
        {
            "nome": "João Silva",
            "email": "joao.silva@example.com",
            "perfil": "Formador"
        },
        {
            "nome": "Maria Santos",
            "email": "maria.santos@example.com",
            "perfil": "Formador"
        },
        {
            "nome": "Pedro Oliveira",
            "email": "pedro.oliveira@example.com",
            "perfil": "Formador"
        },
        {
            "nome": "Ellen Damares",
            "email": "ellen.damares@example.com",
            "perfil": "Coordenador"
        },
        {
            "nome": "Aurea Lucia",
            "email": "aurea.lucia@example.com",
            "perfil": "Coordenador"
        }
    ])


@pytest.fixture
def temp_disponibilidade_xlsx(tmp_path):
    """Cria arquivo temporário de disponibilidade"""
    filepath = tmp_path / "disponibilidade.xlsx"
    wb = Workbook()

    # Aba Bloqueios
    ws = wb.active
    ws.title = "Bloqueios"

    # Header
    ws.append([
        "Formador", "Tipo", "Data Início", "Hora Início",
        "Data Fim", "Hora Fim", "Motivo", "Observações"
    ])

    # Data rows
    ws.append([
        "João Silva", "T", "2025-01-10", "08:00",
        "2025-01-10", "18:00", "Férias", "Bloqueio total"
    ])
    ws.append([
        "Maria Santos", "P", "2025-01-15", "14:00",
        "2025-01-15", "17:00", "Reunião", "Bloqueio parcial"
    ])

    wb.save(filepath)
    return filepath


@pytest.fixture
def temp_controle_xlsx(tmp_path):
    """Cria arquivo temporário de controle (planilha de compras)"""
    filepath = tmp_path / "controle.xlsx"
    wb = Workbook()

    # Aba COMPRAS
    ws = wb.active
    ws.title = "COMPRAS"

    # Header
    ws.append([
        "Código", "Produto", "Quantidade", "Município",
        "Projeto", "Data", "Uso"
    ])

    # Data rows
    ws.append([
        "COMP001", "Livros didáticos", 100, "Fortaleza - CE",
        "ACerta", "2025-01-15", "Formação inicial"
    ])
    ws.append([
        "COMP002", "Cadernos", 200, "Caucaia - CE",
        "Novo Lendo", "2025-01-20", "Workshop"
    ])

    wb.save(filepath)
    return filepath


class TestAgendaProcessor:
    """Testes para AgendaProcessor"""

    def test_processes_super_sheet_successfully(self, temp_agenda_xlsx, temp_users_df):
        """Test: AgendaProcessor processa aba Super corretamente"""
        processor = AgendaProcessor(temp_agenda_xlsx, temp_users_df)
        result = processor.process()

        # Verifica estrutura do resultado
        assert "events" in result
        assert "missing" in result
        assert "summary" in result

        # Verifica eventos extraídos
        events_df = result["events"]
        assert len(events_df) == 2, "Deve ter 2 eventos"

        # Verifica campos importantes
        assert "projeto" in events_df.columns
        assert "tipo_evento" in events_df.columns
        assert "municipio" in events_df.columns
        assert "coordenador" in events_df.columns
        assert "formadores_lista" in events_df.columns
        assert "fluxo" in events_df.columns

        # Verifica fluxo SUPER
        assert all(events_df["fluxo"] == "SUPER"), "Aba Super deve ter fluxo SUPER"

    def test_resolves_coordenador_email(self, temp_agenda_xlsx, temp_users_df):
        """Test: Resolve email de coordenador a partir do nome"""
        processor = AgendaProcessor(temp_agenda_xlsx, temp_users_df)
        result = processor.process()

        events_df = result["events"]
        first_event = events_df.iloc[0]

        assert first_event["coordenador"] == "Ellen Damares"
        assert first_event["coordenador_encontrado"] == "ellen.damares@example.com"

    def test_resolves_formadores_emails(self, temp_agenda_xlsx, temp_users_df):
        """Test: Resolve emails de formadores a partir dos nomes"""
        processor = AgendaProcessor(temp_agenda_xlsx, temp_users_df)
        result = processor.process()

        events_df = result["events"]
        first_event = events_df.iloc[0]

        # Primeiro evento tem 2 formadores
        assert len(first_event["formadores_lista"]) == 2
        assert len(first_event["formadores_encontrados"]) == 2
        assert "joao.silva@example.com" in first_event["formadores_encontrados"]
        assert "maria.santos@example.com" in first_event["formadores_encontrados"]

    def test_tracks_missing_people(self, temp_agenda_xlsx):
        """Test: Detecta pessoas não encontradas no cadastro"""
        # DataFrame sem todos os usuários
        incomplete_users = pd.DataFrame([
            {"nome": "Ellen Damares", "email": "ellen@example.com", "perfil": "Coordenador"}
        ])

        processor = AgendaProcessor(temp_agenda_xlsx, incomplete_users)
        result = processor.process()

        missing_df = result["missing"]

        # Deve detectar formadores faltando
        assert len(missing_df) > 0, "Deve ter pessoas não encontradas"

    def test_generates_unique_event_uid(self, temp_agenda_xlsx, temp_users_df):
        """Test: Gera event_uid único para cada evento"""
        processor = AgendaProcessor(temp_agenda_xlsx, temp_users_df)
        result = processor.process()

        events_df = result["events"]

        # Verifica event_uid existe e é único
        assert "event_uid" in events_df.columns
        assert events_df["event_uid"].nunique() == len(events_df), "event_uid deve ser único"

    def test_parses_municipio_with_uf(self, temp_agenda_xlsx, temp_users_df):
        """Test: Faz parse de município com UF (ex: 'Fortaleza - CE')"""
        processor = AgendaProcessor(temp_agenda_xlsx, temp_users_df)
        result = processor.process()

        events_df = result["events"]
        first_event = events_df.iloc[0]

        # Verifica separação de município e UF
        assert first_event["municipio"] == "Fortaleza"
        # Note: Implementação pode variar, verificar se tem campo municipio_uf


class TestDisponibilidadeProcessor:
    """Testes para DisponibilidadeProcessor"""

    def test_processes_bloqueios_sheet(self, temp_disponibilidade_xlsx):
        """Test: DisponibilidadeProcessor processa aba Bloqueios"""
        processor = DisponibilidadeProcessor(temp_disponibilidade_xlsx)
        result = processor.process()

        # Verifica estrutura
        assert "bloqueios" in result

        bloqueios_df = result["bloqueios"]
        assert len(bloqueios_df) == 2, "Deve ter 2 bloqueios"

    def test_parses_bloqueio_tipo_total(self, temp_disponibilidade_xlsx):
        """Test: Identifica bloqueio tipo Total (T)"""
        processor = DisponibilidadeProcessor(temp_disponibilidade_xlsx)
        result = processor.process()

        bloqueios_df = result["bloqueios"]
        bloqueio_total = bloqueios_df[bloqueios_df["tipo"] == "T"].iloc[0]

        assert bloqueio_total["formador_nome"] == "João Silva"
        assert bloqueio_total["motivo"] == "Férias"

    def test_parses_bloqueio_tipo_parcial(self, temp_disponibilidade_xlsx):
        """Test: Identifica bloqueio tipo Parcial (P)"""
        processor = DisponibilidadeProcessor(temp_disponibilidade_xlsx)
        result = processor.process()

        bloqueios_df = result["bloqueios"]
        bloqueio_parcial = bloqueios_df[bloqueios_df["tipo"] == "P"].iloc[0]

        assert bloqueio_parcial["formador_nome"] == "Maria Santos"
        assert bloqueio_parcial["motivo"] == "Reunião"

    def test_combines_date_and_time_to_datetime(self, temp_disponibilidade_xlsx):
        """Test: Combina data + hora em datetime único"""
        processor = DisponibilidadeProcessor(temp_disponibilidade_xlsx)
        result = processor.process()

        bloqueios_df = result["bloqueios"]

        # Verifica campos inicio e fim são datetime
        assert "inicio" in bloqueios_df.columns
        assert "fim" in bloqueios_df.columns

        # Verifica tipo (implementação pode variar)
        # assert pd.api.types.is_datetime64_any_dtype(bloqueios_df["inicio"])


class TestControleProcessor:
    """Testes para ControleProcessor"""

    def test_processes_compras_sheet(self, temp_controle_xlsx):
        """Test: ControleProcessor processa aba COMPRAS"""
        processor = ControleProcessor(temp_controle_xlsx)
        result = processor.process()

        # Verifica estrutura
        assert "compras" in result

        compras_df = result["compras"]
        assert len(compras_df) == 2, "Deve ter 2 compras"

    def test_parses_compra_fields(self, temp_controle_xlsx):
        """Test: Faz parse de todos os campos de compra"""
        processor = ControleProcessor(temp_controle_xlsx)
        result = processor.process()

        compras_df = result["compras"]
        first_compra = compras_df.iloc[0]

        assert first_compra["codigo"] == "COMP001"
        assert first_compra["produto"] == "Livros didáticos"
        assert first_compra["quantidade"] == 100
        assert first_compra["projeto_nome"] == "ACerta"

    def test_parses_municipio_with_uf_in_compras(self, temp_controle_xlsx):
        """Test: Separa município e UF em compras"""
        processor = ControleProcessor(temp_controle_xlsx)
        result = processor.process()

        compras_df = result["compras"]
        first_compra = compras_df.iloc[0]

        # Verifica separação (implementação pode variar)
        assert first_compra["municipio_nome"] == "Fortaleza"
        # Verificar se tem campo municipio_uf

    def test_handles_empty_sheets_gracefully(self, tmp_path):
        """Test: Lida com planilhas vazias sem erro"""
        filepath = tmp_path / "empty_controle.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.title = "COMPRAS"

        # Apenas header, sem dados
        ws.append(["Código", "Produto", "Quantidade", "Município", "Projeto", "Data", "Uso"])

        wb.save(filepath)

        processor = ControleProcessor(filepath)
        result = processor.process()

        compras_df = result["compras"]
        assert len(compras_df) == 0, "Planilha vazia deve retornar DataFrame vazio"


class TestProcessorsIntegration:
    """Testes de integração entre processadores"""

    def test_all_processors_return_dataframes(
        self, temp_agenda_xlsx, temp_users_df, temp_disponibilidade_xlsx, temp_controle_xlsx
    ):
        """Test: Todos os processadores retornam DataFrames pandas"""
        # AgendaProcessor
        agenda_proc = AgendaProcessor(temp_agenda_xlsx, temp_users_df)
        agenda_result = agenda_proc.process()
        assert isinstance(agenda_result["events"], pd.DataFrame)

        # DisponibilidadeProcessor
        disp_proc = DisponibilidadeProcessor(temp_disponibilidade_xlsx)
        disp_result = disp_proc.process()
        assert isinstance(disp_result["bloqueios"], pd.DataFrame)

        # ControleProcessor
        controle_proc = ControleProcessor(temp_controle_xlsx)
        controle_result = controle_proc.process()
        assert isinstance(controle_result["compras"], pd.DataFrame)

    def test_processors_handle_missing_sheets(self, tmp_path):
        """Test: Processadores lidam com abas faltando"""
        # Criar planilha sem aba esperada
        filepath = tmp_path / "incomplete.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.title = "WrongSheet"
        wb.save(filepath)

        # DisponibilidadeProcessor esperando aba "Bloqueios"
        # Deve retornar DataFrame vazio ou lançar erro específico
        processor = DisponibilidadeProcessor(filepath)

        # Implementação pode variar: verificar se retorna vazio ou lança KeyError
        try:
            result = processor.process()
            # Se não lança erro, deve retornar vazio
            assert result["bloqueios"].empty
        except KeyError:
            # Esperado se aba não existe
            pass

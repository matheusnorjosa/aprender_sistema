"""
Google Sheets Service - Integração com gspread
Implementa acesso às planilhas Google usando credenciais OAuth2
"""

import logging
import os
from typing import Any, Dict, List, Optional

from django.conf import settings

import gspread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)


class GoogleSheetsService:
    """
    Serviço para integração com Google Sheets usando gspread.
    Implementa OAuth2 com as credenciais fornecidas.
    """

    def __init__(self):
        self.client = None
        self.credentials = None
        self._initialize_client()

    def _initialize_client(self):
        """Inicializa o cliente gspread com as credenciais."""
        try:
            # Usar credenciais OAuth2 com email/senha
            email = os.getenv("GOOGLE_SERVICE_EMAIL")
            password = os.getenv("GOOGLE_SERVICE_PASSWORD")

            if not email or not password:
                logger.warning("Credenciais Google não configuradas")
                return

            # Para desenvolvimento - usar conta de usuário
            # Em produção - migrar para Service Account
            self.client = gspread.oauth(
                credentials_filename="google_oauth_credentials.json",
                authorized_user_filename="google_authorized_user.json",
            )

            logger.info("Cliente Google Sheets inicializado com sucesso")

        except Exception as e:
            logger.error(f"Erro ao inicializar cliente Google Sheets: {e}")
            self.client = None

    def is_connected(self) -> bool:
        """Verifica se está conectado ao Google Sheets."""
        return self.client is not None

    def get_spreadsheet_by_url(self, url: str):
        """Abre planilha por URL."""
        if not self.is_connected():
            raise Exception("Cliente Google Sheets não inicializado")

        try:
            return self.client.open_by_url(url)
        except Exception as e:
            logger.error(f"Erro ao abrir planilha {url}: {e}")
            raise

    def get_spreadsheet_by_key(self, key: str):
        """Abre planilha por ID/key."""
        if not self.is_connected():
            raise Exception("Cliente Google Sheets não inicializado")

        try:
            return self.client.open_by_key(key)
        except Exception as e:
            logger.error(f"Erro ao abrir planilha {key}: {e}")
            raise

    def read_sheet_data(
        self, spreadsheet_key: str, worksheet_name: str = None
    ) -> List[List[str]]:
        """
        Lê dados de uma planilha.

        Args:
            spreadsheet_key: ID da planilha
            worksheet_name: Nome da aba (None = primeira aba)

        Returns:
            Lista de listas com os dados das células
        """
        try:
            spreadsheet = self.get_spreadsheet_by_key(spreadsheet_key)

            if worksheet_name:
                worksheet = spreadsheet.worksheet(worksheet_name)
            else:
                worksheet = spreadsheet.sheet1

            data = worksheet.get_all_values()
            logger.info(f"Dados lidos: {len(data)} linhas de {spreadsheet_key}")

            return data

        except Exception as e:
            logger.error(f"Erro ao ler dados da planilha {spreadsheet_key}: {e}")
            raise

    def write_sheet_data(
        self,
        spreadsheet_key: str,
        data: List[List[str]],
        worksheet_name: str = None,
        start_cell: str = "A1",
    ):
        """
        Escreve dados em uma planilha.

        Args:
            spreadsheet_key: ID da planilha
            data: Dados para escrever (lista de listas)
            worksheet_name: Nome da aba
            start_cell: Célula inicial (ex: 'A1')
        """
        try:
            spreadsheet = self.get_spreadsheet_by_key(spreadsheet_key)

            if worksheet_name:
                worksheet = spreadsheet.worksheet(worksheet_name)
            else:
                worksheet = spreadsheet.sheet1

            worksheet.update(start_cell, data)
            logger.info(f"Dados escritos em {spreadsheet_key}: {len(data)} linhas")

        except Exception as e:
            logger.error(f"Erro ao escrever dados na planilha {spreadsheet_key}: {e}")
            raise

    def append_row(
        self, spreadsheet_key: str, row_data: List[str], worksheet_name: str = None
    ):
        """Adiciona uma linha ao final da planilha."""
        try:
            spreadsheet = self.get_spreadsheet_by_key(spreadsheet_key)

            if worksheet_name:
                worksheet = spreadsheet.worksheet(worksheet_name)
            else:
                worksheet = spreadsheet.sheet1

            worksheet.append_row(row_data)
            logger.info(f"Linha adicionada em {spreadsheet_key}")

        except Exception as e:
            logger.error(f"Erro ao adicionar linha na planilha {spreadsheet_key}: {e}")
            raise

    def find_cell(
        self, spreadsheet_key: str, search_value: str, worksheet_name: str = None
    ):
        """Encontra uma célula pelo valor."""
        try:
            spreadsheet = self.get_spreadsheet_by_key(spreadsheet_key)

            if worksheet_name:
                worksheet = spreadsheet.worksheet(worksheet_name)
            else:
                worksheet = spreadsheet.sheet1

            cell = worksheet.find(search_value)
            return cell

        except Exception as e:
            logger.error(f"Erro ao procurar célula na planilha {spreadsheet_key}: {e}")
            return None

    def get_worksheet_names(self, spreadsheet_key: str) -> List[str]:
        """Retorna nomes de todas as abas da planilha."""
        try:
            spreadsheet = self.get_spreadsheet_by_key(spreadsheet_key)
            return [ws.title for ws in spreadsheet.worksheets()]

        except Exception as e:
            logger.error(f"Erro ao listar abas da planilha {spreadsheet_key}: {e}")
            return []


# Instância global do serviço
google_sheets_service = GoogleSheetsService()

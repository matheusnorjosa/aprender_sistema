"""
Google Sheets Service - Integração com gspread
==============================================

Este serviço centraliza toda a lógica de integração com Google Sheets
usando a biblioteca gspread para importação automática de dados.

Autor: Claude Code
Data: Janeiro 2025
"""

import logging
import os
from typing import Dict, List, Optional, Any
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

try:
    import gspread
    from google.oauth2.service_account import Credentials
    from google.oauth2.credentials import Credentials as OAuth2Credentials
except ImportError:
    gspread = None


logger = logging.getLogger(__name__)


class GoogleSheetsService:
    """
    Serviço para integração com Google Sheets via gspread
    
    Funcionalidades:
    - Autenticação via Service Account
    - Importação de dados de planilhas
    - Sincronização bidirecional
    - Cache de conexões
    """
    
    def __init__(self):
        self._client = None
        self._credentials_path = None
        
    def _get_credentials_path(self) -> str:
        """Obtém o caminho das credenciais"""
        # Prioridade: variável de ambiente > service account > oauth
        creds_path = os.getenv('GOOGLE_SHEETS_CREDENTIALS_PATH')
        
        if creds_path and os.path.exists(creds_path):
            return creds_path
            
        # Service Account (preferido)
        service_account_path = os.path.join(settings.BASE_DIR, 'google_service_account.json')
        if os.path.exists(service_account_path):
            return service_account_path
            
        # OAuth credentials (existente no projeto)
        oauth_path = os.path.join(settings.BASE_DIR, 'google_authorized_user.json')
        if os.path.exists(oauth_path):
            return oauth_path
            
        raise ImproperlyConfigured(
            "Google Sheets credentials not found. Available options: "
            "1) Set GOOGLE_SHEETS_CREDENTIALS_PATH, "
            "2) Place google_service_account.json in project root, "
            "3) Use existing google_authorized_user.json"
        )
    
    def _get_client(self) -> gspread.Client:
        """Obtém cliente gspread autenticado"""
        if gspread is None:
            raise ImproperlyConfigured(
                "gspread not installed. Run: pip install gspread"
            )
            
        if self._client is None:
            try:
                creds_path = self._get_credentials_path()
                
                # Detectar tipo de credencial pelo conteúdo do arquivo
                with open(creds_path, 'r') as f:
                    import json
                    creds_data = json.load(f)
                
                if 'type' in creds_data and creds_data['type'] == 'service_account':
                    # Service Account credentials
                    scopes = [
                        'https://www.googleapis.com/auth/spreadsheets',
                        'https://www.googleapis.com/auth/drive.file'
                    ]
                    credentials = Credentials.from_service_account_file(
                        creds_path, scopes=scopes
                    )
                    logger.info("Using Service Account credentials")
                    
                elif 'refresh_token' in creds_data:
                    # OAuth2 credentials
                    credentials = OAuth2Credentials.from_authorized_user_file(creds_path)
                    logger.info("Using OAuth2 user credentials")
                    
                else:
                    raise ImproperlyConfigured(
                        f"Unknown credential format in {creds_path}"
                    )
                
                self._client = gspread.authorize(credentials)
                logger.info("Google Sheets client initialized successfully")
                
            except Exception as e:
                logger.error(f"Failed to initialize Google Sheets client: {e}")
                raise
                
        return self._client
    
    def get_worksheet_data(
        self, 
        spreadsheet_key: str, 
        worksheet_name: str = None,
        worksheet_index: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Obtém dados de uma planilha como lista de dicionários
        
        Args:
            spreadsheet_key: ID da planilha (da URL)
            worksheet_name: Nome da aba (opcional)
            worksheet_index: Índice da aba (padrão: 0)
            
        Returns:
            Lista de dicionários com os dados
        """
        try:
            client = self._get_client()
            spreadsheet = client.open_by_key(spreadsheet_key)
            
            # Selecionar worksheet
            if worksheet_name:
                worksheet = spreadsheet.worksheet(worksheet_name)
            else:
                worksheet = spreadsheet.get_worksheet(worksheet_index)
                
            # Obter todos os registros como dicionários
            records = worksheet.get_all_records()
            
            logger.info(
                f"Retrieved {len(records)} records from {spreadsheet.title} / "
                f"{worksheet.title}"
            )
            
            return records
            
        except Exception as e:
            logger.error(f"Error retrieving worksheet data: {e}")
            raise
    
    def update_worksheet_data(
        self,
        spreadsheet_key: str,
        data: List[Dict[str, Any]],
        worksheet_name: str = None,
        worksheet_index: int = 0,
        clear_first: bool = True
    ) -> bool:
        """
        Atualiza dados em uma planilha
        
        Args:
            spreadsheet_key: ID da planilha
            data: Lista de dicionários com os dados
            worksheet_name: Nome da aba
            worksheet_index: Índice da aba
            clear_first: Se deve limpar a planilha antes
            
        Returns:
            True se sucesso
        """
        try:
            client = self._get_client()
            spreadsheet = client.open_by_key(spreadsheet_key)
            
            if worksheet_name:
                worksheet = spreadsheet.worksheet(worksheet_name)
            else:
                worksheet = spreadsheet.get_worksheet(worksheet_index)
            
            if clear_first:
                worksheet.clear()
            
            if data:
                # Converter para formato de matriz
                headers = list(data[0].keys())
                rows = [headers]
                
                for record in data:
                    row = [str(record.get(header, '')) for header in headers]
                    rows.append(row)
                
                # Atualizar planilha
                worksheet.update(rows, 'A1')
                
                logger.info(
                    f"Updated {len(data)} records in {spreadsheet.title} / "
                    f"{worksheet.title}"
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating worksheet data: {e}")
            raise
    
    def create_worksheet(
        self,
        spreadsheet_key: str,
        worksheet_name: str,
        rows: int = 1000,
        cols: int = 26
    ) -> bool:
        """Cria nova aba em planilha existente"""
        try:
            client = self._get_client()
            spreadsheet = client.open_by_key(spreadsheet_key)
            
            worksheet = spreadsheet.add_worksheet(
                title=worksheet_name,
                rows=rows,
                cols=cols
            )
            
            logger.info(f"Created worksheet '{worksheet_name}' in {spreadsheet.title}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating worksheet: {e}")
            raise
    
    def list_spreadsheets(self) -> List[Dict[str, str]]:
        """Lista planilhas acessíveis pelo service account"""
        try:
            client = self._get_client()
            spreadsheets = []
            
            # Listar planilhas (limitado ao que o service account tem acesso)
            for spreadsheet in client.openall():
                spreadsheets.append({
                    'id': spreadsheet.id,
                    'title': spreadsheet.title,
                    'url': spreadsheet.url
                })
            
            logger.info(f"Found {len(spreadsheets)} accessible spreadsheets")
            return spreadsheets
            
        except Exception as e:
            logger.error(f"Error listing spreadsheets: {e}")
            return []
    
    def get_worksheet_range(
        self, 
        spreadsheet_key: str, 
        range_name: str,
        worksheet_name: str = None
    ) -> List[List[str]]:
        """
        Obtém dados de um range específico da planilha
        
        Args:
            spreadsheet_key: ID da planilha (da URL)
            range_name: Range no formato A1 (ex: 'E1:T1260')
            worksheet_name: Nome da aba (opcional)
            
        Returns:
            Lista de listas com os dados do range
        """
        try:
            client = self._get_client()
            spreadsheet = client.open_by_key(spreadsheet_key)
            
            # Selecionar worksheet
            if worksheet_name:
                worksheet = spreadsheet.worksheet(worksheet_name)
            else:
                worksheet = spreadsheet.get_worksheet(0)
            
            # Obter valores do range especificado
            values = worksheet.get(range_name)
            
            logger.info(
                f"Retrieved range {range_name} from {spreadsheet.title} / "
                f"{worksheet.title}: {len(values)} rows"
            )
            
            return values
            
        except Exception as e:
            logger.error(f"Error retrieving range {range_name}: {e}")
            raise

    def get_spreadsheet_info(self, spreadsheet_key: str) -> Dict[str, Any]:
        """Obtém informações sobre uma planilha"""
        try:
            client = self._get_client()
            spreadsheet = client.open_by_key(spreadsheet_key)
            
            worksheets = []
            for ws in spreadsheet.worksheets():
                worksheets.append({
                    'id': ws.id,
                    'title': ws.title,
                    'row_count': ws.row_count,
                    'col_count': ws.col_count
                })
            
            info = {
                'id': spreadsheet.id,
                'title': spreadsheet.title,
                'url': spreadsheet.url,
                'worksheets': worksheets,
                'worksheet_count': len(worksheets)
            }
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting spreadsheet info: {e}")
            raise


# Instância global do serviço
google_sheets_service = GoogleSheetsService()
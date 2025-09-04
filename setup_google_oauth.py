#!/usr/bin/env python
"""
Setup Google OAuth2 para acesso às planilhas e calendar
"""
import json
import os
from pathlib import Path

from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()


def setup_google_credentials():
    """
    Cria arquivo de credenciais OAuth2 para gspread.
    Necessário executar uma vez para autorizar o acesso.
    """

    print("=== SETUP GOOGLE OAUTH2 ===")

    # Credenciais OAuth2 básicas para Google Sheets API
    credentials = {
        "installed": {
            "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
            "project_id": "aprender-sistema",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": "YOUR_CLIENT_SECRET",
            "redirect_uris": ["http://localhost"],
        }
    }

    print("\nATENCAO: Para funcionar completamente, voce precisa:")
    print("1. Criar projeto no Google Cloud Console")
    print("2. Ativar Google Sheets API e Google Calendar API")
    print("3. Criar credenciais OAuth2")
    print("4. Baixar arquivo credentials.json")
    print("5. Substituir o arquivo google_oauth_credentials.json")

    # Criar arquivo de exemplo
    credentials_file = Path("google_oauth_credentials.json")
    with open(credentials_file, "w") as f:
        json.dump(credentials, f, indent=2)

    print(f"\nOK Arquivo criado: {credentials_file}")
    print("INFO ATENÇÃO: Este é um arquivo de EXEMPLO!")
    print("   Substitua com suas credenciais reais do Google Cloud.")

    return True


def list_target_spreadsheets():
    """Lista as planilhas configuradas e seus propósitos."""

    print("\n=== PLANILHAS CONFIGURADAS ===")

    spreadsheets = [
        {
            "name": "Disponibilidade 2025",
            "id": os.getenv("GOOGLE_SHEETS_DISPONIBILIDADE_ID"),
            "purpose": "Dados históricos de disponibilidade dos formadores",
        },
        {
            "name": "Planilha de Controle 2025",
            "id": os.getenv("GOOGLE_SHEETS_CONTROLE_ID"),
            "purpose": "Controle de eventos realizados",
        },
        {
            "name": "Acompanhamento de Agenda 2025",
            "id": os.getenv("GOOGLE_SHEETS_ACOMPANHAMENTO_ID"),
            "purpose": "Acompanhamento detalhado da agenda",
        },
        {
            "name": "Usuários",
            "id": os.getenv("GOOGLE_SHEETS_USUARIOS_ID"),
            "purpose": "Cadastro de usuários do sistema",
        },
    ]

    for sheet in spreadsheets:
        print(f'\nSHEET {sheet["name"]}')
        print(f'   ID: {sheet["id"]}')
        print(f'   Uso: {sheet["purpose"]}')
        print(f'   URL: https://docs.google.com/spreadsheets/d/{sheet["id"]}/edit')

    return spreadsheets


def show_calendar_info():
    """Mostra informações da agenda configurada."""

    print("\n=== GOOGLE CALENDAR CONFIGURADO ===")

    calendar_id = os.getenv("GOOGLE_CALENDAR_ID")
    print(f"CALENDAR Calendar ID: {calendar_id}")
    print("INFO Uso: Criação automática de eventos aprovados")
    print("PERM Permissão necessária: Fazer alterações em eventos")

    return calendar_id


def test_configuration():
    """Testa se a configuração está completa."""

    print("\n=== TESTE DE CONFIGURAÇÃO ===")

    required_vars = [
        "GOOGLE_SERVICE_EMAIL",
        "GOOGLE_SERVICE_PASSWORD",
        "GOOGLE_CALENDAR_ID",
        "GOOGLE_SHEETS_DISPONIBILIDADE_ID",
        "GOOGLE_SHEETS_CONTROLE_ID",
        "GOOGLE_SHEETS_ACOMPANHAMENTO_ID",
        "GOOGLE_SHEETS_USUARIOS_ID",
    ]

    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"OK {var}: Configurado")
        else:
            print(f"X {var}: NÃO configurado")
            missing.append(var)

    if not missing:
        print("\nSUCCESS CONFIGURAÇÃO COMPLETA!")
        print("INFO Próximo passo: Configurar OAuth2 credentials")
        return True
    else:
        print(f"\nWARNING  Faltam {len(missing)} variáveis")
        return False


if __name__ == "__main__":
    setup_google_credentials()
    list_target_spreadsheets()
    show_calendar_info()
    test_configuration()

    print("\n=== PRÓXIMOS PASSOS ===")
    print("1. OK Planilhas e agenda configuradas")
    print("2. PENDING Aguarda OAuth2 credentials do Google Cloud")
    print("3. TEST Teste de conexão com as planilhas")
    print("4. SHEET Extração dos dados históricos 2025")
    print("5. DEPLOY Migração completa para Django")

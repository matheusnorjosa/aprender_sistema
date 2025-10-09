#!/usr/bin/env python
"""
Script de teste para conexão Google Sheets
==========================================

Testa a conexão com Google Sheets usando as credenciais existentes
e lista planilhas acessíveis.

Para usar:
python test_google_connection.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from core.services.google_sheets_service import google_sheets_service


def test_connection():
    """Testa conexão com Google Sheets"""
    print("Testando conexao com Google Sheets...")

    try:
        # Testar inicialização do cliente
        client = google_sheets_service._get_client()
        print("[OK] Cliente Google Sheets inicializado com sucesso!")

        # Listar planilhas acessíveis
        print("\nListando planilhas acessiveis...")
        spreadsheets = google_sheets_service.list_spreadsheets()

        if spreadsheets:
            print(f"[OK] Encontradas {len(spreadsheets)} planilhas:")
            for i, sheet in enumerate(spreadsheets[:10], 1):  # Mostrar apenas 10
                print(f"  {i}. {sheet['title']}")
                print(f"     ID: {sheet['id']}")
                print(f"     URL: {sheet['url']}")
                print()
        else:
            print("[WARN] Nenhuma planilha encontrada ou acessivel")
            print("   Certifique-se de que as planilhas foram compartilhadas com:")
            print("   - Sua conta Google (para OAuth)")
            print("   - O email do Service Account (se usando)")

        return spreadsheets

    except Exception as e:
        print(f"[ERROR] Erro na conexao: {e}")
        print("\nSolucoes possiveis:")
        print("1. Verifique se as credenciais estão corretas")
        print("2. Para OAuth: execute reauthorize_google_calendar.py")
        print("3. Para Service Account: crie google_service_account.json")
        return None


def test_specific_spreadsheet(spreadsheet_id):
    """Testa acesso a uma planilha específica"""
    print(f"\nTestando acesso a planilha: {spreadsheet_id}")

    try:
        info = google_sheets_service.get_spreadsheet_info(spreadsheet_id)
        print(f"[OK] Planilha acessivel: {info['title']}")
        print(f"   Numero de abas: {info['worksheet_count']}")

        for ws in info["worksheets"][:5]:  # Mostrar apenas 5 abas
            print(f"   {ws['title']} ({ws['row_count']}x{ws['col_count']})")

        return info

    except Exception as e:
        print(f"[ERROR] Erro ao acessar planilha: {e}")
        return None


if __name__ == "__main__":
    print("TESTE DE CONEXAO GOOGLE SHEETS - PROJETO APRENDER SISTEMA")
    print("=" * 60)

    # Teste básico de conexão
    spreadsheets = test_connection()

    if spreadsheets:
        print("\n" + "=" * 60)
        print("[OK] CONEXAO GOOGLE SHEETS FUNCIONANDO!")

        # Se encontrou planilhas, testar a primeira
        if len(spreadsheets) > 0:
            first_sheet = spreadsheets[0]
            print(f"\nTestando primeira planilha encontrada...")
            test_specific_spreadsheet(first_sheet["id"])

            print(f"\nPara importar desta planilha, use:")
            print(
                f"python manage.py import_google_sheets --spreadsheet-key={first_sheet['id']}"
            )
    else:
        print("\n" + "=" * 60)
        print("[ERROR] PROBLEMA NA CONEXAO - Verifique credenciais")

    print("\nTeste concluido!")

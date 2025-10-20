#!/usr/bin/env python
"""
Teste simples de importacao sem emojis
"""
import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from core.services.google_sheets_service import google_sheets_service


def test_simple_import():
    """Teste simples de importacao"""
    print("Testando importacao simples...")

    # Testar uma planilha específica - Usuarios
    spreadsheet_key = "1Zj_I7sqYAJ9uaYbVoBfskl0LqxGM3SAFzwm4Zpph1RI"

    try:
        # Obter informações da planilha
        info = google_sheets_service.get_spreadsheet_info(spreadsheet_key)
        print(f"Planilha: {info['title']}")

        # Listar abas
        for ws in info["worksheets"]:
            print(f"  Aba: {ws['title']} ({ws['row_count']}x{ws['col_count']})")

        # Testar primeira aba com dados
        primeira_aba = info["worksheets"][0]["title"]
        print(f"\nTestando aba: {primeira_aba}")

        data = google_sheets_service.get_worksheet_data(spreadsheet_key, primeira_aba)

        print(f"Registros encontrados: {len(data)}")

        if data:
            # Mostrar primeiros campos do primeiro registro
            primeiro = data[0]
            print("Campos do primeiro registro:")
            for key, value in primeiro.items():
                print(f"  {key}: {str(value)[:50]}")

        return True

    except Exception as e:
        print(f"Erro: {e}")
        return False


if __name__ == "__main__":
    test_simple_import()

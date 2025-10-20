#!/usr/bin/env python
"""
Teste simples para verificar acesso à planilha do Google Sheets
"""

import os
import sys

import django

# Configurar Django
sys.path.append(".")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()


def teste_acesso_planilha():
    """Testa acesso à planilha específica"""

    # ID da planilha
    SPREADSHEET_ID = "16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU"

    print("🔍 Testando acesso à planilha do Google Sheets...")
    print(f"📊 ID da planilha: {SPREADSHEET_ID}")

    try:
        # Importar serviço
        from core.services.google_sheets_service import google_sheets_service

        print("✅ Serviço importado com sucesso")

        # Testar conexão básica
        print("\n🔗 Testando conexão...")
        client = google_sheets_service._get_client()
        print("✅ Cliente Google Sheets criado com sucesso")

        # Tentar acessar a planilha
        print(f"\n📋 Tentando acessar planilha {SPREADSHEET_ID}...")
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        print(f"✅ Planilha acessada: {spreadsheet.title}")

        # Listar abas
        print(f"\n📑 Abas disponíveis:")
        for i, worksheet in enumerate(spreadsheet.worksheets()):
            print(
                f"   {i+1}. {worksheet.title} ({worksheet.row_count} linhas, {worksheet.col_count} colunas)"
            )

        # Testar acesso à primeira aba
        if spreadsheet.worksheets():
            first_worksheet = spreadsheet.worksheets()[0]
            print(f"\n🔍 Testando acesso à aba: {first_worksheet.title}")

            # Obter algumas linhas
            try:
                # Obter cabeçalhos (primeira linha)
                headers = first_worksheet.row_values(1)
                print(f"📊 Cabeçalhos encontrados: {headers}")

                # Obter algumas linhas de dados
                if first_worksheet.row_count > 1:
                    sample_data = first_worksheet.get(
                        "A1:Z5"
                    )  # Primeiras 5 linhas, colunas A-Z
                    print(f"📝 Dados de exemplo (primeiras 5 linhas):")
                    for i, row in enumerate(sample_data):
                        print(f"   Linha {i+1}: {row}")

                # Verificar especificamente a coluna B (aprovação)
                print(f"\n🎯 Verificando coluna B (aprovação):")
                col_b_data = first_worksheet.col_values(2)  # Coluna B
                print(f"📊 Coluna B tem {len(col_b_data)} valores")

                # Analisar valores únicos na coluna B
                valores_unicos = set()
                for valor in col_b_data[1:]:  # Pular cabeçalho
                    if valor.strip():
                        valores_unicos.add(valor.strip())

                print(f"📈 Valores únicos na coluna B: {sorted(valores_unicos)}")

                # Contar ocorrências
                contadores = {}
                for valor in col_b_data[1:]:  # Pular cabeçalho
                    if valor.strip():
                        contadores[valor.strip()] = contadores.get(valor.strip(), 0) + 1

                print(f"📊 Contagem na coluna B:")
                for valor, count in sorted(contadores.items()):
                    print(f"   - '{valor}': {count} registros")

            except Exception as e:
                print(f"❌ Erro ao ler dados da aba: {e}")

        print(f"\n✅ Teste concluído com sucesso!")
        return True

    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        print(f"   Tipo do erro: {type(e).__name__}")

        # Verificar se é erro de permissão
        if "403" in str(e) or "permission" in str(e).lower():
            print(f"\n🔐 ERRO DE PERMISSÃO:")
            print(f"   A planilha não está compartilhada com a conta de serviço")
            print(
                f"   Email da conta de serviço: sistema-aprender-service-334@aprender-sistema-calendar.iam.gserviceaccount.com"
            )
            print(f"   Para resolver:")
            print(f"   1. Abra a planilha no Google Sheets")
            print(f"   2. Clique em 'Compartilhar'")
            print(f"   3. Adicione o email acima com permissão de 'Editor'")

        return False


if __name__ == "__main__":
    teste_acesso_planilha()

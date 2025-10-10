#!/usr/bin/env python
"""
Acesso simples à planilha usando gspread com credenciais existentes
"""

import json
import os
import sys

import django

# Configurar Django
sys.path.append(".")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()


def acessar_planilha_simples():
    """Acesso simples à planilha"""

    print("🔧 Tentando acesso simples à planilha...")

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        # Usar as credenciais de service account existentes
        creds_path = "/app/aprender_sistema/tools/service_account.json"

        if not os.path.exists(creds_path):
            print(f"❌ Arquivo de credenciais não encontrado: {creds_path}")
            return False

        print(f"✅ Usando credenciais: {creds_path}")

        # Configurar escopos
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
        ]

        # Criar credenciais
        creds = Credentials.from_service_account_file(creds_path, scopes=scopes)

        # Criar cliente
        client = gspread.authorize(creds)

        # ID da planilha
        SPREADSHEET_ID = "16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU"

        print(f"📊 Tentando acessar planilha: {SPREADSHEET_ID}")

        # Acessar planilha
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        print(f"✅ Planilha acessada: {spreadsheet.title}")

        # Listar abas
        print(f"\n📑 Abas disponíveis:")
        for i, worksheet in enumerate(spreadsheet.worksheets()):
            print(f"   {i+1}. {worksheet.title} ({worksheet.row_count} linhas)")

        # Testar primeira aba
        if spreadsheet.worksheets():
            first_worksheet = spreadsheet.worksheets()[0]
            print(f"\n🔍 Testando aba: {first_worksheet.title}")

            # Obter cabeçalhos
            headers = first_worksheet.row_values(1)
            print(f"📊 Cabeçalhos: {headers}")

            # Verificar coluna B
            print(f"\n🎯 Verificando coluna B (aprovação):")
            col_b_data = first_worksheet.col_values(2)
            print(f"📊 Coluna B tem {len(col_b_data)} valores")

            # Analisar valores únicos
            valores_unicos = set()
            for valor in col_b_data[1:]:  # Pular cabeçalho
                if valor.strip():
                    valores_unicos.add(valor.strip())

            print(f"📈 Valores únicos na coluna B: {sorted(valores_unicos)}")

            # Contar ocorrências
            contadores = {}
            for valor in col_b_data[1:]:
                if valor.strip():
                    contadores[valor.strip()] = contadores.get(valor.strip(), 0) + 1

            print(f"📊 Contagem na coluna B:")
            for valor, count in sorted(contadores.items()):
                print(f"   - '{valor}': {count} registros")

            # Mostrar algumas linhas de exemplo
            print(f"\n📝 Exemplos de dados (primeiras 5 linhas):")
            for i in range(1, min(6, len(col_b_data))):
                if i < len(col_b_data):
                    print(f"   Linha {i}: '{col_b_data[i]}'")

            # Salvar dados para análise
            salvar_dados_planilha(spreadsheet)

        print(f"\n✅ Acesso concluído com sucesso!")
        return True

    except Exception as e:
        print(f"❌ Erro ao acessar planilha: {e}")
        print(f"   Tipo do erro: {type(e).__name__}")

        if "403" in str(e) or "permission" in str(e).lower():
            print(f"\n🔐 ERRO DE PERMISSÃO:")
            print(f"   A planilha não está compartilhada com a conta de serviço")
            print(
                f"   Email da conta: sistema-aprender-service-334@aprender-sistema-calendar.iam.gserviceaccount.com"
            )
            print(f"   Solução: Compartilhar a planilha com este email")

        return False


def salvar_dados_planilha(spreadsheet):
    """Salva dados da planilha para análise"""

    try:
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Salvar dados de cada aba
        for worksheet in spreadsheet.worksheets():
            print(f"\n💾 Salvando dados da aba: {worksheet.title}")

            # Obter todos os dados
            data = worksheet.get_all_records()

            # Salvar como JSON
            filename = (
                f"planilha_{worksheet.title.lower().replace(' ', '_')}_{timestamp}.json"
            )
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"   ✅ Salvo em: {filename}")
            print(f"   📊 Registros: {len(data)}")

        print(f"\n📁 Todos os dados foram salvos com timestamp: {timestamp}")

    except Exception as e:
        print(f"❌ Erro ao salvar dados: {e}")


if __name__ == "__main__":
    acessar_planilha_simples()

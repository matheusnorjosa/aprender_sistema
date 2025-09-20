#!/usr/bin/env python
"""
Script para configurar OAuth2 para acesso ao Google Sheets
"""

import os
import sys
import json
import pickle
from pathlib import Path

# Configurar Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')

def configurar_oauth():
    """Configura OAuth2 para acesso ao Google Sheets"""
    
    print("🔧 Configurando OAuth2 para Google Sheets...")
    
    # Verificar se o arquivo de credenciais existe
    credentials_file = "google_service_account.json"
    if not os.path.exists(credentials_file):
        print(f"❌ Arquivo {credentials_file} não encontrado!")
        print("\n📋 PASSO A PASSO:")
        print("1. Acesse: https://console.cloud.google.com/")
        print("2. Vá para 'APIs e Serviços' > 'Credenciais'")
        print("3. Clique em 'Criar credenciais' > 'ID do cliente OAuth 2.0'")
        print("4. Tipo: 'Aplicação de desktop'")
        print("5. Baixe o arquivo JSON e salve como 'google_oauth_credentials.json'")
        print("6. Execute este script novamente")
        return False
    
    print(f"✅ Arquivo {credentials_file} encontrado")
    
    try:
        # Importar bibliotecas necessárias
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        
        # Escopos necessários
        SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.file'
        ]
        
        # Arquivo para salvar o token
        token_file = 'google_oauth_token.json'
        
        print("🔑 Iniciando fluxo de autenticação...")
        
        # Carregar credenciais
        flow = InstalledAppFlow.from_client_secrets_file(
            credentials_file, SCOPES
        )
        
        # Executar fluxo de autenticação manual
        print("\n🌐 Iniciando fluxo de autenticação manual...")
        print("📝 Instruções:")
        print("   1. Faça login com a conta: aprender-sistema@aprendereditora.com.br")
        print("   2. Autorize o aplicativo")
        print("   3. Copie o código de autorização")
        
        creds = flow.run_local_server(port=8080)
        
        # Salvar credenciais
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
        
        print(f"✅ Credenciais salvas em {token_file}")
        
        # Testar acesso
        print("\n🧪 Testando acesso...")
        testar_acesso_oauth(creds)
        
        return True
        
    except ImportError as e:
        print(f"❌ Biblioteca não encontrada: {e}")
        print("📦 Execute: pip install google-auth-oauthlib")
        return False
        
    except Exception as e:
        print(f"❌ Erro durante configuração: {e}")
        return False

def testar_acesso_oauth(creds):
    """Testa acesso com credenciais OAuth"""
    
    try:
        import gspread
        
        # ID da planilha
        SPREADSHEET_ID = "16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU"
        
        # Criar cliente
        client = gspread.authorize(creds)
        
        # Acessar planilha
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        print(f"✅ Planilha acessada: {spreadsheet.title}")
        
        # Listar abas
        print(f"\n📑 Abas disponíveis:")
        for i, worksheet in enumerate(spreadsheet.worksheets()):
            print(f"   {i+1}. {worksheet.title} ({worksheet.row_count} linhas)")
        
        # Testar acesso à primeira aba
        if spreadsheet.worksheets():
            first_worksheet = spreadsheet.worksheets()[0]
            print(f"\n🔍 Testando aba: {first_worksheet.title}")
            
            # Obter cabeçalhos
            headers = first_worksheet.row_values(1)
            print(f"📊 Cabeçalhos: {headers}")
            
            # Verificar coluna B (aprovação)
            print(f"\n🎯 Verificando coluna B (aprovação):")
            col_b_data = first_worksheet.col_values(2)  # Coluna B
            print(f"📊 Coluna B tem {len(col_b_data)} valores")
            
            # Analisar valores únicos
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
        
        print(f"\n✅ Teste de acesso concluído com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro no teste de acesso: {e}")

if __name__ == "__main__":
    configurar_oauth()

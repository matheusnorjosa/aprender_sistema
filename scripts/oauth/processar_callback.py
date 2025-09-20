#!/usr/bin/env python
"""
Processa callback OAuth2 e finaliza configuração
"""

import os
import sys
import django
from urllib.parse import urlparse, parse_qs
from google_auth_oauthlib.flow import InstalledAppFlow

# Configurar Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
django.setup()

def processar_callback(callback_url):
    """Processa URL de callback e finaliza OAuth2"""
    
    print("🔧 Processando callback OAuth2...")
    
    # Arquivos
    credentials_file = "acesso_planilhas.json"
    token_file = "google_oauth_token.json"
    
    # Escopos
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets.readonly',
        'https://www.googleapis.com/auth/drive.readonly'
    ]
    
    try:
        # Extrair código da URL
        parsed_url = urlparse(callback_url)
        query_params = parse_qs(parsed_url.query)
        
        if 'code' not in query_params:
            print("❌ Código de autorização não encontrado na URL")
            return False
        
        auth_code = query_params['code'][0]
        print(f"✅ Código de autorização extraído")
        
        # Criar flow
        flow = InstalledAppFlow.from_client_secrets_file(
            credentials_file, 
            SCOPES,
            redirect_uri='http://localhost:8080/oauth2callback'
        )
        
        # Trocar código por token
        print("🔄 Trocando código por token...")
        flow.fetch_token(code=auth_code)
        creds = flow.credentials
        
        # Salvar token
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
        print(f"✅ Token salvo em {token_file}")
        
        # Testar acesso
        print(f"\n🔗 Testando acesso...")
        import gspread
        client = gspread.authorize(creds)
        
        SPREADSHEET_ID = "16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU"
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        
        print(f"✅ Acesso bem-sucedido!")
        print(f"📊 Planilha: {spreadsheet.title}")
        print(f"📑 Abas: {len(spreadsheet.worksheets())}")
        
        # Listar abas
        for i, worksheet in enumerate(spreadsheet.worksheets()):
            print(f"   {i+1}. {worksheet.title}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("❌ Uso: python processar_callback.py [URL_CALLBACK]")
        sys.exit(1)
    
    callback_url = sys.argv[1]
    processar_callback(callback_url)

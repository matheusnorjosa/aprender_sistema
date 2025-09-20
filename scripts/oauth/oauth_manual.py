#!/usr/bin/env python
"""
OAuth2 manual - gera URL para copiar e colar
"""

import os
import sys
import django
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Configurar Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
django.setup()

def oauth_manual():
    """OAuth2 manual - gera URL para copiar"""
    
    print("🔧 Configurando OAuth2 manual...")
    
    # Arquivos
    credentials_file = "acesso_planilhas.json"
    token_file = "google_oauth_token.json"
    
    # Escopos
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets.readonly',
        'https://www.googleapis.com/auth/drive.readonly'
    ]
    
    # Verificar arquivo de credenciais
    if not os.path.exists(credentials_file):
        print(f"❌ Arquivo {credentials_file} não encontrado!")
        return False
    
    print(f"✅ Arquivo {credentials_file} encontrado")
    
    # Carregar credenciais
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        print(f"✅ Token existente encontrado")
    
    # Se não há credenciais válidas, fazer login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Renovando token...")
            creds.refresh(Request())
        else:
            print("🔑 Gerando URL de autorização...")
            
            # Criar flow com localhost
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_file, 
                SCOPES,
                redirect_uri='http://localhost:8080/oauth2callback'
            )
            
            # Obter URL de autorização
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                prompt='consent'
            )
            
            print(f"\n🌐 URL DE AUTORIZAÇÃO:")
            print(f"{auth_url}")
            print(f"\n📝 INSTRUÇÕES:")
            print(f"1. Copie a URL acima")
            print(f"2. Abra no navegador")
            print(f"3. Faça login com: aprender-sistema@aprendereditora.com.br")
            print(f"4. Autorize o aplicativo")
            print(f"5. Após autorizar, você será redirecionado para uma página de erro")
            print(f"6. COPIE A URL COMPLETA da página de erro (incluindo o código)")
            print(f"7. Execute: docker exec -it aprender_web python processar_callback.py [URL_COMPLETA]")
            
            return True
        
        # Salvar token
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
        print(f"✅ Token salvo em {token_file}")
    
    # Testar acesso
    print(f"\n🔗 Testando acesso...")
    try:
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
        print(f"❌ Erro no teste: {e}")
        return False

if __name__ == "__main__":
    oauth_manual()

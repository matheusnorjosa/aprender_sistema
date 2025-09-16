"""
Script para completar autenticação Google OAuth2
"""

import os
import json
import sys
import requests
from urllib.parse import urlparse, parse_qs

# Configurações OAuth
CLIENT_ID = "619322948464-esh8d0nrbnbeo9skr2vhr0ev64e1vrto.apps.googleusercontent.com"
CLIENT_SECRET = "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"
REDIRECT_URI = "http://localhost:8081"

def extract_code_from_url(redirect_url):
    """Extrai código de autorização da URL de redirecionamento"""
    parsed_url = urlparse(redirect_url)
    query_params = parse_qs(parsed_url.query)
    
    if 'code' in query_params:
        return query_params['code'][0]
    else:
        print("❌ Código de autorização não encontrado na URL")
        return None

def exchange_code_for_token(auth_code):
    """Troca código de autorização por tokens"""
    try:
        token_url = 'https://oauth2.googleapis.com/token'
        
        data = {
            'code': auth_code,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'redirect_uri': REDIRECT_URI,
            'grant_type': 'authorization_code'
        }
        
        print("🔄 Trocando código por token...")
        response = requests.post(token_url, data=data)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Erro na troca de token: {response.status_code}")
            print(f"Resposta: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return None

def save_credentials(token_data):
    """Salva credenciais no arquivo google_authorized_user.json"""
    try:
        # Formato esperado pelo gspread
        credentials = {
            "refresh_token": token_data.get("refresh_token"),
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "scopes": [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/calendar"
            ],
            "universe_domain": "googleapis.com",
            "account": "",
            "expiry": None  # Será atualizado automaticamente
        }
        
        # Salvar arquivo
        with open('google_authorized_user.json', 'w') as f:
            json.dump(credentials, f, indent=2)
        
        print("✅ Credenciais salvas em google_authorized_user.json")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao salvar credenciais: {e}")
        return False

def main():
    if len(sys.argv) != 2:
        print("❌ Uso: python complete_auth.py 'URL_DE_REDIRECIONAMENTO'")
        print("Exemplo: python complete_auth.py 'http://localhost:8080/?code=4/0AanFRr...'")
        sys.exit(1)
    
    redirect_url = sys.argv[1]
    
    print("🔄 COMPLETANDO AUTENTICAÇÃO GOOGLE OAUTH2")
    print("=" * 50)
    
    # Extrair código
    auth_code = extract_code_from_url(redirect_url)
    if not auth_code:
        sys.exit(1)
    
    print(f"✅ Código extraído: {auth_code[:10]}...")
    
    # Trocar por token
    token_data = exchange_code_for_token(auth_code)
    if not token_data:
        sys.exit(1)
    
    print("✅ Token obtido com sucesso")
    
    # Salvar credenciais
    if save_credentials(token_data):
        print("\n🎉 AUTENTICAÇÃO RENOVADA COM SUCESSO!")
        print("\n📋 PRÓXIMOS PASSOS:")
        print("1. Teste a conexão:")
        print("   python manage.py import_super_colunas_e_t --spreadsheet-key 16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU --dry-run --verbose")
        print("\n2. Se funcionar, execute sem --dry-run para importar os dados reais")
    else:
        print("❌ Falha ao salvar credenciais")
        sys.exit(1)

if __name__ == "__main__":
    main()
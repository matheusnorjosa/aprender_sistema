"""
Script simplificado para renovar autenticação Google OAuth2
"""

import os
import json
import webbrowser
from urllib.parse import urlencode

# Configurações OAuth
CLIENT_ID = "619322948464-esh8d0nrbnbeo9skr2vhr0ev64e1vrto.apps.googleusercontent.com"
CLIENT_SECRET = "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"
REDIRECT_URI = "http://localhost:8081"

# Escopos necessários
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive", 
    "https://www.googleapis.com/auth/calendar"
]

def generate_auth_url():
    """Gera URL de autorização com escopos corretos"""
    params = {
        'response_type': 'code',
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'scope': ' '.join(SCOPES),
        'access_type': 'offline',
        'prompt': 'consent'  # Força novo consentimento
    }
    
    base_url = 'https://accounts.google.com/o/oauth2/v2/auth'
    auth_url = f"{base_url}?{urlencode(params)}"
    return auth_url

def main():
    print("RENOVANDO AUTENTICACAO GOOGLE OAUTH2")
    print("=" * 50)
    
    # Gerar URL de autorização
    auth_url = generate_auth_url()
    
    print("\nINSTRUCOES:")
    print("1. Copie e cole a URL abaixo no seu navegador")
    print("2. Faca login e autorize as permissoes")
    print("3. Voce sera redirecionado para uma pagina que pode dar erro")
    print("4. Copie a URL COMPLETA da pagina de redirecionamento")
    print("5. Execute o proximo script com essa URL")
    
    print(f"\nURL DE AUTORIZACAO:")
    print(auth_url)
    
    print(f"\nPROXIMO PASSO:")
    print("Apos autorizar, execute:")
    print("python complete_auth.py 'URL_DE_REDIRECIONAMENTO_AQUI'")
    
    # Tentar abrir no navegador
    try:
        webbrowser.open(auth_url)
        print("\nNavegador aberto automaticamente")
    except:
        print("\nNavegador nao pode ser aberto automaticamente")
    
    return auth_url

if __name__ == "__main__":
    main()
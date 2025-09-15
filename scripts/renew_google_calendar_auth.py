"""
Script para renovar autenticação do Google Calendar com escopos corretos.
"""

import os
import json
import webbrowser
from urllib.parse import urlencode, urlparse, parse_qs

# Configurações OAuth
CLIENT_ID = "619322948464-esh8d0nrbnbeo9skr2vhr0ev64e1vrto.apps.googleusercontent.com"
CLIENT_SECRET = "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"
REDIRECT_URI = "http://localhost:8080"  # Mudando para porta diferente

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

def exchange_code_for_token(auth_code):
    """Troca código de autorização por tokens"""
    try:
        import requests
        
        token_url = 'https://oauth2.googleapis.com/token'
        
        data = {
            'code': auth_code,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'redirect_uri': REDIRECT_URI,
            'grant_type': 'authorization_code'
        }
        
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        return token_data
        
    except Exception as e:
        print(f"Erro ao trocar código por token: {e}")
        return None

def save_credentials(token_data):
    """Salva credenciais no formato esperado"""
    if not token_data:
        return False
        
    credentials = {
        "refresh_token": token_data.get("refresh_token"),
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scopes": SCOPES,
        "universe_domain": "googleapis.com",
        "account": "",
        "expiry": ""  # Será preenchido automaticamente
    }
    
    # Adicionar token de acesso inicial se disponível
    if "access_token" in token_data:
        credentials["token"] = token_data["access_token"]
    
    try:
        with open("google_authorized_user.json", "w") as f:
            json.dump(credentials, f, indent=2)
        print("OK: Credenciais salvas em google_authorized_user.json")
        return True
    except Exception as e:
        print(f"ERRO: Erro ao salvar credenciais: {e}")
        return False

def main():
    print("=== RENOVAR AUTORIZAÇÃO GOOGLE CALENDAR ===\n")
    
    # Gerar URL de autorização
    auth_url = generate_auth_url()
    
    print("1. Abra o seguinte link no seu navegador:")
    print(f"   {auth_url}\n")
    
    print("2. Faça login e autorize as permissões solicitadas")
    print("3. Você será redirecionado para uma página que pode não carregar")
    print("4. Copie a URL completa da página de redirecionamento")
    print("5. Cole a URL aqui:\n")
    
    # Tentar abrir automaticamente no navegador
    try:
        webbrowser.open(auth_url)
        print("INFO: Navegador aberto automaticamente\n")
    except:
        print("AVISO: Nao foi possivel abrir o navegador automaticamente\n")
    
    # Obter URL de redirecionamento
    redirect_url = input("URL de redirecionamento: ").strip()
    
    if not redirect_url:
        print("ERRO: URL nao fornecida")
        return False
    
    # Extrair código da URL
    try:
        parsed_url = urlparse(redirect_url)
        query_params = parse_qs(parsed_url.query)
        
        if 'code' not in query_params:
            print("ERRO: Codigo de autorizacao nao encontrado na URL")
            return False
            
        auth_code = query_params['code'][0]
        print(f"OK: Codigo extraido: {auth_code[:20]}...")
        
    except Exception as e:
        print(f"ERRO: Erro ao processar URL: {e}")
        return False
    
    # Trocar código por tokens
    print("\nINFO: Trocando codigo por tokens...")
    token_data = exchange_code_for_token(auth_code)
    
    if not token_data:
        print("ERRO: Falha na troca de tokens")
        return False
    
    # Verificar se recebeu refresh_token
    if 'refresh_token' not in token_data:
        print("AVISO: Refresh token nao recebido. Pode ser necessario revogar acesso anterior.")
        print("   Acesse: https://myaccount.google.com/permissions")
        return False
    
    # Salvar credenciais
    if save_credentials(token_data):
        print("\nSUCESSO: Autorizacao renovada com sucesso!")
        print("   Google Calendar agora deve estar acessivel.")
        return True
    else:
        return False

if __name__ == "__main__":
    try:
        success = main()
        if success:
            exit(0)
        else:
            exit(1)
    except KeyboardInterrupt:
        print("\nERRO: Operacao cancelada pelo usuario")
        exit(1)
    except Exception as e:
        print(f"\nERRO: Erro inesperado: {e}")
        exit(1)
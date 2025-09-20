#!/usr/bin/env python3
"""
Script para gerar URL de OAuth2 para acesso manual
"""

import json

def gerar_url_oauth():
    """Gera URL de OAuth2 para autorização manual"""

    # Carregar credenciais
    with open('credentials.json', 'r') as f:
        creds = json.load(f)

    client_config = creds['installed']
    client_id = client_config['client_id']

    # Escopos necessários
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file'
    ]
    scope_string = '%20'.join(scopes)  # URL encode spaces

    # Gerar URL
    auth_url = (
        f"https://accounts.google.com/o/oauth2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri=http://localhost&"
        f"scope={scope_string}&"
        f"response_type=code&"
        f"access_type=offline&"
        f"prompt=consent"
    )

    print("URL DE AUTORIZACAO OAUTH2")
    print("=" * 50)
    print("CONTA A USAR: aprender-sistema@aprendereditora.com.br")
    print("=" * 50)
    print()
    print("1. Acesse esta URL no navegador:")
    print()
    print(auth_url)
    print()
    print("2. Faca login com: aprender-sistema@aprendereditora.com.br")
    print("3. Autorize o acesso")
    print("4. Voce sera redirecionado para uma pagina de erro")
    print("5. Copie o codigo da URL (parametro 'code')")
    print("6. Use o codigo no proximo script")
    print()
    print("=" * 50)

    # Salvar para uso posterior
    with open('oauth_url.txt', 'w') as f:
        f.write(auth_url)

    print("URL salva em: oauth_url.txt")

if __name__ == "__main__":
    gerar_url_oauth()

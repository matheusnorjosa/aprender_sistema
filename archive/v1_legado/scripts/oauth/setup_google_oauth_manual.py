#!/usr/bin/env python3
"""
Script para configurar OAuth2 para Google Sheets manualmente
Gera URL de autorização e permite inserir código manualmente
"""

import json
from urllib.parse import parse_qs, urlparse

import requests


def setup_oauth_manual():
    """Configura OAuth2 manualmente sem browser"""

    # Carregar credenciais
    with open("credentials.json", "r") as f:
        creds = json.load(f)

    client_config = creds["installed"]
    client_id = client_config["client_id"]
    client_secret = client_config["client_secret"]

    # Escopos necessários
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    scope_string = " ".join(scopes)

    # Gerar URL de autorização
    auth_url = (
        f"https://accounts.google.com/o/oauth2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri=http://localhost&"
        f"scope={scope_string}&"
        f"response_type=code&"
        f"access_type=offline&"
        f"prompt=consent"
    )

    print("🔗 URL de Autorização:")
    print(auth_url)
    print("\n📋 Instruções:")
    print("1. Acesse a URL acima no seu navegador")
    print("2. Faça login e autorize o acesso")
    print("3. Você será redirecionado para uma página de erro")
    print("4. Copie o código da URL (parâmetro 'code')")
    print("5. Cole o código aqui")

    # Aguardar código do usuário
    auth_code = input("\n🔑 Cole o código de autorização aqui: ").strip()

    if not auth_code:
        print("❌ Código não fornecido!")
        return False

    print("🔄 Trocando código por token...")

    # Trocar código por token
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": "http://localhost",
    }

    try:
        response = requests.post(token_url, data=token_data)
        response.raise_for_status()

        token_info = response.json()

        # Salvar token
        authorized_user_info = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": token_info.get("refresh_token"),
            "access_token": token_info.get("access_token"),
            "type": "authorized_user",
        }

        with open("token.json", "w") as f:
            json.dump(authorized_user_info, f, indent=2)

        print("✅ Token salvo em token.json")
        print("🎉 Configuração OAuth concluída!")

        return True

    except Exception as e:
        print(f"❌ Erro ao obter token: {e}")
        return False


if __name__ == "__main__":
    setup_oauth_manual()

#!/usr/bin/env python
"""
Gera URL para autorização OAuth2 manual
"""

import json
import base64
import urllib.parse


def gerar_url_oauth():
    """Gera URL de autorização OAuth2"""

    print("🔐 GERADOR DE URL OAUTH2 - GOOGLE SHEETS")
    print("=" * 50)

    # Carregar credenciais
    with open("credentials.json", "r") as f:
        creds = json.load(f)

    client_id = creds["installed"]["client_id"]

    # Parâmetros OAuth2
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": "http://localhost:9090",
        "scope": "https://www.googleapis.com/auth/spreadsheets.readonly",
        "access_type": "offline",
        "prompt": "consent",
    }

    # Gerar URL
    base_url = "https://accounts.google.com/o/oauth2/auth"
    url_params = urllib.parse.urlencode(params)
    auth_url = f"{base_url}?{url_params}"

    print("📋 PASSOS PARA AUTORIZAÇÃO:")
    print("1. Acesse a URL abaixo no seu navegador")
    print("2. Faça login e autorize o acesso")
    print("3. Copie o código da URL de retorno")
    print("4. Execute o próximo script com o código")
    print()
    print("🔗 URL DE AUTORIZAÇÃO:")
    print(auth_url)
    print()
    print("📋 Após autorização, você receberá uma URL como:")
    print("http://localhost:9090/?code=SEU_CODIGO_AQUI&scope=...")
    print("Copie apenas a parte SEU_CODIGO_AQUI")


if __name__ == "__main__":
    gerar_url_oauth()

#!/usr/bin/env python
"""
Reautorização Google OAuth2 para incluir escopo Calendar
"""
import json
from pathlib import Path

from google_auth_oauthlib.flow import Flow


def reauthorize_with_calendar():
    """Reautoriza OAuth2 incluindo escopo Google Calendar"""

    # Carregar credenciais existentes
    cred_path = Path("google_oauth_credentials.json")
    if not cred_path.exists():
        print("Erro: google_oauth_credentials.json não encontrado!")
        return False

    # Scopes necessários
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/calendar",  # NOVO
    ]

    # Criar fluxo OAuth2
    flow = Flow.from_client_secrets_file(
        str(cred_path), scopes=SCOPES, redirect_uri="http://localhost"
    )

    # URL de autorização
    auth_url, _ = flow.authorization_url(prompt="consent")

    print("=== REAUTORIZAÇÃO GOOGLE CALENDAR ===")
    print()
    print("1. Abra este link no navegador:")
    print(auth_url)
    print()
    print("2. Faça login e autorize as permissões")
    print("3. Copie o código de autorização da URL de redirect")
    print("4. Cole o código aqui:")

    # Obter código do usuário
    code = input("Código de autorização: ").strip()

    try:
        # Trocar código por token
        flow.fetch_token(code=code)

        # Salvar credenciais
        creds = flow.credentials
        authorized_path = Path("google_authorized_user.json")

        cred_data = {
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": SCOPES,
            "universe_domain": "googleapis.com",
            "account": "",
            "expiry": creds.expiry.isoformat() if creds.expiry else None,
        }

        with open(authorized_path, "w") as f:
            json.dump(cred_data, f, indent=2)

        print(f"✓ Credenciais salvas em: {authorized_path}")
        print("✓ Google Calendar autorizado!")
        return True

    except Exception as e:
        print(f"✗ Erro na autorização: {e}")
        return False


if __name__ == "__main__":
    success = reauthorize_with_calendar()
    if success:
        print("\n=== TESTE RÁPIDO ===")
        print("Execute para testar:")
        print(
            "python manage.py shell -c \"from core.services.integrations.google_calendar import GoogleCalendarService; print('OK')\""
        )

#!/usr/bin/env python
"""
Teste rápido de Google Calendar sem reautorizar
"""
import json
import os

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def test_calendar():
    """Testa se o token atual funciona com Calendar"""

    oauth_path = "google_authorized_user.json"

    if not os.path.exists(oauth_path):
        print("✗ Arquivo de credenciais não encontrado")
        return False

    try:
        with open(oauth_path, "r") as f:
            cred_info = json.load(f)

        # Tentar usar token existente
        print("Testando credenciais existentes...")

        # Escopos atuais
        scopes = cred_info.get("scopes", [])
        print(f"Escopos atuais: {scopes}")

        # Adicionar calendar scope
        if "https://www.googleapis.com/auth/calendar" not in scopes:
            scopes.append("https://www.googleapis.com/auth/calendar")
            print("Adicionando escopo Calendar...")

        credentials = Credentials.from_authorized_user_info(cred_info, scopes)

        # Tentar construir serviço
        service = build("calendar", "v3", credentials=credentials)

        # Teste simples - listar calendários
        calendar_list = service.calendarList().list(maxResults=3).execute()
        calendars = calendar_list.get("items", [])

        print(f"✓ Calendar API funcionando! Encontrados {len(calendars)} calendários")

        for calendar in calendars:
            print(f"  - {calendar['summary']} (ID: {calendar['id']})")

        return True

    except Exception as e:
        print(f"✗ Erro: {e}")

        if "insufficient authentication scopes" in str(e).lower():
            print("INFO: Necessário reautorizar com escopo Calendar")
        elif "deleted" in str(e).lower():
            print("INFO: Projeto Google foi deletado - credenciais inválidas")

        return False


if __name__ == "__main__":
    success = test_calendar()
    if success:
        print("\n✓ Google Calendar pronto para uso!")
    else:
        print("\n✗ Necessário reconfigurar credenciais Google")

#!/usr/bin/env python
"""
Script para autorizar acesso às planilhas Google Sheets - Execute LOCALMENTE
"""

import json
import os

import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


def autorizar_google_sheets():
    """Autoriza acesso às planilhas Google Sheets"""

    print("🔐 AUTORIZAÇÃO GOOGLE SHEETS - Execute LOCALMENTE")
    print("=" * 60)

    try:
        # Verificar credenciais
        credentials_file = "credentials.json"
        if not os.path.exists(credentials_file):
            print(f"❌ Arquivo {credentials_file} não encontrado")
            return False

        print("✅ Credenciais encontradas")

        # Configurar fluxo OAuth2
        scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
        flow = InstalledAppFlow.from_client_secrets_file(credentials_file, scopes)

        print("🔧 Iniciando autorização OAuth2...")
        print("📋 Um navegador será aberto para autorização...")

        # Executar fluxo (abrirá navegador automaticamente)
        creds = flow.run_local_server(port=8080)

        print("✅ Autorização concluída!")

        # Salvar token
        token_file = "google_oauth_token.json"
        with open(token_file, "w") as token:
            token.write(creds.to_json())

        print(f"💾 Token salvo em: {token_file}")

        # Testar acesso
        print("\n🔗 Testando acesso às planilhas...")

        gc = gspread.authorize(creds)
        print("✅ Conexão estabelecida!")

        # Testar uma planilha
        test_sheet_id = "1Zj_I7sqYAJ9uaYbVoBfskl0LqxGM3SAFzwm4Zpph1RI"
        sheet = gc.open_by_key(test_sheet_id)
        print(f"✅ Teste bem-sucedido: {sheet.title}")

        print("\n🎉 AUTORIZAÇÃO CONCLUÍDA COM SUCESSO!")
        print(f"📄 Copie o arquivo '{token_file}' para o projeto Docker")

        return True

    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    autorizar_google_sheets()

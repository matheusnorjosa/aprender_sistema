#!/usr/bin/env python
"""
Script para configurar OAuth2 para acessar a planilha Google
"""
import json
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Scopes necessários
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def configurar_oauth():
    print("🔧 CONFIGURANDO OAUTH2 PARA GOOGLE SHEETS")
    print("=" * 60)

    credenciais_path = "/app/acesso_planilhas.json"
    token_path = "/app/google_oauth_token.json"

    # Verificar se há credenciais
    if not os.path.exists(credenciais_path):
        print("❌ Arquivo de credenciais não encontrado")
        print("📋 Crie o arquivo 'acesso_planilhas.json' com suas credenciais OAuth2")
        return None

    print("✅ Credenciais encontradas")

    creds = None

    # Verificar se há token salvo
    if os.path.exists(token_path):
        print("✅ Token encontrado, carregando...")
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # Se não há credenciais válidas, fazer login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Token expirado, renovando...")
            creds.refresh(Request())
        else:
            print("🔐 Fazendo login...")
            flow = InstalledAppFlow.from_client_secrets_file(credenciais_path, SCOPES)
            creds = flow.run_local_server(port=8080)

        # Salvar token para uso futuro
        with open(token_path, "w") as token:
            token.write(creds.to_json())
        print("✅ Token salvo com sucesso")

    # Testar acesso à planilha
    try:
        service = build("sheets", "v4", credentials=creds)
        print("✅ Serviço Google Sheets configurado")

        # Testar acesso à planilha
        planilha_id = "1fsCeGUzsNCv0SCiE6mcIvcCHsMbqNeyzANwdU_148Vw"
        aba_gid = "1510755488"

        print(f"📊 Testando acesso à planilha: {planilha_id}")
        print(f"📊 Aba GID: {aba_gid}")

        # Fazer uma requisição de teste
        range_name = f"B3:B10"  # Primeiras linhas da coluna B (nomes)
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=planilha_id, range=range_name)
            .execute()
        )

        values = result.get("values", [])
        print(f"✅ Acesso confirmado! Dados encontrados: {len(values)} linhas")

        if values:
            print("📋 Primeiros nomes encontrados:")
            for i, row in enumerate(values[:5]):
                if row:
                    print(f"  • {row[0]}")

        return service

    except Exception as e:
        print(f"❌ Erro ao acessar planilha: {e}")
        return None


if __name__ == "__main__":
    service = configurar_oauth()
    if service:
        print("\n🎉 Configuração OAuth2 concluída com sucesso!")
        print("✅ Agora você pode extrair dados da planilha")
    else:
        print("\n❌ Falha na configuração OAuth2")

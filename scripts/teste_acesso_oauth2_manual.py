#!/usr/bin/env python
"""
Teste de acesso às planilhas Google Sheets usando OAuth2 - Versão Manual
"""

import os
import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import json


def teste_oauth2_manual():
    """Gera URL para autorização manual OAuth2"""

    print("🔍 CONFIGURAÇÃO OAUTH2 MANUAL - GOOGLE SHEETS")
    print("=" * 60)

    try:
        # Verificar credenciais
        if not os.path.exists("credentials.json"):
            print("❌ Arquivo credentials.json não encontrado")
            return False

        print("✅ Credenciais OAuth2 encontradas")

        # Verificar token existente
        token_file = "google_oauth_token.json"
        if os.path.exists(token_file):
            print("🔍 Token encontrado, testando...")
            try:
                creds = Credentials.from_authorized_user_file(
                    token_file,
                    ["https://www.googleapis.com/auth/spreadsheets.readonly"],
                )
                if creds and creds.valid:
                    print("✅ Token válido! Testando acesso...")
                    return testar_planilhas_com_token(creds)
            except Exception as e:
                print(f"⚠️ Token inválido: {e}")

        # Gerar URL de autorização
        print("\n🔐 AUTORIZAÇÃO NECESSÁRIA")
        print("Siga estas etapas:")

        flow = InstalledAppFlow.from_client_secrets_file(
            "credentials.json",
            ["https://www.googleapis.com/auth/spreadsheets.readonly"],
        )

        # Configurar para redirect manual
        flow.redirect_uri = "http://localhost:9090"

        auth_url, _ = flow.authorization_url(prompt="consent")

        print(f"\n1. 📋 ACESSE esta URL no seu navegador:")
        print(f"   {auth_url}")
        print(f"\n2. ✅ Faça login e autorize o acesso")
        print(f"3. 📋 Copie o código de autorização da URL")
        print(f"4. 🔄 Execute este script novamente com o código")

        # Solicitar código de autorização
        code = input(
            "\n🔑 Cole o código de autorização aqui (ou Enter para sair): "
        ).strip()

        if not code:
            print("❌ Código não fornecido. Execute novamente quando tiver o código.")
            return False

        # Trocar código por token
        print("🔄 Trocando código por token...")
        flow.fetch_token(code=code)

        # Salvar token
        creds = flow.credentials
        with open(token_file, "w") as token:
            token.write(creds.to_json())

        print("✅ Token OAuth2 salvo com sucesso!")

        # Testar acesso
        return testar_planilhas_com_token(creds)

    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback

        traceback.print_exc()
        return False


def testar_planilhas_com_token(creds):
    """Testa acesso às planilhas com token válido"""

    print("\n🔗 TESTANDO ACESSO ÀS PLANILHAS...")

    planilhas = {
        "usuarios": "1Zj_I7sqYAJ9uaYbVoBfskl0LqxGM3SAFzwm4Zpph1RI",
        "controle": "1P6YG3sIAEpiAPIQL9bKBaIznNl3V9VLan9CpVnrEOgA",
        "disponibilidade": "1fsCeGUzsNCv0SCiE6mcIvcCHsMbqNeyzANwdU_148Vw",
        "acompanhamento": "16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU",
    }

    try:
        # Conectar
        gc = gspread.authorize(creds)
        print("✅ Conexão com Google Sheets estabelecida!")

        resultados = {}

        for nome, sheet_id in planilhas.items():
            print(f"\n📋 TESTANDO: {nome.upper()}")

            try:
                sheet = gc.open_by_key(sheet_id)
                print(f"   ✅ Planilha: {sheet.title}")

                worksheets = sheet.worksheets()
                print(f"   📄 Abas: {len(worksheets)}")

                resultados[nome] = {
                    "sucesso": True,
                    "titulo": sheet.title,
                    "abas": [
                        {
                            "nome": ws.title,
                            "linhas": ws.row_count,
                            "colunas": ws.col_count,
                        }
                        for ws in worksheets
                    ],
                }

                # Mostrar estrutura
                for i, ws in enumerate(worksheets[:5]):  # Primeiras 5 abas
                    print(f"      {i+1}. {ws.title} ({ws.row_count}x{ws.col_count})")

            except Exception as e:
                print(f"   ❌ Erro: {e}")
                resultados[nome] = {"sucesso": False, "erro": str(e)}

        # Salvar resultados
        with open("estrutura_planilhas_reais.json", "w", encoding="utf-8") as f:
            json.dump(resultados, f, indent=2, ensure_ascii=False)

        print("\n" + "=" * 60)
        sucessos = sum(1 for r in resultados.values() if r.get("sucesso", False))
        print(f"📊 RESULTADO: {sucessos}/{len(planilhas)} planilhas acessadas")

        if sucessos == len(planilhas):
            print("🎉 SUCESSO TOTAL! Todas as planilhas acessíveis")
            print("📄 Estrutura salva em: estrutura_planilhas_reais.json")
            return True
        else:
            print("⚠️ Alguns acessos falharam")
            return False

    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        return False


if __name__ == "__main__":
    teste_oauth2_manual()

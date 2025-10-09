#!/usr/bin/env python
"""
Teste de acesso às planilhas Google Sheets usando OAuth2
"""

import os
import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import json


def teste_acesso_oauth2():
    """Testa acesso OAuth2 às planilhas Google Sheets"""

    print("🔍 TESTE DE ACESSO ÀS PLANILHAS GOOGLE SHEETS - OAuth2")
    print("=" * 60)

    # URLs das planilhas
    planilhas = {
        "usuarios": "1Zj_I7sqYAJ9uaYbVoBfskl0LqxGM3SAFzwm4Zpph1RI",
        "controle": "1P6YG3sIAEpiAPIQL9bKBaIznNl3V9VLan9CpVnrEOgA",
        "disponibilidade": "1fsCeGUzsNCv0SCiE6mcIvcCHsMbqNeyzANwdU_148Vw",
        "acompanhamento": "16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU",
    }

    try:
        print("🔧 Configurando OAuth2...")

        # Verificar credenciais
        if not os.path.exists("credentials.json"):
            print("❌ Arquivo credentials.json não encontrado")
            return False

        print("✅ Credenciais OAuth2 encontradas")

        # Configurar autorização
        token_file = "google_oauth_token.json"
        creds = None

        if os.path.exists(token_file):
            print("🔍 Token existente encontrado, carregando...")
            try:
                creds = Credentials.from_authorized_user_file(
                    token_file,
                    ["https://www.googleapis.com/auth/spreadsheets.readonly"],
                )
                if creds and creds.valid:
                    print("✅ Token válido!")
                else:
                    print("⚠️ Token expirado, será renovado...")
                    creds = None
            except Exception as e:
                print(f"⚠️ Erro no token: {e}")
                creds = None

        # Se não há credenciais válidas, autorizar
        if not creds or not creds.valid:
            print("🔐 Iniciando autorização OAuth2...")
            print("📋 Um navegador será aberto para autorização...")

            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                ["https://www.googleapis.com/auth/spreadsheets.readonly"],
            )
            creds = flow.run_local_server(port=8080)

            # Salvar token
            with open(token_file, "w") as token:
                token.write(creds.to_json())
            print("✅ Token OAuth2 salvo!")

        # Conectar ao Google Sheets
        print("🔗 Conectando ao Google Sheets...")
        gc = gspread.authorize(creds)
        print("✅ Conexão estabelecida!")

        # Testar acesso a cada planilha
        resultados = {}

        for nome, sheet_id in planilhas.items():
            print(f"\n📋 TESTANDO PLANILHA: {nome.upper()}")
            print(f"   ID: {sheet_id}")

            try:
                # Abrir planilha
                sheet = gc.open_by_key(sheet_id)
                print(f"   ✅ Planilha acessada: {sheet.title}")

                # Listar abas
                worksheets = sheet.worksheets()
                print(f"   📄 Número de abas: {len(worksheets)}")

                resultados[nome] = {
                    "sucesso": True,
                    "titulo": sheet.title,
                    "abas": len(worksheets),
                    "lista_abas": [ws.title for ws in worksheets],
                }

                # Mostrar primeiras abas
                for i, ws in enumerate(worksheets[:3]):
                    print(f"      {i+1}. {ws.title} ({ws.row_count} linhas)")

                    # Tentar ler primeiras linhas
                    try:
                        values = ws.get_all_values()
                        if values:
                            print(
                                f"         📊 Dados: {len(values)} linhas x {len(values[0]) if values[0] else 0} colunas"
                            )
                            if values[0]:
                                print(f"         📋 Headers: {values[0][:3]}...")
                        else:
                            print("         📊 Aba vazia")
                    except Exception as e:
                        print(f"         ⚠️ Erro ao ler dados: {e}")

            except Exception as e:
                print(f"   ❌ Erro ao acessar: {e}")
                resultados[nome] = {"sucesso": False, "erro": str(e)}

        # Resumo final
        print("\n" + "=" * 60)
        print("📊 RESUMO DOS TESTES:")

        sucessos = sum(1 for r in resultados.values() if r.get("sucesso", False))
        total = len(resultados)

        print(f"   ✅ Planilhas acessadas: {sucessos}/{total}")

        if sucessos == total:
            print("🎉 TODOS OS ACESSOS FUNCIONANDO!")
            print("✅ Pronto para extrair dados reais das planilhas")
        else:
            print("⚠️ Alguns acessos falharam - verificar permissões")

        # Salvar resultados
        with open("teste_acesso_resultado.json", "w", encoding="utf-8") as f:
            json.dump(resultados, f, indent=2, ensure_ascii=False)

        print("📄 Resultados salvos em: teste_acesso_resultado.json")

        return sucessos == total

    except Exception as e:
        print(f"❌ ERRO GERAL: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    teste_acesso_oauth2()

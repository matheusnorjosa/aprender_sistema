#!/usr/bin/env python
"""
Processa código OAuth2 e gera token para acesso às planilhas
"""

import json
import requests
from google.oauth2.credentials import Credentials


def processar_codigo_oauth(codigo):
    """Processa código OAuth2 e gera token"""

    print("🔄 PROCESSANDO CÓDIGO OAUTH2...")
    print("=" * 50)

    try:
        # Carregar credenciais
        with open("credentials.json", "r") as f:
            creds_data = json.load(f)["installed"]

        # Parâmetros para trocar código por token
        token_data = {
            "client_id": creds_data["client_id"],
            "client_secret": creds_data["client_secret"],
            "code": codigo,
            "grant_type": "authorization_code",
            "redirect_uri": "http://localhost:9090",
        }

        print("🔗 Trocando código por token...")

        # Fazer requisição para obter token
        response = requests.post("https://oauth2.googleapis.com/token", data=token_data)

        if response.status_code == 200:
            token_info = response.json()
            print("✅ Token obtido com sucesso!")

            # Criar objeto Credentials
            creds = Credentials(
                token=token_info["access_token"],
                refresh_token=token_info.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=creds_data["client_id"],
                client_secret=creds_data["client_secret"],
                scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
            )

            # Salvar token
            token_file = "google_oauth_token.json"
            with open(token_file, "w") as f:
                f.write(creds.to_json())

            print(f"💾 Token salvo em: {token_file}")

            # Testar acesso
            return testar_acesso_planilhas(creds)

        else:
            print(f"❌ Erro ao obter token: {response.status_code}")
            print(f"Resposta: {response.text}")
            return False

    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback

        traceback.print_exc()
        return False


def testar_acesso_planilhas(creds):
    """Testa acesso às planilhas com o token"""

    print("\n🔗 TESTANDO ACESSO ÀS PLANILHAS...")

    try:
        import gspread

        # Conectar
        gc = gspread.authorize(creds)
        print("✅ Conexão com Google Sheets estabelecida!")

        # URLs das planilhas
        planilhas = {
            "usuarios": "1Zj_I7sqYAJ9uaYbVoBfskl0LqxGM3SAFzwm4Zpph1RI",
            "controle": "1P6YG3sIAEpiAPIQL9bKBaIznNl3V9VLan9CpVnrEOgA",
            "disponibilidade": "1fsCeGUzsNCv0SCiE6mcIvcCHsMbqNeyzANwdU_148Vw",
            "acompanhamento": "16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU",
        }

        resultados = {}

        for nome, sheet_id in planilhas.items():
            print(f"\n📋 TESTANDO: {nome.upper()}")

            try:
                sheet = gc.open_by_key(sheet_id)
                print(f"   ✅ Planilha: {sheet.title}")

                worksheets = sheet.worksheets()
                print(f"   📄 Abas: {len(worksheets)}")

                resultados[nome] = {"sucesso": True, "titulo": sheet.title, "abas": []}

                # Analisar cada aba
                for i, ws in enumerate(worksheets):
                    aba_info = {
                        "nome": ws.title,
                        "linhas": ws.row_count,
                        "colunas": ws.col_count,
                        "gid": ws.id,
                    }

                    # Tentar ler algumas linhas para ver conteúdo
                    try:
                        values = ws.get_all_values()
                        if values and len(values) > 0:
                            aba_info["tem_dados"] = True
                            aba_info["linhas_com_dados"] = len(
                                [
                                    row
                                    for row in values
                                    if any(cell.strip() for cell in row)
                                ]
                            )
                            if values[0]:
                                aba_info["headers"] = values[0]
                        else:
                            aba_info["tem_dados"] = False
                    except Exception as e:
                        aba_info["erro_leitura"] = str(e)

                    resultados[nome]["abas"].append(aba_info)

                    print(f"      {i+1}. {ws.title} ({ws.row_count}x{ws.col_count})")

            except Exception as e:
                print(f"   ❌ Erro: {e}")
                resultados[nome] = {"sucesso": False, "erro": str(e)}

        # Salvar análise completa
        with open("analise_planilhas_reais.json", "w", encoding="utf-8") as f:
            json.dump(resultados, f, indent=2, ensure_ascii=False)

        print("\n" + "=" * 60)
        sucessos = sum(1 for r in resultados.values() if r.get("sucesso", False))
        print(f"📊 RESULTADO: {sucessos}/{len(planilhas)} planilhas acessadas")

        if sucessos == len(planilhas):
            print("🎉 SUCESSO TOTAL! Todas as planilhas acessíveis")
            print("📄 Análise completa salva em: analise_planilhas_reais.json")
            return True
        else:
            print("⚠️ Alguns acessos falharam")
            return False

    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        return False


if __name__ == "__main__":
    # Código recebido do usuário
    codigo = "4/0AVGzR1CxfcSP2JSLzDXcKhgMETEsjyDdjxf6Kysn-Do9uHh3tcYDwqCbHY-16qrsjuGoxg"
    processar_codigo_oauth(codigo)

#!/usr/bin/env python
"""
Mapeia estrutura das planilhas Google Sheets de forma rápida
"""

import json

import gspread
from google.oauth2.credentials import Credentials


def mapear_estrutura():
    """Mapeia apenas a estrutura das planilhas (sem ler todos os dados)"""

    print("📊 MAPEAMENTO RÁPIDO DA ESTRUTURA DAS PLANILHAS")
    print("=" * 60)

    try:
        # Carregar token
        with open("google_oauth_token.json", "r") as f:
            token_data = json.load(f)

        creds = Credentials.from_authorized_user_info(token_data)

        # Conectar
        gc = gspread.authorize(creds)
        print("✅ Conexão estabelecida!")

        # URLs das planilhas
        planilhas = {
            "usuarios": "1Zj_I7sqYAJ9uaYbVoBfskl0LqxGM3SAFzwm4Zpph1RI",
            "controle": "1P6YG3sIAEpiAPIQL9bKBaIznNl3V9VLan9CpVnrEOgA",
            "disponibilidade": "1fsCeGUzsNCv0SCiE6mcIvcCHsMbqNeyzANwdU_148Vw",
            "acompanhamento": "16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU",
        }

        estrutura = {}

        for nome, sheet_id in planilhas.items():
            print(f"\n📋 {nome.upper()}:")

            try:
                sheet = gc.open_by_key(sheet_id)
                print(f"   📊 Título: {sheet.title}")

                worksheets = sheet.worksheets()
                print(f"   📄 Abas: {len(worksheets)}")

                estrutura[nome] = {"titulo": sheet.title, "abas": []}

                for i, ws in enumerate(worksheets):
                    aba_info = {
                        "nome": ws.title,
                        "linhas": ws.row_count,
                        "colunas": ws.col_count,
                        "gid": ws.id,
                    }

                    # Ler apenas cabeçalhos (primeira linha)
                    try:
                        if ws.row_count > 0:
                            headers = ws.row_values(1)
                            aba_info["headers"] = headers[:10]  # Primeiros 10 headers
                            aba_info["total_headers"] = len(headers)
                    except:
                        aba_info["headers"] = []

                    estrutura[nome]["abas"].append(aba_info)

                    print(f"      {i+1}. {ws.title} ({ws.row_count}x{ws.col_count})")
                    if aba_info.get("headers"):
                        print(f"         Headers: {aba_info['headers'][:3]}...")

            except Exception as e:
                print(f"   ❌ Erro: {e}")
                estrutura[nome] = {"erro": str(e)}

        # Salvar estrutura
        with open("estrutura_planilhas_mapeada.json", "w", encoding="utf-8") as f:
            json.dump(estrutura, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Estrutura salva em: estrutura_planilhas_mapeada.json")

        # Resumo
        print("\n📊 RESUMO:")
        for nome, dados in estrutura.items():
            if "erro" not in dados:
                print(f"   {nome}: {dados['titulo']} ({len(dados['abas'])} abas)")
            else:
                print(f"   {nome}: ERRO - {dados['erro']}")

        return True

    except Exception as e:
        print(f"❌ ERRO: {e}")
        return False


if __name__ == "__main__":
    mapear_estrutura()

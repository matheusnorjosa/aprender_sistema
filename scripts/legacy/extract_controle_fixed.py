#!/usr/bin/env python
"""
Extração da planilha Controle 2025 com tratamento de Unicode
"""
import json
import os
import unicodedata
from datetime import datetime

import gspread
from dotenv import load_dotenv

load_dotenv()


def clean_unicode_text(text):
    """Remove ou substitui caracteres Unicode problemáticos"""
    if not isinstance(text, str):
        return text

    # Substituir emojis comuns por texto
    replacements = {
        "\U0001f7e5": "[LARANJA]",  # Quadrado laranja
        "\U0001f7e6": "[AZUL]",  # Quadrado azul
        "\U0001f7e7": "[ROXO]",  # Quadrado roxo
        "\U0001f7e8": "[AMARELO]",  # Quadrado amarelo
        "\U0001f7e9": "[VERDE]",  # Quadrado verde
        "\U0001f7ea": "[VERMELHO]",  # Quadrado vermelho
        "\u2705": "[OK]",  # Check mark
        "\u274c": "[X]",  # Cross mark
        "\U0001f680": "PROXIMOS",  # Foguete
        "\U0001f525": "IMPORTANTE",  # Fogo
    }

    for unicode_char, replacement in replacements.items():
        text = text.replace(unicode_char, replacement)

    # Normalizar outros caracteres Unicode
    try:
        # Tentar normalizar para ASCII
        text = unicodedata.normalize("NFKD", text)
        text = text.encode("ascii", "ignore").decode("ascii")
    except:
        # Se falhar, manter texto original limpo
        pass

    return text


def extract_controle_data():
    """Extrai dados da planilha Controle 2025 com tratamento Unicode"""

    print("=== EXTRAÇÃO PLANILHA CONTROLE 2025 (UNICODE FIXED) ===")

    try:
        # Conectar com gspread
        gc = gspread.oauth(
            credentials_filename="google_oauth_credentials.json",
            authorized_user_filename="google_authorized_user.json",
        )

        # Abrir planilha Controle 2025
        controle_id = os.getenv("GOOGLE_SHEETS_CONTROLE_ID")
        sheet = gc.open_by_key(controle_id)

        print(f"OK Planilha aberta: {sheet.title}")

        # Extrair dados de todas as abas
        worksheets_data = {}

        for worksheet in sheet.worksheets():
            print(f"Processando aba: {worksheet.title}")

            try:
                # Obter todos os dados da aba
                raw_data = worksheet.get_all_values()

                # Limpar dados Unicode
                clean_data = []
                for row in raw_data:
                    clean_row = [clean_unicode_text(cell) for cell in row]
                    clean_data.append(clean_row)

                worksheets_data[worksheet.title] = {
                    "headers": clean_data[0] if clean_data else [],
                    "data": clean_data[1:] if len(clean_data) > 1 else [],
                    "total_rows": len(clean_data),
                    "total_cols": len(clean_data[0]) if clean_data else 0,
                }

                print(
                    f"  OK Linhas: {len(clean_data)}, Colunas: {len(clean_data[0]) if clean_data else 0}"
                )

            except Exception as e:
                print(f"  ERRO na aba {worksheet.title}: {str(e)[:50]}...")
                worksheets_data[worksheet.title] = {
                    "headers": [],
                    "data": [],
                    "total_rows": 0,
                    "total_cols": 0,
                    "error": str(e),
                }

        # Salvar dados extraídos
        dados_controle = {
            "planilha_nome": sheet.title,
            "planilha_id": controle_id,
            "data_extracao": datetime.now().isoformat(),
            "total_abas": len(sheet.worksheets()),
            "worksheets": worksheets_data,
            "unicode_cleaning": "applied",
        }

        # Salvar em arquivo
        with open("extracted_controle.json", "w", encoding="utf-8") as f:
            json.dump(dados_controle, f, indent=2, ensure_ascii=False)

        print(f"SUCCESS Dados salvos em: extracted_controle.json")

        # Resumo da extração
        total_records = sum(
            aba_data["total_rows"] for aba_data in worksheets_data.values()
        )
        print(f"SUCCESS Total de registros extraídos: {total_records}")

        return dados_controle

    except Exception as e:
        print(f"ERRO geral na extração: {e}")
        return None


def analyze_controle_data():
    """Analisa os dados extraídos da planilha Controle"""

    print("\n=== ANÁLISE CONTROLE 2025 ===")

    try:
        with open("extracted_controle.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        print(f'Planilha: {data["planilha_nome"]}')
        print(f'Total de abas: {data["total_abas"]}')
        print(f'Limpeza Unicode aplicada: {data.get("unicode_cleaning", "não")}')

        for aba_nome, aba_data in data["worksheets"].items():
            print(f"\n--- ABA: {aba_nome} ---")
            print(f'Dimensões: {aba_data["total_rows"]} x {aba_data["total_cols"]}')

            if aba_data.get("error"):
                print(f'ERRO: {aba_data["error"]}')
                continue

            headers = aba_data["headers"]
            if headers:
                print(f"Primeiros campos: {headers[:5]}...")

            if aba_data["data"] and len(aba_data["data"]) > 0:
                primeira_linha = aba_data["data"][0]
                print(f"Primeira linha: {primeira_linha[:3]}...")

                # Análise específica por aba importante
                if "solicit" in aba_nome.lower() and len(aba_data["data"]) > 0:
                    print(f'ANÁLISE SOLICITAÇÕES: {len(aba_data["data"])} registros')

                elif "aprovac" in aba_nome.lower() and len(aba_data["data"]) > 0:
                    print(f'ANÁLISE APROVAÇÕES: {len(aba_data["data"])} registros')

                elif "evento" in aba_nome.lower() and len(aba_data["data"]) > 0:
                    print(f'ANÁLISE EVENTOS: {len(aba_data["data"])} registros')

        print("\nSUCESS Extração da planilha Controle 2025 concluída com sucesso!")

    except Exception as e:
        print(f"Erro na análise: {e}")


if __name__ == "__main__":
    dados = extract_controle_data()

    if dados:
        analyze_controle_data()

        print("\nPROXIMO PASSO: Consolidar todos os 4 arquivos JSON")
        print("- extracted_usuarios.json")
        print("- extracted_disponibilidade.json")
        print("- extracted_controle.json (NOVO)")
        print("- extracted_acompanhamento.json")
    else:
        print("\nFALHA na extração da planilha Controle")

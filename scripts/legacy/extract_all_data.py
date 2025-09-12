#!/usr/bin/env python
"""
Extração completa de dados de todas as planilhas
"""
import json
import os
from datetime import datetime

import gspread
from dotenv import load_dotenv

load_dotenv()


def extract_all_spreadsheet_data():
    """Extrai dados de todas as planilhas configuradas"""

    print("=== EXTRAÇÃO COMPLETA DE DADOS ===")

    # Conectar com gspread
    gc = gspread.oauth(
        credentials_filename="google_oauth_credentials.json",
        authorized_user_filename="google_authorized_user.json",
    )

    # Definir planilhas para extração
    planilhas = {
        "usuarios": {
            "id": os.getenv("GOOGLE_SHEETS_USUARIOS_ID"),
            "nome": "Usuários",
            "arquivo": "extracted_usuarios.json",
        },
        "disponibilidade": {
            "id": os.getenv("GOOGLE_SHEETS_DISPONIBILIDADE_ID"),
            "nome": "Disponibilidade 2025",
            "arquivo": "extracted_disponibilidade.json",
        },
        "controle": {
            "id": os.getenv("GOOGLE_SHEETS_CONTROLE_ID"),
            "nome": "Controle 2025",
            "arquivo": "extracted_controle.json",
        },
        "acompanhamento": {
            "id": os.getenv("GOOGLE_SHEETS_ACOMPANHAMENTO_ID"),
            "nome": "Acompanhamento 2025",
            "arquivo": "extracted_acompanhamento.json",
        },
    }

    dados_extraidos = {}

    for key, info in planilhas.items():
        print(f'\n--- Extraindo {info["nome"]} ---')

        try:
            # Abrir planilha
            sheet = gc.open_by_key(info["id"])
            print(f"Planilha aberta: {sheet.title}")

            # Extrair dados de todas as abas
            worksheets_data = {}

            for worksheet in sheet.worksheets():
                print(f"Processando aba: {worksheet.title}")

                # Obter todos os dados da aba
                data = worksheet.get_all_values()

                worksheets_data[worksheet.title] = {
                    "headers": data[0] if data else [],
                    "data": data[1:] if len(data) > 1 else [],
                    "total_rows": len(data),
                    "total_cols": len(data[0]) if data else 0,
                }

                print(f"  Linhas: {len(data)}, Colunas: {len(data[0]) if data else 0}")

            # Salvar dados extraídos
            dados_extraidos[key] = {
                "planilha_nome": sheet.title,
                "planilha_id": info["id"],
                "data_extracao": datetime.now().isoformat(),
                "total_abas": len(sheet.worksheets()),
                "worksheets": worksheets_data,
            }

            # Salvar em arquivo individual
            with open(info["arquivo"], "w", encoding="utf-8") as f:
                json.dump(dados_extraidos[key], f, indent=2, ensure_ascii=False)

            print(f'Dados salvos em: {info["arquivo"]}')

        except Exception as e:
            print(f'ERRO ao extrair {info["nome"]}: {e}')

    # Salvar todos os dados em um arquivo consolidado
    with open("extracted_all_data.json", "w", encoding="utf-8") as f:
        json.dump(dados_extraidos, f, indent=2, ensure_ascii=False)

    print(f"\n=== EXTRAÇÃO CONCLUÍDA ===")
    print(f"Total de planilhas processadas: {len(dados_extraidos)}")
    print("Arquivos gerados:")
    for key, info in planilhas.items():
        if key in dados_extraidos:
            print(f'- {info["arquivo"]}')
    print("- extracted_all_data.json (consolidado)")

    return dados_extraidos


def analyze_data_structure():
    """Analisa a estrutura dos dados extraídos"""

    print("\n=== ANÁLISE DA ESTRUTURA DOS DADOS ===")

    try:
        with open("extracted_all_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        for planilha_key, planilha_data in data.items():
            print(f'\n--- {planilha_data["planilha_nome"]} ---')
            print(f'ID: {planilha_data["planilha_id"]}')
            print(f'Total de abas: {planilha_data["total_abas"]}')

            for aba_nome, aba_data in planilha_data["worksheets"].items():
                print(f"\n  Aba: {aba_nome}")
                print(f'  Linhas: {aba_data["total_rows"]}')
                print(f'  Colunas: {aba_data["total_cols"]}')

                if aba_data["headers"]:
                    print(f'  Cabeçalhos: {aba_data["headers"][:5]}...')  # Primeiros 5

                if aba_data["data"]:
                    print(
                        f'  Primeira linha de dados: {aba_data["data"][0][:3] if aba_data["data"][0] else "Vazia"}...'
                    )

    except Exception as e:
        print(f"Erro na análise: {e}")


if __name__ == "__main__":
    dados = extract_all_spreadsheet_data()
    analyze_data_structure()

    print("\n🚀 PRÓXIMOS PASSOS:")
    print("1. Analisar fórmulas e validações das planilhas")
    print("2. Mapear dados para modelos Django")
    print("3. Implementar migração para o banco de dados")
    print("4. Testar criação de eventos no Google Calendar")

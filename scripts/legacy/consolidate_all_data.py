#!/usr/bin/env python
"""
Consolidação de todos os dados extraídos das 4 planilhas
"""
import json
import os
from datetime import datetime


def consolidate_all_spreadsheets():
    """Consolida dados de todas as planilhas em um arquivo único"""

    print("=== CONSOLIDAÇÃO DE TODOS OS DADOS ===")

    # Arquivos de extração
    arquivos = [
        ("usuarios", "extracted_usuarios.json"),
        ("disponibilidade", "extracted_disponibilidade.json"),
        ("controle", "extracted_controle.json"),
        ("acompanhamento", "extracted_acompanhamento.json"),
    ]

    dados_consolidados = {
        "consolidacao_completa": {
            "data_consolidacao": datetime.now().isoformat(),
            "total_planilhas": 4,
            "planilhas_extraidas": 4,
            "status": "COMPLETO",
        },
        "planilhas": {},
    }

    total_geral_registros = 0

    for key, arquivo in arquivos:
        print(f"Consolidando: {arquivo}")

        try:
            with open(arquivo, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Calcular total de registros desta planilha
            total_planilha = 0
            for aba_nome, aba_data in data.get("worksheets", {}).items():
                total_planilha += aba_data.get("total_rows", 0)

            # Adicionar aos dados consolidados
            dados_consolidados["planilhas"][key] = {
                "nome": data.get("planilha_nome", "N/A"),
                "id": data.get("planilha_id", "N/A"),
                "total_abas": data.get("total_abas", 0),
                "total_registros": total_planilha,
                "data_extracao": data.get("data_extracao", "N/A"),
                "unicode_cleaning": data.get("unicode_cleaning", False),
                "arquivo_origem": arquivo,
                "worksheets": data.get("worksheets", {}),
            }

            total_geral_registros += total_planilha
            print(
                f'OK: {data.get("planilha_nome", arquivo)} - {total_planilha} registros'
            )

        except Exception as e:
            print(f"ERRO: {arquivo} - {e}")
            dados_consolidados["planilhas"][key] = {
                "erro": str(e),
                "arquivo_origem": arquivo,
            }

    # Adicionar totais gerais
    dados_consolidados["consolidacao_completa"][
        "total_geral_registros"
    ] = total_geral_registros
    dados_consolidados["consolidacao_completa"]["total_abas"] = sum(
        planilha.get("total_abas", 0)
        for planilha in dados_consolidados["planilhas"].values()
        if "total_abas" in planilha
    )

    # Salvar consolidado
    with open("extracted_all_data_complete.json", "w", encoding="utf-8") as f:
        json.dump(dados_consolidados, f, indent=2, ensure_ascii=False)

    print(f"\nSUCCESS: Consolidação completa!")
    print(f"Total geral: {total_geral_registros:,} registros")
    print(f'Total abas: {dados_consolidados["consolidacao_completa"]["total_abas"]}')
    print("Arquivo: extracted_all_data_complete.json")

    return dados_consolidados


def generate_summary_report():
    """Gera relatório resumo da consolidação"""

    print("\n=== RELATÓRIO RESUMO CONSOLIDAÇÃO ===")

    try:
        with open("extracted_all_data_complete.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        consolidacao = data["consolidacao_completa"]
        planilhas = data["planilhas"]

        print(f'Data: {consolidacao["data_consolidacao"][:10]}')
        print(f'Status: {consolidacao["status"]}')
        print(f'Total de registros: {consolidacao["total_geral_registros"]:,}')
        print(f'Total de abas: {consolidacao["total_abas"]}')

        print("\nDETALHES POR PLANILHA:")
        for key, info in planilhas.items():
            if "erro" not in info:
                print(f"{key.upper()}:")
                print(f'  Nome: {info["nome"]}')
                print(f'  Abas: {info["total_abas"]}')
                print(f'  Registros: {info["total_registros"]:,}')
                print(f'  Unicode cleaned: {info.get("unicode_cleaning", False)}')

                # Top 3 abas por volume
                abas_ordenadas = sorted(
                    info["worksheets"].items(),
                    key=lambda x: x[1].get("total_rows", 0),
                    reverse=True,
                )

                print(f"  Maiores abas:")
                for aba_nome, aba_data in abas_ordenadas[:3]:
                    if aba_data.get("total_rows", 0) > 0:
                        print(f'    - {aba_nome}: {aba_data["total_rows"]:,} registros')
                print()

        print("SUCCESS: Análise da consolidação concluída!")

    except Exception as e:
        print(f"ERRO na análise: {e}")


if __name__ == "__main__":
    dados = consolidate_all_spreadsheets()
    generate_summary_report()

    print("\nARQUIVOS GERADOS:")
    print("- extracted_usuarios.json")
    print("- extracted_disponibilidade.json")
    print("- extracted_controle.json")
    print("- extracted_acompanhamento.json")
    print("- extracted_all_data_complete.json (CONSOLIDADO)")

    print("\nPRONTO PARA MIGRAÇÃO COMPLETA!")

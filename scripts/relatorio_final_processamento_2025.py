#!/usr/bin/env python3
"""
Relatório Final do Processamento das Planilhas 2025
"""

import json
import os
from datetime import datetime


def gerar_relatorio_final():
    """Gera relatório final com todos os dados processados"""

    relatorio = {
        "titulo": "Relatório Final - Processamento das Planilhas 2025",
        "timestamp": datetime.now().isoformat(),
        "status": "Processamento Concluído",
        "planilhas_processadas": {},
        "resumo_geral": {},
        "problemas_encontrados": [],
    }

    # Verificar arquivos processados
    arquivos = [
        ("agenda_2025_completa.json", "Agenda 2025"),
        ("disponibilidade_2025_data.json", "Disponibilidade 2025"),
        ("controle_2025_data.json", "Controle 2025"),
        ("usuarios_data.json", "Usuários"),
    ]

    total_linhas = 0
    planilhas_sucesso = 0

    for arquivo, nome in arquivos:
        if os.path.exists(f"/app/{arquivo}"):
            try:
                with open(f"/app/{arquivo}", "r", encoding="utf-8") as f:
                    dados = json.load(f)

                relatorio["planilhas_processadas"][nome] = {
                    "status": "✅ Processada com sucesso",
                    "arquivo": arquivo,
                    "timestamp": dados.get("timestamp", "N/A"),
                    "abas": {},
                }

                # Contar linhas por aba
                linhas_planilha = 0
                if "abas" in dados:
                    for aba, info in dados["abas"].items():
                        linhas_aba = info.get("total_linhas", 0)
                        linhas_planilha += linhas_aba
                        relatorio["planilhas_processadas"][nome]["abas"][aba] = {
                            "linhas": linhas_aba,
                            "status": "✅ Processada",
                        }

                relatorio["planilhas_processadas"][nome][
                    "total_linhas"
                ] = linhas_planilha
                total_linhas += linhas_planilha
                planilhas_sucesso += 1

            except Exception as e:
                relatorio["planilhas_processadas"][nome] = {
                    "status": "❌ Erro ao processar",
                    "erro": str(e),
                }
        else:
            relatorio["planilhas_processadas"][nome] = {
                "status": "❌ Arquivo não encontrado",
                "arquivo": arquivo,
            }
            relatorio["problemas_encontrados"].append(
                f"Arquivo {arquivo} não encontrado"
            )

    # Resumo geral
    relatorio["resumo_geral"] = {
        "total_planilhas": len(arquivos),
        "planilhas_processadas": planilhas_sucesso,
        "planilhas_com_erro": len(arquivos) - planilhas_sucesso,
        "total_linhas_processadas": total_linhas,
        "taxa_sucesso": f"{(planilhas_sucesso/len(arquivos)*100):.1f}%",
    }

    # Problemas específicos
    if "Usuários" in relatorio["planilhas_processadas"]:
        if (
            relatorio["planilhas_processadas"]["Usuários"]["status"]
            != "✅ Processada com sucesso"
        ):
            relatorio["problemas_encontrados"].append(
                "Planilha de Usuários: Erro 404 - ID incorreto ou não compartilhada"
            )

    # Salvar relatório
    with open(
        "/app/relatorio_final_processamento_2025.json", "w", encoding="utf-8"
    ) as f:
        json.dump(relatorio, f, ensure_ascii=False, indent=2)

    # Imprimir resumo
    print("🎯 RELATÓRIO FINAL - PROCESSAMENTO DAS PLANILHAS 2025")
    print("=" * 60)
    print(f'📊 Total de planilhas: {relatorio["resumo_geral"]["total_planilhas"]}')
    print(
        f'✅ Processadas com sucesso: {relatorio["resumo_geral"]["planilhas_processadas"]}'
    )
    print(f'❌ Com erro: {relatorio["resumo_geral"]["planilhas_com_erro"]}')
    print(f'📈 Taxa de sucesso: {relatorio["resumo_geral"]["taxa_sucesso"]}')
    print(
        f'📝 Total de linhas processadas: {relatorio["resumo_geral"].get("total_linhas", 0):,}'
    )
    print()

    print("📋 DETALHES POR PLANILHA:")
    for nome, info in relatorio["planilhas_processadas"].items():
        print(f'  {info["status"]} {nome}')
        if "total_linhas" in info:
            print(f'    📊 {info["total_linhas"]:,} linhas totais')
            for aba, aba_info in info.get("abas", {}).items():
                print(f'      - {aba}: {aba_info["linhas"]:,} linhas')
        print()

    if relatorio["problemas_encontrados"]:
        print("⚠️ PROBLEMAS ENCONTRADOS:")
        for problema in relatorio["problemas_encontrados"]:
            print(f"  - {problema}")
        print()

    print("📁 Relatório salvo em: relatorio_final_processamento_2025.json")

    return relatorio


if __name__ == "__main__":
    gerar_relatorio_final()

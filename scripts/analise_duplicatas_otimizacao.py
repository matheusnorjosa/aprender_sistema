#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import hashlib
from datetime import datetime
from pathlib import Path
import difflib


def calcular_hash_arquivo(caminho_arquivo):
    """Calcula hash MD5 de um arquivo"""
    try:
        with open(caminho_arquivo, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception as e:
        return f"ERRO: {e}"


def analisar_conteudo_arquivo(caminho_arquivo):
    """Analisa o conteúdo de um arquivo Python"""
    try:
        with open(caminho_arquivo, "r", encoding="utf-8") as f:
            conteudo = f.read()

        # Extrair informações básicas
        linhas = conteudo.split("\n")
        total_linhas = len(linhas)
        linhas_codigo = len(
            [l for l in linhas if l.strip() and not l.strip().startswith("#")]
        )
        linhas_comentarios = len([l for l in linhas if l.strip().startswith("#")])

        # Extrair imports
        imports = [
            l.strip() for l in linhas if l.strip().startswith(("import ", "from "))
        ]

        # Extrair funções
        funcoes = [l.strip() for l in linhas if l.strip().startswith("def ")]

        # Extrair classes
        classes = [l.strip() for l in linhas if l.strip().startswith("class ")]

        return {
            "total_linhas": total_linhas,
            "linhas_codigo": linhas_codigo,
            "linhas_comentarios": linhas_comentarios,
            "imports": imports,
            "funcoes": funcoes,
            "classes": classes,
            "conteudo": conteudo,
        }
    except Exception as e:
        return {"erro": str(e)}


def identificar_duplicatas_exatas(diretorio):
    """Identifica arquivos com conteúdo idêntico"""
    hashes = {}
    duplicatas = []

    for root, dirs, files in os.walk(diretorio):
        for arquivo in files:
            if arquivo.endswith(".py"):
                caminho_completo = os.path.join(root, arquivo)
                hash_arquivo = calcular_hash_arquivo(caminho_completo)

                if hash_arquivo in hashes:
                    duplicatas.append(
                        {
                            "hash": hash_arquivo,
                            "arquivo1": hashes[hash_arquivo],
                            "arquivo2": caminho_completo,
                        }
                    )
                else:
                    hashes[hash_arquivo] = caminho_completo

    return duplicatas


def identificar_scripts_similares(diretorio):
    """Identifica scripts com funcionalidades similares"""
    scripts_analisados = {}
    similares = []

    # Analisar todos os scripts Python
    for root, dirs, files in os.walk(diretorio):
        for arquivo in files:
            if arquivo.endswith(".py"):
                caminho_completo = os.path.join(root, arquivo)
                analise = analisar_conteudo_arquivo(caminho_completo)

                if "erro" not in analise:
                    scripts_analisados[caminho_completo] = analise

    # Comparar scripts
    caminhos = list(scripts_analisados.keys())
    for i in range(len(caminhos)):
        for j in range(i + 1, len(caminhos)):
            script1 = caminhos[i]
            script2 = caminhos[j]

            analise1 = scripts_analisados[script1]
            analise2 = scripts_analisados[script2]

            # Calcular similaridade baseada em funções e imports
            funcoes1 = set(analise1["funcoes"])
            funcoes2 = set(analise2["funcoes"])

            imports1 = set(analise1["imports"])
            imports2 = set(analise2["imports"])

            # Calcular similaridade
            similaridade_funcoes = len(funcoes1.intersection(funcoes2)) / max(
                len(funcoes1.union(funcoes2)), 1
            )
            similaridade_imports = len(imports1.intersection(imports2)) / max(
                len(imports1.union(imports2)), 1
            )

            # Se similaridade > 0.7, considerar similar
            if similaridade_funcoes > 0.7 or similaridade_imports > 0.7:
                similares.append(
                    {
                        "script1": script1,
                        "script2": script2,
                        "similaridade_funcoes": similaridade_funcoes,
                        "similaridade_imports": similaridade_imports,
                        "funcoes_comuns": list(funcoes1.intersection(funcoes2)),
                        "imports_comuns": list(imports1.intersection(imports2)),
                    }
                )

    return similares


def identificar_scripts_obsoletos(diretorio):
    """Identifica scripts que podem estar obsoletos"""
    scripts_obsoletos = []

    # Padrões que indicam scripts obsoletos
    padroes_obsoletos = [
        "old_",
        "legacy_",
        "backup_",
        "temp_",
        "test_",
        "debug_",
        "antigo",
        "desatualizado",
        "deprecated",
    ]

    # Nomes que sugerem versões antigas
    nomes_versao = ["v1", "v2", "v3", "old", "new", "final", "corrigido", "atualizado"]

    for root, dirs, files in os.walk(diretorio):
        for arquivo in files:
            if arquivo.endswith(".py"):
                caminho_completo = os.path.join(root, arquivo)
                nome_arquivo = arquivo.lower()

                # Verificar padrões obsoletos
                for padrao in padroes_obsoletos:
                    if padrao in nome_arquivo:
                        scripts_obsoletos.append(
                            {
                                "arquivo": caminho_completo,
                                "motivo": f"Contém padrão obsoleto: {padrao}",
                                "tipo": "padrao_obsoleto",
                            }
                        )
                        break

                # Verificar se há versões mais novas
                for versao in nomes_versao:
                    if versao in nome_arquivo:
                        # Procurar por versões mais novas
                        diretorio_arquivo = os.path.dirname(caminho_completo)
                        arquivos_diretorio = os.listdir(diretorio_arquivo)

                        for outro_arquivo in arquivos_diretorio:
                            if outro_arquivo != arquivo and outro_arquivo.endswith(
                                ".py"
                            ):
                                nome_base = arquivo.replace(versao, "").replace(
                                    ".py", ""
                                )
                                if (
                                    nome_base in outro_arquivo
                                    and "final" in outro_arquivo.lower()
                                ):
                                    scripts_obsoletos.append(
                                        {
                                            "arquivo": caminho_completo,
                                            "motivo": f"Versão mais nova encontrada: {outro_arquivo}",
                                            "tipo": "versao_antiga",
                                            "versao_nova": outro_arquivo,
                                        }
                                    )
                                    break

    return scripts_obsoletos


def analisar_qualidade_codigo(diretorio):
    """Analisa a qualidade dos códigos"""
    problemas_qualidade = []

    for root, dirs, files in os.walk(diretorio):
        for arquivo in files:
            if arquivo.endswith(".py"):
                caminho_completo = os.path.join(root, arquivo)
                analise = analisar_conteudo_arquivo(caminho_completo)

                if "erro" not in analise:
                    problemas = []

                    # Verificar problemas de qualidade
                    if (
                        analise["linhas_comentarios"] == 0
                        and analise["total_linhas"] > 10
                    ):
                        problemas.append("Falta de comentários")

                    if analise["total_linhas"] > 500:
                        problemas.append("Arquivo muito grande (>500 linhas)")

                    if len(analise["funcoes"]) > 20:
                        problemas.append("Muitas funções (>20)")

                    # Verificar imports desnecessários
                    imports_suspeitos = [
                        imp for imp in analise["imports"] if "unused" in imp.lower()
                    ]
                    if imports_suspeitos:
                        problemas.append(f"Imports suspeitos: {imports_suspeitos}")

                    if problemas:
                        problemas_qualidade.append(
                            {
                                "arquivo": caminho_completo,
                                "problemas": problemas,
                                "estatisticas": {
                                    "total_linhas": analise["total_linhas"],
                                    "linhas_codigo": analise["linhas_codigo"],
                                    "linhas_comentarios": analise["linhas_comentarios"],
                                    "num_funcoes": len(analise["funcoes"]),
                                    "num_classes": len(analise["classes"]),
                                },
                            }
                        )

    return problemas_qualidade


def gerar_relatorio_analise():
    """Gera relatório completo da análise"""

    print("🔍 Analisando scripts para duplicatas e otimizações...")

    # Executar análises
    duplicatas_exatas = identificar_duplicatas_exatas("scripts")
    scripts_similares = identificar_scripts_similares("scripts")
    scripts_obsoletos = identificar_scripts_obsoletos("scripts")
    problemas_qualidade = analisar_qualidade_codigo("scripts")

    relatorio = {
        "timestamp": datetime.now().isoformat(),
        "resumo": {
            "duplicatas_exatas": len(duplicatas_exatas),
            "scripts_similares": len(scripts_similares),
            "scripts_obsoletos": len(scripts_obsoletos),
            "problemas_qualidade": len(problemas_qualidade),
        },
        "duplicatas_exatas": duplicatas_exatas,
        "scripts_similares": scripts_similares,
        "scripts_obsoletos": scripts_obsoletos,
        "problemas_qualidade": problemas_qualidade,
        "recomendacoes": {
            "remover": [],
            "consolidar": [],
            "melhorar": [],
            "manter": [],
        },
    }

    # Gerar recomendações
    for duplicata in duplicatas_exatas:
        relatorio["recomendacoes"]["remover"].append(
            {
                "arquivo": duplicata["arquivo2"],
                "motivo": "Duplicata exata",
                "referencia": duplicata["arquivo1"],
            }
        )

    for similar in scripts_similares:
        if similar["similaridade_funcoes"] > 0.8:
            relatorio["recomendacoes"]["consolidar"].append(
                {
                    "scripts": [similar["script1"], similar["script2"]],
                    "motivo": "Alta similaridade de funções",
                    "similaridade": similar["similaridade_funcoes"],
                }
            )

    for obsoleto in scripts_obsoletos:
        relatorio["recomendacoes"]["remover"].append(
            {
                "arquivo": obsoleto["arquivo"],
                "motivo": obsoleto["motivo"],
                "tipo": obsoleto["tipo"],
            }
        )

    for problema in problemas_qualidade:
        relatorio["recomendacoes"]["melhorar"].append(
            {
                "arquivo": problema["arquivo"],
                "problemas": problema["problemas"],
                "estatisticas": problema["estatisticas"],
            }
        )

    # Salvar relatório
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_arquivo = f"relatorio_analise_duplicatas_{timestamp}.json"

    with open(nome_arquivo, "w", encoding="utf-8") as f:
        json.dump(relatorio, f, indent=2, ensure_ascii=False)

    print(f"✅ Relatório salvo em: {nome_arquivo}")

    # Exibir resumo
    print(f"\n📊 RESUMO DA ANÁLISE:")
    print(f"Duplicatas exatas: {relatorio['resumo']['duplicatas_exatas']}")
    print(f"Scripts similares: {relatorio['resumo']['scripts_similares']}")
    print(f"Scripts obsoletos: {relatorio['resumo']['scripts_obsoletos']}")
    print(f"Problemas de qualidade: {relatorio['resumo']['problemas_qualidade']}")

    print(
        f"\n🗑️  ARQUIVOS RECOMENDADOS PARA REMOÇÃO: {len(relatorio['recomendacoes']['remover'])}"
    )
    for item in relatorio["recomendacoes"]["remover"][:10]:
        print(f"  - {item['arquivo']}: {item['motivo']}")

    print(
        f"\n🔄 SCRIPTS PARA CONSOLIDAÇÃO: {len(relatorio['recomendacoes']['consolidar'])}"
    )
    for item in relatorio["recomendacoes"]["consolidar"][:5]:
        print(f"  - {item['scripts'][0]} + {item['scripts'][1]}")

    print(f"\n🔧 SCRIPTS PARA MELHORIA: {len(relatorio['recomendacoes']['melhorar'])}")
    for item in relatorio["recomendacoes"]["melhorar"][:5]:
        print(f"  - {item['arquivo']}: {', '.join(item['problemas'])}")

    return relatorio


if __name__ == "__main__":
    relatorio = gerar_relatorio_analise()

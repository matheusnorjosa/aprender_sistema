#!/usr/bin/env python3
"""
ANÁLISE COMPARATIVA COMPLETA DOS DADOS
Senior Data Analyst Approach - Comparação entre dados extraídos e fonte única
"""

import os
import sys
import json
import pandas as pd
from datetime import datetime
from collections import defaultdict, Counter
import re
from typing import Dict, List, Any, Optional


class DataComparisonAnalyst:
    """
    Classe para análise comparativa completa dos dados
    Abordagem de Senior Data Analyst
    """

    def __init__(self):
        self.dados_originais = {}
        self.dados_fonte_unica = {}
        self.analise_comparativa = {}
        self.discrepancias = []
        self.estatisticas_comparacao = {}

    def carregar_dados_originais(self):
        """Carregar dados das planilhas originais"""

        print("📂 CARREGANDO DADOS ORIGINAIS DAS PLANILHAS")
        print("=" * 60)

        arquivos_originais = {
            "Super": "dados_planilhas_originais/super_colunas_e_t_tratados.json",
            "ACerta": "dados_planilhas_originais/acerta_colunas_e_t_tratados.json",
            "Brincando": "dados_planilhas_originais/brincando_colunas_e_t_tratados.json",
            "Outros": "dados_planilhas_originais/outros_colunas_e_t_tratados.json",
            "Vidas": "dados_planilhas_originais/vidas_colunas_e_t_tratados.json",
        }

        for nome_aba, caminho in arquivos_originais.items():
            if os.path.exists(caminho):
                try:
                    with open(caminho, "r", encoding="utf-8") as f:
                        dados = json.load(f)

                    self.dados_originais[nome_aba] = dados
                    print(f"✅ {nome_aba}: {len(dados)} registros carregados")

                except Exception as e:
                    print(f"❌ Erro ao carregar {nome_aba}: {e}")
            else:
                print(f"❌ Arquivo não encontrado: {caminho}")

        total_original = sum(len(dados) for dados in self.dados_originais.values())
        print(f"\n📊 Total de registros originais: {total_original}")

        return len(self.dados_originais) > 0

    def carregar_dados_fonte_unica(self):
        """Carregar dados da fonte única consolidada"""

        print("\n📂 CARREGANDO DADOS DA FONTE ÚNICA")
        print("=" * 60)

        # Encontrar arquivo mais recente da fonte única
        if os.path.exists("fonte_unica_dados/dados_principais"):
            arquivos = [
                f
                for f in os.listdir("fonte_unica_dados/dados_principais")
                if f.startswith("fonte_unica_dados_") and f.endswith(".json")
            ]

            if arquivos:
                arquivo_mais_recente = max(arquivos)
                caminho_arquivo = (
                    f"fonte_unica_dados/dados_principais/{arquivo_mais_recente}"
                )

                try:
                    with open(caminho_arquivo, "r", encoding="utf-8") as f:
                        self.dados_fonte_unica = json.load(f)

                    print(f"✅ Fonte única carregada: {arquivo_mais_recente}")
                    print(
                        f"   • Total de eventos: {len(self.dados_fonte_unica.get('eventos', []))}"
                    )
                    print(
                        f"   • Municípios: {len(self.dados_fonte_unica.get('municipios', {}))}"
                    )
                    print(
                        f"   • Projetos: {len(self.dados_fonte_unica.get('projetos', {}))}"
                    )
                    print(
                        f"   • Formadores: {len(self.dados_fonte_unica.get('formadores', {}))}"
                    )

                    return True

                except Exception as e:
                    print(f"❌ Erro ao carregar fonte única: {e}")
            else:
                print("❌ Nenhum arquivo da fonte única encontrado")
        else:
            print("❌ Diretório da fonte única não encontrado")

        return False

    def analisar_estrutura_dados_originais(self):
        """Analisar estrutura dos dados originais"""

        print("\n🔍 ANÁLISE DA ESTRUTURA DOS DADOS ORIGINAIS")
        print("=" * 60)

        analise_estrutura = {}

        for nome_aba, dados in self.dados_originais.items():
            if not dados:
                continue

            primeiro_registro = dados[0]
            campos_disponiveis = list(primeiro_registro.keys())

            # Analisar preenchimento de campos
            campos_preenchidos = {}
            valores_unicos = {}

            for campo in campos_disponiveis:
                valores_nao_vazios = [
                    registro.get(campo, "")
                    for registro in dados
                    if registro.get(campo, "")
                ]
                campos_preenchidos[campo] = len(valores_nao_vazios)
                valores_unicos[campo] = len(set(valores_nao_vazios))

            analise_estrutura[nome_aba] = {
                "total_registros": len(dados),
                "campos_disponiveis": campos_disponiveis,
                "campos_preenchidos": campos_preenchidos,
                "valores_unicos": valores_unicos,
                "percentual_preenchimento": {
                    campo: (preenchidos / len(dados)) * 100
                    for campo, preenchidos in campos_preenchidos.items()
                },
            }

            print(f"\n📊 {nome_aba}:")
            print(f"   • Total de registros: {len(dados)}")
            print(f"   • Campos disponíveis: {len(campos_disponiveis)}")

            # Mostrar campos mais importantes
            campos_importantes = ["municipio", "projeto", "tipo_evento", "formadores"]
            for campo in campos_importantes:
                if campo in campos_preenchidos:
                    percentual = analise_estrutura[nome_aba][
                        "percentual_preenchimento"
                    ][campo]
                    print(f"   • {campo}: {percentual:.1f}% preenchido")

        return analise_estrutura

    def extrair_metricas_dados_originais(self):
        """Extrair métricas dos dados originais"""

        print("\n📊 EXTRAINDO MÉTRICAS DOS DADOS ORIGINAIS")
        print("=" * 60)

        metricas = {
            "total_registros": 0,
            "municipios_unicos": set(),
            "projetos_unicos": set(),
            "formadores_unicos": set(),
            "tipos_evento_unicos": set(),
            "distribuicao_por_aba": {},
            "municipios_por_aba": defaultdict(set),
            "projetos_por_aba": defaultdict(set),
            "formadores_por_aba": defaultdict(set),
        }

        for nome_aba, dados in self.dados_originais.items():
            registros_aba = len(dados)
            metricas["total_registros"] += registros_aba
            metricas["distribuicao_por_aba"][nome_aba] = registros_aba

            print(f"\n📊 Processando {nome_aba}: {registros_aba} registros")

            for registro in dados:
                # Municípios
                municipio = registro.get("municipio", "")
                if municipio:
                    metricas["municipios_unicos"].add(municipio)
                    metricas["municipios_por_aba"][nome_aba].add(municipio)

                # Projetos
                projeto = registro.get("projeto", "")
                if projeto:
                    metricas["projetos_unicos"].add(projeto)
                    metricas["projetos_por_aba"][nome_aba].add(projeto)

                # Formadores
                formadores = registro.get("formadores", [])
                if isinstance(formadores, list):
                    for formador in formadores:
                        if formador:
                            metricas["formadores_unicos"].add(formador)
                            metricas["formadores_por_aba"][nome_aba].add(formador)

                # Tipos de evento
                tipo_evento = registro.get("tipo_evento", "")
                if tipo_evento:
                    metricas["tipos_evento_unicos"].add(tipo_evento)

        # Converter sets para listas
        metricas["municipios_unicos"] = list(metricas["municipios_unicos"])
        metricas["projetos_unicos"] = list(metricas["projetos_unicos"])
        metricas["formadores_unicos"] = list(metricas["formadores_unicos"])
        metricas["tipos_evento_unicos"] = list(metricas["tipos_evento_unicos"])

        # Converter defaultdicts
        metricas["municipios_por_aba"] = dict(metricas["municipios_por_aba"])
        metricas["projetos_por_aba"] = dict(metricas["projetos_por_aba"])
        metricas["formadores_por_aba"] = dict(metricas["formadores_por_aba"])

        print(f"\n📊 RESUMO DAS MÉTRICAS ORIGINAIS:")
        print(f"   • Total de registros: {metricas['total_registros']}")
        print(f"   • Municípios únicos: {len(metricas['municipios_unicos'])}")
        print(f"   • Projetos únicos: {len(metricas['projetos_unicos'])}")
        print(f"   • Formadores únicos: {len(metricas['formadores_unicos'])}")
        print(f"   • Tipos de evento únicos: {len(metricas['tipos_evento_unicos'])}")

        return metricas

    def extrair_metricas_fonte_unica(self):
        """Extrair métricas da fonte única"""

        print("\n📊 EXTRAINDO MÉTRICAS DA FONTE ÚNICA")
        print("=" * 60)

        if not self.dados_fonte_unica:
            print("❌ Dados da fonte única não carregados")
            return {}

        eventos = self.dados_fonte_unica.get("eventos", [])
        municipios = self.dados_fonte_unica.get("municipios", {})
        projetos = self.dados_fonte_unica.get("projetos", {})
        formadores = self.dados_fonte_unica.get("formadores", {})
        estatisticas = self.dados_fonte_unica.get("estatisticas", {})

        metricas = {
            "total_registros": len(eventos),
            "municipios_unicos": len(municipios),
            "projetos_unicos": len(projetos),
            "formadores_unicos": len(formadores),
            "tipos_evento_unicos": len(estatisticas.get("tipos_evento_unicos", 0)),
            "distribuicao_por_aba": {},
            "municipios_lista": list(municipios.keys()),
            "projetos_lista": list(projetos.keys()),
            "formadores_lista": list(formadores.keys()),
        }

        # Distribuição por aba
        distribuicao_aba = estatisticas.get("distribuicao_por_aba", {})
        metricas["distribuicao_por_aba"] = distribuicao_aba

        print(f"📊 RESUMO DAS MÉTRICAS DA FONTE ÚNICA:")
        print(f"   • Total de registros: {metricas['total_registros']}")
        print(f"   • Municípios únicos: {metricas['municipios_unicos']}")
        print(f"   • Projetos únicos: {metricas['projetos_unicos']}")
        print(f"   • Formadores únicos: {metricas['formadores_unicos']}")
        print(f"   • Tipos de evento únicos: {metricas['tipos_evento_unicos']}")

        return metricas

    def comparar_metricas(self, metricas_originais, metricas_fonte_unica):
        """Comparar métricas entre dados originais e fonte única"""

        print("\n🔍 COMPARAÇÃO DE MÉTRICAS")
        print("=" * 60)

        comparacao = {
            "total_registros": {
                "original": metricas_originais["total_registros"],
                "fonte_unica": metricas_fonte_unica["total_registros"],
                "diferenca": metricas_fonte_unica["total_registros"]
                - metricas_originais["total_registros"],
                "percentual_diferenca": 0,
            },
            "municipios_unicos": {
                "original": len(metricas_originais["municipios_unicos"]),
                "fonte_unica": metricas_fonte_unica["municipios_unicos"],
                "diferenca": metricas_fonte_unica["municipios_unicos"]
                - len(metricas_originais["municipios_unicos"]),
                "percentual_diferenca": 0,
            },
            "projetos_unicos": {
                "original": len(metricas_originais["projetos_unicos"]),
                "fonte_unica": metricas_fonte_unica["projetos_unicos"],
                "diferenca": metricas_fonte_unica["projetos_unicos"]
                - len(metricas_originais["projetos_unicos"]),
                "percentual_diferenca": 0,
            },
            "formadores_unicos": {
                "original": len(metricas_originais["formadores_unicos"]),
                "fonte_unica": metricas_fonte_unica["formadores_unicos"],
                "diferenca": metricas_fonte_unica["formadores_unicos"]
                - len(metricas_originais["formadores_unicos"]),
                "percentual_diferenca": 0,
            },
        }

        # Calcular percentuais de diferença
        for metrica, dados in comparacao.items():
            if dados["original"] > 0:
                dados["percentual_diferenca"] = (
                    dados["diferenca"] / dados["original"]
                ) * 100

        # Relatório de comparação
        print(f"📊 COMPARAÇÃO DE MÉTRICAS:")
        print(f"   • Total de registros:")
        print(f"     - Original: {comparacao['total_registros']['original']}")
        print(f"     - Fonte única: {comparacao['total_registros']['fonte_unica']}")
        print(
            f"     - Diferença: {comparacao['total_registros']['diferenca']} ({comparacao['total_registros']['percentual_diferenca']:+.1f}%)"
        )

        print(f"   • Municípios únicos:")
        print(f"     - Original: {comparacao['municipios_unicos']['original']}")
        print(f"     - Fonte única: {comparacao['municipios_unicos']['fonte_unica']}")
        print(
            f"     - Diferença: {comparacao['municipios_unicos']['diferenca']} ({comparacao['municipios_unicos']['percentual_diferenca']:+.1f}%)"
        )

        print(f"   • Projetos únicos:")
        print(f"     - Original: {comparacao['projetos_unicos']['original']}")
        print(f"     - Fonte única: {comparacao['projetos_unicos']['fonte_unica']}")
        print(
            f"     - Diferença: {comparacao['projetos_unicos']['diferenca']} ({comparacao['projetos_unicos']['percentual_diferenca']:+.1f}%)"
        )

        print(f"   • Formadores únicos:")
        print(f"     - Original: {comparacao['formadores_unicos']['original']}")
        print(f"     - Fonte única: {comparacao['formadores_unicos']['fonte_unica']}")
        print(
            f"     - Diferença: {comparacao['formadores_unicos']['diferenca']} ({comparacao['formadores_unicos']['percentual_diferenca']:+.1f}%)"
        )

        return comparacao

    def identificar_discrepancias(self, metricas_originais, metricas_fonte_unica):
        """Identificar discrepâncias entre os dados"""

        print("\n🔍 IDENTIFICANDO DISCREPÂNCIAS")
        print("=" * 60)

        discrepancias = []

        # Verificar diferenças nos totais
        if (
            metricas_originais["total_registros"]
            != metricas_fonte_unica["total_registros"]
        ):
            discrepancia = {
                "tipo": "total_registros",
                "descricao": f"Diferença no total de registros: {metricas_originais['total_registros']} vs {metricas_fonte_unica['total_registros']}",
                "severidade": "alta",
                "original": metricas_originais["total_registros"],
                "fonte_unica": metricas_fonte_unica["total_registros"],
            }
            discrepancias.append(discrepancia)

        # Verificar diferenças nos municípios
        municipios_originais = set(metricas_originais["municipios_unicos"])
        municipios_fonte_unica = set(metricas_fonte_unica["municipios_lista"])

        municipios_apenas_original = municipios_originais - municipios_fonte_unica
        municipios_apenas_fonte_unica = municipios_fonte_unica - municipios_originais

        if municipios_apenas_original:
            discrepancia = {
                "tipo": "municipios_perdidos",
                "descricao": f"Municípios presentes apenas nos dados originais: {len(municipios_apenas_original)}",
                "severidade": "media",
                "detalhes": list(municipios_apenas_original),
            }
            discrepancias.append(discrepancia)

        if municipios_apenas_fonte_unica:
            discrepancia = {
                "tipo": "municipios_novos",
                "descricao": f"Municípios presentes apenas na fonte única: {len(municipios_apenas_fonte_unica)}",
                "severidade": "baixa",
                "detalhes": list(municipios_apenas_fonte_unica),
            }
            discrepancias.append(discrepancia)

        # Verificar diferenças nos projetos
        projetos_originais = set(metricas_originais["projetos_unicos"])
        projetos_fonte_unica = set(metricas_fonte_unica["projetos_lista"])

        projetos_apenas_original = projetos_originais - projetos_fonte_unica
        projetos_apenas_fonte_unica = projetos_fonte_unica - projetos_originais

        if projetos_apenas_original:
            discrepancia = {
                "tipo": "projetos_perdidos",
                "descricao": f"Projetos presentes apenas nos dados originais: {len(projetos_apenas_original)}",
                "severidade": "media",
                "detalhes": list(projetos_apenas_original),
            }
            discrepancias.append(discrepancia)

        if projetos_apenas_fonte_unica:
            discrepancia = {
                "tipo": "projetos_novos",
                "descricao": f"Projetos presentes apenas na fonte única: {len(projetos_apenas_fonte_unica)}",
                "severidade": "baixa",
                "detalhes": list(projetos_apenas_fonte_unica),
            }
            discrepancias.append(discrepancia)

        # Relatório de discrepâncias
        print(f"📊 DISCREPÂNCIAS IDENTIFICADAS: {len(discrepancias)}")

        for i, discrepancia in enumerate(discrepancias, 1):
            print(f"\n{i}. {discrepancia['tipo'].upper()}")
            print(f"   • Descrição: {discrepancia['descricao']}")
            print(f"   • Severidade: {discrepancia['severidade']}")

            if "detalhes" in discrepancia and len(discrepancia["detalhes"]) <= 10:
                print(f"   • Detalhes: {', '.join(discrepancia['detalhes'])}")
            elif "detalhes" in discrepancia:
                print(f"   • Detalhes: {len(discrepancia['detalhes'])} itens")

        return discrepancias

    def gerar_relatorio_comparativo(
        self,
        analise_estrutura,
        metricas_originais,
        metricas_fonte_unica,
        comparacao,
        discrepancias,
    ):
        """Gerar relatório comparativo completo"""

        print("\n📋 GERANDO RELATÓRIO COMPARATIVO")
        print("=" * 60)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        relatorio = {
            "metadados": {
                "data_analise": datetime.now().isoformat(),
                "analista": "Senior Data Analyst",
                "versao": "1.0.0",
            },
            "resumo_executivo": {
                "total_registros_original": metricas_originais["total_registros"],
                "total_registros_fonte_unica": metricas_fonte_unica["total_registros"],
                "diferenca_registros": comparacao["total_registros"]["diferenca"],
                "percentual_diferenca": comparacao["total_registros"][
                    "percentual_diferenca"
                ],
                "total_discrepancias": len(discrepancias),
                "discrepancias_alta_severidade": len(
                    [d for d in discrepancias if d["severidade"] == "alta"]
                ),
            },
            "analise_estrutura": analise_estrutura,
            "metricas_originais": metricas_originais,
            "metricas_fonte_unica": metricas_fonte_unica,
            "comparacao": comparacao,
            "discrepancias": discrepancias,
            "conclusoes": self._gerar_conclusoes(comparacao, discrepancias),
        }

        # Salvar relatório
        arquivo_relatorio = f"relatorio_comparativo_analise_{timestamp}.json"
        with open(arquivo_relatorio, "w", encoding="utf-8") as f:
            json.dump(relatorio, f, ensure_ascii=False, indent=2)

        # Gerar relatório em markdown
        arquivo_md = f"relatorio_comparativo_analise_{timestamp}.md"
        self._gerar_relatorio_markdown(relatorio, arquivo_md)

        print(f"✅ Relatório salvo:")
        print(f"   • JSON: {arquivo_relatorio}")
        print(f"   • Markdown: {arquivo_md}")

        return relatorio

    def _gerar_conclusoes(self, comparacao, discrepancias):
        """Gerar conclusões da análise"""

        conclusoes = []

        # Análise de integridade
        if comparacao["total_registros"]["diferenca"] == 0:
            conclusoes.append(
                "✅ INTEGRIDADE: Total de registros mantido - nenhuma perda de dados"
            )
        elif comparacao["total_registros"]["diferenca"] > 0:
            conclusoes.append(
                f"⚠️ INTEGRIDADE: {comparacao['total_registros']['diferenca']} registros adicionados na fonte única"
            )
        else:
            conclusoes.append(
                f"❌ INTEGRIDADE: {abs(comparacao['total_registros']['diferenca'])} registros perdidos na fonte única"
            )

        # Análise de qualidade
        discrepancias_alta = [d for d in discrepancias if d["severidade"] == "alta"]
        if not discrepancias_alta:
            conclusoes.append(
                "✅ QUALIDADE: Nenhuma discrepância de alta severidade identificada"
            )
        else:
            conclusoes.append(
                f"❌ QUALIDADE: {len(discrepancias_alta)} discrepâncias de alta severidade identificadas"
            )

        # Análise de consistência
        if len(discrepancias) <= 2:
            conclusoes.append(
                "✅ CONSISTÊNCIA: Dados altamente consistentes entre origem e fonte única"
            )
        elif len(discrepancias) <= 5:
            conclusoes.append(
                "⚠️ CONSISTÊNCIA: Algumas inconsistências identificadas, mas dentro do aceitável"
            )
        else:
            conclusoes.append(
                "❌ CONSISTÊNCIA: Múltiplas inconsistências identificadas - revisão necessária"
            )

        return conclusoes

    def _gerar_relatorio_markdown(self, relatorio, arquivo):
        """Gerar relatório em formato markdown"""

        with open(arquivo, "w", encoding="utf-8") as f:
            f.write(f"# Relatório Comparativo - Análise de Dados\n\n")
            f.write(f"**Data da Análise:** {relatorio['metadados']['data_analise']}\n")
            f.write(f"**Analista:** {relatorio['metadados']['analista']}\n")
            f.write(f"**Versão:** {relatorio['metadados']['versao']}\n\n")

            f.write(f"## Resumo Executivo\n\n")
            resumo = relatorio["resumo_executivo"]
            f.write(
                f"- **Total de registros originais:** {resumo['total_registros_original']}\n"
            )
            f.write(
                f"- **Total de registros fonte única:** {resumo['total_registros_fonte_unica']}\n"
            )
            f.write(
                f"- **Diferença:** {resumo['diferenca_registros']} ({resumo['percentual_diferenca']:+.1f}%)\n"
            )
            f.write(f"- **Total de discrepâncias:** {resumo['total_discrepancias']}\n")
            f.write(
                f"- **Discrepâncias alta severidade:** {resumo['discrepancias_alta_severidade']}\n\n"
            )

            f.write(f"## Comparação de Métricas\n\n")
            comparacao = relatorio["comparacao"]
            f.write(f"| Métrica | Original | Fonte Única | Diferença | % Diferença |\n")
            f.write(f"|---------|----------|-------------|-----------|-------------|\n")

            for metrica, dados in comparacao.items():
                f.write(
                    f"| {metrica.replace('_', ' ').title()} | {dados['original']} | {dados['fonte_unica']} | {dados['diferenca']:+d} | {dados['percentual_diferenca']:+.1f}% |\n"
                )

            f.write(f"\n## Discrepâncias Identificadas\n\n")
            for i, discrepancia in enumerate(relatorio["discrepancias"], 1):
                f.write(
                    f"### {i}. {discrepancia['tipo'].replace('_', ' ').title()}\n\n"
                )
                f.write(f"- **Descrição:** {discrepancia['descricao']}\n")
                f.write(f"- **Severidade:** {discrepancia['severidade']}\n")
                if "detalhes" in discrepancia:
                    f.write(
                        f"- **Detalhes:** {', '.join(discrepancia['detalhes'][:10])}\n"
                    )
                f.write(f"\n")

            f.write(f"## Conclusões\n\n")
            for conclusao in relatorio["conclusoes"]:
                f.write(f"- {conclusao}\n")

    def executar_analise_completa(self):
        """Executar análise comparativa completa"""

        print("🚀 INICIANDO ANÁLISE COMPARATIVA COMPLETA")
        print("=" * 80)
        print(f"⏰ Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print("👨‍💼 Abordagem de Senior Data Analyst")
        print("=" * 80)

        # 1. Carregar dados originais
        if not self.carregar_dados_originais():
            print("❌ Falha ao carregar dados originais")
            return False

        # 2. Carregar dados da fonte única
        if not self.carregar_dados_fonte_unica():
            print("❌ Falha ao carregar dados da fonte única")
            return False

        # 3. Analisar estrutura dos dados originais
        analise_estrutura = self.analisar_estrutura_dados_originais()

        # 4. Extrair métricas dos dados originais
        metricas_originais = self.extrair_metricas_dados_originais()

        # 5. Extrair métricas da fonte única
        metricas_fonte_unica = self.extrair_metricas_fonte_unica()

        # 6. Comparar métricas
        comparacao = self.comparar_metricas(metricas_originais, metricas_fonte_unica)

        # 7. Identificar discrepâncias
        discrepancias = self.identificar_discrepancias(
            metricas_originais, metricas_fonte_unica
        )

        # 8. Gerar relatório comparativo
        relatorio = self.gerar_relatorio_comparativo(
            analise_estrutura,
            metricas_originais,
            metricas_fonte_unica,
            comparacao,
            discrepancias,
        )

        print(f"\n🎉 ANÁLISE COMPARATIVA CONCLUÍDA COM SUCESSO!")
        print(
            f"   ✅ Dados originais analisados: {metricas_originais['total_registros']} registros"
        )
        print(
            f"   ✅ Dados fonte única analisados: {metricas_fonte_unica['total_registros']} registros"
        )
        print(f"   ✅ Discrepâncias identificadas: {len(discrepancias)}")
        print(f"   ✅ Relatório comparativo gerado")

        return relatorio


def main():
    """Função principal"""

    # Inicializar analista
    analista = DataComparisonAnalyst()

    # Executar análise completa
    relatorio = analista.executar_analise_completa()

    if relatorio:
        print(f"\n📊 RESUMO FINAL:")
        resumo = relatorio["resumo_executivo"]
        print(
            f"   • Integridade dos dados: {resumo['diferenca_registros']:+d} registros"
        )
        print(
            f"   • Qualidade: {resumo['discrepancias_alta_severidade']} discrepâncias críticas"
        )
        print(
            f"   • Consistência: {resumo['total_discrepancias']} discrepâncias totais"
        )

        return analista
    else:
        print(f"\n❌ ANÁLISE FALHOU!")
        return None


if __name__ == "__main__":
    analista = main()

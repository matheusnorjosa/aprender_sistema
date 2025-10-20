#!/usr/bin/env python3
"""
Análise e Cruzamento de Dados das Planilhas
===========================================

Analisa e cruza informações de todas as planilhas mapeadas.

Author: Claude Code
Date: Setembro 2025
"""

import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


def load_latest_data():
    """Carrega os dados mais recentes de cada planilha"""
    print("📂 CARREGANDO DADOS DAS PLANILHAS")
    print("=" * 50)

    data = {}

    # Encontrar arquivos mais recentes
    files = {
        "usuarios": "usuarios_planilha_",
        "controle": "controle_planilha_",
        "agenda": "agenda_planilha_",
        "disponibilidade": "disponibilidade_planilha_",
    }

    for key, prefix in files.items():
        # Encontrar arquivo mais recente
        matching_files = [
            f for f in os.listdir(".") if f.startswith(prefix) and f.endswith(".json")
        ]
        if matching_files:
            latest_file = max(matching_files)
            print(f"📋 {key.upper()}: {latest_file}")

            with open(latest_file, "r", encoding="utf-8") as f:
                data[key] = json.load(f)
        else:
            print(f"❌ {key.upper()}: Nenhum arquivo encontrado")
            data[key] = None

    return data


def analyze_usuarios(data):
    """Analisa dados de usuários"""
    print("\n👥 ANÁLISE DE USUÁRIOS")
    print("=" * 50)

    if not data or "worksheets" not in data:
        print("❌ Dados de usuários não disponíveis")
        return {}

    usuarios_analysis = {
        "total_usuarios": 0,
        "ativos": 0,
        "inativos": 0,
        "pendentes": 0,
        "cargos": Counter(),
        "municipios": Counter(),
        "projetos": Counter(),
    }

    for ws in data["worksheets"]:
        ws_title = ws.get("title", "")
        records = ws.get("records", [])

        print(f"📊 {ws_title}: {len(records)} registros")

        if "Ativos" in ws_title:
            usuarios_analysis["ativos"] = len(records)
        elif "Inativos" in ws_title:
            usuarios_analysis["inativos"] = len(records)
        elif "Pendentes" in ws_title:
            usuarios_analysis["pendentes"] = len(records)

        usuarios_analysis["total_usuarios"] += len(records)

        # Analisar cargos
        for record in records:
            cargo = record.get("Cargo", "") or record.get("cargo", "")
            if cargo:
                usuarios_analysis["cargos"][cargo] += 1

            municipio = record.get("Município", "") or record.get("municipio", "")
            if municipio:
                usuarios_analysis["municipios"][municipio] += 1

            projeto = record.get("Projeto", "") or record.get("projeto", "")
            if projeto:
                usuarios_analysis["projetos"][projeto] += 1

    print(f"📈 Total de usuários: {usuarios_analysis['total_usuarios']}")
    print(f"✅ Ativos: {usuarios_analysis['ativos']}")
    print(f"❌ Inativos: {usuarios_analysis['inativos']}")
    print(f"⏳ Pendentes: {usuarios_analysis['pendentes']}")

    print(f"\n👔 Top 10 Cargos:")
    for cargo, count in usuarios_analysis["cargos"].most_common(10):
        print(f"   {cargo}: {count}")

    print(f"\n🏙️ Top 10 Municípios:")
    for municipio, count in usuarios_analysis["municipios"].most_common(10):
        print(f"   {municipio}: {count}")

    print(f"\n🎯 Top 10 Projetos:")
    for projeto, count in usuarios_analysis["projetos"].most_common(10):
        print(f"   {projeto}: {count}")

    return usuarios_analysis


def analyze_controle(data):
    """Analisa dados de controle"""
    print("\n🎯 ANÁLISE DE CONTROLE")
    print("=" * 50)

    if not data or "worksheets" not in data:
        print("❌ Dados de controle não disponíveis")
        return {}

    controle_analysis = {
        "total_registros": 0,
        "acoes": 0,
        "compras": 0,
        "formacoes": 0,
        "cadastros": 0,
        "municipios": Counter(),
        "projetos": Counter(),
        "coordenadores": Counter(),
    }

    for ws in data["worksheets"]:
        ws_title = ws.get("title", "")
        records = ws.get("records", [])

        print(f"📊 {ws_title}: {len(records)} registros")

        controle_analysis["total_registros"] += len(records)

        if "AÇÕES" in ws_title:
            controle_analysis["acoes"] = len(records)
        elif "COMPRAS" in ws_title:
            controle_analysis["compras"] = len(records)
        elif "FORMAÇÕES" in ws_title:
            controle_analysis["formacoes"] = len(records)
        elif "CADASTROS" in ws_title:
            controle_analysis["cadastros"] += len(records)

        # Analisar dados específicos
        for record in records:
            municipio = record.get("Município", "") or record.get("municipio", "")
            if municipio:
                controle_analysis["municipios"][municipio] += 1

            projeto = record.get("Projeto", "") or record.get("projeto", "")
            if projeto:
                controle_analysis["projetos"][projeto] += 1

            coordenador = record.get("Coordenador", "") or record.get("coordenador", "")
            if coordenador:
                controle_analysis["coordenadores"][coordenador] += 1

    print(f"📈 Total de registros: {controle_analysis['total_registros']}")
    print(f"🎯 Ações: {controle_analysis['acoes']}")
    print(f"🛒 Compras: {controle_analysis['compras']}")
    print(f"📚 Formações: {controle_analysis['formacoes']}")
    print(f"📝 Cadastros: {controle_analysis['cadastros']}")

    print(f"\n🏙️ Top 10 Municípios:")
    for municipio, count in controle_analysis["municipios"].most_common(10):
        print(f"   {municipio}: {count}")

    print(f"\n🎯 Top 10 Projetos:")
    for projeto, count in controle_analysis["projetos"].most_common(10):
        print(f"   {projeto}: {count}")

    print(f"\n👨‍💼 Top 10 Coordenadores:")
    for coordenador, count in controle_analysis["coordenadores"].most_common(10):
        print(f"   {coordenador}: {count}")

    return controle_analysis


def analyze_agenda(data):
    """Analisa dados de agenda"""
    print("\n📅 ANÁLISE DE AGENDA")
    print("=" * 50)

    if not data or "worksheets" not in data:
        print("❌ Dados de agenda não disponíveis")
        return {}

    agenda_analysis = {
        "total_registros": 0,
        "projetos": Counter(),
        "municipios": Counter(),
        "eventos_por_projeto": defaultdict(int),
        "eventos_por_municipio": defaultdict(int),
    }

    for ws in data["worksheets"]:
        ws_title = ws.get("title", "")
        records = ws.get("records", [])

        print(f"📊 {ws_title}: {len(records)} registros")

        agenda_analysis["total_registros"] += len(records)

        # Analisar dados específicos
        for record in records:
            municipio = record.get("município", "") or record.get("Município", "")
            if municipio:
                agenda_analysis["municipios"][municipio] += 1
                agenda_analysis["eventos_por_municipio"][municipio] += 1

            projeto = record.get("projeto", "") or record.get("Projeto", "")
            if projeto:
                agenda_analysis["projetos"][projeto] += 1
                agenda_analysis["eventos_por_projeto"][projeto] += 1

    print(f"📈 Total de registros: {agenda_analysis['total_registros']}")

    print(f"\n🏙️ Top 10 Municípios:")
    for municipio, count in agenda_analysis["municipios"].most_common(10):
        print(f"   {municipio}: {count}")

    print(f"\n🎯 Top 10 Projetos:")
    for projeto, count in agenda_analysis["projetos"].most_common(10):
        print(f"   {projeto}: {count}")

    return agenda_analysis


def analyze_disponibilidade(data):
    """Analisa dados de disponibilidade"""
    print("\n📊 ANÁLISE DE DISPONIBILIDADE")
    print("=" * 50)

    if not data or "worksheets" not in data:
        print("❌ Dados de disponibilidade não disponíveis")
        return {}

    disponibilidade_analysis = {
        "total_registros": 0,
        "eventos": 0,
        "deslocamentos": 0,
        "bloqueios": 0,
        "municipios": Counter(),
        "tipos_evento": Counter(),
    }

    for ws in data["worksheets"]:
        ws_title = ws.get("title", "")
        records = ws.get("records", [])

        print(f"📊 {ws_title}: {len(records)} registros")

        disponibilidade_analysis["total_registros"] += len(records)

        if "Eventos" in ws_title:
            disponibilidade_analysis["eventos"] = len(records)
        elif "DESLOCAMENTO" in ws_title:
            disponibilidade_analysis["deslocamentos"] = len(records)
        elif "Bloqueios" in ws_title:
            disponibilidade_analysis["bloqueios"] = len(records)

        # Analisar dados específicos
        for record in records:
            municipio = record.get("municipio", "") or record.get("Município", "")
            if municipio:
                disponibilidade_analysis["municipios"][municipio] += 1

            tipo = record.get("tipo", "") or record.get("Tipo", "")
            if tipo:
                disponibilidade_analysis["tipos_evento"][tipo] += 1

    print(f"📈 Total de registros: {disponibilidade_analysis['total_registros']}")
    print(f"📅 Eventos: {disponibilidade_analysis['eventos']}")
    print(f"🚗 Deslocamentos: {disponibilidade_analysis['deslocamentos']}")
    print(f"🚫 Bloqueios: {disponibilidade_analysis['bloqueios']}")

    print(f"\n🏙️ Top 10 Municípios:")
    for municipio, count in disponibilidade_analysis["municipios"].most_common(10):
        print(f"   {municipio}: {count}")

    print(f"\n📋 Top 10 Tipos de Evento:")
    for tipo, count in disponibilidade_analysis["tipos_evento"].most_common(10):
        print(f"   {tipo}: {count}")

    return disponibilidade_analysis


def cross_reference_analysis(
    usuarios_analysis, controle_analysis, agenda_analysis, disponibilidade_analysis
):
    """Cruza informações de todas as análises"""
    print("\n🔗 CRUZAMENTO DE INFORMAÇÕES")
    print("=" * 50)

    cross_analysis = {
        "municipios_comuns": set(),
        "projetos_comuns": set(),
        "coordenadores_identificados": set(),
        "inconsistencias": [],
        "dados_faltantes": [],
    }

    # Cruzar municípios
    usuarios_municipios = set(usuarios_analysis.get("municipios", {}).keys())
    controle_municipios = set(controle_analysis.get("municipios", {}).keys())
    agenda_municipios = set(agenda_analysis.get("municipios", {}).keys())
    disponibilidade_municipios = set(
        disponibilidade_analysis.get("municipios", {}).keys()
    )

    cross_analysis["municipios_comuns"] = (
        usuarios_municipios
        & controle_municipios
        & agenda_municipios
        & disponibilidade_municipios
    )

    print(
        f"🏙️ Municípios comuns em todas as planilhas: {len(cross_analysis['municipios_comuns'])}"
    )
    for municipio in sorted(cross_analysis["municipios_comuns"])[:10]:
        print(f"   - {municipio}")

    # Cruzar projetos
    usuarios_projetos = set(usuarios_analysis.get("projetos", {}).keys())
    controle_projetos = set(controle_analysis.get("projetos", {}).keys())
    agenda_projetos = set(agenda_analysis.get("projetos", {}).keys())

    cross_analysis["projetos_comuns"] = (
        usuarios_projetos & controle_projetos & agenda_projetos
    )

    print(
        f"\n🎯 Projetos comuns em todas as planilhas: {len(cross_analysis['projetos_comuns'])}"
    )
    for projeto in sorted(cross_analysis["projetos_comuns"])[:10]:
        print(f"   - {projeto}")

    # Identificar coordenadores
    coordenadores_controle = set(controle_analysis.get("coordenadores", {}).keys())
    cross_analysis["coordenadores_identificados"] = coordenadores_controle

    print(
        f"\n👨‍💼 Coordenadores identificados: {len(cross_analysis['coordenadores_identificados'])}"
    )
    for coordenador in sorted(cross_analysis["coordenadores_identificados"])[:10]:
        print(f"   - {coordenador}")

    # Identificar inconsistências
    municipios_usuarios_nao_controle = usuarios_municipios - controle_municipios
    if municipios_usuarios_nao_controle:
        cross_analysis["inconsistencias"].append(
            f"Municípios em usuários mas não em controle: {len(municipios_usuarios_nao_controle)}"
        )

    projetos_usuarios_nao_controle = usuarios_projetos - controle_projetos
    if projetos_usuarios_nao_controle:
        cross_analysis["inconsistencias"].append(
            f"Projetos em usuários mas não em controle: {len(projetos_usuarios_nao_controle)}"
        )

    print(f"\n⚠️ Inconsistências identificadas:")
    for inconsistencia in cross_analysis["inconsistencias"]:
        print(f"   - {inconsistencia}")

    return cross_analysis


def generate_import_recommendations(cross_analysis):
    """Gera recomendações para importação"""
    print("\n💡 RECOMENDAÇÕES PARA IMPORTAÇÃO")
    print("=" * 50)

    recommendations = []

    # Recomendações baseadas no cruzamento
    if cross_analysis["municipios_comuns"]:
        recommendations.append(
            f"✅ Importar {len(cross_analysis['municipios_comuns'])} municípios comuns"
        )

    if cross_analysis["projetos_comuns"]:
        recommendations.append(
            f"✅ Importar {len(cross_analysis['projetos_comuns'])} projetos comuns"
        )

    if cross_analysis["coordenadores_identificados"]:
        recommendations.append(
            f"✅ Importar {len(cross_analysis['coordenadores_identificados'])} coordenadores identificados"
        )

    # Recomendações de prioridade
    recommendations.extend(
        [
            "🎯 Prioridade 1: Importar dados de usuários (ativos, inativos, pendentes)",
            "🎯 Prioridade 2: Importar mapeamento coordenador-projeto-município",
            "🎯 Prioridade 3: Importar eventos e formações",
            "🎯 Prioridade 4: Importar disponibilidade e deslocamentos",
        ]
    )

    for rec in recommendations:
        print(f"   {rec}")

    return recommendations


def main():
    """Função principal"""
    print("🔍 ANÁLISE E CRUZAMENTO DE DADOS DAS PLANILHAS")
    print("=" * 80)

    # Carregar dados
    data = load_latest_data()

    if not any(data.values()):
        print("❌ Nenhum dado disponível para análise")
        return False

    # Analisar cada planilha
    usuarios_analysis = analyze_usuarios(data.get("usuarios"))
    controle_analysis = analyze_controle(data.get("controle"))
    agenda_analysis = analyze_agenda(data.get("agenda"))
    disponibilidade_analysis = analyze_disponibilidade(data.get("disponibilidade"))

    # Cruzar informações
    cross_analysis = cross_reference_analysis(
        usuarios_analysis, controle_analysis, agenda_analysis, disponibilidade_analysis
    )

    # Gerar recomendações
    recommendations = generate_import_recommendations(cross_analysis)

    # Salvar análise completa
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    analysis_file = f"analise_cruzada_completa_{timestamp}.json"

    complete_analysis = {
        "timestamp": timestamp,
        "usuarios": usuarios_analysis,
        "controle": controle_analysis,
        "agenda": agenda_analysis,
        "disponibilidade": disponibilidade_analysis,
        "cruzamento": cross_analysis,
        "recomendacoes": recommendations,
    }

    with open(analysis_file, "w", encoding="utf-8") as f:
        json.dump(complete_analysis, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n✅ Análise completa salva em: {analysis_file}")
    print("\n" + "=" * 80)
    print("🎯 ANÁLISE CONCLUÍDA!")
    print("=" * 80)

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

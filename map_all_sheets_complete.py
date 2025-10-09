#!/usr/bin/env python3
"""
Mapeamento Completo de Todas as Planilhas
=========================================

Acessa todas as 4 planilhas e faz mapeamento completo dos dados.

Author: Claude Code
Date: Setembro 2025
"""

import os
import sys
import json
import gspread
from google.oauth2.credentials import Credentials
from pathlib import Path
from datetime import datetime


def access_all_sheets():
    """Acessa todas as 4 planilhas"""
    print("📊 ACESSANDO TODAS AS 4 PLANILHAS")
    print("=" * 80)

    # Configurar credenciais
    creds_file = "google_oauth_token.json"
    if not os.path.exists(creds_file):
        print("❌ Arquivo de credenciais não encontrado")
        return None

    try:
        # Carregar credenciais
        with open(creds_file, "r") as f:
            creds_data = json.load(f)

        credentials = Credentials.from_authorized_user_info(creds_data)
        client = gspread.authorize(credentials)

        # URLs das planilhas
        sheets_info = {
            "Disponibilidade_2025": {
                "url": "https://docs.google.com/spreadsheets/d/1fsCeGUzsNCv0SCiE6mcIvcCHsMbqNeyzANwdU_148Vw/edit?gid=1510755488#gid=1510755488",
                "id": "1fsCeGUzsNCv0SCiE6mcIvcCHsMbqNeyzANwdU_148Vw",
                "purpose": "Disponibilidade de formadores",
            },
            "Controle_2025": {
                "url": "https://docs.google.com/spreadsheets/d/1P6YG3sIAEpiAPIQL9bKBaIznNl3V9VLan9CpVnrEOgA/edit?gid=0#gid=0",
                "id": "1P6YG3sIAEpiAPIQL9bKBaIznNl3V9VLan9CpVnrEOgA",
                "purpose": "Mapeamento coordenador-projeto-município",
            },
            "Acompanhamento_Agenda_2025": {
                "url": "https://docs.google.com/spreadsheets/d/16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU/edit?gid=2043156665#gid=2043156665",
                "id": "16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU",
                "purpose": "Eventos, projetos, municípios, formadores, coordenadores",
            },
            "Usuarios": {
                "url": "https://docs.google.com/spreadsheets/d/1Zj_I7sqYAJ9uaYbVoBfskl0LqxGM3SAFzwm4Zpph1RI/edit?gid=143336602#gid=143336602",
                "id": "1Zj_I7sqYAJ9uaYbVoBfskl0LqxGM3SAFzwm4Zpph1RI",
                "purpose": "Cadastro de usuários",
            },
        }

        all_data = {}

        for sheet_name, info in sheets_info.items():
            print(f"\n📋 ACESSANDO: {sheet_name}")
            print(f"   Propósito: {info['purpose']}")
            print(f"   ID: {info['id']}")

            try:
                # Acessar planilha
                spreadsheet = client.open_by_key(info["id"])
                print(f"   ✅ Planilha acessada: {spreadsheet.title}")

                # Listar abas
                worksheets = spreadsheet.worksheets()
                print(f"   📊 Abas disponíveis: {len(worksheets)}")

                sheet_data = {
                    "title": spreadsheet.title,
                    "purpose": info["purpose"],
                    "worksheets": [],
                }

                for ws in worksheets:
                    print(f"      - {ws.title} (ID: {ws.id})")

                    try:
                        # Obter dados da aba
                        records = ws.get_all_records()
                        print(f"         📊 Registros: {len(records)}")

                        # Analisar estrutura dos dados
                        if records:
                            sample_keys = list(records[0].keys())[
                                :5
                            ]  # Primeiras 5 colunas
                            print(f"         🔑 Colunas: {', '.join(sample_keys)}...")

                        worksheet_data = {
                            "title": ws.title,
                            "id": ws.id,
                            "records": records,
                            "record_count": len(records),
                        }

                        sheet_data["worksheets"].append(worksheet_data)

                    except Exception as e:
                        print(f"         ❌ Erro ao ler aba {ws.title}: {e}")
                        worksheet_data = {
                            "title": ws.title,
                            "id": ws.id,
                            "error": str(e),
                            "records": [],
                            "record_count": 0,
                        }
                        sheet_data["worksheets"].append(worksheet_data)

                all_data[sheet_name] = sheet_data

            except Exception as e:
                print(f"   ❌ Erro ao acessar planilha {sheet_name}: {e}")
                all_data[sheet_name] = {
                    "title": sheet_name,
                    "purpose": info["purpose"],
                    "error": str(e),
                    "worksheets": [],
                }

        return all_data

    except Exception as e:
        print(f"❌ Erro geral ao acessar planilhas: {e}")
        return None


def analyze_data_structure(all_data):
    """Analisa a estrutura dos dados de todas as planilhas"""
    print("\n🔍 ANÁLISE DA ESTRUTURA DOS DADOS")
    print("=" * 80)

    analysis = {
        "usuarios": set(),
        "coordenadores": set(),
        "formadores": set(),
        "municipios": set(),
        "projetos": set(),
        "eventos": 0,
    }

    for sheet_name, sheet_data in all_data.items():
        print(f"\n📋 {sheet_name.upper()}")
        print(f"   Propósito: {sheet_data.get('purpose', 'N/A')}")

        if "error" in sheet_data:
            print(f"   ❌ Erro: {sheet_data['error']}")
            continue

        for worksheet in sheet_data.get("worksheets", []):
            print(
                f"\n   📊 {worksheet['title']} ({worksheet['record_count']} registros)"
            )

            if "error" in worksheet:
                print(f"      ❌ Erro: {worksheet['error']}")
                continue

            records = worksheet.get("records", [])
            if not records:
                continue

            # Analisar campos relevantes
            for record in records:
                # Usuários/Coordenadores/Formadores
                for field in [
                    "Nome",
                    "nome",
                    "Coordenador",
                    "coordenador",
                    "Formador",
                    "formador",
                ]:
                    if field in record and record[field]:
                        name = str(record[field]).strip()
                        if name:
                            if "coordenador" in field.lower():
                                analysis["coordenadores"].add(name)
                            elif "formador" in field.lower():
                                analysis["formadores"].add(name)
                            else:
                                analysis["usuarios"].add(name)

                # Municípios
                for field in ["Município", "município", "Municipio", "municipio"]:
                    if field in record and record[field]:
                        municipio = str(record[field]).strip()
                        if municipio:
                            analysis["municipios"].add(municipio)

                # Projetos
                for field in ["Projeto", "projeto"]:
                    if field in record and record[field]:
                        projeto = str(record[field]).strip()
                        if projeto:
                            analysis["projetos"].add(projeto)

                # Contar eventos
                if any(
                    field in record for field in ["Data", "data", "Evento", "evento"]
                ):
                    analysis["eventos"] += 1

    # Resumo da análise
    print(f"\n📊 RESUMO DA ANÁLISE:")
    print(f"   👥 Usuários únicos: {len(analysis['usuarios'])}")
    print(f"   👨‍💼 Coordenadores únicos: {len(analysis['coordenadores'])}")
    print(f"   👨‍🏫 Formadores únicos: {len(analysis['formadores'])}")
    print(f"   🏙️ Municípios únicos: {len(analysis['municipios'])}")
    print(f"   📋 Projetos únicos: {len(analysis['projetos'])}")
    print(f"   📅 Total de eventos: {analysis['eventos']}")

    return analysis


def identify_data_sources(all_data):
    """Identifica as fontes de dados para cada tipo de informação"""
    print("\n🎯 IDENTIFICANDO FONTES DE DADOS")
    print("=" * 80)

    data_sources = {
        "usuarios": [],
        "coordenadores": [],
        "formadores": [],
        "municipios": [],
        "projetos": [],
        "eventos": [],
    }

    for sheet_name, sheet_data in all_data.items():
        if "error" in sheet_data:
            continue

        for worksheet in sheet_data.get("worksheets", []):
            if "error" in worksheet:
                continue

            records = worksheet.get("records", [])
            if not records:
                continue

            # Analisar cada tipo de dado
            for record in records:
                # Usuários
                if any(
                    field in record
                    for field in ["Nome", "nome", "CPF", "cpf", "Email", "email"]
                ):
                    data_sources["usuarios"].append(
                        {
                            "sheet": sheet_name,
                            "worksheet": worksheet["title"],
                            "record": record,
                        }
                    )

                # Coordenadores
                if any(field in record for field in ["Coordenador", "coordenador"]):
                    data_sources["coordenadores"].append(
                        {
                            "sheet": sheet_name,
                            "worksheet": worksheet["title"],
                            "record": record,
                        }
                    )

                # Formadores
                if any(field in record for field in ["Formador", "formador"]):
                    data_sources["formadores"].append(
                        {
                            "sheet": sheet_name,
                            "worksheet": worksheet["title"],
                            "record": record,
                        }
                    )

                # Municípios
                if any(
                    field in record
                    for field in ["Município", "município", "Municipio", "municipio"]
                ):
                    data_sources["municipios"].append(
                        {
                            "sheet": sheet_name,
                            "worksheet": worksheet["title"],
                            "record": record,
                        }
                    )

                # Projetos
                if any(field in record for field in ["Projeto", "projeto"]):
                    data_sources["projetos"].append(
                        {
                            "sheet": sheet_name,
                            "worksheet": worksheet["title"],
                            "record": record,
                        }
                    )

                # Eventos
                if any(
                    field in record
                    for field in [
                        "Data",
                        "data",
                        "Evento",
                        "evento",
                        "Título",
                        "titulo",
                    ]
                ):
                    data_sources["eventos"].append(
                        {
                            "sheet": sheet_name,
                            "worksheet": worksheet["title"],
                            "record": record,
                        }
                    )

    # Mostrar resumo das fontes
    for data_type, sources in data_sources.items():
        print(f"\n📊 {data_type.upper()}:")
        sheet_counts = {}
        for source in sources:
            sheet = source["sheet"]
            sheet_counts[sheet] = sheet_counts.get(sheet, 0) + 1

        for sheet, count in sheet_counts.items():
            print(f"   - {sheet}: {count} registros")

    return data_sources


def save_complete_mapping(all_data, analysis, data_sources):
    """Salva o mapeamento completo"""
    print("\n💾 SALVANDO MAPEAMENTO COMPLETO")
    print("=" * 50)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Salvar dados completos
    complete_file = f"mapeamento_completo_todas_planilhas_{timestamp}.json"
    with open(complete_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": timestamp,
                "sheets": all_data,
                "analysis": {
                    "usuarios_count": len(analysis["usuarios"]),
                    "coordenadores_count": len(analysis["coordenadores"]),
                    "formadores_count": len(analysis["formadores"]),
                    "municipios_count": len(analysis["municipios"]),
                    "projetos_count": len(analysis["projetos"]),
                    "eventos_count": analysis["eventos"],
                },
                "data_sources": data_sources,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"✅ Dados completos salvos em: {complete_file}")

    # Salvar resumo
    summary_file = f"resumo_mapeamento_{timestamp}.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": timestamp,
                "summary": {
                    "usuarios": list(analysis["usuarios"]),
                    "coordenadores": list(analysis["coordenadores"]),
                    "formadores": list(analysis["formadores"]),
                    "municipios": list(analysis["municipios"]),
                    "projetos": list(analysis["projetos"]),
                },
                "data_sources_summary": {
                    data_type: len(sources)
                    for data_type, sources in data_sources.items()
                },
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"✅ Resumo salvo em: {summary_file}")

    return complete_file, summary_file


def main():
    """Função principal"""
    print("🗺️ MAPEAMENTO COMPLETO DE TODAS AS PLANILHAS")
    print("=" * 80)

    # Acessar todas as planilhas
    all_data = access_all_sheets()
    if not all_data:
        print("❌ Falha ao acessar planilhas")
        return False

    # Analisar estrutura dos dados
    analysis = analyze_data_structure(all_data)

    # Identificar fontes de dados
    data_sources = identify_data_sources(all_data)

    # Salvar mapeamento completo
    complete_file, summary_file = save_complete_mapping(
        all_data, analysis, data_sources
    )

    print("\n" + "=" * 80)
    print("🎯 MAPEAMENTO COMPLETO CONCLUÍDO!")
    print(f"   📄 Dados completos: {complete_file}")
    print(f"   📄 Resumo: {summary_file}")
    print("=" * 80)

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

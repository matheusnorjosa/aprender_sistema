#!/usr/bin/env python3
"""
Mapeamento Simples das Planilhas
===============================

Acessa as planilhas uma por vez para evitar travamento.

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


def access_single_sheet(sheet_id, sheet_name, purpose):
    """Acessa uma única planilha"""
    print(f"📋 ACESSANDO: {sheet_name}")
    print(f"   Propósito: {purpose}")
    print(f"   ID: {sheet_id}")

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

        # Acessar planilha
        spreadsheet = client.open_by_key(sheet_id)
        print(f"   ✅ Planilha acessada: {spreadsheet.title}")

        # Listar abas
        worksheets = spreadsheet.worksheets()
        print(f"   📊 Abas disponíveis: {len(worksheets)}")

        sheet_data = {"title": spreadsheet.title, "purpose": purpose, "worksheets": []}

        for ws in worksheets:
            print(f"      - {ws.title} (ID: {ws.id})")

            try:
                # Obter dados da aba
                records = ws.get_all_records()
                print(f"         📊 Registros: {len(records)}")

                # Analisar estrutura dos dados
                if records:
                    sample_keys = list(records[0].keys())[:5]  # Primeiras 5 colunas
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

        return sheet_data

    except Exception as e:
        print(f"   ❌ Erro ao acessar planilha {sheet_name}: {e}")
        return {
            "title": sheet_name,
            "purpose": purpose,
            "error": str(e),
            "worksheets": [],
        }


def map_usuarios_sheet():
    """Mapeia a planilha de usuários"""
    print("👥 MAPEANDO PLANILHA DE USUÁRIOS")
    print("=" * 50)

    sheet_id = "1Zj_I7sqYAJ9uaYbVoBfskl0LqxGM3SAFzwm4Zpph1RI"
    sheet_name = "Usuarios"
    purpose = "Cadastro de usuários"

    data = access_single_sheet(sheet_id, sheet_name, purpose)

    if data and "worksheets" in data:
        # Salvar dados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"usuarios_planilha_{timestamp}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✅ Dados salvos em: {filename}")

        # Analisar dados
        total_records = sum(ws.get("record_count", 0) for ws in data["worksheets"])
        print(f"📊 Total de registros: {total_records}")

        return data

    return None


def map_controle_sheet():
    """Mapeia a planilha de controle"""
    print("\n🎯 MAPEANDO PLANILHA DE CONTROLE")
    print("=" * 50)

    sheet_id = "1P6YG3sIAEpiAPIQL9bKBaIznNl3V9VLan9CpVnrEOgA"
    sheet_name = "Controle_2025"
    purpose = "Mapeamento coordenador-projeto-município"

    data = access_single_sheet(sheet_id, sheet_name, purpose)

    if data and "worksheets" in data:
        # Salvar dados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"controle_planilha_{timestamp}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✅ Dados salvos em: {filename}")

        # Analisar dados
        total_records = sum(ws.get("record_count", 0) for ws in data["worksheets"])
        print(f"📊 Total de registros: {total_records}")

        return data

    return None


def map_agenda_sheet():
    """Mapeia a planilha de acompanhamento de agenda"""
    print("\n📅 MAPEANDO PLANILHA DE ACOMPANHAMENTO DE AGENDA")
    print("=" * 50)

    sheet_id = "16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU"
    sheet_name = "Acompanhamento_Agenda_2025"
    purpose = "Eventos, projetos, municípios, formadores, coordenadores"

    data = access_single_sheet(sheet_id, sheet_name, purpose)

    if data and "worksheets" in data:
        # Salvar dados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"agenda_planilha_{timestamp}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✅ Dados salvos em: {filename}")

        # Analisar dados
        total_records = sum(ws.get("record_count", 0) for ws in data["worksheets"])
        print(f"📊 Total de registros: {total_records}")

        return data

    return None


def map_disponibilidade_sheet():
    """Mapeia a planilha de disponibilidade"""
    print("\n📊 MAPEANDO PLANILHA DE DISPONIBILIDADE")
    print("=" * 50)

    sheet_id = "1fsCeGUzsNCv0SCiE6mcIvcCHsMbqNeyzANwdU_148Vw"
    sheet_name = "Disponibilidade_2025"
    purpose = "Disponibilidade de formadores"

    data = access_single_sheet(sheet_id, sheet_name, purpose)

    if data and "worksheets" in data:
        # Salvar dados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"disponibilidade_planilha_{timestamp}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✅ Dados salvos em: {filename}")

        # Analisar dados
        total_records = sum(ws.get("record_count", 0) for ws in data["worksheets"])
        print(f"📊 Total de registros: {total_records}")

        return data

    return None


def main():
    """Função principal"""
    print("🗺️ MAPEAMENTO SIMPLES DAS PLANILHAS")
    print("=" * 80)

    # Mapear cada planilha individualmente
    usuarios_data = map_usuarios_sheet()
    controle_data = map_controle_sheet()
    agenda_data = map_agenda_sheet()
    disponibilidade_data = map_disponibilidade_sheet()

    print("\n" + "=" * 80)
    print("🎯 MAPEAMENTO CONCLUÍDO!")
    print("=" * 80)

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

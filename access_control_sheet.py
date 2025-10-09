#!/usr/bin/env python3
"""
Acessar Planilha de Controle 2025
=================================

Acessa a planilha de controle e extrai dados de município, projeto e coordenador.

Author: Claude Code
Date: Setembro 2025
"""

import os
import sys
import json
import gspread
from google.oauth2.credentials import Credentials
from pathlib import Path


def access_control_sheet():
    """Acessa a planilha de controle"""
    print("📊 ACESSANDO PLANILHA DE CONTROLE 2025")
    print("=" * 60)

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

        # Acessar a planilha
        sheet_id = "1P6YG3sIAEpiAPIQL9bKBaIznNl3V9VLan9CpVnrEOgA"
        spreadsheet = client.open_by_key(sheet_id)

        print(f"✅ Planilha acessada: {spreadsheet.title}")

        # Listar todas as planilhas
        worksheets = spreadsheet.worksheets()
        print(f"📋 Planilhas disponíveis: {len(worksheets)}")
        for ws in worksheets:
            print(f"   - {ws.title} (ID: {ws.id})")

        # Tentar acessar a planilha específica (gid=1393267536)
        target_gid = "1393267536"
        target_worksheet = None

        for ws in worksheets:
            if str(ws.id) == target_gid:
                target_worksheet = ws
                break

        if not target_worksheet:
            print(f"⚠️ Planilha com gid {target_gid} não encontrada, usando a primeira")
            target_worksheet = worksheets[0]

        print(f"📊 Acessando planilha: {target_worksheet.title}")

        # Obter todos os dados
        all_data = target_worksheet.get_all_records()
        print(f"📊 Total de registros: {len(all_data)}")

        # Extrair dados das colunas A, B, C
        control_data = []
        for i, row in enumerate(all_data):
            municipio = (
                row.get("Município", "")
                or row.get("município", "")
                or row.get("Municipio", "")
            )
            projeto = row.get("Projeto", "") or row.get("projeto", "")
            coordenador = row.get("Coordenador", "") or row.get("coordenador", "")

            if municipio or projeto or coordenador:
                control_data.append(
                    {
                        "linha": i
                        + 2,  # +2 porque começa na linha 2 (linha 1 é cabeçalho)
                        "municipio": municipio,
                        "projeto": projeto,
                        "coordenador": coordenador,
                    }
                )

        print(f"📊 Registros válidos extraídos: {len(control_data)}")

        # Salvar dados
        output_file = f"planilha_controle_2025_{len(control_data)}_registros.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "planilha": spreadsheet.title,
                    "worksheet": target_worksheet.title,
                    "gid": target_worksheet.id,
                    "total_registros": len(all_data),
                    "registros_validos": len(control_data),
                    "dados": control_data,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        print(f"💾 Dados salvos em: {output_file}")

        # Mostrar primeiros registros
        print("\n📋 PRIMEIROS 10 REGISTROS:")
        for i, item in enumerate(control_data[:10]):
            print(
                f"   {i+1}. Linha {item['linha']}: {item['municipio']} | {item['projeto']} | {item['coordenador']}"
            )

        # Análise dos dados
        print("\n📊 ANÁLISE DOS DADOS:")

        # Municípios únicos
        municipios = set(
            item["municipio"] for item in control_data if item["municipio"]
        )
        print(f"   🏙️ Municípios únicos: {len(municipios)}")

        # Projetos únicos
        projetos = set(item["projeto"] for item in control_data if item["projeto"])
        print(f"   📋 Projetos únicos: {len(projetos)}")

        # Coordenadores únicos
        coordenadores = set(
            item["coordenador"] for item in control_data if item["coordenador"]
        )
        print(f"   👨‍💼 Coordenadores únicos: {len(coordenadores)}")

        # Relacionamentos
        relacionamentos = {}
        for item in control_data:
            if item["municipio"] and item["projeto"] and item["coordenador"]:
                key = f"{item['municipio']} - {item['projeto']}"
                if key not in relacionamentos:
                    relacionamentos[key] = []
                relacionamentos[key].append(item["coordenador"])

        print(f"   🔗 Relacionamentos únicos: {len(relacionamentos)}")

        return output_file

    except Exception as e:
        print(f"❌ Erro ao acessar planilha: {e}")
        return None


def main():
    """Função principal"""
    print("🚀 ACESSANDO PLANILHA DE CONTROLE 2025")
    print("=" * 80)

    output_file = access_control_sheet()

    if output_file:
        print(f"\n✅ SUCESSO! Dados extraídos e salvos em: {output_file}")
    else:
        print("\n❌ FALHA! Não foi possível acessar a planilha")

    print("=" * 80)

    return output_file


if __name__ == "__main__":
    result = main()
    sys.exit(0 if result else 1)

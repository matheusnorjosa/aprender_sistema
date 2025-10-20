#!/usr/bin/env python3
"""
Verificar Eventos da Bahia
=========================

Verifica os eventos da Bahia nos dados extraídos.

Author: Claude Code
Date: Setembro 2025
"""

import json
import os
import sys
from pathlib import Path


def check_bahia_events():
    """Verifica os eventos da Bahia"""
    print("🌴 VERIFICANDO EVENTOS DA BAHIA")
    print("=" * 50)

    # Carregar dados de eventos
    eventos_file = Path("eventos_completos_20250924_172144.json")
    if not eventos_file.exists():
        print("❌ Arquivo de eventos não encontrado")
        return

    with open(eventos_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    eventos = data.get("eventos", [])
    print(f"📊 Total de eventos: {len(eventos)}")

    # Filtrar eventos da Bahia
    eventos_bahia = []
    for evento in eventos:
        dados = evento.get("dados", {})
        municipio = dados.get("municipio", "")
        if "BA" in municipio or "Bahia" in municipio:
            eventos_bahia.append(evento)

    print(f"🌴 Eventos da Bahia: {len(eventos_bahia)}")

    # Analisar eventos da Bahia
    municipios_bahia = {}
    for evento in eventos_bahia:
        dados = evento.get("dados", {})
        municipio = dados.get("municipio", "")
        projeto = dados.get("projeto", "")
        tipo = dados.get("tipo", "")

        if municipio not in municipios_bahia:
            municipios_bahia[municipio] = {
                "eventos": 0,
                "projetos": set(),
                "tipos": set(),
            }

        municipios_bahia[municipio]["eventos"] += 1
        if projeto:
            municipios_bahia[municipio]["projetos"].add(projeto)
        if tipo:
            municipios_bahia[municipio]["tipos"].add(tipo)

    print("\n🌴 MUNICÍPIOS DA BAHIA NOS DADOS EXTRAÍDOS:")
    for municipio, info in municipios_bahia.items():
        print(f"   {municipio}: {info['eventos']} eventos")
        print(f"     Projetos: {', '.join(info['projetos'])}")
        print(f"     Tipos: {', '.join(info['tipos'])}")
        print()


def check_atibaia_data():
    """Verifica dados de Atibaia"""
    print("🏔️ VERIFICANDO DADOS DE ATIBAIA")
    print("=" * 50)

    # Verificar em todos os arquivos
    files_to_check = [
        "usuarios_completos_20250924_172144.json",
        "eventos_completos_20250924_172144.json",
        "formacoes_completas_20250924_172144.json",
        "mapeamento_completo_google_sheets_20250923_220315.json",
    ]

    for file_name in files_to_check:
        file_path = Path(file_name)
        if file_path.exists():
            print(f"\n📄 {file_name}:")
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Procurar por Atibaia
                atibaia_found = False

                if "usuarios" in data:
                    usuarios = data["usuarios"]
                    for usuario in usuarios:
                        if "Atibaia" in str(usuario):
                            print(f"   👥 Usuário: {usuario}")
                            atibaia_found = True

                if "eventos" in data:
                    eventos = data["eventos"]
                    for evento in eventos:
                        if "Atibaia" in str(evento):
                            print(f"   📅 Evento: {evento}")
                            atibaia_found = True

                if "formacoes" in data:
                    formacoes = data["formacoes"]
                    for formacao in formacoes:
                        if "Atibaia" in str(formacao):
                            print(f"   📚 Formação: {formacao}")
                            atibaia_found = True

                if "planilhas" in data:
                    planilhas = data["planilhas"]
                    for planilha_nome, planilha_data in planilhas.items():
                        if "abas" in planilha_data:
                            for aba in planilha_data["abas"]:
                                if "dados" in aba:
                                    dados = aba["dados"]
                                    for dado in dados:
                                        if "Atibaia" in str(dado):
                                            print(
                                                f"   📊 {planilha_nome} - {aba['nome']}: {dado}"
                                            )
                                            atibaia_found = True

                if not atibaia_found:
                    print("   ❌ Nenhum dado de Atibaia encontrado")

            except Exception as e:
                print(f"   ❌ Erro ao ler arquivo: {e}")


def main():
    """Função principal"""
    print("🔍 VERIFICAÇÃO DE DADOS FALTANTES")
    print("=" * 80)

    check_bahia_events()
    check_atibaia_data()

    print("\n" + "=" * 80)
    print("🎯 VERIFICAÇÃO CONCLUÍDA")
    print("=" * 80)


if __name__ == "__main__":
    main()
    sys.exit(0)

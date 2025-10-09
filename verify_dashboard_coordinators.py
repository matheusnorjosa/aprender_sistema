#!/usr/bin/env python3
"""
Verificar Dashboard Coordenadores por Município
==============================================

Verifica se os dados do dashboard estão corretos comparando com os dados extraídos.

Author: Claude Code
Date: Setembro 2025
"""

import os
import sys
import json
import django
from pathlib import Path

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()

from core.models import Usuario, Setor, Municipio, Projeto, TipoEvento, Solicitacao
from core.services.data_services import DashboardService


def load_control_sheet_data():
    """Carrega os dados da planilha de controle"""
    control_files = list(Path(".").glob("planilha_controle_2025_*.json"))
    if not control_files:
        return None

    with open(control_files[0], "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("dados", [])


def get_dashboard_data():
    """Obtém dados do dashboard"""
    print("📊 OBTENDO DADOS DO DASHBOARD")
    print("=" * 50)

    try:
        dashboard_data = DashboardService.get_coordenadores_por_municipio()
        return dashboard_data
    except Exception as e:
        print(f"❌ Erro ao obter dados do dashboard: {e}")
        return None


def verify_rondonopolis_data():
    """Verifica dados específicos de Rondonópolis"""
    print("\n🏙️ VERIFICANDO DADOS DE RONDONÓPOLIS")
    print("=" * 50)

    # Buscar município Rondonópolis
    municipio = Municipio.objects.filter(nome__icontains="Rondonópolis").first()
    if not municipio:
        print("❌ Município Rondonópolis não encontrado")
        return

    print(f"✅ Município encontrado: {municipio.nome} - {municipio.uf}")

    # Buscar solicitações para Rondonópolis
    solicitacoes = Solicitacao.objects.filter(municipio=municipio)
    print(f"📊 Total de solicitações: {solicitacoes.count()}")

    # Agrupar por coordenador
    coordenadores_count = {}
    for solicitacao in solicitacoes:
        if (
            solicitacao.usuario_solicitante
            and solicitacao.usuario_solicitante.cargo == "coordenador"
        ):
            nome = f"{solicitacao.usuario_solicitante.first_name} {solicitacao.usuario_solicitante.last_name}".strip()
            coordenadores_count[nome] = coordenadores_count.get(nome, 0) + 1

    print(f"\n👨‍💼 COORDENADORES E SEUS EVENTOS:")
    for nome, count in sorted(
        coordenadores_count.items(), key=lambda x: x[1], reverse=True
    ):
        print(f"   {nome}: {count} eventos")

    return coordenadores_count


def verify_control_sheet_rondonopolis():
    """Verifica dados de Rondonópolis na planilha de controle"""
    print("\n📋 VERIFICANDO PLANILHA DE CONTROLE - RONDONÓPOLIS")
    print("=" * 50)

    control_data = load_control_sheet_data()
    if not control_data:
        print("❌ Dados da planilha não encontrados")
        return None

    # Filtrar dados de Rondonópolis
    rondonopolis_data = []
    for item in control_data:
        municipio = item.get("municipio", "").strip()
        if "RONDONÓPOLIS" in municipio.upper() or "RONDONOPOLIS" in municipio.upper():
            rondonopolis_data.append(item)

    print(f"📊 Registros de Rondonópolis na planilha: {len(rondonopolis_data)}")

    # Agrupar por coordenador
    coordenadores_planilha = {}
    for item in rondonopolis_data:
        coordenador = item.get("coordenador", "").strip()
        if coordenador:
            coordenadores_planilha[coordenador] = (
                coordenadores_planilha.get(coordenador, 0) + 1
            )

    print(f"\n👨‍💼 COORDENADORES NA PLANILHA:")
    for nome, count in sorted(
        coordenadores_planilha.items(), key=lambda x: x[1], reverse=True
    ):
        print(f"   {nome}: {count} registros")

    return coordenadores_planilha


def compare_data(dashboard_data, planilha_data):
    """Compara dados do dashboard com a planilha"""
    print("\n🔍 COMPARANDO DADOS")
    print("=" * 50)

    print("📊 DASHBOARD vs PLANILHA:")

    # Comparar coordenadores
    dashboard_coords = set(dashboard_data.keys())
    planilha_coords = set(planilha_data.keys())

    print(f"\n👨‍💼 Coordenadores no dashboard: {len(dashboard_coords)}")
    print(f"👨‍💼 Coordenadores na planilha: {len(planilha_coords)}")

    # Coordenadores apenas no dashboard
    only_dashboard = dashboard_coords - planilha_coords
    if only_dashboard:
        print(f"\n➕ Coordenadores apenas no dashboard: {len(only_dashboard)}")
        for coord in sorted(only_dashboard):
            print(f"   - {coord}")

    # Coordenadores apenas na planilha
    only_planilha = planilha_coords - dashboard_coords
    if only_planilha:
        print(f"\n➕ Coordenadores apenas na planilha: {len(only_planilha)}")
        for coord in sorted(only_planilha):
            print(f"   - {coord}")

    # Coordenadores em ambos
    both = dashboard_coords & planilha_coords
    print(f"\n🔄 Coordenadores em ambos: {len(both)}")

    # Comparar contagens
    print(f"\n📊 COMPARAÇÃO DE CONTAGENS:")
    for coord in sorted(both):
        dashboard_count = dashboard_data[coord]
        planilha_count = planilha_data[coord]
        diff = dashboard_count - planilha_count
        status = "✅" if diff == 0 else "⚠️"
        print(
            f"   {status} {coord}: Dashboard={dashboard_count}, Planilha={planilha_count} (diff={diff:+d})"
        )


def check_dashboard_service():
    """Verifica o serviço do dashboard"""
    print("\n🔧 VERIFICANDO SERVIÇO DO DASHBOARD")
    print("=" * 50)

    try:
        # Testar método do dashboard
        dashboard_data = DashboardService.get_coordenadores_por_municipio()

        if "municipios" in dashboard_data:
            municipios = dashboard_data["municipios"]
            print(f"📊 Municípios no dashboard: {len(municipios)}")

            # Encontrar Rondonópolis
            rondonopolis = None
            for municipio in municipios:
                if "Rondonópolis" in municipio.get("municipio", ""):
                    rondonopolis = municipio
                    break

            if rondonopolis:
                print(f"✅ Rondonópolis encontrado no dashboard")
                coordenadores = rondonopolis.get("coordenadores", [])
                print(f"👨‍💼 Coordenadores no dashboard: {len(coordenadores)}")

                for coord in coordenadores:
                    nome = coord.get("nome", "")
                    eventos = coord.get("eventos", 0)
                    print(f"   - {nome}: {eventos} eventos")
            else:
                print("❌ Rondonópolis não encontrado no dashboard")
        else:
            print("❌ Estrutura de dados do dashboard inválida")

    except Exception as e:
        print(f"❌ Erro ao verificar serviço do dashboard: {e}")


def main():
    """Função principal"""
    print("🔍 VERIFICANDO DASHBOARD COORDENADORES POR MUNICÍPIO")
    print("=" * 80)

    # Verificar dados do dashboard
    dashboard_data = get_dashboard_data()

    # Verificar dados de Rondonópolis no sistema
    rondonopolis_dashboard = verify_rondonopolis_data()

    # Verificar dados de Rondonópolis na planilha
    rondonopolis_planilha = verify_control_sheet_rondonopolis()

    # Verificar serviço do dashboard
    check_dashboard_service()

    # Comparar dados
    if rondonopolis_dashboard and rondonopolis_planilha:
        compare_data(rondonopolis_dashboard, rondonopolis_planilha)

    print("\n" + "=" * 80)
    print("🎯 VERIFICAÇÃO CONCLUÍDA")
    print("=" * 80)


if __name__ == "__main__":
    main()
    sys.exit(0)

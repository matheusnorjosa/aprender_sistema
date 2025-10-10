#!/usr/bin/env python3
"""
Investigar Dados Faltantes
==========================

Investiga os dados que deveriam estar no sistema mas não estão.

Author: Claude Code
Date: Setembro 2025
"""

import json
import os
import sys
from pathlib import Path

import django

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()

from core.models import Municipio, Projeto, Setor, Solicitacao, TipoEvento, Usuario


def investigate_extracted_data():
    """Investiga os dados extraídos dos Google Sheets"""
    print("📊 INVESTIGAÇÃO DOS DADOS EXTRAÍDOS")
    print("=" * 60)

    # Procurar arquivos de dados extraídos
    data_files = [
        "usuarios_completos_20250924_172144.json",
        "eventos_completos_20250924_172144.json",
        "formacoes_completas_20250924_172144.json",
        "mapeamento_completo_google_sheets_20250923_220315.json",
    ]

    for file_name in data_files:
        file_path = Path(file_name)
        if file_path.exists():
            print(f"\n📄 {file_name}:")
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if "usuarios" in data:
                    usuarios = data["usuarios"]
                    print(f"   👥 Usuários: {len(usuarios)}")

                    # Verificar usuários da Bahia
                    usuarios_bahia = [
                        u for u in usuarios if "BA" in str(u.get("UF", ""))
                    ]
                    print(f"   🌴 Usuários da Bahia: {len(usuarios_bahia)}")

                    # Verificar Atibaia
                    usuarios_atibaia = [
                        u for u in usuarios if "Atibaia" in str(u.get("Municipio", ""))
                    ]
                    print(f"   🏔️ Usuários de Atibaia: {len(usuarios_atibaia)}")

                elif "eventos" in data:
                    eventos = data["eventos"]
                    print(f"   📅 Eventos: {len(eventos)}")

                    # Verificar eventos da Bahia
                    eventos_bahia = [
                        e
                        for e in eventos
                        if "BA" in str(e.get("dados", {}).get("municipio", ""))
                    ]
                    print(f"   🌴 Eventos da Bahia: {len(eventos_bahia)}")

                    # Verificar Atibaia
                    eventos_atibaia = [
                        e
                        for e in eventos
                        if "Atibaia" in str(e.get("dados", {}).get("municipio", ""))
                    ]
                    print(f"   🏔️ Eventos de Atibaia: {len(eventos_atibaia)}")

                elif "formacoes" in data:
                    formacoes = data["formacoes"]
                    print(f"   📚 Formações: {len(formacoes)}")

                elif "planilhas" in data:
                    planilhas = data["planilhas"]
                    print(f"   📊 Planilhas: {len(planilhas)}")

                    # Verificar dados específicos
                    for planilha_nome, planilha_data in planilhas.items():
                        if "abas" in planilha_data:
                            for aba in planilha_data["abas"]:
                                if "dados" in aba:
                                    dados = aba["dados"]
                                    if dados:
                                        # Verificar se há dados da Bahia
                                        dados_bahia = [
                                            d
                                            for d in dados
                                            if "BA" in str(d.get("municipio", ""))
                                        ]
                                        if dados_bahia:
                                            print(
                                                f"     🌴 {planilha_nome} - {aba['nome']}: {len(dados_bahia)} registros da Bahia"
                                            )

                                        # Verificar Atibaia
                                        dados_atibaia = [
                                            d
                                            for d in dados
                                            if "Atibaia" in str(d.get("municipio", ""))
                                        ]
                                        if dados_atibaia:
                                            print(
                                                f"     🏔️ {planilha_nome} - {aba['nome']}: {len(dados_atibaia)} registros de Atibaia"
                                            )

            except Exception as e:
                print(f"   ❌ Erro ao ler arquivo: {e}")
        else:
            print(f"❌ Arquivo não encontrado: {file_name}")


def investigate_current_data():
    """Investiga os dados atuais no sistema"""
    print("\n🗄️ INVESTIGAÇÃO DOS DADOS ATUAIS")
    print("=" * 60)

    # Municípios da Bahia
    municipios_bahia = Municipio.objects.filter(uf="BA")
    print(f"🌴 Municípios da Bahia no sistema: {municipios_bahia.count()}")
    for municipio in municipios_bahia:
        solicitacoes = Solicitacao.objects.filter(municipio=municipio).count()
        print(f"   - {municipio.nome}: {solicitacoes} solicitações")

    # Verificar Atibaia
    municipios_atibaia = Municipio.objects.filter(nome__icontains="Atibaia")
    print(f"\n🏔️ Municípios com 'Atibaia' no sistema: {municipios_atibaia.count()}")
    for municipio in municipios_atibaia:
        solicitacoes = Solicitacao.objects.filter(municipio=municipio).count()
        print(f"   - {municipio.nome} - {municipio.uf}: {solicitacoes} solicitações")

    # Verificar todos os municípios
    print(f"\n🗺️ TODOS OS MUNICÍPIOS NO SISTEMA:")
    municipios = Municipio.objects.all().order_by("uf", "nome")
    for municipio in municipios:
        solicitacoes = Solicitacao.objects.filter(municipio=municipio).count()
        if solicitacoes > 0:
            print(f"   {municipio.nome} - {municipio.uf}: {solicitacoes} solicitações")


def investigate_solicitations_by_municipality():
    """Investiga as solicitações por município"""
    print("\n📝 INVESTIGAÇÃO DAS SOLICITAÇÕES POR MUNICÍPIO")
    print("=" * 60)

    from django.db.models import Count

    # Solicitações por município
    solicitacoes_por_municipio = (
        Solicitacao.objects.values("municipio__nome", "municipio__uf")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    print("📊 Top 20 municípios por solicitações:")
    for item in solicitacoes_por_municipio[:20]:
        municipio = item["municipio__nome"] or "Sem município"
        uf = item["municipio__uf"] or "N/A"
        count = item["count"]
        print(f"   {municipio} - {uf}: {count} solicitações")

    # Verificar municípios sem solicitações
    municipios_sem_solicitacoes = Municipio.objects.exclude(solicitacao__isnull=False)
    print(f"\n⚠️ Municípios sem solicitações: {municipios_sem_solicitacoes.count()}")
    for municipio in municipios_sem_solicitacoes[:10]:
        print(f"   - {municipio.nome} - {municipio.uf}")


def investigate_missing_municipalities():
    """Investiga municípios que deveriam estar mas não estão"""
    print("\n🔍 INVESTIGAÇÃO DE MUNICÍPIOS FALTANTES")
    print("=" * 60)

    # Municípios conhecidos que deveriam estar
    municipios_esperados = [
        "Atibaia",
        "São Paulo",
        "Santos",
        "Campinas",
        "Ribeirão Preto",
        "Salvador",
        "Feira de Santana",
        "Vitória da Conquista",
        "Camaçari",
        "Fortaleza",
        "Caucaia",
        "Sobral",
        "Juazeiro do Norte",
        "Maracanaú",
    ]

    print("🔍 Verificando municípios esperados:")
    for municipio_nome in municipios_esperados:
        municipio = Municipio.objects.filter(nome__icontains=municipio_nome).first()
        if municipio:
            solicitacoes = Solicitacao.objects.filter(municipio=municipio).count()
            print(
                f"   ✅ {municipio.nome} - {municipio.uf}: {solicitacoes} solicitações"
            )
        else:
            print(f"   ❌ {municipio_nome}: NÃO ENCONTRADO")


def main():
    """Função principal"""
    print("🔍 INVESTIGAÇÃO DOS DADOS FALTANTES")
    print("=" * 80)

    investigate_extracted_data()
    investigate_current_data()
    investigate_solicitations_by_municipality()
    investigate_missing_municipalities()

    print("\n" + "=" * 80)
    print("🎯 INVESTIGAÇÃO CONCLUÍDA")
    print("=" * 80)


if __name__ == "__main__":
    main()
    sys.exit(0)

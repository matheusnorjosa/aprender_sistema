#!/usr/bin/env python3
"""
Verificação Final do Status do Sistema
=====================================

Verifica o status final do sistema após todas as importações.

Author: Claude Code
Date: Setembro 2025
"""

import os
import sys
from datetime import datetime
from pathlib import Path

from django.utils import timezone

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
import django

django.setup()

from core.models import (
    Municipio,
    Projeto,
    Setor,
    Solicitacao,
    SolicitacaoStatus,
    TipoEvento,
    Usuario,
)
from core.services import (
    CoordinatorService,
    DashboardService,
    FormadorService,
    UsuarioService,
)


def verify_users():
    """Verifica status dos usuários"""
    print("👥 VERIFICAÇÃO DE USUÁRIOS")
    print("=" * 50)

    total_usuarios = Usuario.objects.count()
    usuarios_ativos = Usuario.objects.filter(is_active=True).count()
    usuarios_inativos = Usuario.objects.filter(is_active=False).count()

    formadores = FormadorService.get_formadores_queryset().count()
    coordenadores = CoordinatorService.get_coordenadores_queryset().count()

    print(f"📊 Total de usuários: {total_usuarios}")
    print(f"✅ Usuários ativos: {usuarios_ativos}")
    print(f"❌ Usuários inativos: {usuarios_inativos}")
    print(f"👨‍🏫 Formadores: {formadores}")
    print(f"👨‍💼 Coordenadores: {coordenadores}")

    # Verificar cargos
    cargos = Usuario.objects.values_list("cargo", flat=True).distinct()
    print(f"\n👔 Cargos identificados:")
    for cargo in cargos:
        if cargo:
            count = Usuario.objects.filter(cargo=cargo).count()
            print(f"   - {cargo}: {count}")

    return {
        "total_usuarios": total_usuarios,
        "usuarios_ativos": usuarios_ativos,
        "usuarios_inativos": usuarios_inativos,
        "formadores": formadores,
        "coordenadores": coordenadores,
    }


def verify_entities():
    """Verifica status das entidades"""
    print("\n🏢 VERIFICAÇÃO DE ENTIDADES")
    print("=" * 50)

    setores = Setor.objects.filter(ativo=True).count()
    municipios = Municipio.objects.filter(ativo=True).count()
    projetos = Projeto.objects.filter(ativo=True).count()
    tipos_evento = TipoEvento.objects.filter(ativo=True).count()

    print(f"🏢 Setores ativos: {setores}")
    print(f"🏙️ Municípios ativos: {municipios}")
    print(f"🎯 Projetos ativos: {projetos}")
    print(f"📋 Tipos de evento ativos: {tipos_evento}")

    # Verificar distribuição por UF
    ufs = Municipio.objects.values_list("uf", flat=True).distinct()
    print(f"\n🗺️ Distribuição por UF:")
    for uf in ufs:
        if uf:
            count = Municipio.objects.filter(uf=uf, ativo=True).count()
            print(f"   - {uf}: {count}")

    return {
        "setores": setores,
        "municipios": municipios,
        "projetos": projetos,
        "tipos_evento": tipos_evento,
    }


def verify_solicitations():
    """Verifica status das solicitações"""
    print("\n📋 VERIFICAÇÃO DE SOLICITAÇÕES")
    print("=" * 50)

    total_solicitacoes = Solicitacao.objects.count()
    solicitacoes_aprovadas = Solicitacao.objects.filter(
        status=SolicitacaoStatus.APROVADO
    ).count()
    solicitacoes_pendentes = Solicitacao.objects.filter(
        status=SolicitacaoStatus.PENDENTE
    ).count()
    solicitacoes_rejeitadas = Solicitacao.objects.filter(status="rejeitado").count()

    print(f"📊 Total de solicitações: {total_solicitacoes}")
    print(f"✅ Aprovadas: {solicitacoes_aprovadas}")
    print(f"⏳ Pendentes: {solicitacoes_pendentes}")
    print(f"❌ Rejeitadas: {solicitacoes_rejeitadas}")

    # Verificar distribuição por projeto
    projetos_solicitacoes = Solicitacao.objects.values_list(
        "projeto__nome", flat=True
    ).distinct()
    print(f"\n🎯 Solicitações por projeto:")
    for projeto in projetos_solicitacoes:
        if projeto:
            count = Solicitacao.objects.filter(projeto__nome=projeto).count()
            print(f"   - {projeto}: {count}")

    # Verificar distribuição por município
    municipios_solicitacoes = Solicitacao.objects.values_list(
        "municipio__nome", flat=True
    ).distinct()
    print(f"\n🏙️ Solicitações por município (top 10):")
    for municipio in municipios_solicitacoes[:10]:
        if municipio:
            count = Solicitacao.objects.filter(municipio__nome=municipio).count()
            print(f"   - {municipio}: {count}")

    return {
        "total_solicitacoes": total_solicitacoes,
        "solicitacoes_aprovadas": solicitacoes_aprovadas,
        "solicitacoes_pendentes": solicitacoes_pendentes,
        "solicitacoes_rejeitadas": solicitacoes_rejeitadas,
    }


def verify_dashboard():
    """Verifica status do dashboard"""
    print("\n📊 VERIFICAÇÃO DO DASHBOARD")
    print("=" * 50)

    try:
        # Verificar estatísticas gerais
        stats = DashboardService.get_estatisticas_gerais()
        print(f"📈 Estatísticas gerais:")
        for key, value in stats.items():
            print(f"   - {key}: {value}")

        # Verificar coordenadores por município
        coordenadores_municipio = DashboardService.get_coordenadores_por_municipio()
        municipios_data = coordenadores_municipio.get("municipios", [])
        print(f"\n👨‍💼 Coordenadores por município: {len(municipios_data)} municípios")

        # Mostrar alguns exemplos
        for municipio in municipios_data[:5]:
            coordenadores = municipio.get("coordenadores", [])
            print(
                f"   - {municipio.get('municipio', 'N/A')} - {municipio.get('uf', 'N/A')}: {len(coordenadores)} coordenadores"
            )

        # Verificar formadores por área
        formadores_area = DashboardService.get_formadores_por_area()
        print(f"\n👨‍🏫 Formadores por área: {len(formadores_area)} áreas")

        # Verificar projetos por setor
        projetos_setor = DashboardService.get_projetos_por_setor()
        print(f"\n🎯 Projetos por setor: {len(projetos_setor)} setores")

        # Verificar solicitações por status
        solicitacoes_status = DashboardService.get_solicitacoes_por_status()
        print(f"\n📋 Solicitações por status: {len(solicitacoes_status)} status")

        # Verificar eventos por tipo
        eventos_tipo = DashboardService.get_eventos_por_tipo()
        print(f"\n📅 Eventos por tipo: {len(eventos_tipo)} tipos")

        return True

    except Exception as e:
        print(f"❌ Erro ao verificar dashboard: {e}")
        return False


def verify_services():
    """Verifica status dos serviços"""
    print("\n🔧 VERIFICAÇÃO DOS SERVIÇOS")
    print("=" * 50)

    try:
        # Verificar UsuarioService
        usuarios_ativos = UsuarioService.ativos().count()
        print(f"👥 UsuarioService.ativos(): {usuarios_ativos}")

        # Verificar FormadorService
        formadores = FormadorService.get_formadores_queryset().count()
        print(f"👨‍🏫 FormadorService.get_formadores_queryset(): {formadores}")

        # Verificar CoordinatorService
        coordenadores = CoordinatorService.get_coordenadores_queryset().count()
        print(f"👨‍💼 CoordinatorService.get_coordenadores_queryset(): {coordenadores}")

        return True

    except Exception as e:
        print(f"❌ Erro ao verificar serviços: {e}")
        return False


def generate_final_report(
    users_data, entities_data, solicitations_data, dashboard_ok, services_ok
):
    """Gera relatório final"""
    print("\n" + "=" * 80)
    print("📋 RELATÓRIO FINAL DO SISTEMA")
    print("=" * 80)

    print(f"👥 USUÁRIOS:")
    print(f"   - Total: {users_data['total_usuarios']}")
    print(f"   - Ativos: {users_data['usuarios_ativos']}")
    print(f"   - Formadores: {users_data['formadores']}")
    print(f"   - Coordenadores: {users_data['coordenadores']}")

    print(f"\n🏢 ENTIDADES:")
    print(f"   - Setores: {entities_data['setores']}")
    print(f"   - Municípios: {entities_data['municipios']}")
    print(f"   - Projetos: {entities_data['projetos']}")
    print(f"   - Tipos de evento: {entities_data['tipos_evento']}")

    print(f"\n📋 SOLICITAÇÕES:")
    print(f"   - Total: {solicitations_data['total_solicitacoes']}")
    print(f"   - Aprovadas: {solicitations_data['solicitacoes_aprovadas']}")
    print(f"   - Pendentes: {solicitations_data['solicitacoes_pendentes']}")

    print(f"\n🔧 SERVIÇOS:")
    print(f"   - Dashboard: {'✅ OK' if dashboard_ok else '❌ ERRO'}")
    print(f"   - Serviços: {'✅ OK' if services_ok else '❌ ERRO'}")

    print(f"\n🎯 STATUS GERAL:")
    if (
        users_data["total_usuarios"] > 0
        and entities_data["municipios"] > 0
        and entities_data["projetos"] > 0
        and solicitations_data["total_solicitacoes"] > 0
        and dashboard_ok
        and services_ok
    ):
        print("   ✅ SISTEMA FUNCIONANDO CORRETAMENTE")
    else:
        print("   ⚠️ SISTEMA COM PROBLEMAS")

    print("=" * 80)


def main():
    """Função principal"""
    print("🔍 VERIFICAÇÃO FINAL DO STATUS DO SISTEMA")
    print("=" * 80)

    try:
        # Verificar usuários
        users_data = verify_users()

        # Verificar entidades
        entities_data = verify_entities()

        # Verificar solicitações
        solicitations_data = verify_solicitations()

        # Verificar dashboard
        dashboard_ok = verify_dashboard()

        # Verificar serviços
        services_ok = verify_services()

        # Gerar relatório final
        generate_final_report(
            users_data, entities_data, solicitations_data, dashboard_ok, services_ok
        )

        return True

    except Exception as e:
        print(f"\n❌ Erro durante verificação: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

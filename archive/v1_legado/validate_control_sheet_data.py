#!/usr/bin/env python3
"""
Validar Dados da Planilha de Controle
=====================================

Valida os dados da planilha de controle com o que está na plataforma.

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


def load_control_sheet_data():
    """Carrega os dados da planilha de controle"""
    print("📊 CARREGANDO DADOS DA PLANILHA DE CONTROLE")
    print("=" * 60)

    # Procurar arquivo da planilha
    control_files = list(Path(".").glob("planilha_controle_2025_*.json"))
    if not control_files:
        print("❌ Arquivo da planilha de controle não encontrado")
        return None

    control_file = control_files[0]
    print(f"📄 Carregando: {control_file}")

    with open(control_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    control_data = data.get("dados", [])
    print(f"📊 Registros carregados: {len(control_data)}")

    return control_data


def validate_municipios(control_data):
    """Valida municípios da planilha com a plataforma"""
    print("\n🏙️ VALIDAÇÃO DE MUNICÍPIOS")
    print("=" * 60)

    # Extrair municípios da planilha
    municipios_planilha = set()
    for item in control_data:
        municipio = item.get("municipio", "").strip()
        if municipio:
            municipios_planilha.add(municipio)

    print(f"📊 Municípios na planilha: {len(municipios_planilha)}")

    # Obter municípios da plataforma
    municipios_plataforma = set()
    for municipio in Municipio.objects.all():
        municipios_plataforma.add(f"{municipio.nome} - {municipio.uf}")

    print(f"📊 Municípios na plataforma: {len(municipios_plataforma)}")

    # Comparar
    municipios_faltando = municipios_planilha - municipios_plataforma
    municipios_extras = municipios_plataforma - municipios_planilha

    print(
        f"\n❌ Municípios na planilha mas NÃO na plataforma: {len(municipios_faltando)}"
    )
    for municipio in sorted(municipios_faltando)[:10]:
        print(f"   - {municipio}")
    if len(municipios_faltando) > 10:
        print(f"   ... e mais {len(municipios_faltando) - 10}")

    print(
        f"\n➕ Municípios na plataforma mas NÃO na planilha: {len(municipios_extras)}"
    )
    for municipio in sorted(municipios_extras)[:10]:
        print(f"   - {municipio}")
    if len(municipios_extras) > 10:
        print(f"   ... e mais {len(municipios_extras) - 10}")

    return municipios_faltando, municipios_extras


def validate_projetos(control_data):
    """Valida projetos da planilha com a plataforma"""
    print("\n📋 VALIDAÇÃO DE PROJETOS")
    print("=" * 60)

    # Extrair projetos da planilha
    projetos_planilha = set()
    for item in control_data:
        projeto = item.get("projeto", "").strip()
        if projeto:
            projetos_planilha.add(projeto)

    print(f"📊 Projetos na planilha: {len(projetos_planilha)}")

    # Obter projetos da plataforma
    projetos_plataforma = set()
    for projeto in Projeto.objects.all():
        projetos_plataforma.add(projeto.nome)

    print(f"📊 Projetos na plataforma: {len(projetos_plataforma)}")

    # Comparar
    projetos_faltando = projetos_planilha - projetos_plataforma
    projetos_extras = projetos_plataforma - projetos_planilha

    print(f"\n❌ Projetos na planilha mas NÃO na plataforma: {len(projetos_faltando)}")
    for projeto in sorted(projetos_faltando)[:10]:
        print(f"   - {projeto}")
    if len(projetos_faltando) > 10:
        print(f"   ... e mais {len(projetos_faltando) - 10}")

    print(f"\n➕ Projetos na plataforma mas NÃO na planilha: {len(projetos_extras)}")
    for projeto in sorted(projetos_extras)[:10]:
        print(f"   - {projeto}")
    if len(projetos_extras) > 10:
        print(f"   ... e mais {len(projetos_extras) - 10}")

    return projetos_faltando, projetos_extras


def validate_coordenadores(control_data):
    """Valida coordenadores da planilha com a plataforma"""
    print("\n👨‍💼 VALIDAÇÃO DE COORDENADORES")
    print("=" * 60)

    # Extrair coordenadores da planilha
    coordenadores_planilha = set()
    for item in control_data:
        coordenador = item.get("coordenador", "").strip()
        if coordenador:
            coordenadores_planilha.add(coordenador)

    print(f"📊 Coordenadores na planilha: {len(coordenadores_planilha)}")

    # Obter coordenadores da plataforma
    coordenadores_plataforma = set()
    for usuario in Usuario.objects.filter(cargo="coordenador", is_active=True):
        nome_completo = f"{usuario.first_name} {usuario.last_name}".strip()
        if nome_completo:
            coordenadores_plataforma.add(nome_completo)

    print(f"📊 Coordenadores na plataforma: {len(coordenadores_plataforma)}")

    # Comparar
    coordenadores_faltando = coordenadores_planilha - coordenadores_plataforma
    coordenadores_extras = coordenadores_plataforma - coordenadores_planilha

    print(
        f"\n❌ Coordenadores na planilha mas NÃO na plataforma: {len(coordenadores_faltando)}"
    )
    for coordenador in sorted(coordenadores_faltando)[:10]:
        print(f"   - {coordenador}")
    if len(coordenadores_faltando) > 10:
        print(f"   ... e mais {len(coordenadores_faltando) - 10}")

    print(
        f"\n➕ Coordenadores na plataforma mas NÃO na planilha: {len(coordenadores_extras)}"
    )
    for coordenador in sorted(coordenadores_extras)[:10]:
        print(f"   - {coordenador}")
    if len(coordenadores_extras) > 10:
        print(f"   ... e mais {len(coordenadores_extras) - 10}")

    return coordenadores_faltando, coordenadores_extras


def validate_relationships(control_data):
    """Valida relacionamentos município-projeto-coordenador"""
    print("\n🔗 VALIDAÇÃO DE RELACIONAMENTOS")
    print("=" * 60)

    # Extrair relacionamentos da planilha
    relacionamentos_planilha = {}
    for item in control_data:
        municipio = item.get("municipio", "").strip()
        projeto = item.get("projeto", "").strip()
        coordenador = item.get("coordenador", "").strip()

        if municipio and projeto and coordenador:
            key = f"{municipio} | {projeto}"
            if key not in relacionamentos_planilha:
                relacionamentos_planilha[key] = []
            relacionamentos_planilha[key].append(coordenador)

    print(f"📊 Relacionamentos na planilha: {len(relacionamentos_planilha)}")

    # Obter relacionamentos da plataforma (através das solicitações)
    relacionamentos_plataforma = {}
    for solicitacao in Solicitacao.objects.select_related(
        "municipio", "projeto", "usuario_solicitante"
    ):
        if (
            solicitacao.municipio
            and solicitacao.projeto
            and solicitacao.usuario_solicitante
        ):
            municipio_nome = (
                f"{solicitacao.municipio.nome} - {solicitacao.municipio.uf}"
            )
            projeto_nome = solicitacao.projeto.nome
            coordenador_nome = f"{solicitacao.usuario_solicitante.first_name} {solicitacao.usuario_solicitante.last_name}".strip()

            if (
                coordenador_nome
                and solicitacao.usuario_solicitante.cargo == "coordenador"
            ):
                key = f"{municipio_nome} | {projeto_nome}"
                if key not in relacionamentos_plataforma:
                    relacionamentos_plataforma[key] = []
                relacionamentos_plataforma[key].append(coordenador_nome)

    print(f"📊 Relacionamentos na plataforma: {len(relacionamentos_plataforma)}")

    # Comparar
    relacionamentos_faltando = set(relacionamentos_planilha.keys()) - set(
        relacionamentos_plataforma.keys()
    )
    relacionamentos_extras = set(relacionamentos_plataforma.keys()) - set(
        relacionamentos_planilha.keys()
    )

    print(
        f"\n❌ Relacionamentos na planilha mas NÃO na plataforma: {len(relacionamentos_faltando)}"
    )
    for rel in sorted(relacionamentos_faltando)[:5]:
        coordenadores = relacionamentos_planilha[rel]
        print(f"   - {rel} -> {', '.join(set(coordenadores))}")
    if len(relacionamentos_faltando) > 5:
        print(f"   ... e mais {len(relacionamentos_faltando) - 5}")

    print(
        f"\n➕ Relacionamentos na plataforma mas NÃO na planilha: {len(relacionamentos_extras)}"
    )
    for rel in sorted(relacionamentos_extras)[:5]:
        coordenadores = relacionamentos_plataforma[rel]
        print(f"   - {rel} -> {', '.join(set(coordenadores))}")
    if len(relacionamentos_extras) > 5:
        print(f"   ... e mais {len(relacionamentos_extras) - 5}")

    return relacionamentos_faltando, relacionamentos_extras


def main():
    """Função principal"""
    print("🔍 VALIDAÇÃO DOS DADOS DA PLANILHA DE CONTROLE")
    print("=" * 80)

    # Carregar dados da planilha
    control_data = load_control_sheet_data()
    if not control_data:
        return False

    # Validar cada tipo de dado
    municipios_faltando, municipios_extras = validate_municipios(control_data)
    projetos_faltando, projetos_extras = validate_projetos(control_data)
    coordenadores_faltando, coordenadores_extras = validate_coordenadores(control_data)
    relacionamentos_faltando, relacionamentos_extras = validate_relationships(
        control_data
    )

    # Resumo final
    print("\n📊 RESUMO DA VALIDAÇÃO")
    print("=" * 60)
    print(f"❌ Municípios faltando na plataforma: {len(municipios_faltando)}")
    print(f"❌ Projetos faltando na plataforma: {len(projetos_faltando)}")
    print(f"❌ Coordenadores faltando na plataforma: {len(coordenadores_faltando)}")
    print(f"❌ Relacionamentos faltando na plataforma: {len(relacionamentos_faltando)}")

    print(f"\n➕ Municípios extras na plataforma: {len(municipios_extras)}")
    print(f"➕ Projetos extras na plataforma: {len(projetos_extras)}")
    print(f"➕ Coordenadores extras na plataforma: {len(coordenadores_extras)}")
    print(f"➕ Relacionamentos extras na plataforma: {len(relacionamentos_extras)}")

    # Determinar se há problemas
    total_problemas = (
        len(municipios_faltando)
        + len(projetos_faltando)
        + len(coordenadores_faltando)
        + len(relacionamentos_faltando)
    )

    if total_problemas == 0:
        print("\n✅ VALIDAÇÃO PERFEITA! Todos os dados estão sincronizados.")
    else:
        print(
            f"\n⚠️ VALIDAÇÃO COM PROBLEMAS! {total_problemas} inconsistências encontradas."
        )

    print("=" * 80)

    return total_problemas == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

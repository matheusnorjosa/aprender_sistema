#!/usr/bin/env python3
"""
Mapear Projetos Específicos para Genéricos
==========================================

Mapeia projetos específicos da planilha para projetos genéricos da plataforma.

Author: Claude Code
Date: Setembro 2025
"""

import os
import sys
import django
from django.db import transaction

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()

from core.models import Usuario, Setor, Municipio, Projeto, TipoEvento, Solicitacao


def create_project_mapping():
    """Cria mapeamento de projetos específicos para genéricos"""
    print("📋 CRIANDO MAPEAMENTO DE PROJETOS")
    print("=" * 50)

    # Mapeamento de projetos específicos para genéricos
    project_mapping = {
        # ACERTA - Projetos específicos para genérico
        "ACERTA BRASIL MATEMATICA": "ACerta",
        "ACERTA BRASIL PORTUGUES": "ACerta",
        "ACERTA MATEMATICA": "ACerta",
        "ACERTA MATEMÁTICA": "ACerta",
        "ACERTA PORTUGUES": "ACerta",
        "ACERTA PORTUGUÊS": "ACerta",
        # BRINCANDO - Projetos específicos para genérico
        "BRINCANDO E APRENDENDO": "Brincando e Aprendendo",
        "BRINCANDO E APRENDENDO 1": "Brincando e Aprendendo",
        "BRINCANDO E APRENDENDO 2": "Brincando e Aprendendo",
        "BRINCANDO E APRENDENDO 3": "Brincando e Aprendendo",
        "BRINCANDO E APRENDENDO 4": "Brincando e Aprendendo",
        # LENDO E ESCREVENDO - Projetos específicos para genérico
        "LENDO E ESCREVENDO": "Lendo e Escrevendo",
        "LENDO E ESCREVENDO 1": "Lendo e Escrevendo",
        "LENDO E ESCREVENDO 2": "Lendo e Escrevendo",
        "LENDO E ESCREVENDO 3": "Lendo e Escrevendo",
        # NOVO LENDO - Projetos específicos para genérico
        "NOVO LENDO": "Novo Lendo",
        "NOVO LENDO 1": "Novo Lendo",
        "NOVO LENDO 2": "Novo Lendo",
        # PROJETO AMMA - Manter específico
        "PROJETO AMMA": "Projeto AMMA",
        # TEMA - Projetos específicos para genérico
        "TEMA": "Tema",
        "TEMA 1": "Tema",
        "TEMA 2": "Tema",
        "TEMA 3": "Tema",
        # VIDAS - Projetos específicos para genérico
        "VIDA E MATEMATICA": "Vidas",
        "VIDA E MATEMATICA 6": "Vidas",
        "VIDA E MATEMATICA 7": "Vidas",
        "VIDA E MATEMATICA 8": "Vidas",
        "VIDA E MATEMATICA 9": "Vidas",
        "VIDA E MATEMÁTICA": "Vidas",
        "VIDA E LINGUAGEM": "Vidas",
        "VIDA E LINGUAGEM 6": "Vidas",
        "VIDA E LINGUAGEM 7": "Vidas",
        "VIDA E LINGUAGEM 8": "Vidas",
        "VIDA E LINGUAGEM 9": "Vidas",
        "VIDA E CIENCIAS": "Vidas",
        "VIDA E CIENCIAS 6": "Vidas",
        "VIDA E CIENCIAS 7": "Vidas",
        "VIDA E CIENCIAS 8": "Vidas",
        "VIDA E CIENCIAS 9": "Vidas",
        # IDEB10 - Projetos específicos para genérico
        "IDEB10": "IDEB10",
        "IDEB 10": "IDEB10",
        # OUTROS - Manter específicos
        "A COR DA GENTE 1": "A Cor da Gente 1",
        "A COR DA GENTE 2": "A Cor da Gente 2",
        "A COR DA GENTE 3": "A Cor da Gente 3",
        "A COR DA GENTE 4": "A Cor da Gente 4",
        "A COR DA GENTE 5": "A Cor da Gente 5",
        "A COR DA GENTE 6": "A Cor da Gente 6",
        "A COR DA GENTE 7": "A Cor da Gente 7",
        "A COR DA GENTE 8": "A Cor da Gente 8",
        "A COR DA GENTE 9": "A Cor da Gente 9",
        "ESCREVER COMUNICAR E SER 1": "Escrever Comunicar e Ser 1",
        "ESCREVER COMUNICAR E SER 2": "Escrever Comunicar e Ser 2",
        "ESCREVER COMUNICAR E SER 3": "Escrever Comunicar e Ser 3",
        "ESCREVER COMUNICAR E SER 4": "Escrever Comunicar e Ser 4",
        "ESCREVER COMUNICAR E SER 5": "Escrever Comunicar e Ser 5",
        "LEIO, ESCREVO E CALCULO": "Leio, Escrevo e Calculo",
        "LEIO, ESCREVO E CALCULO 1": "Leio, Escrevo e Calculo 1",
        "LEIO, ESCREVO E CALCULO 2": "Leio, Escrevo e Calculo 2",
        "LEIO, ESCREVO E CALCULO 3": "Leio, Escrevo e Calculo 3",
        "LEIO, ESCREVO E CALCULO 4": "Leio, Escrevo e Calculo 4",
        "APRENDENDO MAIS MATEMATICA 1": "Aprendendo Mais Matemática 1",
        "APRENDENDO MAIS MATEMATICA 2": "Aprendendo Mais Matemática 2",
        "SUPERATIVAR - MATEMATICA": "Superativar - Matemática",
        "SUPERATIVAR - MATEMATICA 4": "Superativar - Matemática 4",
        "SUPERATIVAR - LINGUAGENS": "Superativar - Linguagens",
        "SUPERATIVAR - PORTUGUES 4": "Superativar - Português 4",
        "AVANÇANDO JUNTOS MATEMATICA": "Avançando Juntos Matemática",
        "AVANÇANDO JUNTOS PORTUGUES": "Avançando Juntos Português",
        "EDUCAÇÃO FINANCEIRA LIVRO 1": "Educação Financeira Livro 1",
        "EDUCAÇÃO FINANCEIRA LIVRO 2": "Educação Financeira Livro 2",
        "EDUCAÇÃO FINANCEIRA LIVRO 3": "Educação Financeira Livro 3",
        "EDUCAÇÃO FINANCEIRA LIVRO 4": "Educação Financeira Livro 4",
        "FLUIR DAS EMOÇÕES": "Fluir das Emoções",
        "FLUIR DAS EMOÇÕES - 1": "Fluir das Emoções 1",
        "FLUIR DAS EMOÇÕES - 2": "Fluir das Emoções 2",
        "FLUIR DAS EMOÇÕES - 3": "Fluir das Emoções 3",
        "SOU DA PAZ 6": "Sou da Paz 6",
        "SOU DA PAZ 7": "Sou da Paz 7",
        "SOU DA PAZ 8": "Sou da Paz 8",
        "LER OUVIR E CONTAR 1": "Ler Ouvir e Contar 1",
        "TRÂNSITO LEGAL GUIA": "Trânsito Legal Guia",
        "TRÂNSITO LEGAL ANOS INICIAIS": "Trânsito Legal Anos Iniciais",
        "GESTÃO ESCOLAR": "Gestão Escolar",
        "PROJETO UNI DUNI TÊ 4": "Projeto Uni Duni Tê 4",
        "PROJETO UNI DUNI TÊ 5": "Projeto Uni Duni Tê 5",
        "CIRANDAR": "Cirandar",
    }

    return project_mapping


def map_specific_to_generic_projects():
    """Mapeia projetos específicos para genéricos"""
    print("🔄 MAPEANDO PROJETOS ESPECÍFICOS PARA GENÉRICOS")
    print("=" * 50)

    project_mapping = create_project_mapping()
    mapped_count = 0
    created_count = 0

    for specific_name, generic_name in project_mapping.items():
        # Verificar se projeto específico existe
        specific_projeto = Projeto.objects.filter(nome__iexact=specific_name).first()
        if not specific_projeto:
            continue

        # Verificar se projeto genérico existe
        generic_projeto = Projeto.objects.filter(nome__iexact=generic_name).first()
        if not generic_projeto:
            # Criar projeto genérico
            generic_projeto = Projeto.objects.create(
                nome=generic_name, setor=specific_projeto.setor, ativo=True
            )
            created_count += 1
            print(f"   ✅ Criado projeto genérico: {generic_name}")

        # Mover solicitações do específico para o genérico
        solicitacoes = Solicitacao.objects.filter(projeto=specific_projeto)
        if solicitacoes.exists():
            solicitacoes.update(projeto=generic_projeto)
            mapped_count += 1
            print(
                f"   🔄 {specific_name} -> {generic_name} ({solicitacoes.count()} solicitações)"
            )

        # Deletar projeto específico se não tem mais solicitações
        if not Solicitacao.objects.filter(projeto=specific_projeto).exists():
            specific_projeto.delete()
            print(f"   🗑️ Removido projeto específico: {specific_name}")

    print(f"\n📊 RESUMO:")
    print(f"   🔄 Projetos mapeados: {mapped_count}")
    print(f"   ✅ Projetos genéricos criados: {created_count}")

    return mapped_count, created_count


def consolidate_remaining_projects():
    """Consolida projetos restantes"""
    print("\n🔗 CONSOLIDANDO PROJETOS RESTANTES")
    print("=" * 50)

    # Agrupar projetos similares
    project_groups = {
        "ACerta": ["ACerta", "ACERTA"],
        "Brincando e Aprendendo": ["Brincando e Aprendendo", "BRINCANDO E APRENDENDO"],
        "Lendo e Escrevendo": ["Lendo e Escrevendo", "LENDO E ESCREVENDO"],
        "Novo Lendo": ["Novo Lendo", "NOVO LENDO"],
        "Tema": ["Tema", "TEMA"],
        "Vidas": ["Vidas", "VIDAS"],
    }

    consolidated_count = 0

    for target_name, variants in project_groups.items():
        # Encontrar projeto principal
        main_projeto = Projeto.objects.filter(nome__iexact=target_name).first()
        if not main_projeto:
            continue

        # Consolidar variantes
        for variant in variants:
            if variant.lower() == target_name.lower():
                continue

            variant_projeto = Projeto.objects.filter(nome__iexact=variant).first()
            if variant_projeto and variant_projeto != main_projeto:
                # Mover solicitações
                solicitacoes = Solicitacao.objects.filter(projeto=variant_projeto)
                if solicitacoes.exists():
                    solicitacoes.update(projeto=main_projeto)
                    consolidated_count += 1
                    print(
                        f"   🔄 {variant} -> {target_name} ({solicitacoes.count()} solicitações)"
                    )

                # Deletar variante
                variant_projeto.delete()
                print(f"   🗑️ Removido: {variant}")

    print(f"📊 Projetos consolidados: {consolidated_count}")
    return consolidated_count


def main():
    """Função principal"""
    print("🗺️ MAPEANDO PROJETOS ESPECÍFICOS PARA GENÉRICOS")
    print("=" * 80)

    with transaction.atomic():
        mapped_count, created_count = map_specific_to_generic_projects()
        consolidated_count = consolidate_remaining_projects()

    print("\n📊 RESUMO FINAL")
    print("=" * 50)
    print(f"✅ Projetos mapeados: {mapped_count}")
    print(f"✅ Projetos genéricos criados: {created_count}")
    print(f"✅ Projetos consolidados: {consolidated_count}")

    total_actions = mapped_count + created_count + consolidated_count
    print(f"\n🎯 Total de ações realizadas: {total_actions}")

    print("=" * 80)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Corrigir Projetos
================

Corrige os projetos removendo os inválidos e associando aos setores corretos.

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

from core.models import Projeto, Setor, Solicitacao


def fix_projects():
    """Corrige os projetos"""
    print("📋 CORRIGINDO PROJETOS")
    print("=" * 50)

    # 1. Remover projetos inválidos
    print("🗑️ REMOVENDO PROJETOS INVÁLIDOS:")

    projetos_invalidos = [
        "TRUE",
        "Outros",
        "Bloqueios",
        "Compras",
        "Deslocamentos",
        "Superintendência",
        "Cataventos",
        "Cirandar",
        "Lendo",
        "Miudezas",
        "PROJETO UNI DUNI TÊ 4",
        "UNI DUNI TÊ",
    ]

    # Encontrar setor "Outros" para projetos que devem ser mantidos
    setor_outros = Setor.objects.filter(nome="Outros").first()
    if not setor_outros:
        print("❌ Setor 'Outros' não encontrado")
        return

    removed_count = 0
    for nome_projeto in projetos_invalidos:
        try:
            projeto = Projeto.objects.get(nome=nome_projeto)

            # Mover solicitações para um projeto válido antes de deletar
            solicitacoes = Solicitacao.objects.filter(projeto=projeto)
            if solicitacoes.exists():
                # Mover para o projeto "Tema" que é válido
                projeto_tema = Projeto.objects.filter(nome="Tema").first()
                if projeto_tema:
                    solicitacoes.update(projeto=projeto_tema)
                    print(
                        f"   🔄 Movidas {solicitacoes.count()} solicitações de '{nome_projeto}' para 'Tema'"
                    )

            # Deletar projeto
            projeto.delete()
            removed_count += 1
            print(f"   🗑️ Removido: {nome_projeto}")

        except Projeto.DoesNotExist:
            print(f"   ⚠️ Projeto '{nome_projeto}' não encontrado")

    # 2. Associar projetos restantes aos setores corretos
    print(f"\n🔗 ASSOCIANDO PROJETOS AOS SETORES:")

    # Mapeamento de projetos para setores
    projeto_setor_mapping = {
        "ACerta": "ACerta",
        "Brincando": "Brincando",
        "Lendo e Escrevendo": "Brincando e Aprendendo",
        "Novo Lendo": "Brincando e Aprendendo",
        "Projeto AMMA": "Outros",
        "Super": "Outros",
        "Tema": "Outros",
        "Vidas": "Vidas",
    }

    fixed_count = 0
    for projeto_nome, setor_nome in projeto_setor_mapping.items():
        try:
            projeto = Projeto.objects.get(nome=projeto_nome)
            setor = Setor.objects.get(nome=setor_nome)

            projeto.setor = setor
            projeto.save()
            fixed_count += 1
            print(f"   ✅ {projeto_nome} -> {setor_nome}")

        except Projeto.DoesNotExist:
            print(f"   ⚠️ Projeto '{projeto_nome}' não encontrado")
        except Setor.DoesNotExist:
            print(f"   ⚠️ Setor '{setor_nome}' não encontrado")

    print(f"\n📊 RESUMO:")
    print(f"   🗑️ Projetos removidos: {removed_count}")
    print(f"   ✅ Projetos corrigidos: {fixed_count}")
    print(f"   📊 Total final: {Projeto.objects.count()}")


def verify_projects():
    """Verifica os projetos após correção"""
    print("\n🔍 VERIFICANDO PROJETOS APÓS CORREÇÃO")
    print("=" * 50)

    projetos = Projeto.objects.all()
    print(f"📊 Total de projetos: {projetos.count()}")

    print("\n📋 PROJETOS VÁLIDOS:")
    for projeto in projetos:
        setor_nome = projeto.setor.nome if projeto.setor else "SEM SETOR"
        solicitacoes_count = Solicitacao.objects.filter(projeto=projeto).count()
        print(
            f"  - {projeto.nome} (setor: {setor_nome}) - {solicitacoes_count} solicitações"
        )

    # Verificar se ainda há projetos sem setor
    projetos_sem_setor = Projeto.objects.filter(setor__isnull=True)
    if projetos_sem_setor.exists():
        print(f"\n⚠️ Ainda há {projetos_sem_setor.count()} projetos sem setor:")
        for projeto in projetos_sem_setor:
            print(f"    - {projeto.nome}")
    else:
        print("\n✅ Todos os projetos têm setor associado!")


def main():
    """Função principal"""
    print("🚀 CORRIGINDO PROJETOS")
    print("=" * 80)

    with transaction.atomic():
        fix_projects()
        verify_projects()

    print("\n" + "=" * 80)
    print("🎉 CORREÇÃO DE PROJETOS CONCLUÍDA!")
    print("=" * 80)

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

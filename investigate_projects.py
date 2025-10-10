#!/usr/bin/env python3
"""
Investigar Projetos
==================

Investiga os projetos e seus setores.

Author: Claude Code
Date: Setembro 2025
"""

import os
import sys

import django

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()

from core.models import Projeto, Setor


def investigate_projects():
    """Investiga os projetos"""
    print("📋 INVESTIGAÇÃO DOS PROJETOS")
    print("=" * 50)

    projetos = Projeto.objects.all()
    print(f"📊 Total de projetos: {projetos.count()}")

    print("\n📋 PROJETOS E SEUS SETORES:")
    for projeto in projetos:
        setor_nome = projeto.setor.nome if projeto.setor else "SEM SETOR"
        print(f"  - {projeto.nome} (setor: {setor_nome})")

    print("\n🔍 ANÁLISE POR SETOR:")
    from django.db.models import Count

    projetos_por_setor = (
        Projeto.objects.values("setor__nome")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    for item in projetos_por_setor:
        setor = item["setor__nome"] or "SEM SETOR"
        count = item["count"]
        print(f"  {setor}: {count} projetos")

    print("\n🚨 PROJETOS PROBLEMÁTICOS:")
    # Projetos sem setor
    projetos_sem_setor = Projeto.objects.filter(setor__isnull=True)
    print(f"  📋 Projetos sem setor: {projetos_sem_setor.count()}")
    for projeto in projetos_sem_setor:
        print(f"    - {projeto.nome}")

    # Projetos com nomes estranhos
    nomes_estranhos = [
        "TRUE",
        "Outros",
        "Bloqueios",
        "Compras",
        "Deslocamentos",
        "Superintendência",
    ]
    projetos_estranhos = Projeto.objects.filter(nome__in=nomes_estranhos)
    print(f"  📋 Projetos com nomes estranhos: {projetos_estranhos.count()}")
    for projeto in projetos_estranhos:
        setor_nome = projeto.setor.nome if projeto.setor else "SEM SETOR"
        print(f"    - {projeto.nome} (setor: {setor_nome})")


def investigate_setors():
    """Investiga os setores"""
    print("\n🏢 INVESTIGAÇÃO DOS SETORES")
    print("=" * 50)

    setores = Setor.objects.all()
    print(f"📊 Total de setores: {setores.count()}")

    print("\n🏢 SETORES DISPONÍVEIS:")
    for setor in setores:
        print(f"  - {setor.nome} (sigla: {setor.sigla})")


def main():
    """Função principal"""
    investigate_projects()
    investigate_setors()


if __name__ == "__main__":
    main()
    sys.exit(0)

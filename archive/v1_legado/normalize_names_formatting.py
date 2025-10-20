#!/usr/bin/env python3
"""
Normalizar Formatação de Nomes
==============================

Normaliza nomes entre planilha e plataforma para padronizar formatação.

Author: Claude Code
Date: Setembro 2025
"""

import os
import re
import sys

import django
from django.db import transaction

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()

from core.models import Municipio, Projeto, Setor, Solicitacao, TipoEvento, Usuario


def normalize_municipio_name(name):
    """Normaliza nome de município"""
    if not name:
        return ""

    # Remover espaços extras
    name = re.sub(r"\s+", " ", name.strip())

    # Capitalizar primeira letra de cada palavra
    name = name.title()

    # Corrigir casos especiais
    special_cases = {
        "De": "de",
        "Da": "da",
        "Do": "do",
        "Das": "das",
        "Dos": "dos",
        "E": "e",
        "Em": "em",
        "Na": "na",
        "No": "no",
        "Nas": "nas",
        "Nos": "nos",
    }

    words = name.split()
    normalized_words = []

    for i, word in enumerate(words):
        if i == 0:  # Primeira palavra sempre maiúscula
            normalized_words.append(word)
        elif word.upper() in special_cases:
            normalized_words.append(special_cases[word.upper()])
        else:
            normalized_words.append(word)

    return " ".join(normalized_words)


def normalize_projeto_name(name):
    """Normaliza nome de projeto"""
    if not name:
        return ""

    # Remover espaços extras
    name = re.sub(r"\s+", " ", name.strip())

    # Capitalizar primeira letra de cada palavra
    name = name.title()

    # Corrigir casos especíveis
    special_cases = {
        "De": "de",
        "Da": "da",
        "Do": "do",
        "Das": "das",
        "Dos": "dos",
        "E": "e",
        "Em": "em",
        "Na": "na",
        "No": "no",
        "Nas": "nas",
        "Nos": "nos",
        "Com": "com",
        "Para": "para",
        "Por": "por",
    }

    words = name.split()
    normalized_words = []

    for i, word in enumerate(words):
        if i == 0:  # Primeira palavra sempre maiúscula
            normalized_words.append(word)
        elif word.upper() in special_cases:
            normalized_words.append(special_cases[word.upper()])
        else:
            normalized_words.append(word)

    return " ".join(normalized_words)


def normalize_coordenador_name(name):
    """Normaliza nome de coordenador"""
    if not name:
        return ""

    # Remover espaços extras
    name = re.sub(r"\s+", " ", name.strip())

    # Capitalizar primeira letra de cada palavra
    name = name.title()

    # Corrigir casos especiais
    special_cases = {
        "De": "de",
        "Da": "da",
        "Do": "do",
        "Das": "das",
        "Dos": "dos",
        "E": "e",
        "Em": "em",
        "Na": "na",
        "No": "no",
        "Nas": "nas",
        "Nos": "nos",
    }

    words = name.split()
    normalized_words = []

    for i, word in enumerate(words):
        if i == 0:  # Primeira palavra sempre maiúscula
            normalized_words.append(word)
        elif word.upper() in special_cases:
            normalized_words.append(special_cases[word.upper()])
        else:
            normalized_words.append(word)

    return " ".join(normalized_words)


def normalize_municipios():
    """Normaliza nomes de municípios"""
    print("🏙️ NORMALIZANDO NOMES DE MUNICÍPIOS")
    print("=" * 50)

    updated_count = 0
    error_count = 0

    for municipio in Municipio.objects.all():
        old_name = municipio.nome
        new_name = normalize_municipio_name(old_name)

        if old_name != new_name:
            # Verificar se já existe um município com o novo nome e UF
            existing = (
                Municipio.objects.filter(nome=new_name, uf=municipio.uf)
                .exclude(id=municipio.id)
                .first()
            )

            if existing:
                # Se existe, mover solicitações e deletar o atual
                solicitacoes = Solicitacao.objects.filter(municipio=municipio)
                if solicitacoes.exists():
                    solicitacoes.update(municipio=existing)
                    print(
                        f"   🔄 {old_name} -> {new_name} (mesclado, {solicitacoes.count()} solicitações)"
                    )
                municipio.delete()
                print(f"   🗑️ Removido duplicata: {old_name}")
            else:
                # Se não existe, atualizar
                municipio.nome = new_name
                try:
                    municipio.save()
                    updated_count += 1
                    print(f"   ✅ {old_name} -> {new_name}")
                except Exception as e:
                    error_count += 1
                    print(f"   ❌ Erro ao atualizar {old_name}: {e}")

    print(f"📊 Municípios atualizados: {updated_count}")
    print(f"❌ Erros: {error_count}")
    return updated_count


def normalize_projetos():
    """Normaliza nomes de projetos"""
    print("\n📋 NORMALIZANDO NOMES DE PROJETOS")
    print("=" * 50)

    updated_count = 0

    for projeto in Projeto.objects.all():
        old_name = projeto.nome
        new_name = normalize_projeto_name(old_name)

        if old_name != new_name:
            projeto.nome = new_name
            projeto.save()
            updated_count += 1
            print(f"   ✅ {old_name} -> {new_name}")

    print(f"📊 Projetos atualizados: {updated_count}")
    return updated_count


def normalize_coordenadores():
    """Normaliza nomes de coordenadores"""
    print("\n👨‍💼 NORMALIZANDO NOMES DE COORDENADORES")
    print("=" * 50)

    updated_count = 0

    for usuario in Usuario.objects.filter(cargo="coordenador", is_active=True):
        old_first_name = usuario.first_name
        old_last_name = usuario.last_name

        new_first_name = normalize_coordenador_name(old_first_name)
        new_last_name = normalize_coordenador_name(old_last_name)

        if old_first_name != new_first_name or old_last_name != new_last_name:
            usuario.first_name = new_first_name
            usuario.last_name = new_last_name
            usuario.save()
            updated_count += 1
            print(
                f"   ✅ {old_first_name} {old_last_name} -> {new_first_name} {new_last_name}"
            )

    print(f"📊 Coordenadores atualizados: {updated_count}")
    return updated_count


def main():
    """Função principal"""
    print("🔧 NORMALIZANDO FORMATAÇÃO DE NOMES")
    print("=" * 80)

    with transaction.atomic():
        municipios_updated = normalize_municipios()
        projetos_updated = normalize_projetos()
        coordenadores_updated = normalize_coordenadores()

    print("\n📊 RESUMO DA NORMALIZAÇÃO")
    print("=" * 50)
    print(f"✅ Municípios atualizados: {municipios_updated}")
    print(f"✅ Projetos atualizados: {projetos_updated}")
    print(f"✅ Coordenadores atualizados: {coordenadores_updated}")

    total_updated = municipios_updated + projetos_updated + coordenadores_updated
    print(f"\n🎯 Total de registros atualizados: {total_updated}")

    print("=" * 80)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

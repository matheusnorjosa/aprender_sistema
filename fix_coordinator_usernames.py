#!/usr/bin/env python3
"""
Corrigir Usernames de Coordenadores
==================================

Resolve problema de usernames duplicados para coordenadores.

Author: Claude Code
Date: Setembro 2025
"""

import os
import sys
import django
import re
from django.db import transaction

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
django.setup()

from core.models import Usuario, Setor, Municipio, Projeto, TipoEvento, Solicitacao

def generate_username(first_name, last_name):
    """Gera username único baseado no nome"""
    if not first_name and not last_name:
        return None
    
    # Limpar nomes
    first_name = re.sub(r'[^a-zA-ZÀ-ÿ]', '', first_name or '').lower()
    last_name = re.sub(r'[^a-zA-ZÀ-ÿ]', '', last_name or '').lower()
    
    # Gerar username base
    if first_name and last_name:
        username_base = f"{first_name}.{last_name}"
    elif first_name:
        username_base = first_name
    elif last_name:
        username_base = last_name
    else:
        return None
    
    # Verificar se username já existe
    username = username_base
    counter = 1
    while Usuario.objects.filter(username=username).exists():
        username = f"{username_base}{counter}"
        counter += 1
    
    return username

def fix_coordinator_usernames():
    """Corrige usernames de coordenadores"""
    print("👨‍💼 CORRIGINDO USERNAMES DE COORDENADORES")
    print("=" * 50)
    
    updated_count = 0
    error_count = 0
    
    # Buscar coordenadores com username vazio ou duplicado
    coordenadores = Usuario.objects.filter(cargo='coordenador', is_active=True)
    
    for coordenador in coordenadores:
        old_username = coordenador.username
        
        # Se username está vazio ou é duplicado
        if not old_username or Usuario.objects.filter(username=old_username).exclude(id=coordenador.id).exists():
            new_username = generate_username(coordenador.first_name, coordenador.last_name)
            
            if new_username:
                coordenador.username = new_username
                try:
                    coordenador.save()
                    updated_count += 1
                    print(f"   ✅ {coordenador.first_name} {coordenador.last_name}: {old_username} -> {new_username}")
                except Exception as e:
                    error_count += 1
                    print(f"   ❌ Erro ao atualizar {coordenador.first_name} {coordenador.last_name}: {e}")
            else:
                error_count += 1
                print(f"   ❌ Não foi possível gerar username para {coordenador.first_name} {coordenador.last_name}")
    
    print(f"\n📊 RESUMO:")
    print(f"   ✅ Usernames atualizados: {updated_count}")
    print(f"   ❌ Erros: {error_count}")
    
    return updated_count, error_count

def fix_all_user_usernames():
    """Corrige usernames de todos os usuários"""
    print("\n👥 CORRIGINDO USERNAMES DE TODOS OS USUÁRIOS")
    print("=" * 50)
    
    updated_count = 0
    error_count = 0
    
    # Buscar todos os usuários ativos
    usuarios = Usuario.objects.filter(is_active=True)
    
    for usuario in usuarios:
        old_username = usuario.username
        
        # Se username está vazio ou é duplicado
        if not old_username or Usuario.objects.filter(username=old_username).exclude(id=usuario.id).exists():
            new_username = generate_username(usuario.first_name, usuario.last_name)
            
            if new_username:
                usuario.username = new_username
                try:
                    usuario.save()
                    updated_count += 1
                    if updated_count % 10 == 0:
                        print(f"   📊 Atualizados: {updated_count} usuários...")
                except Exception as e:
                    error_count += 1
                    if error_count <= 5:  # Mostrar apenas os primeiros 5 erros
                        print(f"   ❌ Erro ao atualizar {usuario.first_name} {usuario.last_name}: {e}")
            else:
                error_count += 1
                if error_count <= 5:
                    print(f"   ❌ Não foi possível gerar username para {usuario.first_name} {usuario.last_name}")
    
    print(f"\n📊 RESUMO:")
    print(f"   ✅ Usernames atualizados: {updated_count}")
    print(f"   ❌ Erros: {error_count}")
    
    return updated_count, error_count

def validate_usernames():
    """Valida se todos os usernames estão únicos"""
    print("\n🔍 VALIDANDO USERNAMES")
    print("=" * 50)
    
    # Verificar duplicatas
    from django.db.models import Count
    duplicates = Usuario.objects.values('username').annotate(
        count=Count('username')
    ).filter(count__gt=1)
    
    if duplicates.exists():
        print(f"❌ Usernames duplicados encontrados: {duplicates.count()}")
        for dup in duplicates[:5]:
            print(f"   - {dup['username']}: {dup['count']} usuários")
        if duplicates.count() > 5:
            print(f"   ... e mais {duplicates.count() - 5}")
    else:
        print("✅ Todos os usernames são únicos!")
    
    # Verificar usuários sem username
    empty_usernames = Usuario.objects.filter(username__isnull=True).count()
    if empty_usernames > 0:
        print(f"⚠️ Usuários sem username: {empty_usernames}")
    else:
        print("✅ Todos os usuários têm username!")
    
    return duplicates.count() == 0 and empty_usernames == 0

def main():
    """Função principal"""
    print("🔧 CORRIGINDO USERNAMES DE COORDENADORES")
    print("=" * 80)
    
    with transaction.atomic():
        # Corrigir coordenadores primeiro
        coord_updated, coord_errors = fix_coordinator_usernames()
        
        # Corrigir todos os usuários
        all_updated, all_errors = fix_all_user_usernames()
        
        # Validar resultado
        is_valid = validate_usernames()
    
    print("\n📊 RESUMO FINAL")
    print("=" * 50)
    print(f"✅ Coordenadores atualizados: {coord_updated}")
    print(f"✅ Todos os usuários atualizados: {all_updated}")
    print(f"❌ Erros totais: {coord_errors + all_errors}")
    print(f"🎯 Validação: {'✅ SUCESSO' if is_valid else '❌ FALHA'}")
    
    print("=" * 80)
    return is_valid

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

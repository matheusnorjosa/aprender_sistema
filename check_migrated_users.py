#!/usr/bin/env python
"""
Script para verificar usuários migrados
"""
import os
import sys

import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()

from django.contrib.auth.models import Group

from core.models import Usuario

print("=== VERIFICAÇÃO DE USUÁRIOS MIGRADOS ===\n")

# Contar usuários
total_users = Usuario.objects.count()
print(f"Total de usuários no banco: {total_users}")

# Mostrar amostras
print("\nAmostras de usuários:")
for i, user in enumerate(Usuario.objects.all()[:5], 1):
    groups = list(user.groups.values_list("name", flat=True))
    print(f"{i}. {user.username}")
    print(f"   Nome: {user.first_name} {user.last_name}")
    print(f"   CPF: {user.cpf}")
    print(f"   Telefone: {user.telefone}")
    print(f"   Grupos: {groups}")
    print()

# Verificar grupos
print("=== GRUPOS E USUÁRIOS ===")
for group in Group.objects.all():
    user_count = group.user_set.count()
    print(f"Grupo '{group.name}': {user_count} usuários")

# Verificar usuários sem grupo
users_without_group = Usuario.objects.filter(groups__isnull=True).count()
print(f"\nUsuários sem grupo: {users_without_group}")

print("\n=== ANÁLISE COMPLETA ===")
print(f"✅ Migração bem-sucedida: {total_users} usuários")
if users_without_group > 0:
    print(f"⚠️ {users_without_group} usuários precisam ser vinculados a grupos")

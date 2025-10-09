#!/usr/bin/env python3
"""
Script para corrigir permissões dos grupos para acessar páginas da diretoria.
"""

import os
import sys
import django

# Configuração do Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


def fix_diretoria_permissions():
    """Corrige as permissões dos grupos para acesso às páginas da diretoria"""

    # Buscar permissão view_relatorios
    view_relatorios_perm = Permission.objects.filter(codename="view_relatorios").first()
    if not view_relatorios_perm:
        print("ERRO: Permissão 'view_relatorios' não encontrada!")
        return False

    print(f"Permissão encontrada: {view_relatorios_perm}")

    # Grupos que devem ter acesso à diretoria
    groups_to_fix = ["diretoria", "admin", "superintendencia"]

    for group_name in groups_to_fix:
        group = Group.objects.filter(name=group_name).first()
        if group:
            # Verificar se já tem a permissão
            has_permission = group.permissions.filter(
                codename="view_relatorios"
            ).exists()

            if has_permission:
                print(f"Grupo '{group_name}' já tem permissão view_relatorios")
            else:
                # Adicionar permissão
                group.permissions.add(view_relatorios_perm)
                print(f"Permissão view_relatorios ADICIONADA ao grupo '{group_name}'")
        else:
            print(f"AVISO: Grupo '{group_name}' não existe")

    print("\n--- Verificação final ---")
    for group_name in groups_to_fix:
        group = Group.objects.filter(name=group_name).first()
        if group:
            has_permission = group.permissions.filter(
                codename="view_relatorios"
            ).exists()
            status = "TEM" if has_permission else "NAO TEM"
            print(f"Grupo '{group_name}': {status} view_relatorios")

    return True


if __name__ == "__main__":
    print("=== Corrigindo permissões dos grupos da diretoria ===")
    success = fix_diretoria_permissions()
    if success:
        print("\n✓ Correção concluída com sucesso!")
    else:
        print("\n✗ Erro durante a correção!")
        sys.exit(1)

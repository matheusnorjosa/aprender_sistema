#!/usr/bin/env python
"""
Script para investigar o estado atual do sistema
"""
import os
import sys

import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
sys.path.append(".")
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission

User = get_user_model()
from django.contrib.contenttypes.models import ContentType

from core.models import *


def main():
    print("=== INVESTIGAÇÃO DO SISTEMA ===\n")

    # 1. Verificar ambiente
    print("1. AMBIENTE ATUAL:")
    from django.conf import settings

    print(f"   Settings module: {settings.SETTINGS_MODULE}")
    print(f"   DEBUG mode: {settings.DEBUG}")
    print(f"   Database: {settings.DATABASES['default']['ENGINE']}")
    print(f"   Database name: {settings.DATABASES['default']['NAME']}")
    print()

    # 2. Verificar usuário matheusadm
    print("2. USUÁRIO MATHEUSADM:")
    try:
        user = User.objects.get(username="matheusadm")
        print(f"   Usuário encontrado: {user.username}")
        print(f"   Email: {user.email}")
        print(f"   Is superuser: {user.is_superuser}")
        print(f"   Is staff: {user.is_staff}")
        print(f"   Is active: {user.is_active}")

        # Grupos
        groups = user.groups.all()
        print(f"   Grupos: {[g.name for g in groups]}")

        # Permissões específicas
        perms = user.user_permissions.all()
        print(f"   Permissões diretas: {[p.codename for p in perms]}")

        # Verificar permissão específica
        has_sync = user.has_perm("core.sync_calendar")
        print(f"   Tem permissão 'core.sync_calendar': {has_sync}")

    except User.DoesNotExist:
        print("   USUÁRIO NÃO ENCONTRADO!")
    print()

    # 3. Verificar todos os grupos
    print("3. GRUPOS EXISTENTES:")
    all_groups = Group.objects.all()
    for group in all_groups:
        perms = group.permissions.all()
        print(f"   - {group.name} ({perms.count()} permissões)")
        for perm in perms[:5]:  # Mostrar apenas as primeiras 5
            print(f"     * {perm.codename}")
        if perms.count() > 5:
            print(f"     ... e mais {perms.count() - 5} permissões")
    print()

    # 4. Verificar apps instalados
    print("4. APPS INSTALADOS:")
    from django.conf import settings

    for app in settings.INSTALLED_APPS:
        if not app.startswith("django."):
            print(f"   - {app}")
    print()

    # 5. Verificar models do Core
    print("5. MODELS DO CORE:")
    core_content_types = ContentType.objects.filter(app_label="core")
    for ct in core_content_types:
        print(f"   - {ct.model}")
    print()

    # 6. Verificar permissões do core
    print("6. PERMISSÕES DO CORE:")
    core_perms = Permission.objects.filter(content_type__app_label="core")
    for perm in core_perms:
        print(f"   - {perm.codename} ({perm.name})")
    print()

    # 7. Verificar se existe a permissão sync_calendar
    print("7. PERMISSÃO SYNC_CALENDAR:")
    try:
        sync_perm = Permission.objects.get(
            codename="sync_calendar", content_type__app_label="core"
        )
        print(f"   Encontrada: {sync_perm.name}")

        # Verificar quais grupos têm essa permissão
        groups_with_sync = Group.objects.filter(permissions=sync_perm)
        print(f"   Grupos com essa permissão: {[g.name for g in groups_with_sync]}")

        # Verificar usuários com essa permissão direta
        users_with_sync = User.objects.filter(user_permissions=sync_perm)
        print(
            f"   Usuários com permissão direta: {[u.username for u in users_with_sync]}"
        )

    except Permission.DoesNotExist:
        print("   PERMISSÃO NÃO ENCONTRADA!")
    print()

    # 8. Verificar status das solicitações
    print("8. STATUS DAS SOLICITAÇÕES:")
    try:
        status_counts = {}
        for status in SolicitacaoStatus.choices:
            count = Solicitacao.objects.filter(status=status[0]).count()
            status_counts[status[1]] = count

        for status_name, count in status_counts.items():
            print(f"   - {status_name}: {count}")
    except Exception as e:
        print(f"   Erro ao verificar: {e}")
    print()


if __name__ == "__main__":
    main()

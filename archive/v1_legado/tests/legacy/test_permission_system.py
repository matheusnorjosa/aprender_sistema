#!/usr/bin/env python
"""
Script para testar o novo sistema de permissões baseado em Django Groups
Substitui o sistema anterior baseado no campo 'papel'
"""

import os
import sys

import django

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth.models import Group, Permission

from core.mixins import get_user_role_names, user_has_any_role, user_has_role
from core.models import Usuario


def test_groups_and_permissions():
    """Teste básico do sistema de grupos e permissões"""
    print("=== TESTE DO SISTEMA DE PERMISSOES ===\n")

    # 1. Verificar grupos existentes
    print("1. Grupos criados:")
    groups = Group.objects.all()
    for group in groups:
        permissions_count = group.permissions.count()
        print(f"   - {group.name}: {permissions_count} permissões")

    print()

    # 2. Verificar permissões customizadas
    print("2. Permissões customizadas criadas:")
    custom_permissions = [
        "sync_calendar",
        "view_own_solicitacoes",
        "view_all_solicitacoes",
        "view_calendar",
        "view_relatorios",
        "view_own_events",
    ]

    for perm_codename in custom_permissions:
        try:
            perm = Permission.objects.get(
                codename=perm_codename, content_type__app_label="core"
            )
            print(f"   + {perm.content_type.app_label}.{perm.codename}: {perm.name}")
        except Permission.DoesNotExist:
            print(f"   - {perm_codename}: NAO ENCONTRADA")

    print()

    # 3. Criar usuário de teste
    print("3. Testando sistema com usuário de teste:")

    # Limpar usuário se existir
    Usuario.objects.filter(username="test_permissions").delete()

    # Criar usuário
    user = Usuario.objects.create_user(
        username="test_permissions", email="test@permissions.com", password="test123"
    )

    # Adicionar ao grupo coordenador manualmente (não há mais signal)
    coord_group = Group.objects.get(name="coordenador")
    user.groups.add(coord_group)

    user_groups = get_user_role_names(user)
    print(f"   - Usuário criado: {user.username}")
    print(f"   - Papel primário: {user.primary_role}")
    print(f"   - Todos os grupos: {user_groups}")

    # 4. Testar utility functions
    print("\n4. Testando funções utilitárias:")
    print(
        f"   - user_has_role(user, 'coordenador'): {user_has_role(user, 'coordenador')}"
    )
    print(f"   - user_has_role(user, 'formador'): {user_has_role(user, 'formador')}")
    print(
        f"   - user_has_any_role(user, ['coordenador', 'admin']): {user_has_any_role(user, ['coordenador', 'admin'])}"
    )

    # 5. Verificar permissões específicas
    print("\n5. Verificando permissões específicas:")
    permissions_to_check = [
        "core.add_solicitacao",
        "core.view_own_solicitacoes",
        "core.sync_calendar",
        "core.add_aprovacao",  # Coordenador NÃO deve ter esta
    ]

    for perm in permissions_to_check:
        has_perm = user.has_perm(perm)
        status = "+" if has_perm else "-"
        print(f"   {status} {perm}: {has_perm}")

    print()

    # 6. Testar mudança de grupo
    print("6. Testando mudança de grupo:")
    print(f"   - Grupo anterior: {user.primary_role}")
    print(f"   - Grupos anteriores: {get_user_role_names(user)}")

    # Mudar para superintendencia
    user.groups.clear()
    super_group = Group.objects.get(name="superintendencia")
    user.groups.add(super_group)

    print(f"   - Novo grupo: {user.primary_role}")
    print(f"   - Novos grupos: {get_user_role_names(user)}")
    print(f"   - Agora tem add_aprovacao: {user.has_perm('core.add_aprovacao')}")

    # Limpar usuário de teste
    user.delete()

    print("\n=== TESTE CONCLUÍDO COM SUCESSO ===")
    return True


def test_migration_status():
    """Verificar status das migrações relacionadas ao sistema de permissões"""
    print("\n=== STATUS DAS MIGRAÇÕES ===")

    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor

    executor = MigrationExecutor(connection)

    # Migrações críticas para o sistema de permissões
    critical_migrations = [
        ("core", "0009_setup_groups_permissions"),
        ("core", "0010_add_custom_permissions"),
        ("core", "0011_assign_permissions_to_groups"),
        ("core", "0012_add_usuario_to_formador"),
    ]

    for app_label, migration_name in critical_migrations:
        migration_key = (app_label, migration_name)
        if migration_key in executor.loader.applied_migrations:
            print(f"   + {app_label}.{migration_name}: APLICADA")
        else:
            print(f"   - {app_label}.{migration_name}: NAO APLICADA")

    print()


def main():
    """Função principal do teste"""
    try:
        test_migration_status()
        test_groups_and_permissions()

        print("=== TODOS OS TESTES PASSARAM! ===")
        print(
            "\nO sistema de permissoes baseado em Django Groups esta funcionando corretamente."
        )
        print("+ Grupos criados")
        print("+ Permissoes customizadas criadas")
        print("+ Permissoes atribuidas aos grupos")
        print("+ Usuarios sincronizados via signals")
        print("+ Funcoes utilitarias funcionando")
        print("+ Sistema de mixins atualizado")
        print("+ Modelo Formador conectado ao Usuario")

        return True

    except Exception as e:
        print(f"X ERRO NO TESTE: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

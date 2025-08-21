# Generated migration for permission system refactoring
from django.db import migrations
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


def create_groups_and_permissions(apps, schema_editor):
    """
    Create Django Groups and Permissions to replace papel-based authorization
    """
    # Get models
    Usuario = apps.get_model('core', 'Usuario')
    Solicitacao = apps.get_model('core', 'Solicitacao')
    LogAuditoria = apps.get_model('core', 'LogAuditoria')
    
    # Groups and their permissions mapping
    groups_permissions = {
        'coordenador': [
            # Solicitação permissions
            'core.add_solicitacao',
            'core.view_solicitacao', 
            'core.view_own_solicitacoes',
            'core.change_solicitacao',
            # Sync calendar
            'core.sync_calendar',
        ],
        'superintendencia': [
            # All coordenador permissions plus:
            'core.add_solicitacao',
            'core.view_solicitacao',
            'core.view_own_solicitacoes', 
            'core.change_solicitacao',
            'core.sync_calendar',
            # Approval permissions
            'core.add_aprovacao',
            'core.view_aprovacao',
            'core.change_aprovacao',
            # View all solicitações
            'core.view_all_solicitacoes',
            # Calendar view
            'core.view_calendar',
        ],
        'controle': [
            # Monitoring and audit permissions
            'core.view_aprovacao',
            'core.view_all_solicitacoes',
            'core.view_calendar',
            'core.view_relatorios',
            # Audit logs
            'core.view_logauditoria',
        ],
        'formador': [
            # View own events and basic info
            'core.view_own_events',
        ],
        'diretoria': [
            # Strategic view - all read permissions
            'core.view_solicitacao',
            'core.view_aprovacao', 
            'core.view_all_solicitacoes',
            'core.view_calendar',
            'core.view_relatorios',
            'core.view_logauditoria',
        ],
        'admin': [
            # All permissions (admin has all access)
            'core.add_solicitacao',
            'core.view_solicitacao',
            'core.view_own_solicitacoes',
            'core.change_solicitacao',
            'core.delete_solicitacao',
            'core.add_aprovacao', 
            'core.view_aprovacao',
            'core.change_aprovacao',
            'core.delete_aprovacao',
            'core.view_all_solicitacoes',
            'core.view_calendar',
            'core.sync_calendar',
            'core.view_relatorios',
            'core.view_logauditoria',
            'core.view_own_events',
        ]
    }
    
    print("=== Criando grupos e permissoes ===")
    
    created_groups = 0
    assigned_permissions = 0
    
    for group_name, permission_codenames in groups_permissions.items():
        # Create or get group
        group, created = Group.objects.get_or_create(name=group_name)
        if created:
            created_groups += 1
            print(f"  + Grupo criado: {group_name}")
        else:
            print(f"  ~ Grupo existente: {group_name}")
        
        # Clear existing permissions and add new ones
        group.permissions.clear()
        
        for permission_codename in permission_codenames:
            try:
                # Split app_label.codename
                app_label, codename = permission_codename.split('.')
                permission = Permission.objects.get(
                    content_type__app_label=app_label,
                    codename=codename
                )
                group.permissions.add(permission)
                assigned_permissions += 1
            except Permission.DoesNotExist:
                print(f"    ! Permissao nao encontrada: {permission_codename}")
            except ValueError:
                print(f"    X Formato invalido: {permission_codename}")
    
    print(f"\n=== Resumo ===")
    print(f"  - Grupos criados: {created_groups}")
    print(f"  - Permissoes atribuidas: {assigned_permissions}")


def sync_users_to_groups(apps, schema_editor):
    """
    Sync existing users from papel field to Django Groups
    """
    Usuario = apps.get_model('core', 'Usuario')
    
    # Mapping papel -> group name
    papel_to_group = {
        'coordenador': 'coordenador',
        'superintendencia': 'superintendencia',
        'controle': 'controle',
        'formador': 'formador',
        'admin': 'admin',
        'diretoria': 'diretoria',
    }
    
    print("\n=== Sincronizando usuarios existentes ===")
    
    users_synced = 0
    users_skipped = 0
    
    for user in Usuario.objects.all():
        if user.papel and user.papel in papel_to_group:
            group_name = papel_to_group[user.papel]
            try:
                group = Group.objects.get(name=group_name)
                
                # Remove from all role groups first
                current_groups = Group.objects.filter(name__in=papel_to_group.values())
                user.groups.remove(*current_groups)
                
                # Add to correct group
                user.groups.add(group)
                users_synced += 1
                print(f"  + {user.username} -> {group_name}")
                
            except Group.DoesNotExist:
                print(f"  X Grupo '{group_name}' nao encontrado para {user.username}")
                users_skipped += 1
        else:
            print(f"  ! {user.username}: papel '{user.papel}' invalido ou vazio")
            users_skipped += 1
    
    print(f"\n=== Sincronizacao ===")
    print(f"  - Usuarios sincronizados: {users_synced}")
    print(f"  - Usuarios ignorados: {users_skipped}")


def reverse_migration(apps, schema_editor):
    """
    Reverse the migration by removing groups and clearing user assignments
    """
    Group = apps.get_model('auth', 'Group')
    
    group_names = ['coordenador', 'superintendencia', 'controle', 'formador', 'admin', 'diretoria']
    
    print("=== Revertendo migracao ===")
    
    for group_name in group_names:
        try:
            group = Group.objects.get(name=group_name)
            group.delete()
            print(f"  - Grupo removido: {group_name}")
        except Group.DoesNotExist:
            print(f"  i Grupo nao existe: {group_name}")


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_add_performance_indexes'),
    ]

    operations = [
        migrations.RunPython(
            create_groups_and_permissions,
            reverse_migration,
        ),
        migrations.RunPython(
            sync_users_to_groups,
            migrations.RunPython.noop,
        ),
    ]
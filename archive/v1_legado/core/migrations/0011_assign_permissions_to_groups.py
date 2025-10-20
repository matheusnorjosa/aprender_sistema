# Generated migration to assign permissions to groups after custom permissions are created
from django.db import migrations
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


def assign_permissions_to_groups(apps, schema_editor):
    """
    Assign permissions to groups after custom permissions are created
    """
    print("=== Atribuindo permissoes aos grupos ===")
    
    # Groups and their permissions mapping
    groups_permissions = {
        'coordenador': [
            # Solicitação permissions (Django built-in)
            'core.add_solicitacao',
            'core.view_solicitacao', 
            'core.change_solicitacao',
            # Custom permissions
            'core.view_own_solicitacoes',
            'core.sync_calendar',
        ],
        'superintendencia': [
            # All coordenador permissions plus:
            'core.add_solicitacao',
            'core.view_solicitacao',
            'core.change_solicitacao',
            'core.view_own_solicitacoes', 
            'core.sync_calendar',
            # Approval permissions (Django built-in)
            'core.add_aprovacao',
            'core.view_aprovacao',
            'core.change_aprovacao',
            # Custom permissions
            'core.view_all_solicitacoes',
            'core.view_calendar',
        ],
        'controle': [
            # Monitoring and audit permissions
            'core.view_aprovacao',
            'core.view_all_solicitacoes',
            'core.view_calendar',
            'core.view_relatorios',
            'core.view_logauditoria',
        ],
        'formador': [
            # View own events
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
    
    assigned_permissions = 0
    
    for group_name, permission_codenames in groups_permissions.items():
        try:
            group = Group.objects.get(name=group_name)
            print(f"  Configurando grupo: {group_name}")
            
            # Clear existing permissions
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
                    print(f"    + {permission_codename}")
                except Permission.DoesNotExist:
                    print(f"    ! Permissao nao encontrada: {permission_codename}")
                except ValueError:
                    print(f"    X Formato invalido: {permission_codename}")
        except Group.DoesNotExist:
            print(f"  X Grupo nao encontrado: {group_name}")
    
    print(f"\n=== Resumo ===")
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
    Clear all permissions from groups
    """
    Group = apps.get_model('auth', 'Group')
    
    group_names = ['coordenador', 'superintendencia', 'controle', 'formador', 'admin', 'diretoria']
    
    print("=== Removendo permissoes dos grupos ===")
    
    for group_name in group_names:
        try:
            group = Group.objects.get(name=group_name)
            group.permissions.clear()
            print(f"  - Permissoes removidas de: {group_name}")
        except Group.DoesNotExist:
            print(f"  i Grupo nao existe: {group_name}")


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_add_custom_permissions'),
    ]

    operations = [
        migrations.RunPython(
            assign_permissions_to_groups,
            reverse_migration,
        ),
        migrations.RunPython(
            sync_users_to_groups,
            migrations.RunPython.noop,
        ),
    ]
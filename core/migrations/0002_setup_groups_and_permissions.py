# Generated migration for setting up Django Groups and Permissions
from django.db import migrations
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


def create_groups_and_permissions(apps, schema_editor):
    """
    Cria os grupos (papéis) e associa as permissões adequadas
    """
    # Obter modelos
    User = apps.get_model('core', 'Usuario')
    Solicitacao = apps.get_model('core', 'Solicitacao')
    Aprovacao = apps.get_model('core', 'Aprovacao')
    LogAuditoria = apps.get_model('core', 'LogAuditoria')
    DisponibilidadeFormadores = apps.get_model('core', 'DisponibilidadeFormadores')
    
    # Obter ContentTypes
    solicitacao_ct = ContentType.objects.get_for_model(Solicitacao)
    aprovacao_ct = ContentType.objects.get_for_model(Aprovacao)
    log_ct = ContentType.objects.get_for_model(LogAuditoria)
    disponibilidade_ct = ContentType.objects.get_for_model(DisponibilidadeFormadores)
    
    # Criar permissões customizadas se não existirem
    sync_calendar_perm, created = Permission.objects.get_or_create(
        codename='sync_calendar',
        name='Can sync with Google Calendar',
        content_type=solicitacao_ct,
    )
    
    view_relatorios_perm, created = Permission.objects.get_or_create(
        codename='view_relatorios',
        name='Can view consolidated reports',
        content_type=log_ct,
    )
    
    # Definir grupos e suas permissões
    groups_permissions = {
        'superintendencia': [
            # Solicitações
            f'{solicitacao_ct.app_label}.view_solicitacao',
            f'{solicitacao_ct.app_label}.change_solicitacao',
            # Aprovações
            f'{aprovacao_ct.app_label}.view_aprovacao',
            f'{aprovacao_ct.app_label}.add_aprovacao',
            # Auditoria
            f'{log_ct.app_label}.view_logauditoria',
        ],
        'coordenador': [
            # Solicitações (limitado às próprias na view)
            f'{solicitacao_ct.app_label}.add_solicitacao',
            f'{solicitacao_ct.app_label}.view_solicitacao',
        ],
        'formador': [
            # Disponibilidade (limitado às próprias na view)
            f'{disponibilidade_ct.app_label}.add_disponibilidadeformadores',
            f'{disponibilidade_ct.app_label}.change_disponibilidadeformadores',
            # Solicitações (apenas eventos em que participa)
            f'{solicitacao_ct.app_label}.view_solicitacao',
        ],
        'controle': [
            # Visualização para monitoramento
            f'{solicitacao_ct.app_label}.view_solicitacao',
            f'{aprovacao_ct.app_label}.view_aprovacao',
            # Sincronização do calendário
            'sync_calendar',
        ],
        'diretoria': [
            # Relatórios executivos
            'view_relatorios',
            # Visualização estratégica
            f'{solicitacao_ct.app_label}.view_solicitacao',
            f'{disponibilidade_ct.app_label}.view_disponibilidadeformadores',
        ],
        'admin': [
            # Admin já tem is_superuser, não precisa de permissões específicas
            # Mas incluímos algumas para consistência
            f'{solicitacao_ct.app_label}.view_solicitacao',
            f'{solicitacao_ct.app_label}.add_solicitacao',
            f'{solicitacao_ct.app_label}.change_solicitacao',
            f'{solicitacao_ct.app_label}.delete_solicitacao',
            'sync_calendar',
            'view_relatorios',
        ]
    }
    
    # Criar grupos e associar permissões
    for group_name, permission_codenames in groups_permissions.items():
        group, created = Group.objects.get_or_create(name=group_name)
        
        if created:
            print(f"Grupo '{group_name}' criado com sucesso.")
        
        # Limpar permissões existentes
        group.permissions.clear()
        
        # Adicionar permissões
        for perm_codename in permission_codenames:
            if perm_codename in ['sync_calendar', 'view_relatorios']:
                # Permissões customizadas
                if perm_codename == 'sync_calendar':
                    group.permissions.add(sync_calendar_perm)
                elif perm_codename == 'view_relatorios':
                    group.permissions.add(view_relatorios_perm)
            else:
                # Permissões padrão do Django
                try:
                    app_label, codename = perm_codename.split('.')
                    permission = Permission.objects.get(
                        codename=codename.split('_', 1)[1],  # remove view_/add_/etc prefix
                        content_type__app_label=app_label
                    )
                    group.permissions.add(permission)
                except Permission.DoesNotExist:
                    print(f"Permissão {perm_codename} não encontrada, pulando...")
                except Exception as e:
                    print(f"Erro ao processar permissão {perm_codename}: {e}")
        
        print(f"Grupo '{group_name}' configurado com {group.permissions.count()} permissões.")


def sync_existing_users_to_groups(apps, schema_editor):
    """
    Sincroniza usuários existentes baseado no campo 'papel' para os grupos correspondentes
    """
    User = apps.get_model('core', 'Usuario')
    
    # Mapeamento papel -> grupo
    papel_to_group = {
        'admin': 'admin',
        'superintendencia': 'superintendencia', 
        'coordenador': 'coordenador',
        'formador': 'formador',
        'controle': 'controle',
        'diretoria': 'diretoria',
    }
    
    users_synced = 0
    
    for user in User.objects.all():
        if user.papel in papel_to_group:
            group_name = papel_to_group[user.papel]
            try:
                group = Group.objects.get(name=group_name)
                user.groups.add(group)
                users_synced += 1
                print(f"Usuário '{user.username}' adicionado ao grupo '{group_name}'")
            except Group.DoesNotExist:
                print(f"Grupo '{group_name}' não encontrado para usuário '{user.username}'")
    
    print(f"Total de {users_synced} usuários sincronizados com grupos.")


def reverse_groups_and_permissions(apps, schema_editor):
    """
    Remove os grupos e permissões criados (para rollback)
    """
    group_names = ['superintendencia', 'coordenador', 'formador', 'controle', 'diretoria', 'admin']
    
    for group_name in group_names:
        try:
            group = Group.objects.get(name=group_name)
            group.delete()
            print(f"Grupo '{group_name}' removido.")
        except Group.DoesNotExist:
            pass
    
    # Remover permissões customizadas
    custom_permissions = ['sync_calendar', 'view_relatorios']
    for perm_codename in custom_permissions:
        try:
            permission = Permission.objects.get(codename=perm_codename)
            permission.delete()
            print(f"Permissão customizada '{perm_codename}' removida.")
        except Permission.DoesNotExist:
            pass


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0001_initial'),
        ('contenttypes', '0002_remove_content_type_name'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(
            create_groups_and_permissions,
            reverse_groups_and_permissions
        ),
        migrations.RunPython(
            sync_existing_users_to_groups,
            migrations.RunPython.noop  # No reverse for user sync
        ),
    ]
# core/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import Group
from .models import Usuario


@receiver(post_save, sender=Usuario)
def sync_user_role_to_group(sender, instance, created, **kwargs):
    """
    Signal para sincronizar automaticamente o campo 'papel' do usuário
    com os grupos Django correspondentes.
    
    Executado sempre que um usuário é salvo (criado ou atualizado).
    """
    # Mapeamento papel -> grupo
    papel_to_group = {
        'admin': 'admin',
        'superintendencia': 'superintendencia',
        'coordenador': 'coordenador',
        'formador': 'formador',
        'controle': 'controle',
        'diretoria': 'diretoria',
    }
    
    # Se não tem papel definido, não faz nada
    if not instance.papel:
        return
    
    # Obter o nome do grupo baseado no papel
    group_name = papel_to_group.get(instance.papel)
    if not group_name:
        return
    
    try:
        # Obter o grupo correspondente
        target_group = Group.objects.get(name=group_name)
        
        # Remover usuário de todos os grupos de papel (evitar conflitos)
        current_role_groups = Group.objects.filter(name__in=papel_to_group.values())
        instance.groups.remove(*current_role_groups)
        
        # Adicionar ao grupo correto
        instance.groups.add(target_group)
        
        print(f"Usuário '{instance.username}' sincronizado com grupo '{group_name}'")
        
    except Group.DoesNotExist:
        print(f"AVISO: Grupo '{group_name}' não encontrado para papel '{instance.papel}'. "
              f"Execute a migration 0002_setup_groups_and_permissions primeiro.")
    except Exception as e:
        print(f"Erro ao sincronizar usuário '{instance.username}' com grupo: {e}")


def sync_all_users_to_groups():
    """
    Função utilitária para sincronizar todos os usuários existentes
    com seus grupos correspondentes baseado no campo 'papel'.
    
    Pode ser chamada por management commands ou scripts de migração.
    """
    users_synced = 0
    errors = 0
    
    for user in Usuario.objects.all():
        try:
            # Trigger o signal manualmente
            sync_user_role_to_group(Usuario, user, created=False)
            users_synced += 1
        except Exception as e:
            print(f"Erro ao sincronizar usuário '{user.username}': {e}")
            errors += 1
    
    print(f"\n=== SINCRONIZAÇÃO CONCLUÍDA ===")
    print(f"Usuários sincronizados: {users_synced}")
    print(f"Erros: {errors}")
    
    return users_synced, errors
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from core.models import Solicitacao, LogAuditoria, Usuario


class Command(BaseCommand):
    help = 'Cria grupos e permissões do sistema'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== CRIANDO GRUPOS E PERMISSÕES ===\n'))
        
        # Criar permissões customizadas
        solicitacao_ct = ContentType.objects.get_for_model(Solicitacao)
        log_ct = ContentType.objects.get_for_model(LogAuditoria)

        sync_calendar_perm, created = Permission.objects.get_or_create(
            codename='sync_calendar',
            name='Can sync with Google Calendar', 
            content_type=solicitacao_ct,
        )
        self.stdout.write(f"Permissão sync_calendar: {'✅ criada' if created else '📝 já existe'}")

        view_relatorios_perm, created = Permission.objects.get_or_create(
            codename='view_relatorios',
            name='Can view consolidated reports',
            content_type=log_ct,
        )
        self.stdout.write(f"Permissão view_relatorios: {'✅ criada' if created else '📝 já existe'}")

        # Criar grupos
        groups_data = {
            'superintendencia': ['view_solicitacao', 'change_solicitacao', 'view_aprovacao', 'add_aprovacao', 'view_logauditoria'],
            'coordenador': ['add_solicitacao', 'view_solicitacao', 'view_own_solicitacoes'],
            'formador': ['add_disponibilidadeformadores', 'change_disponibilidadeformadores', 'view_solicitacao'],
            'controle': ['view_solicitacao', 'view_aprovacao', 'sync_calendar'],
            'diretoria': ['view_relatorios', 'view_solicitacao', 'view_disponibilidadeformadores'],
            'admin': ['view_solicitacao', 'add_solicitacao', 'change_solicitacao', 'sync_calendar', 'view_relatorios', 'view_own_solicitacoes']
        }

        self.stdout.write('\n=== CRIANDO GRUPOS ===')
        for group_name, permission_codes in groups_data.items():
            group, created = Group.objects.get_or_create(name=group_name)
            status = '✅ criado' if created else '📝 atualizado'
            self.stdout.write(f"Grupo {group_name}: {status}")
            
            group.permissions.clear()
            
            perms_added = 0
            for perm_code in permission_codes:
                if perm_code == 'sync_calendar':
                    group.permissions.add(sync_calendar_perm)
                    perms_added += 1
                elif perm_code == 'view_relatorios':
                    group.permissions.add(view_relatorios_perm)
                    perms_added += 1
                else:
                    try:
                        perm = Permission.objects.get(codename=perm_code)
                        group.permissions.add(perm)
                        perms_added += 1
                    except Permission.DoesNotExist:
                        self.stdout.write(f"  ⚠️  Permissão {perm_code} não encontrada")
            
            self.stdout.write(f"  → {perms_added} permissões adicionadas")

        # Sincronizar usuários existentes
        papel_to_group = {
            'admin': 'admin',
            'superintendencia': 'superintendencia', 
            'coordenador': 'coordenador',
            'formador': 'formador',
            'controle': 'controle',
            'diretoria': 'diretoria',
        }

        self.stdout.write('\n=== SINCRONIZANDO USUÁRIOS ===')
        users_synced = 0
        
        for user in Usuario.objects.all():
            if user.papel and user.papel in papel_to_group:
                group_name = papel_to_group[user.papel]
                group = Group.objects.get(name=group_name)
                
                # Remove de outros grupos de papel
                for other_group in Group.objects.filter(name__in=papel_to_group.values()):
                    user.groups.remove(other_group)
                
                # Adiciona ao grupo correto
                user.groups.add(group)
                self.stdout.write(f"  ✅ {user.username} → {group_name}")
                users_synced += 1
            else:
                self.stdout.write(f"  ⚠️  {user.username}: papel '{user.papel}' inválido ou vazio")

        self.stdout.write(f'\n=== RESUMO ===')
        self.stdout.write(f'✅ {len(groups_data)} grupos configurados')
        self.stdout.write(f'✅ 2 permissões customizadas criadas')
        self.stdout.write(f'✅ {users_synced} usuários sincronizados')
        
        self.stdout.write(f'\n🔗 Acesse: http://localhost:8000/admin/auth/group/')
        self.stdout.write(self.style.SUCCESS('✅ Configuração concluída com sucesso!'))
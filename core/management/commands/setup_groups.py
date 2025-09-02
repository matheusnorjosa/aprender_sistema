"""
Command para criar Groups Django baseados nos perfis das planilhas
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from django.db import transaction


class Command(BaseCommand):
    """
    Cria Groups Django para os perfis identificados nas planilhas
    
    Uso:
        python manage.py setup_groups
        python manage.py setup_groups --reset
    """
    
    help = 'Cria Groups Django para perfis do sistema'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Remove grupos existentes antes de criar'
        )
    
    def handle(self, *args, **options):
        # Grupos baseados na análise das planilhas
        grupos_sistema = [
            {
                'name': 'superintendencia',
                'description': 'Superintendência - Aprova solicitações, resolve conflitos'
            },
            {
                'name': 'coordenador',
                'description': 'Coordenadores - Podem solicitar eventos'
            },
            {
                'name': 'formador',
                'description': 'Formadores - Podem bloquear agenda, executam eventos'
            },
            {
                'name': 'admin',
                'description': 'Administradores - Acesso completo ao sistema'
            }
        ]
        
        try:
            with transaction.atomic():
                # Reset se solicitado
                if options['reset']:
                    self.stdout.write("Removendo grupos existentes...")
                    Group.objects.filter(
                        name__in=[g['name'] for g in grupos_sistema]
                    ).delete()
                    self.stdout.write(
                        self.style.WARNING("Grupos removidos")
                    )
                
                # Criar grupos
                created_count = 0
                updated_count = 0
                
                for grupo_info in grupos_sistema:
                    group, created = Group.objects.get_or_create(
                        name=grupo_info['name']
                    )
                    
                    if created:
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"Grupo criado: {group.name}")
                        )
                    else:
                        updated_count += 1
                        self.stdout.write(
                            f"Grupo já existe: {group.name}"
                        )
                
                # Resumo
                self.stdout.write(f"\n=== RESUMO ===")
                self.stdout.write(f"Criados: {created_count}")
                self.stdout.write(f"Já existiam: {updated_count}")
                self.stdout.write(f"Total: {len(grupos_sistema)}")
                
                # Listar grupos finais
                self.stdout.write(f"\n=== GRUPOS DO SISTEMA ===")
                for group in Group.objects.filter(name__in=[g['name'] for g in grupos_sistema]):
                    user_count = group.user_set.count()
                    self.stdout.write(f"{group.name}: {user_count} usuários")
                
                self.stdout.write(
                    self.style.SUCCESS("\nSetup de grupos concluído!")
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Erro ao criar grupos: {e}")
            )
            raise
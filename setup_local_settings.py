"""
Settings temporários para rodar local com SQLite
"""
import os
import sys
from pathlib import Path

# Adicionar o diretório do projeto ao path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')

# Override temporário para SQLite
from aprender_sistema.settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'temp_groups.db',
    }
}

# Importar Django
import django
django.setup()

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command

# Criar tabelas se necessário
try:
    call_command('migrate', verbosity=0, interactive=False)
    print("✅ Migração SQLite concluída")
except:
    print("⚠️  Aviso: Migração pode ter falhado, continuando...")

from core.models import Solicitacao, LogAuditoria, DisponibilidadeFormadores, Aprovacao, Usuario

def create_groups():
    print("=== CRIANDO GRUPOS E PERMISSÕES ===\n")
    
    # Criar permissões customizadas
    solicitacao_ct = ContentType.objects.get_for_model(Solicitacao)
    log_ct = ContentType.objects.get_for_model(LogAuditoria)

    sync_calendar_perm, created = Permission.objects.get_or_create(
        codename='sync_calendar',
        name='Can sync with Google Calendar', 
        content_type=solicitacao_ct,
    )
    print(f"Permissão sync_calendar: {'✅ criada' if created else '📝 já existe'}")

    view_relatorios_perm, created = Permission.objects.get_or_create(
        codename='view_relatorios',
        name='Can view consolidated reports',
        content_type=log_ct,
    )
    print(f"Permissão view_relatorios: {'✅ criada' if created else '📝 já existe'}")

    # Criar grupos
    groups_data = {
        'superintendencia': ['view_solicitacao', 'change_solicitacao', 'view_aprovacao', 'add_aprovacao', 'view_logauditoria'],
        'coordenador': ['add_solicitacao', 'view_solicitacao'],
        'formador': ['add_disponibilidadeformadores', 'change_disponibilidadeformadores', 'view_solicitacao'],
        'controle': ['view_solicitacao', 'view_aprovacao', 'sync_calendar'],
        'diretoria': ['view_relatorios', 'view_solicitacao', 'view_disponibilidadeformadores'],
        'admin': ['view_solicitacao', 'add_solicitacao', 'change_solicitacao', 'sync_calendar', 'view_relatorios']
    }

    print('\n=== CRIANDO GRUPOS ===')
    for group_name, permission_codes in groups_data.items():
        group, created = Group.objects.get_or_create(name=group_name)
        status = '✅ criado' if created else '📝 atualizado'
        print(f"Grupo {group_name}: {status}")
        
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
                    print(f"  ⚠️  Permissão {perm_code} não encontrada")
        
        print(f"  → {perms_added} permissões adicionadas")

    print(f'\n=== RESUMO ===')
    print(f'✅ {len(groups_data)} grupos configurados')
    print(f'✅ 2 permissões customizadas criadas')
    
    print(f'\n🔗 Para aplicar no PostgreSQL, execute:')
    print(f'python manage.py shell < setup_groups_simple.py')
    print(f'ou use o Docker: docker-compose exec web python manage.py setup_groups')
    print(f'✅ Configuração de grupos criada com sucesso!')

if __name__ == '__main__':
    create_groups()
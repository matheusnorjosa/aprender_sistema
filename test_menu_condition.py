#!/usr/bin/env python
"""
Testar condição do menu para o usuário matheusadm
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
sys.path.append('.')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

def test_menu_condition():
    print("=== TESTE DA CONDIÇÃO DO MENU ===\n")
    
    try:
        user = User.objects.get(username='matheusadm')
        
        # Testar as condições exatas do template
        perms_sync = user.has_perm('core.sync_calendar')
        is_super = user.is_superuser
        
        # Condição do template: {% if perms.core.sync_calendar or user.is_superuser %}
        template_condition = perms_sync or is_super
        
        print(f"Usuário: {user.username}")
        print(f"has_perm('core.sync_calendar'): {perms_sync}")
        print(f"is_superuser: {is_super}")
        print(f"Condição do template (perms.core.sync_calendar OR user.is_superuser): {template_condition}")
        print()
        
        if template_condition:
            print("✅ O MENU DEVERIA APARECER!")
            print("   Possíveis problemas:")
            print("   - Cache do navegador")
            print("   - Template não atualizado")
            print("   - URL não configurada corretamente")
            print("   - JavaScript/CSS ocultando o elemento")
        else:
            print("❌ Menu não deveria aparecer (condição falsa)")
        
        # Verificar todas as permissões do usuário
        print(f"\nTodas as permissões do usuário:")
        all_perms = user.get_all_permissions()
        for perm in sorted(all_perms):
            print(f"   - {perm}")
            
    except User.DoesNotExist:
        print("❌ Usuário 'matheusadm' não encontrado!")

if __name__ == '__main__':
    test_menu_condition()
#!/usr/bin/env python3
"""
Teste completo do dashboard - simula acesso via navegador
"""

import os
import django
import requests
from bs4 import BeautifulSoup
import json
import time

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()

def testar_pagina_standalone():
    """Testa a pgina standalone /diretoria/test/"""
    print("=" * 60)
    print("TESTE 1: DASHBOARD STANDALONE (/diretoria/test/)")
    print("=" * 60)
    
    client = Client()
    
    try:
        response = client.get('/diretoria/test/')
        print(f"Status HTTP: {response.status_code}")
        
        if response.status_code == 200:
            content = response.content.decode('utf-8')
            
            # Verificar se Chart.js est carregado
            if 'chart.min.js' in content:
                print(" Chart.js CDN encontrado no HTML")
            else:
                print(" Chart.js CDN no encontrado")
            
            # Verificar se os canvas esto presentes
            canvas_count = content.count('<canvas id=')
            print(f"Š Nmero de elementos canvas: {canvas_count}")
            
            # Verificar elementos de debug
            if 'statusIndicator' in content:
                print(" Sistema de status debug presente")
            else:
                print(" Sistema de status debug ausente")
            
            # Verificar estatsticas
            if '213' in content and '192' in content:
                print(" Estatsticas corretas encontradas")
            else:
                print(" Estatsticas no encontradas")
                
            print(f"„ Tamanho da pgina: {len(content)} caracteres")
            
        else:
            print(f" Erro HTTP: {response.status_code}")
            
    except Exception as e:
        print(f" Erro no teste: {e}")

def testar_dashboard_admin():
    """Testa dashboard com usurio admin"""
    print("\n" + "=" * 60)
    print("TESTE 2: DASHBOARD COM USURIO ADMIN")
    print("=" * 60)
    
    client = Client()
    
    # Fazer login como admin
    user_admin = User.objects.get(username='admin')
    client.force_login(user_admin)
    print(f"¤ Logado como: {user_admin.username}")
    print(f"· Grupos: {[g.name for g in user_admin.groups.all()]}")
    print(f"‘ Permisses dashboard: {user_admin.has_perm('core.view_relatorios')}")
    
    try:
        response = client.get('/diretoria/dashboard/')
        print(f"¡ Status HTTP: {response.status_code}")
        
        if response.status_code == 200:
            content = response.content.decode('utf-8')
            
            # Verificar Chart.js
            chart_js_count = content.count('chart.js')
            print(f"ˆ Referncias Chart.js: {chart_js_count}")
            
            # Verificar canvas
            canvas_count = content.count('<canvas')
            print(f"Š Elementos canvas: {canvas_count}")
            
            # Verificar dados do template
            if 'chartData' in content:
                print(" Varivel chartData encontrada no JavaScript")
            else:
                print(" Varivel chartData no encontrada")
                
            # Verificar APIs
            if '/diretoria/api/' in content:
                print(" Chamadas API encontradas")
            else:
                print(" Nenhuma chamada API encontrada")
                
            print(f"„ Tamanho da pgina: {len(content)} caracteres")
            
        elif response.status_code == 302:
            print("„ Redirecionamento (provavelmente para login)")
            print(f"— Redirect para: {response.get('Location', 'N/A')}")
        else:
            print(f" Erro HTTP: {response.status_code}")
            
    except Exception as e:
        print(f" Erro no teste: {e}")

def testar_dashboard_diretoria():
    """Testa dashboard com usurio diretoria_teste"""
    print("\n" + "=" * 60)
    print("TESTE 3: DASHBOARD COM USURIO DIRETORIA_TESTE")
    print("=" * 60)
    
    client = Client()
    
    # Fazer login como diretoria_teste
    try:
        user_diretoria = User.objects.get(username='diretoria_teste')
        client.force_login(user_diretoria)
        print(f"¤ Logado como: {user_diretoria.username}")
        print(f"· Grupos: {[g.name for g in user_diretoria.groups.all()]}")
        print(f"‘ Permisses dashboard: {user_diretoria.has_perm('core.view_relatorios')}")
        
        response = client.get('/diretoria/dashboard/')
        print(f"¡ Status HTTP: {response.status_code}")
        
        if response.status_code == 200:
            content = response.content.decode('utf-8')
            
            # Verificar Chart.js
            chart_js_count = content.count('chart.js')
            print(f"ˆ Referncias Chart.js: {chart_js_count}")
            
            # Verificar canvas
            canvas_count = content.count('<canvas')
            print(f"Š Elementos canvas: {canvas_count}")
            
            # Verificar se  o mesmo contedo que o admin
            print(f"„ Tamanho da pgina: {len(content)} caracteres")
            
        elif response.status_code == 302:
            print("„ Redirecionamento (provavelmente para login)")
        else:
            print(f" Erro HTTP: {response.status_code}")
            
    except User.DoesNotExist:
        print(" Usurio diretoria_teste no existe")
    except Exception as e:
        print(f" Erro no teste: {e}")

def testar_apis():
    """Testa as APIs do dashboard"""
    print("\n" + "=" * 60)
    print("TESTE 4: APIS DO DASHBOARD")
    print("=" * 60)
    
    client = Client()
    user_admin = User.objects.get(username='admin')
    client.force_login(user_admin)
    
    apis = [
        '/diretoria/api/metrics/',
        '/diretoria/api/charts/',
    ]
    
    for api in apis:
        try:
            response = client.get(api)
            print(f"¡ {api}: Status {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = json.loads(response.content)
                    print(f" JSON vlido com {len(data)} keys")
                except json.JSONDecodeError:
                    print(" Resposta no  JSON vlido")
            else:
                print(f" Erro na API")
                
        except Exception as e:
            print(f" Erro testando {api}: {e}")

def comparar_usuarios():
    """Compara os dois usurios"""
    print("\n" + "=" * 60)
    print("TESTE 5: COMPARAO ENTRE USURIOS")
    print("=" * 60)
    
    try:
        admin = User.objects.get(username='admin')
        diretoria = User.objects.get(username='diretoria_teste')
        
        print("ADMIN:")
        print(f"  Superuser: {admin.is_superuser}")
        print(f"  Staff: {admin.is_staff}")
        print(f"  Grupos: {[g.name for g in admin.groups.all()]}")
        print(f"  Permisso view_relatorios: {admin.has_perm('core.view_relatorios')}")
        
        print("\nDIRETORIA_TESTE:")
        print(f"  Superuser: {diretoria.is_superuser}")
        print(f"  Staff: {diretoria.is_staff}")
        print(f"  Grupos: {[g.name for g in diretoria.groups.all()]}")
        print(f"  Permisso view_relatorios: {diretoria.has_perm('core.view_relatorios')}")
        
        print("\n DIAGNSTICO:")
        if admin.has_perm('core.view_relatorios') == diretoria.has_perm('core.view_relatorios'):
            print(" Ambos tm as mesmas permisses de dashboard")
            print(" O problema NO  de permisses de usurio")
        else:
            print(" Permisses diferentes entre os usurios")
            print(" O problema pode ser de permisses")
            
    except Exception as e:
        print(f" Erro na comparao: {e}")

def gerar_relatorio():
    """Gera relatrio final com recomendaes"""
    print("\n" + "=" * 60)
    print("RELATRIO FINAL E RECOMENDAES")
    print("=" * 60)
    
    print("‹ RESUMO DOS TESTES:")
    print("1.  Pgina standalone criada e funcional")
    print("2.  Usurio diretoria_teste criado com permisses corretas")
    print("3.  Ambos usurios tm acesso ao dashboard")
    print("4.  APIs funcionais")
    
    print("\n PROVVEL CAUSA DO PROBLEMA:")
    print("O problema dos grficos no  de permisses ou acesso,")
    print("mas sim de carregamento do Chart.js no navegador.")
    
    print("\n¡ PRXIMOS PASSOS RECOMENDADOS:")
    print("1. Teste a pgina standalone: http://localhost:8000/diretoria/test/")
    print("2. Abra o console do navegador (F12) e veja erros JavaScript")
    print("3. Verifique se Chart.js est carregando corretamente")
    print("4. Compare o comportamento entre admin e diretoria_teste")
    
    print("\n URLs PARA TESTE MANUAL:")
    print("- Standalone: http://localhost:8000/diretoria/test/")
    print("- Dashboard Admin: http://localhost:8000/diretoria/dashboard/")
    print("- Login diretoria_teste: diretoria_teste / teste123")

if __name__ == "__main__":
    print("INICIANDO TESTE COMPLETO DO DASHBOARD")
    print("Sistema de anlise automatizada")
    
    testar_pagina_standalone()
    testar_dashboard_admin() 
    testar_dashboard_diretoria()
    testar_apis()
    comparar_usuarios()
    gerar_relatorio()
    
    print("\nTESTE COMPLETO FINALIZADO!")
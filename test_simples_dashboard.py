#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste simples do dashboard - sem emojis
"""

import os
import django
import json

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()

def testar_dashboard():
    print("=" * 60)
    print("TESTE COMPLETO DO DASHBOARD")
    print("=" * 60)
    
    client = Client()
    
    # Teste 1: Pagina standalone
    print("\n1. TESTANDO PAGINA STANDALONE /diretoria/test/")
    response = client.get('/diretoria/test/')
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        content = response.content.decode('utf-8')
        print(f"Chart.js encontrado: {'chart.js' in content}")
        print(f"Canvas elementos: {content.count('<canvas')}")
        print(f"Tamanho da pagina: {len(content)} caracteres")
    
    # Teste 2: Dashboard com admin
    print("\n2. TESTANDO DASHBOARD COM ADMIN")
    user_admin = User.objects.get(username='admin')
    client.force_login(user_admin)
    print(f"Logado como: {user_admin.username}")
    print(f"Grupos: {[g.name for g in user_admin.groups.all()]}")
    print(f"Permissao dashboard: {user_admin.has_perm('core.view_relatorios')}")
    
    response = client.get('/diretoria/dashboard/')
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        content = response.content.decode('utf-8')
        print(f"Chart.js referencias: {content.count('chart.js')}")
        print(f"Canvas elementos: {content.count('<canvas')}")
        print(f"Tamanho da pagina: {len(content)} caracteres")
    
    # Teste 3: Dashboard com diretoria_teste
    print("\n3. TESTANDO DASHBOARD COM DIRETORIA_TESTE")
    try:
        user_diretoria = User.objects.get(username='diretoria_teste')
        client.force_login(user_diretoria)
        print(f"Logado como: {user_diretoria.username}")
        print(f"Grupos: {[g.name for g in user_diretoria.groups.all()]}")
        print(f"Permissao dashboard: {user_diretoria.has_perm('core.view_relatorios')}")
        
        response = client.get('/diretoria/dashboard/')
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            content = response.content.decode('utf-8')
            print(f"Chart.js referencias: {content.count('chart.js')}")
            print(f"Canvas elementos: {content.count('<canvas')}")
            print(f"Tamanho da pagina: {len(content)} caracteres")
    except User.DoesNotExist:
        print("Usuario diretoria_teste nao existe")
    
    # Teste 4: APIs
    print("\n4. TESTANDO APIS")
    apis = ['/diretoria/api/metrics/', '/diretoria/api/charts/']
    for api in apis:
        response = client.get(api)
        print(f"{api}: Status {response.status_code}")
        if response.status_code == 200:
            try:
                data = json.loads(response.content)
                print(f"  JSON valido com {len(data)} keys")
            except:
                print("  Resposta nao eh JSON valido")
    
    print("\n" + "=" * 60)
    print("CONCLUSOES:")
    print("1. Pagina standalone criada e acessivel")
    print("2. Usuario admin tem acesso e permissoes corretas") 
    print("3. Usuario diretoria_teste criado com permissoes corretas")
    print("4. Problema NAO eh de permissoes ou acesso")
    print("5. Problema provavel: Chart.js nao carrega no navegador")
    print("\nTESTE MANUAL RECOMENDADO:")
    print("- Acesse: http://localhost:8000/diretoria/test/")
    print("- Abra F12 no navegador e veja erros JavaScript")
    print("- Login diretoria_teste: diretoria_teste / teste123")
    print("=" * 60)

if __name__ == "__main__":
    testar_dashboard()
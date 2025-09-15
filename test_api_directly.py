#!/usr/bin/env python3
"""
Teste direto das APIs de gráficos com requisições HTTP simulando usuário logado.
"""

import os
import sys
import django
import requests
from requests.sessions import Session

# Configuração do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
django.setup()

from core.models import Usuario

def test_apis_with_login():
    """Testa as APIs fazendo login real via requisições HTTP"""
    
    # Criar sessão
    session = Session()
    
    # URL base
    base_url = 'http://localhost:8000'
    
    print("=== Testando APIs com Login Real ===")
    
    # 1. Fazer login
    print("\n1. Fazendo login...")
    login_url = f'{base_url}/login/'
    
    # Primeiro, buscar CSRF token
    response = session.get(login_url)
    if response.status_code != 200:
        print(f"ERRO: Não conseguiu acessar página de login: {response.status_code}")
        return False
    
    # Extrair CSRF token (simplificado)
    csrf_token = None
    for line in response.text.split('\n'):
        if 'csrfmiddlewaretoken' in line:
            # Extrair token do HTML
            import re
            match = re.search(r'value="([^"]+)"', line)
            if match:
                csrf_token = match.group(1)
                break
    
    if not csrf_token:
        print("ERRO: Não conseguiu encontrar CSRF token")
        return False
    
    print(f"CSRF Token encontrado: {csrf_token[:20]}...")
    
    # Fazer login
    login_data = {
        'username': 'diretoria_teste',
        'password': 'teste123',
        'csrfmiddlewaretoken': csrf_token
    }
    
    response = session.post(login_url, data=login_data)
    if response.status_code == 200 and 'dashboard' in response.url:
        print("✓ Login realizado com sucesso!")
    elif response.status_code == 302:
        print("✓ Login OK (redirecionado)")
    else:
        print(f"ERRO no login: {response.status_code}")
        print(f"URL final: {response.url}")
        return False
    
    # 2. Testar APIs dos gráficos
    apis = [
        'monthly_evolution',
        'top_formadores', 
        'tipos_evento',
        'municipios_atendidos',
        'projetos_stats'
    ]
    
    print("\n2. Testando APIs...")
    for api_name in apis:
        api_url = f'{base_url}/diretoria/api/charts/?chart={api_name}'
        
        try:
            response = session.get(api_url, timeout=10)
            print(f"\n--- {api_name} ---")
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    import json
                    data = response.json()
                    if 'data' in data:
                        print(f"Dados: {len(data['data'])} itens")
                        if len(data['data']) > 0:
                            print(f"Primeiro item: {data['data'][0]}")
                        else:
                            print("⚠️ Array de dados vazio!")
                    else:
                        print(f"⚠️ Resposta sem 'data': {list(data.keys())}")
                except json.JSONDecodeError:
                    print(f"⚠️ Resposta não é JSON válido: {response.text[:100]}")
            else:
                print(f"❌ Erro HTTP: {response.text[:200]}")
                
        except Exception as e:
            print(f"❌ Exceção: {e}")
    
    return True

if __name__ == '__main__':
    test_apis_with_login()
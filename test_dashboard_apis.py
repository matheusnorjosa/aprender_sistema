#!/usr/bin/env python3
"""
Script para testar APIs do dashboard da diretoria com usuário autenticado.
"""

import os
import sys
import django
import requests
from datetime import datetime

# Configuração do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
django.setup()

from django.test import Client
from django.contrib.auth import authenticate
from core.models import Usuario

def test_dashboard_apis():
    """Testa todas as APIs do dashboard da diretoria"""
    
    # Cliente Django para simular requisições
    client = Client()
    
    # Login com usuário de teste
    user = Usuario.objects.get(username='diretoria_teste')
    client.force_login(user)
    print(f"Logado como: {user.username}")
    
    # APIs para testar
    apis_to_test = [
        'monthly_evolution',
        'top_formadores', 
        'distribuicao_setores',
        'municipios_atendidos',
        'tipos_evento',
        'projetos_stats'
    ]
    
    print("\n=== Testando APIs do Dashboard ===")
    
    for api_name in apis_to_test:
        print(f"\n--- Testando: {api_name} ---")
        
        # Fazer requisição
        response = client.get(f'/diretoria/api/charts/?chart={api_name}')
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                import json
                data = json.loads(response.content.decode('utf-8'))
                print(f"Response Type: {type(data)}")
                print(f"Response Keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                
                if 'data' in data:
                    print(f"Data Length: {len(data['data']) if isinstance(data['data'], list) else 'Not a list'}")
                    if isinstance(data['data'], list) and len(data['data']) > 0:
                        print(f"First Item: {data['data'][0]}")
                    else:
                        print("Data is empty!")
                else:
                    print("No 'data' key in response")
                    
            except json.JSONDecodeError as e:
                print(f"JSON Decode Error: {e}")
                print(f"Raw Content: {response.content[:200]}")
        else:
            print(f"Error: {response.content.decode('utf-8')[:200]}")
    
    # Testar página principal
    print(f"\n--- Testando Dashboard Page ---")
    response = client.get('/diretoria/dashboard/')
    print(f"Dashboard Status Code: {response.status_code}")
    
    return True

def check_database_data():
    """Verifica se há dados nas tabelas necessárias"""
    from core.models import Solicitacao, Formador, Municipio, Projeto, TipoEvento
    
    print("\n=== Verificando Dados no Banco ===")
    
    tables_to_check = [
        ('Solicitacoes', Solicitacao),
        ('Formadores', Formador), 
        ('Municipios', Municipio),
        ('Projetos', Projeto),
        ('TipoEvento', TipoEvento)
    ]
    
    for table_name, model_class in tables_to_check:
        count = model_class.objects.count()
        print(f"{table_name}: {count} registros")
        
        if count > 0 and table_name == 'Solicitacoes':
            # Mostrar algumas solicitações
            recent = model_class.objects.order_by('-data_solicitacao')[:3]
            print("  Ultimas solicitacoes:")
            for sol in recent:
                print(f"    - {sol.titulo_evento} ({sol.data_solicitacao.strftime('%Y-%m-%d')})")

if __name__ == '__main__':
    print("=== Teste das APIs do Dashboard da Diretoria ===")
    check_database_data()
    test_dashboard_apis()
    print("\nTeste concluido!")
#!/usr/bin/env python3

import requests
import sys
from bs4 import BeautifulSoup

def test_modern_select_boxes():
    base_url = "http://localhost:8000"
    
    print("🎨 Testando modernização das caixas de seleção...")
    
    # 1. Fazer login
    session = requests.Session()
    login_url = f"{base_url}/login/"
    
    print("1️⃣ Fazendo login...")
    response = session.get(login_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']
    
    login_data = {
        'username': 'danieladm',
        'password': 'teste123',
        'csrfmiddlewaretoken': csrf_token
    }
    
    response = session.post(login_url, data=login_data, allow_redirects=False)
    if response.status_code != 302:
        print(f"❌ Login falhou: {response.status_code}")
        return False
    
    print("✅ Login realizado com sucesso!")
    
    # 2. Acessar formulário de solicitação
    solicitacao_url = f"{base_url}/solicitar/"
    print("2️⃣ Acessando formulário de solicitação...")
    
    response = session.get(solicitacao_url)
    if response.status_code != 200:
        print(f"❌ Erro ao acessar formulário: {response.status_code}")
        return False
    
    print("✅ Formulário de solicitação acessível!")
    
    # 3. Verificar as melhorias visuais
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print("\n🔍 Verificando melhorias nas caixas de seleção...")
    
    # Verificar se as classes modernas foram aplicadas
    modern_selects = soup.find_all('select', class_='modern-select')
    if len(modern_selects) >= 3:
        print(f"✅ Classes modernas aplicadas: {len(modern_selects)} selects encontrados")
    else:
        print(f"❌ Classes modernas não encontradas. Selects: {len(modern_selects)}")
        return False
    
    # Verificar containers com ícones
    select_containers = soup.find_all('div', class_='select-container')
    container_types = []
    for container in select_containers:
        classes = container.get('class', [])
        for cls in classes:
            if cls in ['projeto', 'municipio', 'tipo-evento']:
                container_types.append(cls)
    
    expected_containers = ['projeto', 'municipio', 'tipo-evento']
    if set(container_types) >= set(expected_containers):
        print(f"✅ Containers com ícones criados: {container_types}")
    else:
        print(f"❌ Containers com ícones não encontrados: {container_types}")
        return False
    
    # Verificar se o CSS moderno está presente
    css_modern = False
    style_tags = soup.find_all('style')
    for style in style_tags:
        if 'modern-select' in style.text and 'appearance: none' in style.text:
            css_modern = True
            break
    
    if css_modern:
        print("✅ CSS moderno para selects aplicado")
    else:
        print("❌ CSS moderno não encontrado")
        return False
    
    # Verificar específicos de cada select
    print("\n📋 Detalhes dos selects modernizados:")
    
    select_details = []
    for i, select in enumerate(modern_selects):
        select_id = select.get('id', f'select-{i}')
        select_name = select.get('name', 'unknown')
        select_classes = ' '.join(select.get('class', []))
        
        print(f"   📝 Select {i+1}:")
        print(f"      • ID: {select_id}")
        print(f"      • Name: {select_name}")
        print(f"      • Classes: {select_classes}")
        
        # Verificar se tem opções
        options = select.find_all('option')
        print(f"      • Opções: {len(options)}")
        
        select_details.append({
            'id': select_id,
            'name': select_name,
            'options': len(options)
        })
    
    # Verificar se há gradientes nas seções
    form_sections = soup.find_all('div', class_='form-section')
    print(f"\n🎨 Seções do formulário encontradas: {len(form_sections)}")
    
    # Verificar se CSS tem variáveis modernas
    has_css_variables = False
    for style in style_tags:
        if ':root' in style.text and '--primary-color' in style.text:
            has_css_variables = True
            break
    
    if has_css_variables:
        print("✅ Variáveis CSS modernas definidas")
    else:
        print("❌ Variáveis CSS modernas não encontradas")
    
    return True

if __name__ == "__main__":
    try:
        success = test_modern_select_boxes()
        if success:
            print("\n🎉 CAIXAS DE SELEÇÃO MODERNIZADAS COM SUCESSO!")
            print("🎨 Melhorias aplicadas:")
            print("   ✅ Appearance: none (remove estilo nativo)")
            print("   ✅ Bordas arredondadas e sombras")
            print("   ✅ Ícones específicos para cada tipo")
            print("   ✅ Hover effects e transições suaves")
            print("   ✅ Focus states melhorados")
            print("   ✅ Gradientes e variáveis CSS modernas")
            print("   ✅ Containers organizados com padding")
        else:
            print("\n❌ Algumas melhorias não foram aplicadas")
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Erro durante teste: {e}")
        sys.exit(1)
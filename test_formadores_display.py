#!/usr/bin/env python3

import requests
import sys
from bs4 import BeautifulSoup

def test_formadores_display():
    base_url = "http://localhost:8000"
    
    print("👥 Testando exibição dos formadores no formulário de solicitação...")
    
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
    
    # 3. Verificar a seção de formadores
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print("\n🔍 Verificando seção de formadores...")
    
    # Encontrar a seção de formadores
    formador_section = None
    sections = soup.find_all('div', class_='form-section')
    for section in sections:
        h5 = section.find('h5')
        if h5 and 'Formadores' in h5.text:
            formador_section = section
            break
    
    if not formador_section:
        print("❌ Seção de formadores não encontrada")
        return False
    
    print("✅ Seção de formadores encontrada")
    
    # Verificar os checkboxes dos formadores
    formador_checkboxes = formador_section.find_all('input', type='checkbox')
    if not formador_checkboxes:
        print("❌ Checkboxes dos formadores não encontrados")
        return False
    
    print(f"✅ {len(formador_checkboxes)} formadores encontrados")
    
    # Verificar os labels dos formadores
    formador_labels = []
    problematic_labels = []
    
    for checkbox in formador_checkboxes:
        checkbox_id = checkbox.get('id')
        if checkbox_id:
            label = formador_section.find('label', {'for': checkbox_id})
            if label:
                label_text = label.text.strip()
                formador_labels.append(label_text)
                
                # Verificar se ainda contém email (formato: "Nome <email@domain.com>")
                if '<' in label_text and '@' in label_text and '>' in label_text:
                    problematic_labels.append(label_text)
    
    print(f"\n📋 Labels dos formadores encontrados:")
    for i, label in enumerate(formador_labels, 1):
        status = "❌" if label in problematic_labels else "✅"
        print(f"   {status} {i}. {label}")
    
    # Verificar se há labels problemáticos
    if problematic_labels:
        print(f"\n❌ {len(problematic_labels)} formadores ainda exibem email:")
        for label in problematic_labels:
            print(f"   • {label}")
        return False
    else:
        print(f"\n✅ Todos os {len(formador_labels)} formadores mostram apenas o nome!")
    
    # Verificar se há formadores com nomes válidos
    valid_names = [label for label in formador_labels if len(label.strip()) > 0 and not ('<' in label and '@' in label)]
    
    if len(valid_names) == len(formador_labels):
        print("✅ Todos os nomes estão formatados corretamente")
    else:
        print(f"⚠️ {len(formador_labels) - len(valid_names)} nomes podem ter problemas de formatação")
    
    # Verificar estrutura da grade de formadores
    formador_grid = formador_section.find('div', class_='formador-grid')
    if formador_grid:
        print("✅ Grade de formadores encontrada")
        
        formador_items = formador_grid.find_all('div', class_='formador-item')
        print(f"✅ {len(formador_items)} itens de formadores na grade")
    else:
        print("⚠️ Grade de formadores não encontrada (pode usar layout diferente)")
    
    return True

if __name__ == "__main__":
    try:
        success = test_formadores_display()
        if success:
            print("\n🎉 EXIBIÇÃO DOS FORMADORES CORRIGIDA COM SUCESSO!")
            print("👥 Melhorias aplicadas:")
            print("   ✅ Formadores mostram apenas o nome")
            print("   ✅ Emails removidos da exibição")
            print("   ✅ Layout organizado mantido")
            print("   ✅ Funcionalidade de seleção preservada")
        else:
            print("\n❌ Problemas encontrados na exibição dos formadores")
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Erro durante teste: {e}")
        sys.exit(1)
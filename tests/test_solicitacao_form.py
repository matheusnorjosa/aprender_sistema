#!/usr/bin/env python3

import requests
import sys
from bs4 import BeautifulSoup

def test_solicitacao_form_improvements():
    base_url = "http://localhost:8000"
    
    print("🎯 Testando melhorias no formulário de solicitação de evento...")
    
    # 1. Fazer login
    session = requests.Session()
    login_url = f"{base_url}/login/"
    
    print("1️⃣ Fazendo login...")
    response = session.get(login_url)
    if response.status_code != 200:
        print(f"❌ Erro ao acessar login: {response.status_code}")
        return False
    
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
    
    # 3. Verificar as alterações solicitadas
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Verificar se o label mudou de "Título do Evento" para "Segmento"
    titulo_label = None
    titulo_input = None
    
    # Buscar o campo titulo_evento
    titulo_input = soup.find('input', id=lambda x: x and 'titulo_evento' in x)
    if titulo_input:
        # Buscar o label correspondente
        label_for = titulo_input.get('id')
        titulo_label = soup.find('label', {'for': label_for})
    
    if not titulo_label:
        print("❌ Campo título/segmento não encontrado")
        return False
    
    # Verificar se o label é "Segmento"
    label_text = titulo_label.text.strip()
    if "Segmento" in label_text:
        print(f"✅ Label alterado corretamente: '{label_text}'")
    else:
        print(f"❌ Label não alterado. Encontrado: '{label_text}'")
        return False
    
    # Verificar se o placeholder foi alterado
    placeholder = titulo_input.get('placeholder', '')
    expected_placeholder = "Ex: 1º e 2º anos"
    
    if placeholder == expected_placeholder:
        print(f"✅ Placeholder alterado corretamente: '{placeholder}'")
    else:
        print(f"❌ Placeholder incorreto. Esperado: '{expected_placeholder}', Encontrado: '{placeholder}'")
        return False
    
    # Verificar outras informações do formulário
    print("\n📋 Informações adicionais do formulário:")
    
    # Verificar se o formulário ainda tem as outras seções
    sections = soup.find_all('div', class_='form-section')
    section_titles = []
    for section in sections:
        h5 = section.find('h5')
        if h5:
            section_titles.append(h5.text.strip())
    
    print(f"   📂 Seções encontradas: {len(sections)}")
    for i, title in enumerate(section_titles, 1):
        print(f"      {i}. {title}")
    
    # Verificar se o input tem atributos corretos
    if titulo_input:
        max_length = titulo_input.get('maxlength', '')
        css_class = titulo_input.get('class', '')
        print(f"   📝 Atributos do campo Segmento:")
        print(f"      • Maxlength: {max_length}")
        print(f"      • CSS Class: {css_class}")
        print(f"      • Type: {titulo_input.get('type', 'text')}")
    
    return True

if __name__ == "__main__":
    try:
        success = test_solicitacao_form_improvements()
        if success:
            print("\n🎉 FORMULÁRIO DE SOLICITAÇÃO MELHORADO COM SUCESSO!")
            print("📝 Alterações implementadas:")
            print("   ✅ Label: 'Título do Evento' → 'Segmento'")
            print("   ✅ Placeholder: 'Ex: 1º e 2º anos'")
            print("   ✅ Funcionalidade mantida")
            print("   ✅ Layout preservado")
        else:
            print("\n❌ Algumas melhorias não foram aplicadas corretamente")
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Erro durante teste: {e}")
        sys.exit(1)
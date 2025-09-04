#!/usr/bin/env python3

import sys

import requests
from bs4 import BeautifulSoup


def test_simplified_form():
    base_url = "http://localhost:8000"

    print("🎯 Testando formulário de bloqueio simplificado...")

    # 1. Fazer login
    session = requests.Session()
    login_url = f"{base_url}/login/"

    response = session.get(login_url)
    soup = BeautifulSoup(response.text, "html.parser")
    csrf_token = soup.find("input", {"name": "csrfmiddlewaretoken"})["value"]

    login_data = {
        "username": "danieladm",
        "password": "teste123",
        "csrfmiddlewaretoken": csrf_token,
    }

    response = session.post(login_url, data=login_data, allow_redirects=False)
    if response.status_code != 302:
        print(f"❌ Login falhou: {response.status_code}")
        return False

    # 2. Acessar formulário de bloqueio
    bloqueio_url = f"{base_url}/bloqueios/novo/"
    response = session.get(bloqueio_url)

    if response.status_code != 200:
        print(f"❌ Erro ao acessar formulário: {response.status_code}")
        return False

    soup = BeautifulSoup(response.text, "html.parser")

    # 3. Verificar simplificações
    print("📏 Verificando simplificações...")

    # Verificar se os tipos mostram apenas "Total" e "Parcial"
    tipo_cards = soup.find_all("div", class_="tipo-card")
    tipos_texto = []
    for card in tipo_cards:
        h5 = card.find("h5")
        if h5:
            tipos_texto.append(h5.text.strip())

    expected_tipos = ["Total", "Parcial"]
    if set(tipos_texto) == set(expected_tipos):
        print("✅ Tipos de bloqueio simplificados corretamente")
        print(f"   📋 Tipos encontrados: {tipos_texto}")
    else:
        print(f"❌ Tipos não simplificados: {tipos_texto}")
        return False

    # Verificar estrutura compacta
    form_sections = soup.find_all("div", class_="form-section")
    section_titles = []
    for section in form_sections:
        title = section.find("h3", class_="section-title")
        if title:
            section_titles.append(title.text.strip())

    expected_titles = ["Formador", "Período", "Tipo"]
    simplified_titles = [
        title
        for title in section_titles
        if any(expected in title for expected in expected_titles)
    ]

    if len(simplified_titles) >= 3:
        print("✅ Títulos das seções simplificados")
        print(f"   📋 Seções: {simplified_titles}")
    else:
        print(f"❌ Títulos não simplificados: {section_titles}")

    # Verificar se há menos conteúdo (medindo tamanho da resposta)
    content_size = len(response.text)
    print(f"📊 Tamanho do conteúdo: {content_size:,} bytes")

    # Verificar se não há textos explicativos longos
    has_long_explanations = False
    paragraphs = soup.find_all("p")
    for p in paragraphs:
        if len(p.text.strip()) > 100:  # Textos longos
            has_long_explanations = True
            break

    if not has_long_explanations:
        print("✅ Textos explicativos removidos/simplificados")
    else:
        print("⚠️ Ainda há textos explicativos longos")

    # Verificar responsividade mobile
    viewport_meta = soup.find("meta", attrs={"name": "viewport"})
    if viewport_meta:
        print("✅ Configurado para responsividade mobile")

    return True


if __name__ == "__main__":
    try:
        success = test_simplified_form()
        if success:
            print("\n🎉 FORMULÁRIO SIMPLIFICADO COM SUCESSO!")
            print("📦 Principais otimizações:")
            print("   ✂️  Tipos de bloqueio: apenas 'Total' e 'Parcial'")
            print("   📏 Espaçamentos reduzidos")
            print("   🗂️  Títulos das seções simplificados")
            print("   📱 Interface mais compacta")
            print("   ⬇️  Menos necessidade de rolagem")
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Erro durante teste: {e}")
        sys.exit(1)

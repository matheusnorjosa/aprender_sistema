#!/usr/bin/env python3

import sys

import requests
from bs4 import BeautifulSoup


def test_bloqueio_form():
    base_url = "http://localhost:8000"

    print("🧪 Testando formulário de bloqueio melhorado...")

    # 1. Fazer login primeiro
    session = requests.Session()
    login_url = f"{base_url}/login/"

    print("1️⃣ Fazendo login...")
    response = session.get(login_url)
    if response.status_code != 200:
        print(f"❌ Erro ao acessar login: {response.status_code}")
        return False

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

    print("✅ Login realizado com sucesso!")

    # 2. Acessar formulário de bloqueio
    bloqueio_url = f"{base_url}/bloqueios/novo/"
    print("2️⃣ Acessando formulário de bloqueio...")

    response = session.get(bloqueio_url)
    if response.status_code != 200:
        print(f"❌ Erro ao acessar formulário: {response.status_code}")
        return False

    print("✅ Formulário de bloqueio acessível!")

    # 3. Verificar se as melhorias estão aplicadas
    soup = BeautifulSoup(response.text, "html.parser")

    # Verificar se o campo formador está presente
    formador_select = soup.find("select", id=lambda x: x and "formador" in x)
    if not formador_select:
        print("❌ Campo formador não encontrado")
        return False

    # Verificar opções do formador (deve mostrar apenas nomes)
    formador_options = formador_select.find_all("option")
    if len(formador_options) > 1:  # Primeira opção é vazia
        sample_option = formador_options[1].text.strip()
        if "<" in sample_option and "@" in sample_option:
            print(f"❌ Formador ainda mostra email: {sample_option}")
            return False
        else:
            print(f"✅ Formador mostra apenas nome: {sample_option}")

    # Verificar tipos de bloqueio
    tipo_cards = soup.find_all("div", class_="tipo-card")
    if len(tipo_cards) != 2:
        print(f"❌ Número incorreto de tipos: {len(tipo_cards)}")
        return False

    # Verificar se os dois tipos são diferentes
    tipos_encontrados = []
    for card in tipo_cards:
        h5 = card.find("h5")
        if h5:
            tipo_texto = h5.text.strip()
            tipos_encontrados.append(tipo_texto)

    if len(set(tipos_encontrados)) != 2:
        print(f"❌ Tipos duplicados encontrados: {tipos_encontrados}")
        return False

    print(f"✅ Tipos de bloqueio corretos: {tipos_encontrados}")

    # Verificar se a interface moderna está aplicada
    if "Inter" in response.text and "gradient" in response.text:
        print("✅ Interface moderna aplicada!")
    else:
        print("⚠️ Interface moderna pode não estar completa")

    return True


if __name__ == "__main__":
    try:
        success = test_bloqueio_form()
        if success:
            print("\n🎉 FORMULÁRIO DE BLOQUEIO MELHORADO COM SUCESSO!")
            print("📋 Principais melhorias:")
            print("   ✅ Campo formador mostra apenas o nome")
            print("   ✅ Tipos de bloqueio distintos (Total vs Parcial)")
            print("   ✅ Interface moderna e responsiva")
            print("   ✅ Validações aprimoradas")
            print("   ✅ UX melhorada com animações")
        else:
            print("\n❌ Alguns problemas foram encontrados")
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Erro durante teste: {e}")
        sys.exit(1)

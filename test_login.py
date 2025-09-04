#!/usr/bin/env python3

import sys

import requests


def test_login():
    base_url = "http://localhost:8000"

    # 1. Acessar a página de login para obter o token CSRF
    session = requests.Session()
    login_url = f"{base_url}/login/"

    print("1. Acessando página de login...")
    response = session.get(login_url)
    if response.status_code != 200:
        print(f"❌ Erro ao acessar login: {response.status_code}")
        return False

    print("✅ Página de login acessível")

    # 2. Extrair o token CSRF
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(response.text, "html.parser")
    csrf_token = soup.find("input", {"name": "csrfmiddlewaretoken"})

    if not csrf_token:
        print("❌ Token CSRF não encontrado")
        return False

    csrf_value = csrf_token["value"]
    print("✅ Token CSRF obtido")

    # 3. Fazer login
    login_data = {
        "username": "danieladm",  # usuário existente
        "password": "teste123",  # senha que definimos
        "csrfmiddlewaretoken": csrf_value,
    }

    print("2. Tentando fazer login...")
    response = session.post(login_url, data=login_data, allow_redirects=False)

    if response.status_code == 302:
        print("✅ Login redirecionou (potencialmente bem-sucedido)")
        redirect_location = response.headers.get("Location", "")
        print(f"   Redirecionado para: {redirect_location}")

        # 4. Tentar acessar a home
        print("3. Acessando página home após login...")
        home_response = session.get(f"{base_url}/", allow_redirects=False)

        if home_response.status_code == 200:
            print("✅ Home page carregou com sucesso!")
            return True
        elif home_response.status_code == 302:
            print(
                f"❌ Home ainda redirecionando: {home_response.headers.get('Location', '')}"
            )
            print("   Possível problema com credenciais")
            return False
        else:
            print(f"❌ Erro na home: {home_response.status_code}")
            return False
    else:
        print(f"❌ Login falhou: {response.status_code}")
        if response.status_code == 200:
            print("   Formulário retornou (credenciais inválidas)")
        return False


if __name__ == "__main__":
    try:
        success = test_login()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Erro durante teste: {e}")
        sys.exit(1)

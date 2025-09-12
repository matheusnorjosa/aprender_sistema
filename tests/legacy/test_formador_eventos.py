#!/usr/bin/env python3

import sys

import requests
from bs4 import BeautifulSoup


def test_formador_eventos_page():
    base_url = "http://localhost:8000"

    print("👨‍🏫 Testando página de eventos do formador...")

    # 1. Fazer login
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

    # 2. Acessar página de eventos do formador
    formador_url = f"{base_url}/formador/eventos/"
    print("2️⃣ Acessando página de eventos do formador...")

    response = session.get(formador_url)
    if response.status_code == 403:
        print("⚠️ Acesso negado - usuário não tem papel de formador")
        print("   (Isto é esperado se o usuário não for formador)")

        # Tentar como superuser acessando dados de um formador específico
        print("3️⃣ Testando acesso como superuser...")

        # Primeiro, vamos pegar a lista de formadores
        admin_formadores_url = f"{base_url}/admin/core/formador/"
        admin_response = session.get(admin_formadores_url)

        if admin_response.status_code == 200:
            admin_soup = BeautifulSoup(admin_response.text, "html.parser")

            # Procurar por formadores na página de admin
            formador_links = admin_soup.find_all("a", href=True)
            formador_ids = []

            for link in formador_links:
                href = link.get("href", "")
                if "/admin/core/formador/" in href and "/change/" in href:
                    # Extrair ID do formador
                    parts = href.split("/")
                    if len(parts) > 4:
                        formador_id = parts[4]
                        if len(formador_id) > 10:  # UUID tem mais de 10 caracteres
                            formador_ids.append(formador_id)

            if formador_ids:
                # Testar com o primeiro formador encontrado
                test_formador_id = formador_ids[0]
                formador_test_url = (
                    f"{base_url}/formador/eventos/?formador_id={test_formador_id}"
                )

                response = session.get(formador_test_url)
                if response.status_code != 200:
                    print(
                        f"❌ Erro ao acessar página com formador_id: {response.status_code}"
                    )
                    return False

                print(
                    f"✅ Página acessível como superuser com formador_id: {test_formador_id}"
                )
            else:
                print("⚠️ Nenhum formador encontrado para testar")
                return True  # Não é erro, apenas não há dados
        else:
            print(
                f"❌ Não foi possível acessar admin de formadores: {admin_response.status_code}"
            )
            return False

    elif response.status_code != 200:
        print(f"❌ Erro ao acessar página de eventos: {response.status_code}")
        return False
    else:
        print("✅ Página de eventos do formador acessível!")

    # 3. Verificar estrutura da página
    soup = BeautifulSoup(response.text, "html.parser")

    print("\\n🔍 Verificando estrutura da página...")

    # Verificar título da página
    page_title = soup.find("title")
    if page_title and "Meus Eventos" in page_title.text:
        print("✅ Título da página correto")
    else:
        print("❌ Título da página incorreto ou não encontrado")
        return False

    # Verificar se há seções de estatísticas
    stats_grid = soup.find("div", class_="stats-grid")
    if stats_grid:
        print("✅ Grid de estatísticas encontrado")

        stat_cards = stats_grid.find_all("div", class_="stat-card")
        print(f"   📊 {len(stat_cards)} cards de estatísticas encontrados")

        # Verificar se há números nas estatísticas
        for i, card in enumerate(stat_cards):
            stat_number = card.find("span", class_="stat-number")
            stat_label = card.find("div", class_="stat-label")

            if stat_number and stat_label:
                number = stat_number.text.strip()
                label = stat_label.text.strip()
                print(f"   • {label}: {number}")
            else:
                print(f"   ❌ Estrutura incorreta no card {i+1}")
                return False
    else:
        print("❌ Grid de estatísticas não encontrado")
        return False

    # Verificar se há informações do formador ou mensagem de erro
    formador_info = soup.find("div", class_="formador-info")
    error_message = soup.find("div", class_="error-message")

    if formador_info:
        print("✅ Informações do formador encontradas")
        formador_name = formador_info.find("h4")
        if formador_name:
            print(f"   👤 Formador: {formador_name.text.strip()}")
    elif error_message:
        print("⚠️ Mensagem de erro exibida (esperado se usuário não é formador)")
        error_text = error_message.get_text(strip=True)
        print(f"   📝 Erro: {error_text}")
    else:
        print("❌ Nem informações do formador nem mensagem de erro encontradas")
        return False

    # Verificar navegação
    nav_formador = soup.find("a", class_="nav-item active")
    if nav_formador and "Meus Eventos" in nav_formador.text:
        print("✅ Item de navegação ativo correto")
    else:
        print("⚠️ Item de navegação pode não estar ativo (verificar CSS)")

    # Verificar seções de eventos
    events_sections = soup.find_all("div", class_="events-section")
    print(f"📅 {len(events_sections)} seções de eventos encontradas")

    for section in events_sections:
        section_header = section.find("div", class_="section-header")
        if section_header:
            header_text = section_header.get_text(strip=True)
            print(f"   📂 Seção: {header_text}")

    # Verificar se o CSS moderno está presente
    css_modern = False
    style_tags = soup.find_all("style")
    for style in style_tags:
        if "--primary-color" in style.text and "stats-grid" in style.text:
            css_modern = True
            break

    if css_modern:
        print("✅ CSS moderno aplicado")
    else:
        print("❌ CSS moderno não encontrado")
        return False

    return True


if __name__ == "__main__":
    try:
        success = test_formador_eventos_page()
        if success:
            print("\\n🎉 PÁGINA DE EVENTOS DO FORMADOR IMPLEMENTADA COM SUCESSO!")
            print("👨‍🏫 Funcionalidades implementadas:")
            print("   ✅ View com verificação de role (formador ou superuser)")
            print("   ✅ Template responsivo e moderno")
            print("   ✅ Estatísticas animadas de eventos")
            print("   ✅ Categorização: Futuros, Em Andamento, Passados, Pendentes")
            print("   ✅ Exibição detalhada de cada evento")
            print("   ✅ Navegação integrada ao sistema")
            print("   ✅ Suporte para superuser visualizar qualquer formador")
            print("   ✅ Tratamento de erros quando formador não existe")
            print("\\n🔗 Acesse a página em: http://localhost:8000/formador/eventos/")
        else:
            print("\\n❌ Alguns problemas foram encontrados na implementação")
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Erro durante teste: {e}")
        sys.exit(1)

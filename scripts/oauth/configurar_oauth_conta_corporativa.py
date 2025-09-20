#!/usr/bin/env python3
"""
Script para configurar OAuth2 especificamente para aprender-sistema@aprendereditora.com.br
"""

import os
import json
import webbrowser
from urllib.parse import parse_qs, urlparse

def configurar_oauth_manual():
    """Configura OAuth2 manualmente para a conta corporativa"""

    print("CONFIGURACAO OAUTH - CONTA CORPORATIVA")
    print("=" * 50)
    print("CONTA: aprender-sistema@aprendereditora.com.br")
    print("=" * 50)

    # Verificar se credentials.json existe
    if not os.path.exists('credentials.json'):
        print("[ERROR] credentials.json nao encontrado!")
        print("[INFO] Certifique-se de que o arquivo esta na pasta do projeto")
        return False

    # Carregar credenciais
    with open('credentials.json', 'r') as f:
        creds = json.load(f)

    client_config = creds['installed']
    client_id = client_config['client_id']
    client_secret = client_config['client_secret']

    print(f"[INFO] Client ID: {client_id}")
    print(f"[INFO] Project ID: {client_config.get('project_id', 'N/A')}")

    # Escopos necessários para Google Sheets
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file'
    ]
    scope_string = ' '.join(scopes)

    # Gerar URL de autorização
    auth_url = (
        f"https://accounts.google.com/o/oauth2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri=http://localhost&"
        f"scope={scope_string}&"
        f"response_type=code&"
        f"access_type=offline&"
        f"prompt=consent"
    )

    print("\\n[INFO] PROXIMOS PASSOS:")
    print("1. Uma pagina sera aberta no seu navegador")
    print("2. IMPORTANTE: Faca login com: aprender-sistema@aprendereditora.com.br")
    print("3. Autorize o acesso para o aplicativo")
    print("4. Voce sera redirecionado para uma pagina de erro")
    print("5. Copie o codigo da URL (parametro 'code')")
    print("6. Cole o codigo aqui")

    input("\\nPressione Enter para abrir o navegador...")

    # Abrir navegador
    try:
        webbrowser.open(auth_url)
        print("[INFO] Navegador aberto com URL de autorizacao")
    except Exception as e:
        print(f"[WARN] Nao foi possivel abrir automaticamente: {e}")
        print(f"[INFO] Acesse manualmente: {auth_url}")

    print("\\n[MANUAL] Se o navegador nao abriu, copie esta URL:")
    print(auth_url)

    # Aguardar código do usuário
    print("\\n" + "="*50)
    auth_code = input("Cole o codigo de autorizacao aqui: ").strip()

    if not auth_code:
        print("[ERROR] Codigo nao fornecido!")
        return False

    print("[INFO] Codigo recebido, obtendo token...")

    # Fazer requisição para obter token
    import requests

    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'code': auth_code,
        'grant_type': 'authorization_code',
        'redirect_uri': 'http://localhost'
    }

    try:
        response = requests.post(token_url, data=token_data)
        response.raise_for_status()

        token_info = response.json()

        # Criar authorized user file para gspread
        authorized_user_info = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": token_info.get('refresh_token'),
            "access_token": token_info.get('access_token'),
            "type": "authorized_user"
        }

        # Salvar em formato compatível com gspread
        with open('google_authorized_user.json', 'w') as f:
            json.dump(authorized_user_info, f, indent=2)

        print("[SUCCESS] Token salvo em: google_authorized_user.json")

        # Testar acesso
        print("[INFO] Testando acesso a planilha...")

        import gspread
        from google.oauth2.credentials import Credentials

        # Carregar credenciais
        creds = Credentials.from_authorized_user_file('google_authorized_user.json')

        # Autorizar cliente
        gc = gspread.authorize(creds)

        # Testar acesso à planilha
        PLANILHA_ID = '16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU'

        try:
            sheet = gc.open_by_key(PLANILHA_ID)
            print(f"[SUCCESS] Planilha acessada: {sheet.title}")

            worksheets = [ws.title for ws in sheet.worksheets()]
            print(f"[INFO] Abas disponiveis: {worksheets}")

            # Verificar aba Super
            super_ws = sheet.worksheet('Super')
            print(f"[INFO] Aba Super: {super_ws.row_count} linhas x {super_ws.col_count} colunas")

            # Salvar configuração de sucesso
            config = {
                'account_used': 'aprender-sistema@aprendereditora.com.br',
                'spreadsheet_id': PLANILHA_ID,
                'spreadsheet_title': sheet.title,
                'worksheets': worksheets,
                'credentials_file': 'google_authorized_user.json',
                'access_confirmed': True
            }

            with open('oauth_config_success.json', 'w') as f:
                json.dump(config, f, indent=2)

            print("[SUCCESS] Configuracao completa salva em: oauth_config_success.json")
            print("\\n[SUCCESS] CONFIGURACAO CONCLUIDA!")
            print("[INFO] O arquivo google_authorized_user.json pode ser usado pelo sistema")

            return True

        except Exception as e:
            print(f"[ERROR] Erro ao acessar planilha: {e}")

            if "403" in str(e) or "permission" in str(e).lower():
                print("\\n[WARN] ERRO DE PERMISSAO!")
                print("[INFO] A planilha precisa ser compartilhada com:")
                print("       aprender-sistema@aprendereditora.com.br")
                print("[INFO] Vá para a planilha e clique em 'Compartilhar'")

            return False

    except Exception as e:
        print(f"[ERROR] Erro ao obter token: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"[DEBUG] Resposta: {e.response.text}")
        return False

if __name__ == "__main__":
    if configurar_oauth_manual():
        print("\\n[SUCCESS] Pronto para usar a planilha!")
    else:
        print("\\n[ERROR] Configuracao falhou.")
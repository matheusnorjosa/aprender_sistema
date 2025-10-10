#!/usr/bin/env python
"""
OAuth2 com servidor localhost temporário
"""

import os
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import django

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Configurar Django
sys.path.append(".")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()


class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Manipula requisições GET"""
        if self.path.startswith("/oauth2callback"):
            # Extrair código de autorização
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)

            if "code" in query_params:
                self.server.auth_code = query_params["code"][0]
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                html_content = """
                <html>
                <body>
                    <h1>Autorização bem-sucedida!</h1>
                    <p>Você pode fechar esta janela e voltar ao terminal.</p>
                </body>
                </html>
                """
                self.wfile.write(html_content.encode("utf-8"))
            else:
                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(
                    "<html><body><h1>Erro na autorização</h1></body></html>".encode(
                        "utf-8"
                    )
                )
        else:
            self.send_response(404)
            self.end_headers()


def configurar_oauth_localhost():
    """Configuração OAuth2 com localhost"""

    print("🔧 Configurando OAuth2 com localhost...")

    # Arquivos
    credentials_file = "acesso_planilhas.json"
    token_file = "google_oauth_token.json"

    # Escopos
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]

    # Verificar arquivo de credenciais
    if not os.path.exists(credentials_file):
        print(f"❌ Arquivo {credentials_file} não encontrado!")
        return False

    print(f"✅ Arquivo {credentials_file} encontrado")

    # Carregar credenciais
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        print(f"✅ Token existente encontrado")

    # Se não há credenciais válidas, fazer login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Renovando token...")
            creds.refresh(Request())
        else:
            print("🔑 Iniciando fluxo de autenticação...")

            # Criar flow com localhost
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_file,
                SCOPES,
                redirect_uri="http://localhost:8080/oauth2callback",
            )

            # Iniciar servidor local
            server = HTTPServer(("localhost", 8080), OAuthHandler)
            server.auth_code = None

            print("🌐 Iniciando servidor local na porta 8080...")

            # Thread para o servidor
            server_thread = threading.Thread(target=server.serve_forever)
            server_thread.daemon = True
            server_thread.start()

            # Obter URL de autorização
            auth_url, _ = flow.authorization_url(
                access_type="offline", prompt="consent"
            )

            print(f"\n🌐 Abrindo navegador...")
            print(f"URL: {auth_url}")

            # Abrir navegador
            webbrowser.open(auth_url)

            print(f"\n⏳ Aguardando autorização...")
            print(f"Faça login com: aprender-sistema@aprendereditora.com.br")
            print(f"Após autorizar, volte aqui...")

            # Aguardar código
            while server.auth_code is None:
                import time

                time.sleep(1)

            # Parar servidor
            server.shutdown()
            server_thread.join()

            # Trocar código por token
            print("🔄 Trocando código por token...")
            flow.fetch_token(code=server.auth_code)
            creds = flow.credentials

        # Salvar token
        with open(token_file, "w") as token:
            token.write(creds.to_json())
        print(f"✅ Token salvo em {token_file}")

    # Testar acesso
    print(f"\n🔗 Testando acesso...")
    try:
        import gspread

        client = gspread.authorize(creds)

        SPREADSHEET_ID = "16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU"
        spreadsheet = client.open_by_key(SPREADSHEET_ID)

        print(f"✅ Acesso bem-sucedido!")
        print(f"📊 Planilha: {spreadsheet.title}")
        print(f"📑 Abas: {len(spreadsheet.worksheets())}")

        # Listar abas
        for i, worksheet in enumerate(spreadsheet.worksheets()):
            print(f"   {i+1}. {worksheet.title}")

        return True

    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False


if __name__ == "__main__":
    configurar_oauth_localhost()

#!/usr/bin/env python3
"""
Script Otimizado - Alta similaridade de funções
=====================================

Script consolidado e otimizado gerado automaticamente.
Consolida funcionalidades de múltiplos scripts similares.

Scripts originais:
- scripts/oauth/finalizar_oauth.py
- scripts/oauth/finalizar_oauth_novo.py

Author: Sistema de Otimização
Date: 19/09/2025
Similaridade: 1.0
"""

#!/usr/bin/env python3
"""
Script para finalizar configuração OAuth2 com código de autorização
"""

import json
import requests

def finalizar_oauth(auth_code):
    """Finaliza OAuth2 com código de autorização"""

    print("FINALIZANDO CONFIGURACAO OAUTH2")
    print("=" * 50)
    print(f"Codigo recebido: {auth_code[:20]}...")

    # Carregar credenciais
    with open('credentials.json', 'r') as f:
        creds = json.load(f)

    client_config = creds['installed']
    client_id = client_config['client_id']
    client_secret = client_config['client_secret']

    print(f"[INFO] Client ID: {client_id}")

    # Tentar diferentes redirect_uris
    redirect_uris = [
        'http://localhost',
        'http://localhost:8080/oauth2callback',
        'http://localhost:8080'
    ]

    token_url = "https://oauth2.googleapis.com/token"

    response = None
    for redirect_uri in redirect_uris:
        try:
            print(f"[INFO] Tentando com redirect_uri: {redirect_uri}")

            token_data = {
                'client_id': client_id,
                'client_secret': client_secret,
                'code': auth_code,
                'grant_type': 'authorization_code',
                'redirect_uri': redirect_uri
            }

            response = requests.post(token_url, data=token_data)
            response.raise_for_status()
            print(f"[SUCCESS] Token obtido com redirect_uri: {redirect_uri}")
            break

        except requests.exceptions.HTTPError as e:
            print(f"[WARN] Falhou com {redirect_uri}: {e.response.status_code}")
            continue

    if response is None or not response.ok:
        raise Exception("Nenhum redirect_uri funcionou")

    try:

        token_info = response.json()
        print("[SUCCESS] Token obtido com sucesso!")

        # Criar arquivo authorized user para gspread
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

        print("[SUCCESS] Credenciais salvas em: google_authorized_user.json")

        # Testar acesso à planilha
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
            print(f"[INFO] Abas disponiveis ({len(worksheets)}): {worksheets}")

            # Testar aba Super especificamente
            super_ws = sheet.worksheet('Super')
            print(f"[INFO] Aba Super: {super_ws.row_count} linhas x {super_ws.col_count} colunas")

            # Obter cabeçalhos da aba Super
            headers = super_ws.row_values(1)
            print(f"[INFO] Headers da aba Super ({len(headers)}):")
            for i, header in enumerate(headers[:10], 1):  # Primeiros 10
                letra = chr(64+i) if i <= 26 else f"A{chr(64+i-26)}"
                print(f"  {letra} ({i:2d}): {header}")

            # Localizar coluna de aprovação
            aprovacao_col = None
            for i, header in enumerate(headers, 1):
                if 'aprovação' in header.lower() or 'aprovacao' in header.lower():
                    aprovacao_col = i
                    letra = chr(64+i) if i <= 26 else f"A{chr(64+i-26)}"
                    print(f"[FOUND] Coluna de aprovacao: {letra} ({i}) - '{header}'")
                    break

            if not aprovacao_col:
                print("[WARN] Coluna 'Aprovacao' nao encontrada explicitamente")
                print("[INFO] Assumindo coluna B (2) conforme explicado")
                aprovacao_col = 2

            # Analisar algumas linhas para entender aprovação
            print(f"\\n[INFO] Analisando dados de aprovacao...")

            # Obter primeiras 10 linhas de dados (pular cabeçalho)
            sample_data = super_ws.get_values('A2:T11')  # Linhas 2-11, colunas A-T

            aprovados = 0
            pendentes = 0

            for i, row in enumerate(sample_data, 2):
                if len(row) >= aprovacao_col:
                    valor_aprovacao = row[aprovacao_col-1].strip() if row[aprovacao_col-1] else ''

                    if valor_aprovacao.upper() == 'SIM':
                        aprovados += 1
                        status = 'APROVADO'
                    else:
                        pendentes += 1
                        status = 'PENDENTE'

                    municipio = row[0] if len(row) > 0 else 'N/A'
                    print(f"  Linha {i:2d}: {status:8} | '{valor_aprovacao:3}' | {municipio[:20]}")

            print(f"\\n[STATS] Amostra de 10 linhas:")
            print(f"  Aprovados: {aprovados}")
            print(f"  Pendentes: {pendentes}")

            # Salvar configuração de sucesso
            config = {
                'account_used': 'aprender-sistema@aprendereditora.com.br',
                'spreadsheet_id': PLANILHA_ID,
                'spreadsheet_title': sheet.title,
                'worksheets': worksheets,
                'super_worksheet': {
                    'rows': super_ws.row_count,
                    'columns': super_ws.col_count,
                    'headers': headers,
                    'aprovacao_column': aprovacao_col
                },
                'sample_stats': {
                    'aprovados': aprovados,
                    'pendentes': pendentes,
                    'total_sample': len(sample_data)
                },
                'credentials_file': 'google_authorized_user.json',
                'access_confirmed': True
            }

            with open('oauth_config_success.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            print("\\n[SUCCESS] CONFIGURACAO COMPLETA!")
            print("[SUCCESS] Configuracao salva em: oauth_config_success.json")
            print("[SUCCESS] Arquivo google_authorized_user.json pronto para uso")
            print("\\n[NEXT] Agora voce pode:")
            print("1. Copiar google_authorized_user.json para o Docker")
            print("2. Executar importacao da aba Super")
            print("3. Analisar dados com logica de aprovacao correta")

            return True

        except Exception as e:
            print(f"[ERROR] Erro ao acessar planilha: {e}")

            if "403" in str(e) or "permission" in str(e).lower():
                print("\\n[WARN] ERRO DE PERMISSAO!")
                print("[ACTION] A planilha precisa ser compartilhada com:")
                print("         aprender-sistema@aprendereditora.com.br")
                print("[ACTION] Va para a planilha e clique em 'Compartilhar'")

            return False

    except Exception as e:
        print(f"[ERROR] Erro ao obter token: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"[DEBUG] Status: {e.response.status_code}")
            print(f"[DEBUG] Resposta: {e.response.text}")
        print(f"[DEBUG] Dados enviados: {token_data}")
        return False

if __name__ == "__main__":
    # Código extraído da URL fornecida
    auth_code = "4/0AVGzR1CVd11r_77kfFv61mE-2pQ5pr4GdNeTwLhQLRsYG3HECICwOxVL-Re6GfbPwK9peg"

    if finalizar_oauth(auth_code):
        print("\\n[SUCCESS] OAuth configurado com sucesso!")
    else:
        print("\\n[ERROR] Falha na configuracao OAuth")
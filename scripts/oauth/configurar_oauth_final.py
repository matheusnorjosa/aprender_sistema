#!/usr/bin/env python
"""
Configuração final de OAuth2 para acessar planilha do domínio Aprender Editora
"""

import os
import sys
import json
import django

# Configurar Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
django.setup()

def configurar_oauth_final():
    """Configura OAuth2 final para domínio Aprender Editora"""
    
    print("🔧 Configurando OAuth2 para domínio Aprender Editora...")
    
    # Verificar arquivo de credenciais OAuth2
    oauth_file = "acesso_planilhas.json"
    if not os.path.exists(oauth_file):
        print(f"❌ Arquivo {oauth_file} não encontrado!")
        print(f"📋 Certifique-se de que o arquivo está na pasta do projeto")
        return False
    
    print(f"✅ Arquivo {oauth_file} encontrado")
    
    # Ler credenciais
    with open(oauth_file, 'r') as f:
        creds_data = json.load(f)
    
    print("📋 Credenciais OAuth2:")
    print(f"   Project ID: {creds_data.get('installed', {}).get('project_id', 'N/A')}")
    print(f"   Client ID: {creds_data.get('installed', {}).get('client_id', 'N/A')}")
    
    # Gerar URL de autorização
    client_id = creds_data.get('installed', {}).get('client_id')
    redirect_uri = "urn:ietf:wg:oauth:2.0:oob"  # Para aplicações desktop
    
    if client_id:
        auth_url = (
            f"https://accounts.google.com/o/oauth2/auth?"
            f"client_id={client_id}&"
            f"redirect_uri={redirect_uri}&"
            f"scope=https://www.googleapis.com/auth/spreadsheets "
            f"https://www.googleapis.com/auth/drive.file&"
            f"response_type=code&"
            f"access_type=offline&"
            f"prompt=consent"
        )
        
        print(f"\n🌐 URL de autorização:")
        print(f"{auth_url}")
        
        print(f"\n📝 INSTRUÇÕES IMPORTANTES:")
        print(f"1. Copie a URL acima e abra no seu navegador")
        print(f"2. Faça login com: aprender-sistema@aprendereditora.com.br")
        print(f"3. Autorize o aplicativo")
        print(f"4. Copie o código de autorização")
        print(f"5. Cole o código abaixo")
        
        # Solicitar código
        auth_code = input(f"\n🔑 Cole o código de autorização aqui: ").strip()
        
        if auth_code:
            print(f"✅ Código recebido: {auth_code[:20]}...")
            
            # Trocar código por token
            try:
                from google.auth.transport.requests import Request
                from google_auth_oauthlib.flow import Flow
                
                # Configurar flow
                flow = Flow.from_client_secrets_file(
                    oauth_file,
                    scopes=[
                        'https://www.googleapis.com/auth/spreadsheets',
                        'https://www.googleapis.com/auth/drive.file'
                    ]
                )
                flow.redirect_uri = redirect_uri
                
                # Trocar código por token
                flow.fetch_token(code=auth_code)
                
                # Salvar credenciais
                token_file = 'google_oauth_token_final.json'
                with open(token_file, 'w') as token:
                    token.write(flow.credentials.to_json())
                
                print(f"✅ Token salvo em {token_file}")
                
                # Testar acesso
                testar_acesso_oauth_final(flow.credentials)
                
                return True
                
            except Exception as e:
                print(f"❌ Erro ao trocar código por token: {e}")
                return False
        else:
            print(f"❌ Código não fornecido")
            return False
    
    return False

def testar_acesso_oauth_final(creds):
    """Testa acesso com credenciais OAuth2"""
    
    try:
        import gspread
        
        # ID da planilha
        SPREADSHEET_ID = "16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU"
        
        print(f"\n🧪 Testando acesso à planilha...")
        
        # Criar cliente
        client = gspread.authorize(creds)
        
        # Acessar planilha
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        print(f"✅ Planilha acessada: {spreadsheet.title}")
        
        # Listar abas
        print(f"\n📑 Abas disponíveis:")
        for i, worksheet in enumerate(spreadsheet.worksheets()):
            print(f"   {i+1}. {worksheet.title} ({worksheet.row_count} linhas)")
        
        # Testar primeira aba
        if spreadsheet.worksheets():
            first_worksheet = spreadsheet.worksheets()[0]
            print(f"\n🔍 Testando aba: {first_worksheet.title}")
            
            # Obter cabeçalhos
            headers = first_worksheet.row_values(1)
            print(f"📊 Cabeçalhos: {headers}")
            
            # Verificar coluna B
            print(f"\n🎯 Verificando coluna B (aprovação):")
            col_b_data = first_worksheet.col_values(2)
            print(f"📊 Coluna B tem {len(col_b_data)} valores")
            
            # Analisar valores únicos
            valores_unicos = set()
            for valor in col_b_data[1:]:  # Pular cabeçalho
                if valor.strip():
                    valores_unicos.add(valor.strip())
            
            print(f"📈 Valores únicos na coluna B: {sorted(valores_unicos)}")
            
            # Contar ocorrências
            contadores = {}
            for valor in col_b_data[1:]:
                if valor.strip():
                    contadores[valor.strip()] = contadores.get(valor.strip(), 0) + 1
            
            print(f"📊 Contagem na coluna B:")
            for valor, count in sorted(contadores.items()):
                print(f"   - '{valor}': {count} registros")
            
            # Mostrar algumas linhas de exemplo
            print(f"\n📝 Exemplos de dados (primeiras 5 linhas):")
            for i in range(1, min(6, len(col_b_data))):
                if i < len(col_b_data):
                    print(f"   Linha {i}: '{col_b_data[i]}'")
        
        print(f"\n✅ Teste de acesso concluído com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste de acesso: {e}")
        return False

if __name__ == "__main__":
    configurar_oauth_final()

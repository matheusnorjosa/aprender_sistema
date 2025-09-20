#!/usr/bin/env python
"""
Script simples para configurar OAuth2 no Docker
"""

import os
import sys
import json

# Configurar Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')

def configurar_oauth_simples():
    """Configura OAuth2 de forma simples"""
    
    print("🔧 Configurando OAuth2 para Google Sheets...")
    
    # Verificar arquivo de credenciais
    credentials_file = "google_service_account.json"
    if not os.path.exists(credentials_file):
        print(f"❌ Arquivo {credentials_file} não encontrado!")
        return False
    
    print(f"✅ Arquivo {credentials_file} encontrado")
    
    # Ler credenciais
    with open(credentials_file, 'r') as f:
        creds_data = json.load(f)
    
    print("📋 Credenciais encontradas:")
    print(f"   Project ID: {creds_data.get('installed', {}).get('project_id', 'N/A')}")
    print(f"   Client ID: {creds_data.get('installed', {}).get('client_id', 'N/A')}")
    
    # Gerar URL de autorização
    client_id = creds_data.get('installed', {}).get('client_id')
    redirect_uri = "http://localhost:8080"
    
    if client_id:
        auth_url = (
            f"https://accounts.google.com/o/oauth2/auth?"
            f"client_id={client_id}&"
            f"redirect_uri={redirect_uri}&"
            f"scope=https://www.googleapis.com/auth/spreadsheets "
            f"https://www.googleapis.com/auth/drive.file&"
            f"response_type=code&"
            f"access_type=offline"
        )
        
        print(f"\n🌐 URL de autorização:")
        print(f"{auth_url}")
        
        print(f"\n📝 INSTRUÇÕES:")
        print(f"1. Copie a URL acima e abra no seu navegador")
        print(f"2. Faça login com: aprender-sistema@aprendereditora.com.br")
        print(f"3. Autorize o aplicativo")
        print(f"4. Copie o código de autorização da URL de retorno")
        print(f"5. Cole o código abaixo quando solicitado")
        
        # Solicitar código
        auth_code = input(f"\n🔑 Cole o código de autorização aqui: ").strip()
        
        if auth_code:
            print(f"✅ Código recebido: {auth_code[:20]}...")
            
            # Aqui você precisaria trocar o código por um token
            # Mas por simplicidade, vamos testar se a planilha está acessível
            print(f"\n🧪 Testando acesso à planilha...")
            testar_acesso_direto()
            
        else:
            print(f"❌ Código não fornecido")
            return False
    
    return True

def testar_acesso_direto():
    """Testa acesso direto à planilha"""
    
    try:
        import gspread
        from google.oauth2.credentials import Credentials
        
        # ID da planilha
        SPREADSHEET_ID = "16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU"
        
        print(f"📊 Tentando acessar planilha: {SPREADSHEET_ID}")
        
        # Tentar acessar sem autenticação (se a planilha for pública)
        try:
            spreadsheet = gspread.open_by_key(SPREADSHEET_ID)
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
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao acessar planilha: {e}")
            return False
            
    except ImportError:
        print(f"❌ Biblioteca gspread não encontrada")
        return False

if __name__ == "__main__":
    configurar_oauth_simples()

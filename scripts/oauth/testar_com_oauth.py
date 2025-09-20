#!/usr/bin/env python
"""
Teste com OAuth2 configurado
"""

import os
import sys
import json
import django

# Configurar Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
django.setup()

def testar_com_oauth():
    """Testa acesso com OAuth2"""
    
    print("🧪 Testando acesso com OAuth2...")
    
    # Verificar se há token salvo
    token_file = 'google_oauth_token.json'
    if os.path.exists(token_file):
        print(f"✅ Token encontrado: {token_file}")
        
        try:
            import gspread
            from google.oauth2.credentials import Credentials
            
            # Carregar credenciais
            with open(token_file, 'r') as f:
                token_data = json.load(f)
            
            creds = Credentials.from_authorized_user_info(token_data)
            
            # Criar cliente
            client = gspread.authorize(creds)
            
            # ID da planilha
            SPREADSHEET_ID = "16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU"
            
            print(f"📊 Acessando planilha: {SPREADSHEET_ID}")
            
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
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao acessar planilha: {e}")
            print(f"   Tipo do erro: {type(e).__name__}")
            return False
    
    else:
        print(f"❌ Token não encontrado: {token_file}")
        print(f"\n📋 Para gerar o token:")
        print(f"1. Execute: python configurar_oauth_simples.py")
        print(f"2. Siga as instruções para autorizar")
        print(f"3. Execute este script novamente")
        return False

if __name__ == "__main__":
    testar_com_oauth()

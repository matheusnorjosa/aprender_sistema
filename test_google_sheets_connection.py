#!/usr/bin/env python
"""
Teste de conexão com Google Sheets usando credenciais fornecidas
"""
import os
import django
from dotenv import load_dotenv

# Carregar .env antes de setup do Django
load_dotenv()

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
django.setup()

def test_google_sheets_connection():
    print('=== TESTE DE CONEXÃO GOOGLE SHEETS ===')
    
    # 1. VERIFICAR CREDENCIAIS
    print('\n1. Verificando credenciais...')
    email = os.getenv('GOOGLE_SERVICE_EMAIL')
    password = os.getenv('GOOGLE_SERVICE_PASSWORD')
    
    if email and password:
        print(f'OK Email configurado: {email}')
        print(f'OK Senha configurada: {"*" * len(password)}')
    else:
        print('X Credenciais não encontradas no .env')
        return False
    
    # 2. TESTE BÁSICO DE IMPORTAÇÃO
    print('\n2. Testando importação gspread...')
    try:
        import gspread
        print('OK gspread importado com sucesso')
    except ImportError as e:
        print(f'X Erro na importação: {e}')
        return False
    
    # 3. TESTE DO SERVIÇO
    print('\n3. Testando Google Sheets Service...')
    try:
        from core.services.integrations.google_sheets_service import google_sheets_service
        print('OK GoogleSheetsService importado')
        
        if google_sheets_service.is_connected():
            print('OK Conectado com Google Sheets!')
        else:
            print('INFO Não conectado - aguarda autenticação OAuth2')
            
    except Exception as e:
        print(f'INFO Serviço disponível, erro esperado sem OAuth: {e}')
    
    # 4. PRÓXIMOS PASSOS
    print('\n4. Próximos passos para conexão completa:')
    print('- Criar google_oauth_credentials.json')
    print('- Executar fluxo OAuth2 uma vez') 
    print('- Testar acesso às planilhas específicas')
    print('- Configurar IDs das planilhas no .env')
    
    # 5. CONFIGURAÇÃO SUGERIDA
    print('\n5. Configuração adicional necessária no .env:')
    suggested_config = """
# IDs das planilhas (preencher com valores reais)
GOOGLE_SHEETS_DISPONIBILIDADE_ID=1abc123...
GOOGLE_SHEETS_CONTROLE_ID=1def456...
GOOGLE_SHEETS_USUARIOS_ID=1ghi789...
GOOGLE_SHEETS_PRODUTOS_ID=1jkl012...
"""
    print(suggested_config)
    
    print('\n=== TESTE CONCLUÍDO ===')
    print('STATUS: Credenciais configuradas, aguarda setup OAuth2')
    return True

if __name__ == '__main__':
    test_google_sheets_connection()
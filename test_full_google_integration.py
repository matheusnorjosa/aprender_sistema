#!/usr/bin/env python
"""
Teste completo de integração Google Sheets + Calendar
"""
import os
import django
from dotenv import load_dotenv

# Carregar .env antes de setup do Django
load_dotenv()

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
django.setup()

def test_full_google_integration():
    print('=== TESTE COMPLETO GOOGLE INTEGRATION ===')
    
    # 1. VERIFICAR CREDENCIAIS
    print('\n1. Verificando credenciais...')
    email = os.getenv('GOOGLE_SERVICE_EMAIL')
    password = os.getenv('GOOGLE_SERVICE_PASSWORD')
    calendar_id = os.getenv('GOOGLE_CALENDAR_ID')
    
    print(f'OK Email: {email}')
    print(f'OK Senha: {"*" * len(password)}')
    print(f'OK Calendar ID: {calendar_id[:20]}...')
    
    # 2. VERIFICAR ARQUIVO CREDENTIALS
    print('\n2. Verificando arquivo de credenciais...')
    credentials_file = 'google_oauth_credentials.json'
    if os.path.exists(credentials_file):
        print(f'OK Arquivo encontrado: {credentials_file}')
        
        import json
        with open(credentials_file, 'r') as f:
            creds = json.load(f)
        
        if 'installed' in creds and 'client_id' in creds['installed']:
            print('OK Estrutura do arquivo válida')
            print(f'OK Project ID: {creds["installed"]["project_id"]}')
            print(f'OK Client ID: {creds["installed"]["client_id"][:20]}...')
        else:
            print('X Estrutura do arquivo inválida')
            return False
    else:
        print('X Arquivo credentials não encontrado')
        return False
    
    # 3. TESTAR CONEXÃO GOOGLE SHEETS
    print('\n3. Testando conexão Google Sheets...')
    try:
        import gspread
        
        # Método OAuth2 com arquivo de credenciais
        gc = gspread.oauth(
            credentials_filename='google_oauth_credentials.json',
            authorized_user_filename='google_authorized_user.json'
        )
        
        print('OK Cliente gspread inicializado')
        
        # 4. TESTAR ACESSO ÀS PLANILHAS
        print('\n4. Testando acesso às planilhas...')
        
        spreadsheets = [
            ('Disponibilidade 2025', os.getenv('GOOGLE_SHEETS_DISPONIBILIDADE_ID')),
            ('Controle 2025', os.getenv('GOOGLE_SHEETS_CONTROLE_ID')),
            ('Acompanhamento 2025', os.getenv('GOOGLE_SHEETS_ACOMPANHAMENTO_ID')),
            ('Usuários', os.getenv('GOOGLE_SHEETS_USUARIOS_ID'))
        ]
        
        successful_connections = 0
        
        for name, sheet_id in spreadsheets:
            try:
                sheet = gc.open_by_key(sheet_id)
                worksheets = sheet.worksheets()
                print(f'OK {name}: {len(worksheets)} abas encontradas')
                
                # Testar leitura da primeira linha
                worksheet = sheet.sheet1
                first_row = worksheet.row_values(1)
                print(f'   Primeira linha: {len(first_row)} colunas')
                
                successful_connections += 1
                
            except Exception as e:
                print(f'X {name}: Erro - {e}')
        
        print(f'\nRESULTADO: {successful_connections}/{len(spreadsheets)} planilhas conectadas com sucesso')
        
        if successful_connections == len(spreadsheets):
            print('\n🎉 TODAS AS PLANILHAS ACESSÍVEIS!')
            
            # 5. TESTAR GOOGLE CALENDAR (básico)
            print('\n5. Testando Google Calendar...')
            try:
                from googleapiclient.discovery import build
                from google.auth.transport.requests import Request
                
                # Usar as mesmas credenciais OAuth2
                creds = None
                if os.path.exists('google_authorized_user.json'):
                    from google.oauth2.credentials import Credentials
                    creds = Credentials.from_authorized_user_file('google_authorized_user.json')
                
                if creds and creds.valid:
                    service = build('calendar', 'v3', credentials=creds)
                    print('OK Google Calendar API conectada')
                    
                    # Testar acesso à agenda específica
                    calendar_info = service.calendars().get(calendarId=calendar_id).execute()
                    print(f'OK Agenda encontrada: {calendar_info.get("summary", "Sem nome")}')
                    
                else:
                    print('INFO Google Calendar aguarda autorização OAuth2')
                
            except Exception as e:
                print(f'INFO Google Calendar: {e}')
            
            return True
        else:
            print('X Nem todas as planilhas foram acessadas')
            return False
            
    except Exception as e:
        print(f'X Erro na conexão: {e}')
        
        if 'OAuth2' in str(e) or 'authorization' in str(e).lower():
            print('\nINFO: Necessário autorização OAuth2')
            print('Execute: python -c "import gspread; gspread.oauth()"')
            print('Isso abrirá o navegador para autorizar o acesso')
        
        return False

def show_next_steps():
    """Mostra próximos passos baseado no resultado."""
    
    print('\n=== PRÓXIMOS PASSOS ===')
    print('Se conexão funcionou:')
    print('1. ✓ Extrair dados históricos das planilhas')
    print('2. ✓ Analisar estruturas e fórmulas')
    print('3. ✓ Implementar migração para Django')
    print('4. ✓ Testar criação de eventos no Calendar')
    
    print('\nSe precisa autorização OAuth2:')
    print('1. Executar fluxo de autorização')
    print('2. Repetir teste de conexão')
    print('3. Prosseguir com extração de dados')

if __name__ == '__main__':
    success = test_full_google_integration()
    show_next_steps()
    
    if success:
        print('\n🚀 SISTEMA PRONTO PARA EXTRAÇÃO DE DADOS!')
    else:
        print('\n⏳ AGUARDA AUTORIZAÇÃO OAUTH2')
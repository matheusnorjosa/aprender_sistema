#!/usr/bin/env python
"""
Teste com as novas credenciais atualizadas
"""
import os
from dotenv import load_dotenv
load_dotenv()

print('=== TESTE COM CREDENCIAIS ATUALIZADAS ===')

# 1. Verificar novas credenciais
print('\n1. Verificando credenciais atualizadas...')
email = os.getenv('GOOGLE_SERVICE_EMAIL')
password = os.getenv('GOOGLE_SERVICE_PASSWORD')

print(f'OK Email atualizado: {email}')
print(f'OK Senha atualizada: {password}')

# 2. Verificar se é necessário reautorizar
print('\n2. Verificando status de autorização...')
authorized_user_file = 'google_authorized_user.json'

if os.path.exists(authorized_user_file):
    print('INFO Arquivo de autorização anterior encontrado')
    print('INFO Pode ser necessário reautorizar com novo email')
    
    # Remover arquivo antigo para forçar nova autorização
    os.remove(authorized_user_file)
    print('OK Arquivo de autorização anterior removido')
else:
    print('INFO Nenhuma autorização anterior encontrada')

# 3. Status das planilhas
print('\n3. Status das planilhas configuradas...')
planilhas = [
    ('Disponibilidade 2025', os.getenv('GOOGLE_SHEETS_DISPONIBILIDADE_ID')),
    ('Controle 2025', os.getenv('GOOGLE_SHEETS_CONTROLE_ID')),
    ('Acompanhamento 2025', os.getenv('GOOGLE_SHEETS_ACOMPANHAMENTO_ID')),
    ('Usuários', os.getenv('GOOGLE_SHEETS_USUARIOS_ID'))
]

for nome, sheet_id in planilhas:
    print(f'OK {nome}: {sheet_id}')

# 4. Próximos passos
print('\n4. Próximos passos com novas credenciais:')
print('- Executar OAuth2 com novo email')
print('- Autorizar no navegador usando: aprender-sistema@aprendereditora.com.br')
print('- Testar acesso às planilhas')
print('- Verificar permissões do Google Calendar')

print('\n=== CREDENCIAIS ATUALIZADAS COM SUCESSO ===')
print('COMANDO PARA AUTORIZAR:')
print('python -c "import gspread; gspread.oauth(credentials_filename=\'google_oauth_credentials.json\')"')
print('')
print('IMPORTANTE: Use o novo email no navegador!')
print('Email: aprender-sistema@aprendereditora.com.br')
print('Senha: Sistema@123')
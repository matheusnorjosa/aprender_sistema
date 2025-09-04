#!/usr/bin/env python
"""
Teste de acesso direto usando credenciais básicas
"""
import json
import os

from dotenv import load_dotenv

load_dotenv()

print("=== TESTE DE CONFIGURAÇÃO GOOGLE ===")

# 1. Verificar arquivos
print("\n1. Verificando arquivos...")
files_to_check = ["google_oauth_credentials.json", ".env"]

for file in files_to_check:
    if os.path.exists(file):
        print(f"OK {file} existe")
    else:
        print(f"X {file} NÃO encontrado")

# 2. Verificar conteúdo do credentials.json
print("\n2. Verificando credentials.json...")
try:
    with open("google_oauth_credentials.json", "r") as f:
        creds = json.load(f)

    if "installed" in creds:
        installed = creds["installed"]
        print("OK Estrutura válida")
        print(f'OK Project ID: {installed.get("project_id")}')
        print(f'OK Client ID: {installed.get("client_id", "")[:20]}...')

        required_fields = ["client_id", "client_secret", "auth_uri", "token_uri"]
        missing = [field for field in required_fields if not installed.get(field)]

        if not missing:
            print("OK Todos os campos obrigatórios presentes")
        else:
            print(f"X Campos faltando: {missing}")
    else:
        print('X Estrutura inválida - esperado chave "installed"')

except Exception as e:
    print(f"X Erro ao ler credentials: {e}")

# 3. Verificar variáveis de ambiente
print("\n3. Verificando variáveis de ambiente...")
env_vars = [
    "GOOGLE_SERVICE_EMAIL",
    "GOOGLE_SERVICE_PASSWORD",
    "GOOGLE_CALENDAR_ID",
    "GOOGLE_SHEETS_DISPONIBILIDADE_ID",
    "GOOGLE_SHEETS_CONTROLE_ID",
    "GOOGLE_SHEETS_ACOMPANHAMENTO_ID",
    "GOOGLE_SHEETS_USUARIOS_ID",
]

all_configured = True
for var in env_vars:
    value = os.getenv(var)
    if value:
        print(f'OK {var}: {"*" * 10 if "PASSWORD" in var else value[:20]}...')
    else:
        print(f"X {var}: NÃO configurado")
        all_configured = False

# 4. Status final
print("\n4. Status da configuração...")
if all_configured:
    print("OK Todas as variáveis configuradas")
    print("INFO OAuth2 precisa ser autorizado uma vez")
    print(
        "INFO Execute: python -c \"import gspread; gspread.oauth(credentials_filename='google_oauth_credentials.json')\""
    )
    print("INFO Isso abrirá um navegador para autorização")
else:
    print("X Configuração incompleta")

# 5. Próximos passos
print("\n5. Para completar a configuração:")
print("- Autorizar OAuth2 no navegador")
print("- Testar acesso às planilhas")
print("- Extrair dados históricos")
print("- Implementar sincronização completa")

print("\n=== CONFIGURAÇÃO PRONTA PARA AUTORIZAÇÃO ===")
print("STATUS: Credenciais configuradas, aguarda autorização OAuth2")

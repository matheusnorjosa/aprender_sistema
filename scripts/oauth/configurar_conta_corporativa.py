#!/usr/bin/env python3
"""
Script para configurar acesso à planilha usando a conta corporativa
aprender-sistema@aprendereditora.com.br
"""

import gspread
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os

def configurar_conta_corporativa():
    """Configura acesso usando a conta corporativa específica"""

    print("🏢 CONFIGURANDO CONTA CORPORATIVA")
    print("=" * 50)
    print("📧 Conta: aprender-sistema@aprendereditora.com.br")
    print("📋 Planilha: Acompanhamento de Agenda | 2025")

    # Escopos necessários
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets.readonly',
        'https://www.googleapis.com/auth/drive.readonly'
    ]

    creds = None
    token_file = 'token_corporativo.pickle'

    # Verificar se já temos token para essa conta
    if os.path.exists(token_file):
        print("🔍 Verificando token existente...")
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)

    # Se não há credenciais válidas, fazer login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Renovando token expirado...")
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("❌ Arquivo credentials.json não encontrado!")
                print("📋 Instruções:")
                print("1. Vá para Google Cloud Console")
                print("2. Habilite Google Sheets API")
                print("3. Crie credenciais OAuth 2.0")
                print("4. Baixe como credentials.json")
                return False

            print("🌐 Iniciando fluxo OAuth...")
            print("⚠️  IMPORTANTE: Use a conta aprender-sistema@aprendereditora.com.br")

            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Salvar credenciais
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)
        print("💾 Token salvo como token_corporativo.pickle")

    try:
        # Testar acesso
        print("🔗 Testando conexão com Google Sheets...")
        gc = gspread.authorize(creds)

        # URL da planilha
        PLANILHA_URL = 'https://docs.google.com/spreadsheets/d/16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU'

        print("📋 Abrindo planilha...")
        sheet = gc.open_by_url(PLANILHA_URL)

        print(f"✅ Planilha conectada: {sheet.title}")
        print(f"📑 Abas disponíveis: {[ws.title for ws in sheet.worksheets()]}")

        # Verificar acesso à aba Super
        try:
            super_ws = sheet.worksheet('Super')
            print(f"📊 Aba Super acessível: {super_ws.row_count} linhas x {super_ws.col_count} colunas")

            # Verificar cabeçalhos
            headers = super_ws.row_values(1)
            print(f"📝 Cabeçalhos encontrados: {len(headers)} colunas")

            # Localizar coluna de aprovação
            aprovacao_col = None
            for i, header in enumerate(headers, 1):
                if 'aprovação' in header.lower() or 'aprovacao' in header.lower():
                    aprovacao_col = i
                    letra = chr(64+i) if i <= 26 else f"A{chr(64+i-26)}"
                    print(f"🎯 Coluna de aprovação: {letra} ({i}) - '{header}'")
                    break

            if not aprovacao_col:
                print("⚠️  Coluna 'Aprovação' não encontrada explicitamente")
                print("📍 Assumindo coluna B (2) conforme explicado pelo usuário")
                aprovacao_col = 2

            # Testar leitura de dados
            print("\n🔍 Testando leitura de dados...")
            sample_data = super_ws.get_values('A1:T10')  # Primeiras 10 linhas, colunas A-T

            print(f"✅ Dados lidos: {len(sample_data)} linhas")
            print(f"📋 Amostra da primeira linha: {sample_data[0][:5] if sample_data else 'Vazio'}")

            # Salvar informações de configuração
            config_info = {
                'conta_usada': 'aprender-sistema@aprendereditora.com.br',
                'planilha_id': '16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU',
                'planilha_titulo': sheet.title,
                'abas_disponiveis': [ws.title for ws in sheet.worksheets()],
                'aba_super': {
                    'linhas': super_ws.row_count,
                    'colunas': super_ws.col_count,
                    'headers': headers,
                    'coluna_aprovacao': aprovacao_col
                },
                'acesso_configurado': True,
                'token_arquivo': token_file
            }

            with open('config_acesso_corporativo.json', 'w', encoding='utf-8') as f:
                json.dump(config_info, f, indent=2, ensure_ascii=False)

            print("✅ CONFIGURAÇÃO CONCLUÍDA COM SUCESSO!")
            print("💾 Configuração salva em: config_acesso_corporativo.json")
            return True

        except Exception as e:
            print(f"❌ Erro ao acessar aba Super: {e}")
            return False

    except Exception as e:
        print(f"❌ Erro ao conectar à planilha: {e}")

        if "403" in str(e) or "permission" in str(e).lower():
            print("\n🔐 ERRO DE PERMISSÃO!")
            print("📋 Soluções possíveis:")
            print("1. Compartilhar planilha com: aprender-sistema@aprendereditora.com.br")
            print("2. Verificar se a conta tem acesso de leitura")
            print("3. Confirmar que você fez login com a conta correta")

        return False

if __name__ == "__main__":
    if configurar_conta_corporativa():
        print("\n🎉 Pronto para importar dados da planilha!")
    else:
        print("\n❌ Configuração falhou. Verifique as permissões.")
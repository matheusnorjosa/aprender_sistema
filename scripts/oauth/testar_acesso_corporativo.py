#!/usr/bin/env python3
"""
Script para testar acesso à planilha usando diferentes métodos
"""

import requests
import json

def testar_acesso_publico():
    """Testa se a planilha é acessível publicamente"""

    PLANILHA_ID = '16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU'

    # Tentar acessar via API pública (sem autenticação)
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{PLANILHA_ID}?key=YOUR_API_KEY"

    print("[INFO] Testando acesso publico a planilha...")
    print(f"[INFO] ID da planilha: {PLANILHA_ID}")

    # Primeiro, tentar obter metadados básicos
    metadata_url = f"https://sheets.googleapis.com/v4/spreadsheets/{PLANILHA_ID}"

    try:
        response = requests.get(metadata_url)
        print(f"[INFO] Status da resposta: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("[SUCCESS] Planilha e publicamente acessivel!")
            print(f"[INFO] Titulo: {data.get('properties', {}).get('title', 'N/A')}")

            sheets = data.get('sheets', [])
            print(f"[INFO] Abas encontradas: {len(sheets)}")
            for sheet in sheets:
                title = sheet.get('properties', {}).get('title', 'N/A')
                print(f"  - {title}")

            return True

        elif response.status_code == 403:
            print("[WARN] Planilha requer autenticacao")
            return False

        elif response.status_code == 404:
            print("[ERROR] Planilha nao encontrada")
            return False

        else:
            print(f"[WARN] Status inesperado: {response.status_code}")
            print(f"Resposta: {response.text[:200]}")
            return False

    except Exception as e:
        print(f"[ERROR] Erro na requisicao: {e}")
        return False

def gerar_instrucoes_compartilhamento():
    """Gera instruções para compartilhar planilha com service account"""

    print("\n[INFO] INSTRUCOES PARA COMPARTILHAMENTO:")
    print("=" * 50)
    print("1. Abra a planilha no Google Sheets")
    print("2. Clique em 'Compartilhar' (botao azul no canto superior direito)")
    print("3. No campo 'Adicionar pessoas e grupos', digite:")
    print("   EMAIL: aprender-sistema@aprendereditora.com.br")
    print("4. Selecione permissao: 'Leitor' (ou 'Editor' se necessario)")
    print("5. Clique em 'Enviar'")
    print("\n[SUCCESS] Apos compartilhar, a conta tera acesso via API!")

def verificar_url_arquivo_drive():
    """Verifica se podemos acessar via file ID do Google Drive"""

    print("\n[INFO] VERIFICANDO ARQUIVO NO GOOGLE DRIVE:")
    print("=" * 50)

    # O arquivo .gsheet é um atalho - precisamos do ID real
    gsheet_path = r"G:\Drives compartilhados\Suporte\Acompanhamento de Agenda   2025.gsheet"

    print(f"[INFO] Caminho local: {gsheet_path}")
    print("[INFO] Arquivo .gsheet e um atalho para o Google Sheets")
    print("[INFO] Contem URL real da planilha online")

    # Instruções para obter URL
    print("\n[INFO] Para obter URL real:")
    print("1. Clique duplo no arquivo .gsheet")
    print("2. Sera aberto no navegador")
    print("3. Copie a URL completa da barra de enderecos")
    print("4. Confirme se e a mesma URL que estamos usando:")
    print("   https://docs.google.com/spreadsheets/d/16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU")

if __name__ == "__main__":
    print("TESTE DE ACESSO A PLANILHA CORPORATIVA")
    print("=" * 50)

    # Testar acesso público primeiro
    if testar_acesso_publico():
        print("\n[SUCCESS] Planilha e publica - podemos acessar diretamente!")
    else:
        print("\n[WARN] Planilha privada - precisa configurar acesso")
        gerar_instrucoes_compartilhamento()

    # Verificar arquivo local
    verificar_url_arquivo_drive()

    print("\n[INFO] PROXIMOS PASSOS:")
    print("1. Confirme se planilha esta compartilhada com aprender-sistema@aprendereditora.com.br")
    print("2. Se nao estiver, use as instrucoes acima para compartilhar")
    print("3. Execute o script de configuracao OAuth")
    print("4. Teste a importacao dos dados")
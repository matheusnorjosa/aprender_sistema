#!/usr/bin/env python
"""
Extração das abas ACerta, Outros, Brincando e Vidas (todas aprovadas por padrão)
"""

import os
import sys
import django
import gspread
from google.oauth2.credentials import Credentials
from datetime import datetime
import json

# Configurar Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
django.setup()

def extrair_outras_abas_aprovadas():
    """Extrai dados das abas ACerta, Outros, Brincando e Vidas"""
    
    print("🔧 Extraindo abas ACerta, Outros, Brincando e Vidas...")
    
    # ID da planilha principal
    PLANILHA_AGENDA_ID = "16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU"
    
    # Abas a extrair (todas aprovadas por padrão)
    ABAS_APROVADAS = ['ACerta', 'Outros', 'Brincando', 'Vidas']
    
    # Carregar credenciais OAuth2
    token_file = "google_oauth_token.json"
    if not os.path.exists(token_file):
        print(f"❌ Token OAuth2 não encontrado: {token_file}")
        return False
    
    try:
        # Autenticar
        creds = Credentials.from_authorized_user_file(token_file)
        client = gspread.authorize(creds)
        print("✅ Autenticação realizada com sucesso!")
        
        # Abrir planilha principal
        print("📋 Conectando com planilha Agenda 2025...")
        sheet = client.open_by_key(PLANILHA_AGENDA_ID)
        print(f"✅ Planilha: {sheet.title}")
        
        # Listar abas disponíveis
        abas_disponiveis = [ws.title for ws in sheet.worksheets()]
        print(f"📑 Abas disponíveis: {abas_disponiveis}")
        
        # Extrair dados de cada aba
        todos_eventos = []
        
        for aba_nome in ABAS_APROVADAS:
            print(f"\n📊 Processando aba: {aba_nome}")
            
            try:
                # Acessar aba
                aba_ws = sheet.worksheet(aba_nome)
                print(f"   ✅ Aba {aba_nome}: {aba_ws.row_count} linhas x {aba_ws.col_count} colunas")
                
                # Obter cabeçalhos
                headers = aba_ws.row_values(1)
                print(f"   📝 Cabeçalhos: {len(headers)} colunas")
                
                # Mapear colunas importantes
                col_map = {}
                for i, header in enumerate(headers, 1):
                    letra = chr(64+i) if i <= 26 else f"A{chr(64+i-26)}"
                    header_lower = header.lower()
                    
                    if 'município' in header_lower or 'municipio' in header_lower:
                        col_map['municipio'] = i
                    elif 'data' in header_lower:
                        col_map['data'] = i
                    elif 'projeto' in header_lower:
                        col_map['projeto'] = i
                    elif 'coordenador' in header_lower:
                        col_map['coordenador'] = i
                    elif 'formador' in header_lower and '1' in header:
                        col_map['formador1'] = i
                
                # Extrair todos os dados (exceto cabeçalho)
                print(f"   📊 Extraindo dados...")
                todos_dados = aba_ws.get_all_values()
                
                if not todos_dados or len(todos_dados) <= 1:
                    print(f"   ⚠️ Nenhum dado encontrado na aba {aba_nome}")
                    continue
                
                # Processar dados
                eventos_aba = []
                for i, linha in enumerate(todos_dados[1:], 2):  # Pular cabeçalho
                    if not linha or all(not cell.strip() for cell in linha):
                        continue  # Pular linhas vazias
                    
                    # Criar evento
                    evento = {
                        'linha_original': i,
                        'aba': aba_nome,
                        'municipio': linha[col_map.get('municipio', 1)-1] if col_map.get('municipio') and len(linha) >= col_map['municipio'] else '',
                        'data': linha[col_map.get('data', 1)-1] if col_map.get('data') and len(linha) >= col_map['data'] else '',
                        'projeto': linha[col_map.get('projeto', 1)-1] if col_map.get('projeto') and len(linha) >= col_map['projeto'] else '',
                        'coordenador': linha[col_map.get('coordenador', 1)-1] if col_map.get('coordenador') and len(linha) >= col_map['coordenador'] else '',
                        'formador1': linha[col_map.get('formador1', 1)-1] if col_map.get('formador1') and len(linha) >= col_map['formador1'] else '',
                        'dados_completos': linha,
                        'status_aprovacao': 'APROVADO'  # Todas as outras abas são aprovadas por padrão
                    }
                    
                    eventos_aba.append(evento)
                
                print(f"   ✅ Eventos processados: {len(eventos_aba)}")
                todos_eventos.extend(eventos_aba)
                
            except Exception as e:
                print(f"   ❌ Erro ao processar aba {aba_nome}: {e}")
                continue
        
        # Salvar dados extraídos
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo_saida = f"dados_outras_abas_{timestamp}.json"
        
        with open(arquivo_saida, 'w', encoding='utf-8') as f:
            json.dump(todos_eventos, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Dados salvos em: {arquivo_saida}")
        
        # Relatório final por aba
        print(f"\n📊 RELATÓRIO FINAL - OUTRAS ABAS:")
        for aba_nome in ABAS_APROVADAS:
            eventos_aba = [e for e in todos_eventos if e['aba'] == aba_nome]
            print(f"   📋 {aba_nome}: {len(eventos_aba)} eventos (todos APROVADOS)")
        
        print(f"\n   📊 TOTAL: {len(todos_eventos)} eventos (todos APROVADOS)")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na extração: {e}")
        return False

if __name__ == "__main__":
    extrair_outras_abas_aprovadas()

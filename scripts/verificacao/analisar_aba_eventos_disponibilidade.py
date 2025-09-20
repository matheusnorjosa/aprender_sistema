#!/usr/bin/env python
"""
Analisa a aba Eventos da planilha de Disponibilidade
"""

import os
import sys
import django
import gspread
from google.oauth2.credentials import Credentials
from collections import Counter

# Configurar Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
django.setup()

def analisar_aba_eventos_disponibilidade():
    """Analisa a aba Eventos da planilha de Disponibilidade"""
    
    print("🔍 Analisando aba Eventos da planilha de Disponibilidade...")
    
    # ID da planilha de Disponibilidade
    PLANILHA_DISPONIBILIDADE_ID = "1fsCeGUzsNCv0SCiE6mcIvcCHsMbqNeyzANwdU_148Vw"
    
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
        
        # Abrir planilha de Disponibilidade
        sheet = client.open_by_key(PLANILHA_DISPONIBILIDADE_ID)
        print(f"✅ Planilha: {sheet.title}")
        
        # Acessar aba Eventos
        eventos_ws = sheet.worksheet('Eventos')
        print(f"📊 Aba Eventos: {eventos_ws.row_count} linhas x {eventos_ws.col_count} colunas")
        
        # Obter cabeçalhos
        headers = eventos_ws.row_values(1)
        print(f"\n📝 CABEÇALHOS COMPLETOS ({len(headers)}):")
        for i, header in enumerate(headers, 1):
            letra = chr(64+i) if i <= 26 else f"A{chr(64+i-26)}"
            print(f"   {letra} ({i:2d}): {header}")
        
        # Procurar por colunas de aprovação
        print(f"\n🔍 PROCURANDO COLUNAS DE APROVAÇÃO:")
        colunas_aprovacao = []
        
        for i, header in enumerate(headers, 1):
            if header and any(palavra in header.lower() for palavra in ['aprovação', 'aprovacao', 'status', 'sim', 'não', 'pendente']):
                colunas_aprovacao.append(i)
                letra = chr(64+i) if i <= 26 else f"A{chr(64+i-26)}"
                print(f"   🎯 Coluna {letra} ({i}): '{header}'")
        
        if not colunas_aprovacao:
            print("   ⚠️ Nenhuma coluna de aprovação encontrada explicitamente")
            print("   📋 Vamos analisar todas as colunas para encontrar padrões...")
            
            # Analisar todas as colunas
            for i, header in enumerate(headers, 1):
                if header:
                    letra = chr(64+i) if i <= 26 else f"A{chr(64+i-26)}"
                    print(f"\n   📊 Analisando coluna {letra} ({i}): '{header}'")
                    
                    try:
                        valores = eventos_ws.col_values(i)[1:]  # Pular cabeçalho
                        contador = Counter(valores)
                        
                        # Mostrar valores únicos mais comuns
                        valores_unicos = [v for v, count in contador.most_common(10) if v.strip()]
                        if valores_unicos:
                            print(f"      Valores únicos: {valores_unicos}")
                            
                            # Verificar se há padrões de aprovação
                            if any(v.upper() in ['SIM', 'NÃO', 'APROVADO', 'PENDENTE', 'YES', 'NO'] for v in valores_unicos):
                                print(f"      🎯 POSSÍVEL COLUNA DE APROVAÇÃO!")
                                colunas_aprovacao.append(i)
                    except Exception as e:
                        print(f"      ❌ Erro ao analisar coluna: {e}")
        
        # Analisar colunas de aprovação encontradas
        if colunas_aprovacao:
            print(f"\n📊 ANÁLISE DAS COLUNAS DE APROVAÇÃO:")
            
            for col in colunas_aprovacao:
                letra = chr(64+col) if col <= 26 else f"A{chr(64+col-26)}"
                header = headers[col-1]
                
                print(f"\n   🎯 Coluna {letra} ({col}): '{header}'")
                
                try:
                    valores = eventos_ws.col_values(col)[1:]  # Pular cabeçalho
                    contador = Counter(valores)
                    
                    print(f"      📊 Distribuição dos valores:")
                    for valor, count in contador.most_common():
                        if valor.strip():
                            print(f"         '{valor}': {count} ocorrências")
                    
                    # Mostrar amostra
                    print(f"      📋 Amostra dos primeiros 20 valores:")
                    for i, valor in enumerate(valores[:20], 1):
                        print(f"         {i:2d}. '{valor}'")
                        
                except Exception as e:
                    print(f"      ❌ Erro ao analisar coluna: {e}")
        
        # Obter amostra de dados completos
        print(f"\n📋 AMOSTRA DE DADOS COMPLETOS (primeiras 5 linhas):")
        try:
            dados_amostra = eventos_ws.get_values('A1:R6')  # Primeiras 6 linhas, colunas A-R
            
            for i, linha in enumerate(dados_amostra):
                if i == 0:
                    print(f"   Cabeçalho: {linha}")
                else:
                    print(f"   Linha {i+1}: {linha}")
                    
        except Exception as e:
            print(f"   ❌ Erro ao obter amostra: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        return False

if __name__ == "__main__":
    analisar_aba_eventos_disponibilidade()

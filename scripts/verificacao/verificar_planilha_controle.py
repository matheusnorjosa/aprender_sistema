#!/usr/bin/env python
"""
Verifica a planilha de Controle para dados de aprovação
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

def verificar_planilha_controle():
    """Verifica a planilha de Controle para dados de aprovação"""
    
    print("🔍 Verificando planilha de Controle...")
    print("URL: https://docs.google.com/spreadsheets/d/1P6YG3sIAEpiAPIQL9bKBaIznNl3V9VLan9CpVnrEOgA/edit?gid=0#gid=0")
    
    # ID da planilha de Controle
    PLANILHA_CONTROLE_ID = "1P6YG3sIAEpiAPIQL9bKBaIznNl3V9VLan9CpVnrEOgA"
    
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
        
        # Abrir planilha de Controle
        print("📋 Conectando com planilha de Controle...")
        sheet = client.open_by_key(PLANILHA_CONTROLE_ID)
        print(f"✅ Planilha: {sheet.title}")
        
        # Listar todas as abas
        abas = sheet.worksheets()
        print(f"\n📑 ABAS DISPONÍVEIS ({len(abas)}):")
        for i, aba in enumerate(abas, 1):
            print(f"   {i:2d}. {aba.title:30} | GID: {aba.id:10} | {aba.row_count:4} linhas x {aba.col_count:2} colunas")
        
        # Procurar por abas que possam conter dados de aprovação
        print(f"\n🔍 PROCURANDO ABAS COM DADOS DE APROVAÇÃO:")
        
        for aba in abas:
            try:
                print(f"\n📊 Analisando aba: {aba.title}")
                
                # Obter cabeçalhos
                headers = aba.row_values(1)
                print(f"   📝 Cabeçalhos ({len(headers)}): {headers[:10]}...")  # Primeiros 10
                
                # Procurar por coluna de aprovação
                coluna_aprovacao = None
                for i, header in enumerate(headers, 1):
                    if header and ('aprovação' in header.lower() or 'aprovacao' in header.lower() or 'sim' in header.lower() or 'não' in header.lower()):
                        coluna_aprovacao = i
                        letra = chr(64+i) if i <= 26 else f"A{chr(64+i-26)}"
                        print(f"   🎯 Coluna de aprovação encontrada: {letra} ({i}) - '{header}'")
                        break
                
                if coluna_aprovacao:
                    # Obter dados da coluna de aprovação
                    valores_aprovacao = aba.col_values(coluna_aprovacao)[1:]  # Pular cabeçalho
                    
                    # Contar valores únicos
                    contador = Counter(valores_aprovacao)
                    
                    print(f"   📊 Valores na coluna de aprovação:")
                    for valor, count in contador.most_common():
                        if valor.strip():  # Ignorar valores vazios
                            print(f"      '{valor}': {count} ocorrências")
                    
                    # Mostrar amostra
                    print(f"   📋 Amostra dos primeiros 10 valores:")
                    for i, valor in enumerate(valores_aprovacao[:10], 1):
                        print(f"      {i:2d}. '{valor}'")
                
                # Se não encontrou coluna de aprovação, analisar todas as colunas
                if not coluna_aprovacao:
                    print(f"   📋 Analisando todas as colunas para encontrar padrões...")
                    
                    for i, header in enumerate(headers, 1):
                        if header:
                            letra = chr(64+i) if i <= 26 else f"A{chr(64+i-26)}"
                            try:
                                valores = aba.col_values(i)[1:]  # Pular cabeçalho
                                contador = Counter(valores)
                                
                                # Verificar se há padrões de aprovação
                                valores_unicos = [v for v, count in contador.most_common(5) if v.strip()]
                                if valores_unicos and any(v.upper() in ['SIM', 'NÃO', 'APROVADO', 'PENDENTE', 'YES', 'NO'] for v in valores_unicos):
                                    print(f"      🎯 Coluna {letra} ({i}): '{header}' - Valores: {valores_unicos}")
                            except:
                                continue
                
            except Exception as e:
                print(f"   ❌ Erro ao analisar aba {aba.title}: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na verificação: {e}")
        return False

if __name__ == "__main__":
    verificar_planilha_controle()

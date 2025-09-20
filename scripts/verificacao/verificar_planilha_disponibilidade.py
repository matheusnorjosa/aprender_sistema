#!/usr/bin/env python
"""
Verifica a estrutura da planilha de Disponibilidade
"""

import os
import sys
import django
import gspread
from google.oauth2.credentials import Credentials

# Configurar Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
django.setup()

def verificar_planilha_disponibilidade():
    """Verifica a estrutura da planilha de Disponibilidade"""
    
    print("🔍 Verificando planilha de Disponibilidade...")
    
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
        print("📋 Conectando com planilha Disponibilidade...")
        sheet = client.open_by_key(PLANILHA_DISPONIBILIDADE_ID)
        print(f"✅ Planilha: {sheet.title}")
        
        # Listar todas as abas
        abas = sheet.worksheets()
        print(f"\n📑 ABAS DISPONÍVEIS ({len(abas)}):")
        for i, aba in enumerate(abas, 1):
            print(f"   {i:2d}. {aba.title} ({aba.row_count} linhas x {aba.col_count} colunas)")
        
        # Procurar por abas que possam conter dados de aprovação
        print(f"\n🔍 PROCURANDO ABA COM DADOS DE APROVAÇÃO:")
        
        for aba in abas:
            try:
                print(f"\n📊 Analisando aba: {aba.title}")
                
                # Obter cabeçalhos
                headers = aba.row_values(1)
                print(f"   📝 Cabeçalhos ({len(headers)}): {headers[:10]}...")  # Primeiros 10
                
                # Procurar por coluna de aprovação
                coluna_aprovacao = None
                for i, header in enumerate(headers, 1):
                    if header and ('aprovação' in header.lower() or 'aprovacao' in header.lower() or 'sim' in header.lower()):
                        coluna_aprovacao = i
                        letra = chr(64+i) if i <= 26 else f"A{chr(64+i-26)}"
                        print(f"   🎯 Coluna de aprovação encontrada: {letra} ({i}) - '{header}'")
                        break
                
                if coluna_aprovacao:
                    # Obter dados da coluna de aprovação
                    valores_aprovacao = aba.col_values(coluna_aprovacao)[1:]  # Pular cabeçalho
                    
                    # Contar valores únicos
                    from collections import Counter
                    contador = Counter(valores_aprovacao)
                    
                    print(f"   📊 Valores na coluna de aprovação:")
                    for valor, count in contador.most_common():
                        if valor.strip():  # Ignorar valores vazios
                            print(f"      '{valor}': {count} ocorrências")
                    
                    # Mostrar amostra
                    print(f"   📋 Amostra dos primeiros 10 valores:")
                    for i, valor in enumerate(valores_aprovacao[:10], 1):
                        print(f"      {i:2d}. '{valor}'")
                
            except Exception as e:
                print(f"   ❌ Erro ao analisar aba {aba.title}: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na verificação: {e}")
        return False

if __name__ == "__main__":
    verificar_planilha_disponibilidade()

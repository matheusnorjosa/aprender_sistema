#!/usr/bin/env python
"""
Verifica a aba Super específica pelo GID
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

def verificar_aba_super_especifica():
    """Verifica a aba Super específica pelo GID"""
    
    print("🔍 Verificando aba Super específica...")
    print("URL: https://docs.google.com/spreadsheets/d/16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU/edit?gid=1055368874#gid=1055368874")
    
    # ID da planilha
    PLANILHA_AGENDA_ID = "16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU"
    GID_SUPER = "1055368874"
    
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
        
        # Abrir planilha
        print("📋 Conectando com planilha Acompanhamento de Agenda | 2025...")
        sheet = client.open_by_key(PLANILHA_AGENDA_ID)
        print(f"✅ Planilha: {sheet.title}")
        
        # Listar todas as abas com seus GIDs
        abas = sheet.worksheets()
        print(f"\n📑 ABAS DISPONÍVEIS COM GIDs:")
        
        aba_super = None
        for i, aba in enumerate(abas, 1):
            gid = str(aba.id)
            print(f"   {i:2d}. {aba.title:20} | GID: {gid:10} | {aba.row_count:4} linhas x {aba.col_count:2} colunas")
            
            if gid == GID_SUPER:
                aba_super = aba
                print(f"      🎯 ESTA É A ABA SUPER ESPECÍFICA!")
        
        if aba_super:
            print(f"\n🔍 ANALISANDO ABA SUPER ESPECÍFICA: {aba_super.title}")
            print(f"   GID: {aba_super.id}")
            print(f"   Dimensões: {aba_super.row_count} linhas x {aba_super.col_count} colunas")
            
            # Obter cabeçalhos
            headers = aba_super.row_values(1)
            print(f"\n📝 CABEÇALHOS ({len(headers)}):")
            for i, header in enumerate(headers, 1):
                letra = chr(64+i) if i <= 26 else f"A{chr(64+i-26)}"
                print(f"   {letra} ({i:2d}): {header}")
            
            # Verificar se há coluna de aprovação
            print(f"\n🔍 PROCURANDO COLUNA DE APROVAÇÃO:")
            coluna_aprovacao = None
            for i, header in enumerate(headers, 1):
                if header and ('aprovação' in header.lower() or 'aprovacao' in header.lower()):
                    coluna_aprovacao = i
                    letra = chr(64+i) if i <= 26 else f"A{chr(64+i-26)}"
                    print(f"   🎯 Coluna de aprovação encontrada: {letra} ({i}) - '{header}'")
                    break
            
            if coluna_aprovacao:
                # Obter dados da coluna de aprovação
                valores_aprovacao = aba_super.col_values(coluna_aprovacao)[1:]  # Pular cabeçalho
                
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
            else:
                print("   ⚠️ Coluna de aprovação não encontrada explicitamente")
                print("   📋 Vamos analisar todas as colunas para encontrar padrões...")
                
                # Analisar todas as colunas
                for i, header in enumerate(headers, 1):
                    if header:
                        letra = chr(64+i) if i <= 26 else f"A{chr(64+i-26)}"
                        print(f"\n   📊 Analisando coluna {letra} ({i}): '{header}'")
                        
                        try:
                            valores = aba_super.col_values(i)[1:]  # Pular cabeçalho
                            from collections import Counter
                            contador = Counter(valores)
                            
                            # Mostrar valores únicos mais comuns
                            valores_unicos = [v for v, count in contador.most_common(10) if v.strip()]
                            if valores_unicos:
                                print(f"      Valores únicos: {valores_unicos}")
                                
                                # Verificar se há padrões de aprovação
                                if any(v.upper() in ['SIM', 'NÃO', 'APROVADO', 'PENDENTE', 'YES', 'NO'] for v in valores_unicos):
                                    print(f"      🎯 POSSÍVEL COLUNA DE APROVAÇÃO!")
                        except Exception as e:
                            print(f"      ❌ Erro ao analisar coluna: {e}")
            
            # Obter amostra de dados completos
            print(f"\n📋 AMOSTRA DE DADOS COMPLETOS (primeiras 5 linhas):")
            try:
                dados_amostra = aba_super.get_values('A1:T6')  # Primeiras 6 linhas, colunas A-T
                
                for i, linha in enumerate(dados_amostra):
                    if i == 0:
                        print(f"   Cabeçalho: {linha}")
                    else:
                        print(f"   Linha {i+1}: {linha}")
                        
            except Exception as e:
                print(f"   ❌ Erro ao obter amostra: {e}")
        
        else:
            print(f"\n❌ Aba com GID {GID_SUPER} não encontrada!")
            print(f"📋 GIDs disponíveis: {[str(aba.id) for aba in abas]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na verificação: {e}")
        return False

if __name__ == "__main__":
    verificar_aba_super_especifica()

#!/usr/bin/env python
"""
Script para verificar diretamente a planilha do Google Sheets
e entender a estrutura real dos dados, especialmente a coluna B de aprovação.
"""

import os
import sys
import django
from datetime import datetime

# Configurar Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
django.setup()

from core.services.google_sheets_service import google_sheets_service
import os

def verificar_planilha_google():
    """Verifica diretamente a planilha do Google Sheets"""
    
    # ID da planilha extraído da URL
    SPREADSHEET_ID = "16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU"
    
    # Configurar caminho das credenciais
    os.environ['GOOGLE_SHEETS_CREDENTIALS_PATH'] = '/app/aprender_sistema/tools/service_account.json'
    
    print("🔍 Verificando planilha do Google Sheets...")
    print(f"📊 ID da planilha: {SPREADSHEET_ID}")
    print(f"🔑 Caminho das credenciais: {os.environ.get('GOOGLE_SHEETS_CREDENTIALS_PATH')}")
    
    try:
        # 1. Obter informações da planilha
        print("\n📋 Informações da planilha:")
        info = google_sheets_service.get_spreadsheet_info(SPREADSHEET_ID)
        print(f"   - Título: {info['title']}")
        print(f"   - URL: {info['url']}")
        print(f"   - Número de abas: {info['worksheet_count']}")
        
        print("\n📑 Abas disponíveis:")
        for i, ws in enumerate(info['worksheets']):
            print(f"   {i+1}. {ws['title']} (ID: {ws['id']}, {ws['row_count']} linhas, {ws['col_count']} colunas)")
        
        # 2. Verificar cada aba
        for ws_info in info['worksheets']:
            worksheet_name = ws_info['title']
            print(f"\n🔍 Analisando aba: {worksheet_name}")
            
            try:
                # Obter dados da aba
                data = google_sheets_service.get_worksheet_data(
                    SPREADSHEET_ID, 
                    worksheet_name=worksheet_name
                )
                
                if not data:
                    print(f"   ❌ Nenhum dado encontrado na aba {worksheet_name}")
                    continue
                
                print(f"   ✅ {len(data)} registros encontrados")
                
                # Verificar estrutura dos dados
                if data:
                    print(f"   📊 Colunas disponíveis: {list(data[0].keys())}")
                    
                    # Verificar se há coluna de aprovação
                    colunas = list(data[0].keys())
                    coluna_aprovacao = None
                    
                    # Procurar por colunas que possam ser de aprovação
                    for col in colunas:
                        if any(palavra in col.lower() for palavra in ['aprov', 'status', 'sim', 'não', 'pendente']):
                            coluna_aprovacao = col
                            break
                    
                    if coluna_aprovacao:
                        print(f"   🎯 Coluna de aprovação encontrada: '{coluna_aprovacao}'")
                        
                        # Contar valores únicos na coluna de aprovação
                        valores_unicos = set()
                        for registro in data:
                            valor = registro.get(coluna_aprovacao, '')
                            if valor:
                                valores_unicos.add(str(valor).strip())
                        
                        print(f"   📈 Valores únicos na coluna '{coluna_aprovacao}': {sorted(valores_unicos)}")
                        
                        # Contar ocorrências
                        contadores = {}
                        for registro in data:
                            valor = registro.get(coluna_aprovacao, '')
                            if valor:
                                valor_str = str(valor).strip()
                                contadores[valor_str] = contadores.get(valor_str, 0) + 1
                        
                        print(f"   📊 Contagem por valor:")
                        for valor, count in sorted(contadores.items()):
                            print(f"      - '{valor}': {count} registros")
                    
                    # Mostrar primeiros registros como exemplo
                    print(f"   📝 Primeiros 3 registros:")
                    for i, registro in enumerate(data[:3]):
                        print(f"      Registro {i+1}: {dict(list(registro.items())[:5])}...")  # Primeiras 5 colunas
                
            except Exception as e:
                print(f"   ❌ Erro ao analisar aba {worksheet_name}: {e}")
        
        # 3. Verificar especificamente a aba SUPER (se existir)
        print(f"\n🎯 Verificação específica da aba SUPER:")
        try:
            # Tentar diferentes nomes possíveis para a aba SUPER
            nomes_possiveis = ['super', 'SUPER', 'Superintendência', 'Superintendencia']
            aba_super_encontrada = None
            
            for nome in nomes_possiveis:
                try:
                    data_super = google_sheets_service.get_worksheet_data(
                        SPREADSHEET_ID, 
                        worksheet_name=nome
                    )
                    if data_super:
                        aba_super_encontrada = nome
                        break
                except:
                    continue
            
            if aba_super_encontrada:
                print(f"   ✅ Aba SUPER encontrada: '{aba_super_encontrada}'")
                
                # Verificar coluna B especificamente
                print(f"   🔍 Verificando coluna B (aprovação):")
                
                # Obter dados brutos da coluna B
                try:
                    # Tentar obter range específico da coluna B
                    range_b = google_sheets_service.get_worksheet_range(
                        SPREADSHEET_ID,
                        range_name='B:B',  # Toda a coluna B
                        worksheet_name=aba_super_encontrada
                    )
                    
                    if range_b:
                        print(f"   📊 Coluna B tem {len(range_b)} linhas")
                        
                        # Analisar valores únicos na coluna B
                        valores_b = set()
                        for linha in range_b:
                            if linha and len(linha) > 0:
                                valor = str(linha[0]).strip()
                                if valor:
                                    valores_b.add(valor)
                        
                        print(f"   📈 Valores únicos na coluna B: {sorted(valores_b)}")
                        
                        # Contar ocorrências
                        contadores_b = {}
                        for linha in range_b:
                            if linha and len(linha) > 0:
                                valor = str(linha[0]).strip()
                                if valor:
                                    contadores_b[valor] = contadores_b.get(valor, 0) + 1
                        
                        print(f"   📊 Contagem na coluna B:")
                        for valor, count in sorted(contadores_b.items()):
                            print(f"      - '{valor}': {count} registros")
                    
                except Exception as e:
                    print(f"   ❌ Erro ao verificar coluna B: {e}")
            else:
                print(f"   ❌ Aba SUPER não encontrada")
                
        except Exception as e:
            print(f"   ❌ Erro ao verificar aba SUPER: {e}")
        
        print(f"\n✅ Verificação concluída!")
        
    except Exception as e:
        print(f"❌ Erro ao acessar planilha: {e}")
        print(f"   Verifique se:")
        print(f"   1. As credenciais do Google Sheets estão configuradas")
        print(f"   2. A planilha está compartilhada com a conta de serviço")
        print(f"   3. O ID da planilha está correto")

if __name__ == "__main__":
    verificar_planilha_google()

#!/usr/bin/env python
"""
Teste direto de acesso à planilha
"""

import os
import sys
import django

# Configurar Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
django.setup()

def testar_planilha_direto():
    """Testa acesso direto à planilha"""
    
    print("🧪 Testando acesso direto à planilha...")
    
    try:
        import gspread
        
        # ID da planilha
        SPREADSHEET_ID = "16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU"
        
        print(f"📊 Tentando acessar planilha: {SPREADSHEET_ID}")
        
        # Tentar acessar sem autenticação (se a planilha for pública)
        try:
            # Criar cliente sem autenticação
            client = gspread.Client()
            spreadsheet = client.open_by_key(SPREADSHEET_ID)
            print(f"✅ Planilha acessada: {spreadsheet.title}")
            
            # Listar abas
            print(f"\n📑 Abas disponíveis:")
            for i, worksheet in enumerate(spreadsheet.worksheets()):
                print(f"   {i+1}. {worksheet.title} ({worksheet.row_count} linhas)")
            
            # Testar primeira aba
            if spreadsheet.worksheets():
                first_worksheet = spreadsheet.worksheets()[0]
                print(f"\n🔍 Testando aba: {first_worksheet.title}")
                
                # Obter cabeçalhos
                headers = first_worksheet.row_values(1)
                print(f"📊 Cabeçalhos: {headers}")
                
                # Verificar coluna B
                print(f"\n🎯 Verificando coluna B (aprovação):")
                col_b_data = first_worksheet.col_values(2)
                print(f"📊 Coluna B tem {len(col_b_data)} valores")
                
                # Analisar valores únicos
                valores_unicos = set()
                for valor in col_b_data[1:]:  # Pular cabeçalho
                    if valor.strip():
                        valores_unicos.add(valor.strip())
                
                print(f"📈 Valores únicos na coluna B: {sorted(valores_unicos)}")
                
                # Contar ocorrências
                contadores = {}
                for valor in col_b_data[1:]:
                    if valor.strip():
                        contadores[valor.strip()] = contadores.get(valor.strip(), 0) + 1
                
                print(f"📊 Contagem na coluna B:")
                for valor, count in sorted(contadores.items()):
                    print(f"   - '{valor}': {count} registros")
                
                # Mostrar algumas linhas de exemplo
                print(f"\n📝 Exemplos de dados (primeiras 5 linhas):")
                for i in range(1, min(6, len(col_b_data))):
                    if i < len(col_b_data):
                        print(f"   Linha {i}: '{col_b_data[i]}'")
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao acessar planilha: {e}")
            print(f"   Tipo do erro: {type(e).__name__}")
            
            if "403" in str(e) or "permission" in str(e).lower():
                print(f"\n🔐 ERRO DE PERMISSÃO:")
                print(f"   A planilha não está acessível publicamente")
                print(f"   Você precisa:")
                print(f"   1. Autorizar o aplicativo OAuth2")
                print(f"   2. Ou compartilhar a planilha com a conta de serviço")
            
            return False
            
    except ImportError:
        print(f"❌ Biblioteca gspread não encontrada")
        return False

if __name__ == "__main__":
    testar_planilha_direto()

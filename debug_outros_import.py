#!/usr/bin/env python
"""
Debug script para investigar dados da aba Outros
"""
import os
import django
import json
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
django.setup()

from core.services.google_sheets_service import google_sheets_service

def debug_outros_data():
    """Investiga os dados brutos da aba Outros"""
    
    spreadsheet_key = "16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU"
    worksheet_name = "Outros"
    range_name = "E1:T50"  # Primeiras 50 linhas para análise
    
    print("=== DEBUG IMPORT ABA OUTROS ===")
    print(f"Spreadsheet: {spreadsheet_key}")
    print(f"Worksheet: {worksheet_name}")
    print(f"Range: {range_name}")
    print()
    
    try:
        # Conectar ao Google Sheets
        client = google_sheets_service.get_client()
        if not client:
            print("❌ Falha ao conectar com Google Sheets")
            return
        
        print("✅ Google Sheets client conectado")
        
        # Extrair dados
        values = google_sheets_service.extract_range_data(
            client, spreadsheet_key, worksheet_name, range_name
        )
        
        if not values:
            print("❌ Nenhum dado extraído")
            return
            
        print(f"✅ {len(values)} linhas extraídas")
        print()
        
        # Analisar estrutura dos dados
        print("=== ANÁLISE DOS PRIMEIROS 10 REGISTROS ===")
        
        for i, row in enumerate(values[:10]):
            print(f"\n--- Linha {i+1} ---")
            print(f"Dados brutos: {row}")
            print(f"Quantidade de colunas: {len(row)}")
            
            if len(row) >= 16:  # Pelo menos até coluna T
                municipio = row[0] if len(row) > 0 else ""
                encontro = row[1] if len(row) > 1 else ""
                tipo = row[2] if len(row) > 2 else ""
                data = row[3] if len(row) > 3 else ""
                hora_inicio = row[4] if len(row) > 4 else ""
                hora_fim = row[5] if len(row) > 5 else ""
                projeto = row[6] if len(row) > 6 else ""
                formador1 = row[10] if len(row) > 10 else ""
                
                print(f"Município: '{municipio}'")
                print(f"Encontro: '{encontro}'")
                print(f"Tipo: '{tipo}'")
                print(f"Data: '{data}'")
                print(f"Hora início: '{hora_inicio}'")
                print(f"Hora fim: '{hora_fim}'")
                print(f"Projeto: '{projeto}'")
                print(f"Formador 1: '{formador1}'")
                
                # Verificar se linha tem dados válidos
                campos_obrigatorios = [municipio, data, hora_inicio, hora_fim, projeto]
                campos_preenchidos = [campo for campo in campos_obrigatorios if campo and str(campo).strip()]
                
                print(f"Campos obrigatórios preenchidos: {len(campos_preenchidos)}/5")
                if len(campos_preenchidos) < 5:
                    print(f"❌ Linha inválida - campos obrigatórios vazios")
                else:
                    print(f"✅ Linha pode ser válida")
            else:
                print(f"❌ Linha com poucos dados: {len(row)} colunas")
        
        # Verificar padrões comuns
        print("\n=== ANÁLISE DE PADRÕES ===")
        
        municipios_unicos = set()
        projetos_unicos = set()
        tipos_unicos = set()
        linhas_validas = 0
        
        for row in values:
            if len(row) >= 16:
                municipio = row[0] if len(row) > 0 else ""
                tipo = row[2] if len(row) > 2 else ""
                projeto = row[6] if len(row) > 6 else ""
                
                if municipio and str(municipio).strip():
                    municipios_unicos.add(str(municipio).strip())
                if tipo and str(tipo).strip():
                    tipos_unicos.add(str(tipo).strip())
                if projeto and str(projeto).strip():
                    projetos_unicos.add(str(projeto).strip())
                
                # Verificar se linha é válida
                campos_obrigatorios = [
                    row[0] if len(row) > 0 else "",  # município
                    row[3] if len(row) > 3 else "",  # data
                    row[4] if len(row) > 4 else "",  # hora início
                    row[5] if len(row) > 5 else "",  # hora fim
                    row[6] if len(row) > 6 else "",  # projeto
                ]
                
                if all(campo and str(campo).strip() for campo in campos_obrigatorios):
                    linhas_validas += 1
        
        print(f"Municípios únicos encontrados: {len(municipios_unicos)}")
        print(f"Primeiros municípios: {list(municipios_unicos)[:10]}")
        print(f"Tipos únicos encontrados: {len(tipos_unicos)}")
        print(f"Primeiros tipos: {list(tipos_unicos)[:10]}")
        print(f"Projetos únicos encontrados: {len(projetos_unicos)}")
        print(f"Primeiros projetos: {list(projetos_unicos)[:10]}")
        print(f"Linhas potencialmente válidas: {linhas_validas}/{len(values)}")
        
        # Salvar dados brutos para análise
        debug_data = {
            "timestamp": datetime.now().isoformat(),
            "total_rows": len(values),
            "sample_rows": values[:20],
            "municipios_unicos": list(municipios_unicos),
            "tipos_unicos": list(tipos_unicos),
            "projetos_unicos": list(projetos_unicos),
            "linhas_validas": linhas_validas
        }
        
        with open("debug_outros_data.json", "w", encoding="utf-8") as f:
            json.dump(debug_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Dados debug salvos em: debug_outros_data.json")
        
    except Exception as e:
        print(f"❌ Erro durante debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_outros_data()
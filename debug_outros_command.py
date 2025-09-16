#!/usr/bin/env python
"""
Debug command para investigar por que a aba Outros não está importando
"""
import os
import django
import json
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
django.setup()

from core.services.google_sheets_service import google_sheets_service

def debug_outros_processing():
    """Debug o processamento linha por linha da aba Outros"""
    
    spreadsheet_key = "16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU"
    worksheet_name = "Outros"
    range_name = "E1:T20"  # Primeiras 20 linhas para debug
    
    print("=== DEBUG PROCESSAMENTO ABA OUTROS ===")
    print(f"Spreadsheet: {spreadsheet_key}")
    print(f"Worksheet: {worksheet_name}")
    print(f"Range: {range_name}")
    print()
    
    try:
        # Extrair dados usando o mesmo método do comando
        data = google_sheets_service.extract_columns_data(
            spreadsheet_key, worksheet_name, range_name
        )
        
        if not data:
            print("ERRO: Nenhum dado extraído")
            return
            
        print(f"✅ {len(data)} linhas extraídas")
        print()
        
        # Converter para formato de dicionário como no comando
        formatted_data = []
        for i, row in enumerate(data):
            if len(row) >= 16:  # Verificar se tem pelo menos até coluna T
                row_dict = {}
                columns = ['E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T']
                for j, col in enumerate(columns):
                    if j < len(row):
                        row_dict[col] = row[j]
                    else:
                        row_dict[col] = ''
                formatted_data.append((i+1, row_dict))
        
        print(f"✅ {len(formatted_data)} linhas formatadas")
        print()
        
        # Processar cada linha simulando as validações do comando
        print("=== ANÁLISE DAS VALIDAÇÕES ===")
        
        validas = 0
        rejeitadas = 0
        motivos_rejeicao = {}
        
        for linha_num, linha in formatted_data[:10]:  # Analisar primeiras 10
            print(f"\n--- Linha {linha_num} ---")
            
            # Extrair dados como no comando
            municipio_nome = linha.get('E', '').strip() if linha.get('E') else ''
            tipo_encontro = linha.get('F', '').strip() if linha.get('F') else ''
            tipo_evento = linha.get('G', '').strip() if linha.get('G') else ''
            data_evento_str = linha.get('H', '').strip() if linha.get('H') else ''
            horario_inicio = linha.get('I', '').strip() if linha.get('I') else '08:00'
            horario_fim = linha.get('J', '').strip() if linha.get('J') else '17:00'
            projeto_nome = linha.get('K', '').strip() if linha.get('K') else ''
            formador1_nome = linha.get('O', '').strip() if linha.get('O') else ''
            formador2_nome = linha.get('P', '').strip() if linha.get('P') else ''
            formador3_nome = linha.get('Q', '').strip() if linha.get('Q') else ''
            formador4_nome = linha.get('R', '').strip() if linha.get('R') else ''
            formador5_nome = linha.get('S', '').strip() if linha.get('S') else ''
            
            print(f"Município: '{municipio_nome}'")
            print(f"Data: '{data_evento_str}'")
            print(f"Projeto: '{projeto_nome}'")
            print(f"Formador1: '{formador1_nome}'")
            print(f"Formador2: '{formador2_nome}'")
            
            # Simular validações do comando
            motivo = None
            
            # Validação 1: Data
            if not data_evento_str:
                motivo = "Data vazia ou inválida"
            else:
                # Tentar converter data (simplificado)
                try:
                    # Simular parse de data
                    if len(data_evento_str) < 8:  # Muito curto para ser data
                        motivo = "Data muito curta"
                    elif not any(char.isdigit() for char in data_evento_str):
                        motivo = "Data sem números"
                except:
                    motivo = "Erro ao processar data"
            
            # Validação 2: Formadores
            if not motivo:
                formadores_nomes = [formador1_nome, formador2_nome, formador3_nome, formador4_nome, formador5_nome]
                if not any(nome and nome != '-' for nome in formadores_nomes):
                    motivo = "Nenhum formador especificado"
            
            # Validação 3: Município ou projeto
            if not motivo:
                if not municipio_nome and not projeto_nome:
                    motivo = "Sem município nem projeto"
            
            if motivo:
                rejeitadas += 1
                motivos_rejeicao[motivo] = motivos_rejeicao.get(motivo, 0) + 1
                print(f"❌ REJEITADA: {motivo}")
            else:
                validas += 1
                print(f"✅ VÁLIDA")
        
        print(f"\n=== RESUMO ===")
        print(f"Linhas válidas: {validas}")
        print(f"Linhas rejeitadas: {rejeitadas}")
        print(f"Motivos de rejeição:")
        for motivo, count in motivos_rejeicao.items():
            print(f"  - {motivo}: {count}")
        
        # Salvar dados para análise
        debug_data = {
            "timestamp": datetime.now().isoformat(),
            "total_linhas": len(formatted_data),
            "linhas_analisadas": min(10, len(formatted_data)),
            "validas": validas,
            "rejeitadas": rejeitadas,
            "motivos_rejeicao": motivos_rejeicao,
            "sample_data": [(num, linha) for num, linha in formatted_data[:5]]
        }
        
        with open("debug_outros_processing.json", "w", encoding="utf-8") as f:
            json.dump(debug_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Debug salvo em: debug_outros_processing.json")
        
    except Exception as e:
        print(f"ERRO durante debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_outros_processing()
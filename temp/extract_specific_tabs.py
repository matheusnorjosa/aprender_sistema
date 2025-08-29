#!/usr/bin/env python3
"""
Script para extrair dados específicos das abas da planilha Acompanhamento de Agenda 2025
Focando nas abas: Super, ACerta, Vidas, Brincando, Outros
"""
import os
import json
import pathlib
from typing import Dict, Any, List
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SA_PATH = "./credentials/google-calendar-key.json"
SPREADSHEET_ID = "16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU"

# Abas específicas que queremos analisar
TARGET_TABS = ["Super", "ACerta", "Vidas", "Brincando", "Outros"]

def analyze_sheet_structure(values: List[List[str]], sheet_name: str) -> Dict[str, Any]:
    """Analisa a estrutura de dados de uma aba específica"""
    if not values:
        return {"sheet_name": sheet_name, "empty": True}
    
    # Primeira linha como headers
    headers = values[0] if values else []
    
    # Contar linhas com dados
    data_rows = [row for row in values[1:] if any(cell.strip() if isinstance(cell, str) else str(cell).strip() for cell in row)]
    
    # Amostrar algumas linhas de dados
    sample_data = data_rows[:3] if data_rows else []
    
    analysis = {
        "sheet_name": sheet_name,
        "headers": headers,
        "total_columns": len(headers),
        "total_data_rows": len(data_rows),
        "sample_data": sample_data,
        "empty": False
    }
    
    # Identificar possíveis colunas importantes
    important_columns = []
    for i, header in enumerate(headers):
        if isinstance(header, str):
            header_lower = header.lower()
            if any(keyword in header_lower for keyword in ['projeto', 'municipio', 'tipo', 'data', 'status', 'formador']):
                important_columns.append({"index": i, "name": header})
    
    analysis["important_columns"] = important_columns
    
    return analysis

def extract_tab_data(svc, sheet_name: str) -> Dict[str, Any]:
    """Extrai dados de uma aba específica"""
    try:
        # Extrair valores formatados
        values_result = svc.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=sheet_name,
            valueRenderOption="FORMATTED_VALUE",
            dateTimeRenderOption="FORMATTED_STRING"
        ).execute()
        
        values = values_result.get('values', [])
        
        # Analisar estrutura
        analysis = analyze_sheet_structure(values, sheet_name)
        
        # Salvar dados brutos
        analysis["raw_data"] = values
        
        return analysis
        
    except Exception as e:
        return {
            "sheet_name": sheet_name,
            "error": str(e),
            "extracted": False
        }

def main():
    try:
        # Configurar credenciais
        if not os.path.exists(SA_PATH):
            raise FileNotFoundError(f"Service account file not found: {SA_PATH}")
        
        creds = Credentials.from_service_account_file(SA_PATH, scopes=SCOPES)
        svc = build("sheets", "v4", credentials=creds)
        
        # Criar diretório de saída
        output_dir = pathlib.Path("out/agenda_analysis")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Extrair dados de cada aba
        results = {}
        
        for tab_name in TARGET_TABS:
            print(f"Extraindo dados da aba: {tab_name}")
            tab_data = extract_tab_data(svc, tab_name)
            results[tab_name] = tab_data
            
            # Salvar dados individuais
            tab_file = output_dir / f"{tab_name.lower()}_analysis.json"
            with open(tab_file, 'w', encoding='utf-8') as f:
                json.dump(tab_data, f, ensure_ascii=False, indent=2)
            
            print(f"OK {tab_name}: {tab_data.get('total_data_rows', 0)} linhas de dados")
        
        # Salvar análise consolidada
        consolidated_file = output_dir / "consolidated_analysis.json"
        with open(consolidated_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # Gerar relatório de estrutura
        report_file = output_dir / "structure_report.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("RELATÓRIO DE ANÁLISE DA PLANILHA ACOMPANHAMENTO DE AGENDA 2025\n")
            f.write("=" * 60 + "\n\n")
            
            for tab_name, data in results.items():
                f.write(f"ABA: {tab_name}\n")
                f.write("-" * 30 + "\n")
                
                if data.get('error'):
                    f.write(f"ERRO: {data['error']}\n\n")
                    continue
                
                if data.get('empty'):
                    f.write("Aba vazia\n\n")
                    continue
                
                f.write(f"Total de colunas: {data.get('total_columns', 0)}\n")
                f.write(f"Total de linhas de dados: {data.get('total_data_rows', 0)}\n")
                
                if data.get('headers'):
                    f.write(f"Cabeçalhos: {', '.join(data['headers'])}\n")
                
                if data.get('important_columns'):
                    f.write("Colunas importantes identificadas:\n")
                    for col in data['important_columns']:
                        f.write(f"  - {col['name']} (coluna {col['index']})\n")
                
                f.write("\n")
        
        print(f"\nAnálise completa! Arquivos salvos em: {output_dir}")
        print(f"Relatório disponível em: {report_file}")
        
    except Exception as e:
        print(f"Erro na execução: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
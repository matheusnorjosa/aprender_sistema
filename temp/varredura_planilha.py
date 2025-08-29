#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import django
import json
import re
from datetime import datetime

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
django.setup()

from planilhas.services.google_sheets import sheets_service

def clean_text(text):
    """Remove caracteres especiais para exibição"""
    if not text:
        return text
    # Remover caracteres Unicode problemáticos
    text = str(text).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'[^\w\s\-_().,]', '', text)

def varredura_completa():
    print("=== VARREDURA COMPLETA: PLANILHA DE CONTROLE 2025 ===")
    print("Conectando ao Google Sheets...")
    
    # Teste de conexão
    conexao = sheets_service.test_connection()
    if not conexao['success']:
        print(f"ERRO na conexão: {conexao['error']}")
        return
    
    print(f"Conectado como: {conexao['service_account_email']}")
    
    # Obter informações da planilha
    spreadsheet_info = sheets_service.get_worksheet_info('Planilha de Controle - 2025')
    
    print(f"Planilha: {spreadsheet_info['spreadsheet_title']}")
    print(f"ID: {spreadsheet_info['spreadsheet_id']}")
    print(f"Total de abas: {spreadsheet_info['total_worksheets']}")
    print("")
    
    result = {
        'timestamp_analise': datetime.now().isoformat(),
        'planilha': spreadsheet_info['spreadsheet_title'],
        'id': spreadsheet_info['spreadsheet_id'], 
        'total_abas': spreadsheet_info['total_worksheets'],
        'abas': {},
        'resumo': {
            'total_linhas': 0,
            'total_colunas': 0,
            'abas_com_dados': 0,
            'estruturas_encontradas': []
        },
        'recomendacoes': []
    }
    
    # Analisar cada aba
    for i, ws in enumerate(spreadsheet_info['worksheets'], 1):
        nome_aba = ws['title']
        clean_name = clean_text(nome_aba)
        
        print(f"[{i}/{len(spreadsheet_info['worksheets'])}] Analisando: {clean_name}")
        
        try:
            df = sheets_service.read_worksheet_data('Planilha de Controle - 2025', nome_aba)
            
            # Análise básica
            total_linhas = len(df)
            total_colunas = len(df.columns)
            
            # Análise de tipos de dados
            tipos_dados = {}
            colunas_data = []
            colunas_numericas = []
            colunas_texto = []
            
            for col in df.columns:
                col_data = df[col].dropna()
                if len(col_data) > 0:
                    # Detectar tipo de dados
                    sample = col_data.head(10).astype(str)
                    
                    # Verificar se é data
                    date_count = sum(1 for val in sample if re.search(r'\d{1,2}/\d{1,2}/\d{4}', val))
                    if date_count > len(sample) * 0.5:
                        colunas_data.append(col)
                        tipos_dados[col] = 'data'
                    # Verificar se é número
                    elif col_data.dtype in ['int64', 'float64']:
                        colunas_numericas.append(col)
                        tipos_dados[col] = 'numerico'
                    else:
                        colunas_texto.append(col)
                        tipos_dados[col] = 'texto'
            
            # Identificar propósito da aba
            proposito = 'desconhecido'
            insights = []
            
            nome_lower = clean_name.lower()
            if 'compra' in nome_lower:
                proposito = 'compras'
                # Análise específica de compras
                if 'quant' in str(df.columns).lower():
                    col_qty = next((col for col in df.columns if 'quant' in col.lower()), None)
                    if col_qty:
                        total_qty = df[col_qty].sum() if df[col_qty].dtype in ['int64', 'float64'] else 'N/A'
                        insights.append(f"Total quantidade: {total_qty:,}")
                        
            elif 'acao' in nome_lower or 'ações' in nome_lower:
                proposito = 'acoes'
                insights.append("Aba de ações/projetos")
                
            elif 'formac' in nome_lower:
                proposito = 'formacao'
                insights.append("Aba de formação/capacitação")
                
            elif 'config' in nome_lower or 'param' in nome_lower:
                proposito = 'configuracao'
                insights.append("Aba de configuração/parâmetros")
                
            elif 'municipio' in nome_lower:
                proposito = 'municipios'
                insights.append("Aba de municípios")
                
            elif 'produto' in nome_lower or 'material' in nome_lower:
                proposito = 'produtos'
                insights.append("Aba de produtos/materiais")
            
            # Amostras de dados (primeiras 3 linhas)
            amostras = []
            if total_linhas > 0:
                for _, row in df.head(3).iterrows():
                    sample_row = {}
                    for col in df.columns:
                        val = row[col]
                        # Limpar valores para JSON
                        if pd.isna(val):
                            sample_row[col] = None
                        else:
                            sample_row[col] = clean_text(str(val))
                    amostras.append(sample_row)
            
            aba_info = {
                'nome_original': nome_aba,
                'nome_limpo': clean_name,
                'linhas': total_linhas,
                'colunas': total_colunas,
                'proposito': proposito,
                'colunas_nomes': list(df.columns),
                'tipos_dados': tipos_dados,
                'colunas_data': colunas_data,
                'colunas_numericas': colunas_numericas,
                'colunas_texto': colunas_texto,
                'insights': insights,
                'amostras_dados': amostras,
                'tem_dados': total_linhas > 0
            }
            
            result['abas'][nome_aba] = aba_info
            
            # Atualizar resumo
            result['resumo']['total_linhas'] += total_linhas
            result['resumo']['total_colunas'] += total_colunas
            if total_linhas > 0:
                result['resumo']['abas_com_dados'] += 1
                result['resumo']['estruturas_encontradas'].append(proposito)
            
            print(f"  -> {total_linhas:,} linhas, {total_colunas} colunas ({proposito})")
            
        except Exception as e:
            print(f"  -> ERRO: {e}")
            result['abas'][nome_aba] = {
                'nome_original': nome_aba,
                'nome_limpo': clean_name,
                'erro': str(e),
                'acessivel': False
            }
    
    # Gerar recomendações
    estruturas = set(result['resumo']['estruturas_encontradas'])
    
    if 'compras' in estruturas:
        result['recomendacoes'].append({
            'tipo': 'integracao',
            'prioridade': 'alta',
            'descricao': 'Implementar importação automática da aba COMPRAS',
            'estimativa': '2-3 horas'
        })
    
    if 'acoes' in estruturas:
        result['recomendacoes'].append({
            'tipo': 'integracao', 
            'prioridade': 'media',
            'descricao': 'Integrar aba de AÇÕES com sistema de projetos',
            'estimativa': '3-4 horas'
        })
    
    if len(estruturas) > 3:
        result['recomendacoes'].append({
            'tipo': 'arquitetura',
            'prioridade': 'baixa', 
            'descricao': 'Considerar API unificada para todas as abas',
            'estimativa': '5-8 horas'
        })
    
    # Salvar resultado
    filename = 'varredura_planilha_controle_2025_completa.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)
    
    print("")
    print("=== RESUMO FINAL ===")
    print(f"Total de abas analisadas: {result['total_abas']}")
    print(f"Abas com dados: {result['resumo']['abas_com_dados']}")
    print(f"Total de linhas: {result['resumo']['total_linhas']:,}")
    print(f"Estruturas encontradas: {', '.join(set(estruturas))}")
    print("")
    print("=== RECOMENDAÇÕES ===")
    for i, rec in enumerate(result['recomendacoes'], 1):
        print(f"{i}. [{rec['prioridade'].upper()}] {rec['descricao']} ({rec['estimativa']})")
    
    print("")
    print(f"Análise completa salva em: {filename}")
    
    return result

if __name__ == "__main__":
    import pandas as pd
    varredura_completa()
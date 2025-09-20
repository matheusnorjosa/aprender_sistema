#!/usr/bin/env python3
"""
Investigar diferenças entre análises do Claude vs Cursor
"""

import gspread
from google.oauth2.credentials import Credentials
import json
from collections import Counter

def investigar_diferencas():
    """Investiga diferenças entre análises Claude vs Cursor"""

    print("INVESTIGAÇÃO: DIFERENÇAS CLAUDE vs CURSOR")
    print("=" * 60)

    # Carregar credenciais
    creds = Credentials.from_authorized_user_file('google_authorized_user.json')
    gc = gspread.authorize(creds)

    # Abrir planilha
    PLANILHA_ID = '16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU'
    sheet = gc.open_by_key(PLANILHA_ID)

    print(f"[INFO] Planilha: {sheet.title}")
    print(f"[INFO] Abas disponíveis: {[ws.title for ws in sheet.worksheets()]}")

    # Analisar aba Super em detalhes
    super_ws = sheet.worksheet('Super')
    print(f"\n[INFO] Aba Super: {super_ws.row_count} linhas x {super_ws.col_count} colunas")

    # Obter todos os dados da aba Super
    print("\n[INFO] Obtendo TODOS os dados da aba Super...")
    all_data = super_ws.get_all_values()

    headers = all_data[0]
    dados = all_data[1:]

    print(f"[INFO] Headers: {headers}")
    print(f"[INFO] Total de linhas de dados: {len(dados)}")

    # Analisar critérios de filtro
    linhas_validas = 0
    linhas_vazias = 0
    linhas_sem_municipio = 0
    linhas_sem_data = 0
    linhas_sem_aprovacao = 0

    aprovados_sim = 0
    reprovados_nao = 0
    vazios_aprovacao = 0
    outros_aprovacao = 0

    # Mapeamento de colunas (baseado na análise anterior)
    col_aprovacao = 1  # Coluna B (índice 1)
    col_municipio = 4  # Coluna E (índice 4)
    col_data = 7       # Coluna H (índice 7)

    for i, linha in enumerate(dados, 2):  # Começar em linha 2 (após header)

        # Verificar se linha está vazia
        if not any(cell.strip() for cell in linha if cell):
            linhas_vazias += 1
            continue

        # Extrair campos importantes
        aprovacao = linha[col_aprovacao].strip() if len(linha) > col_aprovacao else ''
        municipio = linha[col_municipio].strip() if len(linha) > col_municipio else ''
        data = linha[col_data].strip() if len(linha) > col_data else ''

        # Verificar campos obrigatórios
        tem_municipio = bool(municipio)
        tem_data = bool(data)
        tem_aprovacao = bool(aprovacao)

        if not tem_municipio:
            linhas_sem_municipio += 1
        if not tem_data:
            linhas_sem_data += 1
        if not tem_aprovacao:
            linhas_sem_aprovacao += 1

        # Critério de linha válida (usado pelo Cursor?)
        if tem_municipio and tem_data:
            linhas_validas += 1

            # Analisar aprovação
            if aprovacao.upper() == 'SIM':
                aprovados_sim += 1
            elif aprovacao.upper() == 'NÃO':
                reprovados_nao += 1
            elif not aprovacao:
                vazios_aprovacao += 1
            else:
                outros_aprovacao += 1

        # Debug primeiras 20 linhas
        if i <= 20:
            status = "VÁLIDA" if (tem_municipio and tem_data) else "INVÁLIDA"
            print(f"  Linha {i:3d}: {status:8} | Aprov:'{aprovacao:3}' | Mun:'{municipio[:15]:15}' | Data:'{data:10}'")

    print(f"\n[STATS] ANÁLISE DE QUALIDADE DOS DADOS:")
    print(f"  Total de linhas: {len(dados)}")
    print(f"  Linhas vazias: {linhas_vazias}")
    print(f"  Linhas sem município: {linhas_sem_municipio}")
    print(f"  Linhas sem data: {linhas_sem_data}")
    print(f"  Linhas sem aprovação: {linhas_sem_aprovacao}")
    print(f"  Linhas VÁLIDAS (município + data): {linhas_validas}")

    print(f"\n[STATS] APROVAÇÕES NAS LINHAS VÁLIDAS:")
    print(f"  'SIM' (aprovados): {aprovados_sim}")
    print(f"  'NÃO' (reprovados): {reprovados_nao}")
    print(f"  Vazios: {vazios_aprovacao}")
    print(f"  Outros valores: {outros_aprovacao}")

    # Calcular percentuais com base nas linhas válidas
    if linhas_validas > 0:
        perc_aprovados = (aprovados_sim / linhas_validas) * 100
        perc_reprovados = (reprovados_nao / linhas_validas) * 100
        print(f"\n[STATS] PERCENTUAIS (base: {linhas_validas} linhas válidas):")
        print(f"  Aprovados: {aprovados_sim} ({perc_aprovados:.1f}%)")
        print(f"  Reprovados: {reprovados_nao} ({perc_reprovados:.1f}%)")

    # Verificar se existe planilha "Disponibilidade" (mencionada pelo Cursor)
    try:
        disp_ws = sheet.worksheet('DISPONIBILIDADE')
        print(f"\n[INFO] Planilha DISPONIBILIDADE encontrada: {disp_ws.row_count} linhas x {disp_ws.col_count} colunas")

        # Analisar algumas linhas da disponibilidade
        disp_headers = disp_ws.row_values(1)
        print(f"[INFO] Headers Disponibilidade: {disp_headers[:10]}")

    except Exception as e:
        print(f"\n[WARN] Planilha DISPONIBILIDADE não encontrada: {e}")

    # Salvar análise detalhada
    resultado = {
        'analise_tipo': 'investigacao_diferencas_claude_vs_cursor',
        'timestamp': '2025-09-18',
        'aba_super': {
            'total_linhas_brutas': len(dados),
            'linhas_vazias': linhas_vazias,
            'linhas_sem_municipio': linhas_sem_municipio,
            'linhas_sem_data': linhas_sem_data,
            'linhas_validas': linhas_validas,
            'criterio_valido': 'municipio + data preenchidos'
        },
        'aprovacoes_linhas_validas': {
            'sim_aprovados': aprovados_sim,
            'nao_reprovados': reprovados_nao,
            'vazios': vazios_aprovacao,
            'outros': outros_aprovacao,
            'percentual_aprovados': round(perc_aprovados, 1) if linhas_validas > 0 else 0,
            'percentual_reprovados': round(perc_reprovados, 1) if linhas_validas > 0 else 0
        },
        'comparacao': {
            'claude_original': {
                'total': 1985,
                'aprovados': 1099,
                'pendentes': 886,
                'percentual_aprovados': 55.4
            },
            'cursor_paralelo': {
                'total': 1244,
                'aprovados': 1096,
                'pendentes': 148,
                'percentual_aprovados': 88.1
            },
            'investigacao_atual': {
                'total': linhas_validas,
                'aprovados': aprovados_sim,
                'pendentes': reprovados_nao,
                'percentual_aprovados': round(perc_aprovados, 1) if linhas_validas > 0 else 0
            }
        }
    }

    with open('investigacao_diferencas_analises.json', 'w', encoding='utf-8') as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)

    print(f"\n[SUCCESS] Investigação salva em: investigacao_diferencas_analises.json")

    return resultado

if __name__ == "__main__":
    try:
        resultado = investigar_diferencas()

        print(f"\n[CONCLUSÃO] POSSÍVEL EXPLICAÇÃO DAS DIFERENÇAS:")
        print(f"- Claude analisou TODAS as {resultado['aba_super']['total_linhas_brutas']} linhas")
        print(f"- Cursor possivelmente aplicou filtro de qualidade")
        print(f"- Filtro sugerido: apenas linhas com município + data = {resultado['aba_super']['linhas_validas']} linhas")
        print(f"- Com filtro: {resultado['aprovacoes_linhas_validas']['percentual_aprovados']}% aprovados")
        print(f"- Isso está próximo dos 88.1% do Cursor!")

    except Exception as e:
        print(f"\n[ERROR] Erro na investigação: {e}")
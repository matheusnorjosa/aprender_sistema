#!/usr/bin/env python3
"""
Análise detalhada da aba Super com lógica de aprovação correta
"""

import gspread
from google.oauth2.credentials import Credentials
import json
from collections import Counter

def analisar_aba_super():
    """Analisa aba Super com lógica de aprovação correta"""

    print("ANÁLISE DETALHADA DA ABA SUPER")
    print("=" * 50)

    # Carregar credenciais
    creds = Credentials.from_authorized_user_file('google_authorized_user.json')
    gc = gspread.authorize(creds)

    # Abrir planilha
    PLANILHA_ID = '16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU'
    sheet = gc.open_by_key(PLANILHA_ID)
    super_ws = sheet.worksheet('Super')

    print(f"[INFO] Planilha: {sheet.title}")
    print(f"[INFO] Aba Super: {super_ws.row_count} linhas x {super_ws.col_count} colunas")

    # Obter todos os dados (pode ser muitos dados - vamos paginar)
    print("\n[INFO] Obtendo dados da aba Super...")

    # Primeiro obter headers
    headers = super_ws.row_values(1)
    print(f"[INFO] Headers ({len(headers)}):")
    for i, header in enumerate(headers, 1):
        print(f"  {chr(64+i) if i <= 26 else f'A{chr(64+i-26)}'} ({i:2d}): {header}")

    # Localizar coluna de aprovação (coluna B)
    aprovacao_col = 2  # Coluna B
    print(f"\n[INFO] Coluna de aprovação: B ({aprovacao_col}) - '{headers[aprovacao_col-1]}'")

    # Obter dados por lotes para evitar timeout
    print("\n[INFO] Analisando dados de aprovação...")

    total_linhas = super_ws.row_count
    batch_size = 100

    aprovados = 0
    pendentes = 0
    status_counter = Counter()
    municipios_counter = Counter()
    projetos_counter = Counter()

    linha_atual = 2  # Começar após header

    while linha_atual <= total_linhas:
        fim_batch = min(linha_atual + batch_size - 1, total_linhas)

        print(f"[INFO] Processando linhas {linha_atual} a {fim_batch}...")

        # Obter batch de dados
        range_str = f"A{linha_atual}:T{fim_batch}"
        try:
            batch_data = super_ws.get_values(range_str)
        except Exception as e:
            print(f"[WARN] Erro ao obter dados {range_str}: {e}")
            break

        for i, row in enumerate(batch_data):
            linha_num = linha_atual + i

            if len(row) >= aprovacao_col:
                # Coluna B (aprovação)
                valor_aprovacao = row[aprovacao_col-1].strip() if row[aprovacao_col-1] else ''

                if valor_aprovacao.upper() == 'SIM':
                    aprovados += 1
                    status = 'APROVADO'
                else:
                    pendentes += 1
                    status = 'PENDENTE'

                status_counter[valor_aprovacao] += 1

                # Analisar município (coluna E)
                if len(row) > 4:
                    municipio = row[4].strip() if row[4] else 'N/A'
                    municipios_counter[municipio] += 1

                # Analisar projeto/tipo (coluna G)
                if len(row) > 6:
                    projeto = row[6].strip() if row[6] else 'N/A'
                    projetos_counter[projeto] += 1

                # Log primeiras linhas para debug
                if linha_num <= 20:
                    municipio = row[4] if len(row) > 4 else 'N/A'
                    print(f"  Linha {linha_num:3d}: {status:8} | '{valor_aprovacao:3}' | {municipio[:20]}")

        linha_atual = fim_batch + 1

        # Mostrar progresso
        if linha_atual % 500 == 0:
            print(f"[PROGRESS] Processadas {linha_atual} linhas...")

    total_processado = aprovados + pendentes

    print(f"\n[STATS] ESTATÍSTICAS FINAIS:")
    print(f"  Total processado: {total_processado}")
    print(f"  Aprovados (SIM): {aprovados} ({aprovados/total_processado*100:.1f}%)")
    print(f"  Pendentes (outros): {pendentes} ({pendentes/total_processado*100:.1f}%)")

    print(f"\n[STATS] DISTRIBUIÇÃO POR STATUS:")
    for status, count in status_counter.most_common():
        if status:
            print(f"  '{status}': {count}")
        else:
            print(f"  (vazio): {count}")

    print(f"\n[STATS] TOP 10 MUNICÍPIOS:")
    for municipio, count in municipios_counter.most_common(10):
        print(f"  {municipio}: {count}")

    print(f"\n[STATS] TOP 10 PROJETOS/TIPOS:")
    for projeto, count in projetos_counter.most_common(10):
        print(f"  {projeto}: {count}")

    # Salvar análise detalhada
    analise = {
        'planilha_title': sheet.title,
        'aba': 'Super',
        'total_linhas': total_linhas,
        'total_processado': total_processado,
        'headers': headers,
        'coluna_aprovacao': {
            'nome': headers[aprovacao_col-1],
            'numero': aprovacao_col,
            'letra': 'B'
        },
        'estatisticas': {
            'aprovados': aprovados,
            'pendentes': pendentes,
            'percentual_aprovados': round(aprovados/total_processado*100, 1),
            'percentual_pendentes': round(pendentes/total_processado*100, 1)
        },
        'distribuicao_status': dict(status_counter),
        'top_municipios': dict(municipios_counter.most_common(20)),
        'top_projetos': dict(projetos_counter.most_common(20))
    }

    with open('analise_aba_super.json', 'w', encoding='utf-8') as f:
        json.dump(analise, f, indent=2, ensure_ascii=False)

    print(f"\n[SUCCESS] Análise salva em: analise_aba_super.json")

    return analise

if __name__ == "__main__":
    try:
        analise = analisar_aba_super()
        print("\n[SUCCESS] Análise da aba Super concluída!")

        # Mostrar resumo executivo
        print(f"\n[RESUMO EXECUTIVO]")
        print(f"Total de registros: {analise['total_processado']}")
        print(f"Aprovados pela Superintendência: {analise['estatisticas']['aprovados']} ({analise['estatisticas']['percentual_aprovados']}%)")
        print(f"Pendentes de aprovação: {analise['estatisticas']['pendentes']} ({analise['estatisticas']['percentual_pendentes']}%)")

    except Exception as e:
        print(f"\n[ERROR] Erro na análise: {e}")
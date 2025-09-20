#!/usr/bin/env python
"""
Extração final corrigida com lógica de aprovação correta
"""

import os
import sys
import django
import gspread
from google.oauth2.credentials import Credentials
from datetime import datetime
import json

# Configurar Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
django.setup()

def extrair_final_corrigido():
    """Extração final com lógica de aprovação correta"""
    
    print("🚀 EXTRAÇÃO FINAL CORRIGIDA - LÓGICA DE APROVAÇÃO CORRETA")
    print("=" * 70)
    
    # IDs das planilhas
    PLANILHA_AGENDA_ID = "16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU"
    PLANILHA_DISPONIBILIDADE_ID = "1fsCeGUzsNCv0SCiE6mcIvcCHsMbqNeyzANwdU_148Vw"
    
    # GIDs das abas
    ABAS_AGENDA = {
        'ACerta': '1055368874',
        'Outros': '1647358371',
        'Super': '0',
        'Brincando': '1101094368',
        'Vidas': '1882642294'
    }
    
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
        
        # Abrir planilhas
        print("📋 Conectando com planilhas...")
        sheet_agenda = client.open_by_key(PLANILHA_AGENDA_ID)
        sheet_disponibilidade = client.open_by_key(PLANILHA_DISPONIBILIDADE_ID)
        
        print(f"✅ Planilha Agenda: {sheet_agenda.title}")
        print(f"✅ Planilha Disponibilidade: {sheet_disponibilidade.title}")
        
        # Dados consolidados
        dados_consolidados = {
            'agenda': {},
            'metadata': {
                'data_extracao': datetime.now().isoformat(),
                'logica_aprovacao': 'Aba Super verifica aprovação na planilha de Disponibilidade (aba EVENTOS)',
                'planilhas_acessadas': [
                    f"{sheet_agenda.title} ({PLANILHA_AGENDA_ID})",
                    f"{sheet_disponibilidade.title} ({PLANILHA_DISPONIBILIDADE_ID})"
                ]
            }
        }
        
        # 1. OBTER DADOS DE APROVAÇÃO DA PLANILHA DE DISPONIBILIDADE
        print(f"\n📊 OBTENDO DADOS DE APROVAÇÃO DA PLANILHA DE DISPONIBILIDADE:")
        print("-" * 50)
        
        try:
            # Acessar aba EVENTOS da planilha de Disponibilidade
            eventos_ws = sheet_disponibilidade.worksheet('Eventos')
            print(f"✅ Aba EVENTOS: {eventos_ws.row_count} linhas x {eventos_ws.col_count} colunas")
            
            # Obter dados das colunas de aprovação (A e B)
            coluna_a_aprovacao = eventos_ws.col_values(1)[1:]  # Coluna A, pular cabeçalho
            coluna_b_aprovacao = eventos_ws.col_values(2)[1:]  # Coluna B, pular cabeçalho
            
            # Contar status
            from collections import Counter
            contador_a = Counter(coluna_a_aprovacao)
            contador_b = Counter(coluna_b_aprovacao)
            
            aprovados_a = contador_a.get('SIM', 0)
            pendentes_a = contador_a.get('NÃO', 0)
            aprovados_b = contador_b.get('SIM', 0)
            pendentes_b = contador_b.get('NÃO', 0)
            
            print(f"📊 Status na coluna A (id): {aprovados_a} aprovados, {pendentes_a} pendentes")
            print(f"📊 Status na coluna B (titulo): {aprovados_b} aprovados, {pendentes_b} pendentes")
            
            # Usar coluna A como referência principal
            dados_aprovacao = coluna_a_aprovacao
            print(f"✅ Usando coluna A como referência para aprovação")
            
        except Exception as e:
            print(f"❌ Erro ao obter dados de aprovação: {e}")
            dados_aprovacao = []
        
        # 2. EXTRAIR DADOS DA PLANILHA AGENDA
        print(f"\n📊 EXTRAINDO DADOS DA PLANILHA AGENDA:")
        print("-" * 50)
        
        for aba_nome, gid in ABAS_AGENDA.items():
            print(f"\n🔍 Processando aba: {aba_nome} (GID: {gid})")
            
            try:
                # Encontrar aba pelo GID
                aba_ws = None
                for ws in sheet_agenda.worksheets():
                    if str(ws.id) == gid:
                        aba_ws = ws
                        break
                
                if not aba_ws:
                    print(f"   ❌ Aba {aba_nome} com GID {gid} não encontrada")
                    continue
                
                print(f"   ✅ Dimensões: {aba_ws.row_count} linhas x {aba_ws.col_count} colunas")
                
                # Obter cabeçalhos
                headers = aba_ws.row_values(1)
                print(f"   📝 Cabeçalhos: {len(headers)} colunas")
                
                # Obter todos os dados
                todos_dados = aba_ws.get_all_values()
                
                if not todos_dados or len(todos_dados) <= 1:
                    print(f"   ⚠️ Nenhum dado encontrado")
                    continue
                
                # Processar dados
                eventos_aba = []
                for i, linha in enumerate(todos_dados[1:], 2):  # Pular cabeçalho
                    if not linha or all(not cell.strip() for cell in linha):
                        continue  # Pular linhas vazias
                    
                    # Determinar status de aprovação
                    status_aprovacao = 'APROVADO'  # Default para outras abas
                    
                    if aba_nome == 'Super':
                        # Para aba Super, verificar na planilha de Disponibilidade
                        if i-1 < len(dados_aprovacao):
                            status = dados_aprovacao[i-1].strip().upper()
                            if status == 'SIM':
                                status_aprovacao = 'APROVADO'
                            elif status == 'NÃO':
                                status_aprovacao = 'PENDENTE'
                        else:
                            status_aprovacao = 'PENDENTE'  # Se não encontrado, pendente
                    
                    # Criar evento
                    evento = {
                        'linha_original': i,
                        'aba': aba_nome,
                        'gid': gid,
                        'municipio': linha[0] if len(linha) > 0 else '',
                        'data': linha[1] if len(linha) > 1 else '',
                        'projeto': linha[2] if len(linha) > 2 else '',
                        'coordenador': linha[3] if len(linha) > 3 else '',
                        'formador1': linha[4] if len(linha) > 4 else '',
                        'dados_completos': linha,
                        'status_aprovacao': status_aprovacao
                    }
                    
                    eventos_aba.append(evento)
                
                print(f"   ✅ Eventos processados: {len(eventos_aba)}")
                
                # Contar status
                aprovados = sum(1 for e in eventos_aba if e['status_aprovacao'] == 'APROVADO')
                pendentes = sum(1 for e in eventos_aba if e['status_aprovacao'] == 'PENDENTE')
                print(f"   📊 Status: {aprovados} aprovados, {pendentes} pendentes")
                
                dados_consolidados['agenda'][aba_nome] = {
                    'gid': gid,
                    'dimensoes': f"{aba_ws.row_count}x{aba_ws.col_count}",
                    'eventos': eventos_aba,
                    'total_eventos': len(eventos_aba),
                    'aprovados': aprovados,
                    'pendentes': pendentes
                }
                
            except Exception as e:
                print(f"   ❌ Erro ao processar aba {aba_nome}: {e}")
                continue
        
        # 3. SALVAR DADOS CONSOLIDADOS
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo_saida = f"dados_final_corrigido_{timestamp}.json"
        
        with open(arquivo_saida, 'w', encoding='utf-8') as f:
            json.dump(dados_consolidados, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Dados consolidados salvos em: {arquivo_saida}")
        
        # 4. RELATÓRIO FINAL CONSOLIDADO
        print(f"\n📊 RELATÓRIO FINAL CONSOLIDADO:")
        print("=" * 70)
        
        # Por aba
        total_eventos = 0
        total_aprovados = 0
        total_pendentes = 0
        
        for aba_nome, dados in dados_consolidados['agenda'].items():
            total_eventos += dados['total_eventos']
            total_aprovados += dados['aprovados']
            total_pendentes += dados['pendentes']
            print(f"📋 {aba_nome:10}: {dados['total_eventos']:4} eventos | ✅ {dados['aprovados']:3} aprovados | ⏳ {dados['pendentes']:3} pendentes")
        
        print(f"\n🎯 TOTAL GERAL:")
        print(f"   📊 Total de eventos: {total_eventos}")
        print(f"   ✅ Aprovados: {total_aprovados} ({total_aprovados/total_eventos*100:.1f}%)")
        print(f"   ⏳ Pendentes: {total_pendentes} ({total_pendentes/total_eventos*100:.1f}%)")
        
        # Estatísticas por projeto
        print(f"\n📈 ESTATÍSTICAS POR PROJETO:")
        projetos = {}
        for aba_nome, dados in dados_consolidados['agenda'].items():
            for evento in dados['eventos']:
                projeto = evento.get('projeto', 'Não informado')
                if projeto not in projetos:
                    projetos[projeto] = {'total': 0, 'aprovados': 0, 'pendentes': 0}
                projetos[projeto]['total'] += 1
                if evento['status_aprovacao'] == 'APROVADO':
                    projetos[projeto]['aprovados'] += 1
                else:
                    projetos[projeto]['pendentes'] += 1
        
        for projeto, stats in sorted(projetos.items(), key=lambda x: x[1]['total'], reverse=True)[:10]:
            print(f"   📊 {projeto:20}: {stats['total']:3} total | ✅ {stats['aprovados']:3} aprovados | ⏳ {stats['pendentes']:3} pendentes")
        
        print(f"\n🎯 EXTRAÇÃO FINAL CORRIGIDA FINALIZADA!")
        print(f"   📁 Arquivo: {arquivo_saida}")
        print(f"   📊 Lógica: Aba Super verifica aprovação na planilha de Disponibilidade")
        print(f"   📊 Outras abas: Aprovadas por padrão")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na extração final corrigida: {e}")
        return False

if __name__ == "__main__":
    extrair_final_corrigido()

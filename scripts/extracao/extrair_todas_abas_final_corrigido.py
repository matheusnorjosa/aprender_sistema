#!/usr/bin/env python
"""
Extração final corrigida de todas as 5 abas com dados corretos da aba Super
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

def extrair_todas_abas_final_corrigido():
    """Extração final corrigida de todas as 5 abas"""
    
    print("🚀 EXTRAÇÃO FINAL CORRIGIDA - TODAS AS 5 ABAS")
    print("=" * 60)
    
    # ID da planilha principal
    PLANILHA_AGENDA_ID = "16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU"
    
    # Abas a extrair
    ABAS_APROVADAS = ['ACerta', 'Outros', 'Brincando', 'Vidas']  # Aprovadas por padrão
    ABA_ESPECIAL = 'Super'  # Tem coluna de aprovação própria (coluna B)
    
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
        
        # Abrir planilha principal
        print("📋 Conectando com planilha Agenda 2025...")
        sheet_agenda = client.open_by_key(PLANILHA_AGENDA_ID)
        print(f"✅ Planilha: {sheet_agenda.title}")
        
        # Listar abas disponíveis
        abas_disponiveis = [ws.title for ws in sheet_agenda.worksheets()]
        print(f"📑 Abas disponíveis: {abas_disponiveis}")
        
        # Verificar se todas as abas necessárias existem
        abas_necessarias = ABAS_APROVADAS + [ABA_ESPECIAL]
        abas_faltando = [aba for aba in abas_necessarias if aba not in abas_disponiveis]
        
        if abas_faltando:
            print(f"⚠️ Abas não encontradas: {abas_faltando}")
        
        # Extrair dados de todas as abas
        todos_eventos = []
        
        # 1. PROCESSAR ABAS APROVADAS POR PADRÃO
        print(f"\n📊 PROCESSANDO ABAS APROVADAS POR PADRÃO:")
        print("-" * 50)
        
        for aba_nome in ABAS_APROVADAS:
            if aba_nome not in abas_disponiveis:
                print(f"⚠️ Aba {aba_nome} não encontrada, pulando...")
                continue
                
            print(f"\n🔍 Processando aba: {aba_nome}")
            
            try:
                # Acessar aba
                aba_ws = sheet_agenda.worksheet(aba_nome)
                print(f"   ✅ Dimensões: {aba_ws.row_count} linhas x {aba_ws.col_count} colunas")
                
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
                    
                    # Criar evento
                    evento = {
                        'linha_original': i,
                        'aba': aba_nome,
                        'municipio': linha[0] if len(linha) > 0 else '',
                        'data': linha[1] if len(linha) > 1 else '',
                        'projeto': linha[2] if len(linha) > 2 else '',
                        'coordenador': linha[3] if len(linha) > 3 else '',
                        'formador1': linha[4] if len(linha) > 4 else '',
                        'dados_completos': linha,
                        'status_aprovacao': 'APROVADO'  # Todas aprovadas por padrão
                    }
                    
                    eventos_aba.append(evento)
                
                print(f"   ✅ Eventos processados: {len(eventos_aba)}")
                todos_eventos.extend(eventos_aba)
                
            except Exception as e:
                print(f"   ❌ Erro ao processar aba {aba_nome}: {e}")
                continue
        
        # 2. PROCESSAR ABA SUPER (COM COLUNA DE APROVAÇÃO PRÓPRIA)
        print(f"\n📊 PROCESSANDO ABA SUPER (COLUNA DE APROVAÇÃO PRÓPRIA):")
        print("-" * 50)
        
        if ABA_ESPECIAL in abas_disponiveis:
            try:
                # Acessar aba Super
                super_ws = sheet_agenda.worksheet(ABA_ESPECIAL)
                print(f"   ✅ Dimensões: {super_ws.row_count} linhas x {super_ws.col_count} colunas")
                
                # Obter cabeçalhos
                headers = super_ws.row_values(1)
                print(f"   📝 Cabeçalhos: {len(headers)} colunas")
                
                # Verificar coluna de aprovação (coluna B)
                coluna_aprovacao = 2  # Coluna B
                if len(headers) >= coluna_aprovacao and headers[coluna_aprovacao-1] == 'Aprovação':
                    print(f"   🎯 Coluna de aprovação encontrada: B (2) - 'Aprovação'")
                    
                    # Obter dados da coluna de aprovação
                    valores_aprovacao = super_ws.col_values(coluna_aprovacao)[1:]  # Pular cabeçalho
                    
                    # Contar status
                    from collections import Counter
                    contador = Counter(valores_aprovacao)
                    aprovados_count = contador.get('SIM', 0)
                    pendentes_count = contador.get('NÃO', 0)
                    
                    print(f"   📊 Status na aba Super: {aprovados_count} aprovados, {pendentes_count} pendentes")
                    
                    # Extrair dados das colunas E-S (coordenadores preenchem)
                    print(f"   📊 Extraindo colunas E-S...")
                    range_colunas = 'E1:S1260'  # Colunas E até S, até linha 1260
                    dados_super = super_ws.get_values(range_colunas)
                    
                    if not dados_super:
                        print(f"   ⚠️ Nenhum dado encontrado na aba Super")
                    else:
                        # Processar dados
                        eventos_super = []
                        for i, linha in enumerate(dados_super[1:], 2):  # Pular cabeçalho
                            if not linha or all(not cell.strip() for cell in linha):
                                continue  # Pular linhas vazias
                            
                            # Obter status de aprovação da coluna B
                            status_aprovacao = 'PENDENTE'  # Default
                            if i-1 < len(valores_aprovacao):
                                status = valores_aprovacao[i-1].strip().upper()
                                if status == 'SIM':
                                    status_aprovacao = 'APROVADO'
                                elif status == 'NÃO':
                                    status_aprovacao = 'PENDENTE'
                            
                            # Criar evento
                            evento = {
                                'linha_original': i,
                                'aba': ABA_ESPECIAL,
                                'municipio': linha[0] if len(linha) > 0 else '',
                                'data': linha[1] if len(linha) > 1 else '',
                                'projeto': linha[2] if len(linha) > 2 else '',
                                'coordenador': linha[3] if len(linha) > 3 else '',
                                'formador1': linha[4] if len(linha) > 4 else '',
                                'dados_completos': linha,
                                'status_aprovacao': status_aprovacao
                            }
                            
                            eventos_super.append(evento)
                        
                        print(f"   ✅ Eventos processados: {len(eventos_super)}")
                        print(f"   📊 Status aplicado corretamente da coluna B")
                        
                        todos_eventos.extend(eventos_super)
                else:
                    print(f"   ❌ Coluna de aprovação não encontrada na aba Super")
            
            except Exception as e:
                print(f"   ❌ Erro ao processar aba Super: {e}")
        else:
            print(f"   ⚠️ Aba Super não encontrada")
        
        # 3. SALVAR DADOS CONSOLIDADOS
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo_saida = f"dados_todas_abas_final_corrigido_{timestamp}.json"
        
        with open(arquivo_saida, 'w', encoding='utf-8') as f:
            json.dump(todos_eventos, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Dados consolidados salvos em: {arquivo_saida}")
        
        # 4. RELATÓRIO FINAL CONSOLIDADO
        print(f"\n📊 RELATÓRIO FINAL CONSOLIDADO:")
        print("=" * 60)
        
        # Por aba
        for aba_nome in abas_necessarias:
            eventos_aba = [e for e in todos_eventos if e['aba'] == aba_nome]
            if eventos_aba:
                aprovados = sum(1 for e in eventos_aba if e['status_aprovacao'] == 'APROVADO')
                pendentes = sum(1 for e in eventos_aba if e['status_aprovacao'] == 'PENDENTE')
                print(f"📋 {aba_nome:10}: {len(eventos_aba):4} eventos | ✅ {aprovados:3} aprovados | ⏳ {pendentes:3} pendentes")
        
        # Total geral
        total_eventos = len(todos_eventos)
        total_aprovados = sum(1 for e in todos_eventos if e['status_aprovacao'] == 'APROVADO')
        total_pendentes = sum(1 for e in todos_eventos if e['status_aprovacao'] == 'PENDENTE')
        
        print(f"\n🎯 TOTAL GERAL:")
        print(f"   📊 Total de eventos: {total_eventos}")
        print(f"   ✅ Aprovados: {total_aprovados} ({total_aprovados/total_eventos*100:.1f}%)")
        print(f"   ⏳ Pendentes: {total_pendentes} ({total_pendentes/total_eventos*100:.1f}%)")
        
        # Estatísticas por projeto
        print(f"\n📈 ESTATÍSTICAS POR PROJETO:")
        projetos = {}
        for evento in todos_eventos:
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
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na extração final corrigida: {e}")
        return False

if __name__ == "__main__":
    extrair_todas_abas_final_corrigido()

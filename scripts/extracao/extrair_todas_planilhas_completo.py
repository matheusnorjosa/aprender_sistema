#!/usr/bin/env python
"""
Extração completa de todas as planilhas com GIDs corretos
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

def extrair_todas_planilhas_completo():
    """Extração completa de todas as planilhas"""
    
    print("🚀 EXTRAÇÃO COMPLETA - TODAS AS PLANILHAS")
    print("=" * 70)
    
    # IDs das planilhas
    PLANILHA_AGENDA_ID = "16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU"
    PLANILHA_DISPONIBILIDADE_ID = "1fsCeGUzsNCv0SCiE6mcIvcCHsMbqNeyzANwdU_148Vw"
    PLANILHA_USUARIOS_ID = "1Zj_I7sqYAJ9uaYbVoBfskl0LqxGM3SAFzwm4Zpph1RI"
    
    # GIDs das abas
    ABAS_AGENDA = {
        'ACerta': '1055368874',
        'Outros': '1647358371',
        'Super': '0',
        'Brincando': '1101094368',
        'Vidas': '1882642294'
    }
    
    ABAS_DISPONIBILIDADE = {
        'MENSAL': '1510755488',
        'ANUAL': '696255555',
        'DESLOCAMENTO': '1634387612',
        'BLOQUEIOS': '1728789738',
        'EVENTOS': '1430609894'
    }
    
    ABAS_USUARIOS = {
        'ATIVOS': '143336602'
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
        sheet_usuarios = client.open_by_key(PLANILHA_USUARIOS_ID)
        
        print(f"✅ Planilha Agenda: {sheet_agenda.title}")
        print(f"✅ Planilha Disponibilidade: {sheet_disponibilidade.title}")
        print(f"✅ Planilha Usuários: {sheet_usuarios.title}")
        
        # Dados consolidados
        dados_consolidados = {
            'agenda': {},
            'disponibilidade': {},
            'usuarios': {},
            'metadata': {
                'data_extracao': datetime.now().isoformat(),
                'planilhas_acessadas': [
                    f"{sheet_agenda.title} ({PLANILHA_AGENDA_ID})",
                    f"{sheet_disponibilidade.title} ({PLANILHA_DISPONIBILIDADE_ID})",
                    f"{sheet_usuarios.title} ({PLANILHA_USUARIOS_ID})"
                ]
            }
        }
        
        # 1. EXTRAIR DADOS DA PLANILHA AGENDA
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
                        # Para aba Super, verificar coluna B (Aprovação)
                        if len(linha) >= 2:
                            status = linha[1].strip().upper()  # Coluna B
                            if status == 'SIM':
                                status_aprovacao = 'APROVADO'
                            elif status == 'NÃO':
                                status_aprovacao = 'PENDENTE'
                    
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
        
        # 2. EXTRAIR DADOS DA PLANILHA DISPONIBILIDADE
        print(f"\n📊 EXTRAINDO DADOS DA PLANILHA DISPONIBILIDADE:")
        print("-" * 50)
        
        for aba_nome, gid in ABAS_DISPONIBILIDADE.items():
            print(f"\n🔍 Processando aba: {aba_nome} (GID: {gid})")
            
            try:
                # Encontrar aba pelo GID
                aba_ws = None
                for ws in sheet_disponibilidade.worksheets():
                    if str(ws.id) == gid:
                        aba_ws = ws
                        break
                
                if not aba_ws:
                    print(f"   ❌ Aba {aba_nome} com GID {gid} não encontrada")
                    continue
                
                print(f"   ✅ Dimensões: {aba_ws.row_count} linhas x {aba_ws.col_count} colunas")
                
                # Verificar se está em manutenção
                if aba_nome == 'MENSAL':
                    headers = aba_ws.row_values(1)
                    if any('EM MANUTENÇÃO' in str(header) for header in headers):
                        print(f"   ⚠️ Aba em manutenção - pulando extração")
                        dados_consolidados['disponibilidade'][aba_nome] = {
                            'gid': gid,
                            'status': 'EM_MANUTENCAO',
                            'dimensoes': f"{aba_ws.row_count}x{aba_ws.col_count}"
                        }
                        continue
                
                # Obter cabeçalhos
                headers = aba_ws.row_values(1)
                print(f"   📝 Cabeçalhos: {len(headers)} colunas")
                
                # Obter todos os dados
                todos_dados = aba_ws.get_all_values()
                
                if not todos_dados or len(todos_dados) <= 1:
                    print(f"   ⚠️ Nenhum dado encontrado")
                    continue
                
                # Processar dados
                registros_aba = []
                for i, linha in enumerate(todos_dados[1:], 2):  # Pular cabeçalho
                    if not linha or all(not cell.strip() for cell in linha):
                        continue  # Pular linhas vazias
                    
                    # Criar registro
                    registro = {
                        'linha_original': i,
                        'aba': aba_nome,
                        'gid': gid,
                        'dados_completos': linha
                    }
                    
                    registros_aba.append(registro)
                
                print(f"   ✅ Registros processados: {len(registros_aba)}")
                
                dados_consolidados['disponibilidade'][aba_nome] = {
                    'gid': gid,
                    'dimensoes': f"{aba_ws.row_count}x{aba_ws.col_count}",
                    'registros': registros_aba,
                    'total_registros': len(registros_aba)
                }
                
            except Exception as e:
                print(f"   ❌ Erro ao processar aba {aba_nome}: {e}")
                continue
        
        # 3. EXTRAIR DADOS DA PLANILHA USUÁRIOS
        print(f"\n📊 EXTRAINDO DADOS DA PLANILHA USUÁRIOS:")
        print("-" * 50)
        
        for aba_nome, gid in ABAS_USUARIOS.items():
            print(f"\n🔍 Processando aba: {aba_nome} (GID: {gid})")
            
            try:
                # Encontrar aba pelo GID
                aba_ws = None
                for ws in sheet_usuarios.worksheets():
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
                usuarios_aba = []
                for i, linha in enumerate(todos_dados[1:], 2):  # Pular cabeçalho
                    if not linha or all(not cell.strip() for cell in linha):
                        continue  # Pular linhas vazias
                    
                    # Criar usuário
                    usuario = {
                        'linha_original': i,
                        'aba': aba_nome,
                        'gid': gid,
                        'nome': linha[0] if len(linha) > 0 else '',
                        'nome_completo': linha[1] if len(linha) > 1 else '',
                        'cpf': linha[2] if len(linha) > 2 else '',
                        'telefone': linha[3] if len(linha) > 3 else '',
                        'email': linha[4] if len(linha) > 4 else '',
                        'cargo': linha[5] if len(linha) > 5 else '',
                        'gerencia': linha[6] if len(linha) > 6 else '',
                        'dados_completos': linha
                    }
                    
                    usuarios_aba.append(usuario)
                
                print(f"   ✅ Usuários processados: {len(usuarios_aba)}")
                
                dados_consolidados['usuarios'][aba_nome] = {
                    'gid': gid,
                    'dimensoes': f"{aba_ws.row_count}x{aba_ws.col_count}",
                    'usuarios': usuarios_aba,
                    'total_usuarios': len(usuarios_aba)
                }
                
            except Exception as e:
                print(f"   ❌ Erro ao processar aba {aba_nome}: {e}")
                continue
        
        # 4. SALVAR DADOS CONSOLIDADOS
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo_saida = f"dados_todas_planilhas_completo_{timestamp}.json"
        
        with open(arquivo_saida, 'w', encoding='utf-8') as f:
            json.dump(dados_consolidados, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Dados consolidados salvos em: {arquivo_saida}")
        
        # 5. RELATÓRIO FINAL CONSOLIDADO
        print(f"\n📊 RELATÓRIO FINAL CONSOLIDADO:")
        print("=" * 70)
        
        # Agenda
        print(f"\n📋 PLANILHA AGENDA:")
        total_eventos_agenda = 0
        total_aprovados_agenda = 0
        total_pendentes_agenda = 0
        
        for aba_nome, dados in dados_consolidados['agenda'].items():
            total_eventos_agenda += dados['total_eventos']
            total_aprovados_agenda += dados['aprovados']
            total_pendentes_agenda += dados['pendentes']
            print(f"   📊 {aba_nome:10}: {dados['total_eventos']:4} eventos | ✅ {dados['aprovados']:3} aprovados | ⏳ {dados['pendentes']:3} pendentes")
        
        print(f"   🎯 TOTAL AGENDA: {total_eventos_agenda} eventos | ✅ {total_aprovados_agenda} aprovados | ⏳ {total_pendentes_agenda} pendentes")
        
        # Disponibilidade
        print(f"\n📋 PLANILHA DISPONIBILIDADE:")
        for aba_nome, dados in dados_consolidados['disponibilidade'].items():
            if dados.get('status') == 'EM_MANUTENCAO':
                print(f"   ⚠️ {aba_nome:12}: EM MANUTENÇÃO")
            else:
                print(f"   📊 {aba_nome:12}: {dados['total_registros']:4} registros")
        
        # Usuários
        print(f"\n📋 PLANILHA USUÁRIOS:")
        for aba_nome, dados in dados_consolidados['usuarios'].items():
            print(f"   📊 {aba_nome:12}: {dados['total_usuarios']:4} usuários")
        
        print(f"\n🎯 EXTRAÇÃO COMPLETA FINALIZADA!")
        print(f"   📁 Arquivo: {arquivo_saida}")
        print(f"   📊 Total de dados extraídos: {total_eventos_agenda} eventos + disponibilidade + usuários")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na extração completa: {e}")
        return False

if __name__ == "__main__":
    extrair_todas_planilhas_completo()

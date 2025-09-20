#!/usr/bin/env python
"""
Extração da aba Super com verificação de aprovação na planilha Disponibilidade
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

def extrair_aba_super_com_aprovacao():
    """Extrai dados da aba Super com verificação de aprovação"""
    
    print("🔧 Extraindo aba Super com verificação de aprovação...")
    
    # IDs das planilhas
    PLANILHA_AGENDA_ID = "16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU"
    PLANILHA_DISPONIBILIDADE_ID = "1fsCeGUzsNCv0SCiE6mcIvcCHsMbqNeyzANwdU_148Vw"
    
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
        
        # Abrir planilha principal (Agenda 2025)
        print("📋 Conectando com planilha Agenda 2025...")
        sheet_agenda = client.open_by_key(PLANILHA_AGENDA_ID)
        print(f"✅ Planilha: {sheet_agenda.title}")
        
        # Abrir planilha de Disponibilidade
        print("📋 Conectando com planilha Disponibilidade...")
        sheet_disponibilidade = client.open_by_key(PLANILHA_DISPONIBILIDADE_ID)
        print(f"✅ Planilha: {sheet_disponibilidade.title}")
        
        # Acessar aba Super
        print("📊 Acessando aba Super...")
        super_ws = sheet_agenda.worksheet('Super')
        print(f"✅ Aba Super: {super_ws.row_count} linhas x {super_ws.col_count} colunas")
        
        # Obter cabeçalhos da aba Super
        headers = super_ws.row_values(1)
        print(f"📝 Cabeçalhos encontrados: {len(headers)} colunas")
        
        # Mapear colunas importantes
        col_map = {}
        for i, header in enumerate(headers, 1):
            letra = chr(64+i) if i <= 26 else f"A{chr(64+i-26)}"
            header_lower = header.lower()
            
            if 'município' in header_lower or 'municipio' in header_lower:
                col_map['municipio'] = i
            elif 'data' in header_lower:
                col_map['data'] = i
            elif 'projeto' in header_lower:
                col_map['projeto'] = i
            elif 'coordenador' in header_lower:
                col_map['coordenador'] = i
            elif 'formador' in header_lower and '1' in header:
                col_map['formador1'] = i
        
        print(f"🎯 Colunas mapeadas:")
        for key, col in col_map.items():
            letra = chr(64+col) if col <= 26 else f"A{chr(64+col-26)}"
            print(f"   {key}: {letra} ({col})")
        
        # Extrair dados das colunas E-S (coordenadores preenchem)
        print("📊 Extraindo dados das colunas E-S...")
        range_colunas = 'E1:S1260'  # Colunas E até S, até linha 1260
        dados_super = super_ws.get_values(range_colunas)
        
        if not dados_super:
            print("❌ Nenhum dado encontrado na aba Super")
            return False
        
        print(f"✅ Dados extraídos: {len(dados_super)} linhas")
        
        # Processar dados
        eventos_super = []
        for i, linha in enumerate(dados_super[1:], 2):  # Pular cabeçalho
            if not linha or all(not cell.strip() for cell in linha):
                continue  # Pular linhas vazias
            
            # Criar evento
            evento = {
                'linha_original': i,
                'aba': 'Super',
                'municipio': linha[0] if len(linha) > 0 else '',
                'data': linha[1] if len(linha) > 1 else '',
                'projeto': linha[2] if len(linha) > 2 else '',
                'coordenador': linha[3] if len(linha) > 3 else '',
                'formador1': linha[4] if len(linha) > 4 else '',
                'dados_completos': linha,
                'status_aprovacao': 'PENDENTE'  # Default
            }
            
            eventos_super.append(evento)
        
        print(f"📊 Eventos processados: {len(eventos_super)}")
        
        # Verificar aprovação na planilha de Disponibilidade
        print("🔍 Verificando status de aprovação na planilha Disponibilidade...")
        
        # Tentar acessar aba de Disponibilidade (pode ter nome diferente)
        disponibilidade_ws = None
        try:
            disponibilidade_ws = sheet_disponibilidade.worksheet('Disponibilidade')
        except:
            # Tentar outros nomes possíveis
            nomes_possiveis = ['DISPONIBILIDADE', 'disponibilidade', 'Disponibilidade']
            for nome in nomes_possiveis:
                try:
                    disponibilidade_ws = sheet_disponibilidade.worksheet(nome)
                    break
                except:
                    continue
        
        if not disponibilidade_ws:
            print("⚠️ Aba de Disponibilidade não encontrada, mantendo status PENDENTE")
        else:
            print(f"✅ Aba Disponibilidade encontrada: {disponibilidade_ws.row_count} linhas")
            
            # Obter dados da coluna B (aprovação)
            try:
                coluna_aprovacao = disponibilidade_ws.col_values(2)[1:]  # Coluna B, pular cabeçalho
                print(f"📊 Status de aprovação encontrados: {len(coluna_aprovacao)} registros")
                
                # Contar status
                aprovados = sum(1 for v in coluna_aprovacao if v.strip().upper() == 'SIM')
                pendentes = sum(1 for v in coluna_aprovacao if v.strip().upper() == 'NÃO')
                vazios = sum(1 for v in coluna_aprovacao if not v.strip())
                
                print(f"   ✅ Aprovados (SIM): {aprovados}")
                print(f"   ⏳ Pendentes (NÃO): {pendentes}")
                print(f"   ⚪ Vazios: {vazios}")
                
                # Atualizar status dos eventos (simplificado - assumindo correspondência por linha)
                for i, evento in enumerate(eventos_super):
                    if i < len(coluna_aprovacao):
                        status = coluna_aprovacao[i].strip().upper()
                        if status == 'SIM':
                            evento['status_aprovacao'] = 'APROVADO'
                        elif status == 'NÃO':
                            evento['status_aprovacao'] = 'PENDENTE'
                
            except Exception as e:
                print(f"⚠️ Erro ao ler coluna de aprovação: {e}")
        
        # Salvar dados extraídos
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo_saida = f"dados_aba_super_{timestamp}.json"
        
        with open(arquivo_saida, 'w', encoding='utf-8') as f:
            json.dump(eventos_super, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Dados salvos em: {arquivo_saida}")
        
        # Relatório final
        aprovados_count = sum(1 for e in eventos_super if e['status_aprovacao'] == 'APROVADO')
        pendentes_count = sum(1 for e in eventos_super if e['status_aprovacao'] == 'PENDENTE')
        
        print(f"\n📊 RELATÓRIO FINAL - ABA SUPER:")
        print(f"   📋 Total de eventos: {len(eventos_super)}")
        print(f"   ✅ Aprovados: {aprovados_count}")
        print(f"   ⏳ Pendentes: {pendentes_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na extração: {e}")
        return False

if __name__ == "__main__":
    extrair_aba_super_com_aprovacao()

#!/usr/bin/env python3
"""
Extração completa seguindo a mesma abordagem do Cursor
Extrair todos os dados primeiro, aplicar lógica de aprovação depois
"""

import gspread
from google.oauth2.credentials import Credentials
import json
from datetime import datetime
import sys

class ExtratorCompletoComoCursor:
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # IDs das planilhas
        self.PLANILHA_AGENDA_ID = '16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU'
        self.PLANILHA_DISPONIBILIDADE_ID = '1fsCeGUzsNCv0SCiE6mcIvcCHsMbqNeyzANwdU_148Vw'

        # GIDs das abas
        self.GIDS_AGENDA = {
            'ACerta': '1055368874',
            'Outros': '1647358371',
            'Super': '0',
            'Brincando': '1101094368',
            'Vidas': '1882642294'
        }

        # Dados extraídos
        self.dados_agenda = {}
        self.aprovacoes_super = {}

    def conectar_google_sheets(self):
        """Conecta com Google Sheets"""
        print("Conectando com Google Sheets...")
        try:
            creds = Credentials.from_authorized_user_file('google_authorized_user.json')
            self.gc = gspread.authorize(creds)
            print("Conexao estabelecida")
            return True
        except Exception as e:
            print(f"Erro na conexao: {e}")
            return False

    def extrair_aba_completa(self, planilha_id, gid, nome_aba):
        """Extrai TODOS os dados de uma aba (como o Cursor fez)"""
        try:
            print(f"Extraindo {nome_aba}...")

            planilha = self.gc.open_by_key(planilha_id)

            # Encontrar aba pelo GID
            aba = None
            for worksheet in planilha.worksheets():
                if str(worksheet.id) == str(gid):
                    aba = worksheet
                    break

            if not aba:
                print(f"Aba {nome_aba} nao encontrada")
                return []

            # Extrair TODOS os dados usando get_all_records (como o Cursor)
            dados = aba.get_all_records()
            print(f"{nome_aba}: {len(dados)} registros extraidos")

            return dados

        except Exception as e:
            print(f"Erro ao extrair {nome_aba}: {e}")
            return []

    def processar_eventos_agenda(self, nome_aba, dados):
        """Processa eventos da agenda seguindo lógica do Cursor"""
        if not dados:
            return []

        eventos = []

        for i, row in enumerate(dados, 2):  # Começar em linha 2 (após header)
            try:
                # Extrair dados básicos usando os mesmos campos que o Cursor identificou
                municipio = row.get('Municípios', '') or row.get('município', '')
                data = row.get('data', '')
                projeto = row.get('projeto', '')
                coordenador = row.get('Coordenador', '')
                formador1 = row.get('Formador 1', '') or row.get('formador', '')

                # Aplicar lógica de status baseada na aba (como o Cursor)
                if nome_aba == 'Super':
                    status_aprovacao = 'VERIFICAR_DISPONIBILIDADE'
                else:
                    status_aprovacao = 'APROVADO'

                evento = {
                    'linha_original': i,
                    'aba': nome_aba,
                    'municipio': municipio,
                    'data': data,
                    'projeto': projeto,
                    'coordenador': coordenador,
                    'formador1': formador1,
                    'dados_completos': list(row.values()),
                    'status_aprovacao': status_aprovacao
                }

                eventos.append(evento)

            except Exception as e:
                print(f"Erro ao processar linha {i} de {nome_aba}: {e}")
                continue

        print(f"{nome_aba}: {len(eventos)} eventos processados")
        return eventos

    def extrair_aprovacoes_disponibilidade(self):
        """Extrai aprovações da planilha Disponibilidade"""
        print("Extraindo aprovacoes da Disponibilidade...")

        # Usar GID da aba EVENTOS
        dados = self.extrair_aba_completa(
            self.PLANILHA_DISPONIBILIDADE_ID,
            '1430609894',  # GID da aba EVENTOS
            'EVENTOS'
        )

        if not dados:
            print("Nao foi possivel extrair aprovacoes")
            return

        print(f"Processando {len(dados)} registros de aprovacao...")

        aprovacoes_sim = 0
        aprovacoes_nao = 0

        # Processar aprovações (assumindo que 'id' contém SIM/NÃO)
        for i, row in enumerate(dados, 2):
            aprovacao_id = row.get('id', '').strip().upper()

            if aprovacao_id == 'SIM':
                aprovacoes_sim += 1
                self.aprovacoes_super[i] = 'APROVADO'
            elif aprovacao_id in ['NAO', 'NÃO']:
                aprovacoes_nao += 1
                self.aprovacoes_super[i] = 'PENDENTE'

        print(f"Aprovacoes: {aprovacoes_sim} SIM, {aprovacoes_nao} NAO")

    def aplicar_cross_reference_super(self):
        """Aplica cross-reference entre Super e Disponibilidade"""
        print("Aplicando cross-reference Super <-> Disponibilidade...")

        eventos_super = self.dados_agenda.get('Super', [])
        if not eventos_super:
            return

        aprovados = 0
        pendentes = 0

        for evento in eventos_super:
            linha_original = evento['linha_original']

            if linha_original in self.aprovacoes_super:
                evento['status_aprovacao'] = self.aprovacoes_super[linha_original]
            else:
                evento['status_aprovacao'] = 'PENDENTE'

            if evento['status_aprovacao'] == 'APROVADO':
                aprovados += 1
            else:
                pendentes += 1

        print(f"Super atualizado: {aprovados} aprovados, {pendentes} pendentes")

    def executar_extracao_completa(self):
        """Executa extração completa como o Cursor"""
        print("EXTRACAO COMPLETA COMO CURSOR")
        print("=" * 50)
        print("Extraindo TODOS os dados primeiro")
        print("Aplicando logica de aprovacao depois")
        print("=" * 50)

        # 1. Conectar
        if not self.conectar_google_sheets():
            return False

        # 2. Extrair todas as abas da Agenda
        for nome_aba, gid in self.GIDS_AGENDA.items():
            dados = self.extrair_aba_completa(self.PLANILHA_AGENDA_ID, gid, nome_aba)
            eventos = self.processar_eventos_agenda(nome_aba, dados)
            self.dados_agenda[nome_aba] = eventos

        # 3. Extrair aprovações da Disponibilidade
        self.extrair_aprovacoes_disponibilidade()

        # 4. Aplicar cross-reference na aba Super
        self.aplicar_cross_reference_super()

        # 5. Gerar relatório final
        self.gerar_relatorio_final()

        # 6. Salvar dados
        arquivo = self.salvar_dados_consolidados()

        print("\nEXTRACAO FINALIZADA!")
        return arquivo

    def gerar_relatorio_final(self):
        """Gera relatório final"""
        print("\nRELATORIO FINAL")
        print("=" * 50)

        total_geral = 0
        aprovados_geral = 0
        pendentes_geral = 0

        for nome_aba, eventos in self.dados_agenda.items():
            aprovados = len([e for e in eventos if e['status_aprovacao'] == 'APROVADO'])
            pendentes = len([e for e in eventos if e['status_aprovacao'] in ['PENDENTE', 'VERIFICAR_DISPONIBILIDADE']])
            total = len(eventos)

            total_geral += total
            aprovados_geral += aprovados
            pendentes_geral += pendentes

            perc = (aprovados / total * 100) if total > 0 else 0
            print(f"{nome_aba:10}: {total:4} eventos ({aprovados:4} aprovados {perc:5.1f}%, {pendentes:3} pendentes)")

        perc_total = (aprovados_geral / total_geral * 100) if total_geral > 0 else 0
        print(f"TOTAL     : {total_geral} eventos ({aprovados_geral} aprovados {perc_total:.1f}%, {pendentes_geral} pendentes)")

    def salvar_dados_consolidados(self):
        """Salva dados em formato similar ao Cursor"""
        todos_eventos = []
        for nome_aba, eventos in self.dados_agenda.items():
            todos_eventos.extend(eventos)

        dados_completos = {
            'metadata': {
                'timestamp': self.timestamp,
                'total_eventos': len(todos_eventos),
                'total_aprovados': len([e for e in todos_eventos if e['status_aprovacao'] == 'APROVADO']),
                'total_pendentes': len([e for e in todos_eventos if e['status_aprovacao'] in ['PENDENTE', 'VERIFICAR_DISPONIBILIDADE']]),
                'metodo': 'Extracao completa como Cursor com cross-reference correto',
                'logica_aprovacao': 'Super verifica Disponibilidade | Outras abas aprovadas'
            },
            'eventos_agenda': todos_eventos
        }

        arquivo = f'dados_completos_como_cursor_{self.timestamp}.json'

        with open(arquivo, 'w', encoding='utf-8') as f:
            json.dump(dados_completos, f, indent=2, ensure_ascii=False)

        print(f"Arquivo gerado: {arquivo}")
        return arquivo

if __name__ == "__main__":
    extrator = ExtratorCompletoComoCursor()

    try:
        arquivo = extrator.executar_extracao_completa()
        if arquivo:
            print(f"Sucesso! Dados salvos: {arquivo}")
        else:
            print("Falha na extracao")
    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()
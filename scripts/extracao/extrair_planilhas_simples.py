#!/usr/bin/env python3
"""
Extração completa das 3 planilhas essenciais (versão sem emojis para Windows)
"""

import gspread
from google.oauth2.credentials import Credentials
import json
from datetime import datetime
from collections import Counter
import sys

class ExtratorPlanilhas:
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # IDs das planilhas
        self.PLANILHA_AGENDA_ID = '16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU'
        self.PLANILHA_DISPONIBILIDADE_ID = '1fsCeGUzsNCv0SCiE6mcIvcCHsMbqNeyzANwdU_148Vw'
        self.PLANILHA_USUARIOS_ID = '1Zj_I7sqYAJ9uaYbVoBfskl0LqxGM3SAFzwm4Zpph1RI'

        # GIDs das abas
        self.GIDS_AGENDA = {
            'ACerta': '1055368874',
            'Outros': '1647358371',
            'Super': '0',
            'Brincando': '1101094368',
            'Vidas': '1882642294'
        }

        self.GIDS_DISPONIBILIDADE = {
            'EVENTOS': '1430609894'  # CHAVE para aprovações da aba Super
        }

        # Dados extraídos
        self.dados_agenda = {}
        self.aprovacoes_super = {}

        # Estatísticas
        self.stats = {
            'agenda_total': 0,
            'agenda_aprovados': 0,
            'agenda_pendentes': 0
        }

    def conectar_google_sheets(self):
        """Conecta com Google Sheets usando OAuth2"""
        print("Conectando com Google Sheets...")
        try:
            creds = Credentials.from_authorized_user_file('google_authorized_user.json')
            self.gc = gspread.authorize(creds)
            print("Conexao estabelecida com sucesso")
            return True
        except Exception as e:
            print(f"Erro na conexao: {e}")
            return False

    def extrair_aba_por_gid(self, planilha_id, gid, nome_aba):
        """Extrai dados de uma aba específica usando GID"""
        try:
            print(f"Extraindo {nome_aba} (GID: {gid})...")

            # Abrir planilha
            planilha = self.gc.open_by_key(planilha_id)

            # Encontrar aba pelo GID
            aba = None
            for worksheet in planilha.worksheets():
                if str(worksheet.id) == str(gid):
                    aba = worksheet
                    break

            if not aba:
                print(f"Aba {nome_aba} (GID: {gid}) nao encontrada")
                return []

            print(f"{nome_aba}: {aba.row_count} linhas x {aba.col_count} colunas")

            # Extrair todos os dados
            dados = aba.get_all_values()

            if not dados:
                print(f"{nome_aba}: Nenhum dado encontrado")
                return []

            print(f"{nome_aba}: {len(dados)} linhas extraidas")
            return dados

        except Exception as e:
            print(f"Erro ao extrair {nome_aba}: {e}")
            return []

    def processar_aba_agenda(self, nome_aba, dados):
        """Processa dados de uma aba da planilha Agenda"""
        if not dados or len(dados) < 2:
            return []

        headers = dados[0]
        linhas_dados = dados[1:]

        print(f"Processando {nome_aba}: {len(linhas_dados)} registros")

        eventos = []
        linhas_validas = 0
        linhas_filtradas = 0

        for i, linha in enumerate(linhas_dados, 2):
            try:
                # Filtro básico: pelo menos 10 colunas
                if len(linha) < 10:
                    linhas_filtradas += 1
                    continue

                # Extrair dados básicos (baseado na estrutura conhecida)
                municipio = linha[4] if len(linha) > 4 else ''  # Coluna E
                data = linha[7] if len(linha) > 7 else ''       # Coluna H
                projeto = linha[10] if len(linha) > 10 else ''  # Coluna K

                # Filtro de qualidade: município e data obrigatórios
                if not municipio.strip() or not data.strip():
                    linhas_filtradas += 1
                    continue

                # Determinar status baseado na aba
                if nome_aba == 'Super':
                    status_aprovacao = 'VERIFICAR_DISPONIBILIDADE'
                else:
                    status_aprovacao = 'APROVADO'

                evento = {
                    'linha_original': i,
                    'aba': nome_aba,
                    'municipio': municipio.strip(),
                    'data': data.strip(),
                    'projeto': projeto.strip(),
                    'dados_completos': linha,
                    'status_aprovacao': status_aprovacao
                }

                eventos.append(evento)
                linhas_validas += 1

            except Exception as e:
                print(f"Erro ao processar linha {i} de {nome_aba}: {e}")
                continue

        print(f"{nome_aba}: {linhas_validas} validos, {linhas_filtradas} filtrados")
        return eventos

    def extrair_planilha_agenda(self):
        """Extrai todas as abas da planilha Agenda"""
        print("\nEXTRAINDO PLANILHA AGENDA")
        print("=" * 50)

        for nome_aba, gid in self.GIDS_AGENDA.items():
            dados = self.extrair_aba_por_gid(self.PLANILHA_AGENDA_ID, gid, nome_aba)
            eventos = self.processar_aba_agenda(nome_aba, dados)
            self.dados_agenda[nome_aba] = eventos

            # Atualizar estatísticas (Super será calculado depois)
            if nome_aba != 'Super':
                self.stats['agenda_total'] += len(eventos)
                self.stats['agenda_aprovados'] += len(eventos)

    def extrair_aprovacoes_disponibilidade(self):
        """Extrai aprovações da aba EVENTOS da planilha Disponibilidade"""
        print("\nEXTRAINDO APROVACOES DA DISPONIBILIDADE")
        print("=" * 50)

        dados = self.extrair_aba_por_gid(
            self.PLANILHA_DISPONIBILIDADE_ID,
            self.GIDS_DISPONIBILIDADE['EVENTOS'],
            'EVENTOS'
        )

        if not dados or len(dados) < 2:
            print("Nao foi possivel extrair aprovacoes da Disponibilidade")
            return

        headers = dados[0]
        linhas_dados = dados[1:]

        print(f"Headers Disponibilidade EVENTOS: {headers[:5]}...")
        print(f"Processando {len(linhas_dados)} linhas de aprovacao...")

        aprovacoes_sim = 0
        aprovacoes_nao = 0

        # Criar mapeamento de aprovações (coluna A)
        for i, linha in enumerate(linhas_dados, 2):
            if len(linha) > 0:
                aprovacao = linha[0].strip().upper()  # Coluna A

                if aprovacao == 'SIM':
                    aprovacoes_sim += 1
                    self.aprovacoes_super[i] = 'APROVADO'
                elif aprovacao in ['NAO', 'NÃO']:
                    aprovacoes_nao += 1
                    self.aprovacoes_super[i] = 'PENDENTE'

        print(f"Aprovacoes encontradas: {aprovacoes_sim} SIM, {aprovacoes_nao} NAO")

    def aplicar_aprovacoes_super(self):
        """Aplica aprovações da Disponibilidade nos eventos da aba Super"""
        print("\nAPLICANDO CROSS-REFERENCE SUPER <-> DISPONIBILIDADE")
        print("=" * 50)

        eventos_super = self.dados_agenda.get('Super', [])
        if not eventos_super:
            print("Nenhum evento da aba Super para processar")
            return

        aprovados = 0
        pendentes = 0
        nao_encontrados = 0

        for evento in eventos_super:
            linha_original = evento['linha_original']

            # Verificar se tem aprovação na Disponibilidade
            if linha_original in self.aprovacoes_super:
                evento['status_aprovacao'] = self.aprovacoes_super[linha_original]
                if evento['status_aprovacao'] == 'APROVADO':
                    aprovados += 1
                else:
                    pendentes += 1
            else:
                # Se não encontrou na Disponibilidade, considerar pendente
                evento['status_aprovacao'] = 'PENDENTE'
                pendentes += 1
                nao_encontrados += 1

        print(f"Super processado: {aprovados} aprovados, {pendentes} pendentes")
        if nao_encontrados > 0:
            print(f"{nao_encontrados} eventos nao encontrados na Disponibilidade")

        # Atualizar estatísticas
        self.stats['agenda_total'] += len(eventos_super)
        self.stats['agenda_aprovados'] += aprovados
        self.stats['agenda_pendentes'] = pendentes

    def gerar_relatorio_final(self):
        """Gera relatório final das extrações"""
        print("\nRELATORIO FINAL")
        print("=" * 60)

        print("PLANILHA AGENDA:")
        for nome_aba, eventos in self.dados_agenda.items():
            aprovados = len([e for e in eventos if e['status_aprovacao'] == 'APROVADO'])
            pendentes = len([e for e in eventos if e['status_aprovacao'] == 'PENDENTE'])
            total = len(eventos)
            perc_aprovados = (aprovados / total * 100) if total > 0 else 0

            print(f"   {nome_aba:10}: {total:4} eventos | {aprovados:4} aprovados ({perc_aprovados:5.1f}%) | {pendentes:3} pendentes")

        # Totais da Agenda
        total_agenda = self.stats['agenda_total']
        aprovados_agenda = self.stats['agenda_aprovados']
        pendentes_agenda = self.stats['agenda_pendentes']
        perc_total = (aprovados_agenda / total_agenda * 100) if total_agenda > 0 else 0

        print(f"   TOTAL     : {total_agenda} eventos | {aprovados_agenda} aprovados ({perc_total:.1f}%) | {pendentes_agenda} pendentes")

    def salvar_dados_consolidados(self):
        """Salva todos os dados extraídos em arquivo JSON"""

        # Consolidar todos os eventos da agenda
        todos_eventos = []
        for nome_aba, eventos in self.dados_agenda.items():
            todos_eventos.extend(eventos)

        dados_completos = {
            'metadata': {
                'timestamp': self.timestamp,
                'total_eventos': len(todos_eventos),
                'total_aprovados': len([e for e in todos_eventos if e['status_aprovacao'] == 'APROVADO']),
                'total_pendentes': len([e for e in todos_eventos if e['status_aprovacao'] == 'PENDENTE']),
                'logica_aprovacao': 'Super verifica Disponibilidade | Outras abas aprovadas por padrao'
            },
            'eventos_agenda': todos_eventos,
            'estatisticas': self.stats
        }

        arquivo = f'dados_extraidos_logica_correta_{self.timestamp}.json'

        with open(arquivo, 'w', encoding='utf-8') as f:
            json.dump(dados_completos, f, indent=2, ensure_ascii=False)

        print(f"\nARQUIVO GERADO: {arquivo}")
        print(f"Total de dados extraidos: {len(todos_eventos)} eventos")

        return arquivo

    def executar_extracao_completa(self):
        """Executa extração completa"""
        print("INICIANDO EXTRACAO COMPLETA COM LOGICA CORRETA")
        print("=" * 70)
        print("Baseado na analise Claude + Cursor + correcoes do usuario")
        print("Aba Super: Status verificado na planilha Disponibilidade")
        print("Outras abas: Status = APROVADO (nao passam pela superintendencia)")
        print("=" * 70)

        # 1. Conectar
        if not self.conectar_google_sheets():
            return False

        # 2. Extrair planilha Agenda
        self.extrair_planilha_agenda()

        # 3. Extrair aprovações da Disponibilidade
        self.extrair_aprovacoes_disponibilidade()

        # 4. Aplicar cross-reference Super <-> Disponibilidade
        self.aplicar_aprovacoes_super()

        # 5. Gerar relatório
        self.gerar_relatorio_final()

        # 6. Salvar dados
        arquivo = self.salvar_dados_consolidados()

        print("\nEXTRACAO COMPLETA FINALIZADA COM SUCESSO!")
        print("OBJETIVOS ALCANCADOS:")
        print("- Logica de aprovacao correta implementada")
        print("- Cross-reference Super <-> Disponibilidade aplicado")
        print("- Dados reais de 2025 consolidados")

        return arquivo

if __name__ == "__main__":
    extrator = ExtratorPlanilhas()

    try:
        arquivo_gerado = extrator.executar_extracao_completa()
        if arquivo_gerado:
            print(f"\nSucesso! Dados salvos em: {arquivo_gerado}")
            sys.exit(0)
        else:
            print("\nFalha na extracao")
            sys.exit(1)

    except Exception as e:
        print(f"\nErro critico: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
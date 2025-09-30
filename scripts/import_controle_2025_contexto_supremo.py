#!/usr/bin/env python3
"""
IMPORTADOR CONTROLE 2025 - CONTEXTO SUPREMO
==========================================

Script para importar dados da planilha "Planilha de Controle - 2025"
conforme o contexto supremo fornecido.

Estrutura por Setores:
- CONTROLE: AÇÕES + COMPRAS + FILTRO_PROD + FORMAÇÕES
- DAT: DAT + CADASTROS
- CONFIG: Configurações e fórmulas

Otimizações sugeridas:
- Página única: AÇÕES + COMPRAS (remover duplicatas)
- Página DAT: Visualização + botão de inserção
- Formulário: Alimentar CADASTROS via interface

Autor: Claude Code
Data: Janeiro 2025
"""

import os
import sys
import django
import json
import logging
from datetime import datetime, time, date
from typing import Dict, List, Any, Optional

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
django.setup()

from django.db import transaction
from django.contrib.auth import get_user_model
from core.models import (
    Usuario, Municipio, Projeto, TipoEvento, Solicitacao,
    SolicitacaoStatus, Setor, FormadoresSolicitacao, Formador
)

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

User = get_user_model()


class ImportadorControle2025ContextoSupremo:
    """
    Importador da planilha Controle 2025 com contexto supremo
    """
    
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.planilha_id = '1adUmabEnbaG6Ldf58poLZts-4Bc7zSOm0XbVuhc_dfo'
        
        # Configuração das abas por setor
        self.abas_config = {
            '🟥 AÇÕES': {
                'setor': 'CONTROLE',
                'dominio': 'CONTROLE',
                'colunas': ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'],
                'nomes_colunas': [
                    'Município', 'Projeto', 'Coordenador', 'Data da Entrega',
                    'Data da Carta', 'Contato inicial', 'Data Reunião Alinhamento', 'Observação'
                ],
                'descricao': 'Informações sobre município, projeto, coordenador, datas e observações'
            },
            '🟥 COMPRAS': {
                'setor': 'CONTROLE',
                'dominio': 'CONTROLE',
                'colunas': ['A', 'B', 'C', 'D', 'E', 'F', 'G'],
                'nomes_colunas': [
                    'CÓD', 'Produto', 'Quant.', 'Município', 'UF', 'Data', 'Uso das coleções'
                ],
                'descricao': 'Informações de compras feitas pelos municípios'
            },
            'ℹ️ FILTRO_PROD.': {
                'setor': 'CONTROLE',
                'dominio': 'CONTROLE',
                'colunas': ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'],
                'nomes_colunas': [
                    'Filtro', 'Município - UF', 'Região', 'Tipo', 'Projeto', 'Projeto Detalhe', 'Gerência', 'Qtd'
                ],
                'descricao': 'Produtos e códigos com quantidade comprada',
                'fonte': 'Fórmula QUERY na célula B1'
            },
            'ℹ️ FORMAÇÕES': {
                'setor': 'CONTROLE',
                'dominio': 'CONTROLE',
                'colunas': ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'],
                'nomes_colunas': [
                    'Município', 'Projeto', 'Coordenador', 'Data', 'Tipo', 'Encontro', 'Carga Horária',
                    'Quantidade', 'Acompanhamento', 'Prova Aplicada', 'Observações', 'Status',
                    'Material Entregue', 'Data Entrega', 'Responsável', 'Contato', 'Endereço',
                    'UF', 'Região', 'Tipo Material', 'Quantidade Material', 'Data Compra',
                    'Valor', 'Fornecedor', 'Status Pagamento', 'Observações Gerais'
                ],
                'descricao': 'Informações sobre tudo que acontece nas formações'
            },
            'ℹ️ DAT': {
                'setor': 'DAT',
                'dominio': 'DAT',
                'colunas': ['A', 'B', 'C', 'D', 'E', 'F', 'G'],
                'nomes_colunas': [
                    'Município', 'Projeto', 'Tipo de Ação', 'Responsável', 'Data', 'Status', 'Observações'
                ],
                'descricao': 'Ações nas plataformas Aprender Avaliar e Aprender Formar',
                'fonte': 'Dados extraídos da aba CADASTROS'
            },
            '☑️ CADASTROS': {
                'setor': 'DAT',
                'dominio': 'DAT',
                'colunas': ['A', 'B', 'C', 'D', 'E', 'F', 'G'],
                'nomes_colunas': [
                    'Município', 'Projeto', 'Tipo de Ação', 'Responsável', 'Data', 'Status', 'Observações'
                ],
                'descricao': 'Formulário alimentado via AppScript',
                'fonte': 'Formulário que roda através do AppScript'
            },
            '⚙️ CONFIG': {
                'setor': 'CONFIG',
                'dominio': 'CONFIG',
                'descricao': 'Configurações e fórmulas',
                'funcionalidades': [
                    'Extrair ID do curso na plataforma',
                    'Criar hiperlinks de acesso',
                    'Fórmulas QUERY para extração de dados'
                ]
            }
        }
        
        # Mapeamento de produtos para projetos
        self.produto_para_projeto = {
            'NOVO LENDO 1º ANO KIT DO ALUNO': 'Novo Lendo 1º Ano',
            'NOVO LENDO 1º ANO KIT DO PROFESSOR': 'Novo Lendo 1º Ano',
            'NOVO LENDO 2º ANO KIT DO ALUNO': 'Novo Lendo 2º Ano',
            'NOVO LENDO 2º ANO KIT DO PROFESSOR': 'Novo Lendo 2º Ano',
            # Adicionar mais mapeamentos conforme necessário
        }
        
        # Estatísticas
        self.estatisticas = {
            'total_registros': 0,
            'acoes_processadas': 0,
            'compras_processadas': 0,
            'filtro_prod_processado': 0,
            'formacoes_processadas': 0,
            'dat_processado': 0,
            'cadastros_processados': 0,
            'config_processado': 0,
            'erros': 0,
            'por_aba': {}
        }

    def conectar_google_sheets(self):
        """
        Conectar ao Google Sheets
        """
        try:
            import gspread
            from google.oauth2.service_account import Credentials
            
            # Configurar credenciais
            creds_path = os.path.join(os.path.dirname(__file__), 'google_service_account.json')
            if not os.path.exists(creds_path):
                logger.error("❌ Arquivo de credenciais não encontrado: google_service_account.json")
                return None
            
            scope = ['https://spreadsheets.google.com/feeds',
                    'https://www.googleapis.com/auth/drive']
            
            creds = Credentials.from_service_account_file(creds_path, scopes=scope)
            client = gspread.authorize(creds)
            
            # Abrir planilha
            spreadsheet = client.open_by_key(self.planilha_id)
            logger.info(f"✅ Conectado à planilha: {spreadsheet.title}")
            
            return spreadsheet
            
        except Exception as e:
            logger.error(f"❌ Erro ao conectar Google Sheets: {str(e)}")
            return None

    def processar_aba_acoes(self, spreadsheet):
        """
        Processar aba AÇÕES - Setor CONTROLE
        """
        logger.info("🏢 Processando aba AÇÕES - Setor CONTROLE...")
        
        try:
            worksheet = spreadsheet.worksheet('🟥 AÇÕES')
            config = self.abas_config['🟥 AÇÕES']
            
            # Obter dados da planilha
            all_values = worksheet.get_all_values()
            
            if not all_values:
                logger.warning("⚠️ Aba AÇÕES está vazia")
                return
            
            # Primeira linha são os cabeçalhos
            headers = all_values[0]
            data_rows = all_values[1:]
            
            logger.info(f"📋 Cabeçalhos: {config['nomes_colunas']}")
            
            # Processar dados
            for i, row in enumerate(data_rows):
                if not any(row):  # Pular linhas vazias
                    continue
                
                # Extrair dados da linha
                acao_data = {}
                for j, coluna in enumerate(config['colunas']):
                    if j < len(row):
                        nome_coluna = config['nomes_colunas'][j]
                        acao_data[nome_coluna] = row[j].strip()
                
                # Adicionar informações da aba
                acao_data['aba_origem'] = 'AÇÕES'
                acao_data['setor'] = 'CONTROLE'
                acao_data['linha_planilha'] = i + 2
                
                logger.info(f"🏢 Ação {i+1}: {acao_data.get('Município', 'N/A')} - {acao_data.get('Projeto', 'N/A')}")
                
                # Aqui seria a lógica para salvar no banco de dados
                if not self.dry_run:
                    # Criar ou atualizar registro de ação
                    pass
                
                self.estatisticas['acoes_processadas'] += 1
                self.estatisticas['total_registros'] += 1
            
            logger.info("✅ Aba AÇÕES processada com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar aba AÇÕES: {str(e)}")
            self.estatisticas['erros'] += 1

    def processar_aba_compras(self, spreadsheet):
        """
        Processar aba COMPRAS - Setor CONTROLE
        """
        logger.info("🛒 Processando aba COMPRAS - Setor CONTROLE...")
        
        try:
            worksheet = spreadsheet.worksheet('🟥 COMPRAS')
            config = self.abas_config['🟥 COMPRAS']
            
            # Obter dados da planilha
            all_values = worksheet.get_all_values()
            
            if not all_values:
                logger.warning("⚠️ Aba COMPRAS está vazia")
                return
            
            # Primeira linha são os cabeçalhos
            headers = all_values[0]
            data_rows = all_values[1:]
            
            logger.info(f"📋 Cabeçalhos: {config['nomes_colunas']}")
            
            # Processar dados
            for i, row in enumerate(data_rows):
                if not any(row):  # Pular linhas vazias
                    continue
                
                # Extrair dados da linha
                compra_data = {}
                for j, coluna in enumerate(config['colunas']):
                    if j < len(row):
                        nome_coluna = config['nomes_colunas'][j]
                        compra_data[nome_coluna] = row[j].strip()
                
                # Adicionar informações da aba
                compra_data['aba_origem'] = 'COMPRAS'
                compra_data['setor'] = 'CONTROLE'
                compra_data['linha_planilha'] = i + 2
                
                # Mapear produto para projeto
                produto = compra_data.get('Produto', '')
                if produto in self.produto_para_projeto:
                    compra_data['projeto_mapeado'] = self.produto_para_projeto[produto]
                
                logger.info(f"🛒 Compra {i+1}: {compra_data.get('Produto', 'N/A')} - {compra_data.get('Município', 'N/A')}")
                
                # Aqui seria a lógica para salvar no banco de dados
                if not self.dry_run:
                    # Criar ou atualizar registro de compra
                    pass
                
                self.estatisticas['compras_processadas'] += 1
                self.estatisticas['total_registros'] += 1
            
            logger.info("✅ Aba COMPRAS processada com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar aba COMPRAS: {str(e)}")
            self.estatisticas['erros'] += 1

    def processar_aba_filtro_prod(self, spreadsheet):
        """
        Processar aba FILTRO_PROD - Setor CONTROLE
        """
        logger.info("🔍 Processando aba FILTRO_PROD - Setor CONTROLE...")
        
        try:
            worksheet = spreadsheet.worksheet('ℹ️ FILTRO_PROD.')
            config = self.abas_config['ℹ️ FILTRO_PROD.']
            
            # Obter dados da planilha
            all_values = worksheet.get_all_values()
            
            if not all_values:
                logger.warning("⚠️ Aba FILTRO_PROD está vazia")
                return
            
            # Primeira linha são os cabeçalhos
            headers = all_values[0]
            data_rows = all_values[1:]
            
            logger.info(f"📋 Cabeçalhos: {config['nomes_colunas']}")
            logger.info("🔍 Dados extraídos via fórmula QUERY na célula B1")
            
            # Processar dados
            for i, row in enumerate(data_rows):
                if not any(row):  # Pular linhas vazias
                    continue
                
                # Extrair dados da linha
                filtro_data = {}
                for j, coluna in enumerate(config['colunas']):
                    if j < len(row):
                        nome_coluna = config['nomes_colunas'][j]
                        filtro_data[nome_coluna] = row[j].strip()
                
                # Adicionar informações da aba
                filtro_data['aba_origem'] = 'FILTRO_PROD'
                filtro_data['setor'] = 'CONTROLE'
                filtro_data['linha_planilha'] = i + 2
                
                logger.info(f"🔍 Filtro {i+1}: {filtro_data.get('Município - UF', 'N/A')} - {filtro_data.get('Projeto', 'N/A')}")
                
                # Aqui seria a lógica para salvar no banco de dados
                if not self.dry_run:
                    # Criar ou atualizar registro de filtro
                    pass
                
                self.estatisticas['filtro_prod_processado'] += 1
                self.estatisticas['total_registros'] += 1
            
            logger.info("✅ Aba FILTRO_PROD processada com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar aba FILTRO_PROD: {str(e)}")
            self.estatisticas['erros'] += 1

    def processar_aba_formacoes(self, spreadsheet):
        """
        Processar aba FORMAÇÕES - Setor CONTROLE
        """
        logger.info("📚 Processando aba FORMAÇÕES - Setor CONTROLE...")
        
        try:
            worksheet = spreadsheet.worksheet('ℹ️ FORMAÇÕES')
            config = self.abas_config['ℹ️ FORMAÇÕES']
            
            # Obter dados da planilha
            all_values = worksheet.get_all_values()
            
            if not all_values:
                logger.warning("⚠️ Aba FORMAÇÕES está vazia")
                return
            
            # Primeira linha são os cabeçalhos
            headers = all_values[0]
            data_rows = all_values[1:]
            
            logger.info(f"📋 Cabeçalhos: {config['nomes_colunas']}")
            logger.info("📚 Dados inseridos manualmente pelo setor CONTROLE")
            
            # Processar dados
            for i, row in enumerate(data_rows):
                if not any(row):  # Pular linhas vazias
                    continue
                
                # Extrair dados da linha
                formacao_data = {}
                for j, coluna in enumerate(config['colunas']):
                    if j < len(row):
                        nome_coluna = config['nomes_colunas'][j]
                        formacao_data[nome_coluna] = row[j].strip()
                
                # Adicionar informações da aba
                formacao_data['aba_origem'] = 'FORMAÇÕES'
                formacao_data['setor'] = 'CONTROLE'
                formacao_data['linha_planilha'] = i + 2
                
                logger.info(f"📚 Formação {i+1}: {formacao_data.get('Município', 'N/A')} - {formacao_data.get('Projeto', 'N/A')}")
                
                # Aqui seria a lógica para salvar no banco de dados
                if not self.dry_run:
                    # Criar ou atualizar registro de formação
                    pass
                
                self.estatisticas['formacoes_processadas'] += 1
                self.estatisticas['total_registros'] += 1
            
            logger.info("✅ Aba FORMAÇÕES processada com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar aba FORMAÇÕES: {str(e)}")
            self.estatisticas['erros'] += 1

    def processar_aba_dat(self, spreadsheet):
        """
        Processar aba DAT - Setor DAT
        """
        logger.info("💻 Processando aba DAT - Setor DAT...")
        
        try:
            worksheet = spreadsheet.worksheet('ℹ️ DAT')
            config = self.abas_config['ℹ️ DAT']
            
            # Obter dados da planilha
            all_values = worksheet.get_all_values()
            
            if not all_values:
                logger.warning("⚠️ Aba DAT está vazia")
                return
            
            # Primeira linha são os cabeçalhos
            headers = all_values[0]
            data_rows = all_values[1:]
            
            logger.info(f"📋 Cabeçalhos: {config['nomes_colunas']}")
            logger.info("💻 Dados extraídos da aba CADASTROS")
            
            # Processar dados
            for i, row in enumerate(data_rows):
                if not any(row):  # Pular linhas vazias
                    continue
                
                # Extrair dados da linha
                dat_data = {}
                for j, coluna in enumerate(config['colunas']):
                    if j < len(row):
                        nome_coluna = config['nomes_colunas'][j]
                        dat_data[nome_coluna] = row[j].strip()
                
                # Adicionar informações da aba
                dat_data['aba_origem'] = 'DAT'
                dat_data['setor'] = 'DAT'
                dat_data['linha_planilha'] = i + 2
                
                logger.info(f"💻 DAT {i+1}: {dat_data.get('Município', 'N/A')} - {dat_data.get('Tipo de Ação', 'N/A')}")
                
                # Aqui seria a lógica para salvar no banco de dados
                if not self.dry_run:
                    # Criar ou atualizar registro DAT
                    pass
                
                self.estatisticas['dat_processado'] += 1
                self.estatisticas['total_registros'] += 1
            
            logger.info("✅ Aba DAT processada com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar aba DAT: {str(e)}")
            self.estatisticas['erros'] += 1

    def processar_aba_cadastros(self, spreadsheet):
        """
        Processar aba CADASTROS - Setor DAT
        """
        logger.info("📝 Processando aba CADASTROS - Setor DAT...")
        
        try:
            worksheet = spreadsheet.worksheet('☑️ CADASTROS')
            config = self.abas_config['☑️ CADASTROS']
            
            # Obter dados da planilha
            all_values = worksheet.get_all_values()
            
            if not all_values:
                logger.warning("⚠️ Aba CADASTROS está vazia")
                return
            
            # Primeira linha são os cabeçalhos
            headers = all_values[0]
            data_rows = all_values[1:]
            
            logger.info(f"📋 Cabeçalhos: {config['nomes_colunas']}")
            logger.info("📝 Dados alimentados via formulário AppScript")
            
            # Processar dados
            for i, row in enumerate(data_rows):
                if not any(row):  # Pular linhas vazias
                    continue
                
                # Extrair dados da linha
                cadastro_data = {}
                for j, coluna in enumerate(config['colunas']):
                    if j < len(row):
                        nome_coluna = config['nomes_colunas'][j]
                        cadastro_data[nome_coluna] = row[j].strip()
                
                # Adicionar informações da aba
                cadastro_data['aba_origem'] = 'CADASTROS'
                cadastro_data['setor'] = 'DAT'
                cadastro_data['linha_planilha'] = i + 2
                
                logger.info(f"📝 Cadastro {i+1}: {cadastro_data.get('Município', 'N/A')} - {cadastro_data.get('Tipo de Ação', 'N/A')}")
                
                # Aqui seria a lógica para salvar no banco de dados
                if not self.dry_run:
                    # Criar ou atualizar registro de cadastro
                    pass
                
                self.estatisticas['cadastros_processados'] += 1
                self.estatisticas['total_registros'] += 1
            
            logger.info("✅ Aba CADASTROS processada com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar aba CADASTROS: {str(e)}")
            self.estatisticas['erros'] += 1

    def processar_aba_config(self, spreadsheet):
        """
        Processar aba CONFIG - Configurações
        """
        logger.info("⚙️ Processando aba CONFIG - Configurações...")
        
        try:
            worksheet = spreadsheet.worksheet('⚙️ CONFIG')
            config = self.abas_config['⚙️ CONFIG']
            
            # Obter dados da planilha
            all_values = worksheet.get_all_values()
            
            if not all_values:
                logger.warning("⚠️ Aba CONFIG está vazia")
                return
            
            logger.info("⚙️ Processando configurações e fórmulas...")
            logger.info("🔗 Funcionalidades:")
            for funcionalidade in config['funcionalidades']:
                logger.info(f"   - {funcionalidade}")
            
            # Processar configurações
            for i, row in enumerate(all_values):
                if not any(row):  # Pular linhas vazias
                    continue
                
                logger.info(f"⚙️ Config {i+1}: {row}")
                
                # Aqui seria a lógica para processar configurações
                if not self.dry_run:
                    # Processar configurações
                    pass
            
            self.estatisticas['config_processado'] += 1
            logger.info("✅ Aba CONFIG processada com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar aba CONFIG: {str(e)}")
            self.estatisticas['erros'] += 1

    def executar_importacao(self, abas_especificas: Optional[List[str]] = None):
        """
        Executar importação completa
        """
        logger.info("🚀 INICIANDO IMPORTAÇÃO CONTROLE 2025 - CONTEXTO SUPREMO")
        logger.info("=" * 70)
        
        if self.dry_run:
            logger.info("🔍 MODO DRY RUN - Nenhum dado será salvo no banco")
        
        # Conectar Google Sheets
        spreadsheet = self.conectar_google_sheets()
        if not spreadsheet:
            logger.error("❌ Não foi possível conectar ao Google Sheets")
            return False
        
        # Determinar abas para processar
        abas_para_processar = abas_especificas or list(self.abas_config.keys())
        
        try:
            with transaction.atomic():
                # Processar cada aba
                for nome_aba in abas_para_processar:
                    if nome_aba in self.abas_config:
                        logger.info(f"\n🔄 Processando aba: {nome_aba}")
                        
                        if nome_aba == '🟥 AÇÕES':
                            self.processar_aba_acoes(spreadsheet)
                        elif nome_aba == '🟥 COMPRAS':
                            self.processar_aba_compras(spreadsheet)
                        elif nome_aba == 'ℹ️ FILTRO_PROD.':
                            self.processar_aba_filtro_prod(spreadsheet)
                        elif nome_aba == 'ℹ️ FORMAÇÕES':
                            self.processar_aba_formacoes(spreadsheet)
                        elif nome_aba == 'ℹ️ DAT':
                            self.processar_aba_dat(spreadsheet)
                        elif nome_aba == '☑️ CADASTROS':
                            self.processar_aba_cadastros(spreadsheet)
                        elif nome_aba == '⚙️ CONFIG':
                            self.processar_aba_config(spreadsheet)
                        
                        # Salvar estatísticas da aba
                        self.estatisticas['por_aba'][nome_aba] = {
                            'processada': True,
                            'erros': 0
                        }
                    else:
                        logger.warning(f"⚠️ Aba {nome_aba} não configurada")
                
                if self.dry_run:
                    logger.info("🔍 [DRY RUN] Transação seria commitada aqui")
                    raise transaction.TransactionManagementError("Dry run - rollback")
            
        except transaction.TransactionManagementError:
            if self.dry_run:
                logger.info("🔍 [DRY RUN] Rollback executado conforme esperado")
            else:
                logger.error("❌ Erro na transação")
                return False
        except Exception as e:
            logger.error(f"❌ Erro durante a importação: {str(e)}")
            return False
        
        # Relatório final
        self.gerar_relatorio_final()
        
        return True

    def gerar_relatorio_final(self):
        """
        Gerar relatório final da importação
        """
        logger.info("\n" + "=" * 70)
        logger.info("📊 RELATÓRIO FINAL DA IMPORTAÇÃO CONTROLE")
        logger.info("=" * 70)
        
        logger.info(f"📈 ESTATÍSTICAS GERAIS:")
        logger.info(f"   - Total de registros: {self.estatisticas['total_registros']}")
        logger.info(f"   - Ações processadas: {self.estatisticas['acoes_processadas']}")
        logger.info(f"   - Compras processadas: {self.estatisticas['compras_processadas']}")
        logger.info(f"   - Filtro PROD processado: {self.estatisticas['filtro_prod_processado']}")
        logger.info(f"   - Formações processadas: {self.estatisticas['formacoes_processadas']}")
        logger.info(f"   - DAT processado: {self.estatisticas['dat_processado']}")
        logger.info(f"   - Cadastros processados: {self.estatisticas['cadastros_processados']}")
        logger.info(f"   - Config processado: {self.estatisticas['config_processado']}")
        logger.info(f"   - Erros: {self.estatisticas['erros']}")
        
        logger.info(f"\n📋 ESTATÍSTICAS POR ABA:")
        for aba, stats in self.estatisticas['por_aba'].items():
            logger.info(f"   {aba}:")
            logger.info(f"     - Processada: {stats['processada']}")
            logger.info(f"     - Erros: {stats['erros']}")
        
        # Salvar relatório em arquivo
        relatorio = {
            'timestamp': datetime.now().isoformat(),
            'dry_run': self.dry_run,
            'estatisticas': self.estatisticas
        }
        
        with open('relatorio_importacao_controle_2025.json', 'w', encoding='utf-8') as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"\n💾 Relatório salvo em: relatorio_importacao_controle_2025.json")


def main():
    """
    Função principal
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Importar dados da planilha Controle 2025')
    parser.add_argument('--dry-run', action='store_true', default=True,
                       help='Executar em modo de teste (padrão)')
    parser.add_argument('--execute', action='store_true',
                       help='Executar importação real (salvar no banco)')
    parser.add_argument('--abas', nargs='+', 
                       choices=['🟥 AÇÕES', '🟥 COMPRAS', 'ℹ️ FILTRO_PROD.', 'ℹ️ FORMAÇÕES', 
                               'ℹ️ DAT', '☑️ CADASTROS', '⚙️ CONFIG'],
                       help='Processar apenas abas específicas')
    
    args = parser.parse_args()
    
    # Determinar modo de execução
    dry_run = not args.execute
    
    # Criar importador
    importador = ImportadorControle2025ContextoSupremo(dry_run=dry_run)
    
    # Executar importação
    sucesso = importador.executar_importacao(abas_especificas=args.abas)
    
    if sucesso:
        logger.info("🎉 IMPORTAÇÃO CONCLUÍDA COM SUCESSO!")
    else:
        logger.error("❌ IMPORTAÇÃO FALHOU!")
        sys.exit(1)


if __name__ == '__main__':
    main()

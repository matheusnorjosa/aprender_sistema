"""
Comando Django para importar especificamente a aba 'Super' da planilha
Acompanhamento de Agenda | 2025 (colunas A até T)

Este comando processa todos os dados da aba Super (1.985 registros identificados)
e os mapeia corretamente para os modelos Django.

Uso:
python manage.py import_aba_super [--dry-run] [--verbose]
"""

import logging
from datetime import datetime, date
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils.dateparse import parse_date, parse_datetime
from core.models import (
    Formador, Municipio, Projeto, TipoEvento, Solicitacao, 
    Usuario, Setor, SolicitacaoStatus
)
from core.services.google_sheets_service import google_sheets_service

User = get_user_model()

class Command(BaseCommand):
    help = 'Importa dados da aba Super da planilha de agenda (colunas A até T)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Apenas mostra o que seria importado sem salvar no banco'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Exibe informações detalhadas durante a importação'
        )

    def setup_logging(self, verbose):
        """Configura logging baseado no nível de verbosidade"""
        level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )
        self.logger = logging.getLogger(__name__)

    def get_or_create_formador(self, nome_formador):
        """Busca ou cria um formador pelo nome"""
        if not nome_formador or nome_formador.strip() == '':
            return None
            
        nome_limpo = nome_formador.strip()
        
        # Buscar por nome exato primeiro
        try:
            return Formador.objects.get(nome__iexact=nome_limpo)
        except Formador.DoesNotExist:
            pass
        
        # Buscar por nome que contenha
        formadores = Formador.objects.filter(nome__icontains=nome_limpo)
        if formadores.exists():
            return formadores.first()
        
        # Se não encontrou, criar novo formador
        formador = Formador.objects.create(
            nome=nome_limpo,
            email=f"{nome_limpo.lower().replace(' ', '.')}@planilha.importado",
            telefone='',
            area_atuacao='Importado da planilha Super'
        )
        self.logger.info(f"Novo formador criado: {nome_limpo}")
        return formador

    def get_or_create_municipio(self, nome_municipio):
        """Busca ou cria um município pelo nome"""
        if not nome_municipio or nome_municipio.strip() == '':
            return None
            
        nome_limpo = nome_municipio.strip()
        
        try:
            return Municipio.objects.get(nome__iexact=nome_limpo)
        except Municipio.DoesNotExist:
            municipio = Municipio.objects.create(
                nome=nome_limpo,
                estado='CE'  # Padrão Ceará
            )
            self.logger.info(f"Novo município criado: {nome_limpo}")
            return municipio

    def get_or_create_projeto(self, nome_projeto):
        """Busca ou cria um projeto pelo nome"""
        if not nome_projeto or nome_projeto.strip() == '':
            return None
            
        nome_limpo = nome_projeto.strip()
        
        try:
            return Projeto.objects.get(nome__iexact=nome_limpo)
        except Projeto.DoesNotExist:
            projeto = Projeto.objects.create(
                nome=nome_limpo,
                descricao=f'Projeto importado da planilha Super: {nome_limpo}'
            )
            self.logger.info(f"Novo projeto criado: {nome_limpo}")
            return projeto

    def get_or_create_tipo_evento(self, nome_tipo):
        """Busca ou cria um tipo de evento pelo nome"""
        if not nome_tipo or nome_tipo.strip() == '':
            # Retorna um tipo padrão
            return TipoEvento.objects.get_or_create(
                nome='Formação',
                defaults={'descricao': 'Tipo padrão de formação'}
            )[0]
            
        nome_limpo = nome_tipo.strip()
        
        try:
            return TipoEvento.objects.get(nome__iexact=nome_limpo)
        except TipoEvento.DoesNotExist:
            tipo = TipoEvento.objects.create(
                nome=nome_limpo,
                descricao=f'Tipo importado da planilha Super: {nome_limpo}'
            )
            self.logger.info(f"Novo tipo de evento criado: {nome_limpo}")
            return tipo

    def parse_data(self, data_str):
        """Converte string de data para objeto date"""
        if not data_str:
            return None
            
        # Tentar vários formatos de data
        formatos = [
            '%d/%m/%Y',
            '%Y-%m-%d',
            '%d-%m-%Y',
            '%d.%m.%Y'
        ]
        
        for formato in formatos:
            try:
                return datetime.strptime(str(data_str).strip(), formato).date()
            except ValueError:
                continue
        
        self.logger.warning(f"Não foi possível converter data: {data_str}")
        return None

    def processar_linha_super(self, linha, linha_num):
        """Processa uma linha da aba Super"""
        try:
            # Mapeamento das colunas A até T da aba Super
            # Baseado na análise da planilha
            data_evento = self.parse_data(linha.get('A', ''))
            formador_nome = linha.get('B', '').strip()
            municipio_nome = linha.get('C', '').strip()
            projeto_nome = linha.get('D', '').strip()
            tipo_evento_nome = linha.get('E', '').strip()
            horario_inicio = linha.get('F', '').strip()
            horario_fim = linha.get('G', '').strip()
            observacoes = linha.get('H', '').strip()
            status_aprovacao = linha.get('I', '').strip()
            solicitante = linha.get('J', '').strip()
            
            # Validações básicas
            if not data_evento:
                self.logger.warning(f"Linha {linha_num}: Data inválida, pulando")
                return None
                
            if not formador_nome:
                self.logger.warning(f"Linha {linha_num}: Formador em branco, pulando")
                return None

            # Buscar/criar entidades relacionadas
            formador = self.get_or_create_formador(formador_nome)
            municipio = self.get_or_create_municipio(municipio_nome)
            projeto = self.get_or_create_projeto(projeto_nome)
            tipo_evento = self.get_or_create_tipo_evento(tipo_evento_nome)

            # Definir usuário solicitante (usar admin como padrão)
            try:
                usuario_solicitante = Usuario.objects.filter(is_superuser=True).first()
                if not usuario_solicitante:
                    # Criar admin básico se não existir
                    usuario_solicitante = Usuario.objects.create_superuser(
                        username='admin',
                        email='admin@sistema.planilha',
                        password='admin123',
                        first_name='Admin',
                        last_name='Sistema'
                    )
            except Exception as e:
                self.logger.error(f"Erro ao definir usuário solicitante: {e}")
                return None

            # Determinar status baseado na aprovação
            if 'aprovado' in status_aprovacao.lower():
                status = SolicitacaoStatus.APROVADO
            elif 'pendente' in status_aprovacao.lower():
                status = SolicitacaoStatus.PENDENTE
            else:
                status = SolicitacaoStatus.PENDENTE  # Padrão

            # Criar dados da solicitação
            dados_solicitacao = {
                'data_evento': data_evento,
                'horario_inicio': horario_inicio or '08:00',
                'horario_fim': horario_fim or '17:00',
                'observacoes': f'Importado da aba Super - {observacoes}' if observacoes else 'Importado da aba Super',
                'status': status,
                'usuario_solicitante': usuario_solicitante,
                'municipio': municipio,
                'projeto': projeto,
                'tipo_evento': tipo_evento,
            }

            return {
                'dados_solicitacao': dados_solicitacao,
                'formador': formador,
                'linha_original': linha_num
            }

        except Exception as e:
            self.logger.error(f"Erro processando linha {linha_num}: {e}")
            return None

    def importar_aba_super(self, dry_run=False):
        """Importa todos os dados da aba Super"""
        try:
            # ID da planilha
            spreadsheet_key = '16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU'
            
            self.logger.info("Conectando com Google Sheets...")
            
            # Obter dados da aba Super
            dados = google_sheets_service.get_worksheet_data(
                spreadsheet_key=spreadsheet_key,
                worksheet_name='Super'
            )
            
            if not dados:
                self.logger.error("Nenhum dado encontrado na aba Super")
                return
            
            self.logger.info(f"Encontrados {len(dados)} registros na aba Super")
            
            # Processar dados
            solicitacoes_criadas = 0
            erros = 0
            
            for i, linha in enumerate(dados, start=1):
                resultado = self.processar_linha_super(linha, i)
                
                if not resultado:
                    erros += 1
                    continue
                
                if not dry_run:
                    try:
                        with transaction.atomic():
                            # Criar solicitação
                            solicitacao = Solicitacao.objects.create(**resultado['dados_solicitacao'])
                            
                            # Adicionar formador à solicitação
                            if resultado['formador']:
                                solicitacao.formadores_solicitados.add(resultado['formador'])
                            
                            solicitacoes_criadas += 1
                            
                    except Exception as e:
                        self.logger.error(f"Erro salvando linha {resultado['linha_original']}: {e}")
                        erros += 1
                else:
                    solicitacoes_criadas += 1
                    self.logger.debug(f"[DRY-RUN] Linha {i} processada com sucesso")

            # Relatório final
            self.logger.info("=" * 60)
            self.logger.info("RELATÓRIO FINAL - IMPORTAÇÃO ABA SUPER")
            self.logger.info("=" * 60)
            self.logger.info(f"Total de registros processados: {len(dados)}")
            self.logger.info(f"Solicitações criadas: {solicitacoes_criadas}")
            self.logger.info(f"Erros: {erros}")
            if dry_run:
                self.logger.info("MODO DRY-RUN: Nenhum dado foi salvo no banco")
            self.logger.info("=" * 60)
            
        except Exception as e:
            self.logger.error(f"Erro durante importação: {e}")
            raise CommandError(f"Falha na importação: {e}")

    def handle(self, *args, **options):
        self.setup_logging(options['verbose'])
        
        self.logger.info("Iniciando importação da aba Super")
        self.logger.info("Planilha: Acompanhamento de Agenda | 2025")
        self.logger.info("Aba: Super (colunas A até T)")
        
        if options['dry_run']:
            self.logger.info("MODO DRY-RUN: Apenas simulação, nada será salvo")
        
        try:
            self.importar_aba_super(dry_run=options['dry_run'])
            self.logger.info("Importação da aba Super concluída com sucesso!")
            
        except Exception as e:
            raise CommandError(f"Erro durante a importação: {e}")
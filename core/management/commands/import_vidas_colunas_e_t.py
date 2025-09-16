"""
Comando Django para importar especificamente as colunas E-T da aba 'Vidas'
da planilha Acompanhamento de Agenda | 2025 (linhas 1-1260)

Estrutura das colunas baseada na mesma estrutura da aba Super:
E: Municípios
F: encontro (tipo de encontro)
G: tipo (tipo de evento)
H: data
I: hora início
J: hora fim
K: projeto
L: segmento
M: Coord. Acompanha
N: Coordenador
O: Formador 1
P: Formador 2
Q: Formador 3
R: Formador 4
S: Formador 5
T: Convidados

Uso:
python manage.py import_vidas_colunas_e_t --spreadsheet-key=<ID> [--dry-run] [--verbose]
"""

import logging
import re
from datetime import datetime, date
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils.dateparse import parse_date, parse_datetime
from core.models import (
    Formador, Municipio, Projeto, TipoEvento, Solicitacao, 
    Usuario, Setor, SolicitacaoStatus, FormadoresSolicitacao
)
from core.services.google_sheets_service import google_sheets_service

User = get_user_model()

class Command(BaseCommand):
    help = 'Importa colunas E-T da aba Vidas (linhas 1-1260)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--spreadsheet-key',
            type=str,
            required=True,
            help='ID da planilha Google (extraído da URL)'
        )
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
        if not nome_formador or nome_formador.strip() == '' or nome_formador.strip() == '-':
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
        from django.contrib.auth.models import Group
        
        # Buscar ou criar grupo padrão para formadores importados
        grupo_formador, created = Group.objects.get_or_create(name='formador')
        
        email_formador = f"{nome_limpo.lower().replace(' ', '.').replace('ã', 'a').replace('ç', 'c')}@planilha.vidas"
        formador = Formador.objects.create(
            nome=nome_limpo,
            email=email_formador,
            area_atuacao=grupo_formador
        )
        self.logger.info(f"Novo formador criado: {nome_limpo}")
        return formador

    def extrair_uf_do_nome(self, nome_municipio):
        """
        Extrai a UF do nome do município
        Exemplos:
        - "Antônio Gonçalves - BA" → "BA"
        - "Araranguá - SC" → "SC"
        - "Atibaia - SP" → "SP"
        - "Chorozinho - CE" → "CE"
        - "Amigos do Bem" → "CE" (padrão quando não tem UF no nome)
        """
        # Padrão para capturar UF no final do nome: " - XX"
        padrao_uf = r'\s*-\s*([A-Z]{2})$'
        match = re.search(padrao_uf, nome_municipio)
        
        if match:
            return match.group(1)
        else:
            # Se não encontrar UF no nome, manter CE como padrão
            return 'CE'

    def get_or_create_municipio(self, nome_municipio):
        """Busca ou cria um município pelo nome"""
        if not nome_municipio or nome_municipio.strip() == '' or nome_municipio.strip() == '-':
            return None
            
        nome_limpo = nome_municipio.strip()
        
        try:
            return Municipio.objects.get(nome__iexact=nome_limpo)
        except Municipio.DoesNotExist:
            uf_extraida = self.extrair_uf_do_nome(nome_limpo)
            municipio = Municipio.objects.create(
                nome=nome_limpo,
                uf=uf_extraida
            )
            self.logger.info(f"Novo município criado: {nome_limpo} (UF: {uf_extraida})")
            return municipio

    def get_or_create_projeto(self, nome_projeto):
        """Busca ou cria um projeto pelo nome"""
        if not nome_projeto or nome_projeto.strip() == '' or nome_projeto.strip() == '-':
            return None
            
        nome_limpo = nome_projeto.strip()
        
        try:
            return Projeto.objects.get(nome__iexact=nome_limpo)
        except Projeto.DoesNotExist:
            # Buscar ou criar setor padrão
            from core.models import Setor
            setor_default, _ = Setor.objects.get_or_create(
                nome="Sem Setor",
                defaults={
                    'sigla': 'SS',
                    'vinculado_superintendencia': True,
                    'ativo': True
                }
            )
            
            projeto = Projeto.objects.create(
                nome=nome_limpo,
                descricao=f'Projeto importado da aba Vidas: {nome_limpo}',
                setor=setor_default,
                vinculado_superintendencia=True,  # Aba Vidas são eventos aprovados
                ativo=True,
                codigo_produto="SEM_COD",
                tipo_produto="FORMACAO"
            )
            self.logger.info(f"Novo projeto criado: {nome_limpo}")
            return projeto

    def get_or_create_tipo_evento(self, tipo_encontro, tipo_evento):
        """Busca ou cria um tipo de evento baseado nos campos F (encontro) e G (tipo)"""
        # Combinar informações dos dois campos para criar um tipo mais específico
        if tipo_encontro and tipo_evento:
            nome_completo = f"{tipo_encontro.strip()} - {tipo_evento.strip()}"
        elif tipo_encontro:
            nome_completo = tipo_encontro.strip()
        elif tipo_evento:
            nome_completo = tipo_evento.strip()
        else:
            nome_completo = 'Formação'  # Padrão
            
        try:
            return TipoEvento.objects.get(nome__iexact=nome_completo)
        except TipoEvento.DoesNotExist:
            tipo = TipoEvento.objects.create(
                nome=nome_completo,
                online=False  # Padrão presencial
            )
            self.logger.info(f"Novo tipo de evento criado: {nome_completo}")
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
            '%d.%m.%Y',
            '%d/%m/%y',
            '%d-%m-%y'
        ]
        
        for formato in formatos:
            try:
                data_convertida = datetime.strptime(str(data_str).strip(), formato).date()
                
                # Validar se a data está no ano de 2025 (aceita datas futuras)
                if data_convertida.year == 2025:
                    return data_convertida
                else:
                    self.logger.debug(f"Data fora do ano 2025 ignorada: {data_str}")
                    return None
                    
            except ValueError:
                continue
        
        self.logger.warning(f"Não foi possível converter data: {data_str}")
        return None

    def processar_linha_vidas(self, linha, linha_num):
        """Processa uma linha da aba Vidas focando nas colunas E-T"""
        try:
            # Mapear colunas E-T baseado na mesma estrutura da aba Super
            municipio_nome = linha.get('E', '').strip() if linha.get('E') else ''
            tipo_encontro = linha.get('F', '').strip() if linha.get('F') else ''
            tipo_evento = linha.get('G', '').strip() if linha.get('G') else ''
            data_evento = self.parse_data(linha.get('H', ''))
            horario_inicio = linha.get('I', '').strip() if linha.get('I') else '08:00'
            horario_fim = linha.get('J', '').strip() if linha.get('J') else '17:00'
            projeto_nome = linha.get('K', '').strip() if linha.get('K') else ''
            segmento = linha.get('L', '').strip() if linha.get('L') else ''
            coord_acompanha = linha.get('M', '').strip() if linha.get('M') else ''
            coordenador = linha.get('N', '').strip() if linha.get('N') else ''
            formador1_nome = linha.get('O', '').strip() if linha.get('O') else ''
            formador2_nome = linha.get('P', '').strip() if linha.get('P') else ''
            formador3_nome = linha.get('Q', '').strip() if linha.get('Q') else ''
            formador4_nome = linha.get('R', '').strip() if linha.get('R') else ''
            formador5_nome = linha.get('S', '').strip() if linha.get('S') else ''
            convidados = linha.get('T', '').strip() if linha.get('T') else ''

            # Validações básicas
            if not data_evento:
                self.logger.debug(f"Linha {linha_num}: Data inválida ou vazia, pulando")
                return None
                
            if not any([formador1_nome, formador2_nome, formador3_nome, formador4_nome, formador5_nome]):
                self.logger.debug(f"Linha {linha_num}: Nenhum formador especificado, pulando")
                return None

            if not municipio_nome and not projeto_nome:
                self.logger.debug(f"Linha {linha_num}: Sem município nem projeto, pulando")
                return None

            # Buscar/criar entidades relacionadas
            municipio = self.get_or_create_municipio(municipio_nome)
            projeto = self.get_or_create_projeto(projeto_nome)
            tipo_evento_obj = self.get_or_create_tipo_evento(tipo_encontro, tipo_evento)

            # Buscar/criar formadores (todos os que estão preenchidos)
            formadores = []
            for nome_formador in [formador1_nome, formador2_nome, formador3_nome, formador4_nome, formador5_nome]:
                if nome_formador and nome_formador != '-':
                    formador = self.get_or_create_formador(nome_formador)
                    if formador:
                        formadores.append(formador)

            if not formadores:
                self.logger.debug(f"Linha {linha_num}: Não foi possível criar/encontrar formadores")
                return None

            # Definir usuário solicitante (usar admin padrão)
            try:
                usuario_solicitante = Usuario.objects.filter(is_superuser=True).first()
                if not usuario_solicitante:
                    self.logger.error("Nenhum superusuário encontrado para ser o solicitante")
                    return None
            except Exception as e:
                self.logger.error(f"Erro ao definir usuário solicitante: {e}")
                return None

            # Criar observações detalhadas
            observacoes_partes = []
            if segmento:
                observacoes_partes.append(f"Segmento: {segmento}")
            if coord_acompanha:
                observacoes_partes.append(f"Coordenador Acompanha: {coord_acompanha}")
            if coordenador:
                observacoes_partes.append(f"Coordenador Responsável: {coordenador}")
            if convidados:
                observacoes_partes.append(f"Convidados: {convidados}")
            
            observacoes_completas = " | ".join(observacoes_partes) if observacoes_partes else "Importado da aba Vidas (colunas E-T)"

            # Status como aprovado (aba Vidas contém eventos aprovados)
            status = SolicitacaoStatus.APROVADO

            # Converter data e horários para o formato correto do modelo
            from datetime import datetime, time, date
            import pytz
            
            # Timezone padrão
            timezone = pytz.timezone('America/Fortaleza')
            
            # Combinar data com horários
            try:
                horario_inicio_time = datetime.strptime(horario_inicio, '%H:%M').time()
                horario_fim_time = datetime.strptime(horario_fim, '%H:%M').time()
            except:
                horario_inicio_time = time(8, 0)  # 08:00 como padrão
                horario_fim_time = time(17, 0)    # 17:00 como padrão
            
            # Criar datetime completos
            data_inicio = timezone.localize(
                datetime.combine(data_evento, horario_inicio_time)
            )
            data_fim = timezone.localize(
                datetime.combine(data_evento, horario_fim_time)
            )

            # Criar dados da solicitação com campos corretos do modelo
            dados_solicitacao = {
                'usuario_solicitante': usuario_solicitante,
                'projeto': projeto,
                'municipio': municipio,
                'tipo_evento': tipo_evento_obj,
                'titulo_evento': f"{projeto_nome} - {municipio_nome}" if projeto_nome and municipio_nome else "Evento Importado",
                'data_inicio': data_inicio,
                'data_fim': data_fim,
                'observacoes': observacoes_completas,
                'status': status,
                'coordenador_acompanha': 'Sim' in coord_acompanha if coord_acompanha else False,
                'numero_encontro_formativo': '1',  # Padrão
            }

            return {
                'dados_solicitacao': dados_solicitacao,
                'formadores': formadores,
                'linha_original': linha_num,
                'resumo': {
                    'data': data_evento.strftime('%d/%m/%Y') if data_evento else 'INVÁLIDA',
                    'municipio': municipio_nome or 'N/A',
                    'projeto': projeto_nome or 'N/A',
                    'formadores': [f.nome for f in formadores],
                    'tipo': f"{tipo_encontro} - {tipo_evento}".strip(' -')
                }
            }

        except Exception as e:
            self.logger.error(f"Erro processando linha {linha_num}: {e}")
            return None

    def extrair_dados_google_sheets(self, spreadsheet_key):
        """Extrai dados reais das colunas E-T da aba Vidas do Google Sheets"""
        try:
            self.logger.info(f"Conectando com Google Sheets: {spreadsheet_key}")
            self.logger.info("Extraindo colunas E-T da aba 'Vidas' (linhas 1-1260)")
            
            # Usar o serviço real do Google Sheets
            valores_raw = google_sheets_service.get_worksheet_range(
                spreadsheet_key=spreadsheet_key,
                range_name='E1:T1260',
                worksheet_name='Vidas'
            )
            
            if not valores_raw:
                self.logger.error("Nenhum dado encontrado no range especificado")
                return []
            
            self.logger.info(f"Dados extraídos: {len(valores_raw)} linhas")
            
            # Converter para formato de dicionário usando colunas como chaves
            colunas = ['E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T']
            dados_formatados = []
            
            for i, linha_raw in enumerate(valores_raw):
                # Pular linha de cabeçalho se for a primeira linha
                if i == 0:
                    continue
                    
                # Garantir que a linha tenha 16 colunas (E até T)
                linha_padded = linha_raw + [''] * (16 - len(linha_raw))
                
                # Criar dicionário da linha
                linha_dict = {}
                for j, coluna in enumerate(colunas):
                    if j < len(linha_padded):
                        linha_dict[coluna] = linha_padded[j]
                    else:
                        linha_dict[coluna] = ''
                
                dados_formatados.append(linha_dict)
            
            self.logger.info(f"Dados formatados: {len(dados_formatados)} registros válidos")
            return dados_formatados
            
        except Exception as e:
            self.logger.error(f"Erro ao extrair dados do Google Sheets: {e}")
            raise

    def importar_aba_vidas_colunas_e_t(self, spreadsheet_key, dry_run=False):
        """Importa dados das colunas E-T da aba Vidas"""
        try:
            self.logger.info("Conectando com Google Sheets real (aba Vidas)...")
            self.logger.info("Foco: Colunas E-T, Linhas 1-1260")
            
            # Extrair dados reais do Google Sheets
            dados = self.extrair_dados_google_sheets(spreadsheet_key)
            
            if not dados:
                self.logger.error("Nenhum dado encontrado")
                return
            
            self.logger.info(f"Processando {len(dados)} registros extraídos do Google Sheets")
            
            # Processar dados
            solicitacoes_criadas = 0
            erros = 0
            formadores_criados = 0
            municipios_criados = 0
            projetos_criados = 0
            
            for i, linha in enumerate(dados, start=1):
                resultado = self.processar_linha_vidas(linha, i)
                
                if not resultado:
                    erros += 1
                    continue
                
                # Mostrar prévia dos dados tratados
                resumo = resultado['resumo']
                self.logger.info(f"Linha {i}: {resumo['data']} | {resumo['municipio']} | {resumo['projeto']} | Formadores: {len(resumo['formadores'])}")
                if self.logger.level == logging.DEBUG:
                    self.logger.debug(f"  Formadores: {', '.join(resumo['formadores'])}")
                    self.logger.debug(f"  Tipo: {resumo['tipo']}")
                
                if not dry_run:
                    try:
                        with transaction.atomic():
                            # Criar solicitação
                            solicitacao = Solicitacao.objects.create(**resultado['dados_solicitacao'])
                            
                            # Criar relacionamentos FormadoresSolicitacao
                            for formador in resultado['formadores']:
                                FormadoresSolicitacao.objects.create(
                                    solicitacao=solicitacao,
                                    formador=formador
                                )
                            
                            solicitacoes_criadas += 1
                            
                    except Exception as e:
                        self.logger.error(f"Erro salvando linha {resultado['linha_original']}: {e}")
                        erros += 1
                else:
                    solicitacoes_criadas += 1

            # Relatório final
            self.logger.info("=" * 70)
            self.logger.info("RELATÓRIO FINAL - IMPORTAÇÃO ABA VIDAS (COLUNAS E-T)")
            self.logger.info("=" * 70)
            self.logger.info(f"Total de registros processados: {len(dados)}")
            self.logger.info(f"Solicitações criadas: {solicitacoes_criadas}")
            self.logger.info(f"Erros/Linhas puladas: {erros}")
            if dry_run:
                self.logger.info("MODO DRY-RUN: Nenhum dado foi salvo no banco")
            else:
                self.logger.info("Dados salvos no banco com sucesso!")
            self.logger.info("=" * 70)
            
            # Salvar dados tratados em arquivo JSON para análise
            dados_tratados = []
            for i, linha in enumerate(dados, start=1):
                resultado = self.processar_linha_vidas(linha, i)
                if resultado:
                    dados_tratados.append({
                        'linha': i,
                        'data_evento': resultado['resumo']['data'],
                        'municipio': resultado['resumo']['municipio'],
                        'projeto': resultado['resumo']['projeto'],
                        'tipo_evento': resultado['resumo']['tipo'],
                        'formadores': resultado['resumo']['formadores'],
                        'dados_completos': resultado['dados_solicitacao'],
                        'observacoes': resultado['dados_solicitacao']['observacoes']
                    })
            
            import json
            arquivo_saida = 'dados_planilhas_originais/vidas_colunas_e_t_tratados.json'
            with open(arquivo_saida, 'w', encoding='utf-8') as f:
                json.dump(dados_tratados, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"✅ Dados tratados salvos em: {arquivo_saida}")
            self.logger.info(f"📊 {len(dados_tratados)} registros válidos no arquivo JSON")
            
        except Exception as e:
            self.logger.error(f"Erro durante importação: {e}")
            raise CommandError(f"Falha na importação: {e}")

    def handle(self, *args, **options):
        self.setup_logging(options['verbose'])
        
        spreadsheet_key = options['spreadsheet_key']
        
        self.logger.info("Iniciando importação das colunas E-T da aba Vidas")
        self.logger.info(f"Planilha Google Sheets: {spreadsheet_key}")
        self.logger.info("Foco: Colunas E (Municípios) até T (Convidados)")
        self.logger.info("Intervalo: Linhas 1 até 1260")
        
        if options['dry_run']:
            self.logger.info("MODO DRY-RUN: Apenas simulação, nada será salvo")
        
        try:
            self.importar_aba_vidas_colunas_e_t(
                spreadsheet_key=spreadsheet_key,
                dry_run=options['dry_run']
            )
            self.logger.info("Importação das colunas E-T da aba Vidas concluída com sucesso!")
            
        except Exception as e:
            raise CommandError(f"Erro durante a importação: {e}")
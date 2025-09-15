"""
Comando para análise da planilha de Acompanhamento de Agenda | 2025
==================================================================

Comando Django para analisar e extrair dados de solicitações de eventos
da planilha Google Sheets "Acompanhamento de Agenda | 2025".

Autor: Claude Code  
Data: Janeiro 2025
"""

import json
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

from core.services.google_sheets_service import google_sheets_service

User = get_user_model()


class Command(BaseCommand):
    help = "Analisa a planilha Google Sheets 'Acompanhamento de Agenda | 2025'"

    def add_arguments(self, parser):
        parser.add_argument(
            '--spreadsheet-key',
            type=str,
            default='16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU',
            help='ID da planilha Google (padrão: Acompanhamento de Agenda | 2025)'
        )
        
        parser.add_argument(
            '--worksheet-name',
            type=str,
            help='Nome da aba específica para analisar'
        )
        
        parser.add_argument(
            '--export-json',
            type=str,
            help='Caminho para exportar dados em JSON'
        )
        
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Mostrar análise detalhada de cada aba'
        )

    def handle(self, *args, **options):
        spreadsheet_key = options['spreadsheet_key']
        worksheet_name = options.get('worksheet_name')
        export_json = options.get('export_json')
        detailed = options['detailed']

        self.stdout.write("=" * 60)
        self.stdout.write("ANÁLISE DA PLANILHA: Acompanhamento de Agenda | 2025")
        self.stdout.write("=" * 60)
        self.stdout.write(f"Planilha ID: {spreadsheet_key}")

        try:
            # Obter informações básicas da planilha
            spreadsheet_info = google_sheets_service.get_spreadsheet_info(
                spreadsheet_key
            )
            
            self.stdout.write(f"Título: {spreadsheet_info['title']}")
            self.stdout.write(f"Total de abas: {len(spreadsheet_info['worksheets'])}")
            self.stdout.write("")

            # Abas alvo para análise
            target_worksheets = ['Super', 'ACerta', 'Outros', 'Brincando', 'Vidas', 'Configurações']
            
            # Estrutura para coleta de dados
            analysis_data = {
                'planilha_info': spreadsheet_info,
                'abas_analisadas': {},
                'resumo_geral': {
                    'total_registros': 0,
                    'formadores_encontrados': set(),
                    'municipios_encontrados': set(),
                    'tipos_evento_encontrados': set(),
                    'projetos_encontrados': set(),
                    'status_encontrados': set()
                }
            }

            # Processar cada aba
            for ws_info in spreadsheet_info['worksheets']:
                ws_name = ws_info['title']
                
                # Se worksheet específico foi solicitado, processar apenas ele
                if worksheet_name and ws_name != worksheet_name:
                    continue
                
                # Se não foi especificado, processar apenas as abas alvo
                if not worksheet_name and ws_name not in target_worksheets:
                    continue
                
                self.stdout.write(f"Analisando aba: {ws_name}")
                self.stdout.write("-" * 40)
                
                try:
                    # Obter dados da aba
                    ws_data = google_sheets_service.get_worksheet_data(
                        spreadsheet_key, ws_name
                    )
                    
                    if not ws_data:
                        self.stdout.write("  [X] Nenhum dado encontrado")
                        analysis_data['abas_analisadas'][ws_name] = {
                            'erro': 'Nenhum dado encontrado',
                            'registros': 0
                        }
                        continue
                    
                    # Analisar estrutura da aba
                    aba_analysis = self.analyze_worksheet(ws_name, ws_data, detailed)
                    analysis_data['abas_analisadas'][ws_name] = aba_analysis
                    
                    # Atualizar resumo geral
                    analysis_data['resumo_geral']['total_registros'] += aba_analysis['total_registros']
                    
                    # Coletar valores únicos
                    if 'valores_unicos' in aba_analysis:
                        for campo, valores in aba_analysis['valores_unicos'].items():
                            if campo == 'formadores':
                                analysis_data['resumo_geral']['formadores_encontrados'].update(valores)
                            elif campo == 'municipios':
                                analysis_data['resumo_geral']['municipios_encontrados'].update(valores)
                            elif campo == 'tipos_evento':
                                analysis_data['resumo_geral']['tipos_evento_encontrados'].update(valores)
                            elif campo == 'projetos':
                                analysis_data['resumo_geral']['projetos_encontrados'].update(valores)
                            elif campo == 'status':
                                analysis_data['resumo_geral']['status_encontrados'].update(valores)
                    
                    self.stdout.write("")
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  [X] Erro ao processar aba {ws_name}: {e}"))
                    analysis_data['abas_analisadas'][ws_name] = {
                        'erro': str(e),
                        'registros': 0
                    }

            # Converter sets para listas para serialização JSON
            for key in analysis_data['resumo_geral']:
                if isinstance(analysis_data['resumo_geral'][key], set):
                    analysis_data['resumo_geral'][key] = list(analysis_data['resumo_geral'][key])

            # Exibir resumo final
            self.display_final_summary(analysis_data)
            
            # Exportar para JSON se solicitado
            if export_json:
                self.export_to_json(analysis_data, export_json)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro durante análise: {e}"))
            raise CommandError(f"Falha na análise: {e}")

    def analyze_worksheet(self, ws_name, data, detailed=False):
        """Analisa uma aba específica"""
        analysis = {
            'nome_aba': ws_name,
            'total_registros': len(data),
            'estrutura_colunas': [],
            'amostra_dados': [],
            'valores_unicos': {},
            'observacoes': []
        }
        
        if not data:
            return analysis
        
        # Analisar estrutura das colunas
        if data:
            first_row = data[0]
            analysis['estrutura_colunas'] = list(first_row.keys())
            
            self.stdout.write(f"  [#] Total de registros: {len(data)}")
            self.stdout.write(f"  [+] Colunas encontradas: {len(first_row.keys())}")
            
            if detailed:
                self.stdout.write("  [-] Colunas:")
                for col in first_row.keys():
                    self.stdout.write(f"    - {col}")
        
        # Coletar amostra de dados (primeiros 5 registros)
        sample_size = min(5, len(data))
        analysis['amostra_dados'] = data[:sample_size]
        
        if detailed and sample_size > 0:
            self.stdout.write(f"  [*] Amostra de dados (primeiros {sample_size} registros):")
            for i, record in enumerate(analysis['amostra_dados'], 1):
                self.stdout.write(f"    Registro {i}:")
                for key, value in record.items():
                    if value:  # Mostrar apenas campos preenchidos
                        value_str = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                        self.stdout.write(f"      {key}: {value_str}")
        
        # Identificar valores únicos em campos relevantes
        self.extract_unique_values(data, analysis)
        
        # Análise específica por tipo de aba
        if ws_name.lower() in ['super', 'acerta', 'outros', 'brincando', 'vidas']:
            self.analyze_event_worksheet(ws_name, data, analysis, detailed)
        elif ws_name.lower() == 'configurações':
            self.analyze_config_worksheet(data, analysis, detailed)
        
        return analysis

    def extract_unique_values(self, data, analysis):
        """Extrai valores únicos de campos relevantes"""
        campos_relevantes = [
            'formador', 'formadores', 'nome_formador', 'instrutor',
            'municipio', 'cidade', 'local', 'localidade',
            'tipo_evento', 'tipo', 'modalidade', 'evento',
            'projeto', 'programa', 'acao',
            'status', 'situacao', 'aprovado', 'aprovacao'
        ]
        
        unique_values = {}
        
        for record in data:
            for key, value in record.items():
                # Verificar se a coluna é relevante (busca parcial)
                key_lower = key.lower()
                is_relevant = any(campo in key_lower for campo in campos_relevantes)
                
                if is_relevant and value:
                    # Normalizar nome do campo
                    field_name = self.normalize_field_name(key_lower)
                    if field_name not in unique_values:
                        unique_values[field_name] = set()
                    
                    # Adicionar valor (limpo)
                    clean_value = str(value).strip()
                    if clean_value:
                        unique_values[field_name].add(clean_value)
        
        # Converter para listas e armazenar
        for field_name, values in unique_values.items():
            analysis['valores_unicos'][field_name] = list(values)
        
        return unique_values

    def normalize_field_name(self, field_name):
        """Normaliza nomes de campos para categorias padrão"""
        if any(term in field_name for term in ['formador', 'instrutor', 'professor']):
            return 'formadores'
        elif any(term in field_name for term in ['municipio', 'cidade', 'local']):
            return 'municipios'  
        elif any(term in field_name for term in ['tipo', 'modalidade', 'evento']):
            return 'tipos_evento'
        elif any(term in field_name for term in ['projeto', 'programa', 'acao']):
            return 'projetos'
        elif any(term in field_name for term in ['status', 'situacao', 'aprovad']):
            return 'status'
        else:
            return field_name

    def analyze_event_worksheet(self, ws_name, data, analysis, detailed=False):
        """Análise específica para abas de eventos"""
        analysis['observacoes'].append(f"Aba identificada como: SOLICITAÇÕES DE EVENTOS")
        
        # Buscar padrões específicos de evento
        event_patterns = []
        date_fields = []
        time_fields = []
        
        for record in data:
            for key in record.keys():
                key_lower = key.lower()
                if any(term in key_lower for term in ['data', 'dia', 'quando']):
                    if key not in date_fields:
                        date_fields.append(key)
                elif any(term in key_lower for term in ['hora', 'horario', 'inicio', 'fim']):
                    if key not in time_fields:
                        time_fields.append(key)
        
        if date_fields:
            analysis['observacoes'].append(f"Campos de data encontrados: {', '.join(date_fields)}")
        if time_fields:
            analysis['observacoes'].append(f"Campos de horário encontrados: {', '.join(time_fields)}")

    def analyze_config_worksheet(self, data, analysis, detailed=False):
        """Análise específica para aba de configurações"""
        analysis['observacoes'].append("Aba identificada como: CONFIGURAÇÕES DO SISTEMA")
        
        # Buscar configurações relevantes
        config_types = []
        for record in data:
            for key, value in record.items():
                if value and any(term in key.lower() for term in ['config', 'parametro', 'opcao']):
                    config_types.append(f"{key}: {value}")
        
        if config_types:
            analysis['observacoes'].append("Configurações encontradas:")
            analysis['observacoes'].extend(config_types[:10])  # Limitar a 10 itens

    def display_final_summary(self, analysis_data):
        """Exibe resumo final da análise"""
        self.stdout.write("=" * 60)
        self.stdout.write("RESUMO FINAL DA ANÁLISE")
        self.stdout.write("=" * 60)
        
        resumo = analysis_data['resumo_geral']
        
        self.stdout.write(f"[#] Total de registros analisados: {resumo['total_registros']}")
        self.stdout.write(f"[+] Total de abas processadas: {len(analysis_data['abas_analisadas'])}")
        self.stdout.write("")
        
        # Exibir contadores por categoria
        categories = [
            ('formadores_encontrados', 'Formadores únicos'),
            ('municipios_encontrados', 'Municípios únicos'),
            ('tipos_evento_encontrados', 'Tipos de evento únicos'),
            ('projetos_encontrados', 'Projetos únicos'),
            ('status_encontrados', 'Status únicos')
        ]
        
        for key, label in categories:
            items = resumo.get(key, [])
            if items:
                self.stdout.write(f"[*] {label}: {len(items)}")
                if len(items) <= 10:
                    for item in sorted(items):
                        self.stdout.write(f"   - {item}")
                else:
                    for item in sorted(items)[:8]:
                        self.stdout.write(f"   - {item}")
                    self.stdout.write(f"   ... e mais {len(items)-8} itens")
                self.stdout.write("")
        
        # Resumo por aba
        self.stdout.write("[+] RESUMO POR ABA:")
        for aba_nome, aba_data in analysis_data['abas_analisadas'].items():
            if 'erro' in aba_data:
                self.stdout.write(f"  [X] {aba_nome}: {aba_data['erro']}")
            else:
                registros = aba_data.get('total_registros', 0)
                colunas = len(aba_data.get('estrutura_colunas', []))
                self.stdout.write(f"  [OK] {aba_nome}: {registros} registros, {colunas} colunas")

    def export_to_json(self, data, file_path):
        """Exporta dados para arquivo JSON"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.stdout.write(f"[OK] Dados exportados para: {file_path}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[X] Erro ao exportar JSON: {e}"))
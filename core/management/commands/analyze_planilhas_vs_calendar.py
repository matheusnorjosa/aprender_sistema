"""
Comando Django para analisar planilhas de controle existentes e comparar com Google Calendar.
Como não conseguimos acessar o Calendar por problemas de escopo, vamos analisar as planilhas.
"""

import json
import os
import pandas as pd
from datetime import datetime
from collections import defaultdict, Counter
from typing import Dict, List, Any

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Analisa planilhas de controle existentes e gera relatório comparativo'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-file',
            type=str,
            default='out/analise_planilhas_controle.json',
            help='Arquivo JSON de saída para salvar os resultados'
        )
        parser.add_argument(
            '--year',
            type=int,
            default=2025,
            help='Ano dos eventos a serem analisados (padrão: 2025)'
        )

    def handle(self, *args, **options):
        output_file = options['output_file']
        year = options['year']

        self.stdout.write(
            self.style.HTTP_INFO(f'Analisando planilhas de controle para {year}...')
        )

        try:
            # Analisar planilhas existentes
            planilhas_data = self._analyze_spreadsheets(year)
            
            # Gerar análise estatística das planilhas
            statistics = self._generate_spreadsheet_statistics(planilhas_data, year)
            
            # Preparar resultado final
            result = {
                'analyzed_at': datetime.now().isoformat(),
                'year': year,
                'planilhas_found': len(planilhas_data),
                'statistics': statistics,
                'planilhas_data': planilhas_data,
                'recommendations': self._generate_recommendations(statistics)
            }
            
            # Salvar em arquivo
            self._save_to_file(result, output_file)
            self.stdout.write(
                self.style.SUCCESS(f'Dados salvos em: {output_file}')
            )
            
            # Exibir resumo
            self._display_summary(result)
            
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f'Erro ao analisar planilhas: {str(e)}')
            )
            raise CommandError(f'Falha na análise: {str(e)}')

    def _analyze_spreadsheets(self, year: int) -> List[Dict[str, Any]]:
        """Analisa planilhas encontradas no sistema"""
        planilhas_data = []
        
        # Buscar planilhas no archive/spreadsheets
        spreadsheets_dir = os.path.join('archive', 'spreadsheets')
        
        if not os.path.exists(spreadsheets_dir):
            self.stdout.write(self.style.WARNING('Diretório archive/spreadsheets não encontrado'))
            return planilhas_data
            
        for filename in os.listdir(spreadsheets_dir):
            if filename.endswith('.xlsx'):
                file_path = os.path.join(spreadsheets_dir, filename)
                self.stdout.write(f'Analisando: {filename}')
                
                try:
                    planilha_info = self._analyze_single_spreadsheet(file_path, filename, year)
                    if planilha_info:
                        planilhas_data.append(planilha_info)
                except Exception as e:
                    self.stderr.write(
                        self.style.WARNING(f'Erro ao analisar {filename}: {str(e)}')
                    )
        
        return planilhas_data

    def _analyze_single_spreadsheet(self, file_path: str, filename: str, year: int) -> Dict[str, Any]:
        """Analisa uma planilha individual"""
        try:
            # Ler planilha
            excel_file = pd.ExcelFile(file_path)
            
            # Informações básicas
            info = {
                'filename': filename,
                'file_path': file_path,
                'file_size': os.path.getsize(file_path),
                'sheet_names': excel_file.sheet_names,
                'total_sheets': len(excel_file.sheet_names),
                'events_found': 0,
                'events_2025': 0,
                'formadores_mentioned': set(),
                'municipios_mentioned': set(),
                'analysis_details': {}
            }
            
            # Analisar cada aba
            for sheet_name in excel_file.sheet_names[:5]:  # Limitar a 5 abas por performance
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    
                    sheet_analysis = {
                        'rows': len(df),
                        'columns': len(df.columns),
                        'column_names': list(df.columns)[:10],  # Primeiras 10 colunas
                        'has_dates': False,
                        'date_columns': [],
                        'potential_events': 0,
                        'year_2025_references': 0
                    }
                    
                    # Procurar colunas com datas
                    for col in df.columns:
                        try:
                            # Tentar converter coluna para data
                            date_series = pd.to_datetime(df[col], errors='coerce')
                            valid_dates = date_series.dropna()
                            
                            if len(valid_dates) > 0:
                                sheet_analysis['has_dates'] = True
                                sheet_analysis['date_columns'].append(col)
                                
                                # Contar eventos de 2025
                                dates_2025 = valid_dates[valid_dates.dt.year == year]
                                if len(dates_2025) > 0:
                                    sheet_analysis['year_2025_references'] += len(dates_2025)
                                    info['events_2025'] += len(dates_2025)
                                    
                        except:
                            pass
                    
                    # Procurar menções de formadores (assumindo nomes próprios)
                    text_content = df.astype(str).values.flatten()
                    for text in text_content:
                        if isinstance(text, str) and len(text.split()) == 2:
                            # Possível nome de pessoa (2 palavras)
                            if text.replace(' ', '').isalpha() and text.istitle():
                                info['formadores_mentioned'].add(text)
                    
                    # Procurar menções de municípios (algumas cidades conhecidas do CE)
                    municipios_ce = [
                        'Fortaleza', 'Caucaia', 'Juazeiro', 'Maracanaú', 'Sobral',
                        'Crato', 'Itapipoca', 'Maranguape', 'Iguatu', 'Quixadá',
                        'Canindé', 'Aquiraz', 'Pacatuba', 'Crateús', 'Russas'
                    ]
                    
                    for municipio in municipios_ce:
                        if any(municipio.lower() in str(cell).lower() for cell in text_content):
                            info['municipios_mentioned'].add(municipio)
                    
                    info['analysis_details'][sheet_name] = sheet_analysis
                    info['events_found'] += sheet_analysis['potential_events']
                    
                except Exception as e:
                    self.stderr.write(
                        self.style.WARNING(f'Erro na aba {sheet_name} de {filename}: {str(e)}')
                    )
            
            # Converter sets para lists para serialização JSON
            info['formadores_mentioned'] = list(info['formadores_mentioned'])
            info['municipios_mentioned'] = list(info['municipios_mentioned'])
            
            return info
            
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f'Erro ao analisar planilha {filename}: {str(e)}')
            )
            return None

    def _generate_spreadsheet_statistics(self, planilhas_data: List[Dict[str, Any]], year: int) -> Dict[str, Any]:
        """Gera estatísticas das planilhas analisadas"""
        
        if not planilhas_data:
            return {'error': 'Nenhuma planilha encontrada para análise'}
        
        # Contadores
        total_planilhas = len(planilhas_data)
        total_sheets = sum(p.get('total_sheets', 0) for p in planilhas_data)
        total_events_2025 = sum(p.get('events_2025', 0) for p in planilhas_data)
        
        # Formadores únicos mencionados
        all_formadores = set()
        for planilha in planilhas_data:
            all_formadores.update(planilha.get('formadores_mentioned', []))
        
        # Municípios únicos mencionados  
        all_municipios = set()
        for planilha in planilhas_data:
            all_municipios.update(planilha.get('municipios_mentioned', []))
        
        # Planilhas com mais eventos
        planilhas_por_eventos = sorted(
            planilhas_data, 
            key=lambda p: p.get('events_2025', 0), 
            reverse=True
        )
        
        # Tamanhos de arquivo
        file_sizes = [p.get('file_size', 0) for p in planilhas_data]
        
        return {
            'summary': {
                'total_planilhas': total_planilhas,
                'total_sheets': total_sheets,
                'total_events_2025': total_events_2025,
                'unique_formadores_mentioned': len(all_formadores),
                'unique_municipios_mentioned': len(all_municipios),
                'average_sheets_per_planilha': round(total_sheets / total_planilhas, 1),
                'total_file_size_mb': round(sum(file_sizes) / (1024*1024), 2)
            },
            'top_planilhas_by_events': [
                {
                    'filename': p['filename'],
                    'events_2025': p.get('events_2025', 0),
                    'sheets': p.get('total_sheets', 0)
                }
                for p in planilhas_por_eventos[:5]
            ],
            'formadores_mentioned': sorted(list(all_formadores)),
            'municipios_mentioned': sorted(list(all_municipios)),
            'file_size_distribution': {
                'smallest_mb': round(min(file_sizes) / (1024*1024), 2) if file_sizes else 0,
                'largest_mb': round(max(file_sizes) / (1024*1024), 2) if file_sizes else 0,
                'average_mb': round(sum(file_sizes) / len(file_sizes) / (1024*1024), 2) if file_sizes else 0
            }
        }

    def _generate_recommendations(self, statistics: Dict[str, Any]) -> List[str]:
        """Gera recomendações baseadas na análise"""
        recommendations = []
        
        summary = statistics.get('summary', {})
        
        if summary.get('total_events_2025', 0) > 0:
            recommendations.append(
                f"Encontrados {summary['total_events_2025']} possíveis eventos de 2025 nas planilhas - "
                "considere migrar para o Google Calendar"
            )
        
        if summary.get('unique_formadores_mentioned', 0) > 0:
            recommendations.append(
                f"Identificados {summary['unique_formadores_mentioned']} possíveis formadores - "
                "verificar cadastro no sistema"
            )
        
        if summary.get('unique_municipios_mentioned', 0) > 0:
            recommendations.append(
                f"Identificados {summary['unique_municipios_mentioned']} municípios - "
                "verificar cadastro no sistema"
            )
        
        if summary.get('total_planilhas', 0) > 5:
            recommendations.append(
                "Grande quantidade de planilhas detectada - "
                "considere consolidar dados em sistema único"
            )
        
        recommendations.append(
            "Resolva o problema de escopo do Google Calendar API para acessar eventos reais"
        )
        
        return recommendations

    def _save_to_file(self, data: Dict[str, Any], filename: str):
        """Salva os dados em arquivo JSON"""
        try:
            os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
                
        except Exception as e:
            raise CommandError(f'Erro ao salvar arquivo: {str(e)}')

    def _display_summary(self, result: Dict[str, Any]):
        """Exibe resumo dos resultados na console"""
        stats = result.get('statistics', {})
        summary = stats.get('summary', {})
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.HTTP_INFO('RESUMO DA ANALISE DAS PLANILHAS'))
        self.stdout.write('='*60)
        
        self.stdout.write(f'Periodo analisado: {result["year"]}')
        self.stdout.write(f'Total de planilhas: {self.style.SUCCESS(str(summary.get("total_planilhas", 0)))}')
        self.stdout.write(f'Total de abas: {summary.get("total_sheets", 0)}')
        self.stdout.write(f'Eventos de 2025 encontrados: {summary.get("total_events_2025", 0)}')
        
        # Formadores
        unique_formadores = summary.get('unique_formadores_mentioned', 0)
        if unique_formadores > 0:
            self.stdout.write(f'Possíveis formadores identificados: {unique_formadores}')
            
            formadores_list = stats.get('formadores_mentioned', [])[:5]
            if formadores_list:
                self.stdout.write('  Exemplos: ' + ', '.join(formadores_list))
        
        # Municípios
        unique_municipios = summary.get('unique_municipios_mentioned', 0)
        if unique_municipios > 0:
            self.stdout.write(f'Municípios identificados: {unique_municipios}')
            
            municipios_list = stats.get('municipios_mentioned', [])
            if municipios_list:
                self.stdout.write('  Municípios: ' + ', '.join(municipios_list))
        
        # Top planilhas
        top_planilhas = stats.get('top_planilhas_by_events', [])
        if top_planilhas:
            self.stdout.write('\nPlanilhas com mais eventos de 2025:')
            for i, planilha in enumerate(top_planilhas[:3], 1):
                if planilha.get('events_2025', 0) > 0:
                    self.stdout.write(
                        f'  {i}. {planilha["filename"]}: {planilha["events_2025"]} eventos'
                    )
        
        # Recomendações
        recommendations = result.get('recommendations', [])
        if recommendations:
            self.stdout.write('\nRecomendações:')
            for i, rec in enumerate(recommendations, 1):
                self.stdout.write(f'  {i}. {rec}')
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('Analise concluida!'))
        self.stdout.write('='*60 + '\n')
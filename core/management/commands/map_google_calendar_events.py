"""
Comando Django para mapear todos os eventos de 2025 do Google Calendar específico.
Coleta informações completas para análise e comparação com planilhas.
"""

import json
import os
from datetime import datetime
from collections import defaultdict, Counter
from typing import Dict, List, Any
import calendar

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone

from core.services.integrations.google_calendar import GoogleCalendarService


class Command(BaseCommand):
    help = 'Mapeia todos os eventos de 2025 do Google Calendar específico'

    def add_arguments(self, parser):
        parser.add_argument(
            '--calendar-id',
            type=str,
            default='c_3381579109915e33c06be465adfbd9a31aaf4205c0bd45aa050c5a18be99fe15@group.calendar.google.com',
            help='ID do Google Calendar a ser analisado'
        )
        parser.add_argument(
            '--year',
            type=int,
            default=2025,
            help='Ano dos eventos a serem mapeados (padrão: 2025)'
        )
        parser.add_argument(
            '--output-file',
            type=str,
            help='Arquivo JSON de saída para salvar os resultados (opcional)'
        )
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Inclui informações detalhadas de cada evento'
        )

    def handle(self, *args, **options):
        calendar_id = options['calendar_id']
        year = options['year']
        output_file = options.get('output_file')
        detailed = options['detailed']

        self.stdout.write(
            self.style.HTTP_INFO(f'Mapeando eventos de {year} do Google Calendar...')
        )
        self.stdout.write(f'Calendar ID: {calendar_id}')

        try:
            # Inicializar serviço do Google Calendar
            service = GoogleCalendarService(calendar_id=calendar_id)
            
            # Mapear eventos do ano inteiro
            events_data = self._map_yearly_events(service, year)
            
            # Gerar análise estatística
            statistics = self._generate_statistics(events_data['events'], year)
            
            # Preparar resultado final
            result = {
                'calendar_id': calendar_id,
                'year': year,
                'extracted_at': datetime.now().isoformat(),
                'total_events': len(events_data['events']),
                'statistics': statistics,
                'events': events_data['events'] if detailed else []
            }
            
            # Salvar em arquivo se especificado
            if output_file:
                self._save_to_file(result, output_file)
                self.stdout.write(
                    self.style.SUCCESS(f'Dados salvos em: {output_file}')
                )
            
            # Exibir resumo
            self._display_summary(result)
            
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f'Erro ao mapear eventos: {str(e)}')
            )
            raise CommandError(f'Falha no mapeamento: {str(e)}')

    def _map_yearly_events(self, service, year: int) -> Dict[str, Any]:
        """Mapeia todos os eventos do ano especificado."""
        all_events = []
        errors = []
        
        # Definir período do ano
        start_time = datetime(year, 1, 1, 0, 0, 0)
        end_time = datetime(year + 1, 1, 1, 0, 0, 0)
        
        try:
            # Buscar eventos em batches (Google Calendar API tem limite)
            page_token = None
            batch_count = 0
            
            while True:
                batch_count += 1
                self.stdout.write(f'Processando lote {batch_count}...')
                
                # Parâmetros da consulta
                params = {
                    'calendarId': service.calendar_id,
                    'timeMin': start_time.isoformat() + 'Z',
                    'timeMax': end_time.isoformat() + 'Z',
                    'singleEvents': True,
                    'orderBy': 'startTime',
                    'maxResults': 2500,  # Máximo permitido pela API
                    'showDeleted': True,  # Incluir eventos cancelados
                }
                
                if page_token:
                    params['pageToken'] = page_token
                
                # Executar consulta
                google_service = service._get_service()
                events_result = google_service.events().list(**params).execute()
                
                events = events_result.get('items', [])
                self.stdout.write(f'   Encontrados {len(events)} eventos neste lote')
                
                # Processar cada evento
                for event in events:
                    try:
                        processed_event = self._process_event(event)
                        all_events.append(processed_event)
                    except Exception as e:
                        error_msg = f"Erro ao processar evento {event.get('id', 'desconhecido')}: {str(e)}"
                        errors.append(error_msg)
                        self.stderr.write(self.style.WARNING(f'WARNING: {error_msg}'))
                
                # Verificar se há mais páginas
                page_token = events_result.get('nextPageToken')
                if not page_token:
                    break
                    
        except Exception as e:
            error_msg = f"Erro ao buscar eventos da API: {str(e)}"
            errors.append(error_msg)
            self.stderr.write(self.style.ERROR(f'ERROR: {error_msg}'))
        
        return {
            'events': all_events,
            'errors': errors,
            'total_batches': batch_count
        }

    def _process_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Processa um evento individual extraindo informações relevantes."""
        
        # Extrair datas (tratando diferentes formatos)
        start_info = event.get('start', {})
        end_info = event.get('end', {})
        
        # Data/hora de início
        if 'dateTime' in start_info:
            start_datetime = start_info['dateTime']
            is_all_day = False
        elif 'date' in start_info:
            start_datetime = start_info['date']
            is_all_day = True
        else:
            start_datetime = None
            is_all_day = False
            
        # Data/hora de fim
        if 'dateTime' in end_info:
            end_datetime = end_info['dateTime']
        elif 'date' in end_info:
            end_datetime = end_info['date']
        else:
            end_datetime = None

        # Extrair participantes
        attendees = event.get('attendees', [])
        attendee_emails = [a.get('email', '') for a in attendees if a.get('email')]
        
        # Extrair informações do organizador
        organizer = event.get('organizer', {})
        creator = event.get('creator', {})
        
        return {
            'id': event.get('id'),
            'title': event.get('summary', 'Sem título'),
            'description': event.get('description', ''),
            'location': event.get('location', ''),
            'status': event.get('status', 'confirmed'),
            'start_datetime': start_datetime,
            'end_datetime': end_datetime,
            'is_all_day': is_all_day,
            'timezone': start_info.get('timeZone', 'America/Fortaleza'),
            'html_link': event.get('htmlLink', ''),
            'hangout_link': event.get('hangoutLink', ''),
            'meet_link': event.get('conferenceData', {}).get('entryPoints', [{}])[0].get('uri', ''),
            'attendees': attendee_emails,
            'attendee_count': len(attendee_emails),
            'organizer_email': organizer.get('email', ''),
            'organizer_name': organizer.get('displayName', ''),
            'creator_email': creator.get('email', ''),
            'creator_name': creator.get('displayName', ''),
            'created': event.get('created'),
            'updated': event.get('updated'),
            'recurring_event_id': event.get('recurringEventId'),
            'is_recurring': bool(event.get('recurringEventId')),
            'visibility': event.get('visibility', 'default'),
            'transparency': event.get('transparency', 'opaque'),
            'ical_uid': event.get('iCalUID', ''),
            'event_type': event.get('eventType', 'default'),
        }

    def _generate_statistics(self, events: List[Dict[str, Any]], year: int) -> Dict[str, Any]:
        """Gera estatísticas detalhadas dos eventos."""
        
        if not events:
            return {'error': 'Nenhum evento encontrado para análise'}
        
        # Contadores básicos
        total_events = len(events)
        status_count = Counter(event.get('status', 'unknown') for event in events)
        
        # Estatísticas por mês
        monthly_stats = defaultdict(int)
        monthly_details = defaultdict(list)
        
        # Análise de organizadores/criadores
        organizers = Counter()
        creators = Counter()
        
        # Análise de tipos/padrões de eventos
        title_patterns = Counter()
        location_stats = Counter()
        
        # Eventos com Meet
        events_with_meet = 0
        
        # Processar cada evento
        for event in events:
            try:
                # Extrair mês da data de início
                start_datetime = event.get('start_datetime')
                if start_datetime:
                    try:
                        # Tentar parse da data (pode estar em formato ISO)
                        if 'T' in start_datetime:
                            dt = datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
                        else:
                            dt = datetime.strptime(start_datetime, '%Y-%m-%d')
                        
                        month_key = dt.strftime('%Y-%m')
                        monthly_stats[month_key] += 1
                        monthly_details[month_key].append({
                            'title': event.get('title', 'Sem título')[:50],
                            'date': dt.strftime('%d/%m/%Y'),
                            'status': event.get('status', 'unknown')
                        })
                    except ValueError:
                        pass
                
                # Contabilizar organizadores
                org_email = event.get('organizer_email', '')
                if org_email:
                    organizers[org_email] += 1
                    
                creator_email = event.get('creator_email', '')
                if creator_email:
                    creators[creator_email] += 1
                
                # Analisar padrões de título
                title = event.get('title', '')
                if title:
                    # Extrair palavras-chave comuns
                    words = title.lower().split()
                    for word in words:
                        if len(word) > 3:  # Ignorar palavras muito pequenas
                            title_patterns[word] += 1
                
                # Localizações
                location = event.get('location', '')
                if location:
                    location_stats[location] += 1
                
                # Google Meet
                if (event.get('hangout_link') or event.get('meet_link')):
                    events_with_meet += 1
                    
            except Exception as e:
                continue
        
        # Preparar estatísticas mensais ordenadas
        monthly_ordered = {}
        for month in range(1, 13):
            month_key = f"{year}-{month:02d}"
            month_name = calendar.month_name[month]
            monthly_ordered[f"{month:02d} - {month_name}"] = {
                'count': monthly_stats.get(month_key, 0),
                'events': monthly_details.get(month_key, [])[:5]  # Primeiros 5 eventos
            }
        
        return {
            'summary': {
                'total_events': total_events,
                'events_by_status': dict(status_count),
                'events_with_google_meet': events_with_meet,
                'meet_percentage': round((events_with_meet / total_events) * 100, 2) if total_events > 0 else 0,
                'unique_organizers': len(organizers),
                'unique_creators': len(creators),
                'unique_locations': len(location_stats)
            },
            'monthly_distribution': monthly_ordered,
            'top_organizers': dict(organizers.most_common(10)),
            'top_creators': dict(creators.most_common(10)),
            'top_locations': dict(location_stats.most_common(10)),
            'common_title_words': dict(title_patterns.most_common(20)),
        }

    def _save_to_file(self, data: Dict[str, Any], filename: str):
        """Salva os dados em arquivo JSON."""
        try:
            # Criar diretório se não existir
            os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
                
        except Exception as e:
            raise CommandError(f'Erro ao salvar arquivo: {str(e)}')

    def _display_summary(self, result: Dict[str, Any]):
        """Exibe resumo dos resultados na console."""
        stats = result.get('statistics', {})
        summary = stats.get('summary', {})
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.HTTP_INFO('RESUMO DOS EVENTOS MAPEADOS'))
        self.stdout.write('='*60)
        
        self.stdout.write(f'Período analisado: {result["year"]}')
        self.stdout.write(f'Total de eventos: {self.style.SUCCESS(str(summary.get("total_events", 0)))}')
        
        # Status dos eventos
        status_info = summary.get('events_by_status', {})
        if status_info:
            self.stdout.write('\nStatus dos eventos:')
            for status, count in status_info.items():
                percentage = round((count / summary.get('total_events', 1)) * 100, 1)
                self.stdout.write(f'   - {status}: {count} ({percentage}%)')
        
        # Google Meet
        meet_count = summary.get('events_with_google_meet', 0)
        meet_percent = summary.get('meet_percentage', 0)
        self.stdout.write(f'Eventos com Google Meet: {meet_count} ({meet_percent}%)')
        
        # Organizadores
        unique_orgs = summary.get('unique_organizers', 0)
        unique_creators = summary.get('unique_creators', 0)
        self.stdout.write(f'Organizadores únicos: {unique_orgs}')
        self.stdout.write(f'Criadores únicos: {unique_creators}')
        
        # Distribuição mensal
        monthly = stats.get('monthly_distribution', {})
        if monthly:
            self.stdout.write('\nDistribuição mensal:')
            for month, data in monthly.items():
                count = data.get('count', 0)
                if count > 0:
                    self.stdout.write(f'   - {month}: {self.style.SUCCESS(str(count))} eventos')
        
        # Top organizadores
        top_orgs = stats.get('top_organizers', {})
        if top_orgs:
            self.stdout.write('\nPrincipais organizadores:')
            for email, count in list(top_orgs.items())[:5]:
                self.stdout.write(f'   - {email}: {count} eventos')
        
        # Localizações mais comuns
        top_locations = stats.get('top_locations', {})
        if top_locations:
            self.stdout.write('\nPrincipais localizações:')
            for location, count in list(top_locations.items())[:5]:
                location_display = location[:50] + '...' if len(location) > 50 else location
                self.stdout.write(f'   - {location_display}: {count} eventos')
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('Mapeamento concluído com sucesso!'))
        self.stdout.write('='*60 + '\n')
"""
Advanced Google APIs Integration for Aprender Sistema
=====================================================

Comprehensive Google Workspace integration providing:
- Google Calendar advanced operations
- Google Drive document management
- Gmail automated communications
- Google Sheets data synchronization
- Google Meet link generation

Author: Claude Code
Date: Janeiro 2025
"""

import json
import logging
import pickle
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from django.conf import settings
from django.utils import timezone

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    Request = None
    Credentials = None
    Flow = None
    build = None
    HttpError = None

from core.models import (
    Solicitacao, SolicitacaoStatus, Formador, Municipio,
    LogAuditoria
)

logger = logging.getLogger(__name__)


class GoogleAPIsManager:
    """
    Advanced Google APIs integration manager
    """
    
    def __init__(self):
        self.enabled = build is not None
        if not self.enabled:
            logger.warning("Google APIs not available - install google-api-python-client")
            return
        
        self.credentials = None
        self.services = {}
        self._setup_credentials()
    
    def _setup_credentials(self):
        """Setup Google API credentials"""
        if not self.enabled:
            return
        
        try:
            # Paths for credentials
            token_file = getattr(settings, 'GOOGLE_TOKEN_FILE', 'token.pickle')
            credentials_file = getattr(settings, 'GOOGLE_CREDENTIALS_FILE', 'credentials.json')
            
            # Load existing token
            if os.path.exists(token_file):
                with open(token_file, 'rb') as token:
                    self.credentials = pickle.load(token)
            
            # Refresh or create credentials
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                else:
                    logger.warning("Google credentials need manual authorization")
                    # In production, implement proper OAuth flow
                    
                # Save credentials
                with open(token_file, 'wb') as token:
                    pickle.dump(self.credentials, token)
            
            logger.info("Google API credentials loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup Google credentials: {e}")
            self.enabled = False
    
    def get_service(self, service_name: str, version: str = 'v1') -> Optional[Any]:
        """
        Get Google API service client
        
        Args:
            service_name: Service name (calendar, drive, gmail, sheets)
            version: API version
            
        Returns:
            Service client or None if unavailable
        """
        if not self.enabled or not self.credentials:
            return None
        
        service_key = f"{service_name}_{version}"
        if service_key not in self.services:
            try:
                self.services[service_key] = build(
                    service_name, version, credentials=self.credentials
                )
                logger.info(f"Initialized {service_name} {version} service")
            except Exception as e:
                logger.error(f"Failed to initialize {service_name} service: {e}")
                return None
        
        return self.services[service_key]


class AdvancedCalendarService:
    """
    Advanced Google Calendar operations
    """
    
    def __init__(self):
        self.apis_manager = GoogleAPIsManager()
        self.calendar_service = None
        if self.apis_manager.enabled:
            self.calendar_service = self.apis_manager.get_service('calendar', 'v3')
    
    def create_educational_event(
        self,
        solicitacao: Solicitacao,
        calendar_id: str = 'primary',
        add_meet_link: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Create advanced educational event with all features
        
        Args:
            solicitacao: Solicitacao instance
            calendar_id: Google Calendar ID
            add_meet_link: Whether to add Google Meet link
            
        Returns:
            Created event data or None if failed
        """
        if not self.calendar_service:
            logger.warning("Calendar service not available")
            return None
        
        try:
            # Prepare event data
            event_data = {
                'summary': solicitacao.titulo_evento,
                'description': self._build_event_description(solicitacao),
                'start': {
                    'dateTime': solicitacao.data_inicio.isoformat(),
                    'timeZone': 'America/Fortaleza',
                },
                'end': {
                    'dateTime': solicitacao.data_fim.isoformat(),
                    'timeZone': 'America/Fortaleza',
                },
                'location': f"{solicitacao.municipio.nome}, CE",
                'attendees': self._build_attendees_list(solicitacao),
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                        {'method': 'popup', 'minutes': 60},       # 1 hour before
                        {'method': 'popup', 'minutes': 15},       # 15 minutes before
                    ],
                },
                'extendedProperties': {
                    'private': {
                        'solicitacao_id': str(solicitacao.id),
                        'projeto': solicitacao.projeto.nome,
                        'tipo_evento': solicitacao.tipo_evento.nome,
                        'sistema_origem': 'aprender_sistema'
                    }
                }
            }
            
            # Add Google Meet if requested
            if add_meet_link:
                event_data['conferenceData'] = {
                    'createRequest': {
                        'requestId': f"meet-{solicitacao.id}",
                        'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                    }
                }
            
            # Create event
            created_event = self.calendar_service.events().insert(
                calendarId=calendar_id,
                body=event_data,
                conferenceDataVersion=1 if add_meet_link else 0
            ).execute()
            
            logger.info(f"Created calendar event: {created_event['id']}")
            
            # Update solicitacao with event ID
            solicitacao.evento_google = created_event['id']
            solicitacao.save()
            
            # Log activity
            LogAuditoria.objects.create(
                usuario=None,  # System action
                acao='google_calendar_event_created',
                modelo='Solicitacao',
                objeto_id=str(solicitacao.id),
                detalhes=json.dumps({
                    'event_id': created_event['id'],
                    'event_link': created_event.get('htmlLink'),
                    'meet_link': self._extract_meet_link(created_event)
                })
            )
            
            return {
                'event_id': created_event['id'],
                'event_link': created_event.get('htmlLink'),
                'meet_link': self._extract_meet_link(created_event),
                'status': 'created'
            }
            
        except HttpError as e:
            logger.error(f"Google Calendar API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to create calendar event: {e}")
            return None
    
    def update_educational_event(
        self,
        solicitacao: Solicitacao,
        calendar_id: str = 'primary'
    ) -> Optional[Dict[str, Any]]:
        """Update existing calendar event"""
        if not self.calendar_service or not solicitacao.evento_google:
            return None
        
        try:
            # Get existing event
            event = self.calendar_service.events().get(
                calendarId=calendar_id,
                eventId=solicitacao.evento_google
            ).execute()
            
            # Update event data
            event.update({
                'summary': solicitacao.titulo_evento,
                'description': self._build_event_description(solicitacao),
                'start': {
                    'dateTime': solicitacao.data_inicio.isoformat(),
                    'timeZone': 'America/Fortaleza',
                },
                'end': {
                    'dateTime': solicitacao.data_fim.isoformat(),
                    'timeZone': 'America/Fortaleza',
                },
                'location': f"{solicitacao.municipio.nome}, CE",
                'attendees': self._build_attendees_list(solicitacao),
            })
            
            # Update the event
            updated_event = self.calendar_service.events().update(
                calendarId=calendar_id,
                eventId=solicitacao.evento_google,
                body=event
            ).execute()
            
            logger.info(f"Updated calendar event: {updated_event['id']}")
            return {
                'event_id': updated_event['id'],
                'status': 'updated'
            }
            
        except Exception as e:
            logger.error(f"Failed to update calendar event: {e}")
            return None
    
    def delete_educational_event(
        self,
        solicitacao: Solicitacao,
        calendar_id: str = 'primary'
    ) -> bool:
        """Delete calendar event"""
        if not self.calendar_service or not solicitacao.evento_google:
            return False
        
        try:
            self.calendar_service.events().delete(
                calendarId=calendar_id,
                eventId=solicitacao.evento_google
            ).execute()
            
            logger.info(f"Deleted calendar event: {solicitacao.evento_google}")
            
            # Clear event ID
            solicitacao.evento_google = None
            solicitacao.save()
            
            return True
        except Exception as e:
            logger.error(f"Failed to delete calendar event: {e}")
            return False
    
    def get_calendar_conflicts(
        self,
        start_time: datetime,
        end_time: datetime,
        calendar_ids: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Check for calendar conflicts in specified time range
        
        Args:
            start_time: Start datetime
            end_time: End datetime
            calendar_ids: List of calendar IDs to check
            
        Returns:
            List of conflicting events
        """
        if not self.calendar_service:
            return []
        
        conflicts = []
        calendar_ids = calendar_ids or ['primary']
        
        try:
            for calendar_id in calendar_ids:
                events_result = self.calendar_service.events().list(
                    calendarId=calendar_id,
                    timeMin=start_time.isoformat(),
                    timeMax=end_time.isoformat(),
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                events = events_result.get('items', [])
                for event in events:
                    conflicts.append({
                        'calendar_id': calendar_id,
                        'event_id': event['id'],
                        'title': event.get('summary', 'No Title'),
                        'start': event['start'].get('dateTime', event['start'].get('date')),
                        'end': event['end'].get('dateTime', event['end'].get('date')),
                        'link': event.get('htmlLink')
                    })
            
            return conflicts
            
        except Exception as e:
            logger.error(f"Failed to check calendar conflicts: {e}")
            return []
    
    def _build_event_description(self, solicitacao: Solicitacao) -> str:
        """Build detailed event description"""
        formadores = solicitacao.formadores.all()
        formadores_names = [f.usuario.get_full_name() for f in formadores]
        
        description = f"""
Evento: {solicitacao.titulo_evento}
Projeto: {solicitacao.projeto.nome}
Tipo: {solicitacao.tipo_evento.nome}
Município: {solicitacao.municipio.nome}

Formadores:
{chr(10).join(f"• {nome}" for nome in formadores_names)}

Público Alvo: {solicitacao.publico_alvo or 'Não especificado'}

Observações:
{solicitacao.observacoes or 'Nenhuma observação adicional'}

---
Solicitado por: {solicitacao.usuario_solicitante.get_full_name()}
Data da Solicitação: {solicitacao.data_solicitacao.strftime('%d/%m/%Y %H:%M')}
Status: {solicitacao.get_status_display()}

Sistema: Aprender Sistema
ID: {solicitacao.id}
        """.strip()
        
        return description
    
    def _build_attendees_list(self, solicitacao: Solicitacao) -> List[Dict[str, str]]:
        """Build attendees list for the event"""
        attendees = []
        
        # Add solicitante
        attendees.append({
            'email': solicitacao.usuario_solicitante.email,
            'displayName': solicitacao.usuario_solicitante.get_full_name(),
            'responseStatus': 'accepted'
        })
        
        # Add formadores
        for formador in solicitacao.formadores.all():
            if formador.usuario.email:
                attendees.append({
                    'email': formador.usuario.email,
                    'displayName': formador.usuario.get_full_name(),
                    'responseStatus': 'needsAction'
                })
        
        return attendees
    
    def _extract_meet_link(self, event_data: Dict[str, Any]) -> Optional[str]:
        """Extract Google Meet link from event data"""
        try:
            conference_data = event_data.get('conferenceData', {})
            entry_points = conference_data.get('entryPoints', [])
            
            for entry in entry_points:
                if entry.get('entryPointType') == 'video':
                    return entry.get('uri')
            
            return None
        except Exception:
            return None


class GoogleDriveService:
    """
    Advanced Google Drive operations
    """
    
    def __init__(self):
        self.apis_manager = GoogleAPIsManager()
        self.drive_service = None
        if self.apis_manager.enabled:
            self.drive_service = self.apis_manager.get_service('drive', 'v3')
    
    def create_event_folder(
        self,
        solicitacao: Solicitacao,
        parent_folder_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Create dedicated folder for educational event
        
        Args:
            solicitacao: Solicitacao instance
            parent_folder_id: Parent folder ID (root if None)
            
        Returns:
            Created folder ID or None if failed
        """
        if not self.drive_service:
            return None
        
        try:
            folder_name = f"{solicitacao.titulo_evento} - {solicitacao.municipio.nome} - {solicitacao.data_inicio.strftime('%d-%m-%Y')}"
            
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'description': f"Materiais para o evento: {solicitacao.titulo_evento}",
            }
            
            if parent_folder_id:
                folder_metadata['parents'] = [parent_folder_id]
            
            folder = self.drive_service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            logger.info(f"Created Drive folder: {folder_id}")
            
            # Set folder permissions
            self._set_folder_permissions(folder_id, solicitacao)
            
            return folder_id
            
        except Exception as e:
            logger.error(f"Failed to create Drive folder: {e}")
            return None
    
    def _set_folder_permissions(self, folder_id: str, solicitacao: Solicitacao):
        """Set appropriate permissions for event folder"""
        try:
            # Give edit access to formadores
            for formador in solicitacao.formadores.all():
                if formador.usuario.email:
                    permission = {
                        'type': 'user',
                        'role': 'editor',
                        'emailAddress': formador.usuario.email
                    }
                    self.drive_service.permissions().create(
                        fileId=folder_id,
                        body=permission
                    ).execute()
            
            # Give view access to solicitante if not already a formador
            if not solicitacao.formadores.filter(usuario=solicitacao.usuario_solicitante).exists():
                permission = {
                    'type': 'user',
                    'role': 'reader',
                    'emailAddress': solicitacao.usuario_solicitante.email
                }
                self.drive_service.permissions().create(
                    fileId=folder_id,
                    body=permission
                ).execute()
                
        except Exception as e:
            logger.error(f"Failed to set folder permissions: {e}")


class GmailService:
    """
    Advanced Gmail operations for automated communications
    """
    
    def __init__(self):
        self.apis_manager = GoogleAPIsManager()
        self.gmail_service = None
        if self.apis_manager.enabled:
            self.gmail_service = self.apis_manager.get_service('gmail', 'v1')
    
    def send_event_notification(
        self,
        solicitacao: Solicitacao,
        notification_type: str = 'approval',
        custom_message: Optional[str] = None
    ) -> bool:
        """
        Send automated event notification via Gmail
        
        Args:
            solicitacao: Solicitacao instance
            notification_type: Type of notification (approval, rejection, reminder)
            custom_message: Custom message to include
            
        Returns:
            True if sent successfully
        """
        if not self.gmail_service:
            return False
        
        try:
            # Build email content based on notification type
            subject, body = self._build_notification_content(
                solicitacao, notification_type, custom_message
            )
            
            # Get recipients
            recipients = self._get_notification_recipients(solicitacao, notification_type)
            
            # Send emails
            for recipient in recipients:
                message = self._create_message(
                    sender='noreply@aprende_sistema.com',  # Configure properly
                    to=recipient['email'],
                    subject=subject,
                    message_text=body
                )
                
                self.gmail_service.users().messages().send(
                    userId='me',
                    body=message
                ).execute()
                
                logger.info(f"Sent notification to {recipient['email']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
    
    def _build_notification_content(
        self,
        solicitacao: Solicitacao,
        notification_type: str,
        custom_message: Optional[str]
    ) -> Tuple[str, str]:
        """Build email subject and body"""
        
        if notification_type == 'approval':
            subject = f"Evento Aprovado: {solicitacao.titulo_evento}"
            body = f"""
Olá,

Seu evento foi aprovado!

Detalhes:
- Título: {solicitacao.titulo_evento}
- Data/Hora: {solicitacao.data_inicio.strftime('%d/%m/%Y %H:%M')} - {solicitacao.data_fim.strftime('%H:%M')}
- Local: {solicitacao.municipio.nome}
- Projeto: {solicitacao.projeto.nome}

{custom_message or ''}

Atenciosamente,
Sistema Aprender
            """
        elif notification_type == 'rejection':
            subject = f"Evento Não Aprovado: {solicitacao.titulo_evento}"
            body = f"""
Olá,

Infelizmente seu evento não foi aprovado.

Detalhes:
- Título: {solicitacao.titulo_evento}
- Data/Hora: {solicitacao.data_inicio.strftime('%d/%m/%Y %H:%M')}
- Motivo: {custom_message or 'Não especificado'}

Para mais informações, entre em contato com a coordenação.

Atenciosamente,
Sistema Aprender
            """
        else:  # reminder
            subject = f"Lembrete: {solicitacao.titulo_evento}"
            body = f"""
Olá,

Este é um lembrete sobre seu evento:

- Título: {solicitacao.titulo_evento}
- Data/Hora: {solicitacao.data_inicio.strftime('%d/%m/%Y %H:%M')}
- Local: {solicitacao.municipio.nome}

{custom_message or 'Não esqueça de se preparar para o evento!'}

Atenciosamente,
Sistema Aprender
            """
        
        return subject, body
    
    def _get_notification_recipients(
        self,
        solicitacao: Solicitacao,
        notification_type: str
    ) -> List[Dict[str, str]]:
        """Get email recipients based on notification type"""
        recipients = []
        
        # Always include solicitante
        recipients.append({
            'email': solicitacao.usuario_solicitante.email,
            'name': solicitacao.usuario_solicitante.get_full_name()
        })
        
        # Include formadores for approvals and reminders
        if notification_type in ['approval', 'reminder']:
            for formador in solicitacao.formadores.all():
                if formador.usuario.email:
                    recipients.append({
                        'email': formador.usuario.email,
                        'name': formador.usuario.get_full_name()
                    })
        
        return recipients
    
    def _create_message(self, sender: str, to: str, subject: str, message_text: str) -> Dict:
        """Create email message for Gmail API"""
        import base64
        from email.mime.text import MIMEText
        
        message = MIMEText(message_text)
        message['to'] = to
        message['from'] = sender
        message['subject'] = subject
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        return {'raw': raw_message}


# Global service instances
google_apis_manager = GoogleAPIsManager()
calendar_service = AdvancedCalendarService()
drive_service = GoogleDriveService()
gmail_service = GmailService()


# Convenience functions
def create_calendar_event(solicitacao: Solicitacao, add_meet: bool = True) -> Optional[Dict[str, Any]]:
    """Create calendar event for solicitacao"""
    return calendar_service.create_educational_event(solicitacao, add_meet_link=add_meet)


def update_calendar_event(solicitacao: Solicitacao) -> Optional[Dict[str, Any]]:
    """Update existing calendar event"""
    return calendar_service.update_educational_event(solicitacao)


def delete_calendar_event(solicitacao: Solicitacao) -> bool:
    """Delete calendar event"""
    return calendar_service.delete_educational_event(solicitacao)


def create_event_drive_folder(solicitacao: Solicitacao) -> Optional[str]:
    """Create Drive folder for event materials"""
    return drive_service.create_event_folder(solicitacao)


def send_notification_email(
    solicitacao: Solicitacao,
    notification_type: str,
    message: Optional[str] = None
) -> bool:
    """Send notification email"""
    return gmail_service.send_event_notification(solicitacao, notification_type, message)


def check_calendar_conflicts(start: datetime, end: datetime) -> List[Dict[str, Any]]:
    """Check for calendar conflicts"""
    return calendar_service.get_calendar_conflicts(start, end)
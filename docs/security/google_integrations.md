# 🔗 Google Integrations Security - Sistema Aprender

This document provides comprehensive security guidelines for Google API integrations in the Sistema Aprender project, covering Google Calendar, Google Sheets, and OAuth 2.0 implementations.

## 📋 Overview

### Google Services Used
- **Google Calendar API**: Event creation and synchronization
- **Google Sheets API**: Data import and export (optional)
- **Google OAuth 2.0**: User authentication and authorization
- **Google Drive API**: File storage and sharing (future)

### Security Scope
- OAuth 2.0 flow security
- API key and credential management
- Token handling and refresh
- Scope limitation and principle of least privilege
- Data privacy and LGPD compliance

---

## 🔐 OAuth 2.0 Security Implementation

### 1. Google Cloud Console Setup

#### Project Configuration
```bash
# 1. Create Google Cloud Project
# Go to: https://console.cloud.google.com/
# Create new project: "sistema-aprender-prod"

# 2. Enable Required APIs
# - Google Calendar API
# - Google Sheets API (if needed)
# - Google Drive API (if needed)

# 3. Configure OAuth Consent Screen
# - Application name: "Sistema Aprender"
# - User support email: support@yourdomain.com
# - Developer contact: dev@yourdomain.com
# - Scopes: Only necessary scopes
# - Test users: Limited to development team
```

#### OAuth Client Creation
```json
{
  "client_id": "123456789-abcdef.apps.googleusercontent.com",
  "client_secret": "GOCSPX-your-client-secret-here",
  "redirect_uris": [
    "https://yourdomain.com/auth/google/callback",
    "https://staging.yourdomain.com/auth/google/callback",
    "http://localhost:8000/auth/google/callback"
  ],
  "javascript_origins": [
    "https://yourdomain.com",
    "https://staging.yourdomain.com",
    "http://localhost:8000"
  ]
}
```

### 2. Secure OAuth Flow Implementation

#### OAuth Service Class
```python
# core/services/google_oauth.py
import json
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode
import requests
from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
import logging

logger = logging.getLogger('security.google_oauth')

class GoogleOAuthService:
    """Secure Google OAuth 2.0 implementation"""
    
    SCOPES = [
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile',
        # Add only necessary scopes
    ]
    
    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
        
        if not all([self.client_id, self.client_secret, self.redirect_uri]):
            raise ValueError("Missing Google OAuth configuration")
    
    def get_authorization_url(self, user_id=None):
        """Generate secure authorization URL with CSRF protection"""
        
        # Generate CSRF token
        state_token = secrets.token_urlsafe(32)
        
        # Store state token with expiration
        cache_key = f"oauth_state:{state_token}"
        cache.set(cache_key, {
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
        }, timeout=600)  # 10 minutes
        
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(self.SCOPES),
            'response_type': 'code',
            'access_type': 'offline',  # Get refresh token
            'prompt': 'consent',       # Force consent screen
            'state': state_token,      # CSRF protection
        }
        
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
        
        logger.info(f"OAuth authorization URL generated for user {user_id}")
        return auth_url
    
    def handle_callback(self, code, state, request_ip=None):
        """Securely handle OAuth callback with validation"""
        
        # Validate state token (CSRF protection)
        cache_key = f"oauth_state:{state}"
        state_data = cache.get(cache_key)
        
        if not state_data:
            logger.warning(f"Invalid or expired OAuth state token: {state} from {request_ip}")
            raise ValueError("Invalid or expired state token")
        
        # Remove used state token
        cache.delete(cache_key)
        
        # Exchange code for tokens
        token_data = self._exchange_code_for_tokens(code)
        
        # Validate tokens
        self._validate_tokens(token_data)
        
        # Get user info
        user_info = self._get_user_info(token_data['access_token'])
        
        # Store tokens securely
        self._store_tokens(user_info['id'], token_data)
        
        logger.info(f"OAuth callback successful for user {user_info['email']} from {request_ip}")
        
        return user_info, token_data
    
    def _exchange_code_for_tokens(self, code):
        """Exchange authorization code for access and refresh tokens"""
        
        token_url = "https://oauth2.googleapis.com/token"
        
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri,
        }
        
        try:
            response = requests.post(
                token_url, 
                data=data, 
                timeout=30,
                headers={'User-Agent': 'Sistema-Aprender/1.0'}
            )
            response.raise_for_status()
            
            token_data = response.json()
            
            if 'error' in token_data:
                logger.error(f"OAuth token exchange error: {token_data}")
                raise ValueError(f"Token exchange failed: {token_data['error']}")
            
            return token_data
            
        except requests.RequestException as e:
            logger.error(f"OAuth token exchange request failed: {str(e)}")
            raise ValueError("Token exchange request failed")
    
    def _validate_tokens(self, token_data):
        """Validate received tokens"""
        required_fields = ['access_token', 'token_type']
        
        for field in required_fields:
            if field not in token_data:
                raise ValueError(f"Missing required token field: {field}")
        
        if token_data['token_type'].lower() != 'bearer':
            raise ValueError("Invalid token type")
        
        # Validate token format (basic check)
        access_token = token_data['access_token']
        if not access_token or len(access_token) < 50:
            raise ValueError("Invalid access token format")
    
    def _get_user_info(self, access_token):
        """Get user information using access token"""
        
        userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'User-Agent': 'Sistema-Aprender/1.0'
        }
        
        try:
            response = requests.get(userinfo_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            user_info = response.json()
            
            # Validate required user info
            required_fields = ['id', 'email', 'verified_email']
            for field in required_fields:
                if field not in user_info:
                    raise ValueError(f"Missing user info field: {field}")
            
            if not user_info['verified_email']:
                raise ValueError("Email not verified")
            
            return user_info
            
        except requests.RequestException as e:
            logger.error(f"User info request failed: {str(e)}")
            raise ValueError("Failed to get user information")
    
    def _store_tokens(self, user_id, token_data):
        """Securely store OAuth tokens"""
        from core.models import GoogleOAuthToken
        
        # Calculate expiration
        expires_in = token_data.get('expires_in', 3600)
        expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        # Store or update tokens
        GoogleOAuthToken.objects.update_or_create(
            user_id=user_id,
            defaults={
                'access_token': self._encrypt_token(token_data['access_token']),
                'refresh_token': self._encrypt_token(token_data.get('refresh_token')),
                'expires_at': expires_at,
                'scope': token_data.get('scope', ' '.join(self.SCOPES)),
            }
        )
    
    def _encrypt_token(self, token):
        """Encrypt token for storage (implement based on your encryption strategy)"""
        # Use your encryption service
        from core.utils.encryption import encrypt_data
        return encrypt_data(token) if token else None
    
    def refresh_access_token(self, user_id):
        """Refresh expired access token"""
        from core.models import GoogleOAuthToken
        
        try:
            oauth_token = GoogleOAuthToken.objects.get(user_id=user_id)
            
            if not oauth_token.refresh_token:
                raise ValueError("No refresh token available")
            
            refresh_token = self._decrypt_token(oauth_token.refresh_token)
            
            token_url = "https://oauth2.googleapis.com/token"
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token',
            }
            
            response = requests.post(token_url, data=data, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            
            if 'error' in token_data:
                logger.error(f"Token refresh error: {token_data}")
                raise ValueError("Token refresh failed")
            
            # Update stored tokens
            oauth_token.access_token = self._encrypt_token(token_data['access_token'])
            oauth_token.expires_at = datetime.now() + timedelta(
                seconds=token_data.get('expires_in', 3600)
            )
            oauth_token.save()
            
            logger.info(f"Access token refreshed for user {user_id}")
            return token_data['access_token']
            
        except GoogleOAuthToken.DoesNotExist:
            logger.error(f"No OAuth token found for user {user_id}")
            raise ValueError("No OAuth token found")
    
    def _decrypt_token(self, encrypted_token):
        """Decrypt stored token"""
        from core.utils.encryption import decrypt_data
        return decrypt_data(encrypted_token) if encrypted_token else None
```

### 3. Token Storage Model

#### Secure Token Model
```python
# core/models.py (addition)
from django.db import models
from django.utils import timezone
from datetime import timedelta

class GoogleOAuthToken(models.Model):
    """Secure storage for Google OAuth tokens"""
    
    user_id = models.CharField(max_length=100, unique=True, db_index=True)
    access_token = models.TextField()  # Encrypted
    refresh_token = models.TextField(null=True, blank=True)  # Encrypted
    expires_at = models.DateTimeField()
    scope = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'google_oauth_tokens'
        verbose_name = 'Google OAuth Token'
        verbose_name_plural = 'Google OAuth Tokens'
    
    def is_expired(self):
        """Check if access token is expired"""
        return timezone.now() >= self.expires_at
    
    def expires_soon(self, minutes=5):
        """Check if token expires soon"""
        return timezone.now() >= (self.expires_at - timedelta(minutes=minutes))
    
    def __str__(self):
        return f"OAuth Token for {self.user_id}"
```

---

## 📅 Google Calendar API Security

### 1. Secure Calendar Service

#### Calendar Service Implementation
```python
# core/services/google_calendar.py
import logging
from datetime import datetime, timezone
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from django.conf import settings
from core.services.google_oauth import GoogleOAuthService

logger = logging.getLogger('security.google_calendar')

class GoogleCalendarService:
    """Secure Google Calendar API integration"""
    
    def __init__(self, user_id):
        self.user_id = user_id
        self.oauth_service = GoogleOAuthService()
        self._service = None
    
    def _get_service(self):
        """Get authenticated Calendar service"""
        if self._service is None:
            credentials = self._get_credentials()
            self._service = build('calendar', 'v3', credentials=credentials)
        return self._service
    
    def _get_credentials(self):
        """Get valid credentials for API calls"""
        from core.models import GoogleOAuthToken
        
        try:
            oauth_token = GoogleOAuthToken.objects.get(user_id=self.user_id)
            
            # Check if token needs refresh
            if oauth_token.is_expired() or oauth_token.expires_soon():
                access_token = self.oauth_service.refresh_access_token(self.user_id)
            else:
                access_token = self.oauth_service._decrypt_token(oauth_token.access_token)
            
            # Create credentials object
            credentials = Credentials(
                token=access_token,
                refresh_token=self.oauth_service._decrypt_token(oauth_token.refresh_token),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                scopes=oauth_token.scope.split(' ')
            )
            
            return credentials
            
        except GoogleOAuthToken.DoesNotExist:
            logger.error(f"No OAuth token found for user {self.user_id}")
            raise ValueError("User not authenticated with Google")
    
    def create_event(self, event_data, calendar_id='primary'):
        """Create calendar event with security validation"""
        
        # Validate input data
        self._validate_event_data(event_data)
        
        try:
            service = self._get_service()
            
            # Sanitize event data
            sanitized_event = self._sanitize_event_data(event_data)
            
            # Create event
            event = service.events().insert(
                calendarId=calendar_id,
                body=sanitized_event,
                conferenceDataVersion=1  # Enable Google Meet
            ).execute()
            
            logger.info(f"Event created: {event['id']} for user {self.user_id}")
            
            return {
                'id': event['id'],
                'html_link': event['htmlLink'],
                'meet_link': event.get('conferenceData', {}).get('entryPoints', [{}])[0].get('uri'),
                'status': event['status']
            }
            
        except HttpError as e:
            logger.error(f"Calendar API error: {e}")
            if e.resp.status == 403:
                raise ValueError("Insufficient permissions for calendar access")
            elif e.resp.status == 404:
                raise ValueError("Calendar not found")
            else:
                raise ValueError(f"Calendar API error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error creating event: {str(e)}")
            raise ValueError("Failed to create calendar event")
    
    def _validate_event_data(self, event_data):
        """Validate event data before API call"""
        required_fields = ['summary', 'start', 'end']
        
        for field in required_fields:
            if field not in event_data:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate datetime formats
        for datetime_field in ['start', 'end']:
            if 'dateTime' in event_data[datetime_field]:
                try:
                    datetime.fromisoformat(
                        event_data[datetime_field]['dateTime'].replace('Z', '+00:00')
                    )
                except ValueError:
                    raise ValueError(f"Invalid datetime format in {datetime_field}")
        
        # Validate summary length and content
        summary = event_data['summary']
        if len(summary) > 1024:
            raise ValueError("Event summary too long")
        
        # Basic XSS protection
        if any(char in summary for char in ['<', '>', '"', "'"]):
            event_data['summary'] = self._sanitize_text(summary)
    
    def _sanitize_event_data(self, event_data):
        """Sanitize event data for security"""
        import html
        
        sanitized = event_data.copy()
        
        # Sanitize text fields
        text_fields = ['summary', 'description', 'location']
        for field in text_fields:
            if field in sanitized:
                sanitized[field] = html.escape(sanitized[field])
        
        # Ensure attendees are validated email addresses
        if 'attendees' in sanitized:
            sanitized['attendees'] = self._validate_attendees(sanitized['attendees'])
        
        # Add conference data for Google Meet
        if 'conferenceData' not in sanitized:
            sanitized['conferenceData'] = {
                'createRequest': {
                    'requestId': f"meet-{datetime.now().isoformat()}",
                    'conferenceSolutionKey': {
                        'type': 'hangoutsMeet'
                    }
                }
            }
        
        return sanitized
    
    def _validate_attendees(self, attendees):
        """Validate attendee email addresses"""
        import re
        
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        validated_attendees = []
        
        for attendee in attendees:
            email = attendee.get('email', '')
            if email_pattern.match(email):
                validated_attendees.append(attendee)
            else:
                logger.warning(f"Invalid attendee email: {email}")
        
        return validated_attendees
    
    def _sanitize_text(self, text):
        """Sanitize text content"""
        import html
        import re
        
        # HTML escape
        text = html.escape(text)
        
        # Remove potentially dangerous characters
        text = re.sub(r'[<>"\']', '', text)
        
        return text
    
    def get_event(self, event_id, calendar_id='primary'):
        """Get calendar event with access control"""
        
        try:
            service = self._get_service()
            
            event = service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            # Only return safe fields
            safe_event = {
                'id': event['id'],
                'summary': event.get('summary', ''),
                'start': event.get('start', {}),
                'end': event.get('end', {}),
                'status': event.get('status', ''),
                'html_link': event.get('htmlLink', ''),
                'meet_link': self._extract_meet_link(event),
            }
            
            logger.info(f"Event retrieved: {event_id} for user {self.user_id}")
            return safe_event
            
        except HttpError as e:
            if e.resp.status == 404:
                return None
            logger.error(f"Error retrieving event {event_id}: {e}")
            raise ValueError("Failed to retrieve event")
    
    def _extract_meet_link(self, event):
        """Safely extract Google Meet link from event"""
        conference_data = event.get('conferenceData', {})
        entry_points = conference_data.get('entryPoints', [])
        
        for entry_point in entry_points:
            if entry_point.get('entryPointType') == 'video':
                return entry_point.get('uri')
        
        return None
    
    def delete_event(self, event_id, calendar_id='primary'):
        """Delete calendar event with proper authorization"""
        
        try:
            service = self._get_service()
            
            # Verify event exists and user has access
            existing_event = self.get_event(event_id, calendar_id)
            if not existing_event:
                raise ValueError("Event not found or access denied")
            
            # Delete event
            service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            logger.info(f"Event deleted: {event_id} by user {self.user_id}")
            return True
            
        except HttpError as e:
            if e.resp.status == 410:  # Event already deleted
                return True
            logger.error(f"Error deleting event {event_id}: {e}")
            raise ValueError("Failed to delete event")
```

---

## 📊 Google Sheets API Security

### 1. Secure Sheets Integration

#### Sheets Service Implementation
```python
# core/services/google_sheets.py
import logging
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from django.conf import settings
from core.services.google_oauth import GoogleOAuthService

logger = logging.getLogger('security.google_sheets')

class GoogleSheetsService:
    """Secure Google Sheets API integration"""
    
    def __init__(self, user_id):
        self.user_id = user_id
        self.oauth_service = GoogleOAuthService()
        self._service = None
    
    def _get_service(self):
        """Get authenticated Sheets service"""
        if self._service is None:
            credentials = self._get_credentials()
            self._service = build('sheets', 'v4', credentials=credentials)
        return self._service
    
    def _get_credentials(self):
        """Get valid credentials (similar to CalendarService)"""
        # Implementation similar to GoogleCalendarService._get_credentials()
        pass
    
    def read_sheet_data(self, spreadsheet_id, range_name):
        """Read data from Google Sheet with security validation"""
        
        # Validate inputs
        self._validate_spreadsheet_access(spreadsheet_id)
        self._validate_range(range_name)
        
        try:
            service = self._get_service()
            
            # Read data
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueRenderOption='UNFORMATTED_VALUE',  # Prevent formula execution
                dateTimeRenderOption='FORMATTED_STRING'
            ).execute()
            
            values = result.get('values', [])
            
            # Sanitize data
            sanitized_values = self._sanitize_sheet_data(values)
            
            logger.info(f"Sheet data read: {spreadsheet_id} range {range_name} by user {self.user_id}")
            
            return sanitized_values
            
        except HttpError as e:
            if e.resp.status == 403:
                logger.warning(f"Access denied to spreadsheet {spreadsheet_id} for user {self.user_id}")
                raise ValueError("Access denied to spreadsheet")
            logger.error(f"Sheets API error: {e}")
            raise ValueError("Failed to read sheet data")
    
    def _validate_spreadsheet_access(self, spreadsheet_id):
        """Validate spreadsheet ID and access permissions"""
        import re
        
        # Basic format validation
        if not re.match(r'^[a-zA-Z0-9-_]{44}$', spreadsheet_id):
            raise ValueError("Invalid spreadsheet ID format")
        
        # Check against whitelist (if configured)
        allowed_spreadsheets = getattr(settings, 'GOOGLE_SHEETS_WHITELIST', [])
        if allowed_spreadsheets and spreadsheet_id not in allowed_spreadsheets:
            logger.warning(f"Unauthorized spreadsheet access attempt: {spreadsheet_id}")
            raise ValueError("Spreadsheet not in allowed list")
    
    def _validate_range(self, range_name):
        """Validate range specification"""
        import re
        
        # Allow only safe range formats: Sheet1!A1:Z100
        range_pattern = r'^[a-zA-Z0-9_\s]+![A-Z]+[0-9]*:[A-Z]+[0-9]*$'
        
        if not re.match(range_pattern, range_name):
            raise ValueError("Invalid range format")
        
        # Prevent extremely large ranges (DoS protection)
        if ':' in range_name:
            start, end = range_name.split('!')[-1].split(':')
            if self._calculate_range_size(start, end) > 10000:  # Max 10k cells
                raise ValueError("Range too large")
    
    def _calculate_range_size(self, start, end):
        """Calculate approximate range size for DoS protection"""
        import re
        
        def parse_cell(cell):
            match = re.match(r'^([A-Z]+)([0-9]*)$', cell)
            if not match:
                return 1, 1
            
            col = match.group(1)
            row = int(match.group(2)) if match.group(2) else 1
            
            # Convert column letters to number
            col_num = 0
            for char in col:
                col_num = col_num * 26 + (ord(char) - ord('A') + 1)
            
            return col_num, row
        
        start_col, start_row = parse_cell(start)
        end_col, end_row = parse_cell(end)
        
        return (end_col - start_col + 1) * (end_row - start_row + 1)
    
    def _sanitize_sheet_data(self, values):
        """Sanitize data from Google Sheets"""
        import html
        
        sanitized = []
        
        for row in values:
            sanitized_row = []
            for cell in row:
                if isinstance(cell, str):
                    # HTML escape and remove potentially dangerous content
                    cell = html.escape(cell)
                    # Remove Excel/Sheets formulas
                    if cell.startswith('='):
                        cell = cell[1:]  # Remove formula prefix
                    # Limit cell content length
                    if len(cell) > 1000:
                        cell = cell[:1000] + "..."
                
                sanitized_row.append(cell)
            sanitized.append(sanitized_row)
        
        return sanitized
```

---

## 🔒 Access Control & Permissions

### 1. Scope Management

#### Minimal Scope Configuration
```python
# core/services/google_auth_scopes.py
class GoogleScopes:
    """Centralized Google API scope management"""
    
    # Calendar scopes
    CALENDAR_READONLY = 'https://www.googleapis.com/auth/calendar.readonly'
    CALENDAR_EVENTS = 'https://www.googleapis.com/auth/calendar.events'
    CALENDAR_FULL = 'https://www.googleapis.com/auth/calendar'
    
    # Sheets scopes
    SHEETS_READONLY = 'https://www.googleapis.com/auth/spreadsheets.readonly'
    SHEETS_WRITE = 'https://www.googleapis.com/auth/spreadsheets'
    
    # User info scopes
    USERINFO_EMAIL = 'https://www.googleapis.com/auth/userinfo.email'
    USERINFO_PROFILE = 'https://www.googleapis.com/auth/userinfo.profile'
    
    @classmethod
    def get_required_scopes(cls, user_role):
        """Get minimal required scopes based on user role"""
        
        base_scopes = [
            cls.USERINFO_EMAIL,
            cls.USERINFO_PROFILE,
        ]
        
        if user_role in ['superintendencia', 'controle']:
            # Full calendar access for event creation
            return base_scopes + [
                cls.CALENDAR_EVENTS,
                cls.SHEETS_READONLY,  # Only read access to sheets
            ]
        elif user_role == 'coordenador':
            # Limited calendar access
            return base_scopes + [
                cls.CALENDAR_READONLY,
            ]
        elif user_role == 'formador':
            # Read-only calendar access
            return base_scopes + [
                cls.CALENDAR_READONLY,
            ]
        
        return base_scopes
    
    @classmethod
    def validate_scopes(cls, requested_scopes, user_role):
        """Validate that requested scopes don't exceed user permissions"""
        allowed_scopes = set(cls.get_required_scopes(user_role))
        requested_scopes = set(requested_scopes)
        
        if not requested_scopes.issubset(allowed_scopes):
            excess_scopes = requested_scopes - allowed_scopes
            raise ValueError(f"Requested scopes exceed permissions: {excess_scopes}")
        
        return True
```

### 2. Role-Based API Access

#### API Access Control
```python
# core/decorators/google_api_auth.py
from functools import wraps
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from core.models import Usuario

def require_google_auth(required_role=None):
    """Decorator to ensure user has Google authentication and proper role"""
    
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped_view(request, *args, **kwargs):
            try:
                usuario = Usuario.objects.get(username=request.user.username)
                
                # Check role if specified
                if required_role and usuario.grupo != required_role:
                    return JsonResponse({
                        'error': 'Insufficient permissions for this operation'
                    }, status=403)
                
                # Check Google authentication
                from core.models import GoogleOAuthToken
                try:
                    oauth_token = GoogleOAuthToken.objects.get(user_id=str(usuario.id))
                    if oauth_token.is_expired():
                        return JsonResponse({
                            'error': 'Google authentication expired',
                            'action': 'reauth_required'
                        }, status=401)
                        
                except GoogleOAuthToken.DoesNotExist:
                    return JsonResponse({
                        'error': 'Google authentication required',
                        'action': 'auth_required'
                    }, status=401)
                
                # Add user context to request
                request.usuario = usuario
                request.oauth_token = oauth_token
                
                return view_func(request, *args, **kwargs)
                
            except Usuario.DoesNotExist:
                return JsonResponse({'error': 'User profile not found'}, status=404)
            except Exception as e:
                logger.error(f"Google auth decorator error: {str(e)}")
                return JsonResponse({'error': 'Authentication error'}, status=500)
        
        return wrapped_view
    
    return decorator

# Usage in views
@require_google_auth(required_role='superintendencia')
def create_calendar_event(request):
    # Only superintendencia can create events
    pass

@require_google_auth()
def view_calendar_events(request):
    # Any authenticated user can view (subject to their scope)
    pass
```

---

## 🛡️ Security Monitoring

### 1. API Usage Monitoring

#### Google API Audit Log
```python
# core/models.py (addition)
class GoogleAPIAuditLog(models.Model):
    """Audit log for Google API usage"""
    
    API_SERVICES = [
        ('calendar', 'Google Calendar'),
        ('sheets', 'Google Sheets'),
        ('oauth', 'Google OAuth'),
    ]
    
    OPERATIONS = [
        ('create', 'Create'),
        ('read', 'Read'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('auth', 'Authentication'),
    ]
    
    user_id = models.CharField(max_length=100, db_index=True)
    service = models.CharField(max_length=20, choices=API_SERVICES, db_index=True)
    operation = models.CharField(max_length=20, choices=OPERATIONS, db_index=True)
    resource_id = models.CharField(max_length=200, null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(null=True, blank=True)
    success = models.BooleanField(default=True, db_index=True)
    error_message = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'google_api_audit_log'
        indexes = [
            models.Index(fields=['user_id', 'timestamp']),
            models.Index(fields=['service', 'timestamp']),
            models.Index(fields=['success', 'timestamp']),
        ]

# Audit logging utility
def log_google_api_usage(user_id, service, operation, resource_id=None, 
                        ip_address=None, user_agent=None, success=True, 
                        error_message=None):
    """Log Google API usage for security audit"""
    
    GoogleAPIAuditLog.objects.create(
        user_id=user_id,
        service=service,
        operation=operation,
        resource_id=resource_id,
        ip_address=ip_address or '0.0.0.0',
        user_agent=user_agent,
        success=success,
        error_message=error_message,
    )
```

### 2. Anomaly Detection

#### Suspicious Activity Detection
```python
# core/services/google_api_security.py
import logging
from datetime import datetime, timedelta
from django.core.cache import cache
from django.conf import settings
from core.models import GoogleAPIAuditLog

logger = logging.getLogger('security.google_api')

class GoogleAPISecurityMonitor:
    """Monitor Google API usage for suspicious patterns"""
    
    def __init__(self):
        self.rate_limits = {
            'calendar_create': 10,  # Max events per hour
            'sheets_read': 100,     # Max reads per hour
            'oauth_attempts': 5,    # Max auth attempts per hour
        }
    
    def check_rate_limit(self, user_id, operation, limit_per_hour=None):
        """Check if user exceeds rate limits"""
        
        if limit_per_hour is None:
            limit_per_hour = self.rate_limits.get(operation, 60)
        
        cache_key = f"api_rate_limit:{user_id}:{operation}"
        
        # Get current count
        current_count = cache.get(cache_key, 0)
        
        if current_count >= limit_per_hour:
            logger.warning(f"Rate limit exceeded: {user_id} - {operation} ({current_count})")
            return False
        
        # Increment counter (expires in 1 hour)
        cache.set(cache_key, current_count + 1, timeout=3600)
        return True
    
    def detect_suspicious_patterns(self, user_id):
        """Detect suspicious API usage patterns"""
        
        suspicious_indicators = []
        
        # Check for too many failures
        recent_failures = GoogleAPIAuditLog.objects.filter(
            user_id=user_id,
            success=False,
            timestamp__gte=datetime.now() - timedelta(hours=1)
        ).count()
        
        if recent_failures > 10:
            suspicious_indicators.append(f"High failure rate: {recent_failures} in 1 hour")
        
        # Check for unusual access patterns
        recent_services = GoogleAPIAuditLog.objects.filter(
            user_id=user_id,
            timestamp__gte=datetime.now() - timedelta(minutes=10)
        ).values('service').distinct()
        
        if len(recent_services) > 3:
            suspicious_indicators.append("Rapid service switching")
        
        # Check for off-hours access
        current_hour = datetime.now().hour
        if current_hour < 6 or current_hour > 22:
            recent_activity = GoogleAPIAuditLog.objects.filter(
                user_id=user_id,
                timestamp__gte=datetime.now() - timedelta(minutes=30)
            ).count()
            
            if recent_activity > 5:
                suspicious_indicators.append("High off-hours activity")
        
        if suspicious_indicators:
            self.alert_suspicious_activity(user_id, suspicious_indicators)
        
        return suspicious_indicators
    
    def alert_suspicious_activity(self, user_id, indicators):
        """Alert security team of suspicious activity"""
        
        logger.critical(f"Suspicious Google API activity detected for user {user_id}: {indicators}")
        
        # Send alert email, Slack notification, etc.
        # Implementation depends on your alerting system
        pass
    
    def block_user_api_access(self, user_id, duration_hours=24):
        """Temporarily block user's API access"""
        
        cache_key = f"api_blocked:{user_id}"
        cache.set(cache_key, True, timeout=duration_hours * 3600)
        
        logger.warning(f"User {user_id} API access blocked for {duration_hours} hours")
    
    def is_user_blocked(self, user_id):
        """Check if user's API access is blocked"""
        
        cache_key = f"api_blocked:{user_id}"
        return cache.get(cache_key, False)
```

---

## 🔐 Data Privacy & LGPD Compliance

### 1. Data Minimization

#### Privacy-Aware Data Handling
```python
# core/services/google_privacy.py
import logging
from datetime import datetime, timedelta
from core.models import GoogleAPIAuditLog

logger = logging.getLogger('privacy.google_api')

class GoogleAPIPrivacyManager:
    """Manage privacy aspects of Google API integrations"""
    
    def __init__(self):
        self.data_retention_days = 90  # LGPD compliance
    
    def anonymize_calendar_data(self, event_data):
        """Anonymize calendar event data for privacy"""
        
        anonymized = event_data.copy()
        
        # Remove or hash personal identifiers
        if 'attendees' in anonymized:
            anonymized['attendees'] = self._anonymize_attendees(anonymized['attendees'])
        
        # Sanitize description
        if 'description' in anonymized:
            anonymized['description'] = self._sanitize_description(anonymized['description'])
        
        # Remove location if contains personal info
        if 'location' in anonymized:
            anonymized['location'] = self._sanitize_location(anonymized['location'])
        
        return anonymized
    
    def _anonymize_attendees(self, attendees):
        """Anonymize attendee information"""
        import hashlib
        
        anonymized_attendees = []
        
        for attendee in attendees:
            email = attendee.get('email', '')
            
            # Hash email for anonymization
            hashed_email = hashlib.sha256(email.encode()).hexdigest()[:8]
            
            anonymized_attendees.append({
                'email': f"user_{hashed_email}@anonymized.local",
                'responseStatus': attendee.get('responseStatus', 'needsAction')
            })
        
        return anonymized_attendees
    
    def cleanup_expired_data(self):
        """Clean up expired API audit logs per LGPD"""
        
        cutoff_date = datetime.now() - timedelta(days=self.data_retention_days)
        
        deleted_count = GoogleAPIAuditLog.objects.filter(
            timestamp__lt=cutoff_date
        ).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} expired API audit logs")
        
        return deleted_count
    
    def export_user_data(self, user_id):
        """Export user's Google API data for LGPD compliance"""
        
        # Get user's API audit logs
        audit_logs = GoogleAPIAuditLog.objects.filter(
            user_id=user_id
        ).values()
        
        # Get OAuth tokens (without sensitive data)
        from core.models import GoogleOAuthToken
        try:
            oauth_token = GoogleOAuthToken.objects.get(user_id=user_id)
            token_data = {
                'created_at': oauth_token.created_at.isoformat(),
                'updated_at': oauth_token.updated_at.isoformat(),
                'expires_at': oauth_token.expires_at.isoformat(),
                'scope': oauth_token.scope,
            }
        except GoogleOAuthToken.DoesNotExist:
            token_data = None
        
        export_data = {
            'user_id': user_id,
            'export_timestamp': datetime.now().isoformat(),
            'oauth_token': token_data,
            'api_audit_logs': list(audit_logs),
        }
        
        return export_data
    
    def delete_user_data(self, user_id):
        """Delete all user's Google API data for LGPD compliance"""
        
        # Delete OAuth tokens
        from core.models import GoogleOAuthToken
        GoogleOAuthToken.objects.filter(user_id=user_id).delete()
        
        # Delete audit logs
        deleted_logs = GoogleAPIAuditLog.objects.filter(user_id=user_id).delete()[0]
        
        logger.info(f"Deleted all Google API data for user {user_id}: {deleted_logs} audit logs")
        
        return {
            'user_id': user_id,
            'deletion_timestamp': datetime.now().isoformat(),
            'deleted_audit_logs': deleted_logs,
            'oauth_tokens_deleted': True,
        }
```

---

## 📚 Best Practices Summary

### ✅ Security Best Practices

#### Authentication & Authorization
- **Use OAuth 2.0 flow** with PKCE for enhanced security
- **Implement CSRF protection** with state parameter
- **Store tokens encrypted** in database
- **Use minimal scopes** based on user roles
- **Refresh tokens proactively** before expiration
- **Validate all API responses** before processing

#### API Security
- **Rate limit API calls** to prevent abuse
- **Sanitize all input data** before API calls
- **Validate API responses** for expected format
- **Log all API operations** for audit trail
- **Monitor for suspicious patterns**
- **Implement circuit breakers** for API failures

#### Data Protection
- **Encrypt sensitive data** at rest and in transit
- **Minimize data collection** to necessary information only
- **Implement data retention policies**
- **Provide data export** capabilities (LGPD)
- **Support data deletion** requests
- **Anonymize logs** where possible

### ❌ Security Anti-Patterns

#### Never Do These
- **Store tokens in plain text**
- **Use overly broad API scopes**
- **Skip input validation**
- **Ignore API rate limits**
- **Log sensitive data**
- **Share credentials between environments**
- **Use hardcoded client secrets**
- **Skip error handling**
- **Ignore security updates**
- **Allow unrestricted API access**

---

## 🚨 Incident Response

### Google API Security Incidents

#### Token Compromise
1. **Immediately revoke** all tokens for affected user
2. **Block API access** temporarily
3. **Force re-authentication** with new tokens
4. **Review audit logs** for unauthorized activity
5. **Update security measures** if needed

#### API Abuse Detection
1. **Rate limit** or block abusive user
2. **Analyze attack patterns**
3. **Update detection rules**
4. **Report to Google** if severe abuse
5. **Document lessons learned**

#### Data Breach Response
1. **Assess scope** of compromised data
2. **Notify affected users** within 72 hours (LGPD)
3. **Revoke compromised credentials**
4. **Implement additional security controls**
5. **Update privacy policies** if needed

---

## 📞 Emergency Contacts

### Google API Issues
- **Google Cloud Support**: [Google Cloud Console](https://console.cloud.google.com/support)
- **Google Calendar API Support**: [Google Workspace Support](https://support.google.com/a/answer/1047213)

### Internal Security Team
- **Security Lead**: security@yourdomain.com
- **Privacy Officer**: privacy@yourdomain.com
- **DevOps Team**: devops@yourdomain.com

---

*Google integrations security guide created during repository cleanup - Phase 4*  
*Date: 2025-09-11*  
*Version: 1.0*
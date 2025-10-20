# 🔐 SEGURANÇA COMPLETA - SISTEMA APRENDER

**Versão**: 2.0.0 Unificada
**Data**: 30 de Setembro de 2025
**Status**: ✅ Segurança Consolidada

---

## 📑 ÍNDICE

1. [Resumo Executivo](#resumo-executivo)
2. [Google Integrations Security](#google-integrations-security)
3. [Secret Management](#secret-management)
4. [Secret Scanning & Detection](#secret-scanning--detection)
5. [Best Practices](#best-practices)
6. [Incident Response](#incident-response)

---

## 🎯 RESUMO EXECUTIVO

Este documento consolida todos os guias de segurança do Sistema Aprender.

### Status Geral: ✅ **SEGURANÇA CONSOLIDADA**

### Principais Características:
- ✅ **Google Integrations Security** completo
- ✅ **Secret Management** abrangente
- ✅ **Secret Scanning** implementado
- ✅ **Best Practices** definidas
- ✅ **Incident Response** estruturado

---

## 🔗 GOOGLE INTEGRATIONS SECURITY

### Overview

#### Google Services Used
- **Google Calendar API**: Event creation and synchronization
- **Google Sheets API**: Data import and export (optional)
- **Google OAuth 2.0**: User authentication and authorization
- **Google Drive API**: File storage and sharing (future)

#### Security Scope
- OAuth 2.0 flow security
- API key and credential management
- Token handling and refresh
- Scope limitation and principle of least privilege
- Data privacy and LGPD compliance

### OAuth 2.0 Security Implementation

#### Google Cloud Console Setup
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

### Secure OAuth Flow Implementation

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
```

### Google Calendar API Security

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
```

### Access Control & Permissions

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
```

---

## 🔐 SECRET MANAGEMENT

### Overview

#### What Are Secrets?
Secrets are sensitive pieces of information that should never be exposed publicly:
- **Database passwords** and connection strings
- **API keys** (Google Calendar, Google Sheets, etc.)
- **JWT tokens** and session keys
- **OAuth client secrets** and refresh tokens
- **Email service credentials** (SMTP passwords)
- **Encryption keys** and signing certificates
- **Third-party service tokens** and webhooks

#### Security Principles
1. **Never commit secrets to version control**
2. **Use environment-specific secret management**
3. **Implement least privilege access**
4. **Rotate secrets regularly**
5. **Monitor and audit secret usage**
6. **Encrypt secrets at rest and in transit**

### Secret Storage Solutions

#### Environment Variables (.env files)
```bash
# .env.development (local development only)
SECRET_KEY=dev-key-not-for-production-123456
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
GOOGLE_CLIENT_ID=your-dev-client-id
GOOGLE_CLIENT_SECRET=your-dev-client-secret
EMAIL_HOST_PASSWORD=your-dev-email-password
```

#### Docker Secrets
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  web:
    image: aprender-sistema:latest
    secrets:
      - django_secret_key
      - db_password
      - google_client_secret
    environment:
      - SECRET_KEY_FILE=/run/secrets/django_secret_key
      - DB_PASSWORD_FILE=/run/secrets/db_password

secrets:
  django_secret_key:
    external: true
  db_password:
    external: true
  google_client_secret:
    external: true
```

### Secret Lifecycle Management

#### Strong Secret Generation
```python
# scripts/generate_secrets.py
import secrets
import string
import base64
import os

def generate_django_secret_key(length=50):
    """Generate a cryptographically secure Django SECRET_KEY"""
    chars = string.ascii_letters + string.digits + '!@#$%^&*(-_=+)'
    return ''.join(secrets.choice(chars) for _ in range(length))

def generate_api_key(length=32):
    """Generate a secure API key"""
    return secrets.token_urlsafe(length)

def generate_database_password(length=20):
    """Generate a secure database password"""
    chars = string.ascii_letters + string.digits + '!@#$%^&*'
    # Ensure at least one of each type
    password = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice('!@#$%^&*')
    ]
    # Fill the rest
    for _ in range(length - 4):
        password.append(secrets.choice(chars))
    
    # Shuffle the password
    secrets.SystemRandom().shuffle(password)
    return ''.join(password)
```

#### Secret Rotation
```bash
#!/bin/bash
# scripts/rotate_db_password.sh

OLD_PASSWORD=$(grep DB_PASSWORD .env | cut -d'=' -f2)
NEW_PASSWORD=$(python -c "import secrets, string; chars=string.ascii_letters+string.digits+'!@#$%^&*'; print(''.join(secrets.choice(chars) for _ in range(20)))")

echo "Rotating database password..."

# 1. Create new user with new password
psql -h $DB_HOST -U postgres -c "CREATE USER temp_user WITH PASSWORD '$NEW_PASSWORD';"
psql -h $DB_HOST -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO temp_user;"

# 2. Test connection with new credentials
if PGPASSWORD=$NEW_PASSWORD psql -h $DB_HOST -U temp_user -d $DB_NAME -c "SELECT 1;" > /dev/null 2>&1; then
    echo "New password verified"
    
    # 3. Update application configuration
    sed -i "s/DB_PASSWORD=$OLD_PASSWORD/DB_PASSWORD=$NEW_PASSWORD/" .env
    
    # 4. Restart application
    make restart-app
    
    # 5. Clean up old user
    psql -h $DB_HOST -U postgres -c "DROP USER IF EXISTS $DB_USER;"
    psql -h $DB_HOST -U postgres -c "ALTER USER temp_user RENAME TO $DB_USER;"
    
    echo "Database password rotated successfully"
else
    echo "Password rotation failed"
    psql -h $DB_HOST -U postgres -c "DROP USER temp_user;"
    exit 1
fi
```

---

## 🔍 SECRET SCANNING & DETECTION

### Pre-commit Hooks

#### Secret Detection Configuration
```yaml
# .pre-commit-config.yaml
repos:
  # Secrets detection
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        name: 🔍 Detect secrets
        args: ['--baseline', '.secrets.baseline']
        exclude: package-lock.json

  # Additional security checks
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.7
    hooks:
      - id: bandit
        name: 🔒 Security scan (Bandit)
        args: [-r, ., -ll, --skip=B101,B601]
        exclude: ^(tests/|migrations/|venv/)
```

#### Initialize Secrets Baseline
```bash
# Create baseline for existing secrets
detect-secrets scan --baseline .secrets.baseline

# Audit baseline (mark false positives)
detect-secrets audit .secrets.baseline

# Update baseline
detect-secrets scan --baseline .secrets.baseline --update
```

### CI/CD Secret Scanning

#### GitHub Actions Secret Scanning
```yaml
# .github/workflows/security.yml
name: Security Scan

on: [push, pull_request]

jobs:
  secret-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
      
      - name: Run secret detection
        run: |
          pip install detect-secrets
          detect-secrets scan --force-use-all-plugins
          detect-secrets audit .secrets.baseline
      
      - name: Security audit
        run: |
          pip install bandit safety
          bandit -r . -ll
          safety check
```

### Runtime Secret Protection

#### Environment Variable Masking
```python
# core/utils/logging.py
import logging
import re

class SecretMaskingFormatter(logging.Formatter):
    """Custom formatter to mask secrets in logs"""
    
    SECRET_PATTERNS = [
        r'password["\']?\s*[:=]\s*["\']?([^"\'\\s]+)',
        r'secret["\']?\s*[:=]\s*["\']?([^"\'\\s]+)',
        r'token["\']?\s*[:=]\s*["\']?([^"\'\\s]+)',
        r'key["\']?\s*[:=]\s*["\']?([^"\'\\s]+)',
    ]
    
    def format(self, record):
        msg = super().format(record)
        
        for pattern in self.SECRET_PATTERNS:
            msg = re.sub(pattern, r'\1=***MASKED***', msg, flags=re.IGNORECASE)
        
        return msg
```

---

## 📚 BEST PRACTICES

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

## 🚨 INCIDENT RESPONSE

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

### Secret Compromise Detection

#### Automated Monitoring
```python
# core/monitoring/secret_monitor.py
import hashlib
import logging
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

class SecretIntegrityMonitor:
    """Monitor secret integrity and detect unauthorized changes"""
    
    def __init__(self):
        self.secret_hashes = {}
        self._initialize_hashes()
    
    def _initialize_hashes(self):
        """Create hashes of current secrets for integrity checking"""
        secrets_to_monitor = [
            'SECRET_KEY',
            'DATABASE_URL', 
            'GOOGLE_CLIENT_SECRET',
            'EMAIL_HOST_PASSWORD',
        ]
        
        for secret_name in secrets_to_monitor:
            secret_value = getattr(settings, secret_name, None)
            if secret_value:
                self.secret_hashes[secret_name] = hashlib.sha256(
                    secret_value.encode()
                ).hexdigest()
    
    def check_integrity(self):
        """Check if secrets have been tampered with"""
        for secret_name, expected_hash in self.secret_hashes.items():
            current_value = getattr(settings, secret_name, None)
            if current_value:
                current_hash = hashlib.sha256(
                    current_value.encode()
                ).hexdigest()
                
                if current_hash != expected_hash:
                    logger.critical(
                        f"Secret integrity violation detected: {secret_name}"
                    )
                    self._alert_security_team(secret_name)
```

### Emergency Contacts

#### Google API Issues
- **Google Cloud Support**: [Google Cloud Console](https://console.cloud.google.com/support)
- **Google Calendar API Support**: [Google Workspace Support](https://support.google.com/a/answer/1047213)

#### Internal Security Team
- **Security Lead**: security@yourdomain.com
- **Privacy Officer**: privacy@yourdomain.com
- **DevOps Team**: devops@yourdomain.com

---

## 📝 CHANGELOG

### Versão 2.0.0 Unificada (30/09/2025)
- ✅ Unificação de 3 documentos de segurança
- ✅ Consolidação de Google Integrations Security
- ✅ Secret Management integrado
- ✅ Secret Scanning implementado

### Versão 1.0.0 (11/09/2025)
- ✅ Documentos individuais criados
- ✅ Google Integrations Security implementado
- ✅ Secret Management estabelecido

---

**🔐 SEGURANÇA COMPLETA - SISTEMA APRENDER**

*Documento unificado em: 2025-09-30*
*Status: ✅ SEGURANÇA CONSOLIDADA*

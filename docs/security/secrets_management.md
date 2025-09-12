# 🔐 Secrets Management - Sistema Aprender

This document outlines comprehensive secrets management practices for the Sistema Aprender project, ensuring secure handling of sensitive information throughout the application lifecycle.

## 📋 Overview

### What Are Secrets?
Secrets are sensitive pieces of information that should never be exposed publicly:
- **Database passwords** and connection strings
- **API keys** (Google Calendar, Google Sheets, etc.)
- **JWT tokens** and session keys
- **OAuth client secrets** and refresh tokens
- **Email service credentials** (SMTP passwords)
- **Encryption keys** and signing certificates
- **Third-party service tokens** and webhooks

### Security Principles
1. **Never commit secrets to version control**
2. **Use environment-specific secret management**
3. **Implement least privilege access**
4. **Rotate secrets regularly**
5. **Monitor and audit secret usage**
6. **Encrypt secrets at rest and in transit**

---

## 🛡️ Secret Storage Solutions

### 1. Environment Variables (.env files)

#### Development Environment
```bash
# .env.development (local development only)
SECRET_KEY=dev-key-not-for-production-123456
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
GOOGLE_CLIENT_ID=your-dev-client-id
GOOGLE_CLIENT_SECRET=your-dev-client-secret
EMAIL_HOST_PASSWORD=your-dev-email-password
```

#### Staging Environment
```bash
# .env.staging (staging server only)
SECRET_KEY=staging-secret-key-random-256-bits
DEBUG=False
DATABASE_URL=postgresql://user:password@staging-db:5432/aprender_staging
GOOGLE_CLIENT_ID=staging-google-client-id
GOOGLE_CLIENT_SECRET=staging-google-client-secret
EMAIL_HOST_PASSWORD=staging-smtp-password
REDIS_URL=redis://staging-redis:6379/0
```

#### Production Environment
```bash
# .env.production (production server only)
SECRET_KEY=super-secure-production-key-256-bits-entropy
DEBUG=False
DATABASE_URL=postgresql://prod_user:complex_password@prod-db:5432/aprender_prod
GOOGLE_CLIENT_ID=production-google-client-id
GOOGLE_CLIENT_SECRET=production-google-client-secret
EMAIL_HOST_PASSWORD=production-smtp-password
REDIS_URL=redis://prod-redis:6379/0
```

### 2. Docker Secrets

#### Docker Compose Secrets
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

#### Creating Docker Secrets
```bash
# Create secrets
echo "super-secure-production-key" | docker secret create django_secret_key -
echo "complex-database-password" | docker secret create db_password -
echo "google-oauth-client-secret" | docker secret create google_client_secret -

# List secrets
docker secret ls

# Inspect secret (without showing value)
docker secret inspect django_secret_key
```

### 3. Cloud-Based Secret Management

#### AWS Secrets Manager
```python
# core/utils/secrets_aws.py
import boto3
from botocore.exceptions import ClientError

def get_secret(secret_name, region_name='us-east-1'):
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return response['SecretString']
    except ClientError as e:
        raise e

# Usage in settings.py
if ENVIRONMENT == 'production':
    SECRET_KEY = get_secret('aprender-sistema/secret-key')
    DB_PASSWORD = get_secret('aprender-sistema/db-password')
```

#### Google Secret Manager
```python
# core/utils/secrets_gcp.py
from google.cloud import secretmanager

def get_secret(project_id, secret_id, version_id='latest'):
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

# Usage in settings.py
if ENVIRONMENT == 'production':
    PROJECT_ID = 'your-gcp-project'
    SECRET_KEY = get_secret(PROJECT_ID, 'django-secret-key')
    DB_PASSWORD = get_secret(PROJECT_ID, 'database-password')
```

#### Azure Key Vault
```python
# core/utils/secrets_azure.py
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

def get_secret(vault_url, secret_name):
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=vault_url, credential=credential)
    
    secret = client.get_secret(secret_name)
    return secret.value

# Usage in settings.py
if ENVIRONMENT == 'production':
    VAULT_URL = "https://your-vault.vault.azure.net/"
    SECRET_KEY = get_secret(VAULT_URL, 'django-secret-key')
    DB_PASSWORD = get_secret(VAULT_URL, 'database-password')
```

---

## 🔄 Secret Lifecycle Management

### 1. Secret Generation

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

if __name__ == '__main__':
    print("Generated Secrets:")
    print(f"SECRET_KEY={generate_django_secret_key()}")
    print(f"API_KEY={generate_api_key()}")
    print(f"DB_PASSWORD={generate_database_password()}")
```

#### Automated Secret Generation
```bash
#!/bin/bash
# scripts/setup_secrets.sh

echo "Generating secrets for Sistema Aprender..."

# Generate Django secret key
SECRET_KEY=$(python -c "import secrets; print(''.join(secrets.choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)') for _ in range(50)))")

# Generate database password
DB_PASSWORD=$(python -c "import secrets, string; chars=string.ascii_letters+string.digits+'!@#$%^&*'; print(''.join(secrets.choice(chars) for _ in range(20)))")

# Generate API keys
GOOGLE_API_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Create .env file
cat > .env << EOF
SECRET_KEY=${SECRET_KEY}
DB_PASSWORD=${DB_PASSWORD}
GOOGLE_API_KEY=${GOOGLE_API_KEY}
EOF

echo "Secrets generated and saved to .env file"
chmod 600 .env
```

### 2. Secret Rotation

#### Database Password Rotation
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

#### Google OAuth Token Refresh
```python
# core/management/commands/rotate_google_tokens.py
from django.core.management.base import BaseCommand
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from core.services.google_auth import GoogleAuthService

class Command(BaseCommand):
    help = 'Rotate Google OAuth tokens'
    
    def handle(self, *args, **options):
        auth_service = GoogleAuthService()
        
        # Refresh tokens
        try:
            new_credentials = auth_service.refresh_tokens()
            
            # Update stored credentials
            auth_service.save_credentials(new_credentials)
            
            self.stdout.write(
                self.style.SUCCESS('Google OAuth tokens rotated successfully')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Token rotation failed: {str(e)}')
            )
```

### 3. Secret Validation

#### Environment Validation Script
```python
# scripts/validate_secrets.py
import os
import re
from urllib.parse import urlparse

def validate_secret_key():
    """Validate Django SECRET_KEY"""
    secret_key = os.getenv('SECRET_KEY')
    if not secret_key:
        return False, "SECRET_KEY not set"
    
    if len(secret_key) < 50:
        return False, "SECRET_KEY too short (minimum 50 characters)"
    
    if secret_key in ['dev-key', 'changeme', 'insecure']:
        return False, "SECRET_KEY appears to be a default/insecure value"
    
    return True, "SECRET_KEY valid"

def validate_database_url():
    """Validate DATABASE_URL"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        return False, "DATABASE_URL not set"
    
    try:
        parsed = urlparse(db_url)
        if not parsed.password:
            return False, "Database password not found in URL"
        
        if len(parsed.password) < 8:
            return False, "Database password too short"
        
        return True, "DATABASE_URL valid"
    except Exception as e:
        return False, f"Invalid DATABASE_URL: {str(e)}"

def validate_google_credentials():
    """Validate Google API credentials"""
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        return False, "Google credentials not set"
    
    if not client_id.endswith('.apps.googleusercontent.com'):
        return False, "Invalid Google Client ID format"
    
    if len(client_secret) < 24:
        return False, "Google Client Secret appears invalid"
    
    return True, "Google credentials valid"

def main():
    validations = [
        validate_secret_key,
        validate_database_url,
        validate_google_credentials,
    ]
    
    all_valid = True
    
    for validation in validations:
        valid, message = validation()
        status = "✅" if valid else "❌"
        print(f"{status} {message}")
        
        if not valid:
            all_valid = False
    
    if all_valid:
        print("\n🎉 All secrets are valid!")
        return 0
    else:
        print("\n⚠️ Some secrets need attention!")
        return 1

if __name__ == '__main__':
    exit(main())
```

---

## 🔍 Secret Detection & Prevention

### 1. Pre-commit Hooks

#### Secret Detection Configuration
```yaml
# .pre-commit-config.yaml (already in project)
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

### 2. CI/CD Secret Scanning

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

### 3. Runtime Secret Protection

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

# Usage in settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'secure': {
            '()': 'core.utils.logging.SecretMaskingFormatter',
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/django.log',
            'formatter': 'secure',
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'INFO',
    },
}
```

---

## 🚨 Incident Response

### 1. Secret Compromise Detection

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
    
    def _alert_security_team(self, secret_name):
        """Alert security team of potential compromise"""
        # Send alert email, Slack notification, etc.
        pass
```

### 2. Secret Rotation Emergency Procedures

#### Emergency Database Password Reset
```bash
#!/bin/bash
# scripts/emergency_db_reset.sh

echo "EMERGENCY: Resetting database password"

# Generate new password
NEW_PASSWORD=$(openssl rand -base64 32)

# Update database
sudo -u postgres psql << EOF
ALTER USER aprender_user WITH PASSWORD '$NEW_PASSWORD';
EOF

# Update application configuration
kubectl create secret generic db-credentials \
    --from-literal=password="$NEW_PASSWORD" \
    --dry-run=client -o yaml | kubectl apply -f -

# Restart application pods
kubectl rollout restart deployment aprender-sistema

echo "Emergency password reset completed"
echo "New password: $NEW_PASSWORD (store securely)"
```

#### OAuth Token Revocation
```python
# core/management/commands/revoke_oauth_tokens.py
from django.core.management.base import BaseCommand
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import requests

class Command(BaseCommand):
    help = 'Revoke all OAuth tokens in emergency'
    
    def handle(self, *args, **options):
        # Revoke Google OAuth tokens
        credentials_file = 'google_credentials.json'
        
        if os.path.exists(credentials_file):
            with open(credentials_file, 'r') as f:
                creds_data = json.load(f)
            
            # Revoke refresh token
            revoke_url = 'https://oauth2.googleapis.com/revoke'
            response = requests.post(revoke_url, data={
                'token': creds_data.get('refresh_token')
            })
            
            if response.status_code == 200:
                self.stdout.write(
                    self.style.SUCCESS('OAuth tokens revoked successfully')
                )
                
                # Remove credentials file
                os.remove(credentials_file)
            else:
                self.stdout.write(
                    self.style.ERROR('Failed to revoke tokens')
                )
```

### 3. Compromise Response Checklist

#### Immediate Response (0-1 hour)
- [ ] **Identify compromised secrets**
- [ ] **Revoke/rotate compromised credentials**
- [ ] **Block unauthorized access**
- [ ] **Preserve evidence and logs**
- [ ] **Notify security team and stakeholders**

#### Short-term Response (1-24 hours)
- [ ] **Complete forensic analysis**
- [ ] **Update all related secrets**
- [ ] **Review access logs**
- [ ] **Implement additional monitoring**
- [ ] **Update security procedures**

#### Long-term Response (24+ hours)
- [ ] **Conduct security audit**
- [ ] **Update secret management procedures**
- [ ] **Implement additional security controls**
- [ ] **Training and awareness updates**
- [ ] **Document lessons learned**

---

## 📊 Monitoring & Auditing

### 1. Secret Access Logging

#### Custom Middleware for Secret Access
```python
# core/middleware/secret_audit.py
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('security.secrets')

class SecretAccessAuditMiddleware(MiddlewareMixin):
    """Log access to sensitive configuration"""
    
    SENSITIVE_SETTINGS = [
        'SECRET_KEY',
        'DATABASE_URL',
        'GOOGLE_CLIENT_SECRET',
        'EMAIL_HOST_PASSWORD',
    ]
    
    def process_request(self, request):
        # Log when sensitive settings are accessed
        for setting in self.SENSITIVE_SETTINGS:
            if hasattr(settings, setting):
                logger.info(
                    f"Secret access: {setting} accessed by {request.user} "
                    f"from {request.META.get('REMOTE_ADDR')}"
                )
```

### 2. Secret Usage Analytics

#### Secret Usage Tracking
```python
# core/utils/secret_analytics.py
import json
from datetime import datetime
from django.core.cache import cache

class SecretUsageTracker:
    """Track secret usage patterns for security analysis"""
    
    def track_usage(self, secret_name, context=None):
        """Track when and how secrets are used"""
        usage_key = f"secret_usage:{secret_name}"
        
        usage_data = cache.get(usage_key, {
            'count': 0,
            'first_used': None,
            'last_used': None,
            'contexts': []
        })
        
        now = datetime.now().isoformat()
        usage_data['count'] += 1
        usage_data['last_used'] = now
        
        if not usage_data['first_used']:
            usage_data['first_used'] = now
        
        if context and context not in usage_data['contexts']:
            usage_data['contexts'].append(context)
        
        cache.set(usage_key, usage_data, timeout=86400 * 7)  # 7 days
    
    def get_usage_report(self):
        """Generate usage report for all tracked secrets"""
        # Implementation for generating reports
        pass
```

### 3. Compliance Reporting

#### LGPD Compliance for Secrets
```python
# core/compliance/lgpd_secrets.py
from datetime import datetime, timedelta
from django.db import models

class SecretAuditLog(models.Model):
    """LGPD-compliant audit log for secret operations"""
    
    OPERATION_CHOICES = [
        ('CREATE', 'Secret Created'),
        ('READ', 'Secret Accessed'),
        ('UPDATE', 'Secret Modified'),
        ('DELETE', 'Secret Deleted'),
        ('ROTATE', 'Secret Rotated'),
    ]
    
    secret_name = models.CharField(max_length=100)
    operation = models.CharField(max_length=10, choices=OPERATION_CHOICES)
    user = models.CharField(max_length=100, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    purpose = models.TextField()  # LGPD requirement
    legal_basis = models.CharField(max_length=100)  # LGPD requirement
    
    class Meta:
        db_table = 'secret_audit_log'
        indexes = [
            models.Index(fields=['secret_name', 'timestamp']),
            models.Index(fields=['operation', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.operation} on {self.secret_name} at {self.timestamp}"

    @classmethod
    def cleanup_old_logs(cls, days_to_keep=1095):  # 3 years default
        """Clean up old audit logs per LGPD retention requirements"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        cls.objects.filter(timestamp__lt=cutoff_date).delete()
```

---

## 🛠️ Tools & Utilities

### 1. Secret Management CLI

#### Custom Management Commands
```python
# core/management/commands/secrets.py
from django.core.management.base import BaseCommand, CommandError
from core.utils.secrets import SecretManager

class Command(BaseCommand):
    help = 'Manage application secrets'
    
    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='action')
        
        # List secrets
        list_parser = subparsers.add_parser('list')
        list_parser.add_argument('--show-values', action='store_true')
        
        # Generate secret
        gen_parser = subparsers.add_parser('generate')
        gen_parser.add_argument('name', help='Secret name')
        gen_parser.add_argument('--type', choices=['key', 'password', 'token'])
        
        # Rotate secret
        rotate_parser = subparsers.add_parser('rotate')
        rotate_parser.add_argument('name', help='Secret name')
        
        # Validate secrets
        validate_parser = subparsers.add_parser('validate')
    
    def handle(self, *args, **options):
        manager = SecretManager()
        
        if options['action'] == 'list':
            self.list_secrets(manager, options['show_values'])
        elif options['action'] == 'generate':
            self.generate_secret(manager, options)
        elif options['action'] == 'rotate':
            self.rotate_secret(manager, options['name'])
        elif options['action'] == 'validate':
            self.validate_secrets(manager)
    
    def list_secrets(self, manager, show_values=False):
        secrets = manager.list_secrets()
        for name, value in secrets.items():
            if show_values:
                self.stdout.write(f"{name}: {value}")
            else:
                self.stdout.write(f"{name}: ***HIDDEN***")
```

### 2. Secret Backup & Recovery

#### Secure Backup Script
```bash
#!/bin/bash
# scripts/backup_secrets.sh

BACKUP_DIR="/secure/backups/secrets"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="secrets_backup_${DATE}.tar.gz.enc"

echo "Creating secure secrets backup..."

# Create temporary directory
TEMP_DIR=$(mktemp -d)

# Copy environment files (without exposing content)
cp .env* "$TEMP_DIR/" 2>/dev/null || true

# Export Docker secrets (if using Docker Swarm)
if command -v docker &> /dev/null; then
    docker secret ls --format "{{.Name}}" > "$TEMP_DIR/docker_secrets_list.txt"
fi

# Create encrypted archive
tar -czf - -C "$TEMP_DIR" . | \
    openssl enc -aes-256-cbc -salt -pbkdf2 \
    -out "$BACKUP_DIR/$BACKUP_FILE"

# Clean up
rm -rf "$TEMP_DIR"

# Set restrictive permissions
chmod 600 "$BACKUP_DIR/$BACKUP_FILE"
chown root:root "$BACKUP_DIR/$BACKUP_FILE"

echo "Backup created: $BACKUP_DIR/$BACKUP_FILE"
echo "Store the encryption password securely!"
```

### 3. Development Tools

#### Secret Generation for Development
```python
# scripts/dev_setup_secrets.py
import os
import secrets
import string

def generate_dev_env():
    """Generate development environment with secure defaults"""
    
    dev_secrets = {
        'SECRET_KEY': generate_django_secret_key(),
        'DEBUG': 'True',
        'DATABASE_URL': 'sqlite:///db.sqlite3',
        'GOOGLE_CLIENT_ID': 'dev-client-id',
        'GOOGLE_CLIENT_SECRET': 'dev-client-secret',
        'EMAIL_HOST_PASSWORD': 'dev-email-password',
        'REDIS_URL': 'redis://localhost:6379/0',
    }
    
    # Write to .env.development
    with open('.env.development', 'w') as f:
        f.write("# Development Environment\n")
        f.write("# Generated automatically - safe for local development\n\n")
        
        for key, value in dev_secrets.items():
            f.write(f"{key}={value}\n")
    
    print("Development environment created: .env.development")
    print("⚠️  This file contains development secrets only!")

def generate_django_secret_key(length=50):
    chars = string.ascii_letters + string.digits + '!@#$%^&*(-_=+)'
    return ''.join(secrets.choice(chars) for _ in range(length))

if __name__ == '__main__':
    generate_dev_env()
```

---

## 📚 Best Practices Summary

### ✅ Do's
- **Use environment variables** for all secrets
- **Generate strong, unique secrets** for each environment
- **Rotate secrets regularly** (quarterly for production)
- **Use dedicated secret management services** for production
- **Monitor secret access** and usage patterns
- **Implement least privilege access** to secrets
- **Encrypt secrets at rest** and in transit
- **Use separate secrets** for different environments
- **Document secret rotation procedures**
- **Test secret rotation** in staging first

### ❌ Don'ts
- **Never commit secrets** to version control
- **Don't use default or weak secrets**
- **Don't share secrets** via email or chat
- **Don't store secrets** in plain text files
- **Don't use the same secret** across environments
- **Don't skip secret validation**
- **Don't ignore security alerts**
- **Don't hardcode secrets** in application code
- **Don't forget to rotate** compromised secrets
- **Don't mix development and production secrets**

### 🔍 Regular Audits
- **Monthly**: Review secret usage logs
- **Quarterly**: Rotate non-emergency secrets
- **Annually**: Full security audit and penetration testing
- **After incidents**: Emergency rotation and review

---

## 📞 Emergency Contacts

### Security Team
- **Security Lead**: security-lead@yourdomain.com
- **On-call Security**: +55 85 9999-0003
- **Incident Response**: incident@yourdomain.com

### Infrastructure Team
- **DevOps Lead**: devops@yourdomain.com
- **Database Admin**: dba@yourdomain.com
- **System Admin**: sysadmin@yourdomain.com

---

*Secrets management guide created during repository cleanup - Phase 4*  
*Date: 2025-09-11*  
*Version: 1.0*
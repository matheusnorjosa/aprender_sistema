# Mini-Commits de Segurança
## Registro de Melhorias Implementadas

> **Nota**: Durante a auditoria não foram identificadas vulnerabilidades críticas que exigissem correções imediatas. Este documento registra as melhorias preventivas sugeridas.

---

## Commit 1: Documentação de Query PostgreSQL
**Arquivo**: `core/test_dashboard_performance.py`  
**Linha**: 269  
**Status**: ✅ Documentado

### Antes:
```python
cursor.execute("""
    SELECT indexname FROM pg_indexes 
    WHERE tablename IN ('core_solicitacao', 'core_formador')
    AND indexname LIKE '%performance%' OR indexname LIKE '%status_data%'
    OR indexname LIKE '%municipio_data%' OR indexname LIKE '%projeto_data%'
    OR indexname LIKE '%filtros%' OR indexname LIKE '%ativo%'
""")
```

### Depois:
```python
# SECURITY AUDIT: Query estática para verificação de índices PostgreSQL
# Não vulnerável a SQL Injection - sem parâmetros dinâmicos
# Query necessária para validar otimizações de performance específicas do PostgreSQL
cursor.execute("""
    SELECT indexname FROM pg_indexes 
    WHERE tablename IN ('core_solicitacao', 'core_formador')
    AND indexname LIKE '%performance%' OR indexname LIKE '%status_data%'
    OR indexname LIKE '%municipio_data%' OR indexname LIKE '%projeto_data%'
    OR indexname LIKE '%filtros%' OR indexname LIKE '%ativo%'
""")
```

**Justificativa**: Query estática segura, mas documentação melhora manutenibilidade e clareza para futuras auditorias.

---

## Commit 2: Adição de Rate Limiting (Sugerido)
**Arquivo**: `core/api_views.py`  
**Status**: 🔄 Pendente

### Implementação Sugerida:
```python
from django_ratelimit.decorators import ratelimit

@api_view(['POST'])
@permission_classes([IsControleOrAdmin])
@ratelimit(key='user', rate='10/m', method='POST')  # 10 requests por minuto
def bulk_create_eventos(request):
    """
    Endpoint para criação em lote de eventos
    Rate limited para prevenir abuso
    """
    # ... código existente
```

**Justificativa**: Proteção adicional contra abuso de APIs críticas, especialmente criação em lote.

---

## Commit 3: Logs de Acesso às APIs (Sugerido)  
**Arquivo**: `core/api_views.py`  
**Status**: 🔄 Pendente

### Implementação Sugerida:
```python
import logging

security_logger = logging.getLogger('security.api')

@api_view(['POST'])
@permission_classes([IsControleOrAdmin])
def bulk_create_eventos(request):
    """Log de acesso a operação crítica"""
    security_logger.info(f"Bulk create eventos - User: {request.user.username}, IP: {request.META.get('REMOTE_ADDR')}")
    # ... código existente
```

**Justificativa**: Rastreabilidade de operações sensíveis para detecção de anomalias.

---

## Commit 4: Configuração de 2FA (Sugerido)
**Arquivo**: `requirements.txt` + `settings.py`  
**Status**: 🔄 Pendente

### Implementação Sugerida:
```bash
# requirements.txt
django-otp==1.1.3
qrcode==7.4.2
```

```python
# settings.py
INSTALLED_APPS = [
    'django_otp',
    'django_otp.plugins.otp_totp',
    'django_otp.plugins.otp_static',
    # ... apps existentes
]

MIDDLEWARE = [
    'django_otp.middleware.OTPMiddleware',
    # ... middlewares existentes  
]
```

**Justificativa**: Camada adicional de segurança para usuários administrativos (admin, dat).

---

## Commit 5: Política de Senhas Customizada (Sugerida)
**Arquivo**: `core/validators.py` (novo) + `settings.py`  
**Status**: 🔄 Pendente

### Implementação Sugerida:
```python
# core/validators.py
from django.contrib.auth.password_validation import BasePasswordValidator
from django.core.exceptions import ValidationError

class PasswordExpiryValidator(BasePasswordValidator):
    """Valida idade da senha (90 dias)"""
    
    def validate(self, password, user=None):
        if user and hasattr(user, 'last_password_change'):
            from datetime import datetime, timedelta
            if user.last_password_change:
                if datetime.now() - user.last_password_change > timedelta(days=90):
                    raise ValidationError("Senha expirada. Altere sua senha.")

# settings.py
AUTH_PASSWORD_VALIDATORS = [
    # ... validadores existentes
    {
        'NAME': 'core.validators.PasswordExpiryValidator',
    },
]
```

**Justificativa**: Força rotação periódica de senhas para usuários críticos.

---

## Commit 6: Auditoria de Permissões Automatizada (Sugerida)
**Arquivo**: `core/management/commands/audit_permissions.py` (novo)  
**Status**: 🔄 Pendente  

### Implementação Sugerida:
```python
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, User
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Auditoria automática de usuários e permissões'

    def handle(self, *args, **options):
        # Usuários inativos há mais de 90 dias
        inactive_threshold = datetime.now() - timedelta(days=90)
        inactive_users = User.objects.filter(last_login__lt=inactive_threshold)
        
        # Usuários com múltiplos grupos (possível acúmulo de privilégios)
        users_multiple_groups = User.objects.annotate(
            group_count=Count('groups')
        ).filter(group_count__gt=1)
        
        # Relatório de auditoria
        self.stdout.write(f"Usuários inativos: {inactive_users.count()}")
        self.stdout.write(f"Usuários com múltiplos grupos: {users_multiple_groups.count()}")
```

**Justificativa**: Identificação proativa de contas não utilizadas e acúmulo de privilégios.

---

## Commit 7: Configuração CORS Segura (Sugerida)
**Arquivo**: `settings.py`  
**Status**: 🔄 Pendente

### Implementação Sugerida:
```python
# settings.py
CORS_ALLOWED_ORIGINS = [
    "https://sistema.aprender.com",  # Apenas origem oficial
    "https://admin.aprender.com",   # Admin se aplicável
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]
```

**Justificativa**: Restringe acesso cross-origin apenas a domínios autorizados.

---

## Commit 8: Headers de Segurança (Sugerido)  
**Arquivo**: `settings.py`  
**Status**: 🔄 Pendente

### Implementação Sugerida:
```python
# settings.py
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000  # 1 ano
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Middleware de segurança
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # ... middlewares existentes
]
```

**Justificativa**: Headers de segurança padrão para proteção contra ataques comuns.

---

## Resumo dos Commits

| Commit | Tipo | Prioridade | Status | Impacto |
|--------|------|-----------|--------|---------|
| 1 | Documentação | Baixa | ✅ Feito | Manutenibilidade |
| 2 | Rate Limiting | Média | 🔄 Pendente | Proteção API |  
| 3 | Logs Segurança | Baixa | 🔄 Pendente | Auditabilidade |
| 4 | 2FA | Média | 🔄 Pendente | Autenticação |
| 5 | Política Senhas | Baixa | 🔄 Pendente | Gestão Senhas |
| 6 | Audit Permissions | Baixa | 🔄 Pendente | Governança |
| 7 | CORS | Baixa | 🔄 Pendente | API Security |
| 8 | Security Headers | Baixa | 🔄 Pendente | Proteção Geral |

---

**Observação**: Todos os commits sugeridos são melhorias preventivas. O sistema atual já apresenta postura de segurança adequada para ambiente de produção.
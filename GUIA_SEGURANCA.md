# Guia de Segurança - Sistema Aprender

## Introdução

Este guia estabelece as diretrizes de segurança para o desenvolvimento, implantação e operação do Sistema Aprender. A segurança é uma responsabilidade compartilhada entre desenvolvedores, administradores e usuários finais.

## Princípios de Segurança

### Defesa em Profundidade
Implementamos múltiplas camadas de segurança:
- **Autenticação**: Controle de acesso robusto
- **Autorização**: Permissões granulares por funcionalidade
- **Criptografia**: Proteção de dados em trânsito e repouso
- **Auditoria**: Rastreamento completo de ações críticas
- **Monitoramento**: Detecção proativa de anomalias

### Princípio do Menor Privilégio
- Usuários recebem apenas as permissões mínimas necessárias
- Separação clara de responsabilidades por papel
- Revisão periódica de permissões

### Segurança por Design
- Validação de entrada em todas as camadas
- Sanitização de saída para prevenir XSS
- Configurações seguras por padrão

## Autenticação e Autorização

### Sistema de Autenticação Django

```python
# settings.py - Configurações de autenticação seguras
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,  # Mínimo 12 caracteres
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
    {
        'NAME': 'core.validators.CustomPasswordValidator',  # Validador customizado
    },
]

# Configurações de sessão seguras
SESSION_COOKIE_SECURE = not DEBUG  # HTTPS em produção
SESSION_COOKIE_HTTPONLY = True     # Previne acesso via JavaScript
SESSION_COOKIE_SAMESITE = 'Strict' # Proteção CSRF
SESSION_COOKIE_AGE = 3600          # 1 hora de duração

# CSRF Protection
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'
CSRF_TRUSTED_ORIGINS = [
    'https://sistema-aprender.render.com',
    'https://aprender.exemplo.com.br'
]
```

### Validador de Senha Customizado

```python
# core/validators.py
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
import re

class CustomPasswordValidator:
    """
    Validador personalizado para senhas do Sistema Aprender.

    Requisitos:
    - Mínimo 12 caracteres
    - Pelo menos 1 letra maiúscula
    - Pelo menos 1 letra minúscula
    - Pelo menos 1 número
    - Pelo menos 1 caractere especial
    - Não pode conter informações do usuário
    """

    def validate(self, password, user=None):
        """Valida se senha atende aos critérios de segurança."""

        # Verificar comprimento mínimo
        if len(password) < 12:
            raise ValidationError(
                _("A senha deve ter pelo menos 12 caracteres."),
                code='password_too_short',
            )

        # Verificar presença de caracteres obrigatórios
        if not re.search(r'[A-Z]', password):
            raise ValidationError(
                _("A senha deve conter pelo menos uma letra maiúscula."),
                code='password_no_upper',
            )

        if not re.search(r'[a-z]', password):
            raise ValidationError(
                _("A senha deve conter pelo menos uma letra minúscula."),
                code='password_no_lower',
            )

        if not re.search(r'\d', password):
            raise ValidationError(
                _("A senha deve conter pelo menos um número."),
                code='password_no_number',
            )

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError(
                _("A senha deve conter pelo menos um caractere especial."),
                code='password_no_special',
            )

        # Verificar se não contém informações do usuário
        if user:
            user_info = [
                user.username.lower(),
                user.first_name.lower(),
                user.last_name.lower(),
                user.email.lower().split('@')[0],
            ]

            for info in user_info:
                if info and len(info) > 2 and info in password.lower():
                    raise ValidationError(
                        _("A senha não pode conter informações do usuário."),
                        code='password_too_similar',
                    )

    def get_help_text(self):
        return _(
            "Sua senha deve ter pelo menos 12 caracteres, incluindo "
            "maiúsculas, minúsculas, números e caracteres especiais."
        )
```

### Controle de Acesso Baseado em Papéis

```python
# core/decorators.py
from functools import wraps
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required

def papel_required(papeis_permitidos):
    """
    Decorator para controle de acesso baseado em papel do usuário.

    Args:
        papeis_permitidos: Lista de papéis que podem acessar a view

    Example:
        @papel_required(['SUPERINTENDENCIA', 'ADMIN'])
        def aprovar_solicitacao(request, solicitacao_id):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if not hasattr(request.user, 'papel'):
                return HttpResponseForbidden("Usuário sem papel definido")

            if request.user.papel not in papeis_permitidos:
                return HttpResponseForbidden(
                    f"Acesso negado. Papéis permitidos: {', '.join(papeis_permitidos)}"
                )

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

# Exemplo de uso
@papel_required(['SUPERINTENDENCIA'])
def aprovar_solicitacao(request, solicitacao_id):
    """Apenas superintendência pode aprovar solicitações."""
    pass

@papel_required(['COORDENADOR', 'SUPERINTENDENCIA'])
def criar_solicitacao(request):
    """Coordenadores e superintendência podem criar solicitações."""
    pass
```

## Proteção de Dados

### Criptografia de Dados Sensíveis

```python
# core/utils/crypto.py
from cryptography.fernet import Fernet
from django.conf import settings
import base64
import os

class DataEncryption:
    """Utilitário para criptografia de dados sensíveis."""

    def __init__(self):
        # Usar chave do ambiente ou gerar uma nova
        key = os.environ.get('ENCRYPTION_KEY')
        if not key:
            key = Fernet.generate_key()
            print(f"Nova chave gerada: {key.decode()}")
            print("IMPORTANTE: Adicione ENCRYPTION_KEY às variáveis de ambiente")
        else:
            key = key.encode()

        self.cipher = Fernet(key)

    def encrypt(self, data: str) -> str:
        """Criptografa string e retorna resultado em base64."""
        encrypted_data = self.cipher.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """Descriptografa dados de base64."""
        try:
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self.cipher.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            raise ValueError(f"Erro ao descriptografar dados: {e}")

# Uso em models para dados sensíveis
class Usuario(AbstractUser):
    # Campos normais...

    _cpf_encrypted = models.TextField(blank=True)  # Armazena CPF criptografado

    @property
    def cpf(self):
        """Retorna CPF descriptografado."""
        if self._cpf_encrypted:
            crypto = DataEncryption()
            return crypto.decrypt(self._cpf_encrypted)
        return ""

    @cpf.setter
    def cpf(self, value):
        """Criptografa e armazena CPF."""
        if value:
            crypto = DataEncryption()
            self._cpf_encrypted = crypto.encrypt(value)
        else:
            self._cpf_encrypted = ""
```

### Proteção de Informações Pessoais (LGPD)

```python
# core/models.py
from django.db import models
from core.utils.crypto import DataEncryption

class LGPDMixin(models.Model):
    """Mixin para compliance com LGPD."""

    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    consentimento_lgpd = models.BooleanField(
        default=False,
        help_text="Usuário consentiu com o tratamento de dados pessoais"
    )
    data_consentimento = models.DateTimeField(
        null=True, blank=True,
        help_text="Data do consentimento LGPD"
    )

    class Meta:
        abstract = True

    def anonimizar_dados(self):
        """Remove dados pessoais para compliance LGPD."""
        # Implementar lógica específica em cada model
        raise NotImplementedError("Deve ser implementado em cada model")

class Usuario(AbstractUser, LGPDMixin):
    # Campos com dados pessoais criptografados
    _cpf_encrypted = models.TextField(blank=True)
    _telefone_encrypted = models.TextField(blank=True)

    def anonimizar_dados(self):
        """Anonimiza dados pessoais do usuário."""
        self.first_name = "REMOVIDO"
        self.last_name = "REMOVIDO"
        self.email = f"anonimo_{self.id}@removido.com"
        self._cpf_encrypted = ""
        self._telefone_encrypted = ""
        self.is_active = False
        self.save()

        # Log da anonimização
        LogAuditoria.objects.create(
            usuario=None,
            acao='ANONIMIZAR_USUARIO',
            modelo_afetado='Usuario',
            objeto_id=self.id,
            dados_anteriores={'motivo': 'Solicitação LGPD'},
            ip_origem='127.0.0.1'
        )
```

## Prevenção de Vulnerabilidades

### Proteção contra Injeção SQL

```python
# ✅ CORRETO - Uso de ORM Django
def buscar_formadores_por_municipio(municipio_nome):
    """Busca segura usando ORM."""
    return Formador.objects.filter(
        usuario__municipio__nome__icontains=municipio_nome,
        ativo=True
    )

# ✅ CORRETO - Query parametrizada quando necessário
def relatorio_custom(data_inicio, data_fim):
    """Query parametrizada para relatórios complexos."""
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT f.nome, COUNT(s.id) as total_eventos
            FROM core_formador f
            LEFT JOIN core_solicitacao_formadores sf ON f.id = sf.formador_id
            LEFT JOIN core_solicitacao s ON sf.solicitacao_id = s.id
            WHERE s.data_inicio BETWEEN %s AND %s
            GROUP BY f.id, f.nome
            ORDER BY total_eventos DESC
        """, [data_inicio, data_fim])

        return cursor.fetchall()

# ❌ INCORRETO - Vulnerável a SQL Injection
def buscar_formadores_inseguro(municipio_nome):
    """NUNCA FAZER ISSO - Vulnerável a SQL injection."""
    from django.db import connection

    with connection.cursor() as cursor:
        # PERIGOSO - input não sanitizado
        cursor.execute(f"""
            SELECT * FROM core_formador
            WHERE municipio = '{municipio_nome}'
        """)
```

### Proteção contra XSS (Cross-Site Scripting)

```html
<!-- templates/core/base.html -->
<!-- ✅ CORRETO - Django escapa automaticamente -->
<h1>Bem-vindo, {{ user.get_full_name }}</h1>
<p>Município: {{ user.municipio.nome }}</p>

<!-- ✅ CORRETO - Uso do filtro |safe apenas quando necessário -->
<div class="notifications">
    {{ notification.message|safe }}  <!-- Apenas se message for HTML confiável -->
</div>

<!-- ❌ INCORRETO - Usar |safe com dados do usuário -->
<script>
    // PERIGOSO - pode executar JavaScript malicioso
    var userName = "{{ user.username|safe }}";
</script>

<!-- ✅ CORRETO - Usar JSON filter para JavaScript -->
<script>
    var userName = {{ user.username|escapejs }};
    // ou melhor ainda:
    var userData = {{ user_data|json_script:"user-data" }};
</script>
```

```python
# core/utils/security.py
import bleach
from django.utils.html import escape
from django.utils.safestring import mark_safe

def sanitize_html_input(content):
    """
    Sanitiza entrada HTML permitindo apenas tags seguras.

    Args:
        content: Conteúdo HTML a ser sanitizado

    Returns:
        HTML limpo e seguro
    """
    allowed_tags = [
        'p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6'
    ]

    allowed_attributes = {}

    cleaned_content = bleach.clean(
        content,
        tags=allowed_tags,
        attributes=allowed_attributes,
        strip=True
    )

    return mark_safe(cleaned_content)

def escape_user_input(user_input):
    """Escapa entrada do usuário para uso seguro em templates."""
    return escape(user_input)
```

### Proteção CSRF (Cross-Site Request Forgery)

```html
<!-- templates/core/solicitacao_form.html -->
<form method="post" action="{% url 'criar_solicitacao' %}">
    {% csrf_token %}  <!-- OBRIGATÓRIO em todos os forms POST -->

    {{ form.as_p }}

    <button type="submit" class="btn btn-primary">
        Enviar Solicitação
    </button>
</form>
```

```python
# views.py - CSRF protection automática no Django
from django.views.decorators.csrf import csrf_protect
from django.middleware.csrf import get_token

@csrf_protect  # Opcional - Django aplica automaticamente
def criar_solicitacao(request):
    if request.method == 'POST':
        # Token CSRF verificado automaticamente
        form = SolicitacaoForm(request.POST)
        if form.is_valid():
            # Processar formulário...
            pass

    # Para AJAX requests
    context = {
        'csrf_token': get_token(request)
    }
    return render(request, 'solicitacao_form.html', context)
```

### Validação e Sanitização de Entrada

```python
# core/validators.py
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
import re

class CPFValidator:
    """Validador para CPF brasileiro."""

    def __call__(self, value):
        # Remove caracteres não numéricos
        cpf = re.sub(r'[^0-9]', '', value)

        if len(cpf) != 11:
            raise ValidationError('CPF deve ter 11 dígitos')

        # Verifica se não são todos iguais
        if cpf == cpf[0] * 11:
            raise ValidationError('CPF inválido')

        # Algoritmo de validação do CPF
        if not self._validar_cpf(cpf):
            raise ValidationError('CPF inválido')

    def _validar_cpf(self, cpf):
        """Implementa algoritmo de validação do CPF."""
        # Cálculo do primeiro dígito verificador
        soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
        resto = soma % 11
        digito1 = 0 if resto < 2 else 11 - resto

        # Cálculo do segundo dígito verificador
        soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
        resto = soma % 11
        digito2 = 0 if resto < 2 else 11 - resto

        return cpf[-2:] == f"{digito1}{digito2}"

# Uso nos models
class Usuario(AbstractUser):
    cpf = models.CharField(
        max_length=14,
        unique=True,
        validators=[CPFValidator()],
        help_text="CPF no formato 000.000.000-00"
    )

    telefone = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^\(\d{2}\)\s\d{4,5}-\d{4}$',
                message='Telefone deve estar no formato (XX) XXXXX-XXXX'
            )
        ]
    )
```

## Auditoria e Monitoramento

### Sistema de Auditoria Completo

```python
# core/models.py
import json
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

class LogAuditoria(models.Model):
    """Log completo de auditoria para rastreamento de ações."""

    ACOES_CHOICES = [
        ('CREATE', 'Criação'),
        ('UPDATE', 'Atualização'),
        ('DELETE', 'Exclusão'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('APPROVE', 'Aprovação'),
        ('REJECT', 'Rejeição'),
        ('VIEW_SENSITIVE', 'Visualização de dados sensíveis'),
        ('EXPORT_DATA', 'Exportação de dados'),
        ('ADMIN_ACTION', 'Ação administrativa'),
    ]

    usuario = models.ForeignKey(
        'Usuario',
        on_delete=models.SET_NULL,
        null=True,
        help_text="Usuário que executou a ação"
    )
    acao = models.CharField(max_length=50, choices=ACOES_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    # Referência genérica para qualquer modelo
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True)
    object_id = models.PositiveIntegerField(null=True)
    objeto_afetado = GenericForeignKey('content_type', 'object_id')

    # Dados do contexto
    ip_origem = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    dados_anteriores = models.JSONField(null=True, blank=True)
    dados_novos = models.JSONField(null=True, blank=True)
    observacoes = models.TextField(blank=True)

    # Metadados de segurança
    sessao_id = models.CharField(max_length=40, blank=True)
    nivel_risco = models.CharField(
        max_length=10,
        choices=[('LOW', 'Baixo'), ('MEDIUM', 'Médio'), ('HIGH', 'Alto')],
        default='LOW'
    )

    class Meta:
        verbose_name = "Log de Auditoria"
        verbose_name_plural = "Logs de Auditoria"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['usuario', 'timestamp']),
            models.Index(fields=['acao', 'timestamp']),
            models.Index(fields=['ip_origem', 'timestamp']),
            models.Index(fields=['nivel_risco', 'timestamp']),
        ]

    def __str__(self):
        usuario_nome = self.usuario.username if self.usuario else "Sistema"
        return f"{self.timestamp}: {usuario_nome} - {self.get_acao_display()}"

# Middleware para auditoria automática
class AuditoriaMiddleware:
    """Middleware para log automático de ações sensíveis."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Log de ações sensíveis
        if hasattr(request, 'user') and request.user.is_authenticated:
            self._log_sensitive_actions(request, response)

        return response

    def _log_sensitive_actions(self, request, response):
        """Registra ações que devem ser auditadas."""
        sensitive_paths = [
            '/admin/',
            '/aprovacoes/',
            '/usuarios/',
            '/relatorios/',
        ]

        if any(request.path.startswith(path) for path in sensitive_paths):
            LogAuditoria.objects.create(
                usuario=request.user,
                acao='VIEW_SENSITIVE',
                ip_origem=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                observacoes=f"Acesso a: {request.path}",
                nivel_risco='MEDIUM' if '/admin/' in request.path else 'LOW'
            )

    def _get_client_ip(self, request):
        """Obtém IP real do cliente considerando proxies."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
```

### Monitoramento de Segurança

```python
# core/services/security_monitoring.py
from datetime import datetime, timedelta
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger('security')

class SecurityMonitoring:
    """Serviço para monitoramento de eventos de segurança."""

    @staticmethod
    def detectar_tentativas_login_suspeitas():
        """Detecta múltiplas tentativas de login fracassadas."""
        from django.contrib.auth.models import User

        # Buscar logs de login nos últimos 15 minutos
        agora = datetime.now()
        inicio = agora - timedelta(minutes=15)

        # Contar tentativas por IP
        logs_login = LogAuditoria.objects.filter(
            acao='LOGIN_FAILED',
            timestamp__gte=inicio
        ).values('ip_origem').annotate(
            tentativas=models.Count('id')
        ).filter(tentativas__gte=5)

        for log in logs_login:
            SecurityMonitoring._alertar_tentativas_suspeitas(
                log['ip_origem'],
                log['tentativas']
            )

    @staticmethod
    def _alertar_tentativas_suspeitas(ip_origem, tentativas):
        """Envia alerta sobre tentativas de login suspeitas."""
        logger.warning(
            f"Múltiplas tentativas de login do IP {ip_origem}: {tentativas}",
            extra={
                'ip_origem': ip_origem,
                'tentativas': tentativas,
                'level': 'HIGH'
            }
        )

        # Enviar email para administradores
        if settings.EMAIL_ENABLED:
            send_mail(
                subject='[ALERTA SEGURANÇA] Tentativas de login suspeitas',
                message=f'''
                Detectadas {tentativas} tentativas de login fracassadas
                do IP {ip_origem} nos últimos 15 minutos.

                Verifique os logs de auditoria para mais detalhes.
                ''',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=settings.SECURITY_ADMIN_EMAILS,
                fail_silently=False
            )

    @staticmethod
    def verificar_acessos_privilegiados():
        """Monitora acessos a funcionalidades privilegiadas."""
        # Buscar acessos admin nas últimas 24h
        ontem = datetime.now() - timedelta(days=1)

        acessos_admin = LogAuditoria.objects.filter(
            acao__in=['ADMIN_ACTION', 'VIEW_SENSITIVE'],
            timestamp__gte=ontem,
            nivel_risco='HIGH'
        )

        if acessos_admin.count() > 50:  # Limite configurável
            logger.warning(
                f"Alto volume de acessos privilegiados: {acessos_admin.count()}",
                extra={'level': 'MEDIUM'}
            )

# Task periódica (para uso com Celery ou cron)
def executar_monitoramento_seguranca():
    """Executa verificações de segurança periodicamente."""
    SecurityMonitoring.detectar_tentativas_login_suspeitas()
    SecurityMonitoring.verificar_acessos_privilegiados()
```

## Configurações de Segurança

### Settings de Produção

```python
# settings.py - Configurações específicas de segurança
import os

# Segurança HTTPS
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = 31536000  # 1 ano
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Proteção de conteúdo
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# CSP (Content Security Policy)
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "https://fonts.googleapis.com")
CSP_FONT_SRC = ("'self'", "https://fonts.gstatic.com")
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_CONNECT_SRC = ("'self'",)

# Rate Limiting
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'

# Logging de segurança
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'security': {
            'format': '{levelname} {asctime} [SECURITY] {message}',
            'style': '{',
        },
    },
    'handlers': {
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/security.log',
            'maxBytes': 10*1024*1024,  # 10MB
            'backupCount': 5,
            'formatter': 'security',
        },
        'security_mail': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
        },
    },
    'loggers': {
        'security': {
            'handlers': ['security_file', 'security_mail'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# Email para alertas de segurança
SECURITY_ADMIN_EMAILS = [
    'admin@exemplo.com.br',
    'seguranca@exemplo.com.br',
]

# Configurações do banco seguras
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'OPTIONS': {
            'sslmode': 'require',
            'connect_timeout': 10,
        },
        # Outras configurações...
    }
}

# Limitação de upload
FILE_UPLOAD_MAX_MEMORY_SIZE = 2621440  # 2.5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 2621440
```

### Variáveis de Ambiente Seguras

```bash
# .env.production (nunca committar este arquivo)
SECRET_KEY=sua_chave_secreta_muito_longa_e_complexa_aqui
DATABASE_URL=postgresql://user:password@host:port/database

# Criptografia
ENCRYPTION_KEY=sua_chave_de_criptografia_fernet_aqui

# APIs externas
GOOGLE_OAUTH2_CLIENT_ID=seu_client_id_google
GOOGLE_OAUTH2_CLIENT_SECRET=seu_client_secret_google

# Email
EMAIL_HOST_USER=noreply@sistema-aprender.com.br
EMAIL_HOST_PASSWORD=senha_do_email

# Monitoramento
SENTRY_DSN=https://sua_url_sentry_aqui

# Rate limiting
REDIS_URL=redis://localhost:6379/1
```

## Backup e Recuperação

### Estratégia de Backup Seguro

```python
# scripts/backup_seguro.py
import os
import subprocess
import datetime
from cryptography.fernet import Fernet
import boto3

class BackupSeguro:
    """Sistema de backup criptografado."""

    def __init__(self):
        self.encryption_key = os.environ['BACKUP_ENCRYPTION_KEY']
        self.cipher = Fernet(self.encryption_key.encode())

        # Configuração AWS S3 para backup remoto
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
            aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY']
        )
        self.bucket_name = os.environ['BACKUP_S3_BUCKET']

    def criar_backup_database(self):
        """Cria backup criptografado do banco de dados."""
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

        # Gerar dump do PostgreSQL
        dump_file = f"backup_db_{timestamp}.sql"
        subprocess.run([
            'pg_dump',
            '--no-password',
            '--verbose',
            '--file', dump_file,
            os.environ['DATABASE_URL']
        ], check=True)

        # Criptografar backup
        encrypted_file = f"{dump_file}.encrypted"
        self._encrypt_file(dump_file, encrypted_file)

        # Upload para S3
        s3_key = f"database_backups/{encrypted_file}"
        self.s3_client.upload_file(encrypted_file, self.bucket_name, s3_key)

        # Limpar arquivos locais
        os.remove(dump_file)
        os.remove(encrypted_file)

        print(f"Backup criado e enviado para S3: {s3_key}")

    def _encrypt_file(self, input_file, output_file):
        """Criptografa arquivo usando Fernet."""
        with open(input_file, 'rb') as f:
            data = f.read()

        encrypted_data = self.cipher.encrypt(data)

        with open(output_file, 'wb') as f:
            f.write(encrypted_data)

    def recuperar_backup(self, backup_date):
        """Recupera e descriptografa backup específico."""
        encrypted_file = f"backup_db_{backup_date}.sql.encrypted"
        s3_key = f"database_backups/{encrypted_file}"

        # Download do S3
        self.s3_client.download_file(self.bucket_name, s3_key, encrypted_file)

        # Descriptografar
        decrypted_file = encrypted_file.replace('.encrypted', '')
        self._decrypt_file(encrypted_file, decrypted_file)

        print(f"Backup recuperado: {decrypted_file}")
        return decrypted_file

    def _decrypt_file(self, input_file, output_file):
        """Descriptografa arquivo."""
        with open(input_file, 'rb') as f:
            encrypted_data = f.read()

        decrypted_data = self.cipher.decrypt(encrypted_data)

        with open(output_file, 'wb') as f:
            f.write(decrypted_data)

# Agendamento automático (crontab)
# 0 2 * * * cd /path/to/project && python scripts/backup_seguro.py
```

## Checklist de Segurança

### Desenvolvimento
- [ ] Todos os forms usam `{% csrf_token %}`
- [ ] Validação de entrada em todas as camadas
- [ ] Sanitização de saída para prevenir XSS
- [ ] Uso correto do ORM (sem queries raw inseguras)
- [ ] Senhas seguem política de complexidade
- [ ] Dados sensíveis são criptografados
- [ ] Logs não expõem informações sensíveis
- [ ] Testes de segurança implementados

### Configuração
- [ ] `DEBUG = False` em produção
- [ ] `SECRET_KEY` único e seguro
- [ ] HTTPS configurado com HSTS
- [ ] CSP (Content Security Policy) configurado
- [ ] Cabeçalhos de segurança habilitados
- [ ] Rate limiting configurado
- [ ] Backup automático configurado
- [ ] Monitoramento de logs implementado

### Operacional
- [ ] Usuários têm apenas permissões necessárias
- [ ] Senhas são alteradas regularmente
- [ ] Logs de auditoria são revisados
- [ ] Patches de segurança aplicados
- [ ] Backups testados regularmente
- [ ] Plano de resposta a incidentes documentado
- [ ] Equipe treinada em segurança

## Resposta a Incidentes

### Plano de Resposta

1. **Detecção e Avaliação**
   - Monitoramento automático detecta anomalia
   - Equipe de segurança avalia severidade
   - Classificação: Baixa, Média, Alta, Crítica

2. **Contenção**
   - Isolamento do sistema afetado
   - Preservação de evidências
   - Comunicação com stakeholders

3. **Erradicação**
   - Identificação da causa raiz
   - Remoção da ameaça
   - Aplicação de patches/correções

4. **Recuperação**
   - Restauração de serviços
   - Monitoramento intensivo
   - Validação da segurança

5. **Lições Aprendidas**
   - Documentação do incidente
   - Melhoria dos processos
   - Atualização de controles

### Contatos de Emergência

```python
# core/utils/incident_response.py
EMERGENCY_CONTACTS = {
    'security_team': 'seguranca@sistema-aprender.com.br',
    'tech_lead': 'tech-lead@sistema-aprender.com.br',
    'management': 'diretoria@sistema-aprender.com.br',
}

INCIDENT_SEVERITY = {
    'CRITICAL': {
        'response_time': '15 minutes',
        'escalation': ['security_team', 'tech_lead', 'management'],
        'actions': ['immediate_isolation', 'preserve_evidence']
    },
    'HIGH': {
        'response_time': '1 hour',
        'escalation': ['security_team', 'tech_lead'],
        'actions': ['assess_impact', 'contain_threat']
    },
    'MEDIUM': {
        'response_time': '4 hours',
        'escalation': ['security_team'],
        'actions': ['monitor', 'investigate']
    },
    'LOW': {
        'response_time': '24 hours',
        'escalation': ['security_team'],
        'actions': ['log_review', 'routine_investigation']
    }
}
```

## Conclusão

A segurança do Sistema Aprender é uma responsabilidade compartilhada que requer:

- **Desenvolvimento Seguro**: Código que implementa controles de segurança desde o design
- **Operação Segura**: Configurações e procedimentos que mantêm o sistema protegido
- **Monitoramento Contínuo**: Detecção proativa de ameaças e anomalias
- **Resposta Rápida**: Capacidade de responder e recuperar-se de incidentes

Este guia deve ser revisado e atualizado regularmente conforme novas ameaças são identificadas e a tecnologia evolui.

Para dúvidas sobre segurança ou para reportar vulnerabilidades, contate: `seguranca@sistema-aprender.com.br`
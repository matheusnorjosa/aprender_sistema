# 🚀 OPERAÇÕES E DEPLOY COMPLETO - SISTEMA APRENDER

**Versão**: 2.0.0 Unificada
**Data**: 30 de Setembro de 2025
**Status**: ✅ Operações e Deploy Consolidados

---

## 📑 ÍNDICE

1. [Resumo Executivo](#resumo-executivo)
2. [Guia de Deploy](#guia-de-deploy)
3. [Processo de Releases](#processo-de-releases)
4. [Guia de Troubleshooting](#guia-de-troubleshooting)
5. [Arquiteturas de Deploy](#arquiteturas-de-deploy)
6. [Monitoramento e Manutenção](#monitoramento-e-manutenção)

---

## 🎯 RESUMO EXECUTIVO

Este documento consolida todos os guias de operações, deploy e troubleshooting do Sistema Aprender.

### Status Geral: ✅ **OPERAÇÕES E DEPLOY CONSOLIDADOS**

### Principais Características:
- ✅ **Guia de deploy** completo para todos os ambientes
- ✅ **Processo de releases** estruturado e automatizado
- ✅ **Guia de troubleshooting** abrangente
- ✅ **Arquiteturas de deploy** bem definidas
- ✅ **Monitoramento** e manutenção implementados

---

## 🚀 GUIA DE DEPLOY

### Pré-requisitos

#### Requisitos do Sistema
- **Python**: 3.11+ (recomendado 3.13)
- **Banco de Dados**: PostgreSQL 15+ ou SQLite (apenas dev)
- **Memória**: Mínimo 1GB RAM (2GB+ recomendado)
- **Armazenamento**: Mínimo 5GB de espaço em disco
- **Docker**: 24.0+ (para deploys containerizados)
- **Git**: Para deploy de código

#### Dependências Externas
- **Google Calendar API**: Para gestão de eventos
- **Google Sheets API**: Para importação de dados (opcional)
- **Servidor SMTP**: Para notificações
- **Redis**: Para cache (opcional, fallback para in-memory)

### Arquiteturas de Deploy

#### 1. Desenvolvimento (Local)
- **Banco de Dados**: SQLite
- **Ambiente**: `ENVIRONMENT=development`
- **Propósito**: Desenvolvimento e testes locais

#### 2. Staging
- **Banco de Dados**: PostgreSQL
- **Ambiente**: `ENVIRONMENT=staging`
- **Propósito**: Testes de integração e validação

#### 3. Produção
- **Banco de Dados**: PostgreSQL
- **Ambiente**: `ENVIRONMENT=production`
- **Propósito**: Sistema em produção

### Deploy por Ambiente

#### Deploy de Desenvolvimento
```bash
# 1. Clone do repositório
git clone https://github.com/matheusnorjosa/aprender_sistema.git
cd aprender_sistema

# 2. Configurar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com configurações locais

# 5. Aplicar migrações
python manage.py migrate

# 6. Criar superusuário
python manage.py createsuperuser

# 7. Popular dados iniciais
python manage.py populate_data

# 8. Iniciar servidor
python manage.py runserver
```

#### Deploy de Staging
```bash
# 1. Configurar servidor
sudo apt update
sudo apt install python3.13 python3.13-venv postgresql nginx

# 2. Configurar banco de dados
sudo -u postgres createdb aprender_staging
sudo -u postgres createuser aprender_user
sudo -u postgres psql -c "ALTER USER aprender_user PASSWORD 'senha_segura';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE aprender_staging TO aprender_user;"

# 3. Deploy da aplicação
git clone https://github.com/matheusnorjosa/aprender_sistema.git
cd aprender_sistema

python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Configurar variáveis de ambiente
export ENVIRONMENT=staging
export DATABASE_URL=postgresql://aprender_user:senha_segura@localhost/aprender_staging
export SECRET_KEY=chave_secreta_staging
export DEBUG=False

# 5. Aplicar migrações
python manage.py migrate

# 6. Coletar arquivos estáticos
python manage.py collectstatic --noinput

# 7. Configurar Gunicorn
pip install gunicorn
gunicorn --bind 0.0.0.0:8000 aprender_sistema.wsgi:application

# 8. Configurar Nginx
sudo nano /etc/nginx/sites-available/aprender_staging
```

#### Deploy de Produção
```bash
# 1. Configurar servidor
sudo apt update
sudo apt install python3.13 python3.13-venv postgresql nginx redis-server

# 2. Configurar banco de dados
sudo -u postgres createdb aprender_production
sudo -u postgres createuser aprender_user
sudo -u postgres psql -c "ALTER USER aprender_user PASSWORD 'senha_muito_segura';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE aprender_production TO aprender_user;"

# 3. Deploy da aplicação
git clone https://github.com/matheusnorjosa/aprender_sistema.git
cd aprender_sistema

python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Configurar variáveis de ambiente
export ENVIRONMENT=production
export DATABASE_URL=postgresql://aprender_user:senha_muito_segura@localhost/aprender_production
export SECRET_KEY=chave_secreta_producao
export DEBUG=False
export ALLOWED_HOSTS=dominio.com,www.dominio.com

# 5. Aplicar migrações
python manage.py migrate

# 6. Coletar arquivos estáticos
python manage.py collectstatic --noinput

# 7. Configurar Gunicorn
pip install gunicorn
gunicorn --bind 0.0.0.0:8000 aprender_sistema.wsgi:application

# 8. Configurar Nginx
sudo nano /etc/nginx/sites-available/aprender_production
```

### Deploy com Docker

#### Docker Compose para Produção
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://postgres:senha@db:5432/aprender_production
      - SECRET_KEY=chave_secreta_producao
      - DEBUG=False
    depends_on:
      - db
      - redis
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=aprender_production
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=senha
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - web
    restart: unless-stopped

volumes:
  postgres_data:
  static_volume:
  media_volume:
```

#### Deploy com Docker
```bash
# 1. Build das imagens
docker-compose -f docker-compose.prod.yml build

# 2. Iniciar serviços
docker-compose -f docker-compose.prod.yml up -d

# 3. Aplicar migrações
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate

# 4. Coletar arquivos estáticos
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput

# 5. Criar superusuário
docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

### Configuração de Nginx

#### Configuração para Produção
```nginx
# /etc/nginx/sites-available/aprender_production
server {
    listen 80;
    server_name dominio.com www.dominio.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name dominio.com www.dominio.com;

    ssl_certificate /etc/ssl/certs/dominio.com.crt;
    ssl_certificate_key /etc/ssl/private/dominio.com.key;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /app/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /app/media/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

---

## 🔄 PROCESSO DE RELEASES

### Visão Geral de Releases

#### Tipos de Release
- **Major Release** (X.0.0): Mudanças que quebram compatibilidade, novas funcionalidades principais
- **Minor Release** (X.Y.0): Novas funcionalidades, compatível com versões anteriores
- **Patch Release** (X.Y.Z): Correções de bugs, atualizações de segurança
- **Hotfix Release** (X.Y.Z-hotfix.N): Correções de emergência para produção

#### Cronograma de Releases
- **Major Releases**: Trimestral (a cada 3 meses)
- **Minor Releases**: Mensal ou quinzenal
- **Patch Releases**: Conforme necessário (correções de bugs, segurança)
- **Hotfix Releases**: Emergencial (dentro de 24-48 horas)

### Workflow de Release

#### 1. Fase de Planejamento

##### Reunião de Planejamento
- **Quando**: 2 semanas antes do release
- **Participantes**: Product Owner, Equipe de Desenvolvimento, QA, Operações
- **Resultados**: Escopo do release, cronograma, avaliação de riscos

##### Feature Freeze
- **Quando**: 1 semana antes do release
- **Ação**: Parar desenvolvimento de novas funcionalidades
- **Foco**: Correções de bugs e testes

#### 2. Fase de Desenvolvimento

##### Desenvolvimento de Features
```bash
# 1. Criar branch de feature
git checkout -b feature/nova-funcionalidade

# 2. Desenvolver funcionalidade
# ... código ...

# 3. Commits atômicos
git add .
git commit -m "feat: adiciona nova funcionalidade"

# 4. Push da branch
git push origin feature/nova-funcionalidade

# 5. Criar Pull Request
# ... via GitHub/GitLab ...
```

##### Code Review
- **Revisor**: Pelo menos 2 desenvolvedores
- **Critérios**: Funcionalidade, qualidade, testes, documentação
- **Aprovação**: Todos os revisores devem aprovar

#### 3. Fase de Testes

##### Testes Automatizados
```bash
# 1. Testes unitários
python manage.py test

# 2. Testes de integração
python manage.py test --settings=aprender_sistema.settings.test

# 3. Testes de performance
python manage.py test --settings=aprender_sistema.settings.performance

# 4. Testes de segurança
python manage.py test --settings=aprender_sistema.settings.security
```

##### Testes Manuais
- **Testes de funcionalidade**: Verificar se todas as funcionalidades funcionam
- **Testes de regressão**: Verificar se não quebrou funcionalidades existentes
- **Testes de usabilidade**: Verificar se a interface está intuitiva
- **Testes de performance**: Verificar se não degradou performance

#### 4. Fase de Deploy

##### Deploy para Staging
```bash
# 1. Merge para develop
git checkout develop
git merge feature/nova-funcionalidade
git push origin develop

# 2. Deploy automático para staging
# ... via CI/CD pipeline ...

# 3. Testes de aceitação
# ... testes manuais em staging ...
```

##### Deploy para Produção
```bash
# 1. Merge para main
git checkout main
git merge develop
git push origin main

# 2. Criar tag de release
git tag -a v1.2.0 -m "Release v1.2.0"
git push origin v1.2.0

# 3. Deploy automático para produção
# ... via CI/CD pipeline ...

# 4. Verificação pós-deploy
# ... testes de smoke em produção ...
```

### Automação de Releases

#### CI/CD Pipeline
```yaml
# .github/workflows/release.yml
name: Release Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Run tests
        run: |
          python manage.py test
      
      - name: Run linting
        run: |
          black --check .
          flake8 .
          isort --check-only .

  deploy-staging:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to staging
        run: |
          # Deploy para staging
          echo "Deploying to staging..."

  deploy-production:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to production
        run: |
          # Deploy para produção
          echo "Deploying to production..."
```

#### Scripts de Deploy
```bash
#!/bin/bash
# scripts/deploy.sh

set -e

ENVIRONMENT=$1
VERSION=$2

if [ -z "$ENVIRONMENT" ] || [ -z "$VERSION" ]; then
    echo "Usage: $0 <environment> <version>"
    echo "Example: $0 production v1.2.0"
    exit 1
fi

echo "🚀 Deploying version $VERSION to $ENVIRONMENT..."

# 1. Backup do banco de dados
echo "📦 Creating database backup..."
python manage.py dumpdata --natural-foreign --natural-primary > backup_$(date +%Y%m%d_%H%M%S).json

# 2. Aplicar migrações
echo "🔄 Applying migrations..."
python manage.py migrate

# 3. Coletar arquivos estáticos
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

# 4. Reiniciar serviços
echo "🔄 Restarting services..."
sudo systemctl restart gunicorn
sudo systemctl restart nginx

# 5. Verificar saúde do sistema
echo "🏥 Checking system health..."
curl -f http://localhost:8000/health/ || exit 1

echo "✅ Deploy completed successfully!"
```

### Rollback de Releases

#### Rollback Automático
```bash
#!/bin/bash
# scripts/rollback.sh

set -e

ENVIRONMENT=$1
VERSION=$2

if [ -z "$ENVIRONMENT" ] || [ -z "$VERSION" ]; then
    echo "Usage: $0 <environment> <version>"
    echo "Example: $0 production v1.1.0"
    exit 1
fi

echo "🔄 Rolling back to version $VERSION in $ENVIRONMENT..."

# 1. Restaurar código
echo "📦 Restoring code..."
git checkout $VERSION

# 2. Restaurar banco de dados
echo "🗄️ Restoring database..."
python manage.py loaddata backup_$(date +%Y%m%d_%H%M%S).json

# 3. Reiniciar serviços
echo "🔄 Restarting services..."
sudo systemctl restart gunicorn
sudo systemctl restart nginx

# 4. Verificar saúde do sistema
echo "🏥 Checking system health..."
curl -f http://localhost:8000/health/ || exit 1

echo "✅ Rollback completed successfully!"
```

---

## 🔧 GUIA DE TROUBLESHOOTING

### Resposta de Emergência

#### Sistema Completamente Fora do Ar
```bash
# 1. Verificação rápida de saúde
curl -f http://localhost:8000/health/ || echo "Sistema completamente fora do ar"

# 2. Verificar todos os serviços
make system-status

# 3. Revisar mudanças recentes
git log --oneline -10

# 4. Verificar recursos do sistema
make resource-check

# 5. Reinicialização de emergência
make emergency-restart
```

#### Degradação Crítica de Performance
```bash
# 1. Verificar carga do sistema
top
htop

# 2. Verificar uso de memória
free -h
ps aux --sort=-%mem | head -10

# 3. Verificar uso de disco
df -h
du -sh /var/log/*

# 4. Verificar logs de erro
tail -f /var/log/nginx/error.log
tail -f /var/log/gunicorn/error.log

# 5. Verificar conexões de banco
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity;"
```

### Problemas Comuns

#### Problema 1: Erro 500 - Internal Server Error
```bash
# 1. Verificar logs do Django
tail -f /var/log/django/error.log

# 2. Verificar logs do Gunicorn
tail -f /var/log/gunicorn/error.log

# 3. Verificar logs do Nginx
tail -f /var/log/nginx/error.log

# 4. Verificar configuração do Django
python manage.py check

# 5. Verificar migrações
python manage.py showmigrations
```

#### Problema 2: Erro de Conexão com Banco de Dados
```bash
# 1. Verificar se PostgreSQL está rodando
sudo systemctl status postgresql

# 2. Verificar conexões
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity;"

# 3. Verificar configuração
sudo -u postgres psql -c "SHOW max_connections;"

# 4. Verificar logs do PostgreSQL
tail -f /var/log/postgresql/postgresql-15-main.log

# 5. Reiniciar PostgreSQL
sudo systemctl restart postgresql
```

#### Problema 3: Problemas de Performance
```bash
# 1. Verificar queries lentas
python manage.py shell -c "
from django.db import connection
from django.conf import settings
if settings.DEBUG:
    for query in connection.queries:
        if float(query['time']) > 0.1:
            print(f'Slow query: {query[\"time\"]}s - {query[\"sql\"]}')
"

# 2. Verificar uso de cache
python manage.py shell -c "
from django.core.cache import cache
print('Cache stats:', cache.get_stats())
"

# 3. Verificar índices do banco
sudo -u postgres psql -d aprender_production -c "
SELECT schemaname, tablename, indexname, indexdef 
FROM pg_indexes 
WHERE schemaname = 'public';
"

# 4. Analisar performance
python manage.py shell -c "
from django.test.utils import override_settings
from django.db import connection
with override_settings(DEBUG=True):
    # Executar operação
    from core.models import Usuario
    usuarios = Usuario.objects.all()
    print(f'Queries: {len(connection.queries)}')
"
```

#### Problema 4: Problemas de Memória
```bash
# 1. Verificar uso de memória
free -h
ps aux --sort=-%mem | head -10

# 2. Verificar processos Python
ps aux | grep python

# 3. Verificar vazamentos de memória
python manage.py shell -c "
import gc
import sys
print('Objects before GC:', len(gc.get_objects()))
gc.collect()
print('Objects after GC:', len(gc.get_objects()))
"

# 4. Reiniciar Gunicorn
sudo systemctl restart gunicorn

# 5. Verificar configuração do Gunicorn
cat /etc/systemd/system/gunicorn.service
```

### Monitoramento e Alertas

#### Configuração de Monitoramento
```python
# core/monitoring.py
import logging
import time
from django.core.cache import cache
from django.db import connection

logger = logging.getLogger(__name__)

class SystemMonitor:
    def check_database_connection(self):
        """Verifica conexão com banco de dados"""
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def check_cache_connection(self):
        """Verifica conexão com cache"""
        try:
            cache.set('health_check', 'ok', 10)
            result = cache.get('health_check')
            return result == 'ok'
        except Exception as e:
            logger.error(f"Cache connection failed: {e}")
            return False
    
    def check_disk_space(self):
        """Verifica espaço em disco"""
        import shutil
        try:
            total, used, free = shutil.disk_usage('/')
            free_percent = (free / total) * 100
            return free_percent > 10  # Pelo menos 10% livre
        except Exception as e:
            logger.error(f"Disk space check failed: {e}")
            return False
    
    def check_memory_usage(self):
        """Verifica uso de memória"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return memory.percent < 90  # Menos de 90% de uso
        except Exception as e:
            logger.error(f"Memory check failed: {e}")
            return False
    
    def run_health_check(self):
        """Executa verificação completa de saúde"""
        checks = {
            'database': self.check_database_connection(),
            'cache': self.check_cache_connection(),
            'disk_space': self.check_disk_space(),
            'memory': self.check_memory_usage()
        }
        
        all_healthy = all(checks.values())
        
        if not all_healthy:
            logger.warning(f"Health check failed: {checks}")
        
        return all_healthy, checks
```

#### Endpoint de Health Check
```python
# core/views/health_views.py
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from core.monitoring import SystemMonitor

@require_http_methods(["GET"])
def health_check(request):
    """Endpoint de verificação de saúde"""
    monitor = SystemMonitor()
    healthy, checks = monitor.run_health_check()
    
    status_code = 200 if healthy else 503
    
    return JsonResponse({
        'status': 'healthy' if healthy else 'unhealthy',
        'checks': checks,
        'timestamp': time.time()
    }, status=status_code)
```

### Logs e Auditoria

#### Configuração de Logs
```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/django/django.log',
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': '/var/log/django/error.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'core': {
            'handlers': ['file', 'error_file', 'console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
```

#### Sistema de Auditoria
```python
# core/models.py
class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100, null=True, blank=True)
    data = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['model', 'timestamp']),
        ]
```

---

## 📊 MONITORAMENTO E MANUTENÇÃO

### Métricas de Sistema

#### Métricas de Performance
```python
# core/metrics.py
import time
from django.core.cache import cache
from django.db import connection

class PerformanceMetrics:
    def get_response_time(self):
        """Obtém tempo de resposta médio"""
        return cache.get('avg_response_time', 0)
    
    def get_database_queries(self):
        """Obtém número de queries do banco"""
        return len(connection.queries)
    
    def get_cache_hit_rate(self):
        """Obtém taxa de hit do cache"""
        stats = cache.get_stats()
        if stats:
            hits = stats.get('hits', 0)
            misses = stats.get('misses', 0)
            total = hits + misses
            return (hits / total * 100) if total > 0 else 0
        return 0
    
    def get_memory_usage(self):
        """Obtém uso de memória"""
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024  # MB
```

#### Dashboard de Monitoramento
```python
# core/views/monitoring_views.py
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from core.metrics import PerformanceMetrics

@staff_member_required
def monitoring_dashboard(request):
    """Dashboard de monitoramento"""
    metrics = PerformanceMetrics()
    
    data = {
        'response_time': metrics.get_response_time(),
        'database_queries': metrics.get_database_queries(),
        'cache_hit_rate': metrics.get_cache_hit_rate(),
        'memory_usage': metrics.get_memory_usage(),
        'timestamp': time.time()
    }
    
    return JsonResponse(data)
```

### Manutenção Preventiva

#### Limpeza de Logs
```bash
#!/bin/bash
# scripts/cleanup_logs.sh

# Limpar logs antigos (mais de 30 dias)
find /var/log/django -name "*.log" -mtime +30 -delete
find /var/log/nginx -name "*.log" -mtime +30 -delete
find /var/log/gunicorn -name "*.log" -mtime +30 -delete

# Comprimir logs antigos (mais de 7 dias)
find /var/log/django -name "*.log" -mtime +7 -exec gzip {} \;
find /var/log/nginx -name "*.log" -mtime +7 -exec gzip {} \;
find /var/log/gunicorn -name "*.log" -mtime +7 -exec gzip {} \;

echo "✅ Log cleanup completed"
```

#### Limpeza de Cache
```bash
#!/bin/bash
# scripts/cleanup_cache.sh

# Limpar cache do Django
python manage.py shell -c "
from django.core.cache import cache
cache.clear()
print('Cache cleared')
"

# Limpar cache do Redis
redis-cli FLUSHALL

echo "✅ Cache cleanup completed"
```

#### Backup Automático
```bash
#!/bin/bash
# scripts/backup.sh

BACKUP_DIR="/var/backups/aprender"
DATE=$(date +%Y%m%d_%H%M%S)

# Criar diretório de backup
mkdir -p $BACKUP_DIR

# Backup do banco de dados
pg_dump -h localhost -U aprender_user -d aprender_production > $BACKUP_DIR/db_backup_$DATE.sql

# Backup dos arquivos de mídia
tar -czf $BACKUP_DIR/media_backup_$DATE.tar.gz /app/media/

# Backup dos arquivos estáticos
tar -czf $BACKUP_DIR/static_backup_$DATE.tar.gz /app/staticfiles/

# Remover backups antigos (mais de 30 dias)
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "✅ Backup completed: $DATE"
```

### Alertas e Notificações

#### Sistema de Alertas
```python
# core/alerts.py
import smtplib
from email.mime.text import MIMEText
from django.conf import settings

class AlertSystem:
    def send_email_alert(self, subject, message, recipients):
        """Envia alerta por email"""
        try:
            msg = MIMEText(message)
            msg['Subject'] = subject
            msg['From'] = settings.EMAIL_HOST_USER
            msg['To'] = ', '.join(recipients)
            
            server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
            server.starttls()
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            server.send_message(msg)
            server.quit()
            
            return True
        except Exception as e:
            print(f"Failed to send email alert: {e}")
            return False
    
    def send_slack_alert(self, message, webhook_url):
        """Envia alerta para Slack"""
        import requests
        
        try:
            payload = {'text': message}
            response = requests.post(webhook_url, json=payload)
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to send Slack alert: {e}")
            return False
```

---

## 📝 CHANGELOG

### Versão 2.0.0 Unificada (30/09/2025)
- ✅ Unificação de 3 documentos de operações
- ✅ Consolidação de guias de deploy
- ✅ Processo de releases integrado
- ✅ Troubleshooting abrangente

### Versão 1.0.0 (15/09/2025)
- ✅ Documentos individuais criados
- ✅ Guias de deploy implementados
- ✅ Processo de releases estabelecido

---

**🚀 OPERAÇÕES E DEPLOY COMPLETO - SISTEMA APRENDER**

*Documento unificado em: 2025-09-30*
*Status: ✅ OPERAÇÕES E DEPLOY CONSOLIDADOS*

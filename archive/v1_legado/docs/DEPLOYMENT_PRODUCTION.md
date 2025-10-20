# GUIA DE DEPLOYMENT EM PRODUÇÃO - SISTEMA APRENDER

## 🚀 Configurações de Produção

### 1. Configurar Variáveis de Ambiente

Antes do deployment, configure as seguintes variáveis de ambiente:

```bash
# Configurações críticas
export SECRET_KEY_PRODUCTION="sua-chave-super-secreta-de-50-ou-mais-caracteres-aqui"
export ALLOWED_HOSTS_PRODUCTION="seudominio.com,www.seudominio.com,ip-do-servidor"

# Database PostgreSQL
export DB_NAME_PRODUCTION="aprender_sistema_prod"
export DB_USER_PRODUCTION="aprender_user"
export DB_PASSWORD_PRODUCTION="senha-super-forte-aqui"
export DB_HOST_PRODUCTION="localhost"
export DB_PORT_PRODUCTION="5432"

# Email (opcional)
export EMAIL_HOST="smtp.seudominio.com"
export EMAIL_HOST_USER="noreply@seudominio.com"
export EMAIL_HOST_PASSWORD="senha-do-email"
export DEFAULT_FROM_EMAIL="Sistema Aprender <noreply@seudominio.com>"

# Cache Redis (opcional)
export REDIS_URL="redis://127.0.0.1:6379/1"

# Features
export FEATURE_GOOGLE_SYNC_PROD="1"
```

### 2. Usar Settings de Produção

```bash
# Definir o módulo de settings de produção
export DJANGO_SETTINGS_MODULE="aprender_sistema.settings_production"

# Ou no docker-compose.yml:
environment:
  DJANGO_SETTINGS_MODULE: "aprender_sistema.settings_production"
```

### 3. Preparar Banco PostgreSQL

```sql
-- Criar usuário e banco
CREATE USER aprender_user WITH PASSWORD 'senha-super-forte-aqui';
CREATE DATABASE aprender_sistema_prod OWNER aprender_user;
GRANT ALL PRIVILEGES ON DATABASE aprender_sistema_prod TO aprender_user;
```

### 4. Aplicar Migrações

```bash
python manage.py migrate --settings=aprender_sistema.settings_production
python manage.py collectstatic --settings=aprender_sistema.settings_production --noinput
```

### 5. Criar Superusuário

```bash
python manage.py createsuperuser --settings=aprender_sistema.settings_production
```

## 🔐 Checklist de Segurança

- [ ] ✅ DEBUG=False
- [ ] ✅ SECRET_KEY robusta (50+ chars)
- [ ] ✅ SECURE_SSL_REDIRECT=True
- [ ] ✅ SESSION_COOKIE_SECURE=True
- [ ] ✅ CSRF_COOKIE_SECURE=True
- [ ] ✅ ALLOWED_HOSTS configurado corretamente
- [ ] ✅ PostgreSQL com SSL
- [ ] ✅ Firewall configurado
- [ ] ✅ Backup automático configurado

## 🐳 Docker Compose Produção

```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    container_name: aprender_db_prod
    environment:
      POSTGRES_DB: aprender_sistema_prod
      POSTGRES_USER: aprender_user
      POSTGRES_PASSWORD: ${DB_PASSWORD_PRODUCTION}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data_prod:/var/lib/postgresql/data
      - ./backup:/backup
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: aprender_redis_prod
    ports:
      - "6379:6379"
    restart: unless-stopped

  web:
    build: .
    container_name: aprender_web_prod
    environment:
      DJANGO_SETTINGS_MODULE: "aprender_sistema.settings_production"
      SECRET_KEY_PRODUCTION: ${SECRET_KEY_PRODUCTION}
      ALLOWED_HOSTS_PRODUCTION: ${ALLOWED_HOSTS_PRODUCTION}
      DB_PASSWORD_PRODUCTION: ${DB_PASSWORD_PRODUCTION}
      FEATURE_GOOGLE_SYNC_PROD: "1"
    volumes:
      - ./staticfiles:/app/staticfiles
      - ./media:/app/media
      - ./logs:/app/logs
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis
    restart: unless-stopped
    command: >
      sh -c "python manage.py migrate &&
             python manage.py collectstatic --noinput &&
             gunicorn aprender_sistema.wsgi:application --bind 0.0.0.0:8000"

volumes:
  postgres_data_prod:
```

## 🔄 Processo de Deploy

1. **Backup do banco atual**
2. **Testar settings de produção localmente**
3. **Deploy do código**
4. **Aplicar migrações**
5. **Testar funcionalidades críticas**
6. **Monitorar logs**

## 📊 Monitoramento

Verificar regularmente:
- Logs de erro: `/app/logs/error.log`
- Performance do banco
- Uso de memória
- Disponibilidade do serviço
- Backups automáticos

## 🆘 Rollback

Em caso de problemas:

```bash
# Voltar para versão anterior
git checkout versao-anterior
docker-compose down
docker-compose up -d

# Restaurar backup do banco se necessário
psql -U aprender_user -d aprender_sistema_prod < backup.sql
```
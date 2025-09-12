# 🚀 Deployment Guide - Sistema Aprender

This guide provides comprehensive instructions for deploying the Sistema Aprender to different environments.

## 📋 Prerequisites

### System Requirements
- **Python**: 3.11+ (recommended 3.13)
- **Database**: PostgreSQL 15+ or SQLite (dev only)
- **Memory**: Minimum 1GB RAM (2GB+ recommended)
- **Storage**: Minimum 5GB available disk space
- **Docker**: 24.0+ (for containerized deployments)
- **Git**: For code deployment

### External Dependencies
- **Google Calendar API**: For event management
- **Google Sheets API**: For data imports (optional)
- **Email SMTP Server**: For notifications
- **Redis**: For caching (optional, falls back to in-memory)

## 🏗️ Deployment Architectures

### 1. Development (Local)
- **Database**: SQLite
- **Environment**: `ENVIRONMENT=development`
- **Purpose**: Local development and testing

### 2. Staging
- **Database**: PostgreSQL
- **Environment**: `ENVIRONMENT=staging`
- **Purpose**: Pre-production testing and validation

### 3. Production
- **Database**: PostgreSQL with backup
- **Environment**: `ENVIRONMENT=production`
- **Purpose**: Live system for end users

---

## 🐳 Docker Deployment (Recommended)

### Quick Start
```bash
# Clone repository
git clone https://github.com/your-org/aprender_sistema.git
cd aprender_sistema

# Copy environment template
cp .env.example .env

# Edit environment variables
nano .env

# Start production stack
make docker-prod-up
```

### Development Environment
```bash
# Start development stack
make docker-dev-up

# View logs
make docker-logs

# Access shell
make docker-shell

# Stop environment
make docker-down
```

### Production Environment
```bash
# Build production images
make docker-prod-build

# Deploy to production
make docker-prod-deploy

# Monitor health
make docker-health

# View production logs
make docker-prod-logs
```

## 📦 Manual Deployment

### 1. Environment Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

### 3. Database Setup
```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Load initial data (optional)
python manage.py loaddata initial_data.json
```

### 4. Static Files
```bash
# Collect static files
python manage.py collectstatic --noinput
```

### 5. Start Application
```bash
# Development
python manage.py runserver

# Production (use proper WSGI server)
gunicorn aprender_sistema.wsgi:application --bind 0.0.0.0:8000
```

---

## ⚙️ Environment Configuration

### Required Environment Variables

#### Database Configuration
```bash
# PostgreSQL (recommended for staging/production)
DATABASE_URL=postgresql://user:password@host:port/database

# Or individual components
DB_NAME=aprender_sistema
DB_USER=postgres
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432

# SQLite (development only)
# Leave DATABASE_URL empty to use SQLite
```

#### Application Settings
```bash
# Environment type
ENVIRONMENT=production  # development|staging|production

# Security
SECRET_KEY=your-super-secret-key-here
DEBUG=False  # Never True in production

# Allowed hosts (comma-separated)
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Timezone
TIME_ZONE=America/Fortaleza
```

#### Google APIs (Optional)
```bash
GOOGLE_CALENDAR_API_KEY=your_api_key
GOOGLE_SHEETS_API_KEY=your_api_key
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
```

#### Email Configuration
```bash
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@domain.com
EMAIL_HOST_PASSWORD=your_app_password
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
```

#### Cache Configuration (Optional)
```bash
REDIS_URL=redis://localhost:6379/0
# Leave empty to use in-memory cache
```

### Environment Templates

#### Development (.env.development)
```bash
ENVIRONMENT=development
DEBUG=True
SECRET_KEY=dev-key-not-for-production
ALLOWED_HOSTS=localhost,127.0.0.1
# Database will use SQLite automatically
```

#### Staging (.env.staging)
```bash
ENVIRONMENT=staging
DEBUG=False
SECRET_KEY=staging-secret-key
ALLOWED_HOSTS=staging.yourdomain.com
DATABASE_URL=postgresql://user:pass@staging-db:5432/aprender_staging
```

#### Production (.env.production)
```bash
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=super-secure-production-key
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://user:pass@prod-db:5432/aprender_prod
```

---

## 🔧 Server Configuration

### Nginx Configuration
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;
    
    # SSL configuration
    ssl_certificate /path/to/ssl/cert.pem;
    ssl_certificate_key /path/to/ssl/private.key;
    
    # Static files
    location /static/ {
        alias /path/to/aprender_sistema/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, no-transform";
    }
    
    location /media/ {
        alias /path/to/aprender_sistema/media/;
        expires 1y;
        add_header Cache-Control "public, no-transform";
    }
    
    # Application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Systemd Service (Ubuntu/Debian)
```ini
# /etc/systemd/system/aprender-sistema.service
[Unit]
Description=Sistema Aprender Django Application
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/var/www/aprender_sistema
Environment=PATH=/var/www/aprender_sistema/venv/bin
ExecStart=/var/www/aprender_sistema/venv/bin/gunicorn \
    --workers 3 \
    --bind 127.0.0.1:8000 \
    --timeout 120 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    aprender_sistema.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

---

## 📊 Health Checks & Monitoring

### Health Check Endpoints
- **Basic Health**: `GET /health/` - Returns 200 OK if system is operational
- **Detailed Health**: `GET /health/detailed/` - Comprehensive system status
- **Readiness Probe**: `GET /health/ready/` - Kubernetes readiness check
- **Liveness Probe**: `GET /health/live/` - Kubernetes liveness check
- **Metrics**: `GET /health/metrics/` - System metrics for monitoring

### Manual Health Check
```bash
# Quick health check
python manage.py health_check

# Detailed health check with JSON output
python manage.py health_check --format=json

# Check specific components
python manage.py health_check --check-db --check-cache
```

### Monitoring Integration
```bash
# Prometheus metrics (if configured)
curl http://localhost:8000/health/metrics/

# Basic status check
curl -f http://localhost:8000/health/ || echo "System down"
```

---

## 🚀 Deployment Strategies

### Blue-Green Deployment
```bash
# 1. Deploy to staging environment
make deploy-staging

# 2. Run health checks and tests
make test-staging

# 3. Switch traffic to new version
make promote-staging-to-production

# 4. Monitor and rollback if needed
make rollback-production
```

### Rolling Deployment
```bash
# 1. Build new version
make build-production

# 2. Deploy with zero downtime
make deploy-rolling

# 3. Monitor deployment
make monitor-deployment
```

### Automated Deployment (CI/CD)
```yaml
# Example GitHub Actions workflow
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to production
        run: |
          make deploy-production
          make health-check-production
```

---

## 🔄 Database Migrations

### Safe Migration Process
```bash
# 1. Backup database
make backup-db

# 2. Run migrations in staging
ENVIRONMENT=staging python manage.py migrate

# 3. Test staging environment
make test-staging

# 4. Run migrations in production
ENVIRONMENT=production python manage.py migrate

# 5. Verify production health
make health-check-production
```

### Migration Rollback
```bash
# List migrations
python manage.py showmigrations

# Rollback to specific migration
python manage.py migrate app_name 0001_initial

# Zero-downtime rollback strategy
make rollback-with-migration app_name 0001
```

---

## 💾 Backup & Recovery

### Automated Backup
```bash
# Full system backup
make backup-full

# Database only backup
make backup-db

# Media files backup
make backup-media

# Configuration backup
make backup-config
```

### Backup Schedule (Crontab)
```bash
# Daily database backup at 2 AM
0 2 * * * /path/to/aprender_sistema/scripts/backup.sh --db-only

# Weekly full backup on Sundays at 3 AM
0 3 * * 0 /path/to/aprender_sistema/scripts/backup.sh --full

# Monthly archive on 1st day at 4 AM
0 4 1 * * /path/to/aprender_sistema/scripts/backup.sh --archive
```

### Recovery Process
```bash
# Restore from latest backup
make restore-latest

# Restore from specific backup
make restore-backup backup_20250911_020000

# Restore database only
make restore-db backup_20250911_020000
```

---

## 🔍 Troubleshooting

### Common Issues

#### Application Won't Start
```bash
# Check environment variables
make check-env

# Verify database connection
python manage.py dbshell

# Check migrations
python manage.py showmigrations --plan

# View detailed logs
make logs-detailed
```

#### Performance Issues
```bash
# Check system resources
make system-stats

# Analyze slow queries
python manage.py slow_queries

# Profile memory usage
make memory-profile

# Check health status
curl -f http://localhost:8000/health/detailed/
```

#### Database Connection Errors
```bash
# Test database connection
python manage.py dbshell

# Check database logs
make db-logs

# Verify credentials
make check-db-config

# Reset database connection pool
make reset-db-pool
```

### Log Locations
- **Application Logs**: `/var/log/aprender_sistema/`
- **Database Logs**: `/var/log/postgresql/`
- **Nginx Logs**: `/var/log/nginx/`
- **Docker Logs**: `docker-compose logs`

### Emergency Procedures

#### System Recovery
```bash
# 1. Check system status
make system-status

# 2. Stop all services
make stop-all

# 3. Restore from backup
make emergency-restore

# 4. Start services
make start-all

# 5. Verify system health
make health-check-all
```

#### Database Recovery
```bash
# 1. Stop application
make stop-app

# 2. Backup current state
make emergency-backup

# 3. Restore database
make restore-db-emergency

# 4. Run health checks
make db-health-check

# 5. Start application
make start-app
```

---

## 🛡️ Security Considerations

### SSL/TLS Configuration
- Use Let's Encrypt for free SSL certificates
- Configure strong SSL ciphers
- Enable HSTS headers
- Implement certificate renewal automation

### Firewall Rules
```bash
# Allow HTTP/HTTPS
ufw allow 80
ufw allow 443

# Allow SSH (with custom port recommended)
ufw allow 22

# Allow database (internal only)
ufw allow from 10.0.0.0/8 to any port 5432

# Enable firewall
ufw enable
```

### Access Control
- Use strong passwords for database and admin accounts
- Implement SSH key authentication
- Restrict database access to application servers only
- Regular security updates

---

## 📈 Performance Optimization

### Database Optimization
```python
# settings.py optimizations
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'OPTIONS': {
            'MAX_CONNS': 20,
            'conn_max_age': 300,
        }
    }
}
```

### Caching Strategy
```python
# Enable Redis caching
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

### Static Files Optimization
```bash
# Enable gzip compression
python manage.py compress

# Optimize images
make optimize-images

# Set proper cache headers
make configure-static-cache
```

---

## 🔄 Maintenance

### Regular Maintenance Tasks
```bash
# Weekly maintenance
make maintenance-weekly

# Monthly maintenance  
make maintenance-monthly

# Update dependencies
make update-dependencies

# Clean up old logs
make cleanup-logs

# Optimize database
make optimize-database
```

### System Updates
```bash
# Update system packages
make update-system

# Update Python dependencies
make update-python-deps

# Update Docker images
make update-docker-images

# Security updates only
make security-updates
```

---

## 📞 Support & Resources

### Documentation
- [Django Documentation](https://docs.djangoproject.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Docker Documentation](https://docs.docker.com/)
- [Nginx Documentation](https://nginx.org/en/docs/)

### Monitoring & Alerting
- Health check endpoints for uptime monitoring
- Database monitoring with PostgreSQL metrics
- Application performance monitoring
- Log aggregation and analysis

### Emergency Contacts
- **System Administrator**: admin@yourdomain.com
- **Database Administrator**: dba@yourdomain.com
- **Development Team**: dev@yourdomain.com

---

## 📝 Deployment Checklist

### Pre-Deployment
- [ ] Environment variables configured
- [ ] Database backup completed
- [ ] SSL certificates valid
- [ ] Health checks passing
- [ ] Tests passing in staging
- [ ] Performance benchmarks met

### Deployment
- [ ] Code deployed successfully
- [ ] Database migrations applied
- [ ] Static files collected
- [ ] Services restarted
- [ ] Health checks passing
- [ ] Rollback plan ready

### Post-Deployment
- [ ] System monitoring active
- [ ] User acceptance testing completed
- [ ] Performance metrics normal
- [ ] Error rates within acceptable limits
- [ ] Backup verification completed
- [ ] Documentation updated

---

*Deployment guide created during repository cleanup - Phase 4*  
*Date: 2025-09-11*  
*Version: 1.0*
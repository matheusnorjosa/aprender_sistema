#!/bin/bash
# ================================================================
# AS v2 — Docker Entrypoint Script
# ================================================================
# Executa antes de iniciar o serviço principal
# ================================================================

set -e  # Exit on error

# ================================================================
# Cores para output
# ================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ================================================================
# Funções auxiliares
# ================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ================================================================
# Aguardar PostgreSQL ficar pronto
# ================================================================

log_info "Aguardando PostgreSQL..."

until pg_isready -h ${DB_HOST:-db} -p ${DB_PORT:-5432} -U ${DB_USER:-aprender_user}; do
    log_warning "PostgreSQL indisponível - aguardando..."
    sleep 2
done

log_success "PostgreSQL disponível!"

# ================================================================
# Aguardar Redis ficar pronto
# ================================================================

log_info "Aguardando Redis..."

until redis-cli -h ${REDIS_HOST:-redis} -p ${REDIS_PORT:-6379} ping | grep -q PONG; do
    log_warning "Redis indisponível - aguardando..."
    sleep 2
done

log_success "Redis disponível!"

# ================================================================
# Executar migrations (apenas no serviço web)
# ================================================================

if [ "$RUN_MIGRATIONS" = "1" ]; then
    log_info "Executando migrations..."
    python manage.py migrate --noinput

    log_success "Migrations aplicadas com sucesso!"
fi

# ================================================================
# Coletar arquivos estáticos (apenas no serviço web)
# ================================================================

if [ "$COLLECT_STATIC" = "1" ]; then
    log_info "Coletando arquivos estáticos..."
    python manage.py collectstatic --noinput --clear

    log_success "Arquivos estáticos coletados!"
fi

# ================================================================
# Criar superuser (apenas em desenvolvimento)
# ================================================================

if [ "$CREATE_SUPERUSER" = "1" ]; then
    log_info "Criando superuser..."

    python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@aprender.com.br', 'admin123')
    print('Superuser criado: admin / admin123')
else:
    print('Superuser já existe')
EOF

    log_success "Superuser verificado!"
fi

# ================================================================
# Executar comando principal
# ================================================================

log_info "Iniciando aplicação..."
log_info "Comando: $@"

exec "$@"

#!/bin/bash
# ===========================================
# DOCKER RUN WRAPPER - APRENDER SISTEMA
# ===========================================
# Script wrapper para executar comandos no container Docker
# Centraliza todos os comandos de desenvolvimento
#
# Uso:
#   ./scripts/docker-run.sh python manage.py runserver
#   ./scripts/docker-run.sh python manage.py test
#   ./scripts/docker-run.sh pre-commit run --all-files
#

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funções utilitárias
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

# Verificar se Docker está rodando
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker não está rodando. Inicie o Docker primeiro."
        exit 1
    fi
}

# Verificar se os containers estão rodando
check_containers() {
    if ! docker-compose ps | grep -q "aprender_web.*Up"; then
        log_warning "Container web não está rodando. Iniciando containers..."
        docker-compose up -d --build
        log_info "Aguardando containers iniciarem..."
        sleep 10
    fi
}

# Função principal
main() {
    log_info "=== Docker Run Wrapper - Aprender Sistema ==="

    # Verificações iniciais
    check_docker

    # Se não há argumentos, mostrar help
    if [ $# -eq 0 ]; then
        echo "Uso: $0 <comando> [argumentos...]"
        echo ""
        echo "Exemplos:"
        echo "  $0 python manage.py runserver"
        echo "  $0 python manage.py test"
        echo "  $0 python manage.py migrate"
        echo "  $0 pre-commit run --all-files"
        echo "  $0 black ."
        echo "  $0 isort ."
        echo "  $0 flake8 ."
        echo "  $0 bash  # Para shell interativo"
        exit 0
    fi

    # Verificar containers
    check_containers

    # Executar comando no container
    log_info "Executando: $*"

    # Casos especiais para comandos interativos
    if [[ "$1" == "bash" || "$1" == "shell" || "$1" == "sh" ]]; then
        log_info "Iniciando shell interativo..."
        docker-compose exec web bash
    elif [[ "$1" == "python" && "$2" == "manage.py" && "$3" == "shell" ]]; then
        log_info "Iniciando Django shell..."
        docker-compose exec web python manage.py shell
    else
        # Comando padrão
        docker-compose exec web "$@"
    fi

    exit_code=$?

    if [ $exit_code -eq 0 ]; then
        log_success "Comando executado com sucesso"
    else
        log_error "Comando falhou com código de saída: $exit_code"
    fi

    exit $exit_code
}

# Executar função principal com todos os argumentos
main "$@"
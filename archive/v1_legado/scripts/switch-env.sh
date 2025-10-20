#!/bin/bash
# ===========================================
# SCRIPT ALTERNÂNCIA DE AMBIENTE
# ===========================================
# Alterna entre ambiente de produção (main) e desenvolvimento (develop)

set -e

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Função para mostrar uso
show_usage() {
    echo "Uso: $0 [main|develop]"
    echo ""
    echo "Ambientes disponíveis:"
    echo "  main     - Ambiente de Produção (branch: main)"
    echo "  develop  - Ambiente de Desenvolvimento (branch: develop)"
    echo ""
    echo "Exemplos:"
    echo "  $0 main      # Alternar para produção"
    echo "  $0 develop   # Alternar para desenvolvimento"
    echo "  $0           # Mostrar ambiente atual"
}

# Função para mostrar ambiente atual
show_current_env() {
    if [ -f ".env" ]; then
        CURRENT_BRANCH=$(grep "CURRENT_BRANCH=" .env | cut -d'=' -f2 || echo "unknown")
        echo -e "${BLUE}Ambiente atual: ${GREEN}$CURRENT_BRANCH${NC}"
    else
        echo -e "${YELLOW}Nenhum ambiente configurado${NC}"
    fi
}

# Função para alternar ambiente
switch_environment() {
    local target_branch="$1"

    echo -e "${BLUE}Alternando para ambiente: ${GREEN}$target_branch${NC}"

    # Verificar se arquivo de configuração existe
    if [ ! -f ".env.$target_branch" ]; then
        echo -e "${RED}Erro: Arquivo .env.$target_branch não encontrado${NC}"
        exit 1
    fi

    # Parar containers atuais
    echo -e "${YELLOW}Parando containers atuais...${NC}"
    docker-compose down

    # Copiar configuração do ambiente
    echo -e "${YELLOW}Configurando ambiente $target_branch...${NC}"
    cp ".env.$target_branch" ".env"

    # Exportar variável BRANCH
    export BRANCH="$target_branch"

    # Iniciar containers com nova configuração
    echo -e "${YELLOW}Iniciando containers para $target_branch...${NC}"
    BRANCH="$target_branch" docker-compose up -d --build

    # Verificar se containers iniciaram
    sleep 5
    if docker-compose ps | grep -q "Up"; then
        echo -e "${GREEN}✅ Ambiente $target_branch configurado com sucesso!${NC}"
        echo ""
        echo "Serviços disponíveis:"
        echo "  - Django: http://localhost:8000"
        echo "  - Streamlit: http://localhost:8501"
        echo "  - pgAdmin: http://localhost:8080"
        echo "  - MCP: http://localhost:3001"
    else
        echo -e "${RED}❌ Erro ao iniciar containers${NC}"
        exit 1
    fi
}

# Main
main() {
    case "${1:-}" in
        "main"|"develop")
            switch_environment "$1"
            ;;
        "")
            show_current_env
            ;;
        "-h"|"--help"|"help")
            show_usage
            ;;
        *)
            echo -e "${RED}Ambiente inválido: $1${NC}"
            show_usage
            exit 1
            ;;
    esac
}

# Verificar se Docker está rodando
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}Docker não está rodando. Inicie o Docker primeiro.${NC}"
    exit 1
fi

main "$@"
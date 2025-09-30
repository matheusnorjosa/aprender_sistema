#!/bin/bash
# ======================================
# 🐳 SCRIPTS UNIFICADOS - SISTEMA APRENDER
# Interface única para ambientes Docker
# ======================================

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para mostrar ajuda
show_help() {
    echo -e "${BLUE}🐳 Sistema Aprender - Docker Unificado${NC}"
    echo -e "${BLUE}======================================${NC}"
    echo ""
    echo "Uso: $0 <comando> [opções]"
    echo ""
    echo -e "${GREEN}Comandos de Ambiente:${NC}"
    echo "  dev                    - Iniciar ambiente de desenvolvimento"
    echo "  prod                   - Iniciar ambiente de produção"
    echo "  test                   - Executar testes"
    echo "  stop                   - Parar todos os serviços"
    echo "  down                   - Parar e remover containers"
    echo "  clean                  - Limpeza completa (volumes + images)"
    echo ""
    echo -e "${GREEN}Comandos de Desenvolvimento:${NC}"
    echo "  dev-full              - Desenvolvimento com todas as ferramentas"
    echo "  dev-minimal           - Desenvolvimento apenas essencial"
    echo "  logs [serviço]        - Ver logs (opcionalmente de um serviço)"
    echo "  shell                 - Acesso shell ao container web"
    echo "  manage <comando>      - Executar comando Django manage.py"
    echo ""
    echo -e "${GREEN}Comandos de Produção:${NC}"
    echo "  prod-deploy           - Deploy completo produção"
    echo "  prod-backup           - Executar backup manual"
    echo "  prod-monitoring       - Iniciar com monitoramento"
    echo ""
    echo -e "${GREEN}Comandos de Utilitários:${NC}"
    echo "  status                - Status dos containers"
    echo "  ps                    - Processos ativos"
    echo "  build                 - Rebuild images"
    echo "  migrate               - Executar migrações"
    echo "  collectstatic         - Coletar arquivos estáticos"
    echo ""
    echo -e "${YELLOW}Exemplos:${NC}"
    echo "  $0 dev                # Ambiente desenvolvimento básico"
    echo "  $0 dev-full           # Desenvolvimento com pgAdmin, MailHog, etc"
    echo "  $0 prod-deploy        # Deploy produção completo"
    echo "  $0 manage shell       # Django shell"
    echo "  $0 logs web           # Logs do container web"
}

# Verificar se docker-compose está disponível
check_docker() {
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}❌ docker-compose não encontrado${NC}"
        exit 1
    fi
}

# Criar arquivo .env se não existir
ensure_env() {
    if [ ! -f .env ]; then
        echo -e "${YELLOW}⚠️  Arquivo .env não encontrado, criando baseado no .env.example...${NC}"
        cp .env.example .env
        echo -e "${GREEN}✅ Arquivo .env criado. Ajuste as configurações conforme necessário.${NC}"
    fi
}

# Função principal
main() {
    check_docker
    ensure_env

    case "$1" in
        # Ambientes básicos
        "dev")
            echo -e "${GREEN}🚀 Iniciando ambiente de desenvolvimento...${NC}"
            ENVIRONMENT=development BUILD_TARGET=development docker-compose up -d db redis web
            ;;
        "dev-full")
            echo -e "${GREEN}🚀 Iniciando desenvolvimento completo...${NC}"
            ENVIRONMENT=development BUILD_TARGET=development docker-compose --profile dev-tools up -d
            ;;
        "dev-minimal")
            echo -e "${GREEN}🚀 Iniciando desenvolvimento mínimo...${NC}"
            ENVIRONMENT=development BUILD_TARGET=development docker-compose up -d db web
            ;;
        "prod")
            echo -e "${GREEN}🚀 Iniciando ambiente de produção...${NC}"
            ENVIRONMENT=production BUILD_TARGET=production docker-compose up -d db redis web
            ;;
        "prod-deploy")
            echo -e "${GREEN}🚀 Deploy completo produção...${NC}"
            ENVIRONMENT=production BUILD_TARGET=production docker-compose --profile production up -d
            ;;
        "prod-monitoring")
            echo -e "${GREEN}🚀 Produção com monitoramento...${NC}"
            ENVIRONMENT=production BUILD_TARGET=production docker-compose --profile production --profile monitoring up -d
            ;;
        "test")
            echo -e "${GREEN}🧪 Executando testes...${NC}"
            BUILD_TARGET=test docker-compose run --rm web
            ;;

        # Controle de serviços
        "stop")
            echo -e "${YELLOW}⏹️  Parando serviços...${NC}"
            docker-compose stop
            ;;
        "down")
            echo -e "${YELLOW}⏹️  Parando e removendo containers...${NC}"
            docker-compose down
            ;;
        "clean")
            echo -e "${RED}🧹 Limpeza completa...${NC}"
            read -p "Tem certeza? Isso removerá volumes e dados (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                docker-compose down -v
                docker system prune -f
                echo -e "${GREEN}✅ Limpeza concluída${NC}"
            fi
            ;;

        # Utilitários
        "status")
            echo -e "${BLUE}📊 Status dos containers:${NC}"
            docker-compose ps
            ;;
        "ps")
            docker-compose ps
            ;;
        "logs")
            if [ -n "$2" ]; then
                docker-compose logs -f "$2"
            else
                docker-compose logs -f
            fi
            ;;
        "shell")
            echo -e "${BLUE}🐚 Acessando shell do container web...${NC}"
            docker-compose exec web bash
            ;;
        "manage")
            shift
            echo -e "${BLUE}⚙️  Executando: python manage.py $*${NC}"
            docker-compose exec web python manage.py "$@"
            ;;
        "migrate")
            echo -e "${BLUE}📊 Executando migrações...${NC}"
            docker-compose exec web python manage.py migrate
            ;;
        "collectstatic")
            echo -e "${BLUE}📁 Coletando arquivos estáticos...${NC}"
            docker-compose exec web python manage.py collectstatic --noinput
            ;;
        "build")
            echo -e "${BLUE}🔨 Rebuilding images...${NC}"
            docker-compose build
            ;;
        "prod-backup")
            echo -e "${BLUE}💾 Executando backup...${NC}"
            docker-compose --profile backup run --rm backup
            ;;

        # Ajuda
        "help"|"-h"|"--help"|"")
            show_help
            ;;
        *)
            echo -e "${RED}❌ Comando desconhecido: $1${NC}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Executar função principal
main "$@"
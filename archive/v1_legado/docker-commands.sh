#!/bin/bash
# 
# Script para executar TODOS os comandos via Docker
# Garante que tudo seja feito através dos containers
#
# Uso: ./docker-commands.sh [comando]
#

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== COMANDOS DOCKER UNIFICADOS ===${NC}"
echo -e "${YELLOW}IMPORTANTE: Todos os comandos serão executados via containers Docker${NC}"
echo ""

# Verificar se docker-compose está disponível
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ docker-compose não encontrado!${NC}"
    exit 1
fi

# Verificar se containers estão rodando
if ! docker-compose ps | grep -q "Up"; then
    echo -e "${YELLOW}⚠️ Containers não estão rodando. Iniciando...${NC}"
    docker-compose up -d
    echo -e "${GREEN}✅ Containers iniciados${NC}"
fi

# Função para executar comando no container web
exec_web() {
    echo -e "${BLUE}🐳 Executando no container web: $*${NC}"
    docker-compose exec web "$@"
}

# Função para mostrar status do sistema
status() {
    echo -e "${BLUE}=== STATUS DO SISTEMA ===${NC}"
    docker-compose ps
    echo ""
    echo -e "${BLUE}=== DADOS NO BANCO ===${NC}"
    exec_web python manage.py shell -c "
from core.models import *
from django.contrib.auth import get_user_model
User = get_user_model()
print(f'Usuarios: {User.objects.count()}')
print(f'Formadores: {Formador.objects.count()}')
print(f'Municipios: {Municipio.objects.count()}')
print(f'Projetos: {Projeto.objects.count()}')
print(f'Solicitacoes: {Solicitacao.objects.count()}')
print(f'TipoEvento: {TipoEvento.objects.count()}')
print(f'Setores: {Setor.objects.count()}')
"
}

# Função para limpeza completa
reset_completo() {
    echo -e "${RED}⚠️ RESET COMPLETO DO BANCO DE DADOS⚠️${NC}"
    echo -e "${YELLOW}Esta operação removerá TODOS os dados!${NC}"
    read -p "Digite 'CONFIRMAR' para continuar: " confirmacao
    
    if [ "$confirmacao" = "CONFIRMAR" ]; then
        echo -e "${BLUE}🗑️ Executando reset completo via Docker...${NC}"
        exec_web python manage.py reset_database_completo --confirmar-reset-total --verbose
    else
        echo -e "${YELLOW}❌ Operação cancelada${NC}"
    fi
}

# Função para importar aba Super
import_super() {
    echo -e "${BLUE}📊 Importando dados da aba Super via Docker...${NC}"
    echo -e "${YELLOW}Modo: $1${NC}"
    
    if [ "$1" = "dry-run" ]; then
        exec_web python manage.py import_super_colunas_e_t --dry-run --verbose
    else
        exec_web python manage.py import_super_colunas_e_t --verbose
    fi
}

# Função para executar migrações
migrate() {
    echo -e "${BLUE}📦 Executando migrações via Docker...${NC}"
    exec_web python manage.py migrate
}

# Função para criar superusuário
createsuperuser() {
    echo -e "${BLUE}👤 Criando superusuário via Docker...${NC}"
    exec_web python manage.py createsuperuser
}

# Função para shell Django
shell() {
    echo -e "${BLUE}🐍 Abrindo shell Django via Docker...${NC}"
    exec_web python manage.py shell
}

# Função para logs
logs() {
    echo -e "${BLUE}📋 Logs dos containers:${NC}"
    if [ "$1" = "web" ]; then
        docker-compose logs web
    elif [ "$1" = "db" ]; then
        docker-compose logs db
    else
        docker-compose logs
    fi
}

# Função para controlar Streamlit
streamlit() {
    echo -e "${BLUE}📊 Acessando Streamlit Dashboard via Docker...${NC}"
    echo -e "${GREEN}URL: http://localhost:8501${NC}"
    echo -e "${YELLOW}Nota: Streamlit roda no container aprender_streamlit${NC}"
}

# Função para logs específicos
logs_streamlit() {
    echo -e "${BLUE}📋 Logs do Streamlit:${NC}"
    docker-compose logs streamlit
}

# Funções para controle do MCP
mcp_status() {
    echo -e "${BLUE}🔧 Status do Servidor MCP:${NC}"
    docker-compose ps mcp
    echo ""
    echo -e "${BLUE}📊 Health Check MCP:${NC}"
    curl -s http://localhost:3001/health | python -m json.tool 2>/dev/null || echo "MCP não está respondendo"
}

mcp_logs() {
    echo -e "${BLUE}📋 Logs do Servidor MCP:${NC}"
    docker-compose logs mcp
}

mcp_restart() {
    echo -e "${BLUE}🔄 Reiniciando apenas o servidor MCP...${NC}"
    docker-compose restart mcp
    echo -e "${GREEN}✅ Servidor MCP reiniciado${NC}"
}

mcp_shell() {
    echo -e "${BLUE}🐍 Acessando shell do container MCP...${NC}"
    docker-compose exec mcp /bin/bash
}

# Funções Git integradas com Docker
git_status() {
    echo -e "${BLUE}📋 Status do Sistema Docker + Git:${NC}"
    docker-compose ps --format "table {{.Names}}\t{{.Status}}"
    echo ""
    echo -e "${BLUE}📝 Status Git:${NC}"
    git status --short
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Sistema Docker funcionando + Git status OK${NC}"
    else
        echo -e "${RED}❌ Problema no Git${NC}"
    fi
}

git_commit() {
    if [ -z "$2" ]; then
        echo -e "${RED}❌ Uso: ./docker-commands.sh git-commit \"mensagem do commit\"${NC}"
        return 1
    fi
    
    echo -e "${BLUE}🔄 Verificando sistema antes do commit...${NC}"
    if ! docker-compose ps | grep -q "Up"; then
        echo -e "${RED}❌ Containers não estão rodando! Execute: ./docker-commands.sh start${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✅ Sistema Docker funcionando${NC}"
    echo -e "${BLUE}📝 Fazendo commit: $2${NC}"
    
    git add .
    git status --short
    echo ""
    git commit -m "$2"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Commit realizado com sucesso!${NC}"
    else
        echo -e "${RED}❌ Falha no commit${NC}"
        return 1
    fi
}

git_push() {
    echo -e "${BLUE}🔄 Verificando sistema antes do push...${NC}"
    if ! docker-compose ps | grep -q "Up"; then
        echo -e "${YELLOW}⚠️ Containers não estão rodando (recomendado para push)${NC}"
    else
        echo -e "${GREEN}✅ Sistema Docker funcionando${NC}"
    fi
    
    echo -e "${BLUE}🚀 Fazendo push para repositório remoto...${NC}"
    git push
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Push realizado com sucesso!${NC}"
    else
        echo -e "${RED}❌ Falha no push${NC}"
        return 1
    fi
}

git_pull() {
    echo -e "${BLUE}⬇️ Fazendo pull do repositório remoto...${NC}"
    git pull
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Pull realizado com sucesso!${NC}"
        echo -e "${YELLOW}💡 Considere reiniciar containers se houve mudanças: ./docker-commands.sh restart-all${NC}"
    else
        echo -e "${RED}❌ Falha no pull${NC}"
        return 1
    fi
}

# Função para reiniciar TUDO
restart_all() {
    echo -e "${BLUE}🔄 Reiniciando TODOS os containers (DB + Django + Streamlit)...${NC}"
    docker-compose down
    docker-compose up -d
    echo -e "${GREEN}✅ Todos os containers reiniciados${NC}"
}

# Função para build completo
build_all() {
    echo -e "${BLUE}🔨 Rebuilding TODOS os containers...${NC}"
    docker-compose down
    docker-compose build --no-cache
    docker-compose up -d
    echo -e "${GREEN}✅ Build completo finalizado${NC}"
}

# Menu principal
case "$1" in
    "status")
        status
        ;;
    "reset")
        reset_completo
        ;;
    "import-super")
        import_super "$2"
        ;;
    "migrate")
        migrate
        ;;
    "createsuperuser")
        createsuperuser
        ;;
    "shell")
        shell
        ;;
    "logs")
        logs "$2"
        ;;
    "streamlit")
        streamlit
        ;;
    "logs-streamlit")
        logs_streamlit
        ;;
    "mcp-status")
        mcp_status
        ;;
    "mcp-logs")
        mcp_logs
        ;;
    "mcp-restart")
        mcp_restart
        ;;
    "mcp-shell")
        mcp_shell
        ;;
    "git-status")
        git_status
        ;;
    "git-commit")
        git_commit "$1" "$2"
        ;;
    "git-push")
        git_push
        ;;
    "git-pull")
        git_pull
        ;;
    "restart-all")
        restart_all
        ;;
    "build-all")
        build_all
        ;;
    "start")
        echo -e "${BLUE}🚀 Iniciando TODOS os containers (DB + Django + Streamlit + MCP)...${NC}"
        docker-compose up -d
        ;;
    "stop")
        echo -e "${BLUE}🛑 Parando TODOS os containers...${NC}"
        docker-compose down
        ;;
    "restart")
        echo -e "${BLUE}🔄 Reiniciando containers...${NC}"
        docker-compose restart
        ;;
    "help"|"")
        echo -e "${GREEN}📚 COMANDOS DOCKER UNIFICADOS - TODAS AS FUNCIONALIDADES:${NC}"
        echo ""
        echo -e "${BLUE}Gerais:${NC}"
        echo "  ./docker-commands.sh status          - Mostrar status completo do sistema"
        echo "  ./docker-commands.sh start           - Iniciar TODOS os containers (DB + Django + Streamlit)"
        echo "  ./docker-commands.sh stop            - Parar TODOS os containers"
        echo "  ./docker-commands.sh restart         - Reiniciar containers individuais"
        echo "  ./docker-commands.sh restart-all     - Reiniciar TUDO (down + up)"
        echo "  ./docker-commands.sh build-all       - Rebuild completo de TODOS os containers"
        echo "  ./docker-commands.sh logs [web|db]   - Ver logs dos containers"
        echo ""
        echo -e "${BLUE}Django (Container Web):${NC}"
        echo "  ./docker-commands.sh migrate         - Executar migrações via Docker"
        echo "  ./docker-commands.sh shell           - Shell Django via Docker"
        echo "  ./docker-commands.sh createsuperuser - Criar superusuário via Docker"
        echo ""
        echo -e "${BLUE}Streamlit (Container Separado):${NC}"
        echo "  ./docker-commands.sh streamlit       - Info do dashboard Streamlit"
        echo "  ./docker-commands.sh logs-streamlit  - Ver logs do Streamlit"
        echo ""
        echo -e "${BLUE}MCP Server (Container Separado):${NC}"
        echo "  ./docker-commands.sh mcp-status      - Status e health check do MCP"
        echo "  ./docker-commands.sh mcp-logs        - Ver logs do servidor MCP"
        echo "  ./docker-commands.sh mcp-restart     - Reiniciar apenas o MCP"
        echo "  ./docker-commands.sh mcp-shell       - Acessar shell do container MCP"
        echo ""
        echo -e "${BLUE}Git (Integrado com Docker):${NC}"
        echo "  ./docker-commands.sh git-status      - Status do sistema + repositório Git"
        echo "  ./docker-commands.sh git-commit \"msg\" - Commit com verificação de containers"
        echo "  ./docker-commands.sh git-push        - Push para repositório remoto"
        echo "  ./docker-commands.sh git-pull        - Pull do repositório remoto"
        echo ""
        echo -e "${BLUE}Dados:${NC}"
        echo "  ./docker-commands.sh reset           - Reset completo do banco via Docker"
        echo "  ./docker-commands.sh import-super [dry-run] - Importar aba Super via Docker"
        echo ""
        echo -e "${GREEN}🐳 TODAS as funcionalidades rodam 100% em Docker:${NC}"
        echo -e "${YELLOW}   - PostgreSQL: localhost:5433${NC}"
        echo -e "${YELLOW}   - Django:     localhost:8000${NC}" 
        echo -e "${YELLOW}   - Streamlit:  localhost:8501${NC}"
        echo -e "${YELLOW}   - MCP Server: localhost:3001${NC}"
        ;;
    *)
        echo -e "${RED}❌ Comando não reconhecido: $1${NC}"
        echo -e "${YELLOW}Use './docker-commands.sh help' para ver comandos disponíveis${NC}"
        ;;
esac
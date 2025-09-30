#!/bin/bash

# ============================================
# 🔧 SCRIPT DE CORREÇÃO - DJANGO CORROMPIDO
# ============================================
# Sistema Aprender - Fix para ModuleNotFoundError: django.template
# Autor: Claude Code
# Data: 2025-09-30

set -e

echo "🔧 CORREÇÃO DA INSTALAÇÃO DO DJANGO"
echo "===================================="
echo ""

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Passo 1: Desativar venv (se ativo)
echo -e "${YELLOW}🔹 Passo 1: Desativando venv atual...${NC}"
deactivate 2>/dev/null || true

# Passo 2: Fazer backup do venv antigo
echo -e "${YELLOW}🔹 Passo 2: Backup do venv corrompido...${NC}"
if [ -d ".venv" ]; then
    timestamp=$(date +%Y%m%d_%H%M%S)
    backup_name=".venv_backup_$timestamp"
    mv .venv "$backup_name"
    echo -e "   ${GREEN}✅ Backup criado: $backup_name${NC}"
else
    echo -e "   ${YELLOW}⚠️  Nenhum venv encontrado${NC}"
fi

# Passo 3: Criar novo venv
echo -e "${YELLOW}🔹 Passo 3: Criando novo ambiente virtual...${NC}"
python3 -m venv .venv
echo -e "   ${GREEN}✅ Venv criado com sucesso${NC}"

# Passo 4: Ativar novo venv
echo -e "${YELLOW}🔹 Passo 4: Ativando novo venv...${NC}"
source .venv/bin/activate

# Passo 5: Atualizar pip
echo -e "${YELLOW}🔹 Passo 5: Atualizando pip...${NC}"
python -m pip install --upgrade pip --quiet

# Passo 6: Instalar dependências
echo -e "${YELLOW}🔹 Passo 6: Instalando dependências (isso pode demorar)...${NC}"
pip install -r requirements.txt --quiet
echo -e "   ${GREEN}✅ Dependências instaladas${NC}"

# Passo 7: Verificar Django
echo ""
echo -e "${YELLOW}🔹 Passo 7: Verificando instalação do Django...${NC}"
python -c "import django; print(f'   ✅ Django {django.__version__} instalado')"

echo -e "${YELLOW}🔹 Passo 8: Testando django.template...${NC}"
python -c "import django.template; print('   ✅ django.template OK')"

# Passo 9: Executar check do Django
echo ""
echo -e "${YELLOW}🔹 Passo 9: Executando Django check...${NC}"
if python manage.py check; then
    echo -e "   ${GREEN}✅ Sistema Django OK${NC}"
else
    echo -e "   ${YELLOW}⚠️  Warnings encontrados (isso é normal)${NC}"
fi

# Sucesso!
echo ""
echo -e "${GREEN}✅ CORREÇÃO CONCLUÍDA COM SUCESSO!${NC}"
echo -e "${GREEN}===================================${NC}"
echo ""
echo -e "${CYAN}Próximos passos:${NC}"
echo "1. Executar migrations: python manage.py migrate"
echo "2. Criar superuser: python manage.py createsuperuser"
echo "3. Rodar servidor: python manage.py runserver"
echo ""
echo -e "${YELLOW}Para remover backups antigos:${NC}"
echo "rm -rf .venv_backup_*"

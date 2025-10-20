#!/bin/bash
# ===========================================
# SCRIPT DE MIGRAÇÃO - APRENDER SISTEMA
# ===========================================
# Executa migrações Django no container Docker

set -e

echo "=Ä Executando migrações Django..."

# Criar migrações se necessário
echo "=Ý Verificando se há novas migrações..."
./scripts/docker-run.sh python manage.py makemigrations

# Aplicar migrações
echo " Aplicando migrações..."
./scripts/docker-run.sh python manage.py migrate

# Mostrar status das migrações
echo "=Ê Status das migrações:"
./scripts/docker-run.sh python manage.py showmigrations

echo " Migrações concluídas!"
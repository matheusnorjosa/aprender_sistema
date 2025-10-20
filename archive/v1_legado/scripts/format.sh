#!/bin/bash
# ===========================================
# SCRIPT DE FORMATAÇÃO - APRENDER SISTEMA
# ===========================================
# Executa formatação de código no container Docker

set -e

echo "<¨ Executando formatação de código..."

# Executar isort para organizar imports
echo "=æ Organizando imports com isort..."
./scripts/docker-run.sh isort .

# Executar Black para formatação
echo "=Ý Formatando código com Black..."
./scripts/docker-run.sh black .

echo " Formatação concluída!"
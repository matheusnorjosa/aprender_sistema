#!/bin/bash

# Script para usar Codex CLI via WSL com contexto completo do projeto
# Uso: ./codex-wsl.sh "prompt aqui"

# Configurar ambiente
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
export BROWSER=wslview

# Navegar para o projeto
cd '/mnt/c/Users/datsu/OneDrive/Documentos/Aprender Sistema'

echo "🤖 Codex CLI - Projeto Aprender Sistema"
echo "📁 Diretório: $(pwd)"
echo "📋 Contexto disponível:"
echo "   - CODEX_CONTEXT_PACKAGE.md (LEIA PRIMEIRO!)"
echo "   - CODEX_QUICK_START.md (Guia de início)"
echo "   - CLAUDE.md (Histórico completo)"
echo "   - .claude/CLAUDE.md (Diretrizes técnicas)"
echo ""

# Verificar se Docker está rodando
if docker-compose ps | grep -q "Up"; then
    echo "✅ Docker está rodando"
else
    echo "⚠️  Docker não está rodando. Execute: docker-compose up -d"
fi

echo ""

# Executar codex com o prompt fornecido
if [ $# -eq 0 ]; then
    echo "💡 Dica: Para começar, leia: cat CODEX_CONTEXT_PACKAGE.md"
    echo "💡 Ou execute: ./codex-wsl.sh \"ler contexto do projeto\""
    echo ""
    echo "Iniciando Codex no modo interativo..."
    codex -C '/mnt/c/Users/datsu/OneDrive/Documentos/Aprender Sistema'
else
    echo "Executando prompt: $1"
    codex -C '/mnt/c/Users/datsu/OneDrive/Documentos/Aprender Sistema' exec "$1"
fi
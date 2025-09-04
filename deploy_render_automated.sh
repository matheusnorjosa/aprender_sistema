#!/bin/bash
# Script de Deploy Automatizado no Render via API
# Criado via integração com Render MCP Server

set -e  # Exit on error

echo "🚀 Deploy Automatizado no Render - Aprender Sistema"
echo "=================================================="

# Configurações
RENDER_API_KEY="${RENDER_API_KEY:-}"
OWNER_ID="tea-d2ssffeuk2gs73c8rreg"
REPO_URL="https://github.com/matheusnorjosa/aprender_sistema.git"

# Verificar se API key está configurada
if [ -z "$RENDER_API_KEY" ]; then
    echo "❌ ERRO: RENDER_API_KEY não está configurada"
    echo "Execute: export RENDER_API_KEY=sua_api_key_aqui"
    exit 1
fi

# Função para fazer requests à API
render_api() {
    local method=$1
    local endpoint=$2
    local data=$3
    
    if [ -z "$data" ]; then
        curl -X "$method" "https://api.render.com/v1$endpoint" \
            -H "Authorization: Bearer $RENDER_API_KEY" \
            -H "Content-Type: application/json"
    else
        curl -X "$method" "https://api.render.com/v1$endpoint" \
            -H "Authorization: Bearer $RENDER_API_KEY" \
            -H "Content-Type: application/json" \
            -d "$data"
    fi
}

# 1. Criar PostgreSQL Database
echo "📊 Criando banco PostgreSQL..."
DB_RESPONSE=$(render_api POST "/postgres" '{
    "name": "aprender-sistema-db",
    "databaseName": "aprender_sistema", 
    "databaseUser": "aprender_sistema_user",
    "ownerId": "'$OWNER_ID'",
    "plan": "free",
    "region": "oregon",
    "version": "15"
}')

DB_ID=$(echo "$DB_RESPONSE" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
echo "✅ Banco criado com ID: $DB_ID"

# Aguardar banco ficar disponível
echo "⏳ Aguardando banco ficar disponível..."
while true; do
    STATUS=$(render_api GET "/postgres/$DB_ID" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    if [ "$STATUS" = "available" ]; then
        echo "✅ Banco disponível!"
        break
    fi
    echo "   Status: $STATUS - aguardando..."
    sleep 10
done

# 2. Obter connection string
echo "🔗 Obtendo connection string..."
CONN_INFO=$(render_api GET "/postgres/$DB_ID/connection-info")
DATABASE_URL=$(echo "$CONN_INFO" | grep -o '"internalConnectionString":"[^"]*"' | cut -d'"' -f4)
echo "✅ Connection string obtida"

# 3. Criar Web Service
echo "🌐 Criando web service Django..."
SERVICE_RESPONSE=$(render_api POST "/services" '{
    "type": "web_service",
    "name": "aprender-sistema",
    "ownerId": "'$OWNER_ID'",
    "repo": "'$REPO_URL'",
    "serviceDetails": {
        "plan": "starter",
        "region": "oregon",
        "runtime": "python", 
        "branch": "main",
        "buildCommand": "./build.sh",
        "startCommand": "gunicorn aprender_sistema.wsgi:application",
        "envVars": [
            {"key": "ENVIRONMENT", "value": "production"},
            {"key": "SECRET_KEY", "value": "2uxov1VHM1RsYZobrmzkD3A4j3v4x8FpCLRvyKeyl6cEuTIkZ4OfucKA0-hA6fjkk_s"},
            {"key": "DEBUG", "value": "False"}
        ],
        "envSpecificDetails": {
            "buildCommand": "./build.sh",
            "startCommand": "gunicorn aprender_sistema.wsgi:application"
        }
    }
}')

SERVICE_ID=$(echo "$SERVICE_RESPONSE" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
SERVICE_URL=$(echo "$SERVICE_RESPONSE" | grep -o '"url":"[^"]*"' | cut -d'"' -f4)
echo "✅ Web service criado com ID: $SERVICE_ID"
echo "🌍 URL: $SERVICE_URL"

# 4. Configurar variáveis de ambiente adicionais
echo "⚙️  Configurando variáveis de ambiente..."
render_api PUT "/services/$SERVICE_ID/env-vars" '[
    {"key": "DATABASE_URL", "value": "'$DATABASE_URL'"},
    {"key": "ALLOWED_HOSTS", "value": "aprender-sistema.onrender.com"},
    {"key": "CSRF_TRUSTED_ORIGINS", "value": "https://aprender-sistema.onrender.com"}
]'
echo "✅ Variáveis de ambiente configuradas"

# 5. Monitorar deploy
echo "📦 Monitorando deploy inicial..."
DEPLOY_ID=$(echo "$SERVICE_RESPONSE" | grep -o '"deployId":"[^"]*"' | cut -d'"' -f4)

while true; do
    DEPLOY_STATUS=$(render_api GET "/services/$SERVICE_ID/deploys/$DEPLOY_ID" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    echo "   Deploy status: $DEPLOY_STATUS"
    
    if [ "$DEPLOY_STATUS" = "live" ]; then
        echo "🎉 Deploy concluído com sucesso!"
        break
    elif [ "$DEPLOY_STATUS" = "build_failed" ] || [ "$DEPLOY_STATUS" = "deploy_failed" ]; then
        echo "❌ Deploy falhou! Verifique os logs no dashboard."
        exit 1
    fi
    
    sleep 30
done

echo ""
echo "✅ Deploy Automatizado Concluído!"
echo "=================================="
echo "🌍 URL da Aplicação: $SERVICE_URL"
echo "📊 Database ID: $DB_ID" 
echo "🌐 Service ID: $SERVICE_ID"
echo "📦 Deploy ID: $DEPLOY_ID"
echo ""
echo "📋 Dashboard URLs:"
echo "   Aplicação: https://dashboard.render.com/web/$SERVICE_ID"
echo "   Banco: https://dashboard.render.com/d/$DB_ID"
echo ""
echo "🔧 Para futuras atualizações, apenas faça git push - deploy é automático!"
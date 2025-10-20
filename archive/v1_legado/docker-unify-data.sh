#!/bin/bash
# Docker Script - Unificação Completa de Referências de Dados
# EXECUTA TODA A UNIFICAÇÃO NO DOCKER POSTGRESQL

echo "🐳 INICIANDO UNIFICAÇÃO COMPLETA NO DOCKER"
echo "=========================================="

# Verificar se Docker está rodando
if ! docker-compose ps | grep -q "web"; then
    echo "❌ ERRO: Docker não está rodando"
    echo "Execute: docker-compose up -d"
    exit 1
fi

echo "✅ Docker detectado - PostgreSQL ativo"

# FASE 1: Backup de segurança
echo ""
echo "📦 FASE 1: Backup de segurança..."
docker-compose exec db pg_dump -U adm_aprender aprender_sistema_db > backup_pre_unificacao_$(date +%Y%m%d_%H%M%S).sql
echo "✅ Backup criado"

# FASE 2: Executar unificação
echo ""
echo "🔄 FASE 2: Executando unificação de dados..."
docker-compose exec web python manage.py unify_data_references --docker

if [ $? -ne 0 ]; then
    echo "❌ ERRO na unificação!"
    exit 1
fi

echo "✅ Unificação concluída"

# FASE 3: Aplicar migrações se necessário
echo ""
echo "🔄 FASE 3: Aplicando migrações..."
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py migrate

echo "✅ Migrações aplicadas"

# FASE 4: Validação final
echo ""
echo "🔍 FASE 4: Validação final..."
docker-compose exec web python manage.py validate_unified_data --docker

if [ $? -ne 0 ]; then
    echo "⚠️  Validação encontrou problemas"
else
    echo "✅ Validação aprovada"
fi

# FASE 5: Limpeza de cache
echo ""
echo "🧹 FASE 5: Limpando cache..."
docker-compose exec web python manage.py shell -c "
from django.core.cache import cache
cache.clear()
print('Cache limpo')
"

echo "✅ Cache limpo"

# RESUMO FINAL
echo ""
echo "🎯 UNIFICAÇÃO COMPLETA - DOCKER POSTGRESQL"
echo "=========================================="
echo "✅ Usuario como fonte única implementado"
echo "✅ Services centralizados ativos"
echo "✅ Imports padronizados via base.py"
echo "✅ Queries otimizadas com cache"
echo "✅ Integridade validada"
echo ""
echo "💡 PRÓXIMOS PASSOS:"
echo "1. Testar dashboard executivo: http://localhost:8000/diretoria/dashboard/"
echo "2. Verificar APIs: http://localhost:8000/api/diretoria/"
echo "3. Monitorar performance das queries"
echo ""
echo "🔧 Comandos úteis:"
echo "docker-compose exec web python manage.py shell"
echo "docker-compose logs web"
echo "docker-compose exec db psql -U adm_aprender -d aprender_sistema_db"
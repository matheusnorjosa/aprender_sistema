# 🚀 CODEX QUICK START - Aprender Sistema

## 📍 ONDE VOCÊ ESTÁ

Você está no **Projeto Aprender Sistema**, um sistema Django em produção que gerencia eventos educacionais. Este guia te dará contexto imediato para começar a trabalhar.

## 🎯 PRIMEIRO: LEIA O CONTEXTO COMPLETO

```bash
# Leia estes arquivos OBRIGATORIAMENTE (nesta ordem):
cat CODEX_CONTEXT_PACKAGE.md     # Contexto geral (ESTE ARQUIVO É CRÍTICO)
cat CLAUDE.md                    # Histórico detalhado das sessões
cat .claude/CLAUDE.md            # Diretrizes técnicas e regras
```

## 🐳 COMANDOS DOCKER ESSENCIAIS

### Status do Sistema:
```bash
# Ver se containers estão rodando
docker-compose ps

# Verificar logs
docker-compose logs web -f

# Status do banco
docker-compose logs db -f
```

### Comandos Django via Docker:
```bash
# Shell Django
docker-compose exec web python manage.py shell

# Executar migrations
docker-compose exec web python manage.py migrate

# Criar superuser
docker-compose exec web python manage.py createsuperuser

# Importar dados de planilhas
docker-compose exec web python manage.py import_agenda_completa --verbose
```

## 📁 NAVEGAÇÃO NO PROJETO

### Estrutura de Arquivos Importantes:
```bash
# Modelos principais (LEIA PRIMEIRO)
cat core/models.py | head -100

# Configurações Docker
cat docker-compose.yml

# URLs principais
cat core/urls.py

# Views principais
ls core/views/
cat core/views/aprovacao_views.py

# Templates
ls core/templates/core/
```

### Arquivos de Configuração:
```bash
# Variáveis de ambiente
cat .env

# Dependências Python
cat requirements.txt

# Configurações Django
cat aprender_sistema/settings.py
```

## 🌐 ACESSOS DO SISTEMA

### URLs Locais (quando Docker estiver rodando):
- **Sistema Principal**: http://localhost:8000
- **Admin Django**: http://localhost:8000/admin
- **Dashboard Streamlit**: http://localhost:8501
- **PgAdmin**: http://localhost:8080
- **MCP Server**: http://localhost:3001

### Credenciais de Teste:
```bash
# Admin Django (se criar superuser)
# Username: admin
# Password: [o que você definir]

# PgAdmin
# Email: admin@admin.com
# Password: admin
```

## 🔍 EXPLORANDO OS DADOS

### Verificar Estado Atual:
```bash
# Contar registros principais
docker-compose exec web python manage.py shell -c "
from core.models import *
print(f'Usuários: {Usuario.objects.count()}')
print(f'Formadores: {Formador.objects.count()}')
print(f'Solicitações: {Solicitacao.objects.count()}')
print(f'Projetos: {Projeto.objects.count()}')
print(f'Municípios: {Municipio.objects.count()}')
"

# Ver últimas solicitações
docker-compose exec web python manage.py shell -c "
from core.models import Solicitacao
for s in Solicitacao.objects.order_by('-created_at')[:5]:
    print(f'{s.data_evento} - {s.projeto.nome} - {s.municipio.nome}')
"
```

## 📋 COMANDOS ÚTEIS PARA DESENVOLVIMENTO

### Análise de Código:
```bash
# Encontrar TODOs
grep -r "TODO" core/ --include="*.py"

# Encontrar FIXMEs
grep -r "FIXME" core/ --include="*.py"

# Ver migrations
ls core/migrations/

# Ver testes
ls core/tests/ 2>/dev/null || echo "Sem pasta tests específica"
```

### Debug e Logs:
```bash
# Ver logs de auditoria
docker-compose exec web python manage.py shell -c "
from core.models import LogAuditoria
for log in LogAuditoria.objects.order_by('-timestamp')[:10]:
    print(f'{log.timestamp} - {log.usuario.nome} - {log.acao}')
"

# Ver problemas recentes
docker-compose logs web | grep -i error | tail -10
```

## 🧪 TESTES RÁPIDOS

### Verificar Funcionalidades Principais:
```bash
# Testar importação de dados
docker-compose exec web python manage.py import_agenda_completa --dry-run

# Verificar Google Sheets access
docker-compose exec web python manage.py analyze_google_sheets

# Testar models básicos
docker-compose exec web python manage.py shell -c "
from core.models import *
from django.contrib.auth.models import Group
print('Grupos:', [g.name for g in Group.objects.all()])
print('Setores:', [s.nome for s in Setor.objects.all()])
"
```

## 🔧 COMANDOS DE MANUTENÇÃO

### Limpeza e Reset (CUIDADO!):
```bash
# Backup antes de qualquer operação destrutiva
docker-compose exec db pg_dump -U adm_aprender aprender_sistema_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Reset migrações (apenas se necessário)
# docker-compose exec web find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
# docker-compose exec web python manage.py makemigrations
# docker-compose exec web python manage.py migrate
```

### Performance:
```bash
# Ver queries lentas (se Django Debug Toolbar estiver ativo)
# Acesse http://localhost:8000/admin e observe o painel de debug

# Verificar conexões DB
docker-compose exec db psql -U adm_aprender -d aprender_sistema_db -c "SELECT count(*) FROM pg_stat_activity;"
```

## 📚 DOCUMENTAÇÃO ADICIONAL

### Para Entender Melhor o Sistema:
```bash
# Documentação específica
ls docs/
cat docs/DOCUMENTACAO_PROJETO.md
cat docs/fluxo_aprovacao.md
cat docs/GRUPOS_ORGANIZACIONAIS.md

# Histórico de memória
ls docs/memoria/
cat docs/memoria/ANALISE_COMPLETA_TODAS_PLANILHAS.md
```

## 🤖 PROTOCOLO DE COLABORAÇÃO COM CLAUDE

### Como Trabalhar em Conjunto:
1. **Claude Code** é o especialista no contexto e histórico
2. **Codex CLI** (você) é especialista em execução e implementação
3. **Sempre** consulte Claude antes de mudanças importantes
4. **Documente** descobertas para ambos os assistentes
5. **Coordene** tarefas para evitar conflitos

### Padrão de Comunicação:
```bash
# Ao iniciar uma tarefa
echo "🤖 Codex: Iniciando [tarefa]. Claude, você tem algum contexto específico?"

# Ao encontrar problemas
echo "⚠️ Codex: Encontrei [problema]. Preciso de contexto histórico sobre [área]."

# Ao completar tarefa
echo "✅ Codex: Concluí [tarefa]. Resultado: [resumo]. Próximo passo sugerido: [ação]."
```

## 🎯 PRÓXIMOS PASSOS RECOMENDADOS

1. **Leia** todos os arquivos de contexto listados acima
2. **Execute** `docker-compose up -d` para subir o ambiente
3. **Acesse** http://localhost:8000 para ver o sistema funcionando
4. **Explore** as funcionalidades principais via interface web
5. **Converse** com Claude Code para coordenar próximas tarefas

---

**💡 Lembre-se**: Este é um sistema real em produção. Sempre faça backup antes de mudanças e siga as diretrizes de segurança.
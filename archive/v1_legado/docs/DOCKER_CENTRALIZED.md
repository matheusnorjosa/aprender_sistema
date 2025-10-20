# 🐳 SISTEMA CENTRALIZADO 100% DOCKER
**Sistema Aprender - Ambiente Único Dockerizado**
**Data**: 30/09/2025 20:00
**Status**: ✅ ATIVO - Centralização Completa

---

## 🎯 PRINCÍPIO FUNDAMENTAL

**TUDO RODA EM DOCKER. NADA RODA LOCALMENTE.**

Este documento é a **ÚNICA FONTE DE VERDADE** sobre o ambiente do sistema.

**IMPORTANTE**: Claude Code, Cursor AI, e qualquer outra IA **DEVEM SEMPRE LEMBRAR**:
- ✅ Sistema roda 100% em Docker
- ❌ Não usar `python` local
- ❌ Não usar `pip` local
- ❌ Não usar `.venv` local
- ✅ Todos os comandos via `docker-compose exec`

---

## 🏗️ ARQUITETURA DO SISTEMA

### **Containers Ativos**:

```
┌─────────────────────────────────────────────┐
│     DOCKER NETWORK: aprender_network       │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │  WEB (Django 4.2.24)                 │  │
│  │  - Python 3.13                       │  │
│  │  - Porta: 8000                       │  │
│  │  - Volume: ./                        │  │
│  └──────────────────────────────────────┘  │
│                   ↓                         │
│  ┌──────────────────────────────────────┐  │
│  │  DB (PostgreSQL 15)                  │  │
│  │  - Porta: 5433 (externa)             │  │
│  │  - Volume: postgres_data             │  │
│  └──────────────────────────────────────┘  │
│                                             │
└─────────────────────────────────────────────┘
```

### **Serviços Integrados** (MCPs):

```
┌─────────────────────────────────────────────┐
│         ECOSSISTEMA MCP - 8 SERVIÇOS        │
├─────────────────────────────────────────────┤
│                                             │
│  🧠 Serena MCP (porta 3007)                 │
│  ├─ Análise de código inteligente          │
│  ├─ Refatoração automatizada               │
│  └─ Code review com IA                     │
│                                             │
│  📊 RAGFlow (localhost:8081)                │
│  └─ Análise de documentos (79K+ registros) │
│                                             │
│  🚨 Sentry MCP (porta 3002)                 │
│  └─ Monitoramento de erros                 │
│                                             │
│  🐙 GitHub MCP (porta 3003)                 │
│  └─ Automação CI/CD                        │
│                                             │
│  🎭 Playwright MCP (porta 3004)             │
│  └─ Automação web/Google Sheets            │
│                                             │
│  📄 MarkItDown MCP (porta 3005)             │
│  └─ Conversão de documentos                │
│                                             │
│  🗄️ Context7 MCP (porta 3006)              │
│  └─ Banco vetorial semântico               │
│                                             │
│  ⚡ FastMCP (porta 3008)                    │
│  └─ Otimização de performance              │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 📋 COMANDOS ESSENCIAIS

### **Iniciar o Sistema**:
```bash
# Subir todos os containers
docker-compose up -d

# Ver status
docker-compose ps

# Ver logs em tempo real
docker-compose logs -f web
```

### **Comandos Django** (SEMPRE via Docker):
```bash
# Migrations
docker-compose exec web python manage.py migrate

# Criar superuser
docker-compose exec web python manage.py createsuperuser

# Shell Django
docker-compose exec web python manage.py shell

# Collectstatic
docker-compose exec web python manage.py collectstatic --no-input

# Qualquer comando Django
docker-compose exec web python manage.py <comando>
```

### **Banco de Dados**:
```bash
# Acessar PostgreSQL
docker-compose exec db psql -U adm_aprender -d aprender_sistema_db

# Backup do banco
docker-compose exec db pg_dump -U adm_aprender aprender_sistema_db > backup.sql

# Restaurar backup
docker-compose exec -T db psql -U adm_aprender aprender_sistema_db < backup.sql
```

### **Gerenciamento de Containers**:
```bash
# Parar tudo
docker-compose down

# Parar e remover volumes (⚠️ CUIDADO: perde dados!)
docker-compose down -v

# Rebuildar imagens
docker-compose build

# Rebuildar e subir
docker-compose up -d --build

# Ver logs de erro
docker-compose logs --tail=100 web

# Entrar no container
docker-compose exec web bash
```

---

## 🔧 INTEGRAÇÃO COM SERENA MCP

### **O que é Serena?**
Serena é uma IA especializada em análise e refatoração de código Python/Django.

### **Ferramentas do Serena**:
1. **Code Analysis**: Análise profunda de qualidade de código
2. **Refactoring**: Sugestões automatizadas de melhorias
3. **Code Review**: Review inteligente de pull requests
4. **Performance**: Identificação de gargalos
5. **Security**: Análise de vulnerabilidades

### **Como Usar Serena**:
```bash
# Via Claude Code (MCP integrado)
# Serena é acionado automaticamente quando você pede análise de código

# Exemplo:
# "Serena, analise o arquivo core/models.py e sugira melhorias"
```

### **Porta do Serena**: 3007
```bash
# Verificar se Serena está ativo
curl http://localhost:3007/health
```

---

## 🗂️ ESTRUTURA DE DADOS ORGANIZADA

### **Nova Estrutura** (após limpeza):
```
dados/
├── raw/
│   └── planilhas/          # JSONs extraídos das planilhas Google
│       ├── agenda_planilha_*.json
│       ├── controle_planilha_*.json
│       └── ...
├── processed/              # Dados processados/limpos
│   ├── dados_*.json
│   └── ...
├── mapeamentos/            # Mapeamentos e referências
│   ├── mapeamento_*.json
│   └── ...
└── backups/                # Backups de dados
    └── ...

reports/
└── lighthouse/             # Reports de performance
    ├── lighthouse-home.json
    └── ...

neural_system/
└── data/                   # Dados do sistema neural
    ├── neural_*.json
    └── ...
```

### **⚠️ IMPORTANTE**:
- ✅ Todos os JSONs foram movidos da raiz
- ✅ Organização clara por categoria
- ✅ ~200MB de dados organizados
- ❌ NÃO adicionar arquivos .json na raiz do projeto

---

## 🚫 O QUE FOI REMOVIDO (Limpeza Completa)

### **Arquivos de Configuração Duplicados**:
- ❌ `aprender_sistema/settings_backup.py`
- ❌ `aprender_sistema/settings_production.py`
- ❌ `aprender_sistema/settings_simple.py`
- ❌ `aprender_sistema/settings_unificado.py`
- ✅ **MANTIDO**: `aprender_sistema/settings.py` (único)

### **Docker Files Duplicados**:
- ❌ `docker-compose.dev.yml`
- ❌ `docker-compose.prod.yml`
- ❌ `docker-compose.unificado.yml`
- ❌ `Dockerfile.streamlit`
- ❌ `Dockerfile.mcp`
- ❌ `docker/dev/Dockerfile`
- ❌ `docker/prod/Dockerfile`
- ✅ **MANTIDOS**: `docker-compose.yml` + `Dockerfile`

### **.env Duplicados**:
- ❌ `.env.develop`
- ❌ `.env.docker`
- ❌ `.env.main`
- ✅ **MANTIDOS**: `.env.*.example` (templates apenas)

### **Ambientes Virtuais Antigos** (~500MB recuperados!):
- ❌ `backups/removed_directories/.venv/`
- ❌ `backups/removed_directories/venv/`
- ✅ **MANTIDO**: `.venv/` (local, mas será descontinuado)

### **Backups Desnecessários** (~5MB):
- ❌ `backups/removed_files/old_configs/`
- ❌ `backup_extensoes_cursor_*.txt`
- ❌ `backup_pre_unificacao_*.sql`
- ✅ **MANTIDO**: Backups essenciais comprimidos

### **Total Limpo**: ~770MB de duplicatas removidas!

---

## 🔒 SEGURANÇA E CREDENCIAIS

### **Variáveis de Ambiente** (Docker):
```bash
# .env (NÃO versionar!)
DB_NAME=aprender_sistema_db
DB_USER=adm_aprender
DB_PASSWORD=aprender123456
DB_HOST=db
DB_PORT=5432
SECRET_KEY=<gerado-automaticamente>
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1
```

### **Para Produção**:
```bash
# Usar .env.main.example como base
cp .env.main.example .env
# Editar com credenciais reais
```

---

## 📊 MONITORAMENTO

### **Logs**:
```bash
# Logs do Django
docker-compose logs -f web

# Logs do PostgreSQL
docker-compose logs -f db

# Logs de todos os containers
docker-compose logs -f
```

### **Health Checks**:
```bash
# Django
curl http://localhost:8000/health/

# PostgreSQL (dentro do container)
docker-compose exec db pg_isready -U adm_aprender

# Serena MCP
curl http://localhost:3007/health
```

---

## 🚀 DEPLOY EM PRODUÇÃO

### **Ambiente de Produção**:
```bash
# 1. Configurar variáveis de ambiente
export ENVIRONMENT=production
export SECRET_KEY=<chave-segura-gerada>
export DB_PASSWORD=<senha-forte>

# 2. Build otimizado
docker-compose -f docker-compose.yml build --no-cache

# 3. Subir em modo produção
docker-compose up -d

# 4. Migrations
docker-compose exec web python manage.py migrate

# 5. Collectstatic
docker-compose exec web python manage.py collectstatic --no-input
```

---

## 🐛 TROUBLESHOOTING

### **Container não sobe**:
```bash
# Ver logs de erro
docker-compose logs web

# Rebuildar imagem
docker-compose build web

# Reset completo
docker-compose down -v
docker-compose up -d --build
```

### **Erro de conexão com banco**:
```bash
# Verificar se DB está rodando
docker-compose ps db

# Ver logs do PostgreSQL
docker-compose logs db

# Testar conexão
docker-compose exec web python manage.py check --database default
```

### **Performance lenta**:
```bash
# Ver uso de recursos
docker stats

# Aumentar memória/CPU no docker-compose.yml
# resources:
#   limits:
#     cpus: '2.0'
#     memory: 2G
```

---

## 📚 REFERÊNCIAS E DOCUMENTAÇÃO

### **Documentos Relacionados**:
- `docs/AUDITORIA_COMPLETA_DUPLICATAS.md` - Auditoria de duplicatas
- `docs/SOLUCAO_ERRO_DJANGO_TEMPLATE.md` - Correção Django 4.2.24
- `.github/workflows/ci.yml` - Pipeline CI/CD
- `docker-compose.yml` - Configuração Docker principal

### **Repositórios MCPs**:
- **Serena**: https://github.com/oraios/serena
- **RAGFlow**: https://github.com/infiniflow/ragflow
- **Sentry MCP**: https://github.com/getsentry/sentry-mcp
- **Playwright MCP**: https://github.com/microsoft/playwright-mcp
- **Context7**: https://github.com/upstash/context7

---

## ⚠️ AVISOS IMPORTANTES

### **NUNCA FAZER**:
❌ Instalar pacotes Python localmente (`pip install`)
❌ Criar `.venv` localmente
❌ Rodar `python manage.py` localmente
❌ Commitar arquivos `.env` (exceto `.example`)
❌ Adicionar JSONs grandes na raiz do projeto
❌ Criar configurações duplicadas

### **SEMPRE FAZER**:
✅ Usar `docker-compose exec web` para comandos Python
✅ Manter apenas `docker-compose.yml` e `Dockerfile`
✅ Versionar apenas `.env.*.example` (templates)
✅ Organizar dados em `dados/` estruturado
✅ Consultar este documento para comandos

---

## 🎯 CHECKLIST PÓS-LIMPEZA

- [x] Remover venvs locais antigos (~500MB)
- [x] Remover settings.py duplicados (4 arquivos)
- [x] Remover docker-compose duplicados (6 arquivos)
- [x] Remover .env duplicados (6 arquivos)
- [x] Organizar JSONs da raiz (~200MB)
- [x] Limpar backups desnecessários (~5MB)
- [x] Atualizar .gitignore para Docker-only
- [x] Criar estrutura de dados organizada
- [x] Documentar comandos Docker
- [x] Documentar integração Serena MCP

**Total Economizado**: ~770MB de duplicatas removidas!

---

## 🤖 PARA IAs (Claude Code, Cursor, etc.)

**LEMBRAR SEMPRE**:
1. Sistema roda 100% em Docker
2. NUNCA sugerir comandos Python locais
3. SEMPRE usar `docker-compose exec web`
4. Consultar este documento para comandos corretos
5. Serena MCP está disponível para análise de código
6. Organização de dados em `dados/` estruturado
7. Uma única fonte de verdade para cada configuração

**Exemplo de comando CORRETO**:
```bash
# ✅ CORRETO
docker-compose exec web python manage.py migrate

# ❌ ERRADO
python manage.py migrate
```

---

**Última Atualização**: 30/09/2025 20:00
**Responsável**: Sistema Aprender - Equipe DevOps
**Status**: ✅ Documentação Completa e Atualizada

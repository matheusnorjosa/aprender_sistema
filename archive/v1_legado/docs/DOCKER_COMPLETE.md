# 🐳 DOCUMENTAÇÃO DOCKER COMPLETA - SISTEMA APRENDER

**Versão**: 3.0.0 Unificada
**Data**: 30 de Setembro de 2025
**Status**: ✅ Operacional

---

## 📑 ÍNDICE

1. [Visão Geral](#visão-geral)
2. [Arquitetura Unificada](#arquitetura-unificada)
3. [Dockerfile Multi-Stage](#dockerfile-multi-stage)
4. [Docker Compose com Profiles](#docker-compose-com-profiles)
5. [Scripts de Automação](#scripts-de-automação)
6. [Workflows Completos](#workflows-completos)
7. [Comandos Obrigatórios](#comandos-obrigatórios)
8. [Troubleshooting](#troubleshooting)

---

## 🎯 VISÃO GERAL

### Filosofia: "Everything in Docker"

O Sistema Aprender adota a filosofia **"TUDO no Docker"**, onde:
- ✅ **Todo desenvolvimento** é feito via containers
- ✅ **Todas as operações** são executadas via Docker Compose
- ✅ **Nenhum comando local** é necessário (exceto Docker)
- ✅ **Ambientes idênticos** em desenvolvimento e produção

### Stack Tecnológico

| Componente | Versão | Imagem Docker | Porta |
|------------|--------|---------------|-------|
| **Python** | 3.13-slim | python:3.13-slim | - |
| **Django** | 5.2.4 | (custom build) | 8000 |
| **PostgreSQL** | 15-alpine | postgres:15-alpine | 5432 |
| **Redis** | 7-alpine | redis:7-alpine | 6379 |
| **Nginx** | latest | (embutido prod) | 80/443 |
| **pgAdmin** | latest | dpage/pgadmin4 | 8080 |
| **Adminer** | 4-standalone | adminer:4-standalone | 8081 |
| **MailHog** | v1.0.1 | mailhog/mailhog:v1.0.1 | 1025/8025 |

---

## 🏗️ ARQUITETURA UNIFICADA

### Dockerfile Multi-Stage (4 stages)

```dockerfile
FROM python:3.13-slim as base          # Dependências comuns
FROM base as development               # Ferramentas de desenvolvimento
FROM base as builder                   # Build otimizado para produção
FROM base as production                # Runtime produção
```

### Docker Compose com Profiles

```bash
# Profiles disponíveis:
- default: db + web + redis (essencial)
- dev-tools: + pgAdmin, Adminer, MailHog
- production: + backup, monitoramento
- monitoring: + Watchtower
```

---

## 🚀 WORKFLOWS COMPLETOS

### Workflow 1: Setup Inicial

```bash
# 1. Clonar repositório
git clone https://github.com/matheusnorjosa/aprender_sistema.git
cd aprender_sistema

# 2. Configurar .env
cp .env.example .env

# 3. Build das imagens
ENVIRONMENT=development BUILD_TARGET=development docker-compose build

# 4. Iniciar serviços essenciais
docker-compose up -d db redis

# 5. Aplicar migrações
docker-compose exec web python manage.py migrate

# 6. Criar superusuário
docker-compose exec web python manage.py createsuperuser

# 7. Iniciar aplicação
docker-compose up -d web
```

### Workflow 2: Desenvolvimento Diário

```bash
# Manhã: Iniciar ambiente
git pull origin develop
docker-compose exec web python manage.py migrate
docker-compose up -d

# Durante o dia: Desenvolvimento
# Código está montado como volume, mudanças refletem automaticamente
docker-compose logs -f web

# Tarde: Commits
git add .
git commit -m "feat: nova funcionalidade"
git push origin feature/branch

# Noite: Parar ambiente
docker-compose down
```

### Workflow 3: Importação de Dados

```bash
# Importar usuários
docker-compose exec web python manage.py import_usuarios_contexto_supremo

# Importar agenda 2025
docker-compose exec web python manage.py import_agenda_2025_contexto_supremo --aba "Super"

# Importar disponibilidades
docker-compose exec web python manage.py import_disponibilidade_2025_contexto_supremo

# Verificar dados
docker-compose exec web python manage.py validar_dados_finais
```

---

## ⚠️ COMANDOS OBRIGATÓRIOS

### 🚫 PROIBIDO:
- ❌ `python manage.py` (ambiente local)
- ❌ `venv/Scripts/python manage.py` (ambiente local)
- ❌ Qualquer comando Django fora do container

### ✅ OBRIGATÓRIO:
- ✅ `docker exec aprender_web python manage.py` (dentro do container)
- ✅ `docker-compose` para gestão de serviços

### Comandos Essenciais

```bash
# Inicialização
docker-compose up -d
docker-compose logs -f web

# Django Management
docker exec aprender_web python manage.py makemigrations
docker exec aprender_web python manage.py migrate
docker exec -it aprender_web python manage.py createsuperuser
docker exec -it aprender_web python manage.py shell
docker exec aprender_web python manage.py test

# Banco de Dados
docker exec -it aprender_db psql -U adm_aprender -d aprender_sistema_db
docker exec aprender_db pg_dump -U adm_aprender -d aprender_sistema_db > backup.sql

# Verificações
docker exec aprender_web python manage.py check
docker exec aprender_web python manage.py health_check
```

---

## 🔧 TROUBLESHOOTING

### Problema 1: Container Web não inicia

```bash
# Ver logs
docker-compose logs web

# Rebuild do container
docker-compose build --no-cache web
docker-compose up -d
```

### Problema 2: PostgreSQL não conecta

```bash
# Verificar healthcheck
docker-compose ps

# Testar conexão
docker-compose exec db psql -U adm_aprender -d aprender_sistema_db -c "SELECT 1;"
```

### Problema 3: Permissões de volume

```bash
# Recriar volumes
docker-compose down -v
docker-compose up -d
```

### Problema 4: Porta já em uso

```bash
# Usar porta diferente
WEB_PORT=8001 docker-compose up -d
```

---

## 📊 MÉTRICAS E PERFORMANCE

### Tamanhos de Imagens

| Imagem | Tamanho Comprimido | Tamanho Descomprimido |
|--------|-------------------|----------------------|
| Python 3.13-slim (base) | 50MB | 150MB |
| Django Development | 250MB | 800MB |
| Django Production | 180MB | 600MB |
| PostgreSQL 15-alpine | 90MB | 240MB |
| Redis 7-alpine | 30MB | 80MB |

### Uso de Recursos (Desenvolvimento)

| Serviço | CPU (idle) | RAM (idle) | RAM (carga) |
|---------|------------|-----------|-------------|
| PostgreSQL | 1% | 50MB | 200MB |
| Django Web | 5% | 100MB | 300MB |
| Redis | <1% | 10MB | 50MB |
| pgAdmin | 2% | 80MB | 150MB |
| **Total** | **~8%** | **~240MB** | **~700MB** |

---

## 🎯 ESTADO ATUAL CONFIRMADO

### 📊 Dados Populados no Docker:
- ✅ **119 Usuários** (dados das planilhas + teste)
- ✅ **83 Formadores** (vinculados aos usuários)
- ✅ **10 Municípios** (dados reais)
- ✅ **8 Projetos** (dados reais)
- ✅ **PostgreSQL** funcionando
- ✅ **Aplicação** rodando na porta 8000

### 🔑 Usuários de Teste:
- `superintendente`
- `coordenador`
- `formador_teste`
- `controle`
- Qualquer CPF dos usuários das planilhas

---

## 📝 CHANGELOG

### Versão 3.0.0 Unificada (30/09/2025)
- ✅ Unificação completa de 4 arquivos Docker
- ✅ Workflows integrados
- ✅ Comandos obrigatórios consolidados
- ✅ Troubleshooting unificado

### Versão 2.0.0 (30/09/2025)
- ✅ Dockerfile multi-stage unificado
- ✅ Docker Compose com profiles
- ✅ Scripts de automação

### Versão 1.0.0 (01/09/2025)
- ✅ Versão inicial com arquivos separados

---

**🐳 LEMBRETE: TODO COMANDO DEVE SER EXECUTADO VIA DOCKER EXEC!**

*Documento unificado em: 2025-09-30*
*Status: ✅ AMBIENTE 100% DOCKERIZADO*

# Workflow Docker-first  Aprender Sistema

## Objetivo
Este documento define o workflow centralizado em Docker para desenvolvimento, garantindo paridade entre ambientes local e Docker, com todas as operações executadas de forma consistente.

## Estrutura de Arquivos

### Configurações de Ambiente
- **`.env.docker`** ’ Configurações específicas para containers Docker
- **`docker-compose.yml`** ’ Definição dos serviços (web, db, redis, pgadmin, mcp)
- **`.pre-commit-config.yaml`** ’ Hooks configurados para executar via Docker

### Scripts Wrapper
- **`scripts/docker-run.sh`** ’ Script principal para executar qualquer comando no container
- **`scripts/test.sh`** ’ Executa testes Django via Docker
- **`scripts/lint.sh`** ’ Executa linting completo via Docker
- **`scripts/format.sh`** ’ Executa formatação de código via Docker
- **`scripts/migrate.sh`** ’ Executa migrações Django via Docker

## Comandos Padronizados

### Desenvolvimento Diário
```bash
# Iniciar ambiente completo
docker-compose up -d

# Executar servidor de desenvolvimento
./scripts/docker-run.sh python manage.py runserver

# Executar shell Django
./scripts/docker-run.sh python manage.py shell

# Executar shell bash no container
./scripts/docker-run.sh bash
```

### Testes e Qualidade
```bash
# Executar testes
./scripts/test.sh

# Executar linting
./scripts/lint.sh

# Executar formatação
./scripts/format.sh

# Executar pre-commit
pre-commit run --all-files
```

### Migrações e Banco
```bash
# Executar migrações
./scripts/migrate.sh

# Criar superusuário
./scripts/docker-run.sh python manage.py createsuperuser

# Executar comandos customizados
./scripts/docker-run.sh python manage.py import_formadores
```

## Configuração Inicial

### 1. Primeira execução
```bash
# Construir e iniciar containers
docker-compose up -d --build

# Executar migrações iniciais
./scripts/migrate.sh

# Criar superusuário
./scripts/docker-run.sh python manage.py createsuperuser
```

### 2. Instalar pre-commit
```bash
# Instalar pre-commit localmente (apenas uma vez)
pip install pre-commit
pre-commit install
```

## Variáveis de Ambiente

### `.env.docker` (Usado nos containers)
```env
ENVIRONMENT=staging
DEBUG=True
SECRET_KEY=django-development-key-not-for-production

# Database (Docker)
DB_HOST=db
DB_PORT=5432
DB_NAME=aprender_sistema_db
DB_USER=adm_aprender
DB_PASSWORD=aprender123456

# Cache (Docker)
CACHE_LOCATION=redis://redis:6379/1

# Celery (Docker)
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

### Ambiente Local (para referência)
- **DB_HOST**: `localhost` (para acesso direto ao PostgreSQL)
- **DB_PORT**: `5433` (porta externa do Docker)

## Vantagens do Workflow

###  Consistência
- Todos os comandos executam no mesmo ambiente
- Mesmas versões de Python, Django e dependências
- Eliminação de problemas "funciona na minha máquina"

###  Isolamento
- Ambiente de desenvolvimento isolado do sistema local
- Dependências gerenciadas pelo Docker
- Fácil reset do ambiente completo

###  Produtividade
- Scripts wrapper simplificam comandos complexos
- Pre-commit hooks garantem qualidade do código
- Ambiente pronto em segundos com `docker-compose up`

###  Colaboração
- Todos os desenvolvedores usam exatamente o mesmo ambiente
- Documentação centralizada e atualizada
- Commits padronizados e testados

## Troubleshooting

### Container não inicia
```bash
# Verificar logs
docker-compose logs web

# Reconstruir containers
docker-compose down
docker-compose up -d --build
```

### Problemas de permissão
```bash
# Dar permissão aos scripts
chmod +x scripts/*.sh
```

### Banco de dados
```bash
# Acessar PostgreSQL diretamente
docker-compose exec db psql -U adm_aprender -d aprender_sistema_db

# Verificar status do banco via pgAdmin
# http://localhost:8080 (admin@admin.com / admin)
```

### Reset completo
```bash
# Parar e remover tudo
docker-compose down -v

# Reconstruir do zero
docker-compose up -d --build
./scripts/migrate.sh
```

## Integração com Git

### Pre-commit
- Configurado para executar Black e isort via Docker
- Impede commits com código mal formatado
- Mantém consistência no repositório

### Workflow recomendado
1. `git checkout -b feature/nova-funcionalidade`
2. Desenvolver usando scripts Docker
3. `./scripts/test.sh` ’ verificar se testes passam
4. `./scripts/lint.sh` ’ verificar qualidade do código
5. `git commit` ’ pre-commit roda automaticamente
6. `git push` ’ push para repositório

## Próximos Passos

- [ ] Configurar CI/CD para usar mesmos scripts Docker
- [ ] Adicionar testes de integração automatizados
- [ ] Configurar monitoring e logging
- [ ] Documentar deploy de produção

---

**Princípio**: *"Um comando, um resultado, qualquer máquina"*

Mantenha este workflow atualizado conforme o projeto evolui.
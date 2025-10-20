# 🚀 Aprender Sistema v2 — Skeleton

**Status**: 🚧 Em Construção
**Versão**: 2.0.0-alpha
**Data**: 2025-10-10

---

## 📋 Visão Geral

Este diretório contém o **esqueleto (skeleton)** do AS v2, uma reescrita completa do sistema de gestão de eventos e disponibilidade de formadores.

**Principais mudanças vs. v1**:
- ❌ Elimina 82.389 fórmulas Excel/Google Sheets
- ✅ Single Source of Truth em PostgreSQL 15
- ✅ Backend Django 5.2 + DRF
- ✅ Arquitetura de microsserviços (web + worker + beat)
- ✅ Testes automatizados (TDD)
- ✅ CI/CD com GitHub Actions

---

## 📁 Estrutura de Diretórios

```
v2/
├── backend/              # Código Django
│   ├── apps/
│   │   ├── core/         # App principal (models, services, views)
│   │   └── dat_ingest/   # App de ingestão (ETL)
│   ├── config/           # Settings Django
│   ├── services/         # Serviços compartilhados
│   └── requirements.txt  # Dependências Python
│
├── frontend/             # (Futuro) React/Vue ou Templates Django
│   └── src/
│
├── infra/                # Infraestrutura Docker
│   ├── Dockerfile        # Multi-stage build
│   ├── docker-compose.yml
│   ├── entrypoint.sh
│   └── Makefile          # Comandos unificados
│
└── docs/                 # Documentação técnica
    ├── BLUEPRINT.md              # Arquitetura de alto nível
    ├── SINGLE_SOURCE_OF_TRUTH.md # Regras de integridade de dados
    ├── MIGRATION_PLAN.md         # Plano de migração v1→v2
    └── TESTS_PLAN.md             # Estratégia de testes
```

---

## 🚀 Quick Start

### 1. Pré-requisitos

- Docker 24+ & Docker Compose 2+
- Git
- (Opcional) Make

### 2. Clonar e Configurar

```bash
cd v2/

# Copiar .env de exemplo
cp .env.example .env

# Editar variáveis de ambiente
nano .env
```

### 3. Build e Start

```bash
# Via Makefile (recomendado)
cd infra/
make build
make up

# Ou via docker-compose direto
docker compose up -d --build
```

### 4. Executar Migrations

```bash
make migrate

# Ou via docker-compose
docker compose exec web python manage.py migrate
```

### 5. Criar Superuser

```bash
make superuser

# Ou via docker-compose
docker compose exec web python manage.py createsuperuser
```

### 6. Acessar a Aplicação

- **Web**: http://localhost:8000
- **Admin**: http://localhost:8000/admin
- **API Docs**: http://localhost:8000/api/docs/
- **Health Check**: http://localhost:8000/api/health/

---

## 🧪 Testes

```bash
# Todos os testes
make test

# Apenas unit tests
make test-unit

# Apenas integration tests
make test-integration

# E2E tests (Playwright)
make test-e2e

# Relatório de cobertura
make coverage
```

**Meta de cobertura**: 90%+ (crítico: 100%)

---

## 🔄 ETL (Migração de Dados)

### Executar ETL Completo

```bash
# Modo dry-run (simulação)
make etl-dry-run

# Execução real
make etl-all
```

### ETL Parcial

```bash
# Apenas usuários
make etl-usuarios

# Apenas eventos da agenda
make etl-agenda
```

### Verificar Integridade

```bash
make check-integrity
```

**Resultado esperado**:
- ✅ 139 usuários
- ✅ 88 formadores
- ✅ 2.242 solicitações aprovadas
- ✅ 0 dados órfãos (FKs válidas)

---

## 📊 Monitoramento

### Health Check

```bash
make health
```

**Resposta esperada**:
```json
{
  "status": "healthy",
  "database": "ok",
  "redis": "ok",
  "celery": "ok"
}
```

### Logs

```bash
# Web
make logs

# Worker
docker compose logs -f worker

# Todos
docker compose logs -f
```

### Estatísticas

```bash
make stats
```

---

## 🛠️ Comandos Úteis

| Comando | Descrição |
|---------|-----------|
| `make help` | Listar todos os comandos disponíveis |
| `make up` | Iniciar serviços |
| `make down` | Parar serviços |
| `make restart` | Reiniciar serviços |
| `make shell` | Abrir Django shell |
| `make db-shell` | Abrir PostgreSQL shell |
| `make db-backup` | Fazer backup do banco |
| `make clean` | Remover containers e volumes (⚠️ CUIDADO!) |

---

## 📚 Documentação

- **Arquitetura**: [BLUEPRINT.md](docs/BLUEPRINT.md)
- **Single Source of Truth**: [SINGLE_SOURCE_OF_TRUTH.md](docs/SINGLE_SOURCE_OF_TRUTH.md)
- **Plano de Migração**: [MIGRATION_PLAN.md](docs/MIGRATION_PLAN.md)
- **Testes**: [TESTS_PLAN.md](docs/TESTS_PLAN.md)
- **Learning Report**: [AS_LEARNING_REPORT_20251010.md](../docs/AS_LEARNING_REPORT_20251010.md)

---

## 🔐 Segurança

### Variáveis de Ambiente Sensíveis

⚠️ **NUNCA** commitar estas variáveis:
- `SECRET_KEY`
- `DB_PASSWORD`
- `GOOGLE_SERVICE_ACCOUNT_PATH`
- `SENTRY_DSN`

### Checklist de Segurança

- [ ] SECRET_KEY forte em produção (50+ chars aleatórios)
- [ ] DEBUG=0 em produção
- [ ] ALLOWED_HOSTS configurado
- [ ] CSRF_TRUSTED_ORIGINS configurado
- [ ] SECURE_SSL_REDIRECT=True em produção
- [ ] HTTPS configurado (Let's Encrypt)
- [ ] Sentry configurado para monitoramento

---

## 🤝 Contribuindo

### Workflow de Desenvolvimento

1. Criar branch: `git checkout -b feat/minha-feature`
2. Implementar com TDD (Red→Green→Refactor)
3. Executar testes: `make test`
4. Executar linters: `make lint`
5. Commit: `git commit -m "feat: descrição"`
6. Push: `git push origin feat/minha-feature`
7. Abrir Pull Request

### Padrões de Commit

- `feat:` Nova funcionalidade
- `fix:` Correção de bug
- `refactor:` Refatoração de código
- `test:` Adicionar/melhorar testes
- `docs:` Documentação
- `chore:` Tarefas de manutenção

---

## 🚧 Status de Implementação

| Fase | Status | Descrição |
|------|--------|-----------|
| **Preparação** | ✅ Completo | Backup, infra, análise |
| **ETL** | 🚧 Em Progresso | Migração de dados |
| **Backend Services** | ⏳ Pendente | ConflictChecker, DisponibilidadeService |
| **Frontend** | ⏳ Pendente | Templates, forms |
| **Testes** | ⏳ Pendente | Unit, integration, E2E |
| **Deploy** | ⏳ Pendente | Staging, produção |

---

## 📞 Suporte

- **Email**: dev@aprender.com.br
- **Issue Tracker**: [GitHub Issues](https://github.com/seu-usuario/aprender_sistema/issues)
- **Documentação**: [Wiki](https://github.com/seu-usuario/aprender_sistema/wiki)

---

**Última atualização**: 2025-10-10
**Próximos Passos**: Implementar Fase 2 (ETL) conforme [MIGRATION_PLAN.md](docs/MIGRATION_PLAN.md)

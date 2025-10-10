# 🎓 Sistema Aprender

[![Django](https://img.shields.io/badge/Django-5.2-092E20?logo=django)](https://docs.djangoproject.com/en/5.2/)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?logo=postgresql)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)](https://www.docker.com/)
[![CI](https://img.shields.io/github/actions/workflow/status/[USUARIO]/aprender_sistema/ci.yml?branch=main&label=CI)](https://github.com/[USUARIO]/aprender_sistema/actions)

> **Sistema de gestão educacional** para solicitação, aprovação e agendamento de eventos formativos com integração ao Google Calendar.

## 🚀 Início Rápido

### Pré-requisitos
- Python 3.13+
- PostgreSQL 15+ (ou Docker)
- Git
- Node.js 18+ (opcional, para ferramentas de desenvolvimento)

### 🐳 Setup com Docker (Recomendado)

```bash
# 1. Clone o repositório
git clone https://github.com/[USUARIO]/aprender_sistema.git
cd aprender_sistema

# 2. Configure as variáveis de ambiente
cp .env.example .env
# Edite .env com suas configurações

# 3. Execute em modo desenvolvimento (runserver)
make dev

# OU execute em modo produção (Gunicorn)
make prod

# 4. Acesse o sistema
# http://localhost:8000 - Sistema principal
# http://localhost:8000/admin - Painel administrativo
# http://localhost:8000/healthz/ - Health check
```

## Stack & Containers (centralizado)

- Docker único (`docker-compose.yml`) controla **dev** e **prod** via `RUN_MODE`.
- Healthcheck: `GET /healthz/` → `{"status":"ok","db":"ok"}`.

### Primeira execução (dev)

```bash
cp .env.example .env
make dev
curl http://localhost:8000/healthz/
```

### Alternar para prod-like (Gunicorn)

```bash
RUN_MODE=prod make up
# ou
make prod
curl http://localhost:8000/healthz/
```

### 💻 Setup Local (Desenvolvimento)

```bash
# 1. Clone e entre no diretório
git clone https://github.com/[USUARIO]/aprender_sistema.git
cd aprender_sistema

# 2. Crie ambiente virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate

# 3. Instale dependências
pip install -r requirements-dev.txt

# 4. Configure ambiente
cp .env.example .env
# Edite .env com suas configurações locais

# 5. Execute migrações
python manage.py migrate

# 6. Carregue dados iniciais
python manage.py loaddata fixtures/initial_data.json

# 7. Execute o servidor
python manage.py runserver
```

## 🏗️ Arquitetura do Sistema

### Stack Tecnológico
- **Backend**: Django 5.2 + Django REST Framework
- **Banco**: PostgreSQL 15 (desenvolvimento: SQLite)
- **Frontend**: HTML5 + CSS3 + Bootstrap 5 + JavaScript ES6
- **Integração**: Google Calendar API + Google Sheets API
- **Deploy**: Docker + Docker Compose
- **CI/CD**: GitHub Actions

### Estrutura do Projeto
```
aprender_sistema/
├── 🐍 Python Django Apps
│   ├── core/                 # App principal (models, views, templates)
│   ├── api/                  # API REST endpoints
│   ├── relatorios/          # Relatórios e dashboards
│   └── aprender_sistema/    # Configurações Django
├── 🐳 Docker & Deploy
│   ├── docker/              # Dockerfiles por ambiente
│   ├── docker-compose.yml   # Orquestração de containers
│   └── scripts/             # Scripts de automação
├── 📖 Documentação
│   ├── docs/                # Documentação técnica
│   └── README.md           # Este arquivo
└── 🔧 Configuração
    ├── .env.example        # Template de variáveis de ambiente
    ├── requirements*.txt   # Dependências Python
    └── pyproject.toml     # Configurações de lint/format
```

## 🔐 Configuração de Ambiente

### Variáveis de Ambiente Essenciais

Copie `.env.example` para `.env` e configure:

```bash
# === AMBIENTE ===
ENVIRONMENT=development  # development | staging | production
DEBUG=True
SECRET_KEY=your-secret-key-here

# === DATABASE ===
DATABASE_URL=postgresql://user:pass@localhost:5432/aprender_sistema
# OU para desenvolvimento local:
# DATABASE_URL=sqlite:///db.sqlite3

# === GOOGLE INTEGRATIONS ===
GOOGLE_CALENDAR_ID=seu-calendar-id@group.calendar.google.com
GOOGLE_CREDENTIALS_JSON='{...}'  # Service Account JSON
GOOGLE_CALENDAR_TIME_ZONE=America/Fortaleza

# === EMAIL (Opcional) ===
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True

# === SECURITY ===
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,http://localhost:8000
```

### 🔑 Configuração Google Calendar

1. **Criar Service Account**:
   - Acesse [Google Cloud Console](https://console.cloud.google.com/)
   - Crie projeto ou selecione existente
   - Habilite Google Calendar API
   - Crie Service Account e baixe JSON

2. **Configurar Calendar**:
   ```bash
   # Copie o JSON para a variável de ambiente
   export GOOGLE_CREDENTIALS_JSON='{"type": "service_account", ...}'

   # Configure o ID do calendário
   export GOOGLE_CALENDAR_ID='seu-calendar@group.calendar.google.com'
   ```

3. **Testar Integração**:
   ```bash
   python manage.py shell -c "from core.services.integrations.google_calendar import GoogleCalendarService; GoogleCalendarService().test_connection()"
   ```

## 🔄 Fluxo de Trabalho

### Processo de Solicitação → Aprovação → Agenda

```mermaid
graph LR
    A[Coordenador] --> B[Solicita Evento]
    B --> C[Verificação Automática]
    C --> D{Conflitos?}
    D -->|Não| E[Superintendência]
    D -->|Sim| F[Retorna para Ajustes]
    E --> G{Aprovado?}
    G -->|Sim| H[Pré-Agenda]
    G -->|Não| I[Rejeitado]
    H --> J[Controle]
    J --> K[Google Calendar]
    K --> L[Evento Criado]
```

### Perfis de Usuário

| Perfil | Funcionalidades |
|--------|----------------|
| 👨‍🏫 **Formador** | Bloquear agenda, visualizar eventos |
| 👨‍💼 **Coordenador** | Solicitar eventos, acompanhar status |
| 👨‍💻 **Controle** | Pré-agenda, sincronização Calendar |
| 🏢 **Superintendência** | Aprovar/reprovar solicitações |
| 📊 **Diretoria** | Dashboards, relatórios executivos |
| ⚙️ **Admin** | Gestão completa do sistema |

## 🔐 RBAC (Role-Based Access Control)

O sistema utiliza Django Groups para controle de acesso baseado em papéis (RBAC).

### Grupos Canônicos

| Grupo | Código | Permissões |
|-------|--------|-----------|
| **Coordenador** | `coordenador` | Criar solicitações de eventos |
| **Formador** | `formador` | Visualizar próprios eventos, bloquear agenda |
| **Controle** | `controle` | Gerenciar pré-agenda, sincronizar Google Calendar |
| **Gerente Super** | `gerente_super` | Aprovar/reprovar solicitações da Superintendência |
| **DAT** | `dat` | Ingerir dados, visualizar dashboards QA |
| **Admin Ops** | `admin_ops` | Acesso administrativo completo |

### Bootstrap do Sistema RBAC

Após configurar o banco de dados, execute o comando para criar grupos e permissões:

```bash
# Via Docker (recomendado)
make bootstrap-rbac

# Ou diretamente
docker compose exec -T web python manage.py bootstrap_rbac --verbose

# Ou local (sem Docker)
python manage.py bootstrap_rbac --verbose
```

**Saída esperada:**
```
=== BOOTSTRAP RBAC SYSTEM ===

[1/3] Creating canonical groups...
  ✓ Created: coordenador
  ✓ Created: formador
  ✓ Created: controle
  ✓ Created: gerente_super
  ✓ Created: dat
  ✓ Created: admin_ops

[2/3] Assigning native model permissions...
[3/3] Assigning custom permissions...

=== SUMMARY ===
Groups created: 6
Native permissions assigned: 42
Custom permissions assigned: 8

✓ RBAC bootstrap completed successfully!
```

### Atribuir Grupos a Usuários

Via Django Admin (`/admin/`):
1. Acesse **Usuários**
2. Selecione o usuário
3. Na seção **Permissões**, adicione grupos em **groups**
4. Salve

Via Django Shell:
```python
from django.contrib.auth import get_user_model
from core.rbac import assign_user_to_group, CONTROLE, DAT

User = get_user_model()
user = User.objects.get(username='johndoe')

# Adicionar aos grupos
assign_user_to_group(user, CONTROLE)
assign_user_to_group(user, DAT)

# Verificar grupos
print(user.groups.values_list('name', flat=True))
# Output: <QuerySet ['controle', 'dat']>
```

### Endpoints da API

**GET /api/me/** - Informações do usuário autenticado
```json
{
  "username": "johndoe",
  "email": "johndoe@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "is_staff": true,
  "is_superuser": false,
  "groups": ["controle", "dat"]
}
```

**GET /api/ingest/health/** - Health check (requer DAT, Controle ou Admin Ops)
```json
{
  "eventos": {"count": 1234, "last_updated": "2025-01-15T10:30:00Z"},
  "pessoas": {"count": 5678, "last_updated": "2025-01-15T10:30:00Z"},
  ...
}
```

### Uso em Views Django

```python
from core.rbac import require_groups, CONTROLE, ADMIN_OPS

@require_groups(CONTROLE, ADMIN_OPS)
def controle_dashboard(request):
    return render(request, 'dashboard.html')
```

### Uso em DRF ViewSets

```python
from rest_framework import viewsets
from core.rbac import IsControle, IsDat

class DataViewSet(viewsets.ModelViewSet):
    permission_classes = [IsControle | IsDat]
    # ...
```

## 📅 Google Calendar Sync (DAT-P04-GCAL-v2)

Sistema de sincronização idempotente entre pré-agenda e Google Calendar.

### Pré-requisitos

1. **Calendar ID**: Obtenha o ID do calendário Google "Formações"
   - Acesse Google Calendar → Configurações
   - Copie o ID do calendário (formato: `c_xxxxx@group.calendar.google.com`)

2. **Credenciais de Autenticação** (escolha uma):

   **Opção A - Service Account (Recomendado para produção)**:
   ```bash
   # 1. Crie Service Account no Google Cloud Console
   # 2. Baixe o arquivo JSON
   # 3. Configure variável de ambiente:
   export GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'
   ```

   **Opção B - OAuth Client (Desenvolvimento)**:
   ```bash
   # 1. Configure OAuth no Google Cloud Console
   # 2. Baixe credentials.json
   # 3. Execute fluxo OAuth uma vez:
   python scripts/oauth/configurar_oauth.py
   # 4. Token salvo em .gcal_token.json automaticamente
   ```

### Configuração de Ambiente

Adicione ao `.env` ou `docker-compose.yml`:

```bash
# ID do calendário Google
GCAL_CALENDAR_ID=c_xxxxx@group.calendar.google.com

# Service Account JSON (inline ou path)
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}

# OU OAuth (fallback)
GOOGLE_OAUTH_CLIENT_ID=xxxxx.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=xxxxx

# Timezone
TZ=America/Fortaleza
```

### Uso

**Dry-run (simulação sem criar eventos)**:
```bash
# Via Makefile
make preagenda-dryrun

# Ou diretamente
docker compose exec -T web python manage.py preagenda_to_gcal --dry-run
```

**Sincronização real**:
```bash
# Via Makefile
make preagenda-sync

# Ou diretamente
docker compose exec -T web python manage.py preagenda_to_gcal
```

**Com limite (testes)**:
```bash
docker compose exec -T web python manage.py preagenda_to_gcal --dry-run --limit 10
```

### Idempotência

O sistema garante que **eventos não sejam duplicados** usando `external_hash` (SHA1):

- **1ª execução**: Evento criado no Google Calendar
- **2ª execução**: Evento atualizado (se houve mudanças) ou ignorado (sem mudanças)
- **Múltiplas execuções**: Sempre idempotente

```bash
# Executar 3 vezes seguidas:
make preagenda-sync  # → 50 eventos criados
make preagenda-sync  # → 50 eventos ignorados (sem mudanças)
make preagenda-sync  # → 50 eventos ignorados (sem mudanças)
```

### Relatórios

Após cada execução, relatórios são gerados em `./out_gcal/`:

- **`gcal_results.csv`**: Todos os resultados (created, updated, skipped, etc.)
- **`gcal_errors.csv`**: Apenas eventos com erro
- **`gcal_audit.md`**: Resumo executivo da execução

**Exemplo de `gcal_audit.md`**:
```markdown
# Google Calendar Sync Report

**Run ID**: `550e8400-e29b-41d4-a716-446655440000`
**Data/Hora**: 2025-01-15 14:30:00
**Modo**: PRODUÇÃO

---

## Resumo

| Métrica              | Quantidade |
|----------------------|------------|
| Total processado     | 50         |
| ✓ Criados           | 45         |
| ↻ Atualizados       | 3          |
| – Ignorados         | 2          |
| ⚠ Duplicados remotos | 0          |
| ✗ Erros             | 0          |
```

### Logs de Auditoria

Todas as operações são registradas no banco de dados (`CalendarSyncLog`):

```python
from core.models import CalendarSyncLog

# Ver últimas sincronizações
logs = CalendarSyncLog.objects.all()[:10]

# Filtrar por run_id (batch)
run_id = "550e8400-e29b-41d4-a716-446655440000"
logs = CalendarSyncLog.objects.filter(run_id=run_id)

# Ver apenas erros
errors = CalendarSyncLog.objects.filter(action="error")
```

### RBAC

Apenas usuários com permissões adequadas podem executar:
- ✅ **Controle**: Pode sincronizar
- ✅ **Admin Ops**: Pode sincronizar
- ✅ **Superuser**: Pode sincronizar
- ❌ Outros perfis: Acesso negado

### Troubleshooting

**❌ Erro: `GCAL_CALENDAR_ID not found`**
```bash
# Configurar variável de ambiente
export GCAL_CALENDAR_ID=c_xxxxx@group.calendar.google.com
```

**❌ Erro: `No credentials found`**
```bash
# Verificar Service Account
echo $GOOGLE_SERVICE_ACCOUNT_JSON

# Ou verificar OAuth token
ls -la .gcal_token.json
```

**❌ Erro: `HTTP 403 Forbidden`**
```bash
# Verificar permissões do Service Account no Google Calendar
# O Service Account deve ter permissão "Make changes to events" no calendário
```

**❌ Erro: `HTTP 429 Rate Limit`**
```bash
# O sistema já implementa retry automático com backoff exponencial
# Aguardar alguns segundos e tentar novamente
```

## 🧪 Testes

### Executar Testes

```bash
# Todos os testes
python manage.py test

# Testes específicos
python manage.py test core.tests.test_models
python manage.py test core.tests.test_views

# Com coverage
coverage run --source='.' manage.py test
coverage report
coverage html  # Relatório HTML em htmlcov/
```

### Testes E2E (Playwright)

```bash
# Instalar Playwright
pip install playwright
playwright install

# Executar testes E2E
python -m pytest tests/e2e/ -v
```

## 🚀 Deploy

### Ambientes

| Branch | Ambiente | URL | Auto-Deploy |
|--------|----------|-----|-------------|
| `dev` | Desenvolvimento | http://localhost:8000 | ❌ Manual |
| `homolog` | Staging | https://staging.aprender.com | ✅ Auto |
| `main` | Produção | https://aprender.com | ⚠️ Manual + Review |

### Deploy Staging (Render)

1. **Configure secrets no GitHub**:
   ```
   RENDER_API_KEY=your-render-api-key
   DATABASE_URL=postgresql://...
   GOOGLE_CREDENTIALS_JSON={"type": "service_account"...}
   ```

2. **Push para branch `homolog`**:
   ```bash
   git push origin homolog
   # Deploy automático via GitHub Actions
   ```

### Deploy Produção

1. **Criar Release**:
   ```bash
   # Atualizar CHANGELOG.md
   git tag v1.2.3
   git push origin v1.2.3
   ```

2. **GitHub Actions executará**:
   - ✅ Testes completos
   - ✅ Build da imagem Docker
   - ✅ Deploy para produção
   - ✅ Migrações automáticas
   - ✅ Coleta de arquivos estáticos

## 🛠️ Desenvolvimento

### Comandos Úteis

```bash
# Executar servidor de desenvolvimento
make dev
# ou: python manage.py runserver

# Executar testes
make test
# ou: python manage.py test

# Lint e formatação
make lint
# ou: black . && flake8 . && isort .

# Migrações
make migrate
# ou: python manage.py makemigrations && python manage.py migrate

# Coleta de estáticos
make collectstatic
# ou: python manage.py collectstatic --noinput
```

### Pre-commit Hooks

```bash
# Instalar hooks
pre-commit install

# Executar manualmente
pre-commit run --all-files
```

### Estrutura de Branches

```
main (produção)
├── homolog (staging)
│   ├── dev (desenvolvimento)
│   │   ├── feat/nova-funcionalidade
│   │   ├── fix/correcao-bug
│   │   └── chore/atualizacao-dependencias
```

### Convenção de Commits

```bash
feat: adicionar sistema de notificações por email
fix: corrigir erro na validação de datas
docs: atualizar README com instruções de deploy
chore: atualizar dependências do Django para 5.2.4
test: adicionar testes para módulo de calendário
```

## 📊 Monitoramento

### Health Checks

- 🟢 **Sistema**: http://localhost:8000/health/
- 🟢 **Database**: http://localhost:8000/health/db/
- 🟢 **Google Calendar**: http://localhost:8000/health/calendar/

### Métricas (Produção)

- **Performance**: Tempo de resposta < 500ms
- **Disponibilidade**: 99.9% uptime
- **Integrações**: Sync Google Calendar < 30s

## 🐛 Troubleshooting

### Problemas Comuns

**❌ Erro: `django.db.utils.OperationalError`**
```bash
# Verifique se PostgreSQL está rodando
docker-compose up db -d

# Execute migrações
python manage.py migrate
```

**❌ Google Calendar API Error**
```bash
# Verifique credenciais
python manage.py shell -c "import os; print(os.getenv('GOOGLE_CREDENTIALS_JSON'))"

# Teste conexão
python manage.py test_google_calendar
```

**❌ CSS/JS não carregando**
```bash
# Colete arquivos estáticos
python manage.py collectstatic

# Verifique DEBUG=True em desenvolvimento
```

### Logs

```bash
# Docker Compose
docker-compose logs -f web

# Local
tail -f logs/django.log

# Specific service
docker-compose logs -f db
```

## 🤝 Contribuição

Ver [CONTRIBUTING.md](./CONTRIBUTING.md) para guidelines detalhados.

### Quick Start para Contribuição

1. Fork o repositório
2. Crie branch: `git checkout -b feat/minha-feature`
3. Implemente com testes
4. Execute lint: `make lint`
5. Commit: `git commit -m "feat: minha nova feature"`
6. Push: `git push origin feat/minha-feature`
7. Abra Pull Request

## 📄 Licença

Este projeto está licenciado sob a **MIT License** - veja [LICENSE](./LICENSE) para detalhes.

## 🆘 Suporte

- 📧 **Email**: dev@aprender.com
- 💬 **Issues**: [GitHub Issues](https://github.com/[USUARIO]/aprender_sistema/issues)
- 📚 **Docs**: [Wiki do Projeto](https://github.com/[USUARIO]/aprender_sistema/wiki)

## 📈 Status do Projeto

- ✅ **v1.0**: Sistema base de solicitações (Q3 2024)
- ✅ **v1.1**: Integração Google Calendar (Q4 2024)  
- ✅ **v1.2**: Sistema de pré-agenda (Q1 2025)
- ✅ **v1.3**: Dashboards executivos (Q2 2025)

---

<div align="center">
  <strong>Desenvolvido com ❤️ pela equipe DAT</strong><br>
  <em>Transformando educação através da tecnologia</em>
</div>

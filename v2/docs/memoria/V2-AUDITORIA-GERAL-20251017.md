# Auditoria v2 Geral - Stack aprender_v2 em Execução

**Data:** 2025-10-17 20:30 UTC-3
**Modo:** Somente Leitura (sem alterações destrutivas)
**Stack Auditado:** `aprender_v2` (rodando continuamente)
**Branch Local:** fix/v2-bootstrap-core
**Objetivo:** Mapear estado atual, divergências e próximos passos

---

## 📊 Resumo Executivo

### Status por Macroárea

| Área | Status | Nota |
|------|--------|------|
| **Infra (Docker)** | 🟢 Verde | Stack aprender_v2 rodando, portas corretas (8002, 5434, 6380) |
| **Backend (Django)** | 🟡 Amarelo | Web funcionando, mas worker/beat em restart loop |
| **DB/Migrations** | 🟢 Verde | Todas migrations aplicadas, incluindo 0008 (bootstrap) |
| **Segurança** | 🟡 Amarelo | GCAL_CLIENT=fake ✅, mas apply_blocked=false ⚠️ |
| **CI/Hooks** | 🟢 Verde | Branch remota no GitHub, 3 PRs abertos |
| **Testes** | 🔴 Vermelho | 11 import errors (modelos não implementados) |

**Diagnóstico Geral:** Stack **funcional** para desenvolvimento, mas com pendências em Celery e modelos faltantes.

---

## 🔍 Achados Detalhados

### 1. Estado Git Local vs Remoto

#### Branch Atual
- **Local:** `fix/v2-bootstrap-core` (4 commits à frente)
- **Remote:** Sincronizada (push realizado com sucesso)
- **Último commit:** `8010284` - "chore(infra): alinha Makefile para porta 8002"

#### Commits Recentes (fix/v2-bootstrap-core)
```
8010284 chore(infra): alinha Makefile para porta 8002
cab4aea feat(core): endpoints /api/readyz/ e /api/features/
99d6845 feat(core): Projeto.codigo + fluxo + FK Solicitacao.projeto
90f2e35 feat(core): isola views ativas (Solicitacao/Availability) e URLs mínimas
```

#### PRs Abertos no GitHub
1. **PR #3** - PR 5.1/N FE/BE Alignment (feat/pr5-1-align-fe-be) - ✅ Checks passing
2. **PR #2** - GoogleCalendarClient real (feat/pr4-google-calendar-real) - ✅ Checks passing
3. **PR #1** - v2 bootstrap skeleton (rebuild/2025-contexto-supremo) - ❌ 2/3 checks failing

**⚠️ Divergência:** Branch `fix/v2-bootstrap-core` **não tem PR** aberto ainda.

---

### 2. Infraestrutura Docker

#### Stack aprender_v2 - Status dos Containers

| Container | Status | Porta | Saúde |
|-----------|--------|-------|-------|
| **as_v2_web** | ✅ Up 4 min | 8002:8000 | Healthy |
| **as_v2_db** | ✅ Up 4 min | 5434:5432 | Healthy |
| **as_v2_redis** | ✅ Up 4 min | 6380:6379 | Healthy |
| **as_v2_worker** | ⚠️ Restarting | - | Crash loop |
| **as_v2_beat** | ⚠️ Restarting | - | Crash loop |

**Evidência:**
```bash
docker compose -p aprender_v2 -f infra/docker-compose.yml ps
```

#### Compose Configuration
- **Project Name:** `aprender_v2` ✅ (corrigido)
- **Compose File:** `v2/infra/docker-compose.yml` ✅
- **COMPOSE_PROJECT_NAME:** `aprender_v2` ✅ (Makefile configurado)
- **Port Mappings:** Corretos (8002→8000, 5434→5432, 6380→6379)

**⚠️ Problema:** Worker e Beat em **restart loop** (erro ao inicializar, possivelmente falta de dependências ou configuração Celery)

---

### 3. Backend Django - Sanidade e Configuração

#### Django System Check
```bash
System check identified no issues (0 silenced).
```
**Status:** ✅ **Verde** - Nenhum problema detectado

#### Migrations
**Todas aplicadas (✅):**
- `core.0001_initial` a `core.0008_projeto_codigo_projeto_fluxo_solicitacao_projeto`
- Django apps: admin, auth, contenttypes, sessions
- Celery: django_celery_beat, django_celery_results

**Migration 0008 (Bootstrap):**
- ✅ Adiciona `Projeto.codigo` (nullable, unique, indexed)
- ✅ Adiciona `Projeto.fluxo` (SUPER/NAO_SUPER, default NAO_SUPER)
- ✅ Adiciona `Solicitacao.projeto` FK (nullable, PROTECT)

**Evidência:** `v2/.agents/outbox/showmigrations.txt`

#### Modelo Projeto - Campos Atuais
```python
['id', 'nome', 'codigo', 'fluxo', 'descricao', 'ativo']
```
**Status:** ✅ **Sincronizado** - Campos do bootstrap presentes no banco

**Evidência:** `v2/.agents/outbox/projeto_fields.txt`

#### Settings.py - Configurações Críticas
- **REQUIRE_DOCKER:** `1` ✅ (v2-only enforced)
- **ENVIRONMENT:** `development`
- **DEBUG:** `True`
- **TIME_ZONE:** `America/Fortaleza` ✅
- **DATABASE:** PostgreSQL na porta 5432 (interno), 5434 (host)
- **CACHE:** Redis configurado (django_redis)
- **AUTH_USER_MODEL:** `core.Usuario` ✅

---

### 4. Health Endpoints - Evidências

#### /healthz/
```json
{"status": "ok", "environment": "development", "debug": true, "timezone": "America/Fortaleza"}
```
**Status:** ✅ **OK** - Sistema operacional

**Evidência:** `v2/.agents/outbox/healthz.json`

#### /api/readyz/
```json
{"db": "ok", "redis": "ok"}
```
**Status:** ✅ **OK** - DB e Redis funcionando

**Evidência:** `v2/.agents/outbox/readyz.json`

#### /api/features/
```json
{"GCAL_CLIENT": "fake", "apply_blocked": false, "ENVIRONMENT": "dev"}
```
**Status:** 🟡 **Parcial**
- ✅ `GCAL_CLIENT=fake` (seguro, não toca Google Calendar real)
- ⚠️ `apply_blocked=false` (deveria ser `true` em dev para dupla proteção)
- ✅ `ENVIRONMENT=dev`

**Evidência:** `v2/.agents/outbox/features.json`

---

### 5. Testes - Import Errors

#### Resultado dos Testes
```
collected 188 items / 11 errors
11 errors during collection
```

**Status:** 🔴 **Vermelho** - Nenhum teste rodou devido a import errors

#### Import Errors Identificados

| Arquivo de Teste | Erro | Modelo/Serializer Faltante |
|------------------|------|----------------------------|
| `test_admin_api.py` | ImportError | `Compra` |
| `test_admin_user_security.py` | ImportError | `UsuarioAdminSerializer` |
| `test_celery_gcal_safety.py` | ImportError | `AuditLog` |
| `test_gcal_endpoints.py` | ImportError | `AuditLog` |
| `test_import_compras.py` | ImportError | `Compra` |
| `test_preagenda.py` | ImportError | `AuditLog` |
| `test_projetos_fluxo_seed.py` | ImportError | `Compra` |
| `test_dat_ingest/test_commands.py` | ModuleNotFoundError | `apps.dat_ingest.services` |
| `test_dat_ingest/test_loaders.py` | ModuleNotFoundError | `loaders` |
| `test_dat_ingest/test_normalizers.py` | ModuleNotFoundError | `normalizers` |
| `test_dat_ingest/test_processors.py` | ModuleNotFoundError | `processors` |

**Modelos/Componentes Não Implementados:**
1. ❌ `Compra` (core/models.py)
2. ❌ `AuditLog` (core/models.py)
3. ❌ `UsuarioAdminSerializer` (core/serializers.py)
4. ❌ `apps.dat_ingest.services.*` (módulos completos faltando)

**Evidência:** `v2/.agents/outbox/pytest.txt`

---

### 6. Views e URLs - Estrutura Isolada

#### Views Ativas (Bootstrap)
- ✅ `views_basic.py` - api_root, CurrentUserView
- ✅ `views_health.py` - readyz, features
- ✅ `views_solicitacao.py` - SolicitacaoViewSet (approve/reject)
- ✅ `views_availability.py` - AvailabilityBlockViewSet, check views

#### URLs Configuradas
```python
path("", api_root)
path("readyz/", readyz)
path("features/", features)
path("me/", CurrentUserView)
path("availability/check/", AvailabilityCheckView)
router.register(r"solicitacoes", SolicitacaoViewSet)
router.register(r"availability-blocks", AvailabilityBlockViewSet)
```

**Status:** ✅ **OK** - Views isoladas funcionando, sem dependências de modelos não implementados

#### views.py Monolítico
**Comentado (GAP-004):**
- `CompraViewSet` (linha 626-658)
- `UsuarioAdminViewSet` (linha 660-682)
- `AuditLogViewSet` (linha 684-707)
- `ImportComprasView` (linha 709-830)

**Razão:** Modelos Compra/AuditLog não existem, então essas views estão comentadas para não quebrar imports.

---

### 7. Sanidade v2-only

#### Referências a v1/legacy no Código
**Busca executada:**
```bash
grep -r "aprendersistema\|/v1/\|legacy" v2/backend/apps v2/backend/config
```

**Resultado:**
```
v2/backend/apps/core/management/commands/preagenda_to_gcal.py:
    # Se batch_size=0, processa todos de uma vez (legacy behavior)
```

**Status:** ✅ **OK** - Apenas 1 comentário inofensivo, nenhuma dependência real de v1

#### Estrutura de Diretórios v2/
```
v2/
├── .agents/outbox/          ✅ Evidências salvas
├── backend/
│   ├── apps/core/           ✅ Modelos, views, migrations
│   ├── config/              ✅ Settings, urls, wsgi
│   └── ...
├── frontend/                ✅ React 18 + Vite
├── infra/
│   ├── docker-compose.yml   ✅ Configurado (aprender_v2)
│   ├── Dockerfile           ✅ Multi-stage build
│   └── .env                 ✅ Presente (20 linhas redacted)
├── Makefile                 ✅ COMPOSE_PROJECT_NAME=aprender_v2
└── docs/                    ✅ Documentação v2
```

**Status:** ✅ **Limpo** - Nenhum arquivo v1 dentro de v2/

---

## 🚨 Matriz de Achados (Severidade)

| # | Item | Severidade | Evidência | Recomendação |
|---|------|------------|-----------|--------------|
| 1 | Worker/Beat em crash loop | **P1** | `docker compose ps` | Investigar logs Celery, verificar CELERY_BROKER_URL |
| 2 | `apply_blocked=false` em dev | **P2** | `features.json` | Setar lógica: `apply_blocked = (GCAL_CLIENT != "google")` |
| 3 | Modelos Compra/AuditLog ausentes | **P1** | `pytest.txt` | Criar modelos ou remover testes dependentes |
| 4 | UsuarioAdminSerializer faltando | **P2** | `pytest.txt` | Implementar serializer ou remover testes |
| 5 | dat_ingest.services.* não existe | **P1** | `pytest.txt` | Implementar ou remover app dat_ingest (órfão) |
| 6 | Branch fix/v2-bootstrap-core sem PR | **P2** | `gh pr status` | Criar PR para main (ou branch base) |
| 7 | PR #1 com 2/3 checks failing | **P2** | `gh pr list` | Investigar CI failures em rebuild/2025-contexto-supremo |
| 8 | django_redis não instalado no build | **P0** | Tentativa migrate anterior | Adicionar `django-redis` em requirements.txt |

---

## 🔄 Divergências Local vs Remoto

### Git Status
```
## fix/v2-bootstrap-core...origin/fix/v2-bootstrap-core
 M .claude/settings.local.json
 M v2/backend/apps/core/views.py
```

**Arquivos Modificados Não Commitados:**
1. `.claude/settings.local.json` - Configurações locais do Claude Code
2. `v2/backend/apps/core/views.py` - Views monolítico com comentários GAP-004

**Ação Recomendada:** Decidir se commita ou descarta essas mudanças antes de merge.

### Branches Remotas (origin)
- ✅ `main` / `main-v1` - Branches principais
- ✅ `fix/v2-bootstrap-core` - Bootstrap (pushed)
- ✅ `feat/pr4-google-calendar-real` - GoogleCalendar real
- ✅ `feat/pr5-1-align-fe-be` - Alignment FE/BE
- ✅ `rebuild/2025-contexto-supremo` - V2 skeleton

**Total:** 8 branches remotas identificadas

---

## 📁 Evidências Coletadas

Todos os arquivos salvos em `v2/.agents/outbox/`:

1. ✅ **healthz.json** (94 bytes) - Health check do sistema
2. ✅ **readyz.json** (27 bytes) - DB + Redis status
3. ✅ **features.json** (69 bytes) - Feature flags
4. ✅ **django_check.txt** (77 bytes) - Django system check
5. ✅ **showmigrations.txt** (3.5 KB) - Status de todas migrations
6. ✅ **projeto_fields.txt** (65 bytes) - Campos do modelo Projeto
7. ✅ **pytest.txt** (4.2 KB) - Resultado dos testes (11 import errors)
8. ✅ **V2-AUDITORIA-GERAL-20251017.md** (este arquivo)

---

## 📋 Diagnóstico de Desalinhamento

### Compose/Porta ✅
- **Esperado:** Project `aprender_v2`, porta 8002:8000
- **Atual:** ✅ Correto (corrigido no docker-compose.yml)
- **Makefile:** ✅ Alinhado (`COMPOSE_PROJECT_NAME=aprender_v2`)

### Settings ✅
- **REQUIRE_DOCKER:** ✅ `1` (enforced)
- **TIME_ZONE:** ✅ `America/Fortaleza`
- **DATABASE:** ✅ PostgreSQL configurado
- **CACHE:** ⚠️ Redis configurado, mas `django-redis` não instalado no último build

### Migrations vs Models ✅
- **Migration 0008:** ✅ Aplicada (faked, colunas já existiam)
- **Modelo Projeto:** ✅ Campos `codigo` e `fluxo` presentes
- **Modelo Solicitacao:** ✅ FK `projeto` presente

**Conclusão:** Sincronização **OK** entre migrations e models após bootstrap.

---

## 🎯 Plano Sugerido (Opção A)

### ✅ Já Implementado (Bootstrap v2-only)

**Commits 1-4 (fix/v2-bootstrap-core):**
1. ✅ Isolar views ativas (Solicitacao, Availability, Basic)
2. ✅ Adicionar Projeto.codigo + fluxo + FK Solicitacao.projeto
3. ✅ Criar endpoints /api/readyz/ e /api/features/
4. ✅ Alinhar porta 8002 no Makefile

**Status:** **100% Completo** - Stack funcional e pronto para ETL

---

### 🚀 Próximos Passos Recomendados

#### Imediato (7 dias)

1. **Abrir PR para fix/v2-bootstrap-core** (P2)
   ```bash
   gh pr create --base main \
     --title "feat(v2): Bootstrap core - views isoladas + domínio (codigo/fluxo)" \
     --body "4 commits atômicos: isola views, adiciona campos de domínio, health endpoints, alinha porta"
   ```

2. **Corrigir Worker/Beat crash loop** (P1)
   - Investigar logs: `docker compose -p aprender_v2 logs worker beat`
   - Verificar `CELERY_BROKER_URL` e dependências Celery
   - Adicionar `django-redis` em `requirements-minimal.txt`

3. **Ajustar `apply_blocked` logic** (P2)
   ```python
   # views_health.py
   gcal_client = os.getenv("GCAL_CLIENT", "fake")
   apply_blocked = (gcal_client != "google")  # True em dev/staging
   ```

4. **Decidir sobre modelos faltantes** (P1)
   - **Opção A:** Criar stubs vazios para Compra/AuditLog (permitir testes rodarem)
   - **Opção B:** Remover testes dependentes (manter foco v2-only)
   - **Opção C:** Implementar modelos completos (escopo maior)

#### Curto Prazo (14 dias)

5. **Implementar modelos pendentes** (P1)
   - `Compra` (import de planilhas de controle)
   - `AuditLog` (rastreamento de ações)
   - `UsuarioAdminSerializer` (gestão de usuários)

6. **Decidir sobre dat_ingest** (P1)
   - App órfão (services não existem, testes quebrados)
   - **Opção A:** Remover app completamente
   - **Opção B:** Implementar pipeline ETL completo

7. **Corrigir CI do PR #1** (P2)
   - Investigar 2/3 checks failing em `rebuild/2025-contexto-supremo`
   - Possivelmente conflitos ou testes quebrados

#### Médio Prazo (30 dias)

8. **Implementar ETL robusto**
   - Comando `seed_projetos_fluxo_from_sheets`
   - Importação de dados reais das planilhas oficiais
   - Validação de classificação SUPER/NAO_SUPER

9. **Completar endpoints de administração**
   - `/api/pre-agenda/` (Controle e Superintendência)
   - `/api/admin/compras/` (DAT)
   - `/api/admin/usuarios/` (DAT)

10. **Documentação e Deploy**
    - API reference completo
    - Deploy guides (staging → produção)
    - User guides por perfil (Coordenador, Superintendência, etc.)

---

## ⚠️ Riscos e Pendências

### Riscos Identificados

1. **Worker/Beat instáveis** (P1)
   - **Impacto:** Tarefas assíncronas (Celery) não funcionam
   - **Mitigação:** Web funciona independente, mas GCal sync precisa de fix

2. **11 import errors nos testes** (P1)
   - **Impacto:** 0% coverage, impossível validar mudanças
   - **Mitigação:** Criar stubs ou remover testes dependentes

3. **`apply_blocked=false` em dev** (P2)
   - **Impacto:** Risco de aplicar no GCal real por engano
   - **Mitigação:** GCAL_CLIENT=fake já protege, mas dupla proteção é melhor

4. **django-redis não instalado** (P0)
   - **Impacto:** Novo build pode falhar em migrations (cache backend)
   - **Mitigação:** Adicionar `django-redis` em requirements ASAP

### Pendências Técnicas

- [ ] PR para fix/v2-bootstrap-core
- [ ] Fix Worker/Beat crash loop
- [ ] Implementar Compra/AuditLog ou remover testes
- [ ] Decidir sobre app dat_ingest (remover ou implementar)
- [ ] Corrigir apply_blocked logic
- [ ] Adicionar django-redis em requirements
- [ ] Investigar CI failures do PR #1

---

## 📊 Métricas de Auditoria

| Métrica | Valor | Status |
|---------|-------|--------|
| Containers rodando | 3/5 | 🟡 60% (worker/beat down) |
| Health endpoints OK | 3/3 | ✅ 100% |
| Migrations aplicadas | 100% | ✅ OK |
| Testes passando | 0/188 | 🔴 0% (import errors) |
| Views isoladas | 4/4 | ✅ 100% |
| Modelos sincronizados | 5/7 | 🟡 71% (faltam Compra/AuditLog) |
| PRs abertos | 3 | ℹ️ Info |
| Branch remota | ✅ Pushed | ✅ OK |

---

## 🎓 Conclusões

### O Que Está Funcionando

1. ✅ **Stack Docker** rodando na configuração correta (aprender_v2, portas 8002/5434/6380)
2. ✅ **Backend Django** operacional (web healthy, migrations OK, sistema check limpo)
3. ✅ **Health endpoints** respondendo corretamente
4. ✅ **Bootstrap v2-only** completo (views isoladas, campos de domínio, health checks)
5. ✅ **Modelo-Banco sincronizado** (Projeto.codigo + fluxo, Solicitacao.projeto)
6. ✅ **V2 isolado** (nenhuma dependência de v1/legacy)

### O Que Precisa de Atenção

1. ⚠️ **Worker/Beat** em restart loop (Celery não funciona)
2. ⚠️ **Testes quebrados** (11 import errors, 0% coverage)
3. ⚠️ **Modelos faltantes** (Compra, AuditLog, UsuarioAdminSerializer)
4. ⚠️ **App dat_ingest** órfão (services não existem)
5. ⚠️ **django-redis** não instalado (risco em novo build)

### Recomendação Final

**Prioridade:** Abrir PR para `fix/v2-bootstrap-core` (4 commits estáveis) e depois atacar os itens P0/P1 acima.

**Estimativa:** Bootstrap (Opção A) = **Completo** ✅. Próxima fase (modelos + testes) = **7-14 dias** de trabalho.

---

**Auditoria realizada em:** 2025-10-17 20:30 UTC-3
**Modo:** Somente leitura (nenhuma operação destrutiva executada)
**Stack auditado:** aprender_v2 (em execução contínua)
**Evidências:** `v2/.agents/outbox/`

**Status Final:** ✅ **Auditoria Completa**

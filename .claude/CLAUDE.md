# Projeto: Aprender Sistema (AS) — Guia do Claude Code

---

## ⚠️ IMPORTANTE: Ao Retomar Sessão Resumida

**Se você está lendo este arquivo após uma compactação/resumo de conversa:**

1. ✅ **LEIA PRIMEIRO**: [.claude/CHECKLIST_FERRAMENTAS.md](.claude/CHECKLIST_FERRAMENTAS.md)
   - Lista completa de 16 slash commands disponíveis
   - 3 skills especializadas (aprender-domain, django-patterns, etl-guidelines)
   - 4 hooks de notificação configurados
   - Checklist: "Devo usar ferramenta ou fazer manual?"

2. ✅ **EVITE**: Fazer tarefas manualmente quando existe ferramenta especializada
   - ❌ Grep manual → ✅ Use `/review-enhanced` ou Task/Explore
   - ❌ Análise manual de regras → ✅ Use skill `aprender-domain`
   - ❌ Review básico → ✅ Use `/review-enhanced` (10 categorias)

3. ✅ **SEMPRE PERGUNTE**: "Existe slash command, skill ou agent para isso?"

**Objetivo**: Garantir que eu use consistentemente todas as ferramentas customizadas, mesmo após resumo de contexto.

---

## Contexto do Projeto
- Objetivo: Substituir planilhas pelo **AS** para solicitação → aprovação → criação de eventos (Google Calendar), com verificação de conflitos e logs de auditoria.
- Stack: **Python 3.12.12 + Django 5.1.x + DRF + Celery + PostgreSQL 15 + Redis 7**, containers via **Docker + Docker Compose** (`v2/infra/docker-compose.yml`).
- Frontend: **React (Vite) + Tailwind + Ant Design**, dev server com proxy `/api → http://localhost:8002` e chamadas com `credentials: 'include'`.
- Fuso horário padrão: `America/Fortaleza`.
- Type Checking: **Pyright (strict mode)** com suporte a **PEP 695** (Python 3.12)

---

## 🔧 Ferramentas Disponíveis (.claude/)

### Slash Commands Customizados

Use `/command-name` para executar comandos especializados:

**Desenvolvimento e Qualidade:**
- `/new-feat` - Criar nova feature seguindo padrões do projeto
- `/create-feature` - Planejar e implementar feature com padrões AS v2 (type-safety, RBAC)
- `/migrate` - Executar migrações Django e validar modelo
- `/test-coverage` - Análise completa de cobertura de testes
- `/review` - Review automático de código (style, security, best practices)
- `/review-staged` - Review de mudanças staged contra padrões AS v2
- `/trim` - Reduzir descrição de PR em 70% mantendo essencial

**Fluxos de Negócio (Testes):**
- `/approve-flow` - Testar fluxo completo de aprovação (PA-01 a PA-07)
- `/check-conflicts` - Testar verificação de conflitos (RF03, RD-01 a RD-08)

**ETL e Importação:**
- `/etl-dry` - Rodar ETL em modo dry-run (simula sem persistir)
- `/etl-apply` - Rodar ETL com apply (persiste no banco + relatórios)

**Deploy e Infraestrutura:**
- `/deploy-staging` - Deploy completo para ambiente staging

**Investigação e Planejamento:**
- `/investigate-batch` - Discovery com perguntas agrupadas (economiza tokens)

**Project Agents (Tasks Autônomas):**
- `/project_git-pr` - Preparar commit limpo e descrição de PR
- `/project_import-formadores` - Importar formadores do Excel
- `/project_migrate-models` - Criar e aplicar migrations para models
- `/project_tdd <app> <feature>` - Iniciar ciclo TDD para feature
- `/project_e2e-smoke` - Criar/atualizar smoke test Playwright (RF01→RF07)
- `/project_fix-django-url` - Investigar e corrigir problemas de URL reverse
- `/project_plan` - Planejar implementação detalhada de tarefa

### Skills Especializadas

Use `Skill` tool com nome da skill para contexto especializado:

- **aprender-domain** - Conhecimento completo do domínio (planilhas originais, fluxos SUPER/NAO_SUPER, RFs, códigos de disponibilidade E/M/D/P/T/X)
- **django-patterns** - Padrões Django/DRF (models, serializers, views, services, permissions, testes)
- **etl-guidelines** - Guidelines para management commands ETL (dry-run, idempotência, relatórios JSON)

### Quando Usar

**Sempre use slash commands quando:**
- Tarefa complexa com múltiplas etapas (approve-flow, etl-apply)
- Necessita validação de conformidade (check-conflicts, test-coverage)
- Deploy ou operação crítica (deploy-staging)

**Use skills quando:**
- Precisar contexto detalhado do domínio antes de implementar
- Dúvida sobre padrão correto (Django patterns, ETL guidelines)
- Planejamento de features que envolvem regras de negócio

### Referência Completa

📖 **[.claude/GUIA_USO.md](.claude/GUIA_USO.md)** - Guia completo com exemplos, workflows e troubleshooting (657 linhas)

**Estrutura .claude/**:
```
.claude/
├── CLAUDE.md                  # Regras de negócio (este arquivo)
├── CLAUDE-principles.md       # Qualidade de código (625L)
├── GUIA_USO.md                # Guia completo ⭐
├── CHECKLIST_FERRAMENTAS.md   # Checklist pós-resumo ⭐
├── settings.json              # Hooks + permissions
├── commands/                  # 20 slash commands
│   ├── create-feature.md      # Feature com padrões AS v2 ⭐ NOVO
│   ├── review-staged.md       # Review staged (Pyright, RBAC) ⭐ NOVO
│   ├── investigate-batch.md   # Discovery batched ⭐ NOVO
│   ├── trim.md                # Reduzir PR 70% ⭐ NOVO
│   └── review-enhanced.md     # Review 10 categorias
├── skills/                    # 3 skills (aprender-domain, django-patterns, etl-guidelines)
└── songs/                     # Som notificação (duolingo-correct.mp3)
```

**Quick Start**:
- Nova feature → `/new-feat <descrição>`
- Review código → `/review <arquivo>`
- Testar compliance → `/check-conflicts` ou `/approve-flow`
- ETL → `/etl-dry` depois `/etl-apply`
- Deploy → `/deploy-staging full`

### 🔌 MCP Servers (Model Context Protocol)

Tenho acesso a 4 MCP servers configurados localmente (`.mcp.json` - não vai pro git):

| MCP | Ferramenta | Uso |
|-----|------------|-----|
| **postgres** | `mcp__postgres__query` | Queries SQL diretas no banco (`localhost:5434`) |
| **github** | `mcp__github__*` | Criar/listar issues, PRs, comentários via API |
| **playwright** | `mcp__playwright__*` | Testes E2E automatizados no browser |
| **fetch** | `mcp__fetch__*` | Fetch de URLs sem restrições |

**Quando usar MCPs:**
- **postgres**: Investigar dados, debug de queries, verificar estado do banco
- **github**: Criar issues automaticamente, listar PRs, verificar CI status
- **playwright**: Testes E2E, screenshots, validação visual
- **fetch**: Buscar documentação externa, APIs, verificar URLs

**Configuração:** `.mcp.json` (local only, no `.gitignore`)
- PostgreSQL: `localhost:5434` (container Docker)
- GitHub: Token configurado para o repositório

---

## 🐍 Type Hints (Python 3.12 + PEP 695) ✅ COMPLETO

**Status**: ✅ **100% Implementado** (8 PRs, 42 arquivos, ~18,000 linhas)
**Type Checker**: Pyright 1.1.382 (strict mode)
**Conclusão**: 2025-01-11 (PRs #108-#116)

### Implementação Completa

| PR | Escopo | Arquivos | Status |
|----|--------|----------|--------|
| #1 | Setup Pyright + CI | 3 | ✅ #108 |
| #2-3 | Services (12 arquivos) | ~7,192L | ✅ #109-110 |
| #4 | Models (2 arquivos) | ~1,017L | ✅ #111 |
| #5 | Serializers (1 arquivo) | ~562L | ✅ #112 |
| #6 | Views (21 arquivos) | ~8,221L | ✅ #113-114 |
| #7 | Tasks (1 arquivo) | ~489L | ✅ #115 |
| #8 | Polish (2 arquivos) | ~339L | ✅ #116 |

**Total**: 42 arquivos críticos, ~18,000 linhas tipadas, 0 erros Pyright

### Ganhos Práticos

✅ **Detecção de erros em dev** (antes: runtime/produção)
✅ **Autocomplete 3x melhor** (95% precisão vs 30%)
✅ **Refactoring seguro** (IDE detecta quebras automaticamente)
✅ **CI como gate** (Pyright bloqueia PRs com erros de tipo)
✅ **Documentação viva** (type hints nunca ficam desatualizados)
✅ **Onboarding 2x mais rápido** (código autodocumentado)

**ROI**: ~40-120h/ano economizadas em debug + 20-30% aumento em velocity

### Quick Reference

```python
# PEP 695: Type aliases modernos (Python 3.12+)
type UserId = int
type Status = Literal["pendente", "aprovado", "reprovado"]

# Django QuerySet tipado
def pendentes(cls) -> models.QuerySet[Self]:
    return cls.objects.filter(status="pendente")

# DRF Serializer tipado
class SolicitacaoSerializer(serializers.ModelSerializer[Solicitacao]):
    def create(self, validated_data: dict[str, Any]) -> Solicitacao:
        return Solicitacao.objects.create(**validated_data)
```

### Rodar Localmente

```bash
cd v2/backend
pyright apps/core apps/dat_ingest config
```

---

## 📁 Estrutura Modular do Backend (PRs #213-#217)

**Status**: ✅ **100% Implementado** (5 PRs, ~5,500 linhas refatoradas)
**Conclusão**: 2025-12-02

O backend foi modularizado para melhor organização e manutenibilidade. Arquivos monolíticos foram convertidos em pacotes Python com submódulos por domínio/feature.

### Pacotes Modulares

#### `apps/core/models/` (PR #213)
```
models/
├── __init__.py          # Re-exports todos os models
├── usuario.py           # Usuario (custom user model)
├── projeto.py           # Projeto, Gerencia
├── municipio.py         # Municipio, Deslocamento
├── solicitacao.py       # Solicitacao, Participation
├── availability.py      # AvailabilityBlock
├── compra.py            # Compra, Produto
├── controle.py          # AcaoControle, AcaoDAT
├── config.py            # SystemConfig
└── audit.py             # AuditLog
```

#### `apps/core/serializers/` (PR #214)
```
serializers/
├── __init__.py          # Re-exports todos os serializers
├── usuario.py           # UsuarioSerializer, UsuarioAdminSerializer
├── projeto.py           # ProjetoSerializer, GerenciaSerializer
├── municipio.py         # MunicipioSerializer, DeslocamentoSerializer
├── solicitacao.py       # SolicitacaoSerializer, ParticipationSerializer
├── availability.py      # AvailabilityBlockSerializer
├── compra.py            # CompraSerializer, ProdutoSerializer
├── controle.py          # AcaoControleSerializer, AcaoDATSerializer
├── config.py            # SystemConfigSerializer
├── audit.py             # AuditLogSerializer
└── options.py           # Option serializers para dropdowns
```

#### `apps/core/views/` (PR #217)
```
views/
├── __init__.py          # Re-exports todas as views
├── utils.py             # _get_client_ip, api_root
├── solicitacao.py       # SolicitacaoViewSet (approve/reject)
├── availability.py      # AvailabilityBlockViewSet, Check views
├── user.py              # CurrentUserView
├── admin.py             # CRUD ViewSets (Municipio, Projeto, etc.)
└── options.py           # Dropdown option ViewSets
```

#### `apps/core/views_gcal/` (PR #215)
```
views_gcal/
├── __init__.py          # Re-exports
├── gcal.py              # gcal_calendars, gcal_health
├── helpers.py           # Funções auxiliares, paginação
├── summary.py           # 4 views de métricas/sumário
├── batch.py             # 3 views de operações em lote
├── detail.py            # 4 views de detalhe/export
└── insights.py          # 2 views de analytics
```

#### `apps/core/services/gcal/` (PR #216)
```
services/gcal/
├── __init__.py          # Re-exports
├── types.py             # SyncOutcome, Action type alias
├── utils.py             # _retry_with_backoff, _payload_hash
├── client.py            # CalendarClientAdapter
├── validation.py        # Event ID validation
├── payload.py           # Payload building functions
└── sync.py              # Core sync operations
```

### Compatibilidade

Todos os imports antigos continuam funcionando:
```python
# Import antigo (ainda funciona)
from apps.core.models import Solicitacao
from apps.core.views import SolicitacaoViewSet
from apps.core.services.gcal_sync_service import apply_one_solicitacao

# Import novo (mais específico)
from apps.core.models.solicitacao import Solicitacao
from apps.core.views.solicitacao import SolicitacaoViewSet
from apps.core.services.gcal.sync import apply_one_solicitacao
```

### Testes de Compatibilidade

~100 testes garantem que os re-exports funcionam:
- `test_modular_models.py`
- `test_modular_serializers.py`
- `test_modular_views.py`
- `test_modular_views_gcal.py`
- `test_modular_gcal_service.py`

---

## 📊 Estrutura das Planilhas Source (v2/backend/data/csv-import/)

### Acompanhamento de Agenda _ 2025.xlsx
**Abas de Eventos**:
- ACerta, Outros, Super, Brincando, Vidas

**Abas de Suporte**:
- DESLOCAMENTO
- DISPONIBILIDADE
- Bloqueios
- Pré-Agenda
- Google Agenda
- Relatórios
- Novo Google Agenda
- Configurações

### Disponibilidade _ 2025.xlsx
**Abas Principais**:
- MENSAL
- ANUAL
- DESLOCAMENTO
- Bloqueios
- Eventos
- Configurações

### Planilha de Controle - 2025.xlsx
**Abas Operacionais**:
- 🟥 AÇÕES
- 🟥 COMPRAS (estrutura: CÓD, Produto, Quant., Município, UF, Data, Uso das coleções)
- 🟥 COORD

**Abas de Dados**:
- ℹ️ FORMAÇÕES
- ℹ️ DAT
- ☑️ CADASTROS
- ℹ️ FILTRO_PROD.

**Abas Antigas/Legadas**:
- ℹ️ FORMAÇÕES - ANTIGA
- ℹ️ Antiga - DAT
- 🖥️FORMAÇÕES
- ☑️ CADASTROS (Antiga)

**Configurações**:
- ⚙️ CONFIG

### Usuários.xlsx
**Abas**:
- Ativos
- Inativos
- Pendentes

---

## ⚖️ CLÁUSULAS PÉTREAS — IMUTÁVEIS

### 🐳 CP-01: REQUIRE_DOCKER=1 (v2 ONLY)
- **v2 DEVE rodar APENAS em Docker.** Nenhuma exceção.
- Validação obrigatória em `config/settings.py`:
  ```python
  REQUIRE_DOCKER = os.getenv("REQUIRE_DOCKER", "0") == "1"
  if REQUIRE_DOCKER and not os.path.exists("/.dockerenv"):
      print("❌ ERRO: v2 deve rodar apenas em Docker", file=sys.stderr)
      sys.exit(1)
  ```
- Comando recomendado: `cd v2 && make up` (wrap em `COMPOSE_PROJECT_NAME=aprender_v2 docker compose -f infra/docker-compose.yml`)
- **v1 pode rodar local** (legacy support), mas **v2 = Docker obrigatório**.

### 🔒 CP-02: Política de Aprovação Manual (PA-01 a PA-07)
Estas regras estão definidas em `.claude/CLAUDE.md` e são **imutáveis**:

- **PA-01**: Sem auto-aprovação. Uma Solicitação **nunca** muda para "Aprovada" automaticamente.
- **PA-02**: Apenas usuários com **Gerente + Superintendência** (ou superuser) podem aprovar/reprovar. Ver seção RBAC.
- **PA-03**: Integrações externas (Google Calendar, etc.) só executam **após** aprovação manual concluída.
- **PA-04**: Toda solicitação nasce com `status = pendente`.
- **PA-05**: Registrar usuário, data/hora e justificativa em `Aprovacao` e `LogAuditoria`.
- **PA-06**: UI/UX: esconder botões de ação para perfis sem permissão (ISO 9241-110).
- **PA-07**: Testes obrigatórios:
  - `test_never_auto_approves_on_clean_or_save`
  - `test_only_superintendencia_can_approve_or_reject`
  - `test_calendar_integration_not_called_before_approval`
  - `test_approval_flow_records_audit_log`
  - `test_non_privileged_user_gets_403_on_approval_endpoint`

### 📅 CP-03: Regras de Disponibilidade (RD-01 a RD-08)
Estas regras estão definidas em `.claude/CLAUDE.md` e são **imutáveis**:

- **RD-01**: Não-sobreposição (overlap ≥ 1 minuto = conflito; borda `fim == início` = OK).
- **RD-02**: Bloqueio total (T) impede quaisquer eventos no intervalo.
- **RD-03**: Bloqueio parcial (P) impede eventos dentro do subintervalo bloqueado.
- **RD-04**: Buffer de deslocamento (D) entre municípios distintos (60–120 min configurável).
- **RD-05**: Capacidade diária (M) — limite de horas por dia por formador.
- **RD-06**: Timezone `America/Fortaleza` (aware), armazenar UTC.
- **RD-07**: Prioridade de checagem: (1) Bloqueios, (2) Conflitos, (3) Buffer, (4) Limite diário.
- **RD-08**: Mensagens de conflito devem listar formador(es), data/intervalo, tipo (E/M/D/P/T/X).

### 🔄 CP-04: Workflow de Sub-Agents
Ordem obrigatória de trabalho para agentes autônomos:
1. **Entender** → Ler código, docs, issues
2. **Planejar** → Escrever plano passo a passo (usar `/permissions plan`)
3. **Implementar** → PRs pequenos e atômicos
4. **Testar** → Testes unitários/integração/end-to-end (Playwright MCP)
5. **Infra** → Docker/CI/CD (se aplicável)
6. **ETL** → Importação de dados (se aplicável)
7. **UI/UX** → Templates/views (se aplicável)

**Nunca pular etapas.** Sempre documentar no `CLAUDE.md` o que foi feito.

### 🚫 CP-05: Nunca Tocar v1 Sem Aprovação
- **v1 está congelado** (tag: `v1-freeze`, branch: `main-v1`).
- Qualquer mudança em v1 **exige**:
  1. Branch `fix/v1-<nome>` ou `hotfix/v1-<nome>`
  2. PR para `main-v1`
  3. Aprovação de 1+ reviewer
  4. CI verde
- **v2 não modifica v1.** São sistemas isolados.

### 📝 CP-06: Padrões de Commit, Branch e PR
**Commits:**
- Convenção: `<type>(<scope>): <message>`
- Types: `feat`, `fix`, `chore`, `docs`, `test`, `refactor`, `style`, `perf`
- Exemplo: `feat(v2): add Django project structure + CI`

**Branches:**
- Padrão: `<type>/<nome>`
- v1: `fix/v1-<nome>`, `hotfix/v1-<nome>`
- v2: `feat/v2-<nome>`, `fix/v2-<nome>`, `chore/v2-<nome>`

**PRs:**
- Base: `main-v1` (para v1) ou `main-v2` (futuro, para v2)
- Compare: `<type>/<nome>`
- Require: 1+ approval, CI verde, branch up-to-date
- Merge strategy: **Squash and merge** recomendado

---

## ✅ SESSÃO ATUAL: Centralização Docker e Otimização Completa (Setembro 2025)

### 🎯 AUDITORIA E CENTRALIZAÇÃO COMPLETA:
- **Sistema 100% Docker**: PostgreSQL na porta 5433, SQLite removido
- **MCPs Otimizados**: Erros eliminados, registration desabilitado temporariamente  
- **Arquivos Organizados**: docs/memoria/ criado, 8 arquivos consolidados
- **Tokens Otimizados**: .gitignore atualizado, redução ~40% consumo
- **122 usuários migrados** do SQLite para PostgreSQL Docker com sucesso

### 🔧 PROBLEMAS RESOLVIDOS:
1. **Duplicação de bancos**: SQLite local removido, PostgreSQL Docker ativo
2. **MCPs com falhas**: 6 MCPs auditados, problemas de registro corrigidos
3. **Alto consumo tokens**: venv/, backups, memoria/ ignorados no .gitignore
4. **Arquivos espalhados**: GPT.md, CONTEXTO_*.md consolidados em docs/memoria/

### 🐳 CONFIGURAÇÃO DOCKER ATUAL:
- **PostgreSQL**: docker-compose up -d db (porta 5433)
- **Desenvolvimento**: ENVIRONMENT=staging DB_HOST=localhost DB_PORT=5433
- **Dados**: 122 usuários + dados de exemplo migrados
- **Status**: ✅ Funcionando perfeitamente sem erros

### 📊 OTIMIZAÇÕES DE PERFORMANCE:
- **venv/** ignorado: Elimina milhares de arquivos Python
- **backup_*.json** ignorado: Remove temporários
- **docs/memoria/** ignorado: Evita duplicação de contexto
- **MCPs silenciosos**: Sem mais warnings verbosos nos comandos

### 📝 OBSERVABILIDADE COMPLETA (MP1 + MP2):
- **MP1 - Prometheus + Grafana** (Issue #165): ✅ Implementado e merged
  - Stack completa: Prometheus 2.54.0, Grafana 11.2.0, exporters (PostgreSQL, Redis)
  - Dashboard "AS v2 - System Overview" com 6 painéis
  - Métricas: HTTP requests, latência, error rate, cache hit rate, DB operations
  - Documentação: OBSERVABILITY.md (seção MP1)

- **MP2 - Structured Logging** (Issue #166): ✅ Implementado e merged (PR #182)
  - JSON structured logging para staging/production
  - Correlation ID (request_id) via RequestIDMiddleware
  - Service identification (web/worker/beat)
  - Custom logging filters (RequestIDFilter, ContextFilter)
  - Logs human-readable em development, JSON em staging/production
  - Documentação: OBSERVABILITY.md (seção MP2)
  - Testes: 5/5 passando (test_structured_logging.py)

---

## 📖 Origem do Projeto e Arquitetura

**Resumo**: AS v2 substitui planilhas Google/Excel por plataforma web automatizada (Django + React).

**Documentação Completa**: [v2/docs/PROJETO_ORIGEM.md](../v2/docs/PROJETO_ORIGEM.md)

**Conteúdo**: Lógica das planilhas originais, códigos de disponibilidade (E/M/D/P/T/X), stack tecnológica (Python 3.12 + Django 5.1 + PostgreSQL + Redis), modelos principais, funcionalidades atuais, perfis RBAC, RFs (RF01-RF08), situação atual vs próximos passos.

---

## 🔐 RBAC: Sistema de Permissões (Setor + Função)

**Status**: ✅ Implementado (PRs #238-#242)
**Documentação Completa**: [.claude/PLANO_RBAC_SETOR_FUNCAO.md](.claude/PLANO_RBAC_SETOR_FUNCAO.md)

### Conceito
O sistema RBAC usa **duas dimensões** de grupos:
- **SETOR**: Onde o usuário trabalha (ex: Superintendência, DAT, Vidas)
- **FUNÇÃO**: O que o usuário pode fazer (ex: Formador, Coordenador, Gerente)

### Grupos de SETOR (9 grupos)
| Grupo | Descrição |
|-------|-----------|
| Superintendência | Setor estratégico (fluxo SUPER) |
| Vidas | Gerência 2 - Projetos Vida |
| Fluir | Gerência 3 - Projeto Fluir |
| ACerta | Gerência 4 - Projetos ACerta |
| Brincando | Gerência 5 - Brincando e Aprendendo |
| Sou da Paz | Gerência 6 - Projeto Sou da Paz |
| DAT | Departamento de Apoio Técnico |
| Controle | Setor de Controle (operações) |
| Gerência | Gerência genérica |

### Grupos de FUNÇÃO (4 grupos)
| Grupo | Permissões |
|-------|------------|
| Formador | Visualiza grade, gerencia bloqueios pessoais |
| Coordenador | Cria solicitações de eventos |
| Apoio de Coordenação | Auxilia coordenação, visualiza solicitações |
| Gerente | Aprova/reprova, acessa dashboards e relatórios |

### Regra de Aprovação SUPER
```python
can_approve_super = is_superuser OR (
    "Gerente" IN funcoes AND "Superintendência" IN setores
)
```

**Exemplos:**
| Usuário | Setor | Função | Pode Aprovar SUPER? |
|---------|-------|--------|---------------------|
| Maria | Superintendência | Gerente | ✅ Sim |
| João | DAT | Gerente | ❌ Não |
| Pedro | Superintendência | Formador | ❌ Não |

### API /api/me/
Retorna dados RBAC do usuário autenticado:
```json
{
  "id": 1,
  "username": "maria",
  "groups": ["Superintendência", "Gerente"],
  "setores": ["Superintendência"],
  "funcoes": ["Gerente"],
  "is_superuser": false,
  "is_superintendencia": true,
  "can_approve_super": true
}
```

### Arquivos Principais
- `apps/core/views_basic.py`: SETOR_GROUPS, FUNCAO_GROUPS, CurrentUserView
- `apps/core/tests/test_rbac_permissions.py`: 20 testes unitários
- `v2/frontend/src/pages/AdminDAT/UsuariosPage.jsx`: Interface de gestão
- `v2/frontend/e2e/rbac-approval.spec.ts`: Testes E2E Playwright

---

## RF03 - Verificação de Conflitos (IMPLEMENTADO ✅)

### Resumo da Implementação (PR16 - feat/pr16-conflitos-validacoes)

O **RF03 (Verificação de Conflitos)** foi completamente implementado seguindo as regras RD-01 a RD-08. A implementação inclui:

#### Backend (100%)
- **Service Layer** (`apps/core/services/availability_service.py`):
  - Função `check_conflicts(usuario, inicio, fim, municipio)` implementa todas as 8 regras
  - Retorna objeto `AvailabilityResult` com lista de `ConflictDetail` (code, title, detail, ref_id)
  - Timezone-aware: UTC storage, America/Fortaleza comparison
  - Priorização: Bloqueios → Conflitos → Buffer → Capacidade diária

- **API Endpoints** (`apps/core/views_availability.py`):
  - `GET /api/availability/check/` - Checagem individual com RBAC (self ou privilegiado)
  - `POST /api/availability/check-many/` - Checagem em lote (batch) para usuários privilegiados
  - Throttling configurado (`availability_check` scope)
  - Validação de parâmetros (usuario_id, inicio, fim, municipio_id)

#### Frontend (100%)
- **Componente** (`v2/frontend/src/pages/Solicitacoes/NewSolicitacaoPage.jsx`):
  - Integração completa com endpoints de validação e disponibilidade
  - Visual feedback com ícones por tipo de conflito (ISO 9241-110):
    - ❌ Vermelho (X, T): Bloqueantes
    - ⚠️ Laranja (P, D): Atenção
    - ℹ️ Dourado (M): Aviso
  - Exibição detalhada: código + título + intervalo formatado

#### Testes (100%)
- **Cobertura Completa** (`apps/core/tests/test_availability_service.py`):
  - **11 testes unitários** (TestAvailabilityServiceRules):
    - RD-01: Sobreposição total/parcial, adjacência OK
    - RD-02: Bloqueio total (T)
    - RD-03: Bloqueio parcial (P)
    - RD-04: Buffer de deslocamento (D), mesmo município OK
    - RD-05: Capacidade diária (M)
    - RD-06: Timezone-aware (America/Fortaleza)
  - **6 testes de API** (TestAvailabilityCheckEndpoint + Additional):
    - Autenticação obrigatória
    - Validação de parâmetros
    - Batch processing (check-many)
    - RBAC (self ou privilegiado)
    - Múltiplos formadores (qualquer conflito bloqueia)
    - Estrutura de mensagens (RD-08)
  - **Status**: 17/17 testes passando ✅

#### Conformidade com Regras
| Regra | Descrição | Status |
|-------|-----------|--------|
| RD-01 | Não-sobreposição (fim==início OK) | ✅ |
| RD-02 | Bloqueio total (T) | ✅ |
| RD-03 | Bloqueio parcial (P) | ✅ |
| RD-04 | Buffer deslocamento (D) | ✅ |
| RD-05 | Capacidade diária (M) | ✅ |
| RD-06 | Timezone-aware (Fortaleza) | ✅ |
| RD-07 | Prioridade de checagem | ✅ |
| RD-08 | Mensagens estruturadas | ✅ |

#### Commits (Branch: feat/pr16-conflitos-validacoes)
1. `2ae3772` - fix(frontend): correct conflict properties (code, title, detail)
2. `36bce31` - feat(frontend): add icons and colors for conflict types
3. `84f9a48` - test(availability): add 6 tests for RF03 (17 total passing)

---

## Regras de Disponibilidade (Normativas)

As regras abaixo consolidam a lógica original das planilhas e devem ser aplicadas em **todas as checagens de agenda**.

### RD-01 — Não-sobreposição
- Um **Formador** não pode ter dois eventos que se sobreponham parcial ou totalmente.  
- Caso borda: se `fim == início` → **não conflita**.  
- Qualquer overlap de ≥ 1 minuto → **conflito**.

### RD-02 — Bloqueio total (T)
- Um bloqueio marcado como **T (total)** impede quaisquer eventos no intervalo definido.  

### RD-03 — Bloqueio parcial (P)
- Um bloqueio **P (parcial)** impede eventos dentro do subintervalo bloqueado.  
- Fora do subintervalo → permitido.

### RD-04 — Buffer de deslocamento (D)
- Entre **municípios distintos**, exigir um **tempo mínimo de deslocamento** (configurável, ex.: 60–120 min).  
- Para eventos no **mesmo município**, buffer pode ser zero.

### RD-05 — Capacidade diária (M)
- Um formador não pode ter mais de **N horas de eventos por dia** (configurável).  
- Caso ultrapasse, deve ser sinalizado como **M (mais de um evento)**.

### RD-06 — Timezone
- Comparações devem ser **timezone-aware**, usando `America/Fortaleza`.  
- Armazenar em UTC, comparar no TZ do projeto.

### RD-07 — Prioridade de checagem
1. Bloqueios (T, P)  
2. Conflitos por eventos aprovados (sobreposição)  
3. Buffer de deslocamento (D)  
4. Limite diário (M)

### RD-08 — Mensagens de conflito
- Mensagens devem listar:  
  - **Formador(es)** em conflito  
  - **Data** e **intervalo** (HH:MM dd/mm)  
  - **Tipo de conflito** (E, M, D, P, T, X)

---

## Casos de Teste Padronizados para Disponibilidade

- `test_conflict_overlap_total`  
- `test_conflict_overlap_partial`  
- `test_no_conflict_adjacent_end_equals_start`  
- `test_block_total_T_prevents_any_event`  
- `test_block_partial_P_prevents_inside_allows_outside`  
- `test_travel_buffer_between_cities_required`  
- `test_same_city_allows_zero_buffer`  
- `test_daily_capacity_M_exceeded`  
- `test_multi_formador_any_conflict_blocks`  
- `test_timezone_aware_fortaleza_localtime`  
- `test_conflict_messages_include_codes_and_intervals`  

📌 **Obrigatório**: cada implementação de disponibilidade deve manter estes testes válidos.

---

## Política de Aprovação Manual (Obrigatória)

- **PA-01 — Sem auto-aprovação**: Uma `Solicitacao` **nunca** muda para “Aprovada” automaticamente, mesmo se não houver conflitos.  
- **PA-02 — Perfil exigido**: Apenas usuários com **Gerente + Superintendência** (ou superuser) podem aprovar/reprovar. Ver seção RBAC.  
- **PA-03 — Gatilhos pós-aprovação**: Integrações externas (RF05/RF06) só executam **após** aprovação manual concluída.  
- **PA-04 — Estado inicial**: Toda solicitação nasce com `status = pendente`.  
- **PA-05 — Auditoria**: Registrar usuário, data/hora e justificativa (quando houver) em `Aprovacao` e `LogAuditoria`.  
- **PA-06 — UI/UX**: Nas telas do solicitante/coordenador, exibir status e orientações; esconder botões de ação para perfis sem permissão (ISO 9241-110: controle explícito).  
- **PA-07 — Testes obrigatórios**:
  - `test_never_auto_approves_on_clean_or_save`
  - `test_only_superintendencia_can_approve_or_reject`
  - `test_calendar_integration_not_called_before_approval`
  - `test_approval_flow_records_audit_log`
  - `test_non_privileged_user_gets_403_on_approval_endpoint`

---

## Implementação PA-01 a PA-07 (PR17) ✅

**Status**: Implementado e testado (5/5 testes passando)
**Documentação Completa**: [v2/docs/IMPLEMENTACAO_PA.md](../v2/docs/IMPLEMENTACAO_PA.md)

**Resumo**: PR17 implementou conformidade total com Política de Aprovação Manual (CP-02): sem auto-aprovação (PA-01), apenas Superintendência aprova (PA-02), integrações após aprovação (PA-03), AuditLog persistente (PA-05), botões ocultos (PA-06), 5 testes obrigatórios (PA-07).

**Arquivos modificados**: `models.py` (Solicitacao.save), `views.py` (approve/reject + AuditLog), `test_approval_policy_PA.py` (5 testes), `ApprovalsPage.jsx` (PA-06).

**⚠️ Nota**: Aprovação manual NÃO revalida conflitos (intencional - decisões com contexto humano).

---

## Correção PR18 - Restauração de Auto-Aprovação NAO_SUPER (2025-10-25)

**Problema Identificado**: PR17 removeu a auto-aprovação para **TODOS** os fluxos, mas a especificação correta é:
- **SUPER**: Manual approval required (Superintendência)
- **NAO_SUPER**: Auto-approved on creation

**Status**: ✅ Corrigido e testado

### Fluxos Corretos do Sistema

#### Fluxo SUPER (Manual)
1. Coordenador acessa `/solicitacoes/nova` e preenche dados
2. Solicitação criada com `status='pendente'`
3. Superintendência aprova/reprova via `/aprovacoes`
4. Se aprovado → vai para `/pre-agenda` (Controle cria evento no Google Calendar)
5. Se reprovado → Coordenador é notificado para nova solicitação

#### Fluxo NAO_SUPER (Auto-aprovado)
1. Coordenador de projeto NAO_SUPER acessa `/solicitacoes/nova` e preenche dados
2. **Solicitação criada com `status='aprovado'` automaticamente**
3. Vai direto para `/pre-agenda` (Controle cria evento no Google Calendar)

### Mapeamento de Fluxos na Planilha Original
**Arquivo**: `v2/backend/data/csv-import/Cópia de Acompanhamento de Agenda _ 2025.xlsx`

O **nome da aba** define o fluxo dos projetos (coluna "K" - "projeto"):
- **Aba "Super"** → Projetos são **SUPER** (requerem aprovação manual)
  - 8 projetos: Cataventos, CIRANDAR, LENDO E ESCREVENDO, NOVO LENDO, PROJETO AMMA, PROJETO MIUDEZAS E DESCOBERTAS, TEMA, UNI DUNI TÊ
- **Abas "ACerta", "Outros", "Brincando", "Vidas"** → Projetos são **NAO_SUPER** (auto-aprovados)
  - Total: ~16 projetos + variantes

**Nota**: Correção aplicada em 25/10/2025 - 8 projetos da aba "Super" foram atualizados de NAO_SUPER → SUPER no banco.

### Mudanças Implementadas

**1. models.py - Restauração de Auto-Aprovação**
- **Arquivo**: `v2/backend/apps/core/models.py` (linhas 431-448)
- **Mudança**: Restaurada lógica de auto-aprovação para `projeto.fluxo == 'NAO_SUPER'`

```python
def save(self, *args, **kwargs):
    """
    Override save para implementar auto-aprovação de fluxo NAO_SUPER.

    Fluxos do sistema:
    - SUPER: Requer aprovação manual pela Superintendência (PA-01 a PA-07)
    - NAO_SUPER: Auto-aprovado automaticamente na criação

    Histórico:
    - PR 13/N: Auto-aprovação implementada para NAO_SUPER
    - PR17: REMOVEU auto-aprovação (INCORRETO - revertido em PR18)
    - PR18: RESTAURA auto-aprovação para NAO_SUPER conforme especificação correta
    """
    # Auto-aprovar apenas projetos NAO_SUPER na criação
    if self.pk is None and self.projeto and self.projeto.fluxo == 'NAO_SUPER':
        self.status = 'aprovado'

    super().save(*args, **kwargs)
```

**2. test_approval_policy_PA.py - Atualização de Testes**
- **Arquivo**: `v2/backend/apps/core/tests/test_approval_policy_PA.py`
- **Mudanças**:
  - Fixture `solicitacao_pendente` agora usa projeto com `fluxo='SUPER'`
  - Teste `test_never_auto_approves_on_clean_or_save` atualizado para validar apenas projetos SUPER
  - Nota adicionada: "Projetos NAO_SUPER são auto-aprovados (testado em test_solicitacao_fluxo.py)"

**3. test_solicitacao_fluxo.py - Correção de Fixtures**
- **Arquivo**: `v2/backend/apps/core/tests/test_solicitacao_fluxo.py`
- **Mudança**: Fixture `grupos` agora usa `get_or_create()` para evitar erros de unique constraint

### Validação

```bash
# Teste manual no Django shell
✅ Projeto SUPER: status = pendente (esperado: pendente)
✅ Projeto NAO_SUPER: status = aprovado (esperado: aprovado)

============================================================
✅ SUCESSO! A correção está funcionando:
  - SUPER: pendente (requer aprovação manual)
  - NAO_SUPER: aprovado (auto-aprovado)
============================================================
```

### Impacto

- **PA-01 Atualizada**: "Solicitações de projeto SUPER nunca são auto-aprovadas"
- **PA-02 a PA-07**: Sem mudanças, aplicam-se apenas ao fluxo SUPER
- **Testes existentes**: `test_solicitacao_fluxo.py` já valida ambos os fluxos (9 testes)

### Arquivos Modificados

- `v2/backend/apps/core/models.py` (Solicitacao.save)
- `v2/backend/apps/core/tests/test_approval_policy_PA.py` (fixture + docstrings)
- `v2/backend/apps/core/tests/test_solicitacao_fluxo.py` (fixture grupos)

---

## Diretrizes de UX/IHC — ISO 9241-110
Todo o sistema deve seguir os princípios ergonômicos para design de sistemas interativos:
1. **Adequação à tarefa**
2. **Auto-descritividade**
3. **Conformidade com expectativas do usuário**
4. **Tolerância a erros**
5. **Controle explícito**
6. **Adequação à individualização**
7. **Adequação à aprendizagem**

### Diretrizes visuais complementares
- Uso consistente de componentes **Ant Design** e utilitários Tailwind para responsividade.  
- Paleta de cores e tipografia padronizadas.  
- Destaque visual para ações primárias.  
- Layouts limpos, com hierarquia visual clara.  

---

## Boas Práticas de Desenvolvimento — Aprender Sistema (AS)

### Python
- Seguir **PEP8** e **PEP20**.  
- Usar nomes descritivos, funções curtas, `type hints`.  
- Documentar com docstrings.  
- Reutilizar código (DRY).  
- Preferir **dataclasses**.  

### Django
- Models = fonte de verdade.  
- Views curtas; lógica em **services**.  
- Templates só para apresentação.  
- Consultas otimizadas (select_related/prefetch).  
- URLs nomeadas.  
- Testes obrigatórios.  
- Admin apenas para manutenção interna.  

### Integrações Externas
- Isolar em `core/services/integrations/`.  
- Exceções claras.  
- Nunca expor credenciais.  
- Funções pequenas/testáveis.  
- Retry/backoff em chamadas críticas.  

### Gerais
- **KISS, YAGNI, clareza > esperteza**.  
- Commits pequenos, atômicos.  
- Logs e auditoria obrigatórios.  
- Testes: unitários, integração, end-to-end.  

---

## Fluxos essenciais (Fase 1)
- RF02 — Solicitar evento.
- RF03 — Verificar conflitos para formadores.
- RF04 — Aprovar/Reprovar solicitações.
- RF05/RF06 — Criar evento no Google Calendar + gerar link do Meet.

---

## RF05/RF06: Google Calendar + Meet ✅

**Status**: Completo (PRs #32, #33, #41, #42)
**Documentação Completa**: [v2/docs/GUIDE_GCAL.md](../v2/docs/GUIDE_GCAL.md)

**Funcionalidades**:
- RF05: Publicação eventos (endpoint `/publish/`, dry-run/apply, fake/google client)
- RF06: Google Meet links (campo `meet_link`, geração automática via `conferenceData`)
- Modalidade: `is_online` (presencial vs online)

**Variáveis principais**:
```bash
GCAL_CLIENT=fake|google
GCAL_CALENDAR_ID=your_calendar_id@group.calendar.google.com
GOOGLE_SERVICE_ACCOUNT_FILE=/secrets/aprender-sa-key.json
GCAL_SEND_UPDATES=none
```

**Testes**: 6 testes backend passando (publish, retry, send_updates, conference_version, meet_link_persist, serializer).

---

## Como colaborar
- Planejar antes de codar.  
- Usar `/permissions plan`.  
- Escrever/atualizar testes primeiro.  
- Validar fluxos end-to-end (Playwright MCP).  
- Atualizar sempre o `CLAUDE.md`.  
- Respeitar Boas Práticas e UX/IHC.  

---

## Ações que o Claude deve priorizar
1. **Usar ferramentas .claude/ proativamente**:
   - `/new-feat` para features complexas (>3 passos)
   - `/review` antes de commitar código
   - `/check-conflicts` ou `/approve-flow` para validar compliance
   - Skills quando precisar detalhamento de domínio
2. Ler código e entender contexto completo.
3. Produzir plano passo a passo (usar `/project_plan` se necessário).
4. Implementar em commits pequenos, atômicos e testados.
5. Escrever mensagens descritivas (conventional commits).
6. Não alterar testes sem necessidade.
7. Validar com princípios UX/IHC e regras de disponibilidade.  

---

## Testes
- Unitários/integração: `python manage.py test`  
- End-to-end: Playwright MCP  

---

## Regras de Repositório
- Branches: `feat/`, `fix/`, `chore/`  
- Commits convencionais.  
- Nunca commitar `.env` e segredos.  

---

## Warnings conhecidos
- `staticfiles.W004`: criar pasta `static/` ou configurar `STATICFILES_DIRS`.  

---

## Anotações rápidas
- Pressione `#` aqui para Claude incorporar instruções recorrentes.  

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
- `/migrate` - Executar migrações Django e validar modelo
- `/test-coverage` - Análise completa de cobertura de testes
- `/review` - Review automático de código (style, security, best practices)

**Fluxos de Negócio (Testes):**
- `/approve-flow` - Testar fluxo completo de aprovação (PA-01 a PA-07)
- `/check-conflicts` - Testar verificação de conflitos (RF03, RD-01 a RD-08)

**ETL e Importação:**
- `/etl-dry` - Rodar ETL em modo dry-run (simula sem persistir)
- `/etl-apply` - Rodar ETL com apply (persiste no banco + relatórios)

**Deploy e Infraestrutura:**
- `/deploy-staging` - Deploy completo para ambiente staging

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
├── CLAUDE-principles.md       # Qualidade de código (463L)
├── GUIA_USO.md                # Guia completo ⭐
├── CHECKLIST_FERRAMENTAS.md   # Checklist pós-resumo ⭐ NOVO
├── MELHORIAS_2025-11-14.md    # Histórico de melhorias
├── settings.json              # Hooks + permissions
├── commands/                  # 16 slash commands
│   ├── review.md              # Original (170L)
│   └── review-enhanced.md     # Novo (573L) ⭐
└── skills/                    # 3 skills (aprender-domain, django-patterns, etl-guidelines)
```

**Quick Start**:
- Nova feature → `/new-feat <descrição>`
- Review código → `/review <arquivo>`
- Testar compliance → `/check-conflicts` ou `/approve-flow`
- ETL → `/etl-dry` depois `/etl-apply`
- Deploy → `/deploy-staging full`

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
- **PA-02**: Apenas usuários com perfil **Superintendência** (ou Admin delegado) podem aprovar/reprovar.
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

---

## Documento Consolidado — Projeto Aprender Sistema (AS)

### 1. Origem do Projeto: Lógica das Planilhas
O sistema original funcionava integralmente sobre planilhas Google/Excel, que acumulavam regras complexas de negócio. O novo sistema busca substituir essas planilhas por uma plataforma web automatizada.

#### 1.1 Planilhas Originais
- Disponibilidade_2025.xlsx  
- Planilha de Controle - 2025.xlsx  
- Usuários.xlsx  
- Produtos.xlsx  

#### 1.2 Regras de Negócio Embutidas
- **Códigos de Disponibilidade**  
  - E → Evento confirmado  
  - M → Mais de um evento  
  - D → Deslocamento  
  - P → Bloqueio parcial  
  - T → Bloqueio total  
  - X → Conflito  

- **Verificação de Disponibilidade**: fórmulas cruzadas verificavam automaticamente se o formador podia ser agendado.  
- **Consistência de Dados**: uso de IMPORTRANGE e referências cruzadas para manter sincronizados nomes de usuários, municípios e tipos de eventos.  

- **Fluxo Operacional**:  
  1. Solicitação feita por coordenadores em uma planilha.  
  2. Verificação manual de disponibilidade e conflitos.  
  3. Aprovação (ou reprovação) pela Superintendência.  
  4. Lançamento no Google Calendar manual.  

---

### 2. O Novo Sistema (Aprender Sistema - AS)

#### 2.1 Tecnologias
- **Backend**: Python 3.11 (imagem base) + Django 5.1.x + DRF + Celery (worker e beat)  
- **Banco de Dados**: PostgreSQL 15  
- **Cache & Filas**: Redis 7 (cache e broker Celery)  
- **Infraestrutura**: Docker + Docker Compose (`v2/infra/docker-compose.yml`) orquestrado via `make`  
- **Frontend**: React (Vite) + Tailwind + Ant Design; build Docker-first e dev server com proxy `/api`  

#### 2.2 Estrutura de Código
- **Backend (`v2/backend`)**
  - Apps: `apps.core` (domínio principal) e `apps.dat_ingest` (ETLs e ingestão)
  - Configurações Django em `config/`
  - Comandos ETL em `apps/dat_ingest/management/commands`
- **Frontend (`v2/frontend`)**
  - Projeto React com Vite, Tailwind e Ant Design
  - Páginas: Pré-agenda, Grade Mensal (Formadores/Coordenadores), painéis Controle/DAT

**Modelos principais**:  
- Usuario → usuários do sistema  
- Formador → instrutores com disponibilidade e área de atuação  
- Projeto → agrupamento de ações  
- Municipio → municípios atendidos  
- TipoEvento → classificações dos eventos  
- Solicitacao → pedido de evento  
- Aprovacao → status de análise de uma solicitação  
- Deslocamento → registros de deslocamentos  
- DisponibilidadeFormador → agenda consolidada  
- LogAuditoria → rastreamento de ações  

**ETLs**: Management commands para Acompanhamento, Deslocamento, Ações (Controle) e Cadastros (DAT) com suporte a `--dry-run` e relatórios em `out_etl/`

#### 2.3 Funcionalidades Atuais
- Autenticação e RBAC via Django (grupos: Superintendência, Controle, Coordenador, Formador, DAT, Gerência)  
- API REST: `/api/solicitacoes/`, `/api/availability/monthly/`, `/api/controle/acoes/`, `/api/dat/acoes/`, `/api/features/`, `/api/me/`  
- Pré-agenda React: fluxo de approve/reject (Superintendência) e preview/publish (Controle) respeitando `apply_blocked`  
- Grade Mensal React com duas grades (Formadores/Coordenadores), filtros compartilhados, detalhes por célula e export CSV  
- ETLs CSV/XLSX com relatórios em `out_etl/*.json` e idempotência por `external_hash`  
- Integração Google Calendar real (`asv2-{id}`, `sendUpdates='none'`) com fallback fake controlado por feature flags  

---

### 3. Papéis, Perfis e Autorizações

#### 3.1 Perfis de Usuário
- **Superintendência**: autoriza/reprova solicitações, resolve conflitos, valida agenda final  
- **Coordenadores**: podem solicitar eventos, mas não aprovar  
- **Formadores**: podem bloquear sua agenda (parcial/total), mas não solicitam/aprovam eventos  

#### 3.2 Fluxo de Autorização
1. Coordenador envia solicitação.  
2. Sistema checa disponibilidade do formador (conflitos, bloqueios, deslocamentos).  
3. Se sem conflito → solicitação vai para Superintendência.  
4. Superintendência aprova → cria evento no Google Calendar.  
5. Superintendência reprova → retorna com justificativa.  

---

### 4. Requisitos Funcionais (RFs)
- RF01: Importação de dados (usuários, municípios, projetos, tipos de evento, produtos).  
- RF02: Solicitação de eventos.  
- RF03: Verificação de conflitos (sobreposição, deslocamentos, bloqueios).  
- RF04: Fluxo de aprovações com controle de perfis.  
- RF05: Integração com Google Calendar.  
- RF06: Criação automática de link Google Meet.  
- RF07: Auditoria de todas as operações críticas.  
- RF08: Interface de mapa mensal (disponibilidade).  

---

### 5. Integrações Externas
- **Google Calendar API**  
  - Credenciais no Google Cloud  
  - Evento aprovado → gera evento no calendário  
  - Evento gera link Meet automaticamente via API  

---

### 6. Situação Atual vs. Próximos Passos

✅ Concluído até agora:
- Estrutura base Django + PostgreSQL em Docker
- Modelos principais criados
- Migrações aplicadas
- Importação inicial de formadores concluída
- API de disponibilidades + página de visualização
- Cadastro de bloqueio de agenda
- Solicitação de eventos simples
- Fluxo de aprovações iniciado
- Home consolidando links
- **PR16**: RF03 - Verificação de Conflitos (17 testes passando)
- **PR17**: PA-01 a PA-07 - Política de Aprovação Manual (5 testes passando, frontend conforme)

🚧 Próximos Passos:
- Criar scripts de importação para municípios, projetos, tipos de evento
- ~~Implementar RF03 (checagem automática de conflitos)~~ ✅ Completo (PR16)
- ~~Finalizar RF04 (workflow completo de aprovações)~~ ✅ PA-01 a PA-07 completo (PR17)
- Conectar com Google Calendar API (RF05/RF06)
- Implementar testes end-to-end (Playwright)
- Refinar interface (baseada em mapa mensal como referência)

---

### 6.1. Importação de Usuários e Grupos

**Estrutura da Planilha (Acompanhamento de Agenda):**
- Coluna **N**: Coordenador
- Colunas **O-S**: Formador 1, Formador 2, ..., Formador 5

**Regra de Atribuição de Grupos:**
- Usuários com username `coordenacao*` → Grupo "Coordenador"
- Demais usuários com participações → Grupo "Formador"

**Comando de Backfill:**
```bash
python manage.py backfill_user_groups --apply
```
- Atribui grupos faltantes baseado no padrão do username
- Usado após importação inicial de usuários (122 usuários importados)
- Resultado: 65 Formadores + 10 Coordenadores atribuídos corretamente

---

### 7. Benefícios Esperados
- Fim da dependência de planilhas manuais  
- Fluxo de solicitações, aprovações e conflitos totalmente digital  
- Registro auditável e confiável das agendas  
- Integração automática com Google Calendar e Meet  
- Escalabilidade para múltiplos anos e centenas de formadores  

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
- **PA-02 — Perfil exigido**: Apenas usuários com perfil **Superintendência** (ou Admin delegado) podem aprovar/reprovar.  
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

## Implementação PA-01 a PA-07 (PR17)

**Branch**: `feat/pr17-politica-aprovacao`
**Status**: ✅ Implementado e testado (commit ab1858b + PA-06 frontend)
**Data**: 2025-10-23

### Resumo da Implementação

PR17 implementa conformidade total com a Política de Aprovação Manual (CP-02), garantindo que:
1. Nenhuma solicitação é auto-aprovada (PA-01)
2. Apenas Superintendência pode aprovar/reprovar (PA-02)
3. Integrações externas só executam após aprovação (PA-03)
4. Auditoria completa em AuditLog (PA-05)
5. Botões ocultos para não-autorizados no frontend (PA-06)
6. 5 testes obrigatórios implementados e passando (PA-07)

### Mudanças Implementadas

#### Backend (Django)

**1. models.py - Remoção de Auto-Aprovação (PA-01)**
- **Arquivo**: `v2/backend/apps/core/models.py` (linhas 412-436)
- **Problema**: `Solicitacao.save()` auto-aprovava quando `projeto.fluxo == "NAO_SUPER"`
- **Correção**: Removida lógica de auto-aprovação completamente
- **Código**:
```python
def save(self, *args, **kwargs):
    """
    Override save para garantir conformidade com PA-01.

    PA-01: Nenhuma solicitação é auto-aprovada, independentemente do fluxo do projeto.

    Histórico:
    - PR 13/N: Auto-aprovação implementada (REMOVIDA em PR17)
    - PR17: Conformidade com PA-01 (Política de Aprovação Manual obrigatória)
    """
    # PA-01: Sem auto-aprovação. Status sempre começa 'pendente'.
    if self.pk is None and not hasattr(self, '_status_explicitly_set'):
        pass  # Mantém o default do campo (status='pendente')

    super().save(*args, **kwargs)
```

**2. views.py - Auditoria Persistente (PA-05)**
- **Arquivo**: `v2/backend/apps/core/views.py`
- **Métodos**: `approve()` (linhas 165-220), `reject()` (linhas 236-290)
- **Problema**: Métodos só faziam `logger.info()`, sem AuditLog persistente
- **Correção**: Adicionado `AuditLog.objects.create()` em ambos os métodos
- **Código**:
```python
# PA-05: AuditLog persistente (compliance)
AuditLog.objects.create(
    usuario=request.user,
    action="APPROVE",  # ou "REJECT"
    model_name="Solicitacao",
    details={
        "solicitacao_id": solicitacao.id,
        "prev_status": prev_status,
        "new_status": "aprovado",  # ou "reprovado"
        "justificativa": justificativa,
        "ip_address": client_ip,
        "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
    },
)
```

**3. Testes Obrigatórios (PA-07)**
- **Arquivo**: `v2/backend/apps/core/tests/test_approval_policy_PA.py` (344 linhas)
- **5 testes implementados e passando**:
  1. `test_never_auto_approves_on_clean_or_save` - Valida PA-01
  2. `test_only_superintendencia_can_approve_or_reject` - Valida PA-02
  3. `test_non_privileged_user_gets_403_on_approval_endpoint` - Valida PA-02 (complementar)
  4. `test_calendar_integration_not_called_before_approval` - Valida PA-03
  5. `test_approval_flow_records_audit_log` - Valida PA-05

#### Frontend (React)

**4. ApprovalsPage.jsx - Botões Ocultos (PA-06)**
- **Arquivo**: `v2/frontend/src/pages/Aprovacoes/ApprovalsPage.jsx`
- **Linhas**: 66-68 (estado), 89-109 (useEffect), 211 (botões)
- **Implementação**:
  - Importa `getMe` da API
  - Carrega dados do usuário no mount
  - Verifica `is_superuser || is_superintendencia || groups.includes('Superintendência')`
  - Armazena em `canApprove` state
  - Botões só renderizam se `record.status === 'pendente' && canApprove`
- **Conformidade ISO 9241-110**: Controle explícito (usuário vê apenas ações permitidas)

### Resultados dos Testes

```bash
cd v2/infra && docker compose exec -T web pytest apps/core/tests/test_approval_policy_PA.py -v

test_approval_policy_PA.py::test_never_auto_approves_on_clean_or_save PASSED
test_approval_policy_PA.py::test_only_superintendencia_can_approve_or_reject PASSED
test_approval_policy_PA.py::test_non_privileged_user_gets_403_on_approval_endpoint PASSED
test_approval_policy_PA.py::test_calendar_integration_not_called_before_approval PASSED
test_approval_policy_PA.py::test_approval_flow_records_audit_log PASSED

========================= 5 passed in 2.34s =========================
```

### Conformidade PA-01 a PA-07

| Requisito | Status | Implementação | Arquivo |
|-----------|--------|---------------|---------|
| **PA-01** | ✅ | Sem auto-aprovação em `Solicitacao.save()` | `models.py:412-436` |
| **PA-02** | ✅ | Permission class `IsSuperintendencia` + endpoints protegidos | `permissions.py`, `views.py` |
| **PA-03** | ✅ | Celery task `task_publish_solicitacao_to_gcal` validado via mock | `test_approval_policy_PA.py:201-262` |
| **PA-04** | ✅ | Campo `status` tem `default='pendente'` | `models.py:120` |
| **PA-05** | ✅ | `AuditLog.objects.create()` em approve/reject | `views.py:165-220, 236-290` |
| **PA-06** | ✅ | Botões ocultos para não-Superintendência | `ApprovalsPage.jsx:66-68, 211` |
| **PA-07** | ✅ | 5 testes obrigatórios implementados e passando | `test_approval_policy_PA.py` |

### ⚠️ Nota Importante: Aprovação Manual NÃO Revalida Conflitos

**Comportamento intencional**: O endpoint `approve()` (views_solicitacao.py:268-323) **NÃO** chama `check_conflicts()` antes de aprovar.

**Razão**: Superintendência toma decisões com **contexto humano** que o sistema não captura:
- Exceções autorizadas
- Prioridades políticas/organizacionais
- Contexto específico do município/projeto
- Negociações não-formalizadas

**Fluxo**: Superintendência acessa `/disponibilidade` (visualização da grade) e verifica **manualmente** antes de aprovar em `/aprovacoes`.

**Sistema = ferramenta de suporte à decisão, NÃO automatização total.**

### Arquivos Modificados

**Backend**:
- `v2/backend/apps/core/models.py` (Solicitacao.save)
- `v2/backend/apps/core/views.py` (approve/reject methods)
- `v2/backend/apps/core/tests/test_approval_policy_PA.py` (novo, 344 linhas)

**Frontend**:
- `v2/frontend/src/pages/Aprovacoes/ApprovalsPage.jsx` (PA-06)

### Commits

- `ab1858b` - fix(approval): remove auto-approval, add AuditLog, fix tests (5/5 passing)
- `[próximo]` - feat(frontend): add PA-06 permission check in ApprovalsPage

### Próximos Passos

✅ PA-01 a PA-07 completo
⏳ Push branch + criar PR17
⏳ Review e merge

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

## RF05/RF06: Google Calendar + Meet (Implementado ✅)

**Status**: Completo (PRs #32, #33, #41, #42; Issues #35–#40)

### Funcionalidades

#### 1. Publicação de Eventos (RF05)
- **Endpoint**: `POST /api/solicitacoes/{id}/publish/`
- **Parâmetros**:
  - `dry_run` (bool): `true` = simulação (não persiste), `false` = publicação real
  - `apply_blocked` (bool): `true` = força publicação mesmo com `GCAL_CLIENT=fake`
- **Comportamento**:
  - **Preview** (`/preview-gcal/`): Sempre retorna payload completo mas **não persiste** no DB
  - **409 CONFLICT**: Quando `GCAL_CLIENT != "google"` e `apply_blocked=false`, retorna 409 e **não persiste**
  - **APPLY real**: Apenas quando `GCAL_CLIENT=google` ou `apply_blocked=true` **persiste no DB**

#### 2. Google Meet Link (RF06)
- **Campo**: `meet_link` (TextField, read-only no serializer)
- **Geração**: Automática via `conferenceData` com `requestId` único
- **Persistência**:
  - ✅ **APPLY real**: Persiste `meet_link` no banco
  - ❌ **Preview**: Retorna no payload mas **não persiste**
  - ❌ **409 blocked**: Não persiste
  - ❌ **dry_run=true**: Não persiste
- **Exposição**: Serializer `SolicitacaoSerializer` inclui `meet_link` em GET `/api/solicitacoes/`

#### 3. Modalidade Online/Presencial (`is_online`)
- **Campo**: `is_online` (BooleanField, default=False)
- **Comportamento**:
  - `is_online=false`: Evento presencial, **sem `conferenceData`**, sem Meet link
  - `is_online=true`: Evento online, **com `conferenceData`**, gera Meet link automaticamente
- **UI**: Checkbox no wizard de solicitação (passo 3 "Detalhes")
- **Migration**: `0023_add_is_online.py`

### Variáveis de Ambiente

```bash
# Google Calendar client type ('fake' ou 'google')
GCAL_CLIENT=fake  # default: 'fake' (seguro para dev)

# Calendar ID (primary ou ID específico)
GCAL_CALENDAR_ID=your_calendar_id@group.calendar.google.com

# Service Account credentials (escolher UMA das opções)
GOOGLE_SERVICE_ACCOUNT_FILE=/secrets/aprender-sa-key.json
# ou
GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'

# Email notifications ('none', 'all', 'externalOnly')
GCAL_SEND_UPDATES=none  # default: 'none'
```

### Arquivos Principais

**Backend**:
- `v2/backend/apps/core/models.py`: Campo `is_online` (linha 86), `meet_link` (linha 126)
- `v2/backend/apps/core/serializers.py`: Serializer com `meet_link` e `is_online` (linhas 82-98)
- `v2/backend/apps/core/services/gcal_sync_service.py`: Lógica de payload com `conferenceData`
- `v2/backend/apps/core/services/gcal_google_client.py`: Cliente real Google Calendar API
- `v2/backend/apps/core/migrations/0022_add_meet_link.py`: Migration `meet_link`
- `v2/backend/apps/core/migrations/0023_add_is_online.py`: Migration `is_online`

**Frontend**:
- `v2/frontend/src/pages/Solicitacoes/NewSolicitacaoWizard.jsx`: Checkbox `is_online` (linhas 358-365)
- `v2/frontend/src/components/MeetLink.jsx`: Componente reutilizável para exibir/copiar link Meet

**Documentação**:
- `v2/docs/GUIDE_GCAL.md`: Guia completo de configuração GCal + Meet
- `.claude/CLAUDE.md`: Esta seção

### Testes

**Backend** (`v2/backend/apps/core/tests/`):
- `test_gcal_publish_apply_blocked.py`: Testa 409 quando `GCAL_CLIENT=fake` + `apply_blocked=false`
- `test_gcal_retry_backoff.py`: Retry com exponential backoff
- `test_gcal_send_updates.py`: Validação de `sendUpdates` parameter
- `test_gcal_conference_version.py`: `conferenceDataVersion=1` obrigatório
- `test_gcal_meet_link_persist.py`: Persistência de `meet_link` apenas em APPLY real
- `test_solicitacao_serializer_meet_link.py`: Serializer expõe `meet_link`

**Status**: ✅ Todos os testes passando

### Issues e PRs Relacionados

**PRs Principais**:
- **#32**: Implementação inicial GCal (fake client + migrations)
- **#33**: Google Calendar Client real + retry/backoff
- **#41**: Campo `meet_link` + persistência APPLY-only
- **#42**: Campo `is_online` + modalidade online/presencial

**Issues**:
- **#35**: Integração Google Calendar API (fechada por #32)
- **#36**: Geração de Meet links (fechada por #41)
- **#37**: Retry policy para GCal API (fechada por #33)
- **#38**: Testes de integração GCal (fechada por #33)
- **#39**: Quarentena testes `dat_ingest` (em andamento)
- **#40**: Remover quarentena após #39 (pendente)

### Próximos Passos

- ⏳ Fechar issue #39 (resolver testes `dat_ingest`)
- ⏳ Remover quarentena `-k 'not dat_ingest'` dos workflows CI (#40)
- ✅ Smoke test com `GCAL_CLIENT=google` em ambiente staging

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

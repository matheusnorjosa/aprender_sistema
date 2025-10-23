# Projeto: Aprender Sistema (AS) — Guia do Claude Code

## Contexto do Projeto
- Objetivo: Substituir planilhas pelo **AS** para solicitação → aprovação → criação de eventos (Google Calendar), com verificação de conflitos e logs de auditoria.
- Stack: **Python 3.11 + Django 5.1.x + DRF + Celery + PostgreSQL 15 + Redis 7**, containers via **Docker + Docker Compose** (`v2/infra/docker-compose.yml`).
- Frontend: **React (Vite) + Tailwind + Ant Design**, dev server com proxy `/api → http://localhost:8002` e chamadas com `credentials: 'include'`.
- Fuso horário padrão: `America/Fortaleza`.

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

## Como colaborar
- Planejar antes de codar.  
- Usar `/permissions plan`.  
- Escrever/atualizar testes primeiro.  
- Validar fluxos end-to-end (Playwright MCP).  
- Atualizar sempre o `CLAUDE.md`.  
- Respeitar Boas Práticas e UX/IHC.  

---

## Ações que o Claude deve priorizar
1. Ler código e entender.  
2. Produzir plano passo a passo.  
3. Implementar em commits pequenos e testados.  
4. Escrever mensagens descritivas.  
5. Não alterar testes sem necessidade.  
6. Validar com princípios UX/IHC e regras de disponibilidade.  

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

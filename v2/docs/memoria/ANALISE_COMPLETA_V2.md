# 📊 Análise Completa: Aprender Sistema v2 - Estado Atual vs. Falta

**Data:** 2025-10-20
**Escopo:** v2-only (infra, backend Django, ETL, GCal, disponibilidade)
**Objetivo:** Confirmar o que existe vs. o que falta para entregar fluxo E2E completo

---

## 📋 Resumo Executivo (5 linhas)

O v2 possui **infraestrutura sólida** (Docker, Celery, modelos core, comandos GCal) mas **lacunas críticas impedem E2E**:
1. ❌ **Modelo `Participation` inexistente** → não há como representar papéis múltiplos (Coordenador/Formador/Convidado)
2. ❌ **ETL Acompanhamento não implementado** → nenhum loader para ACerta/Brincando/Vidas/Super/Outros
3. ❌ **API `/api/availability/monthly` ausente** → front não consegue exibir matriz E/2/D/D1/P/T/X
4. ❌ **`GoogleCalendarClient` é stub** → NotImplementedError, apenas `FakeCalendarClient` funciona
5. ⚠️ **BUG ativo:** `prefetch_related("formadores")` em 4 linhas (views.py:145,149; views_solicitacao.py:75,79) → relação inexistente

**Prontidão:** ~60% implementado; 4-6 PRs estimados para E2E funcional.

---

## ✅ O QUE JÁ EXISTE (com referências)

### 1. Infra/DevOps

#### Docker Compose ✅
- **Arquivo:** `v2/infra/docker-compose.yml`
- **Project name:** `aprender_v2` (linha 1) ✅
- **Portas:**
  - DB: `5434:5432` (linha 10) ✅
  - Redis: `6380:6379` (linha 16) ✅
  - Web: `8002:8000` (linha 27) ✅
- **Serviços:** db, redis, web, worker, beat ✅
- **Volumes:** apenas `db_data` (linha 52)
- ❌ **FALTA:** volume `/app/data/csv-import` para ETL

#### Makefiles ✅
- **v2/Makefile:** alvos `up`, `down`, `logs`, `shell`, `migrate`, `seed`, `readyz`, `healthz`, `preview-json`, `apply-json`, `flags-fake`, `flags-google`
- **v2/infra/Makefile:** comandos Docker e Celery

#### RUNBOOK ✅
- **Arquivo:** `v2/docs/RUNBOOK.md`
- Instruções para recarregar .env, worker/beat, ETL

#### .env.example ❌
- ❌ **AUSENTE** em `v2/infra/` (não encontrado)
- **IMPACTO:** novos desenvolvedores não sabem quais variáveis são necessárias

#### CI/CD ✅
- **Workflows:**
  - `.github/workflows/v2-ci.yml` (existe, paths corretos para v2)
  - `.github/workflows/ban-v1.yml` (guard v2-only)
- **Checks:** guard, security, test (PR #20 corrigiu compatibilidade)

---

### 2. Backend/Settings/URLs

#### Settings ✅
- **Arquivo:** `v2/backend/config/settings.py`
- **REQUIRE_DOCKER=1:** valida Docker obrigatório (linhas 18-23) ✅
- **Celery Beat Schedule:** `preview_then_apply_gcal` a cada 5 min (linhas 255-260) ✅
- **GCAL_CLIENT:** config para fake vs. google
- **DATA_IMPORT_DIR:** `/app/data/csv-import` (linha 334)

#### URLs e Health Endpoints ✅
- `/healthz/` → `config/urls.py:28`
- `/api/readyz/` → `apps/core/urls.py:29`
- `/api/features/` → `apps/core/urls.py:30`
  - **Lógica:** `apply_blocked = gcal_client != "google"` (`views_health.py:64`)
- `/api/me/` → `apps/core/urls.py:31`

---

### 3. Modelagem/Core

#### Modelos Implementados ✅
- **Usuario, Municipio, Projeto, TipoEvento, AvailabilityBlock**
- **Solicitacao** (`models.py:162`) - status=pendente|aprovado|reprovado
- **Config** (`models.py:277`), **Compra** (`models.py:330`), **AuditLog** (`models.py:389`)

#### Modelo AUSENTE ❌
- ❌ **`Participation`** (NÃO encontrado)
  - **IMPACTO CRÍTICO:** não há como representar múltiplos formadores ou papéis

#### BUG Ativo ❌
- **views.py:145,149** e **views_solicitacao.py:75,79:** `.prefetch_related("formadores")`
- **ERRO:** relação inexistente

---

### 4. Views/Permissões ✅ (com bugs)

- **SolicitacaoViewSet:** Create restrito, Approve/Reject só Superintendência ✅
- **AvailabilityCheckView:** implementa RD-01 a RD-08 ✅
- **BUG:** prefetch_related inválido ❌

---

### 5. GCal Integration

- **Comando:** `preagenda_to_gcal.py` ✅
- **Cliente Fake:** implementado ✅
- **Cliente Google:** stub (NotImplementedError linha 35-38) ❌
- **Celery Beat:** a cada 5min ✅

---

### 6. ETL

- **Loaders existem:** usuarios, municipios, projetos, tipos_evento ✅
- **Comandos:** etl_load_xlsx, etl_upsert_core, etl_all ✅
- **FALTA:** parse_acompanhamento, parse_disponibilidade ❌
- **FALTA:** import_compras_from_file ❌

---

## ❌ LACUNAS CRÍTICAS

1. **Modelo Participation** - BLOQUEADOR para ETL e múltiplos formadores
2. **ETL Acompanhamento** - BLOQUEADOR para popular banco
3. **API /api/availability/monthly** - BLOQUEADOR para UX calendário
4. **GoogleCalendarClient real** - BLOQUEADOR para produção
5. **import_compras_from_file** - Baixa prioridade
6. **Volume /app/data/csv-import** - Ops
7. **.env.example** - Docs
8. **BUG prefetch** - CRÍTICO

---

## 🎯 PLANO DE PRS (4-6 PRs)

### PR #1: Modelo Participation + Fix Bug ⚡ URGENTE
**Tempo:** 1 dia
**Arquivos:** models.py, migrations, serializers.py, views.py, views_solicitacao.py, testes

### PR #2: ETL Acompanhamento ⚡ CRÍTICO
**Tempo:** 3-5 dias
**Escopo:** parse_acompanhamento, normalizações, Participation, aprovações automáticas

### PR #3: API /api/availability/monthly 📊
**Tempo:** 2-3 dias
**Escopo:** matriz E/2/D/P/T/X, cache 5min, sumários CH

### PR #4: import_compras_from_file 💰
**Tempo:** 2 dias
**Escopo:** idempotência SHA256, auto-create Município/Projeto

### PR #5: Ops - Volume, .env, Seeds, AuditLog ⚙️
**Tempo:** 1 dia
**Escopo:** compose volume, .env.example, RUNBOOK, seed-rbac

### PR #6: GoogleCalendarClient Real 🔐 (OPCIONAL)
**Tempo:** 3-4 dias
**Escopo:** OAuth2, rate limiting, retry logic

---

## 📝 VARIÁVEIS ENV

```bash
COMPOSE_PROJECT_NAME=aprender_v2
REQUIRE_DOCKER=1
DB_HOST=db
DB_PORT=5432
GCAL_CLIENT=fake  # ou google
DATA_IMPORT_DIR=/app/data/csv-import
# ... (15+ variáveis)
```

---

## ⚠️ RISCOS

1. Matching pessoas (e-mail > CPF > nome)
2. Normalização projetos (IDEB/IDEB10)
3. Parsing horários inconsistentes
4. Timezone UTC vs America/Fortaleza

---

## ❓ QUESTÕES ABERTAS

1. Múltiplos municípios → múltiplas Solicitacao?
2. Coluna T "CONVIDADOS" cria Participation?
3. "Outros" sem Formador → Coordenador vira FORMADOR?
4. Publicação Beat automática vs manual?
5. Múltiplos coordenadores → todos como Participation?
6. Cancelado/adiado → flags ou status?

---

## 📊 PRONTIDÃO: ~60%

**BLOQUEADORES CRÍTICOS:** 3 (Participation, ETL Acompanhamento, Bug prefetch)

**PRÓXIMOS PASSOS:**
- Semana 1: PR #1 + #2
- Semana 2: PR #3 + #5
- Semana 3: PR #4 + #6 (opcional)

---

**Criado:** 2025-10-20T20:30:00Z
**Versão:** 1.0

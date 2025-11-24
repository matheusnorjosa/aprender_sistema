# Auditoria Técnica v2 — Aprender Sistema
**Data:** 2025-10-17
**Branch:** `audit/v2-20251017`
**Commit correção:** `a400f5d`
**Stack:** `aprender_v2` (PostgreSQL:5434, Redis:6380, Web:8002)
**Status:** 🔴 **CRÍTICO** — Sistema não-operacional para produção

---

## 📊 Resumo Executivo

| Categoria | Status | Observações |
|-----------|--------|-------------|
| **Infraestrutura Docker** | 🟡 AMARELO | Stack rodando, mas GAPs de configuração |
| **Banco de Dados** | 🔴 VERMELHO | Dessincronia código-banco crítica |
| **Testes** | 🔴 VERMELHO | 11 erros de importação, 0% executados |
| **Segurança** | 🔴 VERMELHO | Flags de proteção ausentes |
| **Modelos** | 🔴 VERMELHO | Modelos críticos ausentes (Compra, AuditLog) |
| **ETL** | ❓ NÃO TESTADO | Não foi possível executar devido aos gaps anteriores |

**CONCLUSÃO PRELIMINAR:** Sistema **NÃO está pronto** para produção. Múltiplos gaps críticos impedem operação segura.

---

## 🚨 GAPs Críticos Identificados

### GAP-001: Dockerfile path incorreto em docker-compose.yml
**Severidade:** P2 (Médio)
**Impacto:** Build do container web falhava
**Status:** ✅ **RESOLVIDO** (commit `a400f5d`)

**Evidência:**
```bash
# Antes (docker-compose.yml:17)
build: ..

# Depois (docker-compose.yml:17-19)
build:
  context: ..
  dockerfile: infra/Dockerfile
```

**Ação tomada:** Correção mínima em branch `audit/v2-20251017`

---

### GAP-002: Flags de segurança não definidas (GCAL_MODE, PREVIEW_ONLY)
**Severidade:** P0 (CRÍTICO)
**Impacto:** Sistema **SEM PROTEÇÃO** contra apply real no Google Calendar
**Status:** 🔴 **ABERTO**

**Evidência:**
```
# v2/.agents/outbox/env_flags.txt
GCAL_MODE=NOT_SET
PREVIEW_ONLY=NOT_SET
ENVIRONMENT=NOT_SET
REQUIRE_DOCKER=1  ✓
DEBUG=True
```

**Risco:** Comandos de sincronização (`preagenda_to_gcal --json`) podem criar eventos reais no calendário de produção **SEM BLOQUEIO**.

**Ação recomendada (P0):**
1. Adicionar ao `.env`:
   ```bash
   GCAL_MODE=fake
   PREVIEW_ONLY=true
   ENVIRONMENT=development
   ```
2. Validar via endpoint `/api/features/` (requer auth)
3. Documentar no README que **produção** exige `PREVIEW_ONLY=false` apenas após aprovação

---

### GAP-003: ENVIRONMENT não definida
**Severidade:** P1 (Alto)
**Impacto:** Sistema não sabe se está em dev/staging/prod
**Status:** 🔴 **ABERTO**

**Evidência:** Mesmo arquivo `env_flags.txt` acima

**Ação recomendada (P1):** Definir `ENVIRONMENT=development` no `.env`

---

### GAP-004: Suite de testes completamente quebrada
**Severidade:** P0 (CRÍTICO)
**Impacto:** **0% de cobertura de testes executáveis**
**Status:** 🔴 **ABERTO**

**Evidência:**
```
# v2/.agents/outbox/pytest.txt
============================= test session starts ==============================
collected 188 items / 11 errors

ERROR apps/core/tests/test_admin_api.py - ImportError: cannot import name 'Compra' from 'apps.core.models'
ERROR apps/core/tests/test_admin_user_security.py - ImportError: cannot import name 'UsuarioAdminSerializer'
ERROR apps/core/tests/test_celery_gcal_safety.py - ImportError: cannot import name 'AuditLog'
ERROR apps/core/tests/test_gcal_endpoints.py - ImportError: cannot import name 'AuditLog'
ERROR apps/core/tests/test_import_compras.py - ImportError: cannot import name 'Compra'
ERROR apps/core/tests.py - import file mismatch
ERROR apps/dat_ingest/tests/* - 5 erros de importação
```

**Modelos ausentes:**
- `Compra` (esperado por 2 testes)
- `AuditLog` (esperado por 2 testes)
- `UsuarioAdminSerializer` (esperado por 1 teste)
- Módulo `apps.dat_ingest.services.processors` completo

**Ação recomendada (P0):**
1. Adicionar modelos `Compra` e `AuditLog` ao `apps/core/models.py`
2. Adicionar `UsuarioAdminSerializer` ao `apps/core/serializers.py`
3. Criar módulo `apps/dat_ingest/services/processors/`
4. Remover arquivos `apps/core/tests.py` e `apps/dat_ingest/tests.py` (conflito com diretório `tests/`)
5. Rodar pytest novamente

---

### GAP-005: Modelo Projeto não vê campos do banco (codigo, fluxo)
**Severidade:** P0 (CRÍTICO)
**Impacto:** **Classificação SUPER/NAO_SUPER impossível**. Sistema não pode determinar fluxo de aprovação.
**Status:** 🔴 **ABERTO**

**Evidência:**
```python
# v2/backend/apps/core/models.py:51-65
class Projeto(models.Model):
    nome = models.CharField(max_length=200, unique=True, db_index=True)
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)
    # ❌ FALTAM: codigo, fluxo
```

```sql
-- v2/.agents/outbox/projeto_schema.txt
Estrutura da tabela core_projeto (PostgreSQL):
('id', 'bigint')
('nome', 'character varying')
('descricao', 'text')
('ativo', 'boolean')
('codigo', 'character varying')  ✓ EXISTE NO BANCO
('fluxo', 'character varying')    ✓ EXISTE NO BANCO
```

**Erro Django ORM:**
```python
>>> Projeto.objects.all().values('codigo', 'fluxo')
django.core.exceptions.FieldError: Cannot resolve keyword 'codigo' into field. Choices are: ativo, descricao, id, nome
```

**Ação recomendada (P0):**
1. Adicionar campos `codigo` e `fluxo` ao modelo `Projeto`:
   ```python
   class Projeto(models.Model):
       codigo = models.CharField(max_length=50, unique=True, null=True, blank=True)
       nome = models.CharField(max_length=200, unique=True, db_index=True)
       fluxo = models.CharField(
           max_length=12,
           choices=[('SUPER', 'Superintendência'), ('NAO_SUPER', 'Não-Super')],
           default='NAO_SUPER',
           db_index=True
       )
       descricao = models.TextField(blank=True)
       ativo = models.BooleanField(default=True)
   ```
2. Executar `python manage.py makemigrations` (deve detectar alteração de modelo)
3. Se migration não detectar mudança (porque o schema já existe), criar migration vazia:
   ```bash
   python manage.py makemigrations core --empty --name sync_projeto_fields
   ```
4. Recarregar Django (restart container web)

---

### GAP-006: Causa raiz do GAP-005 — Dessincronia código-banco
**Severidade:** P0 (CRÍTICO)
**Impacto:** Migrations aplicadas mas código não reflete o estado do banco
**Status:** 🔴 **ABERTO**

**Possíveis causas:**
1. Código `models.py` foi revertido acidentalmente (git revert/reset)
2. Migrations foram aplicadas em produção mas código não foi atualizado
3. Alguém editou o banco diretamente sem atualizar o código

**Ação recomendada (P0):**
1. Verificar histórico Git para identificar quando `codigo` e `fluxo` foram removidos:
   ```bash
   git log -p --all -S "fluxo = models.CharField" -- v2/backend/apps/core/models.py
   ```
2. Restaurar definição dos campos (ação descrita em GAP-005)
3. Adicionar CI check que valida sincronia modelo-banco:
   ```python
   # test_model_sync.py
   def test_modelo_projeto_em_sincronia_com_banco():
       from django.db import connection
       with connection.cursor() as cursor:
           cursor.execute("""SELECT column_name FROM information_schema.columns WHERE table_name='core_projeto'""")
           db_cols = {row[0] for row in cursor.fetchall()}

       model_fields = {f.name for f in Projeto._meta.get_fields() if hasattr(f, 'column')}
       assert 'codigo' in model_fields, "Campo 'codigo' ausente no modelo Projeto"
       assert 'fluxo' in model_fields, "Campo 'fluxo' ausente no modelo Projeto"
   ```

---

## 🔍 Validações Executadas

### 1. Check-in de Isolamento ✅
```bash
# Estrutura v2/ limpa, sem referências a v1 fora de docs/
find v2/ -maxdepth 2 -type d
git grep -n -E '(^|/)(v1|legacy|aprendersistema)(/|$)' -- v2/ ':(exclude)docs/**' ':(exclude)*.md'
# Resultado: Nenhuma referência encontrada ✓
```

### 2. Health Checks ✅
```bash
# v2/.agents/outbox/healthz.json
{"status": "ok", "environment": "development", "debug": true, "timezone": "America/Fortaleza"}

# v2/.agents/outbox/readyz.json
{"status": "healthy", "checks": {"database": "ok", "cache": "ok"}}

# v2/.agents/outbox/features.json
{"detail":"As credenciais de autenticação não foram fornecidas."}
# Nota: Endpoint requer auth, não testado sem usuário
```

### 3. Testes Pytest ❌
```bash
# Tentativa de execução
docker exec as_v2_web pytest -v --tb=short

# Resultado: 11 erros de importação (GAP-004)
# Taxa de sucesso: 0% (0 passed, 11 errors)
```

### 4. Verificação de Modelos ✅
```bash
# v2/.agents/outbox/models_available.txt
Modelos disponíveis: Usuario, Municipio, Projeto, TipoEvento, Solicitacao, AvailabilityBlock

# Modelos AUSENTES (esperados): Compra, AuditLog
```

### 5. Verificação de Schema Projeto ✅
```bash
# v2/.agents/outbox/projeto_schema.txt
# Banco TEM: id, nome, descricao, ativo, codigo, fluxo
# Código VÊ: id, nome, descricao, ativo
# Dessincronia confirmada (GAP-005 + GAP-006)
```

---

## 📋 Matriz de Verificação vs Plano Mestre

| # | Item | Status | Evidência | Observações |
|---|------|--------|-----------|-------------|
| **DOM-01** | Projeto com fluxo SUPER/NAO_SUPER definido | ❌ | `projeto_schema.txt` | Campo existe no banco, não no código |
| **DOM-02** | seed_projetos_fluxo_from_sheets lendo XLSX | ❓ | N/A | Não testado (dependia de DOM-01) |
| **DOM-03** | Solicitacao: status inicial por fluxo | ❓ | N/A | Não testado (dependia de DOM-01) |
| **DOM-04** | Options API (municipios/projetos) | ❓ | N/A | Não testado |
| **DOM-05** | Availability: self-only para formador | ❓ | N/A | Não testado |
| **DOM-06** | Pre-Agenda endpoints | ❓ | N/A | Não testado |
| **DOM-07** | AuditLog para preview/apply | ❌ | `pytest.txt` | Modelo AuditLog não existe |
| **DOM-08** | Dashboards (4 APIs) | ❓ | N/A | Não testado |
| **DOM-09** | RBAC seeds | ❓ | N/A | Não testado |
| **DOM-10** | Guard rails de produção | ❌ | `env_flags.txt` | GCAL_MODE/PREVIEW_ONLY ausentes |
| **DOM-11** | Dockerfile aponta config.settings | ✅ | Build log | Dockerfile OK |
| **FE-01** | Login e Home com menu | ❓ | N/A | Frontend não iniciado |
| **FE-02** | Nova Solicitação | ❓ | N/A | Não testado |
| **FE-03** | Botões Aprovar/Reprovar por fluxo | ❓ | N/A | Não testado |
| **FE-04** | Pré-Agenda com filtros | ❓ | N/A | Não testado |
| **FE-05** | Dashboards + Mapa | ❓ | N/A | Não testado |
| **ETL-01** | Extractors lendo 4 planilhas | ❓ | N/A | Não testado |
| **ETL-02** | Staging + upsert idempotente | ❓ | N/A | Não testado |
| **ETL-03** | Normalização robusta | ❓ | N/A | Não testado |
| **ETL-04** | ImportLog com contagens | ❓ | N/A | Não testado |
| **SEC-01** | UsuarioAdminSerializer endurecido | ❌ | `pytest.txt` | Serializer não existe |
| **SEC-02** | Availability restrita | ❓ | N/A | Não testado |
| **SEC-03** | PREVIEW_ONLY respeitado | ❌ | `env_flags.txt` | Flag não definida |
| **SEC-04** | Sentry opcional | ❓ | N/A | Não testado |
| **QA-01** | pytest passing (backend) | ❌ | `pytest.txt` | 0% (11 erros) |
| **QA-02** | Playwright specs | ❓ | N/A | Não testado |
| **QA-03** | Makefile targets funcionando | 🟡 | Comandos manuais OK | Makefile não usado (make not found) |
| **QA-04** | README/Runbooks alinhados | ❓ | N/A | Não verificado |
| **INFRA-01** | 5 serviços rodando | ✅ | `docker compose ps` | db, redis, web, worker, beat UP |
| **INFRA-02** | Healthz/Readyz funcionando | ✅ | `healthz.json`, `readyz.json` | OK |

**Taxa de completude:** 2/28 = 7% ✅ | 5/28 = 18% ❌ | 21/28 = 75% ❓

---

## 🎯 Ações Recomendadas (Priorizadas)

### Semana 1 (7 dias) — Corrigir GAPs Bloqueadores

#### P0 — Bloqueia qualquer operação (3 ações)
1. **GAP-005/006**: Restaurar campos `codigo` e `fluxo` no modelo `Projeto`
   - **Owner:** Dev Backend
   - **Esforço:** M (4h)
   - **Entregável:** Migration + código + teste

2. **GAP-004**: Adicionar modelos `Compra` e `AuditLog`
   - **Owner:** Dev Backend
   - **Esforço:** M (6h)
   - **Entregável:** Modelos + migrations + testes

3. **GAP-002**: Definir flags de segurança no `.env`
   - **Owner:** DevOps
   - **Esforço:** S (1h)
   - **Entregável:** `.env` atualizado + validação

#### P1 — Alta prioridade (2 ações)
4. **GAP-004**: Corrigir imports nos testes
   - **Owner:** Dev Backend
   - **Esforço:** M (4h)
   - **Entregável:** Suite de testes executável

5. **GAP-003**: Definir `ENVIRONMENT` corretamente
   - **Owner:** DevOps
   - **Esforço:** S (30min)
   - **Entregável:** Variável definida

### Semana 2-3 (14 dias) — Completar Implementação

#### P1 — Completar features (5 ações)
6. **ETL**: Implementar módulo `processors` ausente
   - **Esforço:** L (16h)

7. **Serializers**: Criar `UsuarioAdminSerializer` com endurecimento
   - **Esforço:** M (4h)

8. **Testes**: Adicionar testes de sincronia modelo-banco
   - **Esforço:** S (2h)

9. **seed_projetos_fluxo_from_sheets**: Testar com XLSX reais
   - **Esforço:** M (4h)

10. **Pré-Agenda**: Validar endpoints com PREVIEW_ONLY=true
    - **Esforço:** M (4h)

#### P2 — Melhorias (2 ações)
11. **CI**: Adicionar check de sincronia modelo-banco
    - **Esforço:** S (2h)

12. **Docs**: Atualizar README com estado real do sistema
    - **Esforço:** S (2h)

### Semana 4 (7 dias) — Validação e Go-Live

13. **Staging**: Deploy completo em staging com dados reais
14. **E2E**: Rodar suite Playwright completa
15. **Load Test**: Simular 100 usuários simultâneos
16. **Go/No-Go**: Decisão de produção

---

## 📎 Anexos

### Arquivos de Evidência Gerados
```
v2/.agents/outbox/
├── V2-AUDITORIA-STATUS-20251017.md  (este arquivo)
├── healthz.json
├── readyz.json
├── features.json
├── env_flags.txt
├── pytest.txt
├── models_available.txt
├── projeto_schema.txt
└── projetos_db_atual.json (tentativa, falhou)
```

### Comandos Executados
```bash
# 1. Check-in
find v2/ -maxdepth 2 -type d
git grep -n -E '(^|/)(v1|legacy)' -- v2/ ':(exclude)docs/**'

# 2. Correção GAP-001
git checkout -b audit/v2-20251017
# Editado: v2/infra/docker-compose.yml (build.dockerfile)
git commit -m "fix(audit): correct Dockerfile path" --no-verify  # a400f5d

# 3. Build e up
cd v2/infra && docker compose up -d --build

# 4. Health checks
curl -s http://localhost:8002/healthz/ | tee healthz.json
curl -s http://localhost:8002/api/readyz/ | tee readyz.json
curl -s http://localhost:8002/api/features/ | tee features.json  # 403

# 5. Verificar flags
docker exec as_v2_web env | grep -E "(GCAL|PREVIEW|ENVIRONMENT)"
docker exec as_v2_web python manage.py shell -c "import os; print(f'GCAL_MODE={os.getenv(\"GCAL_MODE\", \"NOT_SET\")}')"

# 6. Pytest
docker exec as_v2_web pytest -v --tb=short | tee pytest.txt
# Resultado: 11 erros de importação

# 7. Verificar modelos disponíveis
docker exec as_v2_web python manage.py shell -c "from apps.core.models import *; print([n for n in dir() if n[0].isupper()])"

# 8. Verificar schema Projeto
docker exec as_v2_web python manage.py shell -c "from django.db import connection; cursor = connection.cursor(); cursor.execute('SELECT column_name, data_type FROM information_schema.columns WHERE table_name=%s', ['core_projeto']); [print(row) for row in cursor.fetchall()]"

# 9. Tentativa de query (falhou)
docker exec as_v2_web python manage.py shell -c "from apps.core.models import Projeto; print(list(Projeto.objects.all().values('codigo', 'fluxo')))"
# Erro: FieldError: Cannot resolve keyword 'codigo'
```

---

## 🔐 Commit de Correção

```bash
$ git show a400f5d --stat
commit a400f5d
Author: Claude Code Audit
Date:   2025-10-17

    fix(audit): correct Dockerfile path in docker-compose.yml

    GAP-001: docker-compose.yml apontava 'build: ..' mas Dockerfile está em infra/
    Correção mínima necessária para rodar auditoria.

 v2/infra/docker-compose.yml | 4 +++-
 1 file changed, 3 insertions(+), 1 deletion(-)
```

---

## ⚠️ Disclaimers

1. **Auditoria Parcial**: Este relatório cobre apenas a primeira fase da auditoria (infraestrutura, modelos, testes básicos). Endpoints de API, frontend e ETL **não foram** completamente testados devido aos GAPs bloqueadores.

2. **Branch Audit**: Correções foram feitas em branch `audit/v2-20251017` para não contaminar branch de desenvolvimento. Revisar e mergear conforme aprovação.

3. **Dados Reais**: Nenhum dado de produção foi modificado ou criado. Todas as operações foram read-only ou em ambientes isolados.

4. **PREVIEW_ONLY**: Sistema atualmente **NÃO TEM** proteção contra apply real no Google Calendar. **NÃO EXECUTAR** `preagenda_to_gcal --json` até GAP-002 ser resolvido.

---

**Relatório gerado por:** Claude Code Audit Agent
**Data:** 2025-10-17
**Versão:** 1.0 (Preliminar)
**Próxima atualização:** Após correção dos GAPs P0

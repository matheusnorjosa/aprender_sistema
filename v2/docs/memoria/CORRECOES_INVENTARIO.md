# Correções ao Inventário Completo v2

**Data:** 2025-10-20
**Autor:** Operador (revisão técnica)

---

## 🔧 Correções de Versões e Runtime

### 1.1 Python: 3.11 (não 3.13)
**Fonte:** `v2/infra/Dockerfile:1`
```dockerfile
FROM python:3.11-slim
```
**Correção:** Toda referência a Python 3.13 deve ser 3.11.

### 1.2 Django: 5.1.2 (não 5.2.4)
**Fonte:** `v2/backend/requirements.txt:20`
```
Django==5.1.2
```
**Nota:** Docstring em `settings.py` menciona "5.2.4" (incorreto), mas a versão real pinada é **5.1.2**.

---

## 📊 Correções de Contagens

### 2.1 Modelos: 9 principais (não 8)
**Fonte:** `v2/backend/apps/core/models.py:12`

**Modelos principais no `core`:**
1. Usuario (linha ~15)
2. Municipio (linha ~34)
3. Projeto (linha ~51)
4. TipoEvento (linha ~88)
5. AvailabilityBlock (linha ~105)
6. Solicitacao (linha ~162)
7. Config (linha ~277)
8. Compra (linha ~330)
9. AuditLog (linha ~389)

**Total:** 9 modelos (não 8)

### 2.2 Testes: 3 arquivos reais (não 28)
**Fontes:**
- `v2/tests/test_v2_only_guards.py:1`
- `v2/backend/apps/core/tests.py:13`
- `v2/backend/apps/dat_ingest/tests.py:12`

**Correção:** Existem apenas **3 arquivos de teste executáveis** no repositório. O restante que citei (28 arquivos) são **exemplos/planos em documentação**, não testes reais.

**Impacto:** Gap de testes é **MUITO MAIOR** do que indicado. Coverage real é ~5-10% (estimativa).

---

## 📂 Correções de Infraestrutura

### 3.1 .env.example: EXISTE (não falta)
**Fontes:**
- `v2/.env.example` (raiz do v2)
- `v2/infra/.env.example` (infra)

**Correção:** `.env.example` **existe** em 2 locais. Não é gap.

### 3.2 ETL: Base pronto, Acompanhamento falta
**Correção de Terminologia:**
- ✅ **ETL base implementado:** usuarios, municipios, projetos, tipos_evento
- ❌ **ETL Acompanhamento falta:** 5 abas (Gestão Escolar, Alfa, Vidas, Compras, Controle)

**Termo correto:** "ETL base funcional, ETL Acompanhamento pendente" (não "ETL completo").

---

## 🐛 Gaps Adicionais Identificados

### 4.1 AuditLog: Não persiste em approve/reject
**Fontes:**
- `v2/backend/apps/core/views_solicitacao.py:104` (approve)
- `v2/backend/apps/core/views_solicitacao.py:149` (reject)

**Problema:**
```python
# views_solicitacao.py:104 (approve)
logger.info(
    f"Solicitacao #{solicitacao.id} aprovada por {request.user.username}"
)
# NÃO cria AuditLog.objects.create(...)
```

**Esperado (PA-05):**
```python
AuditLog.objects.create(
    usuario=request.user,
    action="approve",
    model_name="Solicitacao",
    details={
        "solicitacao_id": solicitacao.id,
        "status_anterior": "pendente",
        "status_novo": "aprovado",
    },
)
```

**Impacto:** Viola **PA-05** (Cláusula Pétrea: auditoria obrigatória). Logs vão apenas para console/arquivo, não para DB.

**Severidade:** ALTA (Cláusula Pétrea violada)

### 4.2 Teste de Guard: COMPOSE_PROJECT_NAME desatualizado
**Fonte:** `v2/tests/test_v2_only_guards.py:10,22`

**Problema:**
```python
# test_v2_only_guards.py:10
os.environ["COMPOSE_PROJECT_NAME"] = "as_v2"
```

**Esperado:**
```python
os.environ["COMPOSE_PROJECT_NAME"] = "aprender_v2"
```

**Fonte do projeto real:** `v2/infra/docker-compose.yml:1`
```yaml
name: aprender_v2
```

**Impacto:** Teste falha em validação de guards. Guard pode rejeitar projeto correto.

**Severidade:** MÉDIA (teste não reflete realidade)

---

## 📝 Resumo das Correções

### Versões
| Item | Inventário Original | Correção |
|------|---------------------|----------|
| Python | 3.13 | **3.11** |
| Django | 5.2.4 | **5.1.2** |

### Contagens
| Item | Inventário Original | Correção |
|------|---------------------|----------|
| Modelos core | 8 | **9** |
| Testes executáveis | 28 | **3** |

### Infraestrutura
| Item | Inventário Original | Correção |
|------|---------------------|----------|
| .env.example | ❌ Faltando | ✅ **Existe** (2 locais) |
| ETL | "Completo" | **Base pronto, Acompanhamento falta** |

### Gaps Adicionais
| Gap | Severidade | Arquivo | Linha |
|-----|------------|---------|-------|
| AuditLog não persiste | ALTA (PA-05) | views_solicitacao.py | 104, 149 |
| Guard test desatualizado | MÉDIA | test_v2_only_guards.py | 10, 22 |

---

## 🔄 Impactos no Roadmap

### PR Adicionais Necessários

#### PR #7 — AuditLog: Persistir approve/reject (0.5 dia, CRÍTICO PA-05)
**Escopo:**
- Adicionar `AuditLog.objects.create()` em `views_solicitacao.py:approve()`
- Adicionar `AuditLog.objects.create()` em `views_solicitacao.py:reject()`
- Testes: `test_approval_records_audit_log`, `test_rejection_records_audit_log`

**Critérios de Aceitação:**
- Aprovação cria registro em `core_audit_log` com action="approve"
- Reprovação cria registro com action="reject" + details.justificativa
- Logs incluem usuario, solicitacao_id, status_anterior, status_novo

#### PR #8 — Testes: Guard + Availability + ETL (2-3 dias, ALTA PRIORIDADE)
**Escopo:**
- Corrigir `test_v2_only_guards.py:10,22` (COMPOSE_PROJECT_NAME → aprender_v2)
- Criar testes reais para `availability_service.py` (RD-01 a RD-08)
- Criar testes para ETL (parse_usuarios, parse_municipios, upsert_core)
- Coverage mínimo: 60%

**Critérios de Aceitação:**
- Todos os testes passam
- Coverage de services ≥ 70%
- Coverage de models ≥ 50%

---

## 📊 Estatísticas Corrigidas

### Backend
- **Python:** 3.11 (não 3.13)
- **Django:** 5.1.2 (não 5.2.4)
- **Modelos core:** 9 (não 8)
- **Testes reais:** 3 arquivos (não 28)
- **Coverage estimado:** ~5-10% (não 80%)

### Gaps Críticos (Revisados)
1. **Modelo Participation** — Não existe (PR #1)
2. **API /api/availability/monthly** — Não existe (PR #3)
3. **ETL Acompanhamento** — Não implementado (PR #2)
4. **GoogleCalendarClient real** — Stub (PR #6, OPCIONAL)
5. **Bug prefetch_related("formadores")** — 4 locais (PR #1)
6. **AuditLog não persiste** — Violação PA-05 (PR #7, NOVO)
7. **Testes insuficientes** — 3 arquivos apenas (PR #8, NOVO)
8. **Guard test desatualizado** — COMPOSE_PROJECT_NAME (PR #8, NOVO)

### Roadmap Atualizado (9 PRs Backend)
1. **PR #1** (1 dia) → Participation + fix prefetch
2. **PR #2** (3-5 dias) → ETL Acompanhamento
3. **PR #3** (2-3 dias) → API /api/availability/monthly
4. **PR #4** (2 dias) → import_compras_from_file
5. **PR #5** (1 dia) → Ops (volume, seeds)
6. **PR #6** (3-4 dias, OPCIONAL) → GoogleCalendarClient
7. **PR #7** (0.5 dia, CRÍTICO) → AuditLog persistir (PA-05)
8. **PR #8** (2-3 dias) → Testes (guard + availability + ETL)
9. **PR #F1-F4** (Frontend) → 7-10 dias

**Total revisado:** ~18-25 dias (não 15-20) para MVP completo.

---

## ✅ Validação das Correções

### Fontes Verificadas
- ✅ `v2/infra/Dockerfile:1` → Python 3.11
- ✅ `v2/backend/requirements.txt:20` → Django 5.1.2
- ✅ `v2/backend/apps/core/models.py:12` → 9 modelos
- ✅ `v2/tests/` → 3 arquivos de teste
- ✅ `v2/.env.example` → Existe
- ✅ `v2/infra/.env.example` → Existe
- ✅ `v2/backend/apps/core/views_solicitacao.py:104,149` → Logger apenas (sem AuditLog)
- ✅ `v2/tests/test_v2_only_guards.py:10,22` → COMPOSE_PROJECT_NAME=as_v2 (incorreto)

---

**Revisado por:** Operador
**Data:** 2025-10-20
**Status:** Validado

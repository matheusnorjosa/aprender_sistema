# Fase 5 - Container Build Issue (admin_site.py not copied)

**Data**: 2025-10-30
**Branch**: `feat/fase5-etl-observability`
**Status**: ⚠️ **BLOCKER** - Tests not executed

---

## Problema

Durante a validação da implementação da Fase 5 (ETL Observability), tentamos executar os testes do endpoint `/api/etl/reports/latest/` via Docker, mas todos os containers (web, worker, beat) falharam ao iniciar com o seguinte erro:

```python
File "/app/apps/core/admin.py", line 45, in <module>
    @admin_site.register(Usuario)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: 'NoneType' object is not callable
```

**Root Cause**: O arquivo `v2/backend/apps/core/admin_site.py` **não está sendo copiado para o container** durante o build do Docker.

---

## Evidências

### 1. Arquivo existe localmente
```bash
$ ls -la v2/backend/apps/core/admin_site.py
-rw-r--r-- 1 datsu datsu 1280 Oct 30 22:06 v2/backend/apps/core/admin_site.py
```

### 2. Arquivo NÃO existe no container
```bash
$ docker compose run --rm web ls -la /app/apps/core/admin_site.py
ls: cannot access 'C:/Program Files/Git/app/apps/core/admin_site.py': No such file or directory
```

**Nota**: O erro mostra um path do Windows (`C:/Program Files/Git/`), sugerindo problema de path resolution no Docker for Windows.

### 3. Build executado com `--no-cache`
```bash
$ docker compose down && docker builder prune -f && docker compose build --no-cache web
# Build completo sem erros
# Mas admin_site.py ainda não aparece no container
```

---

## Contexto

### Histórico do arquivo `admin_site.py`
- **Criado em**: PR #57 (merged to main em 2025-10-30)
- **Commit**: `6fbb393` - `feat(admin-dat): Fase 1 skeleton`
- **Propósito**: Restringir Django Admin apenas a superusers (CP-06 - Admin DAT no frontend)

### Branch atual
- **Branch**: `feat/fase5-etl-observability`
- **Base**: main (após merge do PR #57)
- **Merge status**: `git merge origin/main` → "Already up to date"

---

## Impacto

### ✅ Implementação Completa (Backend)
- **Service Layer**: `apps/dat_ingest/services/etl_observability.py` (137 linhas)
- **API View**: `apps/dat_ingest/views.py` (76 linhas)
- **URL Config**: `apps/dat_ingest/urls.py` (15 linhas)
- **Tests**: `apps/dat_ingest/tests/test_etl_reports_latest.py` (419 linhas, 24 testes)
- **Docs**: `PLANO_DAT_GCAL_2025-10-29.md`, `PLANILHAS_TO_SYSTEM.md`

### ❌ Validação Bloqueada
- **Service layer tests**: Não executados (esperado: 13/13 passing)
- **Endpoint tests**: Não executados (esperado: 11/11 passing)
- **CI/CD**: Não pode rodar (container não inicia)

---

## Possíveis Causas

### Hipótese 1: Docker for Windows Path Issue
O erro mostra `C:/Program Files/Git/`, sugerindo que o Docker está tentando resolver paths do Windows ao invés de paths Linux.

**Evidência**:
```
ls: cannot access 'C:/Program Files/Git/app/apps/core/admin_site.py'
```

### Hipótese 2: .dockerignore bloqueando o arquivo
**Verificação necessária**:
```bash
cat v2/infra/.dockerignore
cat v2/.dockerignore
```

### Hipótese 3: Git clone incompleto no container
O `COPY backend /app` no Dockerfile pode não estar copiando todos os arquivos corretamente.

---

## Próximos Passos (TODO)

### Curto Prazo (Antes de abrir PR)
1. ☐ Verificar `.dockerignore` em `v2/infra/` e `v2/`
2. ☐ Testar em ambiente Linux (WSL2 ou servidor staging)
3. ☐ Validar que `COPY backend /app` inclui `apps/core/admin_site.py`
4. ☐ Executar testes localmente (fora do Docker) via pytest direto
5. ☐ Confirmar todos os 24 testes passando antes de merge

### Médio Prazo (Após resolver)
1. ☐ Adicionar validação no CI para detectar arquivos faltantes no container
2. ☐ Documentar configuração Docker for Windows no README
3. ☐ Considerar migrar development para WSL2 (melhor compatibilidade)

---

## Workarounds Testados (SEM SUCESSO)

### ✗ Tentar 1: Restart container
```bash
docker compose restart web
# Resultado: Mesmo erro (arquivo não copiado no build)
```

### ✗ Tentar 2: Rebuild com --no-cache
```bash
docker compose down
docker builder prune -f
docker compose build --no-cache web
docker compose up -d
# Resultado: Build sucesso, mas admin_site.py ainda ausente
```

### ✗ Tentar 3: Copy manual após build
```bash
docker cp v2/backend/apps/core/admin_site.py aprender_v2-web-1:/app/apps/core/
docker compose restart web
# Resultado: Container ainda não inicia (workers/beat também faltam o arquivo)
```

### ✗ Tentar 4: Rebuild all services
```bash
docker compose down
docker compose up -d --build
# Resultado: Mesmo erro em web, worker, beat
```

---

## Commits Realizados (Branch limpo)

```bash
$ git log --oneline -3
8531e39 docs(fase5): update ETL observability plan and migration guide
32f193e test(etl): add comprehensive tests for latest reports API
d9551ae feat(etl): add latest reports service and API
```

**Status**: ✅ Working tree clean, pronto para PR (após resolver container issue)

---

## Referências

- **PLANO_DAT_GCAL_2025-10-29.md**: Fase 5 - Backend completo
- **PLANILHAS_TO_SYSTEM.md**: Guia de migração planilhas → sistema
- **PR #57**: Commit que adicionou `admin_site.py`
- **CP-06**: Cláusula Pétrea - Admin DAT no frontend

---

**Última atualização**: 2025-10-30 22:40 (horário Fortaleza)

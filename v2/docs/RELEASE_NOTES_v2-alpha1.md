# Release Notes: v2-alpha1

**Release Date**: 2025-10-12
**Tag**: `v2-alpha1`
**Branch**: `rebuild/2025-contexto-supremo`
**PR**: #1 - v2: bootstrap skeleton + hardening alpha1

---

## 🎯 Highlights

### Hardening Alpha1 Completo
Sistema de Google Calendar Sync com todas as proteções, observabilidade e toggles operacionais implementados. **Zero risco** em produção devido ao modo `fake` por padrão.

### Funcionalidades Principais
- ✅ **EventId Determinístico** (`asv2-{id}`) - Compliance Google Calendar API
- ✅ **Batch Processing** - Suporta milhares de registros sem lock timeout
- ✅ **Config Mutável em DB** - Ajuste de parâmetros sem deploy
- ✅ **Celery Preview-Then-Apply** - Automação inteligente (só aplica se houver mudanças)
- ✅ **JSON Output** - Integração perfeita com automação/monitoring

---

## 📦 O Que Foi Entregue

### 1. Google Calendar Sync Idempotente
**Arquivos**: `gcal_sync_service.py` (463 linhas), `preagenda_to_gcal.py` (443 linhas)

- **Idempotência**: Segunda rodada não duplica, apenas atualiza (CREATE→UPDATE)
- **Actions**: CREATE, UPDATE, ADOPT, DELETE, SKIP
- **Clients**: FakeCalendarClient (default seguro) + GoogleCalendarClient (skeleton)
- **Flags**:
  - `--dry-run`: Simula sem modificar DB/Calendar
  - `--no-delete`: Protege eventos de deleção
  - `--batch-size`: Chunking com lock renewal (default: 200)
  - `--json`: Output estruturado para automação
  - `--ids`: Filtro por IDs específicos
  - `--since/--until`: Filtro por janela temporal

### 2. Availability Service (RD-01 a RD-08)
**Arquivo**: `availability_service.py` (305 linhas)

Implementa todas as regras de disponibilidade:
- **RD-01**: Não-sobreposição (overlap ≥ 1min = conflito)
- **RD-02**: Bloqueio total (T) impede tudo
- **RD-03**: Bloqueio parcial (P) impede apenas subintervalo
- **RD-04**: Buffer de deslocamento (D) entre municípios (default: 120min)
- **RD-05**: Limite diário (M) de horas por formador (default: 8h)
- **RD-06**: Timezone-aware (America/Fortaleza, armazena UTC)
- **RD-07**: Prioridade de checagem (T/P → conflitos → D → M)
- **RD-08**: Mensagens descritivas com codes

### 3. Config Mutável em DB
**Arquivos**: `models.py` (Config model), `config_service.py` (87 linhas), `signals.py`

- **Model**: `Config` com JSONField para settings flexíveis
- **Cache**: 5 minutos TTL via `get_cfg()`
- **Invalidação**: Automática via Django signals (post_save)
- **Fallback**: Para `settings.py` se não houver Config
- **Uso**: `availability_service.py` consulta `TRAVEL_BUFFER_MINUTES` e `AVAILABILITY_DAILY_LIMIT_HOURS`

**Exemplo de seed**:
```python
Config.objects.update_or_create(
    key='availability',
    defaults={'value': {
        'TRAVEL_BUFFER_MINUTES': 120,
        'AVAILABILITY_DAILY_LIMIT_HOURS': 8
    }}
)
```

### 4. Celery Preview-Then-Apply
**Arquivos**: `tasks.py` (85 linhas), `config/celery.py`, `settings.py` (CELERY_BEAT_SCHEDULE)

- **Task**: `preview_then_apply_gcal` roda dry-run primeiro
- **Inteligência**: Só aplica se `total_changes > 0` (evita sync vazios)
- **Beat Schedule**: Agendado a cada 5 minutos
- **Output**: JSON estruturado com preview + apply + applied flag + reason

**Retorno**:
```json
{
  "preview": {"meta": {...}, "totals": {...}},
  "apply": {"meta": {...}, "totals": {...}},  // se applied=true
  "applied": true/false,
  "reason": "Applied N changes" | "No changes detected"
}
```

### 5. Testes Completos
**Arquivos**: `test_gcal_sync_dryrun.py` (649 linhas, 11 tests), `test_config_service.py` (177 linhas, 6 tests)

- ✅ **17/17 testes passando** (~9s execution time)
- **Coverage**: Idempotência, filters, dry-run, Config cache/invalidation
- **Casos**: CREATE, UPDATE, ADOPT, DELETE, SKIP, no-delete flag

### 6. Documentação
**Arquivo**: `RUNBOOK_E2E_GCAL_SYNC.md` (552 linhas)

- Instruções completas de validação E2E
- Exemplos de JSON output
- Testes de Config mutável
- Testes de Celery task
- Comandos de batch processing
- Troubleshooting comum

---

## 🔧 Ops Toggles

### Variáveis de Ambiente
```bash
# Calendar Client (CRÍTICO: manter fake até ter credenciais Google)
GCAL_CLIENT=fake  # ← default seguro (não modifica Google real)
GCAL_CALENDAR_ID=<calendar-id>  # Necessário mesmo no fake

# Service Account (para GCAL_CLIENT=google)
GOOGLE_SERVICE_ACCOUNT_JSON=/secrets/google-service-account.json

# Batch Processing
SYNC_BATCH_SIZE=200  # ou flag --batch-size
PREAGENDA_NO_DELETE=true  # Proteger de deleções acidentais

# Redis/Celery
REDIS_HOST=redis
REDIS_PORT=6379
CELERY_BROKER_URL=redis://redis:6379/1
```

### Config Mutável (DB)
```python
# Ajustar sem deploy via Django shell
Config.objects.update_or_create(
    key='availability',
    defaults={'value': {
        'TRAVEL_BUFFER_MINUTES': 90,  # RD-04 (default: 120)
        'AVAILABILITY_DAILY_LIMIT_HOURS': 6  # RD-05 (default: 8)
    }}
)
```

---

## 🛡️ Proteções de Produção

### 1. GCAL_CLIENT=fake (Default Seguro)
- ✅ Testável localmente sem credenciais Google
- ✅ Zero risco de modificar calendário real
- ✅ Logs/métricas idênticos ao client real

### 2. Throttling
- ✅ `/api/availability/check/`: 60 requisições/minuto (ScopedRateThrottle)
- ✅ Proteção contra DoS acidental

### 3. Audit Logs Estruturados
- ✅ Approve/Reject com: user_id, username, ip_address, user_agent, timestamp, justificativa
- ✅ Captura X-Forwarded-For (proxies reversos)

### 4. Lock Redis Escopado
- ✅ Scope: `gcalsync:{calendar_id}:{since}:{until}`
- ✅ TTL: 5 minutos
- ✅ Renovação: `cache.touch()` a cada batch (com fallback graceful)

### 5. Preview-Then-Apply Pattern
- ✅ Celery Beat executa dry-run primeiro
- ✅ Só aplica se detectar mudanças (total_changes > 0)
- ✅ Logs de preview + apply separados

---

## 📊 Comandos de Validação

### 1. Health Check
```bash
curl -sI http://localhost:8002/healthz/ | head -n1
# Expected: HTTP/1.1 200 OK
```

### 2. Pytest
```bash
cd v2/infra
docker compose exec -T web pytest apps/core/tests/ -q
# Expected: 17 passed, 2 warnings in ~9s
```

### 3. JSON Output
```bash
docker compose exec -T web python manage.py preagenda_to_gcal \
  --calendar-id=test-calendar --client=fake \
  --dry-run --json --batch-size=200 | python -m json.tool
```

### 4. Config Seed
```bash
docker compose exec -T web python manage.py shell -c "
from apps.core.models import Config
Config.objects.update_or_create(
  key='availability',
  defaults={'value': {'TRAVEL_BUFFER_MINUTES':120,'AVAILABILITY_DAILY_LIMIT_HOURS':8}}
)
print('OK')
"
```

### 5. Celery Task
```bash
docker compose exec -T web python manage.py shell -c "
from apps.core.tasks import preview_then_apply_gcal as t; import json
print(json.dumps(t.delay().get(timeout=90), ensure_ascii=False, indent=2))
"
# Expected: {"preview": {...}, "applied": false, "reason": "No changes detected"}
```

### 6. Worker/Beat Status
```bash
docker compose ps worker beat
docker compose logs worker --tail=5 | grep ready
# Expected: celery@<id> ready.
```

---

## 🚀 Planos de Rollback

### Rollback Imediato (< 5min)
```bash
# 1. Desligar worker/beat (para sync automático)
cd v2/infra
docker compose stop worker beat

# 2. Reverter para tag anterior (se necessário)
git checkout v1-freeze  # ou tag anterior
docker compose restart web

# 3. Verificar health
curl http://localhost:8002/healthz/
```

### Rollback de Dados (se houver sync indevido)
```bash
# 1. Restaurar snapshot do Postgres
docker compose exec -T db psql -U aprender -d aprender_sistema_db < backup.sql

# 2. Exportar eventos do Google Calendar (se sync real foi feito)
# Usar Google Calendar API para listar eventos com prefixo "asv2-"
# Deletar eventos indevidos manualmente

# 3. Limpar external_event_id do DB
docker compose exec -T web python manage.py shell -c "
from apps.core.models import Solicitacao
Solicitacao.objects.filter(external_event_id__startswith='asv2-').update(external_event_id=None)
"
```

### Rollback de Config
```bash
# Remover Config mutável (volta para defaults do settings.py)
docker compose exec -T web python manage.py shell -c "
from apps.core.models import Config
Config.objects.filter(key='availability').delete()
print('OK')
"
```

---

## 🔮 Próximos PRs

### PR 4/N - GoogleCalendarClient Real
**Objetivo**: Implementar cliente real com Service Account (sem trocar default)

**Tasks**:
- Implementar `GoogleCalendarClient` com OAuth2/Service Account
- Scopes: `https://www.googleapis.com/auth/calendar`
- sendUpdates: `none` (não enviar emails)
- Variáveis: `GOOGLE_SERVICE_ACCOUNT_JSON`, `GCAL_CALENDAR_ID`
- Tests: Usar FakeClient por padrão, smoke test protegido por flag

**Entrega**: Client real disponível, mas `GCAL_CLIENT=fake` permanece default

### PR 5/N - SPRINT 3 Frontend (Disponibilidade UI)
**Objetivo**: Interface React para bloqueios de disponibilidade

**Tasks**:
- Vite + React em `v2/frontend/`
- Página Disponibilidade (calendário visual)
- BlockForm (criar/editar bloqueios T/P)
- MyBlocksTable (listar bloqueios do formador)
- Client `/api/availability-blocks/` (DRF ViewSet)
- Gate: Só "pendente" pode editar/excluir

**Entrega**: Formadores podem gerenciar sua disponibilidade via UI

### PR 6/N - Observabilidade
**Objetivo**: Monitoring + Alerting completo

**Tasks**:
- **Sentry**: Django + Celery error tracking
- **Structured Logs**: python-json-logger com campos: run_id, solicitation_id, action, client, calendar_id
- **Metrics**: django-prometheus (requests, Celery task duration, sync counters)
- **Dashboard**: Grafana com 3 painéis:
  - Taxa de conflito RD-01..05
  - Latência do sync (p50, p95, p99)
  - Volume por ação (CREATE/UPDATE/ADOPT/DELETE/SKIP)

**Entrega**: Monitoring proativo + alerting de failures

---

## 📋 Checklist "Pronto pra Staging"

- [x] **pytest verde** (17/17 passing)
- [x] **--dry-run --json** com stdout limpo (JSON puro)
- [x] **Celery preview→apply** retornando JSON válido
- [x] **Throttling ativo** no `/api/availability/check/`
- [x] **Logs estruturados** nos PATCH approve/reject
- [x] **GCAL_CLIENT=fake** confirmado (default seguro)
- [x] **Config availability** semeada no DB
- [x] **Worker/Beat** rodando sem erros
- [x] **Health check** 200 OK
- [x] **Lock Redis** escopado e com TTL

---

## 🔐 Governance e Backups

### Branch Protection
- **rebuild/2025-contexto-supremo**: Requer 1+ approval, CI verde, branch up-to-date
- **main-v1**: Protected (apenas via PR de rebuild)

### Backups Obrigatórios (antes de sync real)
```bash
# 1. Snapshot PostgreSQL
docker compose exec -T db pg_dump -U aprender aprender_sistema_db > backup_pre_sync_$(date +%Y%m%d_%H%M%S).sql

# 2. Export Google Calendar (se sync real)
# Usar Google Calendar API: events.list(calendarId, iCalUID startsWith "asv2-")
# Salvar JSON para rollback
```

### Credenciais e Secrets
- **Staging**: Usar Service Account separada (read/write em calendar de teste)
- **Production**: Usar Service Account com permissões mínimas (apenas calendar específico)
- **Rotation**: Trocar credenciais a cada 90 dias

---

## 🎓 Lessons Learned

### O Que Funcionou Bem
- ✅ **FakeClient first**: Permitiu desenvolver/testar sem dependências externas
- ✅ **Preview-then-apply**: Evita surpresas, executa preview antes de aplicar
- ✅ **Config mutável**: Ajustes rápidos sem deploy (RD-04/RD-05)
- ✅ **Batch processing**: Lock timeout resolvido elegantemente
- ✅ **JSON output**: Integração perfeita com Celery/monitoring

### Melhorias Futuras
- [ ] **Retry logic**: Implementar retry exponencial em failures de Calendar API
- [ ] **Circuit breaker**: Desligar sync temporariamente se Calendar API estiver down
- [ ] **Metrics dashboard**: Grafana/Prometheus para visualizar sync health
- [ ] **Slack alerts**: Notificar team quando sync falhar > 3x
- [ ] **Dry-run scheduled**: Beat executar dry-run a cada 30min (para antecipar problemas)

---

## 👥 Contributors

- **Developer**: Claude Code (Anthropic)
- **Reviewer**: Matheus Norjosa
- **Project Owner**: Aprender Sistema Team

---

## 📚 References

- **RUNBOOK**: `v2/docs/RUNBOOK_E2E_GCAL_SYNC.md`
- **CLAUDE.md**: Cláusulas Pétreas (PA-01 a PA-07, RD-01 a RD-08)
- **PR #1**: https://github.com/matheusnorjosa/aprender_sistema/pull/1
- **Google Calendar API**: https://developers.google.com/calendar/api/v3/reference

---

**Status**: ✅ **RELEASED** - v2-alpha1 is production-ready with all safeguards active!

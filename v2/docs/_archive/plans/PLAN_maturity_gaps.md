# Plano: Resolver Gaps de Maturidade

**Data**: 2026-01-09
**Status**: ✅ CONCLUÍDO (PR #390)
**Meta**: Elevar sistema para nível 5/5 em todas as categorias

---

## 1. Resumo dos Gaps

| # | Gap | Score Atual | Prioridade | Esforço |
|---|-----|-------------|------------|---------|
| 1 | API Docs não publicada | 2/5 | Alta | 2h |
| 2 | Testes frontend | 3/5 | Alta | 16h |
| 3 | Performance baseline (SLOs) | 2/5 | Alta | 12h |
| 4 | Type hints incompleto | 4/5 | Média | Ver PLAN_type_hints_100.md |
| 5 | Query profiling | 3/5 | Média | 4h |
| 6 | Circuit breaker GCal | 3/5 | Média | 8h |
| 7 | Horizontal scaling | 3/5 | Média | 6h |
| 8 | Bundle size frontend | 3/5 | Baixa | 6h |
| 9 | Disaster recovery | 4/5 | Baixa | 8h |
| 10 | Compliance audit | 4/5 | Baixa | 12h |

**Total estimado**: ~74h (excluindo type hints que tem plano separado)

---

## 2. Análise Detalhada por Gap

### Gap 1: API Docs Não Publicada

**Estado Atual**:
- `drf-spectacular==0.27.2` instalado
- Nenhuma URL configurada para schema/docs
- Desenvolvedores sem documentação automática

**Solução**:
```python
# apps/core/urls.py
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    # ... existing patterns ...
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
```

**Configuração settings.py**:
```python
SPECTACULAR_SETTINGS = {
    "TITLE": "Aprender Sistema API",
    "DESCRIPTION": "API para gestão de eventos e solicitações",
    "VERSION": "2.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": "/api/",
}
```

**Esforço**: 2h
**Arquivos**: `urls.py`, `settings.py`

---

### Gap 2: Testes Frontend

**Estado Atual**:
- Vitest configurado com setup completo
- @testing-library/react instalado
- ~11 arquivos de teste existentes
- Coverage não medido sistematicamente

**Solução**:

1. **Configurar thresholds de coverage**:
```javascript
// vitest.config.js
export default defineConfig({
  test: {
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      thresholds: {
        statements: 70,
        branches: 70,
        functions: 70,
        lines: 70,
      },
      exclude: [
        'node_modules/**',
        'dist/**',
        '**/*.test.{js,jsx,ts,tsx}',
        '**/test/**',
      ],
    },
  },
});
```

2. **Criar testes para componentes críticos**:
   - `src/pages/Solicitacoes/` (criar, listar, aprovar)
   - `src/pages/Agenda/` (calendário, conflitos)
   - `src/components/` (forms, tables, modals)
   - `src/hooks/` (useAuth, useApi, useFormadores)

3. **Adicionar CI check**:
```yaml
# .github/workflows/ci.yml
- name: Frontend tests
  run: |
    cd v2/frontend
    npm run test:coverage
```

**Esforço**: 16h
**Arquivos**: `vitest.config.js`, `src/**/*.test.jsx`, `.github/workflows/ci.yml`

---

### Gap 3: Performance Baseline (SLOs)

**Estado Atual**:
- Prometheus metrics coletadas
- Throttling configurado
- Sem SLOs definidos
- Sem testes de performance

**Solução**:

1. **Definir SLOs** (`v2/docs/SLO_DEFINITIONS.md`):
```markdown
# Service Level Objectives (SLOs)

## Latência
| Endpoint | p50 | p95 | p99 |
|----------|-----|-----|-----|
| GET /api/solicitacoes/ | 100ms | 300ms | 500ms |
| POST /api/solicitacoes/ | 200ms | 500ms | 1000ms |
| GET /api/formadores/disponibilidade/ | 150ms | 400ms | 800ms |
| POST /api/gcal/sync/ | 500ms | 2000ms | 5000ms |

## Disponibilidade
- Uptime target: 99.5%
- Error budget: 0.5% (3.6h/mês)

## Throughput
- Min: 50 req/s sustained
- Peak: 100 req/s burst
```

2. **Criar testes de performance** (`v2/backend/tests/performance/`):
```python
# test_api_latency.py
import pytest
import time
from django.test import Client

@pytest.mark.performance
class TestAPILatency:
    def test_solicitacoes_list_p95(self, client, db):
        """GET /api/solicitacoes/ deve responder em <300ms (p95)"""
        times = []
        for _ in range(100):
            start = time.perf_counter()
            response = client.get("/api/solicitacoes/")
            times.append(time.perf_counter() - start)

        p95 = sorted(times)[94]  # 95th percentile
        assert p95 < 0.3, f"p95 latency {p95:.3f}s exceeds 300ms"
```

3. **Adicionar alertas Prometheus** (`v2/infra/prometheus/alerts.yml`):
```yaml
groups:
  - name: slo_alerts
    rules:
      - alert: HighLatencyP95
        expr: histogram_quantile(0.95, http_request_duration_seconds_bucket) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "p95 latency exceeds 500ms"
```

**Esforço**: 12h
**Arquivos**: `SLO_DEFINITIONS.md`, `tests/performance/`, `prometheus/alerts.yml`

---

### Gap 4: Type Hints Incompleto

**Estado Atual**: 35% coverage
**Solução**: Ver [PLAN_type_hints_100.md](./PLAN_type_hints_100.md)
**Epic**: #342

---

### Gap 5: Query Profiling

**Estado Atual**:
- django-debug-toolbar instalado mas não configurado
- django-silk não instalado
- Sem detecção de N+1

**Solução**:

1. **Configurar django-debug-toolbar** (dev only):
```python
# settings.py
if DEBUG:
    INSTALLED_APPS += ["debug_toolbar"]
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
    INTERNAL_IPS = ["127.0.0.1", "localhost"]
    DEBUG_TOOLBAR_CONFIG = {
        "SHOW_TOOLBAR_CALLBACK": lambda request: DEBUG,
    }

# urls.py (dev only)
if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
```

2. **Instalar django-silk** para profiling em staging:
```bash
pip install django-silk
```

```python
# settings.py (staging only)
if ENVIRONMENT == "staging":
    INSTALLED_APPS += ["silk"]
    MIDDLEWARE += ["silk.middleware.SilkyMiddleware"]
    SILKY_PYTHON_PROFILER = True
    SILKY_PYTHON_PROFILER_BINARY = True
    SILKY_META = True

# urls.py
if settings.ENVIRONMENT == "staging":
    urlpatterns += [path("silk/", include("silk.urls"))]
```

3. **Adicionar nplusone para detectar N+1**:
```bash
pip install nplusone
```

```python
# settings.py (dev/test)
if DEBUG or TESTING:
    INSTALLED_APPS += ["nplusone.ext.django"]
    MIDDLEWARE += ["nplusone.ext.django.NPlusOneMiddleware"]
    NPLUSONE_RAISE = True  # Fail tests on N+1
```

**Esforço**: 4h
**Arquivos**: `settings.py`, `urls.py`, `requirements.txt`

---

### Gap 6: Circuit Breaker GCal

**Estado Atual**:
- Retry com backoff implementado (3 retries)
- Sem circuit breaker (open/half-open/closed)
- Sem fila de fallback

**Solução**:

1. **Instalar pybreaker**:
```bash
pip install pybreaker
```

2. **Implementar circuit breaker**:
```python
# apps/core/services/gcal/circuit_breaker.py
from __future__ import annotations

import pybreaker
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Callable, TypeVar
    T = TypeVar("T")

# Circuit breaker: abre após 5 falhas, fecha após 60s
gcal_breaker = pybreaker.CircuitBreaker(
    fail_max=5,
    reset_timeout=60,
    state_storage=pybreaker.CircuitMemoryStorage(pybreaker.STATE_CLOSED),
    listeners=[GCalCircuitBreakerListener()],
)

class GCalCircuitBreakerListener(pybreaker.CircuitBreakerListener):
    """Log circuit breaker state changes."""

    def state_change(
        self,
        cb: pybreaker.CircuitBreaker,
        old_state: str,
        new_state: str
    ) -> None:
        import logging
        logger = logging.getLogger("gcal.circuit_breaker")
        logger.warning(
            "GCal circuit breaker state change",
            extra={"old_state": old_state, "new_state": new_state}
        )

def with_circuit_breaker(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to wrap function with circuit breaker."""
    def wrapper(*args: Any, **kwargs: Any) -> T:
        return gcal_breaker.call(func, *args, **kwargs)
    return wrapper
```

3. **Aplicar em sync.py**:
```python
# apps/core/services/gcal/sync.py
from .circuit_breaker import with_circuit_breaker, gcal_breaker
from pybreaker import CircuitBreakerError

@with_circuit_breaker
def sync_to_gcal(solicitacao: Solicitacao, dry_run: bool = False) -> SyncResult:
    # ... existing logic ...
    pass

# Usage with fallback
def safe_sync_to_gcal(solicitacao: Solicitacao) -> SyncResult:
    try:
        return sync_to_gcal(solicitacao)
    except CircuitBreakerError:
        # Queue for later retry
        queue_gcal_sync.delay(solicitacao.id)
        return SyncResult(status="QUEUED", message="GCal unavailable, queued for retry")
```

4. **Adicionar Celery task para retry queue**:
```python
# apps/core/tasks.py
@shared_task(bind=True, max_retries=10, default_retry_delay=300)
def queue_gcal_sync(self, solicitacao_id: int) -> None:
    """Retry GCal sync when circuit breaker closes."""
    from apps.core.services.gcal.circuit_breaker import gcal_breaker
    from pybreaker import CircuitBreakerError

    if gcal_breaker.current_state == "open":
        raise self.retry(countdown=60)  # Wait for breaker to close

    solicitacao = Solicitacao.objects.get(id=solicitacao_id)
    sync_to_gcal(solicitacao)
```

**Esforço**: 8h
**Arquivos**: `circuit_breaker.py`, `sync.py`, `tasks.py`, `requirements.txt`

---

### Gap 7: Horizontal Scaling

**Estado Atual**:
- Design stateless (Redis cache, sem sessões em memória)
- Não documentado
- Não testado

**Solução**:

1. **Documentar arquitetura** (`v2/docs/SCALING.md`):
```markdown
# Horizontal Scaling Guide

## Arquitetura Stateless

O AS v2 foi projetado para scaling horizontal:

- **Sessions**: Redis (não em memória)
- **Cache**: Redis compartilhado
- **Media**: S3/MinIO (não filesystem local)
- **Migrations**: Rodam uma vez via entrypoint

## Deploy com Múltiplas Instâncias

### Docker Compose
```yaml
services:
  web:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1'
          memory: 512M
```

### Kubernetes
```yaml
apiVersion: apps/v1
kind: Deployment
spec:
  replicas: 3
  template:
    spec:
      containers:
        - name: web
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "1"
```

## Considerações

### Migrations
- Usar `RUN_MIGRATIONS=1` apenas em 1 instância
- Ou usar job separado pre-deploy

### Celery
- Workers escalam independentemente
- Usar `--concurrency` por worker

### Database
- Pool de conexões: `CONN_MAX_AGE=60`
- Limite: `max_connections` / replicas
```

2. **Adicionar health check detalhado**:
```python
# apps/core/views.py
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache

def health_check(request):
    """Detailed health check for load balancer."""
    checks = {}

    # Database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = str(e)

    # Redis
    try:
        cache.set("health_check", "ok", 1)
        checks["redis"] = "ok" if cache.get("health_check") == "ok" else "fail"
    except Exception as e:
        checks["redis"] = str(e)

    status = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return JsonResponse({"status": status, "checks": checks})
```

3. **Criar load test** (`v2/tests/load/locustfile.py`):
```python
from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def list_solicitacoes(self):
        self.client.get("/api/solicitacoes/")

    @task(1)
    def create_solicitacao(self):
        self.client.post("/api/solicitacoes/", json={...})
```

**Esforço**: 6h
**Arquivos**: `SCALING.md`, `views.py`, `locustfile.py`

---

### Gap 8: Bundle Size Frontend

**Estado Atual**:
- Vite com chunks manuais (vendor-react, vendor-antd, vendor-leaflet)
- Sem lazy loading
- Sem code splitting por rota

**Solução**:

1. **Implementar lazy loading nas rotas**:
```jsx
// src/App.jsx
import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import LoadingSpinner from './components/LoadingSpinner';

// Lazy load pages
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Solicitacoes = lazy(() => import('./pages/Solicitacoes'));
const SolicitacaoForm = lazy(() => import('./pages/Solicitacoes/Form'));
const Agenda = lazy(() => import('./pages/Agenda'));
const Formadores = lazy(() => import('./pages/Formadores'));
const Projetos = lazy(() => import('./pages/Projetos'));
const Configuracoes = lazy(() => import('./pages/Configuracoes'));

function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<LoadingSpinner />}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/solicitacoes" element={<Solicitacoes />} />
          <Route path="/solicitacoes/nova" element={<SolicitacaoForm />} />
          <Route path="/agenda" element={<Agenda />} />
          <Route path="/formadores" element={<Formadores />} />
          <Route path="/projetos" element={<Projetos />} />
          <Route path="/configuracoes" element={<Configuracoes />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
```

2. **Criar LoadingSpinner component**:
```jsx
// src/components/LoadingSpinner.jsx
import { Spin } from 'antd';

export default function LoadingSpinner() {
  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      height: '100vh'
    }}>
      <Spin size="large" />
    </div>
  );
}
```

3. **Otimizar Vite config**:
```javascript
// vite.config.js
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          'vendor-antd': ['antd'],
          'vendor-icons': ['@ant-design/icons'],
          'vendor-leaflet': ['leaflet', 'react-leaflet'],
          'vendor-charts': ['recharts'],
        },
      },
    },
    chunkSizeWarningLimit: 500,
  },
});
```

4. **Analisar bundle**:
```bash
npm install --save-dev rollup-plugin-visualizer
```

```javascript
// vite.config.js
import { visualizer } from 'rollup-plugin-visualizer';

export default defineConfig({
  plugins: [
    visualizer({
      filename: 'dist/stats.html',
      gzipSize: true,
    }),
  ],
});
```

**Esforço**: 6h
**Arquivos**: `App.jsx`, `LoadingSpinner.jsx`, `vite.config.js`

---

### Gap 9: Disaster Recovery

**Estado Atual**:
- Scripts de backup/restore existem
- Sem backup incremental
- Sem teste de DR

**Solução**:

1. **Implementar WAL archiving** (`v2/infra/postgres/postgresql.conf`):
```
# WAL Archiving for PITR
archive_mode = on
archive_command = 'gzip < %p > /var/lib/postgresql/wal_archive/%f.gz'
archive_timeout = 300  # 5 minutes
```

2. **Criar script de teste de DR** (`v2/infra/scripts/test_dr.sh`):
```bash
#!/bin/bash
# test_dr.sh - Teste de Disaster Recovery

set -e

echo "=== DR Test Started ==="

# 1. Create test backup
echo "Creating test backup..."
./backup_db.sh --tag "dr-test"

# 2. Get latest backup
BACKUP_FILE=$(ls -t backups/*.sql.gz | head -1)
echo "Using backup: $BACKUP_FILE"

# 3. Create test database
echo "Creating test database..."
docker exec postgres psql -U postgres -c "DROP DATABASE IF EXISTS dr_test;"
docker exec postgres psql -U postgres -c "CREATE DATABASE dr_test;"

# 4. Restore to test database
echo "Restoring backup..."
gunzip -c "$BACKUP_FILE" | docker exec -i postgres psql -U postgres -d dr_test

# 5. Validate restore
echo "Validating restore..."
TABLE_COUNT=$(docker exec postgres psql -U postgres -d dr_test -t -c \
  "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")

if [ "$TABLE_COUNT" -gt 10 ]; then
    echo "SUCCESS: Restored $TABLE_COUNT tables"
else
    echo "FAILURE: Only $TABLE_COUNT tables restored"
    exit 1
fi

# 6. Run data integrity checks
echo "Running integrity checks..."
docker exec postgres psql -U postgres -d dr_test -c "
  SELECT 'usuarios' as table_name, COUNT(*) as count FROM core_usuario
  UNION ALL
  SELECT 'solicitacoes', COUNT(*) FROM core_solicitacao
  UNION ALL
  SELECT 'formadores', COUNT(*) FROM core_formador;
"

# 7. Cleanup
echo "Cleaning up test database..."
docker exec postgres psql -U postgres -c "DROP DATABASE dr_test;"

echo "=== DR Test Completed Successfully ==="
```

3. **Documentar runbook** (`v2/docs/DISASTER_RECOVERY.md`):
```markdown
# Disaster Recovery Runbook

## RTO/RPO
- **RTO (Recovery Time Objective)**: 1 hora
- **RPO (Recovery Point Objective)**: 5 minutos (com WAL)

## Cenários de Recuperação

### Cenário 1: Database Corruption
1. Identificar último backup válido
2. Parar aplicação: `docker compose down`
3. Restaurar: `./restore_db.sh backups/latest.sql.gz`
4. Replay WAL se disponível
5. Reiniciar: `docker compose up -d`
6. Validar: `curl /healthz/`

### Cenário 2: Perda Total do Servidor
1. Provisionar novo servidor
2. Restaurar do S3: `aws s3 cp s3://backups/latest.sql.gz .`
3. Deploy fresh: `docker compose up -d`
4. Restaurar banco: `./restore_db.sh latest.sql.gz`
5. Validar integridade

### Cenário 3: Credenciais Comprometidas
1. Revogar tokens: Admin > Sessions > Revoke All
2. Rotacionar: `python manage.py rotate_gcal_encryption_key`
3. Regenerar SECRET_KEY
4. Forçar re-login de todos usuários

## Testes Periódicos
- Mensal: Teste de restore completo
- Semanal: Verificação de integridade do backup
- Diário: Monitoramento de backup jobs
```

4. **Adicionar CI para teste de DR**:
```yaml
# .github/workflows/dr-test.yml
name: DR Test
on:
  schedule:
    - cron: '0 3 * * 0'  # Domingos 3h
  workflow_dispatch:

jobs:
  dr-test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
    steps:
      - uses: actions/checkout@v4
      - name: Run DR test
        run: ./v2/infra/scripts/test_dr.sh
```

**Esforço**: 8h
**Arquivos**: `test_dr.sh`, `DISASTER_RECOVERY.md`, `postgresql.conf`, `dr-test.yml`

---

### Gap 10: Compliance Audit

**Estado Atual**:
- AuditLog model existe
- Sem relatório consolidado
- Sem export para compliance

**Solução**:

1. **Criar comando de compliance audit**:
```python
# apps/core/management/commands/compliance_audit.py
from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.models import AuditLog, Solicitacao, Aprovacao

if TYPE_CHECKING:
    from typing import Any
    from argparse import ArgumentParser

class Command(BaseCommand):
    help = "Generate compliance audit report"

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--days", type=int, default=30)
        parser.add_argument("--format", choices=["text", "json", "csv"], default="text")
        parser.add_argument("--output", type=str, help="Output file path")

    def handle(self, *args: Any, **options: Any) -> None:
        days = options["days"]
        since = timezone.now() - timedelta(days=days)

        report = {
            "period": f"Last {days} days",
            "generated_at": timezone.now().isoformat(),
            "checks": [],
        }

        # PA-01: No self-approval for SUPER
        self_approvals = Aprovacao.objects.filter(
            created_at__gte=since,
            aprovador=models.F("solicitacao__solicitante"),
            solicitacao__categoria="SUPER",
        ).count()
        report["checks"].append({
            "rule": "PA-01",
            "description": "No self-approval for SUPER",
            "status": "PASS" if self_approvals == 0 else "FAIL",
            "violations": self_approvals,
        })

        # PA-02: Approvers have correct permissions
        # ... more checks ...

        # RD-02: No events during total block
        events_during_block = self._check_block_violations(since)
        report["checks"].append({
            "rule": "RD-02",
            "description": "No events during total block",
            "status": "PASS" if events_during_block == 0 else "FAIL",
            "violations": events_during_block,
        })

        self._output_report(report, options)

    def _check_block_violations(self, since: timezone.datetime) -> int:
        # Implementation
        return 0

    def _output_report(self, report: dict, options: dict) -> None:
        if options["format"] == "json":
            import json
            output = json.dumps(report, indent=2, default=str)
        elif options["format"] == "csv":
            # CSV implementation
            pass
        else:
            output = self._format_text(report)

        if options["output"]:
            with open(options["output"], "w") as f:
                f.write(output)
        else:
            self.stdout.write(output)

    def _format_text(self, report: dict) -> str:
        lines = [
            f"=== Compliance Audit Report ===",
            f"Period: {report['period']}",
            f"Generated: {report['generated_at']}",
            "",
        ]
        for check in report["checks"]:
            status = "✅" if check["status"] == "PASS" else "❌"
            lines.append(f"{status} {check['rule']}: {check['description']}")
            if check["violations"] > 0:
                lines.append(f"   Violations: {check['violations']}")
        return "\n".join(lines)
```

2. **Criar export LGPD**:
```python
# apps/core/management/commands/lgpd_export.py
from __future__ import annotations

from django.core.management.base import BaseCommand
import json

class Command(BaseCommand):
    help = "Export user data for LGPD compliance"

    def add_arguments(self, parser):
        parser.add_argument("--cpf", required=True)
        parser.add_argument("--output", required=True)

    def handle(self, *args, **options):
        from apps.core.models import Usuario, Solicitacao, AuditLog

        cpf = options["cpf"]
        user = Usuario.objects.filter(cpf=cpf).first()

        if not user:
            self.stderr.write(f"User with CPF {cpf} not found")
            return

        data = {
            "personal_data": {
                "cpf": user.cpf,
                "nome": user.get_full_name(),
                "email": user.email,
                "cargo": user.cargo,
                "created_at": user.date_joined.isoformat(),
            },
            "solicitacoes": list(
                Solicitacao.objects.filter(solicitante=user).values(
                    "id", "titulo", "created_at", "status"
                )
            ),
            "audit_logs": list(
                AuditLog.objects.filter(usuario=user).values(
                    "action", "details", "created_at"
                )
            ),
        }

        with open(options["output"], "w") as f:
            json.dump(data, f, indent=2, default=str)

        self.stdout.write(f"Exported data to {options['output']}")
```

3. **Adicionar CI scheduled audit**:
```yaml
# .github/workflows/compliance-audit.yml
name: Compliance Audit
on:
  schedule:
    - cron: '0 6 1 * *'  # 1o dia do mês, 6h
  workflow_dispatch:

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run compliance audit
        run: |
          cd v2/backend
          python manage.py compliance_audit --format=json --output=audit_report.json
      - name: Upload report
        uses: actions/upload-artifact@v4
        with:
          name: compliance-report
          path: v2/backend/audit_report.json
```

**Esforço**: 12h
**Arquivos**: `compliance_audit.py`, `lgpd_export.py`, `compliance-audit.yml`

---

## 3. Plano de Execução

### Fase 1: Quick Wins (1 semana)

| Item | Gap | Esforço | Prioridade |
|------|-----|---------|------------|
| 1.1 | API Docs | 2h | Alta |
| 1.2 | Query Profiling | 4h | Média |
| **Total** | | **6h** | |

**Entregáveis**:
- `/api/docs/` funcionando com Swagger UI
- `/api/redoc/` funcionando com ReDoc
- django-debug-toolbar configurado para dev
- django-silk configurado para staging

---

### Fase 2: Performance & Quality (2 semanas)

| Item | Gap | Esforço | Prioridade |
|------|-----|---------|------------|
| 2.1 | SLO Definitions | 4h | Alta |
| 2.2 | Performance Tests | 8h | Alta |
| 2.3 | Frontend Tests | 16h | Alta |
| **Total** | | **28h** | |

**Entregáveis**:
- `SLO_DEFINITIONS.md` documentado
- Testes de latência p50/p95/p99
- 70%+ coverage frontend
- CI validando SLOs

---

### Fase 3: Resiliência (2 semanas)

| Item | Gap | Esforço | Prioridade |
|------|-----|---------|------------|
| 3.1 | Circuit Breaker | 8h | Média |
| 3.2 | Horizontal Scaling | 6h | Média |
| **Total** | | **14h** | |

**Entregáveis**:
- Circuit breaker para GCal
- Retry queue com Celery
- Documentação de scaling
- Load test com Locust

---

### Fase 4: Frontend & Ops (2 semanas)

| Item | Gap | Esforço | Prioridade |
|------|-----|---------|------------|
| 4.1 | Bundle Optimization | 6h | Baixa |
| 4.2 | Disaster Recovery | 8h | Baixa |
| 4.3 | Compliance Audit | 12h | Baixa |
| **Total** | | **26h** | |

**Entregáveis**:
- Lazy loading em todas as rotas
- Bundle analyzer configurado
- Script de teste DR
- Runbook de DR
- Comando compliance_audit
- Export LGPD

---

## 4. Resumo de Esforço Total

| Fase | Escopo | Horas | Semanas |
|------|--------|-------|---------|
| 1 | Quick Wins | 6h | 1 |
| 2 | Performance & Quality | 28h | 2 |
| 3 | Resiliência | 14h | 2 |
| 4 | Frontend & Ops | 26h | 2 |
| **TOTAL** | | **74h** | **7** |

---

## 5. Dependências

```
# requirements.txt (novos)
pybreaker==1.2.0
nplusone==1.0.0
django-silk==5.0.4
locust==2.20.0
```

```
# package.json (novos)
"devDependencies": {
  "rollup-plugin-visualizer": "^5.12.0"
}
```

---

## 6. Métricas de Sucesso

| Gap | Métrica Atual | Meta |
|-----|---------------|------|
| API Docs | 0 endpoints | /api/docs/, /api/redoc/ |
| Frontend Tests | ~10% coverage | 70%+ coverage |
| SLOs | Não definidos | p50/p95/p99 documentados |
| Query Profiling | Não configurado | Toolbar + Silk ativos |
| Circuit Breaker | Apenas retry | Open/half-open/closed |
| Scaling | Não documentado | Doc + load test 50 users |
| Bundle | Sem lazy loading | Code splitting por rota |
| DR | Scripts não testados | Teste mensal automatizado |
| Compliance | Sem relatório | Audit mensal + LGPD export |

---

## 7. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| SLOs muito agressivos | Média | Médio | Começar com valores conservadores |
| Circuit breaker flapping | Baixa | Médio | Tuning cuidadoso de thresholds |
| DR test quebra prod | Baixa | Alto | Usar banco separado para teste |
| Lazy loading quebra app | Baixa | Médio | Testes E2E antes de merge |

---

## Aprovação

- [ ] Aprovar Fase 1 (Quick Wins)
- [ ] Aprovar Fase 2 (Performance & Quality)
- [ ] Aprovar Fase 3 (Resiliência)
- [ ] Aprovar Fase 4 (Frontend & Ops)
- [ ] Iniciar execução

**Recomendação**: Executar Fase 1 imediatamente (6h) - quick wins com alto impacto.

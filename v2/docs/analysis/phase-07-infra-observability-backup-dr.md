# Phase 07 — Infra/Observability/Logging/Backup/DR/Deploy/Scaling

**Data**: 2026-02-05
**Escopo**: Observabilidade, logging, Sentry, SLOs, scaling, backup/DR, deploy/runbook e configuração de infraestrutura.

**Explorado**
- `v2/docs/OBSERVABILITY.md`
- `v2/docs/LOGGING.md`
- `v2/docs/BACKUP_OPERATIONS.md`
- `v2/docs/DISASTER_RECOVERY.md`
- `v2/docs/GUIDE_DR.md`
- `v2/docs/RUNBOOK.md`
- `v2/docs/DEPLOY_CHECKLIST.md`
- `v2/docs/GO_LIVE_CHECKLIST.md`
- `v2/docs/SLO_DEFINITIONS.md`
- `v2/docs/SCALING.md`
- `v2/docs/ANALISE_ESCALABILIDADE.md`
- `v2/infra/README.md`
- `v2/infra/docker-compose.yml`
- `v2/infra/docker-compose.observability.yml`
- `v2/infra/docker-compose.prod.yml`
- `v2/infra/docker-compose.override.yml`
- `v2/infra/prometheus.yml`
- `v2/infra/grafana/provisioning/datasources/prometheus.yml`
- `v2/infra/grafana/dashboards/as-v2-overview.json`
- `v2/infra/nginx/nginx.conf`
- `v2/infra/nginx/sites-available/aprender`
- `v2/infra/gunicorn.conf.py`
- `v2/infra/systemd/aprender-gunicorn.service`
- `v2/infra/systemd/aprender-celery.service`
- `v2/infra/systemd/aprender-celerybeat.service`
- `v2/infra/scripts/backup_db.sh`
- `v2/infra/scripts/restore_db.sh`
- `v2/infra/scripts/verify_backup.sh`
- `v2/infra/scripts/test_dr.sh`
- `v2/infra/scripts/deploy.sh`
- `v2/infra/scripts/setup_vm01.sh`
- `v2/infra/scripts/setup_vm02.sh`
- `v2/infra/scripts/setup_vm03.sh`
- `v2/infra/cron/aprender-backup`
- `v2/infra/postgresql/postgresql.conf`
- `v2/infra/redis/redis.conf`
- `v2/infra/Dockerfile`
- `v2/infra/entrypoint.sh`
- `v2/infra/Makefile`
- `v2/backend/config/settings.py`
- `v2/backend/config/urls.py`
- `v2/backend/config/celery.py`
- `v2/backend/apps/core/middleware.py`
- `v2/backend/apps/core/logging_filters.py`
- `v2/backend/apps/core/views_health.py`
- `v2/backend/apps/core/views_basic.py`
- `v2/backend/apps/core/tasks_backup.py`
- `v2/frontend/src/utils/logger.ts`
- `v2/frontend/Dockerfile`
- `v2/Makefile`

**Notas de execução (alto nível)**
- Li a documentação de observabilidade, logging, backup/DR, deploy, SLO e scaling.
- Cruzei documentação com compose, Nginx, scripts de backup/DR, settings do Django e Celery.
- Verifiquei implementação de metrics, health checks, structured logging e Sentry.
- Rodei testes focados em readiness, logging, Sentry e SLO de latência.

**Status por módulo (doc vs implementação)**
| Módulo | Status | Evidência principal | Observações |
|---|---|---|---|
| Observabilidade (Prometheus/Grafana) | Parcial | `v2/infra/docker-compose.observability.yml`, `v2/infra/prometheus.yml`, `v2/backend/config/urls.py` | Web metrics OK; worker/beat sem targets; `/metrics` não é proxied no Nginx. |
| Structured Logging | Parcial | `v2/backend/config/settings.py`, `v2/backend/apps/core/logging_filters.py`, `v2/backend/apps/core/middleware.py` | JSON logging OK; bug de `request_id` reaproveitado por thread. |
| Sentry APM | OK | `v2/backend/config/settings.py`, `v2/backend/requirements.txt` | Habilita por `SENTRY_DSN`. |
| Health/Ready | OK | `v2/backend/config/urls.py`, `v2/backend/apps/core/views_health.py` | `/healthz/`, `/healthz/detailed/`, `/api/readyz/`. |
| Backups automatizados (Celery) | Quebrado | `v2/backend/apps/core/tasks_backup.py`, `v2/infra/docker-compose.yml`, `v2/infra/scripts/backup_db.sh` | Script não está disponível no worker; script não usa env; caminho e host incorretos; naming incompatível com health check. |
| Backups VM (cron) | Parcial | `v2/infra/cron/aprender-backup`, `v2/infra/scripts/backup_db.sh` | Funciona para VM local, mas diverge da doc de backup via Celery. |
| DR | Parcial/Desalinhado | `v2/docs/DISASTER_RECOVERY.md`, `v2/docs/GUIDE_DR.md`, `v2/infra/scripts/test_dr.sh` | RPO/RTO e procedimentos inconsistentes; exemplos de scripts no doc não batem com scripts reais. |
| Scaling | Parcial | `v2/docs/SCALING.md`, `v2/backend/config/settings.py` | Sessões Redis OK; media files continuam locais (stateful). |
| Deploy/Runbook | Parcial | `v2/docs/RUNBOOK.md`, `v2/docs/DEPLOY_CHECKLIST.md`, `v2/infra/entrypoint.sh` | `entrypoint.sh` não é usado; variáveis de deploy não têm efeito no compose atual. |
| SLO/Alertas | Parcial | `v2/docs/SLO_DEFINITIONS.md` | Referência a `infra/prometheus/alerts.yml` inexistente. |

**Achados críticos**
1. **Backups via Celery falham por ausência do script no worker**. `tasks_backup.py` chama `/app/infra/scripts/backup_db.sh`, mas `docker-compose.yml` monta scripts apenas no `web` e o `Dockerfile` não copia scripts. Resultado: `FileNotFoundError` no worker e nenhum backup executado.
2. **Script de backup incompatível com o ambiente Docker**. `backup_db.sh` usa `pg_dump -h localhost` e `BACKUP_DIR=/var/backups/aprender` (sem volume). Em Docker, o DB está em `db` e o volume é `/backups`. Mesmo se o script fosse encontrado, o backup falha ou fica em storage efêmero.
3. **Health check de backup sempre degrada**. `verify_backup_health()` busca `backup_full_*.sql.gz`, mas o script gera `aprender_db_YYYYMMDD...sql.gz`. Resultado: nenhum backup “encontrado”, status sempre “degraded”.

**Achados altos**
1. **`/metrics` não é exposto no Nginx de produção**. `v2/infra/nginx/sites-available/aprender` não possui rota para `/metrics`, então o endpoint cai no `location /` (SPA) e quebra scraping do Prometheus externo.
2. **Agenda do Celery Beat pode não rodar em produção**. No systemd, o beat usa `--scheduler=django_celery_beat.schedulers:DatabaseScheduler`. Nesse modo, o `app.conf.beat_schedule` (onde o backup é definido) não é executado. Sem entries no DB, não há backups agendados.
3. **S3 upload prometido mas não disponível**. `BACKUP_OPERATIONS.md` afirma AWS CLI no `Dockerfile`, porém `v2/infra/Dockerfile` não instala `awscli` e `backup_db.sh` não implementa upload real.

**Achados médios**
1. **`RequestIDMiddleware` reaproveita `request_id` entre requisições**. O middleware só seta thread-local se não existir, então threads reutilizadas carregam o mesmo `request_id`. Isso invalida correlação de logs e auditoria.
2. **RPO/RTO e frequência de backup inconsistentes entre documentos**. `DISASTER_RECOVERY.md`, `GUIDE_DR.md`, `BACKUP_OPERATIONS.md` e `SLO_DEFINITIONS.md` divergem (RPO 5 min vs 24h; RTO 30 min vs 1h; backup 2h vs 3h).
3. **Documentos de DR contêm scripts divergentes**. `DISASTER_RECOVERY.md` mostra scripts que usam `docker compose exec`, nomes de arquivos diferentes e retenção de 30 dias, enquanto `infra/scripts/*.sh` são VM-oriented com retenção 7 dias.
4. **`test_dr.sh` usa DB name diferente**. O script tenta backup de `aprender_sistema`, mas o default do settings/compose é `aprender_db`.
5. **`SCALING.md` assume media em S3/MinIO, mas o settings usa `MEDIA_ROOT` local**. Em scaling horizontal, uploads podem ficar inconsistentes entre instâncias.
6. **`SLO_DEFINITIONS.md` referencia `infra/prometheus/alerts.yml`, que não existe**. Não há regras de alerta declaradas.

**Achados baixos**
1. **`LOGGING.md` referencia `logger.js`, mas o arquivo real é `logger.ts`**.
2. **`infra/Makefile` usa endpoints e porta incorretos para o compose padrão** (`/api/health/` e porta 8000). O compose padrão expõe 8002 e não existe `/api/health/`.

**Doc vs implementação (exemplos relevantes)**
| Documento | Afirmação | Implementação real | Impacto |
|---|---|---|---|
| `BACKUP_OPERATIONS.md` | Backup diário 2:00, `backup_db.sh` em `/backups` | Cron 3:00, script usa `/var/backups/aprender` | Confusão operacional e backups no lugar errado. |
| `BACKUP_OPERATIONS.md` | S3 upload via AWS CLI | Dockerfile sem `awscli`; script não implementa upload | S3 não funciona. |
| `DISASTER_RECOVERY.md` | Scripts baseados em `docker compose exec` | Scripts reais são VM-local (`pg_dump` localhost) | Runbook incorreto. |
| `OBSERVABILITY.md` | `/metrics` sempre disponível | Nginx não proxy `/metrics` | Scrape externo falha. |
| `SCALING.md` | Media em S3/MinIO (`django-storages`) | `MEDIA_ROOT` local | Stateless incompleto. |

**Testes executados**
```bash
docker compose -f v2/infra/docker-compose.yml exec -T web \
  pytest apps/core/tests/test_readyz.py \
         apps/core/tests/test_structured_logging.py \
         apps/core/tests/test_sentry.py \
         apps/core/tests/performance/test_api_latency.py -q
```
Resultado: `29 passed, 35 warnings in 4.25s`.

**Sugestões objetivas (ordem de impacto)**
1. **Corrigir backups no Docker**: copiar/montar scripts no worker, usar `DB_HOST`, `DB_PASSWORD`/`PGPASSWORD`, `BACKUP_DIR=/backups`, naming `backup_full_*.sql.gz`, e alinhar `verify_backup_health()` com o padrão real.
2. **Adicionar `/metrics` no Nginx**: criar `location /metrics/` proxy para `http://django`.
3. **Unificar DR/Backup docs**: escolher um caminho oficial (Docker ou VM), alinhar RPO/RTO e horários, e atualizar scripts no doc para refletir os reais.
4. **Consertar `RequestIDMiddleware`**: sempre atualizar o thread-local por requisição e limpar após response.
5. **Criar `infra/prometheus/alerts.yml` ou remover referência** em `SLO_DEFINITIONS.md`.
6. **Ajustar `infra/Makefile`** para porta 8002 e endpoint de health correto.


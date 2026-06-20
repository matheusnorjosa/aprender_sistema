# Plano Completo de Correções — Fases 01 a 07 (v2)

**Data**: 2026-02-05
**Objetivo**: corrigir todas as issues identificadas nas fases 01–07, com prioridade, dependências, critérios de aceite e validação.

## 0) Premissas e princípios
- V2 somente.
- Alinhar documentação e implementação; evitar ampliar acesso sem decisão explícita.
- Preferir mudanças mínimas com impacto alto (segurança/consistência/RBAC/backup).
- Cada etapa deve ter validação automática + smoke manual quando aplicável.

## 0.1) Melhorias propostas ao plano (novas)
- Adicionar decisões bloqueadoras explícitas (RBAC, backup, GCal OAuth, mapa).
- Definir critérios de aceite por item crítico.
- Separar execução em PRs menores por prioridade.
- Incluir risco/rollback por etapa sensível (RBAC, backup, DR).
- Completar configuração ausente de backups em settings e variáveis.

## 0.2) Decisões pendentes (bloqueadores)
1. **RBAC único para dashboards/métricas**: qual grupo tem acesso a quais páginas e endpoints?
2. **Política de conflito na criação**: bloquear criação sempre ou apenas avisar?
3. **Backup oficial**: Docker ou VM? (ou ambos, mas um deve ser o “canônico”).
4. **Exposição de `/metrics`**: aberto, protegido por IP allowlist, ou com auth?
5. **GCal OAuth**: cancelamento deve exigir credencial do publicador ou conta de serviço?

## 0.3) Definição de pronto (global)
- Testes relevantes passam.
- Docs atualizadas refletem comportamento real.
- Sem mudanças de RBAC sem decisão documentada.
- Rollback claro para itens de produção (backup, RBAC, métricas).

## 1) Prioridade P0 — Segurança e integridade operacional

### 1.1 Corrigir pipeline de backup no Docker (MP5)
**Problema**: `tasks_backup.py` chama script inexistente no worker; script usa `localhost` e `BACKUP_DIR` errado; naming incompatível com health check; settings não expõem `BACKUP_DIR`/`RETENTION`.

**Ações**
- Montar/copiar `v2/infra/scripts` em `web`, `worker` e `beat` (compose dev/prod).
- Ajustar `v2/infra/Dockerfile` para garantir scripts presentes em imagem.
- Corrigir `v2/infra/scripts/backup_db.sh`:
  - Usar `DB_HOST`/`DB_PORT`/`DB_USER`/`DB_NAME` e `PGPASSWORD`.
  - Escrever em `BACKUP_DIR=/backups` (configurável via env).
  - Naming padrão: `backup_full_YYYYMMDD_HHMMSS.sql.gz`.
- Ajustar `v2/backend/apps/core/tasks_backup.py`:
  - Passar `PGPASSWORD`.
  - Padronizar log de saída do script para parse confiável.
- Alinhar `verify_backup_health()` com o naming real.
- Adicionar `BACKUP_DIR`, `BACKUP_RETENTION_DAYS`, `BACKUP_S3_BUCKET` em `config/settings.py`.

**Critérios de aceite**
- Task de backup gera arquivo em `/backups` dentro do container.
- Health check retorna `healthy` quando há backup recente.
- Execução manual do script funciona no worker.

**Validação**
- `pytest apps/core/tests/test_tasks_backup.py` (criar se não existir).
- Smoke: `perform_database_backup.delay("full")` e `ls /backups`.

**Risco/Rollback**
- Risco: alterar caminho e naming pode afetar scripts externos.
- Rollback: manter naming antigo temporariamente ou suportar ambos no health check.

### 1.2 Corrigir `assign_groups` para respeitar whitelist e auto‑modificação
**Problema**: endpoint ignora validação do serializer.

**Ações**
- Reusar validação do `UsuarioAdminSerializer` no endpoint `assign_groups`.
- Bloquear auto‑modificação e grupos fora de `ALLOWED_USER_GROUPS`.

**Critérios de aceite**
- Endpoint rejeita grupo inválido e auto‑modificação.

**Validação**
- `pytest apps/core/tests/test_assign_groups.py`.

### 1.3 Corrigir acesso indevido em bloqueios (edit/delete)
**Problema**: usuários podem editar/excluir bloqueios de terceiros da mesma gerência.

**Ações**
- Implementar permissão por objeto para update/delete (owner ou perfil superior).
- Revisar queryset de update/delete (não apenas list).

**Critérios de aceite**
- Usuário comum não consegue alterar bloqueios de terceiros.

**Validação**
- Adicionar/ajustar testes de permissão em `apps/core/tests`.

## 2) Prioridade P1 — RBAC e consistência backend/UI

### 2.1 Alinhar RBAC de dashboards, métricas e mapa
**Problema**: UI e backend divergentes (Diretoria/DAT vs Controle/Gerência).

**Ações**
- Decidir política única e documentar.
- Ajustar gates do frontend (`v2/frontend/src/App.tsx`).
- Ajustar permissões backend quando necessário.

**Critérios de aceite**
- Não há páginas visíveis sem permissão correspondente no backend.

**Validação**
- `test_metrics_*`, `test_reports.py` + smoke UI.

### 2.2 Corrigir aprovação (PA) — permissões e transições
**Problema**: transições fora de “pendente” e permissões divergentes.

**Ações**
- Bloquear approve/reject se status != pendente.
- Unificar permissões entre approve/reject/batch.

**Critérios de aceite**
- Transições inválidas geram erro 400.

**Validação**
- `test_approval_policy_PA.py`, `test_solicitacao_fluxo.py`.

### 2.3 Corrigir criação de solicitação sem `check_conflicts`
**Problema**: backend não aplica validação de disponibilidade.

**Ações**
- Chamar `availability_service.check_conflicts()` na criação.
- Decidir se bloqueia sempre ou é configurável por flag.

**Critérios de aceite**
- Solicitação conflitante é bloqueada (ou sinalizada) de forma consistente.

**Validação**
- Adicionar teste específico de conflito na criação.

### 2.4 Garantir criação do grupo “Diretoria”
**Problema**: grupo usado no frontend sem seed/migration.

**Ações**
- Atualizar migrations/seed para criar “Diretoria”.
- Incluir em UI de Admin DAT.

**Validação**
- Seed/migration test + smoke em Admin DAT.

## 3) Prioridade P2 — Observabilidade, logs e infraestrutura

### 3.1 Expor `/metrics` no Nginx
**Problema**: endpoint não é proxied no Nginx de produção.

**Ações**
- Adicionar `location /metrics/` em `v2/infra/nginx/sites-available/aprender`.
- Decidir sobre proteção (IP allowlist/rede interna) e aplicar.

**Validação**
- `curl https://<host>/metrics` com acesso autorizado.

### 3.2 Corrigir `RequestIDMiddleware` (thread-local)
**Problema**: thread reutiliza `request_id` entre requisições.

**Ações**
- Sempre sobrescrever `threading.current_thread().request_id` por request.
- Limpar após response.

**Validação**
- Ajustar/expandir `test_structured_logging.py`.

### 3.3 Alinhar scheduler de backups no systemd
**Problema**: `DatabaseScheduler` ignora `app.conf.beat_schedule`.

**Ações**
- Definir tarefas no DB ou remover `DatabaseScheduler`.
- Documentar escolha no runbook.

**Validação**
- `celery -A config inspect scheduled`.

## 4) Prioridade P3 — Documentação e divergências

### 4.1 Unificar docs de backup/DR/SLO
**Problema**: RPO/RTO/frequência inconsistentes; scripts divergentes.

**Ações**
- Escolher caminho oficial (Docker ou VM) e atualizar:
  - `BACKUP_OPERATIONS.md`, `DISASTER_RECOVERY.md`, `GUIDE_DR.md`, `SLO_DEFINITIONS.md`.
- Garantir exemplos coerentes com `infra/scripts/*`.

### 4.2 Atualizar docs de API e RBAC
**Problema**: `API_REFERENCE.md` e `RBAC_COMPLETO.md` desatualizados.

**Ações**
- Alinhar endpoints, permissões e exemplos.

### 4.3 Ajustes menores de docs
- `LOGGING.md` -> `logger.ts`.
- Criar `infra/prometheus/alerts.yml` ou remover referência.

## 5) Prioridade P4 — Bugs funcionais e UX

### 5.1 Corrigir `CadastrosPage` (payload)
**Problema**: frontend envia campos não suportados.

**Ações**
- Ajustar payload ou atualizar serializer/model.

### 5.2 Corrigir importações (upload validation)
**Problema**: `ImportComprasView` sem validação de tamanho/MIME.

**Ações**
- Replicar validações dos demais endpoints.

### 5.3 Ajustar rotas quebradas e UI
- Corrigir links `/admin-dat` -> `/dat/admin`.
- Resolver download de ETL reports (endpoint backend ou Nginx/STATIC).

### 5.4 Mapa do Brasil
- Implementar filtros `data_inicio/data_fim` ou remover do frontend.
- Remover truncamento por `limit` para agregações por UF, ou criar endpoint agregado.
- Corrigir chave de coordenadores por `municipio_id`.

## 6) Prioridade P5 — GCal e detalhes de contrato

### 6.1 Corrigir cancelamento OAuth
**Problema**: cancel usa service account.

**Ações**
- Usar OAuth client quando `GCAL_AUTH_MODE=oauth`.

### 6.2 Corrigir drift hash online
**Problema**: hash inconsistente com `conferenceData`.

**Ações**
- Padronizar hash (incluir/excluir conferenceData consistentemente).

### 6.3 RBAC GCal endpoints
- Restringir `/api/gcal/calendars/` e `/api/gcal/health/` conforme docs ou ajustar docs.

## 7) Verificação final (regressão)

**Testes recomendados**
- Auth/RBAC: `test_assign_groups.py`, `test_admin_user_security.py`.
- Solicitações/PA: `test_approval_policy_PA.py`, `test_solicitacao_fluxo.py`.
- Disponibilidade: `test_multi_sector_permissions.py` + novos de bloqueio.
- GCal: `pytest -k gcal`.
- DAT/ETL: `test_dat_module.py`, `test_import_*`, `test_etl_reports_latest.py`.
- Métricas/Relatórios: `test_metrics_*`, `test_reports.py`.
- Observabilidade/infra: `test_readyz.py`, `test_structured_logging.py`, `test_sentry.py`, `test_api_latency.py`.

## 8) Ordem sugerida de execução (resumo)
1. Backup/DR + scripts (P0).
2. RBAC e permissões críticas (P1).
3. Observabilidade e logging (P2).
4. Docs e alinhamentos (P3).
5. Bugs funcionais de UI/ETL/Mapa (P4).
6. Ajustes GCal (P5).
7. Regressão completa.

## 9) Estratégia de entrega
- 1 PR por prioridade (P0, P1, P2, P3, P4, P5) ou por módulo crítico.
- Cada PR deve incluir:
  - mudança + testes + doc correspondente.
  - checklist de aceitação preenchida.
  - rollback básico (revert commit + nota de impacto).

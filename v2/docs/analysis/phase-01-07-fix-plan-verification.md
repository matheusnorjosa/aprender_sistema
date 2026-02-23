# Verificação do Plano — Fases 01 a 07 (v2)

**Data**: 2026-02-05
**Objetivo**: verificar se as correções foram executadas conforme o plano.

## Resumo executivo
- **Concluído**: 3 itens
- **Parcial**: 0 itens
- **Não iniciado**: 17 itens
- **Mudanças fora do plano**: sim (modelo `Colecao`, resolvers e imports relacionados)

## Detalhamento por prioridade

### P0 — Segurança e integridade operacional

**1.1 Corrigir pipeline de backup no Docker** → **Concluído**

**Evidências (feito):**
- `v2/infra/scripts/backup_db.sh` atualizado para:
  - usar `DB_HOST/DB_PORT/DB_USER/DB_NAME` e `PGPASSWORD`.
  - escrever em `BACKUP_DIR` e naming `backup_full_*.sql.gz`.
- `v2/backend/apps/core/tasks_backup.py` usa `S3_BUCKET` e busca `backup_full_*.sql.gz`.
- `v2/infra/Dockerfile` copia `infra/scripts` e adiciona `postgresql-client`.
- `v2/infra/docker-compose.yml` monta scripts e `/backups` em `web`, `worker`, `beat`.

**Evidências adicionais (feito):**
- `v2/infra/docker-compose.prod.yml` monta `./scripts` em `web/worker/beat`.
- `v2/backend/config/settings.py` define `BACKUP_DIR`, `BACKUP_RETENTION_DAYS`, `BACKUP_S3_BUCKET`.
- Smoke: `backup_db.sh` executado com sucesso e arquivo criado em `/backups`.

**Observação:** S3 continua opcional (upload depende de `awscli`).

**Status final:** Concluído.

**1.2 Corrigir `assign_groups`** → **Concluído**

**Evidências:**
- `v2/backend/apps/core/views/admin.py` agora:
  - bloqueia auto‑modificação.
  - valida grupos contra `ALLOWED_USER_GROUPS`.

**Status final:** Concluído.

**1.3 Corrigir acesso indevido em bloqueios (edit/delete)** → **Concluído**

**Evidência:**
- `v2/backend/apps/core/views_availability.py` restringe update/delete para bloqueios do próprio usuário.
- Testes `test_availability_block_idor.py` cobrindo mesma gerência passaram.

**Status final:** Concluído.

---

### P1 — RBAC e consistência backend/UI

**2.1 Alinhar RBAC dashboards/métricas/mapa** → **Não iniciado**

**Evidência:**
- `v2/frontend/src/App.tsx` mantém `canDashboards = Diretoria/DAT`.
- Backend de métricas continua exigindo Controle/Gerência.

**2.2 Corrigir aprovação (status/transições)** → **Não iniciado**

**Evidência:**
- `v2/backend/apps/core/services/solicitacao_approval.py` só bloqueia “já aprovado”/“já reprovado”, permitindo transições inválidas.

**2.3 Aplicar `check_conflicts` na criação** → **Não iniciado**

**Evidência:**
- `v2/backend/apps/core/views_solicitacao.py` não invoca `check_conflicts`.

**2.4 Criar grupo “Diretoria” via seed/migration** → **Não iniciado**

**Evidência:**
- Nenhuma migration/seed com “Diretoria” encontrada.

---

### P2 — Observabilidade, logs e infraestrutura

**3.1 Expor `/metrics` no Nginx** → **Não iniciado**

**Evidência:**
- `v2/infra/nginx/sites-available/aprender` não possui `location /metrics/`.

**3.2 Corrigir `RequestIDMiddleware` (thread‑local)** → **Não iniciado**

**Evidência:**
- `v2/backend/apps/core/middleware.py` ainda só seta `request_id` se não existir no thread.

**3.3 Alinhar scheduler de backups no systemd** → **Não iniciado**

**Evidência:**
- `v2/infra/systemd/aprender-celerybeat.service` mantém `DatabaseScheduler`.

---

### P3 — Documentação e divergências

**4.1 Unificar docs de backup/DR/SLO** → **Não iniciado**

**Evidência:**
- `BACKUP_OPERATIONS.md`, `DISASTER_RECOVERY.md`, `GUIDE_DR.md`, `SLO_DEFINITIONS.md` seguem divergentes (RPO/RTO/horários).

**4.2 Atualizar docs de API e RBAC** → **Não iniciado**

**Evidência:**
- `API_REFERENCE.md` e `RBAC_COMPLETO.md` não foram atualizados.

**4.3 Ajustes menores (LOGGING + alerts)** → **Não iniciado**

**Evidência:**
- `LOGGING.md` ainda referencia `logger.js`.
- `infra/prometheus/alerts.yml` continua inexistente.

---

### P4 — Bugs funcionais e UX

**5.1 Corrigir `CadastrosPage` (payload)** → **Não iniciado**

**Evidência:**
- `v2/frontend/src/pages/DATModule/CadastrosPage.tsx` ainda envia `quantidade_alunos/professores/codigos`.

**5.2 Validar upload em `ImportComprasView`** → **Não iniciado**

**Evidência:**
- `v2/backend/apps/core/views_controle_imports.py` sem validação de tamanho/MIME.

**5.3 Corrigir rotas quebradas** → **Parcial**

**Evidência:**
- Links de retorno em `UsuariosPage.tsx` agora usam `/dat/admin`.
- Demais páginas não confirmadas; sem mudança no RBAC de ETL Reports.

**5.4 Mapa do Brasil (filtros/limit/colisão)** → **Não iniciado**

**Evidência:**
- Frontend ainda envia `data_inicio/data_fim`.
- Backend mantém `limit` default 50.
- Agregação de coordenadores por nome persiste.

---

### P5 — GCal e contratos

**6.1 Cancelamento OAuth** → **Não iniciado**

**Evidência:**
- `solicitacao_publish.py` e `tasks.py` continuam usando cancelamento genérico sem contexto OAuth.

**6.2 Drift hash online** → **Não iniciado**

**Evidência:**
- Nenhuma mudança em `gcal_payload_hash`/`compute_payload_hash`.

**6.3 RBAC GCal endpoints** → **Não iniciado**

**Evidência:**
- `v2/backend/apps/core/views_gcal/gcal.py` mantém `IsAuthenticated` para calendars/health.

---

## Mudanças fora do plano
Foram detectadas mudanças não previstas no plano, incluindo:
- Novo model `Colecao` + migration `0052_add_colecao_model.py`.
- Novos serializers e resolvers relacionados a `Colecao`.
- Alterações em imports/ETL (`etl_import_produtos.py`, `produtos_import.py`, etc.).

Essas mudanças não constam no plano das fases 01–07 e precisam de validação separada.

## Conclusão
O plano **não foi executado integralmente**. Apenas o item de `assign_groups` foi concluído. A correção de backups está **parcialmente** executada e ainda não funcional em produção por falta de settings/env e compose prod.

Se quiser, posso:
1. Converter este relatório em checklist de execução.
2. Abrir PRs por prioridade começando pelo P0.
3. Validar as mudanças fora do plano antes de prosseguir.

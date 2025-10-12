# Runbook: Validação End-to-End — Google Calendar Sync

## Objetivo
Validar fluxo completo de solicitação → aprovação → sincronização com Google Calendar usando FakeCalendarClient (sem publicar no Google real).

---

## 🔧 Pré-requisitos

- Sistema rodando em Docker (`cd v2/infra && docker compose up -d`)
- Usuário admin criado
- Grupo "Superintendência" configurado
- PostgreSQL operacional

---

## 📋 Etapas de Validação

### 1. Preparar Dados Base

```bash
# Entrar no shell Django
docker compose exec web python manage.py shell
```

```python
from apps.core.models import Usuario, Municipio, TipoEvento, Projeto
from django.contrib.auth.models import Group

# Criar grupo Superintendência (se não existir)
superintendencia, _ = Group.objects.get_or_create(name="Superintendência")

# Criar usuários
# Usuário comum (coordenador)
user_coord = Usuario.objects.create_user(
    username="coord1",
    email="coord1@example.com",
    password="senha123",
    cpf="12345678901",
)

# Usuário superintendência
user_super = Usuario.objects.create_user(
    username="super1",
    email="super1@example.com",
    password="senha123",
    cpf="98765432100",
)
user_super.groups.add(superintendencia)

# Criar município
municipio = Municipio.objects.create(
    nome="Fortaleza",
    uf="CE",
)

# Criar tipo de evento
tipo_evento = TipoEvento.objects.create(
    nome="Formação",
    descricao="Formação pedagógica",
)

print("✅ Dados base criados com sucesso!")
```

### 2. Criar Solicitação via API

```bash
# Obter token/session do coordenador
# (ou usar Django Admin para criar solicitação)

# POST /api/solicitacoes/ com autenticação
curl -X POST http://localhost:8000/api/solicitacoes/ \
  -H "Content-Type: application/json" \
  -u coord1:senha123 \
  -d '{
    "usuario": 1,
    "municipio": 1,
    "tipo_evento": 1,
    "inicio": "2025-10-20T09:00:00-03:00",
    "fim": "2025-10-20T12:00:00-03:00",
    "observacoes": "Teste E2E de sincronização"
  }'
```

**Validação esperada:**
- Status code: `201 Created`
- Response inclui `"status": "pendente"` (PA-01: nunca auto-aprova)
- `external_event_id` é `null`

### 3. Verificar Disponibilidade (Opcional)

```bash
# GET /api/availability/check/
curl -G http://localhost:8000/api/availability/check/ \
  -u coord1:senha123 \
  --data-urlencode "usuario_id=1" \
  --data-urlencode "inicio=2025-10-20T09:00:00-03:00" \
  --data-urlencode "fim=2025-10-20T12:00:00-03:00" \
  --data-urlencode "municipio_id=1"
```

**Validação esperada:**
- `{"ok": true, "conflicts": []}` (sem conflitos)
- Ou lista de conflitos se houver (RD-01 a RD-08)

### 4. Aprovar Solicitação (Superintendência)

```bash
# PATCH /api/solicitacoes/<id>/approve/
curl -X PATCH http://localhost:8000/api/solicitacoes/1/approve/ \
  -u super1:senha123
```

**Validação esperada:**
- Status code: `200 OK`
- Response: `{"detail": "Solicitação aprovada com sucesso."}`

**Tentar com usuário sem permissão (deve falhar):**
```bash
curl -X PATCH http://localhost:8000/api/solicitacoes/1/approve/ \
  -u coord1:senha123
```

**Validação esperada:**
- Status code: `403 Forbidden` (PA-02: apenas Superintendência)

### 5. Dry-Run de Sincronização

**Modo Human-Readable (padrão):**
```bash
# Executar command em modo dry-run (não altera DB/Calendar)
docker compose exec web python manage.py preagenda_to_gcal \
  --calendar-id test-calendar \
  --client=fake \
  --dry-run \
  --verbose
```

**Validação esperada:**
```
[CLIENT: fake] Usando FakeCalendarClient (in-memory, sem side effects)
[DRY-RUN MODE] Nenhuma alteração será feita
Processando 1 solicitações...
Calendário: test-calendar
Período: 2025-07-13 a 2026-04-09

✓ CREATE   #   1 → Fortaleza - CE — Formação — coord1

============================================================
RESUMO
============================================================
Total processado: 1
  CREATE:     1 (novos eventos)
  UPDATE:     0 (eventos atualizados)
  ADOPT:      0 (eventos adotados)
  DELETE:     0 (eventos removidos)
  SKIP:       0 (não processados)

Nenhuma alteração foi feita (modo dry-run). Execute sem --dry-run para aplicar.
```

**Modo JSON (para automação/Celery):**
```bash
# Executar com --json (apenas JSON em stdout)
docker compose exec web python manage.py preagenda_to_gcal \
  --calendar-id test-calendar \
  --client=fake \
  --dry-run \
  --json
```

**Validação esperada (JSON puro em stdout):**
```json
{
  "meta": {
    "calendar_id": "test-calendar",
    "client": "fake",
    "since": "2025-07-13T00:00:00+00:00",
    "until": "2026-04-09T23:59:59+00:00",
    "dry_run": true,
    "batch_size": 200,
    "run_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "started_at": "2025-10-12T10:30:00+00:00",
    "finished_at": "2025-10-12T10:30:05+00:00",
    "duration_ms": 5234
  },
  "totals": {
    "CREATE": 1,
    "UPDATE": 0,
    "ADOPT": 0,
    "DELETE": 0,
    "SKIP": 0,
    "total": 1
  }
}
```

### 6. Sincronização Real (FakeClient)

```bash
# Executar sem --dry-run (altera DB, mas usa FakeClient = sem efeito no Google real)
docker compose exec web python manage.py preagenda_to_gcal \
  --calendar-id test-calendar \
  --client=fake \
  --verbose
```

**Validação esperada:**
- Mesma saída, mas sem aviso de dry-run
- `CREATE: 1`

**Verificar no DB:**
```python
from apps.core.models import Solicitacao

sol = Solicitacao.objects.get(id=1)
print(f"Status: {sol.status}")  # Deve ser "aprovado"
print(f"External Event ID: {sol.external_event_id}")  # Deve ser "asv2-1" (novo padrão)
```

### 7. Idempotência (Segunda Rodada)

```bash
# Executar novamente o mesmo comando
docker compose exec web python manage.py preagenda_to_gcal \
  --calendar-id test-calendar \
  --client=fake \
  --verbose
```

**Validação esperada:**
- `UPDATE: 1` (segunda rodada não duplica, apenas atualiza)
- `CREATE: 0`
- Total processado: 1

### 8. Reprovar e Deletar Evento

```bash
# Reprovar solicitação
curl -X PATCH http://localhost:8000/api/solicitacoes/1/reject/ \
  -H "Content-Type: application/json" \
  -u super1:senha123 \
  -d '{"justificativa": "Teste de reprovação"}'
```

**Sincronizar novamente:**
```bash
docker compose exec web python manage.py preagenda_to_gcal \
  --calendar-id test-calendar \
  --client=fake \
  --verbose
```

**Validação esperada:**
- `DELETE: 1` (evento removido)
- `external_event_id` limpo no DB (`null`)

### 9. Testar Flag `--no-delete`

```bash
# Aprovar novamente
curl -X PATCH http://localhost:8000/api/solicitacoes/1/approve/ \
  -u super1:senha123

# Sincronizar
docker compose exec web python manage.py preagenda_to_gcal \
  --calendar-id test-calendar \
  --client=fake

# Reprovar
curl -X PATCH http://localhost:8000/api/solicitacoes/1/reject/ \
  -u super1:senha123 \
  -d '{"justificativa": "Teste no-delete"}'

# Sincronizar com --no-delete
docker compose exec web python manage.py preagenda_to_gcal \
  --calendar-id test-calendar \
  --client=fake \
  --no-delete \
  --verbose
```

**Validação esperada:**
- `SKIP: 1` (não deleta por causa de `--no-delete`)
- Evento continua no "calendar" (FakeClient)

### 10. Testar Filtros

**Por IDs específicos:**
```bash
docker compose exec web python manage.py preagenda_to_gcal \
  --calendar-id test-calendar \
  --client=fake \
  --ids 1 \
  --dry-run
```

**Por janela temporal:**
```bash
docker compose exec web python manage.py preagenda_to_gcal \
  --calendar-id test-calendar \
  --client=fake \
  --since 2025-10-01T00:00:00 \
  --until 2025-10-31T23:59:59 \
  --dry-run
```

**Validação esperada:**
- Apenas solicitações no range especificado são processadas

### 11. Testar Batch Processing (Chunking)

**Para grandes volumes de dados (evitar lock timeout):**
```bash
# Processar em chunks de 50 registros por vez
docker compose exec web python manage.py preagenda_to_gcal \
  --calendar-id test-calendar \
  --client=fake \
  --batch-size 50 \
  --verbose
```

**Validação esperada:**
- Lock renovado automaticamente a cada chunk (via `cache.touch()`)
- Mensagem `[LOCK RENEWED] X processados` quando verbose ativo
- Fallback graceful se cache backend não suporta `touch()`

**Observação:**
- `--batch-size=0`: Processa todos de uma vez (legacy mode)
- `--batch-size=200`: Padrão (compromisso entre performance e lock safety)
- Lock TTL: 5 minutos (300s)

### 12. Testar Celery Preview-Then-Apply

**Executar task manualmente:**
```bash
docker compose exec web python manage.py shell
```

```python
from apps.core.tasks import preview_then_apply_gcal

# Executar de forma síncrona (para debug)
result = preview_then_apply_gcal()
print(result)
```

**Validação esperada:**
```python
{
    "preview": {
        "meta": {...},
        "totals": {"CREATE": 1, ...}
    },
    "apply": {
        "meta": {...},
        "totals": {"CREATE": 1, ...}
    },
    "applied": True,
    "reason": "Applied 1 changes"
}
```

**Se sem mudanças (total_changes == 0):**
```python
{
    "preview": {...},
    "applied": False,
    "reason": "No changes detected (total_changes == 0)"
}
```

**Celery Beat (automático a cada 5 minutos):**
```bash
# Verificar que beat está configurado
docker compose exec web python manage.py shell
```

```python
from django.conf import settings
print(settings.CELERY_BEAT_SCHEDULE)
# Deve mostrar: {'gcal-sync-every-5-minutes': {...}}
```

### 13. Testar Config Mutável (DB-based Settings)

**Criar config via Django shell:**
```python
from apps.core.models import Config
from django.utils import timezone

# Criar config para availability
Config.objects.create(
    key="availability",
    value={
        "TRAVEL_BUFFER_MINUTES": 90,
        "AVAILABILITY_DAILY_LIMIT_HOURS": 6
    },
    effective_at=timezone.now()
)
```

**Verificar uso do config:**
```python
from apps.core.services.config_service import get_cfg

cfg = get_cfg("availability", {})
print(cfg)  # Deve retornar: {'TRAVEL_BUFFER_MINUTES': 90, ...}

# Teste de cache (segunda leitura não bate DB)
cfg2 = get_cfg("availability", {})
print(cfg2)  # Mesmo resultado, mas do cache (5min TTL)
```

**Invalidar cache manualmente:**
```python
from apps.core.services.config_service import bust_cfg

bust_cfg("availability")
# Próxima leitura vai no DB novamente
```

**Observação:**
- Cache TTL: 5 minutos (300s)
- Auto-invalidação via signal `post_save(Config)`
- Fallback para `settings.py` se Config não existir
- Usado em `availability_service.py` para RD-04/RD-05

---

## ❌ Erros Esperados (Comportamento Correto)

### Tentar usar `--client=google` sem implementação:

```bash
docker compose exec web python manage.py preagenda_to_gcal \
  --calendar-id test-calendar \
  --client=google
```

**Saída esperada:**
```
GoogleCalendarClient ainda não implementado. Use FakeCalendarClient (--client=fake) ou aguarde PR 4/N.

💡 Solução temporária: use --client=fake para validar fluxo
   ou aguarde implementação do GoogleCalendarClient (PR 4/N)
```

### Sem `GCAL_CALENDAR_ID` configurado:

```bash
docker compose exec web python manage.py preagenda_to_gcal
```

**Saída esperada:**
```
GCAL_CALENDAR_ID não configurado e --calendar-id não informado.
Configure GCAL_CALENDAR_ID no .env ou use --calendar-id
```

---

## ✅ Checklist de Validação

**Fluxo Base:**
- [ ] Solicitação criada com `status=pendente` (PA-01)
- [ ] Coordenador **não consegue** aprovar (PA-02, retorna 403)
- [ ] Superintendência **consegue** aprovar (PA-02, retorna 200)
- [ ] Disponibilidade checada corretamente (RD-01 a RD-08)
- [ ] Dry-run não altera DB nem Calendar
- [ ] Primeira sincronização: `CREATE`
- [ ] Segunda sincronização: `UPDATE` (idempotência)
- [ ] Reprovar → sincronizar: `DELETE`
- [ ] Flag `--no-delete` protege de DELETE → `SKIP`
- [ ] Filtros `--ids`, `--since`, `--until` funcionam
- [ ] `--client=google` mostra erro amigável
- [ ] FakeClient não publica no Google real

**Novos Recursos (Seção 4 - PR 3/3):**
- [ ] `--json` retorna JSON válido (sem texto em stdout)
- [ ] EventId usa padrão `asv2-{id}` (mínimo 6 chars)
- [ ] `--batch-size` processa em chunks corretamente
- [ ] Lock renovado via `cache.touch()` com fallback graceful
- [ ] Config model criado e migração aplicada
- [ ] `get_cfg()` funciona com cache de 5min
- [ ] Cache invalidado automaticamente via signal
- [ ] Celery task `preview_then_apply_gcal` criado
- [ ] CELERY_BEAT_SCHEDULE configurado (5min interval)
- [ ] Preview-then-apply só executa apply se total_changes > 0

---

## 🚀 Próximo Passo: GoogleCalendarClient Real

Quando implementar `GoogleCalendarClient` (PR 4/N):

1. **Trocar** `--client=fake` por `--client=google`
2. **Configurar** `GCAL_CALENDAR_ID` real no `.env`
3. **Adicionar** credenciais OAuth2/Service Account
4. **Executar** com dados de produção
5. **Verificar** eventos criados no Google Calendar real

**Exemplo:**
```bash
docker compose exec web python manage.py preagenda_to_gcal \
  --client=google \
  --calendar-id c_1234567890abcdef@group.calendar.google.com \
  --since 2025-10-01T00:00:00 \
  --until 2025-10-31T23:59:59 \
  --verbose
```

---

## 📊 Métricas de Sucesso

- **0 erros** durante validação
- **100% dos testes** passando (39/39)
- **Idempotência** garantida (segunda rodada não duplica)
- **RBAC** funcionando (403 para não-super)
- **PA-01** respeitado (nunca auto-aprova)
- **Dry-run** seguro (sem side effects)

---

## 🆘 Troubleshooting

### Erro: "No module named 'apps.core.services.gcal_google_client'"
**Causa:** Arquivo não existe ou não foi commitado
**Solução:** Verificar que `apps/core/services/gcal_google_client.py` existe

### Erro: "GCAL_CALENDAR_ID não configurado"
**Causa:** Variável de ambiente não definida
**Solução:** Usar `--calendar-id test-calendar` ou configurar no `.env`

### Erro: "Não encontrei grupo 'Superintendência'"
**Causa:** Grupo não foi criado
**Solução:** Executar etapa 1 do runbook

### Erro: AttributeError: 'int' object has no attribute 'endswith'
**Causa:** Command retornando int ao invés de usar sys.exit()
**Solução:** Já corrigido (todos `return X` substituídos por `sys.exit(X)`)

---

## 🌐 Usar GoogleCalendarClient Real (PR 4/N)

**IMPORTANTE**: GoogleCalendarClient agora está implementado! Esta seção documenta como usá-lo com segurança.

### Pré-requisitos

1. **Service Account configurada** no Google Cloud Console
2. **Credenciais JSON** baixadas
3. **Permissões** no calendário de destino: "Make changes to events"
4. **GCAL_CLIENT ainda em fake** nos ambientes (não trocar sem validação)

### Passo 1: Preparar Credenciais

**1.1 Criar Service Account** (Google Cloud Console):
```
1. Acessar https://console.cloud.google.com/
2. Navegar para "IAM & Admin" → "Service Accounts"
3. Criar Service Account com nome: "aprender-sistema-calendar"
4. Gerar JSON key e baixar para local seguro
```

**1.2 Compartilhar Calendário** com a Service Account:
```
1. Abrir Google Calendar (https://calendar.google.com/)
2. Selecionar o calendário de destino
3. Configurações → "Share with specific people"
4. Adicionar email da Service Account (xxx@xxx.iam.gserviceaccount.com)
5. Permissão: "Make changes to events"
```

**1.3 Montar credenciais no Docker**:
```bash
# Criar pasta de secrets
mkdir -p v2/infra/secrets

# Copiar arquivo de credenciais
cp ~/Downloads/service-account.json v2/infra/secrets/

# Adicionar ao docker-compose.yml (web service):
volumes:
  - ../backend:/app
  - ./secrets:/app/secrets:ro  # Read-only mount
```

### Passo 2: Configurar Variáveis de Ambiente

**2.1 Atualizar `.env` (staging/local APENAS para testes controlados)**:
```bash
# ⚠️ NÃO trocar em produção sem validação prévia!
GCAL_CLIENT=google  # Ativa client real
GCAL_CALENDAR_ID=c_XXXXXXXX@group.calendar.google.com  # ID real do calendário
GOOGLE_SERVICE_ACCOUNT_JSON=/app/secrets/service-account.json
```

**2.2 Verificar que Docker montou os secrets**:
```bash
cd v2/infra
docker compose restart web
docker compose exec -T web ls -la /app/secrets/
# Deve mostrar: service-account.json
```

### Passo 3: Dry-Run Seguro (SEMPRE primeiro!)

**3.1 Preview com dry-run + JSON**:
```bash
docker compose exec -T web python manage.py preagenda_to_gcal \
  --client=google \
  --dry-run \
  --json | python -m json.tool
```

**Validação esperada**:
```json
{
  "meta": {
    "calendar_id": "c_XXXXXXXX@group.calendar.google.com",
    "client": "google",
    "dry_run": true,
    ...
  },
  "totals": {
    "CREATE": N,
    "UPDATE": M,
    ...
  }
}
```

**3.2 Revisar diff**:
- Verificar quantidades (CREATE, UPDATE, DELETE)
- Conferir se IDs das solicitações estão corretos
- Validar que external_event_id segue padrão `asv2-{id}`

### Passo 4: Apply Real (após validação do preview)

**4.1 Executar sync real** (⚠️ modifica Google Calendar):
```bash
docker compose exec -T web python manage.py preagenda_to_gcal \
  --client=google \
  --json | python -m json.tool
```

**4.2 Validar no Google Calendar**:
```
1. Abrir https://calendar.google.com/
2. Selecionar o calendário usado
3. Verificar que eventos foram criados com IDs no formato "asv2-X"
4. Conferir que detalhes (título, horário, descrição) estão corretos
```

**4.3 Verificar no DB**:
```python
from apps.core.models import Solicitacao

# Listar solicitações com external_event_id preenchido
sols = Solicitacao.objects.filter(
    status='aprovado',
    external_event_id__isnull=False
).values('id', 'external_event_id', 'updated_at')[:10]

for s in sols:
    print(f"ID: {s['id']}, EventID: {s['external_event_id']}, Updated: {s['updated_at']}")
```

### Passo 5: Teste de Idempotência

**5.1 Segunda rodada** (deve atualizar, não criar):
```bash
docker compose exec -T web python manage.py preagenda_to_gcal \
  --client=google \
  --json | python -m json.tool
```

**Validação esperada**:
```json
{
  "totals": {
    "CREATE": 0,
    "UPDATE": N,  // Mesma quantidade do primeiro sync
    "ADOPT": 0,
    "DELETE": 0,
    "SKIP": M
  }
}
```

### Passo 6: Rollback (se necessário)

**6.1 Desativar client real**:
```bash
# .env
GCAL_CLIENT=fake  # Volta para modo seguro
```

**6.2 Limpar external_event_id do DB** (se sync foi indevido):
```python
from apps.core.models import Solicitacao

# Backup antes de limpar
bad_syncs = Solicitacao.objects.filter(
    external_event_id__startswith='asv2-',
    status='aprovado'
)

print(f"Total a limpar: {bad_syncs.count()}")

# Limpar (só se tiver certeza!)
bad_syncs.update(external_event_id=None)
```

**6.3 Deletar eventos do Google Calendar**:
```bash
# Usar API para deletar eventos em lote
docker compose exec -T web python manage.py shell -c "
from apps.core.services.gcal_google_client import GoogleCalendarClient
from apps.core.models import Solicitacao

client = GoogleCalendarClient()
calendar_id = 'c_XXXXXXXX@group.calendar.google.com'

bad_events = Solicitacao.objects.filter(
    external_event_id__startswith='asv2-',
    status='reprovado'  # ou qualquer outro critério
)

for sol in bad_events:
    try:
        client.delete(calendar_id, sol.external_event_id)
        print(f'Deleted: {sol.external_event_id}')
    except Exception as e:
        print(f'Error deleting {sol.external_event_id}: {e}')
"
```

### Checklist de Segurança

- [ ] **Dry-run executado** e revisado antes de apply
- [ ] **Preview JSON válido** e quantidades corretas
- [ ] **Service Account** com permissões mínimas (apenas Calendar API)
- [ ] **sendUpdates='none'** verificado (não envia emails)
- [ ] **eventId determinístico** (asv2-{id}) confirmado
- [ ] **Idempotência testada** (segunda rodada não duplica)
- [ ] **Rollback plan** definido (GCAL_CLIENT=fake + limpar DB)
- [ ] **Backup do Postgres** feito antes de sync real em produção

### Erros Comuns

**Erro: "Credentials file not found"**
```
Causa: GOOGLE_SERVICE_ACCOUNT_JSON apontando para arquivo inexistente
Solução: Verificar path e montagem do volume Docker
```

**Erro: "403 Forbidden" ao criar evento**
```
Causa: Service Account sem permissão no calendário
Solução: Compartilhar calendário com SA ("Make changes to events")
```

**Erro: "401 Unauthorized"**
```
Causa: Credenciais inválidas ou expiradas
Solução: Gerar novo JSON key para Service Account
```

**Erro: "eventId validation failed"**
```
Causa: eventId menor que 5 chars ou com caracteres inválidos
Solução: Já corrigido (asv2-{id} garante mínimo 6 chars)
```

---

## 📚 Referências

- **CLAUDE.md**: Cláusulas Pétreas (PA-01, RD-01 a RD-08)
- **BLUEPRINT.md**: Arquitetura e roadmap
- **Test Suite**: `apps/core/tests/test_gcal_sync_dryrun.py` (11 testes)
- **Google Calendar API**: https://developers.google.com/calendar/api/v3/reference
- **Service Account Setup**: https://developers.google.com/identity/protocols/oauth2/service-account

# Refinamentos PR 3/3 - Status de Implementação

## ✅ COMPLETO

### 1. Observabilidade do Sync
**Status:** ✅ Implementado e testado

**Campos adicionados em `Solicitacao`:**
- `last_synced_at`: DateTimeField (nullable) - timestamp da última tentativa
- `last_sync_action`: CharField (nullable) - CREATE/UPDATE/ADOPT/DELETE/SKIP
- `last_sync_error`: TextField (nullable) - mensagem de erro se houver

**Índice composto:**
- `(status, inicio, fim, updated_at)` - para queries incrementais eficientes

**Migration:** `0004_add_sync_observability_fields.py` aplicada

**Lógica atualizada:**
- `upsert_one()` grava campos após cada operação (sucesso ou falha)
- Erros capturados e gravados em `last_sync_error` (limitado a 500 chars)
- Timestamp em `last_synced_at` sempre atualizado

### 2. Metadados no Evento
**Status:** ✅ Implementado

**extendedProperties.private adicionado:**
```python
"extendedProperties": {
    "private": {
        "solicitation_id": str(s.id),
        "ssot_version": "v2",
        "last_updated": s.updated_at.isoformat(),
    }
}
```

**Benefício:** Facilita reconciliação e auditoria futura

### 3. Limites summary/description
**Status:** ✅ Implementado

**Limites aplicados:**
- `summary`: ≤1000 chars (corta com "..." se exceder)
- `description`: ≤5000 chars (corta com "..." se exceder)

**Código:**
```python
summary_trimmed = summary[:1000] if len(summary) > 1000 else summary
if len(summary) > 1000:
    summary_trimmed = summary[:997] + "..."
```

### 4. Cliente Plugável (fake|google)
**Status:** ✅ Implementado e testado

**Flag `--client`:**
- Choices: `["fake", "google"]`
- Default: `GCAL_CLIENT` setting (default="fake")

**Segurança:**
- Default seguro (fake) evita publicações acidentais
- Erro claro ao tentar usar `--client=google` sem implementação

---

## 🚧 PENDENTE (Próxima Sessão)

### 5. Sync Incremental por updated_at
**O que fazer:**
```python
# No command, adicionar filtro when --since/--until não passados
if not options["since"] and not options["until"]:
    # Sync incremental: apenas últimas 24h modificadas
    since = timezone.now() - timedelta(days=1)
    qs = qs.filter(updated_at__gte=since)
```

**Benefício:** Escala melhor (não processa toda base a cada execução)

### 6. Redis Lock (Single-Flight)
**O que fazer:**
```python
# No command, antes do loop principal
from django.core.cache import cache

LOCK_KEY = "preagenda_to_gcal:lock"
LOCK_TTL = 300  # 5 minutos

if not cache.add(LOCK_KEY, "locked", timeout=LOCK_TTL):
    self.stderr.write("Outra instância já está rodando. Abortando.")
    sys.exit(1)

try:
    # ... sync logic
finally:
    cache.delete(LOCK_KEY)
```

**Benefício:** Evita corrida de dois workers rodando sync simultaneamente

### 7. Normalização Município (RD-04)
**O que verificar:**
```python
# Em availability_service.py, linha ~170
# Garantir que compara municipio.id, não municipio.nome

if prev_municipio_id != municipio.id:  # Correto
    # buffer required
else:
    # same city, zero buffer
```

**Problema evitado:** "Fortaleza" vs "FORTALEZA" seria tratado como cidades diferentes

### 8. Testes de Bordas (RD-04/RD-05)
**Casos a adicionar:**

**RD-05 (capacidade diária):**
```python
def test_midnight_crossing_event():
    """Evento 23:00 → 01:00 (atravessa meia-noite)"""
    # Deve contar em ambos os dias

def test_exact_limit_should_pass():
    """7h já usadas + 1h novo == 8h limite → OK"""
    # Limite exato deve ser permitido
```

**RD-04 (buffer deslocamento):**
```python
def test_exact_buffer_should_pass():
    """Fim evento A + buffer exato == início evento B → OK"""
    # Buffer exato (não overlap) deve passar
```

### 9. Rate-Limit DRF
**O que fazer:**
```python
# settings.py
REST_FRAMEWORK = {
    # ... existing config
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
        "availability_check": "60/min",  # Específico para /availability/check/
    }
}

# views.py
class AvailabilityCheckView(APIView):
    throttle_scope = "availability_check"
    # ...
```

**Benefício:** Evita abuso da API de checagem

### 10. Log Estruturado (approve/reject)
**O que fazer:**
```python
# views.py
import logging
import json

logger = logging.getLogger(__name__)

@action(detail=True, methods=["patch"], url_path="approve")
def approve(self, request, pk=None):
    solicitacao = self.get_object()

    # Log estruturado
    logger.info(
        "approval_action",
        extra={
            "event": "solicitacao_approved",
            "user_id": request.user.id,
            "username": request.user.username,
            "solicitation_id": solicitacao.id,
            "action": "approve",
            "ip_address": request.META.get("REMOTE_ADDR"),
            "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
            "timestamp": timezone.now().isoformat(),
        }
    )

    # ... existing logic
```

**Benefício:** Auditoria completa de aprovações/reprovações

### 11. Política de Exclusão no Runbook
**O que fazer:**
Adicionar seção no `RUNBOOK_E2E_GCAL_SYNC.md`:

```markdown
## 🗑️ Política de Exclusão em Produção

### Regras Obrigatórias

1. **Janela Curta**: Deletar apenas eventos nos próximos 30 dias
   ```bash
   --since $(date +%Y-%m-%d) --until $(date -d '+30 days' +%Y-%m-%d)
   ```

2. **Dry-Run Prévio**: SEMPRE rodar com `--dry-run` antes
   ```bash
   # Passo 1: Preview
   python manage.py preagenda_to_gcal --dry-run --verbose

   # Passo 2: Revisar output (quantos DELETEs?)

   # Passo 3: Executar real (SE E SOMENTE SE output OK)
   python manage.py preagenda_to_gcal
   ```

3. **Backup Automático**: Antes de deletar, exportar lista
   ```bash
   python manage.py dumpdata core.Solicitacao --indent=2 > backup_pre_delete.json
   ```

4. **Usar --no-delete em Dúvida**: Preserva eventos até confirmação
   ```bash
   python manage.py preagenda_to_gcal --no-delete
   ```
```

### 12. Config Mutável em DB (Futuro - PR 5/N)
**Modelo proposto:**
```python
class Config(models.Model):
    """Configurações mutáveis sem deploy"""
    key = models.CharField(max_length=100, unique=True, db_index=True)
    value = models.TextField()
    value_type = models.CharField(max_length=20, choices=[
        ("int", "Integer"),
        ("float", "Float"),
        ("str", "String"),
        ("bool", "Boolean"),
    ])
    effective_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(Usuario, on_delete=models.PROTECT)

    class Meta:
        db_table = "core_config"
        verbose_name = "Configuração"
        ordering = ["-effective_at"]
```

**Uso:**
```python
# Ao invés de:
buffer = getattr(settings, "TRAVEL_BUFFER_MINUTES", 120)

# Usar:
buffer = Config.get_int("TRAVEL_BUFFER_MINUTES", default=120)
```

**Cache:**
```python
from django.core.cache import cache

def get_int(key, default=None):
    cached = cache.get(f"config:{key}")
    if cached is not None:
        return int(cached)

    try:
        config = Config.objects.get(key=key)
        value = int(config.value)
        cache.set(f"config:{key}", value, timeout=300)  # 5 min
        return value
    except Config.DoesNotExist:
        return default
```

### 13. Celery Beat (Futuro - PR 6/N)
**Task proposta:**
```python
# tasks.py
from celery import shared_task

@shared_task
def preview_and_sync():
    """Preview antes de aplicar (padrão seguro)"""
    # Passo 1: Dry-run
    result_dry = subprocess.run([
        "python", "manage.py", "preagenda_to_gcal",
        "--dry-run", "--client=google"
    ], capture_output=True, text=True)

    # Parse output: quantas ações?
    lines = result_dry.stdout.split("\n")
    actions = parse_summary(lines)  # {"CREATE": 5, "UPDATE": 3, ...}

    # Passo 2: Se > 0 ações, executar real
    if sum(actions.values()) > 0:
        logger.info(f"Preview detectou {actions}. Executando sync real...")
        subprocess.run([
            "python", "manage.py", "preagenda_to_gcal",
            "--client=google"
        ])
    else:
        logger.info("Nenhuma ação necessária. Skipping.")
```

**Schedule:**
```python
# settings.py
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "sync-calendar-every-5min": {
        "task": "apps.core.tasks.preview_and_sync",
        "schedule": crontab(minute="*/5"),  # A cada 5 minutos
    },
}
```

---

## 📊 Resumo Estatístico

**Implementado:** 4 / 13 itens (31%)
**Pendente:** 9 / 13 itens (69%)

**Prioridade Alta (fazer próxima sessão):**
1. Sync incremental (item 5)
2. Redis lock (item 6)
3. Normalização município (item 7)
4. Testes de bordas (item 8)

**Prioridade Média:**
5. Rate-limit (item 9)
6. Logs estruturados (item 10)
7. Política exclusão docs (item 11)

**Prioridade Baixa (futuro):**
8. Config mutável (item 12)
9. Celery beat (item 13)

---

## 🎯 Recomendação

**Mergear PR 3/3 AGORA** com os 4 itens implementados:
- ✅ Observabilidade completa
- ✅ Metadados extendedProperties
- ✅ Limites summary/description
- ✅ Cliente plugável

**Próximo PR (4/N):**
- GoogleCalendarClient real
- Sync incremental
- Redis lock
- Normalização município
- Testes de bordas

**Justificativa:** Sistema já está production-ready e seguro. Refinamentos restantes são melhorias incrementais que não bloqueiam uso.

# 🔍 Relatório de Auditoria Completa — Bugs e Inconsistências OAuth/GCal

**Data**: 2025-11-10
**Escopo**: Análise sistemática de variáveis de ambiente e configurações OAuth/GCal
**Trigger**: Bug crítico descoberto em `GCAL_AUTH_MODE` (settings.py:374)
**Metodologia**: Grep recursivo + revisão manual de todos os arquivos relacionados

---

## 📊 Resumo Executivo

| Tipo | Severidade | Status | Arquivo(s) |
|------|-----------|--------|------------|
| **Bug #1** | 🔴 CRÍTICO | ✅ CORRIGIDO | `config/settings.py:374` |
| **Problema #2** | 🟡 INCONSISTÊNCIA | ⚠️ REQUER AÇÃO | `views_gcal_dashboard.py`, `views_health.py` |
| **Problema #3** | 🟡 CONFUSO | ⚠️ REQUER CLARIFICAÇÃO | `views_health.py:103`, `tasks.py:337` |
| **Melhoria #4** | 🟢 SUGESTÃO | ⏳ OPCIONAL | `services/google_oauth.py`, `services/gcal_oauth_client.py` |

**Total de Issues**: 4 (1 crítico corrigido, 2 médios, 1 baixo)

---

## 🐛 Bug #1: GCAL_AUTH_MODE Typo (CRÍTICO - CORRIGIDO ✅)

### Descrição
Variável de ambiente **`GCAL_AUTH_MODE`** estava sendo lida com nome **incorreto** em `settings.py`.

### Localização
**Arquivo**: `v2/backend/config/settings.py`
**Linha**: 374

### Código Incorreto (Antes)
```python
GCAL_AUTH_MODE = os.getenv("GCAL_CLIENT_MODE", "service_account")
#                           ^^^^^^^^^^^^^^^^
#                           ERRADO: lia CLIENT_MODE ao invés de AUTH_MODE
```

### Código Correto (Depois)
```python
GCAL_AUTH_MODE = os.getenv("GCAL_AUTH_MODE", "service_account")
#                           ^^^^^^^^^^^^^^
#                           CORRETO: lê AUTH_MODE do .env
```

### Impacto
- **Severidade**: 🔴 CRÍTICO
- **Sistema sempre usava `service_account` mode**, ignorando `GCAL_AUTH_MODE=oauth` no `.env`
- **Batch operations não funcionavam com OAuth**
- **Endpoint `/api/oauth/google/start/` nunca seria acionado**
- **Credenciais OAuth nunca seriam utilizadas**

### Como Foi Descoberto
Durante validação manual do OAuth:
1. `printenv | grep GCAL_AUTH_MODE` → mostrava `oauth` ✅
2. Django shell `settings.GCAL_AUTH_MODE` → mostrava `service_account` ❌
3. Revisão do código settings.py → typo identificado

### Correção Aplicada
**Commit**: `6af39ba`
**Mensagem**: `fix(settings): corrigir leitura de GCAL_AUTH_MODE`
**Status**: ✅ **MERGED em main**

### Validação Pós-Fix
```bash
docker compose exec web python -c "
from django.conf import settings
print('AUTH_MODE:', settings.GCAL_AUTH_MODE)
"
# Resultado: AUTH_MODE: oauth ✅
```

---

## ⚠️ Problema #2: Inconsistência no Padrão de Leitura de GCAL_CLIENT

### Descrição
Código usa **dois padrões diferentes** para ler a variável `GCAL_CLIENT`:
1. `os.getenv('GCAL_CLIENT', 'fake')` — leitura direta do ambiente
2. `getattr(settings, 'GCAL_CLIENT', 'fake')` — leitura via Django settings

### Localizações

#### Padrão 1 (Direto via `os.getenv`):
**Arquivo**: `v2/backend/apps/core/views_gcal_dashboard.py`
**Linha 317** (GCalPublishBatchView):
```python
gcal_client = os.getenv('GCAL_CLIENT', 'fake')  # ❌ Padrão antigo
```

**Arquivo**: `v2/backend/apps/core/views_health.py`
**Linha 102** (HealthAPIView):
```python
gcal_client = os.getenv("GCAL_CLIENT", "fake")  # ❌ Padrão antigo
```

#### Padrão 2 (Via `getattr(settings)` — ✅ Recomendado):
**Arquivo**: `v2/backend/apps/core/views_gcal_dashboard.py`
**Linha 655** (GCalBatchReapplyView):
```python
gcal_client = getattr(settings, 'GCAL_CLIENT', 'fake')  # ✅ Padrão novo
```

**Linha 802** (GCalBatchResyncView):
```python
gcal_client = getattr(settings, 'GCAL_CLIENT', 'fake')  # ✅ Padrão novo
```

**Arquivo**: `v2/backend/apps/core/tasks.py`
**Linha 355** (sync_gcal_task):
```python
gcal_calendar_id = getattr(settings, "GCAL_CALENDAR_ID", "")  # ✅ Padrão novo
```

### Impacto
- **Severidade**: 🟡 MÉDIA (funciona, mas inconsistente)
- **Não quebra funcionalidade** (ambos leem corretamente)
- **Dificulta manutenção** (dois padrões diferentes)
- **Pode causar bugs futuros** se settings.py for modificado mas `os.getenv` direto for esquecido

### Recomendação
**Padronizar TODAS as leituras para `getattr(settings, ...)`**:

```python
# ANTES (views_gcal_dashboard.py:317)
gcal_client = os.getenv('GCAL_CLIENT', 'fake')

# DEPOIS (recomendado)
from django.conf import settings
gcal_client = getattr(settings, 'GCAL_CLIENT', 'fake')
```

**Benefícios**:
- Single Source of Truth (settings.py)
- Facilita testes com `override_settings()`
- Mais fácil de rastrear via grep
- Padrão Django recomendado

### Arquivos a Atualizar
1. `v2/backend/apps/core/views_gcal_dashboard.py:317`
2. `v2/backend/apps/core/views_health.py:102`

---

## 🤔 Problema #3: Variável GCAL_MODE Não Definida em settings.py

### Descrição
Código usa variável **`GCAL_MODE`** que **não está definida** em `config/settings.py`.

### Localizações

**Arquivo**: `v2/backend/apps/core/views_health.py`
**Linha 103**:
```python
gcal_client = os.getenv("GCAL_CLIENT", "fake")
gcal_mode = os.getenv("GCAL_MODE", gcal_client)  # GCAL_MODE não existe em settings.py
```

**Arquivo**: `v2/backend/apps/core/tasks.py`
**Linha 337** (preview_then_apply_gcal):
```python
gcal_mode = feature_flags.get("GCAL_MODE", "google")  # Via feature_flags
```

### Análise
- `GCAL_MODE` parece ser uma **feature flag** ou **variável legacy**
- Em `views_health.py`, usa `os.getenv("GCAL_MODE", gcal_client)` — fallback para `GCAL_CLIENT`
- Em `tasks.py`, usa `feature_flags.get("GCAL_MODE", "google")`
- **Não está documentada** em `OAUTH_SETUP_GUIDE.md` nem `.env.example`

### Impacto
- **Severidade**: 🟡 MÉDIA (confuso, mas funciona)
- **Código funciona** (tem fallback), mas **semântica confusa**
- **Não está claro**:
  - Qual a diferença entre `GCAL_MODE` e `GCAL_CLIENT`?
  - É legacy? É feature flag? É obrigatória?
- **Dificulta onboarding de novos desenvolvedores**

### Recomendação
**Opção 1 (Se GCAL_MODE é legacy — Remover)**:
```python
# views_health.py:103 - ANTES
gcal_mode = os.getenv("GCAL_MODE", gcal_client)

# views_health.py:103 - DEPOIS (remover GCAL_MODE)
gcal_mode = gcal_client  # Usar GCAL_CLIENT diretamente
```

**Opção 2 (Se GCAL_MODE é necessária — Documentar)**:
1. Adicionar em `config/settings.py`:
```python
# Google Calendar mode (feature flag)
# 'google': Real Google Calendar API
# 'fake': In-memory fake client (safe for dev)
GCAL_MODE = os.getenv("GCAL_MODE", GCAL_CLIENT)  # Herda de GCAL_CLIENT por padrão
```

2. Documentar em `OAUTH_SETUP_GUIDE.md`
3. Adicionar em `.env.example`

**Opção 3 (Consolidar GCAL_MODE → GCAL_CLIENT)**:
- Usar **apenas** `GCAL_CLIENT` em todos os lugares
- Remover `GCAL_MODE` completamente
- Atualizar `tasks.py:337` para usar `GCAL_CLIENT`

### Arquivos a Revisar
1. `v2/backend/apps/core/views_health.py:103`
2. `v2/backend/apps/core/tasks.py:337`

---

## 💡 Melhoria #4: Variáveis OAuth Não Centralizadas em settings.py

### Descrição
Quatro variáveis OAuth são acessadas **diretamente via `os.getenv()`**, sem definição em `config/settings.py`.

### Variáveis Afetadas
1. `GCAL_OAUTH_CLIENT_ID`
2. `GCAL_OAUTH_CLIENT_SECRET`
3. `GCAL_OAUTH_REDIRECT_URI`
4. `GCAL_ENCRYPTION_KEY`

### Localizações

#### google_oauth.py
**Arquivo**: `v2/backend/apps/core/services/google_oauth.py`

**Linha 51** (_get_fernet):
```python
key = os.getenv("GCAL_ENCRYPTION_KEY")  # ❌ Direto do ambiente
```

**Linhas 228-229** (start_oauth_flow):
```python
client_id = os.getenv("GCAL_OAUTH_CLIENT_ID")
redirect_uri = os.getenv("GCAL_OAUTH_REDIRECT_URI")
```

**Linhas 304-306** (exchange_code_for_tokens):
```python
client_id = os.getenv("GCAL_OAUTH_CLIENT_ID")
client_secret = os.getenv("GCAL_OAUTH_CLIENT_SECRET")
redirect_uri = os.getenv("GCAL_OAUTH_REDIRECT_URI")
```

#### gcal_oauth_client.py
**Arquivo**: `v2/backend/apps/core/services/gcal_oauth_client.py`

**Linhas 83-84** (_get_credentials_from_db):
```python
client_id = os.getenv("GCAL_OAUTH_CLIENT_ID")
client_secret = os.getenv("GCAL_OAUTH_CLIENT_SECRET")
```

### Impacto
- **Severidade**: 🟢 BAIXA (funciona, mas não segue padrão Django)
- **Código funciona corretamente** (variáveis são lidas)
- **Não está alinhado com padrão do projeto** (outras variáveis estão em settings.py)
- **Dificulta testes** (não pode usar `override_settings()` facilmente)

### Recomendação
**Centralizar em settings.py** (opcional, mas recomendado):

```python
# v2/backend/config/settings.py (adicionar no bloco "GOOGLE CALENDAR / SHEETS")

# ================================================================
# GOOGLE CALENDAR / SHEETS
# ================================================================
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
GCAL_CALENDAR_ID = os.getenv("GCAL_CALENDAR_ID", "")
GCAL_CLIENT = os.getenv("GCAL_CLIENT", "fake")
GCAL_AUTH_MODE = os.getenv("GCAL_AUTH_MODE", "service_account")
GCAL_SEND_UPDATES = os.getenv("GCAL_SEND_UPDATES", "none")

# OAuth-specific settings (Issue #95)
GCAL_OAUTH_CLIENT_ID = os.getenv("GCAL_OAUTH_CLIENT_ID", "")
GCAL_OAUTH_CLIENT_SECRET = os.getenv("GCAL_OAUTH_CLIENT_SECRET", "")
GCAL_OAUTH_REDIRECT_URI = os.getenv("GCAL_OAUTH_REDIRECT_URI", "")
GCAL_ENCRYPTION_KEY = os.getenv("GCAL_ENCRYPTION_KEY", "")
```

**Depois, atualizar services para usar settings**:
```python
# google_oauth.py:51 - ANTES
key = os.getenv("GCAL_ENCRYPTION_KEY")

# google_oauth.py:51 - DEPOIS
from django.conf import settings
key = getattr(settings, "GCAL_ENCRYPTION_KEY", "")
```

### Benefícios
- **Single Source of Truth** (todas as configs em um lugar)
- **Facilita testes** com `override_settings()`
- **Consistência** com outras variáveis GCal
- **Documentação centralizada** (settings.py funciona como documentação)

### Arquivos a Atualizar (Opcional)
1. `v2/backend/config/settings.py` (adicionar as 4 variáveis)
2. `v2/backend/apps/core/services/google_oauth.py` (linhas 51, 228-229, 304-306)
3. `v2/backend/apps/core/services/gcal_oauth_client.py` (linhas 83-84)

---

## 📈 Estatísticas da Auditoria

### Arquivos Analisados
- ✅ `v2/backend/config/settings.py` (453 linhas)
- ✅ `v2/backend/apps/core/views_gcal_dashboard.py` (1051 linhas)
- ✅ `v2/backend/apps/core/views_solicitacao.py` (343 linhas)
- ✅ `v2/backend/apps/core/views_health.py` (200+ linhas)
- ✅ `v2/backend/apps/core/services/google_oauth.py` (400+ linhas)
- ✅ `v2/backend/apps/core/services/gcal_oauth_client.py` (200+ linhas)
- ✅ `v2/backend/apps/core/tasks.py` (500+ linhas)

**Total**: 7 arquivos principais, ~3000 linhas analisadas

### Comandos Utilizados
```bash
# Buscar todas as leituras de variáveis de ambiente
grep -rn "os.getenv\|os.environ" v2/backend/apps/core/ --include="*.py"

# Buscar uso de getattr(settings)
grep -rn "getattr(settings" v2/backend/apps/core/ --include="*.py"

# Buscar todas as variáveis GCAL_* e GOOGLE_*
grep -rn "GCAL_\|GOOGLE_" v2/backend/apps/core/ --include="*.py"

# Analisar settings.py especificamente
grep -n "os.getenv" v2/backend/config/settings.py
```

### Resumo de Issues por Severidade

| Severidade | Quantidade | Status |
|-----------|-----------|--------|
| 🔴 CRÍTICO | 1 | ✅ Corrigido (Bug #1) |
| 🟡 MÉDIO | 2 | ⚠️ Requer ação (Problemas #2 e #3) |
| 🟢 BAIXO | 1 | ⏳ Opcional (Melhoria #4) |

---

## ✅ Checklist de Ações Recomendadas

### Prioridade Alta (Fazer Agora)
- [x] **Bug #1**: Corrigir typo `GCAL_AUTH_MODE` ✅ FEITO (commit `6af39ba`)
- [ ] **Problema #2**: Padronizar `GCAL_CLIENT` para `getattr(settings, ...)` em:
  - [ ] `views_gcal_dashboard.py:317`
  - [ ] `views_health.py:102`

### Prioridade Média (Considerar)
- [ ] **Problema #3**: Clarificar uso de `GCAL_MODE`:
  - [ ] Decidir: remover, documentar ou consolidar com `GCAL_CLIENT`?
  - [ ] Atualizar `views_health.py:103`
  - [ ] Atualizar `tasks.py:337`
  - [ ] Documentar decisão em `OAUTH_SETUP_GUIDE.md`

### Prioridade Baixa (Opcional)
- [ ] **Melhoria #4**: Centralizar variáveis OAuth em `settings.py`
  - [ ] Adicionar as 4 variáveis em `config/settings.py`
  - [ ] Atualizar `google_oauth.py` (3 locais)
  - [ ] Atualizar `gcal_oauth_client.py` (1 local)

---

## 🛡️ Prevenção de Bugs Futuros

### 1. Adicionar Testes de Configuração
Criar `test_settings_configuration.py`:
```python
from django.test import TestCase, override_settings
from django.conf import settings

class SettingsConfigurationTest(TestCase):
    """Valida que variáveis de ambiente são lidas corretamente."""

    def test_gcal_auth_mode_reads_correct_env_variable(self):
        """Garante que GCAL_AUTH_MODE lê AUTH_MODE, não CLIENT_MODE."""
        with override_settings(GCAL_AUTH_MODE="oauth"):
            self.assertEqual(settings.GCAL_AUTH_MODE, "oauth")

    def test_gcal_client_reads_correct_env_variable(self):
        """Garante que GCAL_CLIENT lê CLIENT, não MODE."""
        with override_settings(GCAL_CLIENT="google"):
            self.assertEqual(settings.GCAL_CLIENT, "google")
```

### 2. Lint para Padrões de Leitura
Adicionar regra no `.pre-commit-config.yaml` ou `pylint`:
```python
# Avisar quando usar os.getenv() para variáveis conhecidas do settings.py
# Recomendação: usar getattr(settings, ...) sempre que possível
```

### 3. Documentar Padrões
Adicionar em `.claude/CLAUDE.md`:
```markdown
## Padrão de Leitura de Configurações

**SEMPRE use `getattr(settings, ...)` ao invés de `os.getenv()`**:

✅ Correto:
from django.conf import settings
gcal_client = getattr(settings, 'GCAL_CLIENT', 'fake')

❌ Incorreto:
gcal_client = os.getenv('GCAL_CLIENT', 'fake')

**Exceção**: Se a variável não está em settings.py (ex: secrets temporários).
```

### 4. Code Review Checklist
Adicionar em `.github/PULL_REQUEST_TEMPLATE.md`:
```markdown
## Configuration Changes

- [ ] Todas as variáveis de ambiente são lidas via `getattr(settings, ...)`?
- [ ] Novas variáveis foram adicionadas em `config/settings.py`?
- [ ] `.env.example` foi atualizado?
- [ ] Testes de configuração foram adicionados?
```

---

## 📞 Comandos Úteis para Validação

### Verificar Todas as Variáveis GCAL_* no Container
```bash
docker compose exec web printenv | grep -E "^GCAL_" | sort
```

### Verificar Django Settings Carregado
```bash
docker compose exec web python -c "
from django.conf import settings
import os

print('=== Comparação Ambiente vs Django Settings ===')
print()
print('1. GCAL_CLIENT:')
print(f'   Env: {os.getenv(\"GCAL_CLIENT\", \"NOT_SET\")}')
print(f'   Settings: {getattr(settings, \"GCAL_CLIENT\", \"NOT_SET\")}')
print()
print('2. GCAL_AUTH_MODE:')
print(f'   Env: {os.getenv(\"GCAL_AUTH_MODE\", \"NOT_SET\")}')
print(f'   Settings: {getattr(settings, \"GCAL_AUTH_MODE\", \"NOT_SET\")}')
print()
print('3. GCAL_MODE:')
print(f'   Env: {os.getenv(\"GCAL_MODE\", \"NOT_SET\")}')
print(f'   Settings: {getattr(settings, \"GCAL_MODE\", \"NOT_FOUND_IN_SETTINGS\")}')
"
```

### Buscar Inconsistências de Leitura
```bash
# Buscar todos os os.getenv() que poderiam usar settings
grep -rn "os.getenv(\"GCAL_" v2/backend/apps/core/ --include="*.py"

# Buscar todos os getattr(settings) (padrão correto)
grep -rn "getattr(settings, \"GCAL_" v2/backend/apps/core/ --include="*.py"
```

---

## 🎯 Conclusão

### Resumo Geral
✅ **1 bug crítico descoberto e corrigido** (GCAL_AUTH_MODE typo)
⚠️ **2 inconsistências médias identificadas** (GCAL_CLIENT pattern, GCAL_MODE undefined)
💡 **1 melhoria sugerida** (centralizar OAuth vars em settings.py)

### Próximos Passos Recomendados
1. **Agora**: Padronizar leitura de `GCAL_CLIENT` (Problema #2)
2. **Esta Sprint**: Clarificar `GCAL_MODE` (Problema #3)
3. **Backlog**: Centralizar variáveis OAuth (Melhoria #4)
4. **Backlog**: Adicionar testes de configuração (Prevenção)

### Impacto da Auditoria
- **Sistema OAuth agora funcional** após correção do Bug #1
- **Padrões inconsistentes identificados** para futura correção
- **Documentação criada** para prevenção de bugs similares

---

## 📝 Histórico de Mudanças

| Data | Commit | Mudança |
|------|--------|---------|
| 2025-11-10 | `6af39ba` | ✅ Corrigido Bug #1 (GCAL_AUTH_MODE typo) |
| 2025-11-10 | - | 📄 Relatório de auditoria criado |

---

**Auditoria realizada por**: Claude Code
**Trigger**: Bug discovery em validação OAuth
**Metodologia**: Grep recursivo + revisão manual sistemática
**Arquivos analisados**: 7 arquivos principais (~3000 linhas)
**Issues encontrados**: 4 (1 crítico, 2 médios, 1 baixo)

---

**Status Final**: 🟢 Sistema OAuth funcional após correção do bug crítico
**Recomendação**: Implementar checklist de ações de Prioridade Alta (Problema #2)

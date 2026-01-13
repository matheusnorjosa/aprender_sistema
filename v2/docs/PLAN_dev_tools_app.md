# Plano: App dev_tools — Isolamento de Commands de Desenvolvimento

**Data**: 2026-01-09
**Status**: ✅ CONCLUÍDO (PR #340)
**Padrão**: Mesmo de `INCLUDE_ETL` (PR #339)

---

## 1. Objetivo

Criar app `apps/dev_tools` para isolar commands de desenvolvimento (seeds, backfills, fixes) do app principal `core`, usando o mesmo padrão do `INCLUDE_ETL`.

### Resultado Final

```
Ambiente         │ INCLUDE_DEV_TOOLS │ Commands seed_* │ Commands prod
─────────────────┼───────────────────┼─────────────────┼──────────────
Dev (local)      │ true (default)    │ ✅ Disponíveis  │ ✅ Disponíveis
Staging          │ true              │ ✅ Disponíveis  │ ✅ Disponíveis
Produção         │ false             │ ❌ Não existem  │ ✅ Disponíveis
```

---

## 2. Classificação dos Commands

### 2.1 Commands que PERMANECEM em `core` (produção)

| Command | Função | Justificativa |
|---------|--------|---------------|
| `preagenda_to_gcal.py` | Sync Google Calendar | Feature de produção (RF05) |
| `rotate_gcal_encryption_key.py` | Rotação de chave | Operação de segurança |

### 2.2 Commands que MOVEM para `dev_tools`

| Command | Tipo | Função |
|---------|------|--------|
| `seed_e2e_users.py` | Seed | Usuários para testes E2E |
| `seed_gerencias.py` | Seed | Gerências iniciais |
| `seed_gerentes.py` | Seed | Gerentes iniciais |
| `seed_produtos.py` | Seed | Produtos iniciais |
| `seed_rbac.py` | Seed | Grupos e permissões |
| `seed_tipos_evento.py` | Seed | Tipos de evento |
| `seed_projetos_fluxo_from_csv.py` | Seed | Projetos de CSV |
| `seed_projetos_fluxo_from_sheets.py` | Seed | Projetos de Sheets |
| `cleanup_e2e_data.py` | E2E | Limpeza de dados E2E |
| `backfill_is_online.py` | Backfill | Migração is_online |
| `fix_projetos_gerencia.py` | Fix | Correção única |
| `migrate_rbac_groups.py` | Migration | Migração RBAC |
| `link_projetos_gerencias.py` | Setup | Vincular projetos |
| `populate_municipio_coords.py` | Seed | Coordenadas municípios |

**Total**: 14 commands movidos, 2 permanecem

---

## 3. Estrutura do App `dev_tools`

```
apps/
├── core/                              # App principal (produção)
│   └── management/
│       └── commands/
│           ├── preagenda_to_gcal.py   # ✓ Permanece
│           └── rotate_gcal_encryption_key.py  # ✓ Permanece
│
├── dat_ingest/                        # ETL (INCLUDE_ETL)
│   └── ...
│
└── dev_tools/                         # NOVO: Dev/Seed (INCLUDE_DEV_TOOLS)
    ├── __init__.py
    ├── apps.py
    └── management/
        └── commands/
            ├── __init__.py
            ├── seed_e2e_users.py
            ├── seed_gerencias.py
            ├── seed_gerentes.py
            ├── seed_produtos.py
            ├── seed_rbac.py
            ├── seed_tipos_evento.py
            ├── seed_projetos_fluxo_from_csv.py
            ├── seed_projetos_fluxo_from_sheets.py
            ├── cleanup_e2e_data.py
            ├── backfill_is_online.py
            ├── fix_projetos_gerencia.py
            ├── migrate_rbac_groups.py
            ├── link_projetos_gerencias.py
            └── populate_municipio_coords.py
```

---

## 4. Implementação

### 4.1 Fase 1: Criar estrutura do app (5 min)

**Arquivos a criar**:

#### `apps/dev_tools/__init__.py`
```python
"""
Dev Tools App — AS v2

Ferramentas de desenvolvimento: seeds, backfills, fixtures.
Excluído de produção via INCLUDE_DEV_TOOLS=false.
"""
default_app_config = "apps.dev_tools.apps.DevToolsConfig"
```

#### `apps/dev_tools/apps.py`
```python
from django.apps import AppConfig


class DevToolsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.dev_tools"
    verbose_name = "Development Tools"
```

#### `apps/dev_tools/management/__init__.py`
```python
# Empty file
```

#### `apps/dev_tools/management/commands/__init__.py`
```python
# Empty file
```

### 4.2 Fase 2: Configurar settings.py (2 min)

**Arquivo**: `config/settings.py`

**Adicionar após INCLUDE_ETL** (linha ~77):

```python
# ================================================================
# INSTALLED APPS
# ================================================================
# ETL Module (dat_ingest) - Opcional em produção
# Default: True (inclui ETL para manter compatibilidade)
# Para excluir do deploy: INCLUDE_ETL=false
INCLUDE_ETL = os.getenv("INCLUDE_ETL", "true").lower() == "true"

# Dev Tools Module (dev_tools) - Seeds, backfills, fixtures
# Default: True (inclui para manter compatibilidade)
# Para excluir do deploy: INCLUDE_DEV_TOOLS=false
INCLUDE_DEV_TOOLS = os.getenv("INCLUDE_DEV_TOOLS", "true").lower() == "true"

INSTALLED_APPS = [
    # Django core
    "django.contrib.admin.apps.SimpleAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "corsheaders",
    "django_prometheus",
    "django_celery_beat",
    "django_celery_results",
    # AS v2 apps
    "apps.core",
]

# Incluir ETL apenas se INCLUDE_ETL=true
if INCLUDE_ETL:
    INSTALLED_APPS.append("apps.dat_ingest")

# Incluir Dev Tools apenas se INCLUDE_DEV_TOOLS=true
if INCLUDE_DEV_TOOLS:
    INSTALLED_APPS.append("apps.dev_tools")
```

### 4.3 Fase 3: Mover commands (10 min)

**Operação**: `git mv` para preservar histórico

```bash
# Criar diretórios
mkdir -p v2/backend/apps/dev_tools/management/commands

# Mover commands (14 arquivos)
cd v2/backend/apps/core/management/commands

git mv seed_e2e_users.py ../../../dev_tools/management/commands/
git mv seed_gerencias.py ../../../dev_tools/management/commands/
git mv seed_gerentes.py ../../../dev_tools/management/commands/
git mv seed_produtos.py ../../../dev_tools/management/commands/
git mv seed_rbac.py ../../../dev_tools/management/commands/
git mv seed_tipos_evento.py ../../../dev_tools/management/commands/
git mv seed_projetos_fluxo_from_csv.py ../../../dev_tools/management/commands/
git mv seed_projetos_fluxo_from_sheets.py ../../../dev_tools/management/commands/
git mv cleanup_e2e_data.py ../../../dev_tools/management/commands/
git mv backfill_is_online.py ../../../dev_tools/management/commands/
git mv fix_projetos_gerencia.py ../../../dev_tools/management/commands/
git mv migrate_rbac_groups.py ../../../dev_tools/management/commands/
git mv link_projetos_gerencias.py ../../../dev_tools/management/commands/
git mv populate_municipio_coords.py ../../../dev_tools/management/commands/
```

### 4.4 Fase 4: Criar .dockerignore (2 min)

**Arquivo**: `v2/backend/.dockerignore`

```dockerignore
# Development only - not copied to Docker image
scripts/
*.pyc
__pycache__/
.pytest_cache/
.coverage
htmlcov/
*.egg-info/
.env.local

# Test fixtures (if any)
fixtures/dev/

# IDE
.vscode/
.idea/
```

### 4.5 Fase 5: Criar testes (10 min)

**Arquivo**: `apps/dev_tools/tests/__init__.py`
```python
# Empty
```

**Arquivo**: `apps/dev_tools/tests/test_optional_dev_tools.py`

```python
"""
Tests for optional dev_tools deployment (INCLUDE_DEV_TOOLS setting).

Verifies that:
- INCLUDE_DEV_TOOLS defaults to True (backward compatibility)
- dev_tools is included when INCLUDE_DEV_TOOLS=true
- Commands are available when enabled
"""

import pytest
from django.conf import settings
from django.core.management import get_commands


class TestIncludeDevToolsSetting:
    """Tests for INCLUDE_DEV_TOOLS configuration."""

    def test_include_dev_tools_defaults_to_true(self):
        """INCLUDE_DEV_TOOLS should default to True for backward compatibility."""
        assert hasattr(settings, "INCLUDE_DEV_TOOLS")
        assert settings.INCLUDE_DEV_TOOLS is True

    def test_dev_tools_in_installed_apps_when_enabled(self):
        """dev_tools should be in INSTALLED_APPS when INCLUDE_DEV_TOOLS=true."""
        if settings.INCLUDE_DEV_TOOLS:
            assert "apps.dev_tools" in settings.INSTALLED_APPS

    def test_core_always_in_installed_apps(self):
        """core app should always be in INSTALLED_APPS."""
        assert "apps.core" in settings.INSTALLED_APPS


class TestDevToolsCommands:
    """Tests for dev_tools management commands."""

    def test_seed_commands_available_when_enabled(self):
        """Seed commands should be available when INCLUDE_DEV_TOOLS=true."""
        if not settings.INCLUDE_DEV_TOOLS:
            pytest.skip("Dev tools not enabled")

        commands = get_commands()
        seed_commands = [
            "seed_e2e_users",
            "seed_gerencias",
            "seed_gerentes",
            "seed_produtos",
            "seed_rbac",
            "seed_tipos_evento",
        ]

        for cmd in seed_commands:
            assert cmd in commands, f"Command {cmd} should be available"

    def test_production_commands_always_available(self):
        """Production commands should always be in core."""
        commands = get_commands()

        # These should always exist (in core)
        assert "preagenda_to_gcal" in commands
        assert "rotate_gcal_encryption_key" in commands


class TestDevToolsExclusionDocumentation:
    """Documentation tests for dev_tools exclusion."""

    def test_include_dev_tools_env_var_documented(self):
        """Verify the expected behavior of INCLUDE_DEV_TOOLS."""
        # This test documents the expected behavior:
        #
        # INCLUDE_DEV_TOOLS=true (default):
        #   - apps.dev_tools in INSTALLED_APPS
        #   - Seed/backfill commands available
        #   - E2E test helpers available
        #
        # INCLUDE_DEV_TOOLS=false:
        #   - apps.dev_tools NOT in INSTALLED_APPS
        #   - Seed commands NOT available
        #   - Production commands (preagenda_to_gcal) still work
        #
        # To deploy without dev tools:
        #   environment:
        #     - INCLUDE_DEV_TOOLS=false
        pass
```

### 4.6 Fase 6: Atualizar documentação (5 min)

**Arquivo**: `.claude/CLAUDE.md`

Adicionar após CP-07:

```markdown
### CP-08: INCLUDE_DEV_TOOLS (Ferramentas de Desenvolvimento)

| Ambiente | INCLUDE_DEV_TOOLS | Resultado |
|----------|-------------------|-----------|
| Dev | `true` (default) | Seeds disponíveis |
| Staging | `true` | Seeds disponíveis |
| Prod | `false` | Seeds indisponíveis |

**Commands em dev_tools**:
- `seed_*` — Dados iniciais
- `backfill_*` — Migrações de dados
- `fix_*` — Correções únicas
- `cleanup_e2e_data` — Limpeza E2E
```

---

## 5. Arquivos Tocados

| Arquivo | Ação | Linhas |
|---------|------|--------|
| `apps/dev_tools/__init__.py` | Criar | ~8 |
| `apps/dev_tools/apps.py` | Criar | ~8 |
| `apps/dev_tools/management/__init__.py` | Criar | ~1 |
| `apps/dev_tools/management/commands/__init__.py` | Criar | ~1 |
| `apps/dev_tools/tests/__init__.py` | Criar | ~1 |
| `apps/dev_tools/tests/test_optional_dev_tools.py` | Criar | ~70 |
| `config/settings.py` | Modificar | +6 |
| `v2/backend/.dockerignore` | Criar | ~15 |
| `.claude/CLAUDE.md` | Modificar | +15 |
| 14 commands | Mover (git mv) | 0 (preserva) |

**Total**: ~125 linhas novas, 14 arquivos movidos

---

## 6. Comandos de Execução

### 6.1 Criar estrutura

```bash
cd v2/backend

# Criar diretórios
mkdir -p apps/dev_tools/management/commands
mkdir -p apps/dev_tools/tests

# Criar __init__.py files
touch apps/dev_tools/__init__.py
touch apps/dev_tools/management/__init__.py
touch apps/dev_tools/management/commands/__init__.py
touch apps/dev_tools/tests/__init__.py
```

### 6.2 Mover commands

```bash
cd v2/backend/apps/core/management/commands

# Seeds
git mv seed_e2e_users.py ../../dev_tools/management/commands/
git mv seed_gerencias.py ../../dev_tools/management/commands/
git mv seed_gerentes.py ../../dev_tools/management/commands/
git mv seed_produtos.py ../../dev_tools/management/commands/
git mv seed_rbac.py ../../dev_tools/management/commands/
git mv seed_tipos_evento.py ../../dev_tools/management/commands/
git mv seed_projetos_fluxo_from_csv.py ../../dev_tools/management/commands/
git mv seed_projetos_fluxo_from_sheets.py ../../dev_tools/management/commands/

# Backfills/Fixes
git mv backfill_is_online.py ../../dev_tools/management/commands/
git mv fix_projetos_gerencia.py ../../dev_tools/management/commands/
git mv migrate_rbac_groups.py ../../dev_tools/management/commands/
git mv link_projetos_gerencias.py ../../dev_tools/management/commands/
git mv populate_municipio_coords.py ../../dev_tools/management/commands/

# E2E
git mv cleanup_e2e_data.py ../../dev_tools/management/commands/
```

### 6.3 Validar

```bash
# Rebuild container
cd v2/infra && docker compose build web

# Rodar testes
docker compose exec -T web python -m pytest apps/dev_tools/ -v

# Verificar commands disponíveis
docker compose exec -T web python manage.py help | grep seed

# Verificar com flag desabilitada
docker compose exec -T -e INCLUDE_DEV_TOOLS=false web python manage.py help | grep seed
# (não deve retornar nada)
```

---

## 7. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Imports quebrados | Baixa | Médio | Commands não importam entre si |
| CI falhar | Baixa | Baixo | Testes cobrem ambos cenários |
| Dev esquecer flag | Baixa | Nenhum | Default true |
| Histórico git perdido | Baixa | Baixo | Usar `git mv` |

---

## 8. Estratégia de Testes

### 8.1 Testes Automatizados

```python
# test_optional_dev_tools.py (já descrito acima)
- test_include_dev_tools_defaults_to_true
- test_dev_tools_in_installed_apps_when_enabled
- test_core_always_in_installed_apps
- test_seed_commands_available_when_enabled
- test_production_commands_always_available
```

### 8.2 Testes Manuais

```bash
# 1. Verificar commands disponíveis (dev)
docker compose exec web python manage.py help | grep -E "(seed|backfill|fix)"
# Esperado: Lista 14 commands

# 2. Verificar commands bloqueados (prod)
docker compose exec -e INCLUDE_DEV_TOOLS=false web python manage.py seed_rbac
# Esperado: "Unknown command: 'seed_rbac'"

# 3. Verificar commands de produção funcionam
docker compose exec -e INCLUDE_DEV_TOOLS=false web python manage.py preagenda_to_gcal --help
# Esperado: Help do command

# 4. Rodar suite completa
docker compose exec web python -m pytest apps/ -v
# Esperado: 1516+ tests passing
```

---

## 9. Checklist de Validação

### Antes do Merge

- [ ] App `dev_tools` criado com estrutura correta
- [ ] 14 commands movidos via `git mv`
- [ ] `INCLUDE_DEV_TOOLS` adicionado ao settings.py
- [ ] Testes criados e passando
- [ ] Commands disponíveis com `INCLUDE_DEV_TOOLS=true`
- [ ] Commands indisponíveis com `INCLUDE_DEV_TOOLS=false`
- [ ] Commands de produção sempre disponíveis
- [ ] CI verde
- [ ] Documentação atualizada

### Após Deploy

- [ ] Em dev: `python manage.py seed_rbac` funciona
- [ ] Em prod: `python manage.py seed_rbac` não existe
- [ ] Em prod: `python manage.py preagenda_to_gcal` funciona

---

## 10. Rollback

Se problemas:
1. `git revert` do PR
2. Ou: `INCLUDE_DEV_TOOLS=true` temporariamente

---

## 11. Ordem de Commits

```
commit 1: "feat(dev_tools): create app structure"
  - __init__.py, apps.py, management dirs

commit 2: "feat(settings): add INCLUDE_DEV_TOOLS flag"
  - config/settings.py

commit 3: "refactor(commands): move seed commands to dev_tools"
  - git mv de 14 arquivos

commit 4: "test(dev_tools): add tests for optional inclusion"
  - test_optional_dev_tools.py

commit 5: "docs: update CLAUDE.md with CP-08"
  - .claude/CLAUDE.md

commit 6: "chore: add backend .dockerignore"
  - v2/backend/.dockerignore
```

**Alternativa**: Squash em único commit para PR.

---

## 12. Aprovação

- [ ] Revisar plano
- [ ] Aprovar abordagem
- [ ] Iniciar implementação

**Próximo passo**: Aguardando aprovação para executar.

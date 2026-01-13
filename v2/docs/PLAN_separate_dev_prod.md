# Plano: Separação Dev/Prod — Componentes de Desenvolvimento

**Data**: 2026-01-09
**Status**: ✅ CONCLUÍDO (PR #339)
**Nota**: Implementado como CP-08 (INCLUDE_DEV_TOOLS)

---

## 1. Objetivo

Separar componentes de desenvolvimento dos componentes de produção, criando flags de controle que permitem:
- **Dev**: Tudo disponível (seeds, tools, scripts)
- **Prod**: Apenas o necessário para rodar a aplicação

**Princípio**: Preservar tudo, não excluir — apenas desvincular.

---

## 2. Análise do Estado Atual

### 2.1 Componentes Identificados para Separação

| Componente | Localização | Tipo | Ação |
|------------|-------------|------|------|
| **ipython, pgcli, pytest-watch** | Dockerfile:17-27 | Deps | Multi-stage build |
| **seed_e2e_users** | commands/ | Cmd | Flag INCLUDE_SEED_COMMANDS |
| **cleanup_e2e_data** | commands/ | Cmd | Flag INCLUDE_SEED_COMMANDS |
| **seed_gerencias** | commands/ | Cmd | Flag INCLUDE_SEED_COMMANDS |
| **seed_gerentes** | commands/ | Cmd | Flag INCLUDE_SEED_COMMANDS |
| **seed_produtos** | commands/ | Cmd | Flag INCLUDE_SEED_COMMANDS |
| **seed_rbac** | commands/ | Cmd | Flag INCLUDE_SEED_COMMANDS |
| **seed_tipos_evento** | commands/ | Cmd | Flag INCLUDE_SEED_COMMANDS |
| **seed_projetos_fluxo_*** | commands/ | Cmd | Flag INCLUDE_SEED_COMMANDS |
| **backfill_is_online** | commands/ | Cmd | Flag (migração concluída) |
| **fix_projetos_gerencia** | commands/ | Cmd | Flag (migração concluída) |
| **migrate_rbac_groups** | commands/ | Cmd | Flag (migração concluída) |
| **link_projetos_gerencias** | commands/ | Cmd | Flag INCLUDE_SEED_COMMANDS |
| **populate_municipio_coords** | commands/ | Cmd | Flag INCLUDE_SEED_COMMANDS |
| **scripts/*.py** | backend/scripts/ | Scripts | Excluir do Docker prod |
| **CREATE_SUPERUSER** | entrypoint.sh | Flag | Já existe, documentar |

### 2.2 Dependências que Permanecem em Prod

Pacotes necessários mesmo sem ETL (usados por core):
- `pandas` — Usado em views de relatórios
- `openpyxl` — Export de dados
- Verificar se podem ser opcionais

---

## 3. Arquitetura da Solução

### 3.1 Nova Flag: INCLUDE_SEED_COMMANDS

```python
# config/settings.py
INCLUDE_SEED_COMMANDS = os.getenv("INCLUDE_SEED_COMMANDS", "true").lower() == "true"
```

| Ambiente | INCLUDE_SEED_COMMANDS | Resultado |
|----------|----------------------|-----------|
| Dev | `true` (default) | Commands disponíveis |
| Staging | `true` | Commands disponíveis |
| Prod | `false` | Commands bloqueados |

### 3.2 Dockerfile Multi-Stage

```dockerfile
# Stage 1: Base (produção)
FROM python:3.12-slim AS base
COPY requirements.txt .
RUN pip install -r requirements.txt
# ... código da aplicação

# Stage 2: Dev (estende base)
FROM base AS dev
RUN pip install ipython pgcli pytest-watch
# ... ferramentas dev

# Build:
# docker build --target base -t app:prod .
# docker build --target dev -t app:dev .
```

### 3.3 Estrutura de Diretórios

```
v2/backend/
├── apps/                      # → Prod ✓
├── config/                    # → Prod ✓
├── scripts/                   # → Dev only (excluir do COPY)
│   ├── check_data.py
│   ├── validate_etl.py
│   └── auditoria_planilhas.py
└── requirements.txt           # → Prod ✓
└── requirements-dev.txt       # → Dev only
```

---

## 4. Plano de Implementação

### Fase 1: Flag INCLUDE_SEED_COMMANDS (PR #340-A)

**Arquivos a modificar**:

1. **`config/settings.py`** (+5 linhas)
   - Adicionar `INCLUDE_SEED_COMMANDS` após `INCLUDE_ETL`

2. **`apps/core/management/commands/base.py`** (novo arquivo, ~40 linhas)
   - Criar `DevOnlyCommand` base class
   - Verificar flag no `handle()`

3. **Commands a modificar** (13 arquivos):
   - `seed_e2e_users.py` — herdar de DevOnlyCommand
   - `cleanup_e2e_data.py` — herdar de DevOnlyCommand
   - `seed_gerencias.py` — herdar de DevOnlyCommand
   - `seed_gerentes.py` — herdar de DevOnlyCommand
   - `seed_produtos.py` — herdar de DevOnlyCommand
   - `seed_rbac.py` — herdar de DevOnlyCommand
   - `seed_tipos_evento.py` — herdar de DevOnlyCommand
   - `seed_projetos_fluxo_from_csv.py` — herdar de DevOnlyCommand
   - `seed_projetos_fluxo_from_sheets.py` — herdar de DevOnlyCommand
   - `backfill_is_online.py` — herdar de DevOnlyCommand
   - `fix_projetos_gerencia.py` — herdar de DevOnlyCommand
   - `migrate_rbac_groups.py` — herdar de DevOnlyCommand
   - `link_projetos_gerencias.py` — herdar de DevOnlyCommand
   - `populate_municipio_coords.py` — herdar de DevOnlyCommand

4. **`apps/core/tests/test_optional_seed_commands.py`** (novo, ~60 linhas)
   - Testar flag
   - Testar bloqueio em prod

### Fase 2: Dockerfile Multi-Stage (PR #340-B)

**Arquivos a modificar**:

1. **`v2/infra/Dockerfile`** (refatorar)
   ```dockerfile
   # ============================================
   # Stage: base (produção)
   # ============================================
   FROM python:3.12-slim AS base
   WORKDIR /app

   # System deps (minimal)
   RUN apt-get update && apt-get install -y --no-install-recommends \
       curl tzdata ca-certificates libpq5 \
    && rm -rf /var/lib/apt/lists/*

   # Python deps (prod only)
   COPY backend/requirements.txt /app/
   RUN pip install --no-cache-dir -r requirements.txt

   # App code (excluding scripts/)
   COPY backend/apps /app/apps
   COPY backend/config /app/config
   COPY backend/manage.py /app/

   # Gunicorn config
   COPY infra/gunicorn.conf.py /app/infra/

   # Build info
   ARG GIT_SHA=unknown
   ARG BUILD_DATE=unknown
   RUN echo '{"git_sha":"'$GIT_SHA'","build_date":"'$BUILD_DATE'"}' > /app/BUILD_INFO.json

   CMD ["gunicorn", "config.wsgi:application", "--config", "/app/infra/gunicorn.conf.py"]

   # ============================================
   # Stage: dev (desenvolvimento)
   # ============================================
   FROM base AS dev

   # Dev system tools
   RUN apt-get update && apt-get install -y --no-install-recommends \
       jq httpie vim nano tree less \
    && rm -rf /var/lib/apt/lists/*

   # Dev Python tools
   COPY backend/requirements-dev.txt /app/
   RUN pip install --no-cache-dir -r requirements-dev.txt

   # Scripts (dev only)
   COPY backend/scripts /app/scripts

   # Override CMD for dev
   CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
   ```

2. **`v2/infra/docker-compose.yml`** (modificar build)
   ```yaml
   web:
     build:
       context: ..
       dockerfile: infra/Dockerfile
       target: ${DOCKER_TARGET:-dev}  # Default: dev para backward compat
   ```

3. **`v2/infra/docker-compose.prod.yml`** (novo arquivo)
   ```yaml
   # Overrides para produção
   services:
     web:
       build:
         target: base
       environment:
         INCLUDE_ETL: "false"
         INCLUDE_SEED_COMMANDS: "false"
         CREATE_SUPERUSER: "0"
         GCAL_CLIENT: "google"
   ```

4. **`v2/backend/requirements.txt`** (limpar)
   - Remover ipython (já em requirements-dev.txt)
   - Manter apenas deps de produção

5. **`v2/backend/requirements-dev.txt`** (verificar)
   - Garantir que tem ipython, pgcli, pytest-watch

### Fase 3: Documentação e Testes (PR #340-C)

1. **`v2/docs/DEPLOY_PRODUCTION.md`** (novo)
   - Checklist de variáveis de ambiente
   - Comandos de build
   - Verificação pós-deploy

2. **Atualizar** `.claude/CLAUDE.md`
   - Adicionar CP-08: INCLUDE_SEED_COMMANDS
   - Documentar flags de ambiente

3. **Testes de integração**
   - Testar build com target=base
   - Testar build com target=dev
   - Verificar comandos bloqueados

---

## 5. Flags de Ambiente — Resumo Final

| Flag | Default | Dev | Staging | Prod | Controla |
|------|---------|-----|---------|------|----------|
| `INCLUDE_ETL` | true | true | true | false | Módulo dat_ingest |
| `INCLUDE_SEED_COMMANDS` | true | true | true | false | Commands de seed/dev |
| `CREATE_SUPERUSER` | 0 | 1 | 0 | 0 | Superuser no entrypoint |
| `DOCKER_TARGET` | dev | dev | dev | base | Stage do Dockerfile |
| `GCAL_CLIENT` | fake | fake | fake | google | Cliente Google Calendar |
| `DEBUG` | 0 | 1 | 0 | 0 | Django debug mode |

---

## 6. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Quebrar dev existente | Média | Alto | Default true para todas as flags |
| Esquecer flag em prod | Baixa | Alto | Documentação + checklist deploy |
| CI falhar | Baixa | Médio | Testes específicos para cada flag |
| Deps faltando em prod | Média | Alto | Testar build prod antes do merge |

---

## 7. Estratégia de Testes

### 7.1 Testes Unitários

```python
# test_optional_seed_commands.py

class TestIncludeSeedCommandsSetting:
    def test_defaults_to_true(self):
        assert settings.INCLUDE_SEED_COMMANDS is True

    def test_commands_blocked_when_disabled(self):
        with override_settings(INCLUDE_SEED_COMMANDS=False):
            cmd = SeedE2EUsersCommand()
            with pytest.raises(CommandError, match="desabilitado"):
                cmd.handle()

class TestDevOnlyCommandBase:
    def test_blocks_in_production(self):
        # Simular INCLUDE_SEED_COMMANDS=false
        pass

    def test_allows_in_development(self):
        # Simular INCLUDE_SEED_COMMANDS=true
        pass
```

### 7.2 Testes de Build

```bash
# CI: Testar ambos os targets
docker build --target base -t test:prod .
docker build --target dev -t test:dev .

# Verificar que ipython não existe em prod
docker run test:prod python -c "import IPython" && exit 1 || echo "OK: IPython not in prod"

# Verificar que ipython existe em dev
docker run test:dev python -c "import IPython" && echo "OK: IPython in dev"
```

---

## 8. Ordem de Execução dos PRs

```
PR #340-A: Flag INCLUDE_SEED_COMMANDS
    ↓
PR #340-B: Dockerfile Multi-Stage
    ↓
PR #340-C: Documentação + docker-compose.prod.yml
```

**Alternativa**: Um único PR #340 com 3 commits separados.

---

## 9. Checklist de Validação

### Antes do Merge

- [ ] `INCLUDE_SEED_COMMANDS=true` (dev): Todos os commands funcionam
- [ ] `INCLUDE_SEED_COMMANDS=false` (prod): Commands bloqueados com mensagem clara
- [ ] `docker build --target base`: Build sem erros
- [ ] `docker build --target dev`: Build sem erros
- [ ] Imagem prod não tem ipython/pgcli
- [ ] Imagem dev tem ipython/pgcli
- [ ] Testes passam (1516+)
- [ ] CI verde

### Após Deploy

- [ ] `python manage.py seed_e2e_users` → Erro em prod
- [ ] `python manage.py migrate` → Funciona em prod
- [ ] Aplicação inicia normalmente
- [ ] Google Calendar integração funciona

---

## 10. Rollback

Se problemas em produção:
1. Reverter para imagem anterior (sem multi-stage)
2. Ou: Setar `INCLUDE_SEED_COMMANDS=true` temporariamente

---

## 11. Arquivos Tocados (Resumo)

| Arquivo | Ação | Linhas |
|---------|------|--------|
| `config/settings.py` | Modificar | +5 |
| `apps/core/management/commands/base.py` | Novo | ~40 |
| `apps/core/management/commands/seed_*.py` | Modificar | ~2 cada (13 arquivos) |
| `apps/core/management/commands/backfill_*.py` | Modificar | ~2 cada |
| `apps/core/management/commands/fix_*.py` | Modificar | ~2 cada |
| `apps/core/tests/test_optional_seed_commands.py` | Novo | ~60 |
| `v2/infra/Dockerfile` | Refatorar | ~60 |
| `v2/infra/docker-compose.yml` | Modificar | +3 |
| `v2/infra/docker-compose.prod.yml` | Novo | ~20 |
| `v2/backend/requirements.txt` | Limpar | -2 |
| `v2/docs/DEPLOY_PRODUCTION.md` | Novo | ~100 |
| `.claude/CLAUDE.md` | Atualizar | +10 |

**Total**: ~15 arquivos, ~300 linhas de código

---

## 12. Decisões de Design

### Por que flag em vez de remover commands?

1. **Preservação**: Commands permanecem no repo para uso em dev
2. **Auditoria**: Código visível, histórico preservado
3. **Flexibilidade**: Staging pode usar commands para popular dados
4. **Simplicidade**: Menos branches/configs para manter

### Por que multi-stage em vez de dois Dockerfiles?

1. **DRY**: Base compartilhada, sem duplicação
2. **Cache**: Layers reutilizáveis entre builds
3. **Padrão**: Best practice Docker
4. **Manutenção**: Um arquivo, duas configurações

### Por que default true?

1. **Backward compatibility**: Dev existente não quebra
2. **Explícito em prod**: Força configuração consciente
3. **Segurança**: Prod requer ação para desabilitar

---

## Aprovação

- [ ] Revisar plano
- [ ] Aprovar abordagem
- [ ] Iniciar implementação

**Próximo passo**: Aguardando aprovação para iniciar Fase 1.

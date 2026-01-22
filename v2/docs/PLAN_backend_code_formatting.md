# Epic #450: Backend Code Formatting (Black + isort + Flake8)

**Data**: 2026-01-19
**Autor**: Claude Code
**Status**: Planejado

## Overview

Formatar todo o backend Python com Black e isort, corrigir erros de Flake8, e tornar o lint obrigatório no CI. Isso garantirá código consistente, facilita code reviews, e previne conflitos de formatação em PRs futuros.

## Estado Atual

### Métricas do Codebase

| Métrica | Valor |
|---------|-------|
| **Total de arquivos Python** | 396 |
| **Arquivos precisando Black** | 330 (83%) |
| **Arquivos já formatados** | 69 (17%) |
| **Arquivos precisando isort** | 251 |
| **Erros Flake8 total** | 713 |

### Breakdown de Erros Flake8

| Código | Quantidade | Descrição | Auto-fix? |
|--------|------------|-----------|-----------|
| E501 | 373 | Linha muito longa (>120) | ✅ Black |
| F401 | 134 | Import não usado | ⚠️ autoflake |
| F841 | 97 | Variável não usada | ⚠️ autoflake |
| F541 | 36 | f-string sem placeholders | ❌ Manual |
| F811 | 18 | Redefinição de nome | ❌ Manual |
| E722 | 11 | Bare except | ❌ Manual |
| E302 | 10 | 2 linhas em branco | ✅ Black |
| W391 | 8 | Linha em branco no final | ✅ Black |
| Outros | 26 | Diversos | ✅ Black |

### Configuração Atual

- `pyproject.toml`: Apenas configuração Pyright (sem Black/isort)
- `setup.cfg`: Não existe
- `.flake8`: Não existe
- CI: lint com `continue-on-error: true` (não-bloqueante)

## Estado Desejado

1. **Todos os 396 arquivos** formatados com Black e isort
2. **Zero erros Flake8** (ou erros documentados e ignorados)
3. **CI bloqueante** - lint deve passar para merge
4. **Configuração centralizada** em `pyproject.toml`
5. **Pre-commit hooks** opcionais para desenvolvedores

## O Que NÃO Estamos Fazendo

- ❌ Mudanças de lógica ou refatoração de código
- ❌ Adicionar type hints (já temos 100% com Pyright)
- ❌ Mudar arquitetura ou estrutura de pastas
- ❌ Atualizar dependências além das de lint

---

## Fases de Implementação

### Fase 1: Configuração de Ferramentas (Issue #451)

**Objetivo**: Configurar Black, isort e Flake8 no pyproject.toml

**Arquivos a modificar**:
- `v2/backend/pyproject.toml`

**Configuração a adicionar**:

```toml
# ================================================================
# Black - Code Formatter
# ================================================================
[tool.black]
line-length = 120
target-version = ['py312']
include = '\.pyi?$'
exclude = '''
/(
    \.git
    | \.venv
    | venv
    | __pycache__
    | migrations
    | node_modules
)/
'''

# ================================================================
# isort - Import Sorter
# ================================================================
[tool.isort]
profile = "black"
line_length = 120
skip = [".venv", "venv", "migrations", "__pycache__"]
known_django = ["django", "rest_framework"]
known_first_party = ["apps", "config"]
sections = ["FUTURE", "STDLIB", "DJANGO", "THIRDPARTY", "FIRSTPARTY", "LOCALFOLDER"]

# ================================================================
# Flake8 - Style Checker (via pyproject-flake8)
# ================================================================
[tool.flake8]
max-line-length = 120
extend-ignore = ["E203", "W503", "E501"]
exclude = [".venv", "venv", "migrations", "__pycache__", "*.pyi"]
per-file-ignores = [
    "__init__.py:F401",
    "conftest.py:F401,F811"
]
```

**Critérios de Sucesso**:
- [ ] Configuração adicionada ao pyproject.toml
- [ ] `black --check .` reconhece a configuração
- [ ] `isort --check .` reconhece a configuração

---

### Fase 2: Formatação Automática com Black (Issue #452)

**Objetivo**: Formatar todos os 330 arquivos com Black

**Comando**:
```bash
cd v2/backend
black .
```

**Arquivos afetados**: ~330 arquivos em:
- `apps/core/` (~200 arquivos)
- `apps/dat_ingest/` (~80 arquivos)
- `apps/dev_tools/` (~30 arquivos)
- `config/` (~10 arquivos)
- `scripts/` (~10 arquivos)

**Critérios de Sucesso**:
- [ ] `black --check .` passa sem erros
- [ ] Nenhum arquivo modificado manualmente (apenas Black)
- [ ] Testes continuam passando: `pytest apps/ -x -q`

---

### Fase 3: Ordenação de Imports com isort (Issue #453)

**Objetivo**: Ordenar imports em todos os 251 arquivos

**Comando**:
```bash
cd v2/backend
isort .
```

**Critérios de Sucesso**:
- [ ] `isort --check .` passa sem erros
- [ ] Imports organizados por seções (stdlib, django, third-party, local)
- [ ] Testes continuam passando

---

### Fase 4: Correção de Imports Não Usados (Issue #454)

**Objetivo**: Remover imports não utilizados (F401) com autoflake

**Comando**:
```bash
cd v2/backend
pip install autoflake
autoflake --in-place --remove-all-unused-imports --recursive .
```

**Atenção**: Revisar manualmente os arquivos `__init__.py` que exportam símbolos.

**Critérios de Sucesso**:
- [ ] Erros F401 reduzidos de 134 para ~10 (apenas __init__.py)
- [ ] Testes continuam passando
- [ ] Pyright continua passando

---

### Fase 5: Correção de Variáveis Não Usadas (Issue #455)

**Objetivo**: Corrigir variáveis não utilizadas (F841)

**Estratégia**:
1. Para variáveis intencionalmente ignoradas: renomear para `_var`
2. Para variáveis realmente não usadas: remover

**Comando para listar**:
```bash
flake8 --select=F841 apps/
```

**Critérios de Sucesso**:
- [ ] Zero erros F841
- [ ] Variáveis ignoradas prefixadas com `_`
- [ ] Testes passando

---

### Fase 6: Correções Manuais Restantes (Issue #456)

**Objetivo**: Corrigir erros que requerem intervenção manual

**Erros a corrigir**:

| Erro | Qtd | Ação |
|------|-----|------|
| F541 | 36 | Remover `f` de strings sem placeholders |
| F811 | 18 | Resolver redefinições de nomes |
| E722 | 11 | Substituir `except:` por `except Exception:` |
| F821 | 6 | Corrigir nomes indefinidos |

**Comando para listar**:
```bash
flake8 --select=F541,F811,E722,F821 apps/
```

**Critérios de Sucesso**:
- [ ] Zero erros manuais restantes
- [ ] Testes passando
- [ ] Pyright passando

---

### Fase 7: Tornar Lint Obrigatório no CI (Issue #457)

**Objetivo**: Remover `continue-on-error: true` do CI

**Arquivo**: `.github/workflows/ci.yaml`

**Mudança**:
```yaml
# ANTES
- name: Lint with Black
  continue-on-error: true  # Remover esta linha
  run: |
    cd v2/backend
    black --check --diff .

# DEPOIS
- name: Lint with Black
  run: |
    cd v2/backend
    black --check --diff .
```

**Critérios de Sucesso**:
- [ ] CI passa com lint obrigatório
- [ ] PRs que quebram formatação são bloqueados
- [ ] Documentação atualizada

---

### Fase 8 (Opcional): Pre-commit Hooks (Issue #458)

**Objetivo**: Configurar pre-commit para desenvolvedores

**Arquivo**: `v2/backend/.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.4.2
    hooks:
      - id: black
        language_version: python3.12

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=120, --extend-ignore=E203,W503]
```

**Critérios de Sucesso**:
- [ ] `pre-commit install` funciona
- [ ] Hooks rodam no commit
- [ ] Documentação no README

---

## Ordem de Execução

```
Fase 1 (Config)     ──────────────────────────────────┐
                                                      │
Fase 2 (Black)      ─────────────────┐                │
                                     ├── Paralelo     │
Fase 3 (isort)      ─────────────────┘                │
                                                      │
Fase 4 (autoflake)  ──────────────────────────────────┤── Sequencial
                                                      │
Fase 5 (F841)       ──────────────────────────────────┤
                                                      │
Fase 6 (Manual)     ──────────────────────────────────┤
                                                      │
Fase 7 (CI)         ──────────────────────────────────┘

Fase 8 (Optional)   ── Pode ser feito a qualquer momento
```

**Recomendação**: Executar Fases 1-3 em um único PR, Fases 4-6 em outro PR, e Fase 7 no final.

---

## Estimativas

| Fase | Tempo | Risco |
|------|-------|-------|
| Fase 1 | 15min | Baixo |
| Fase 2 | 5min | Baixo |
| Fase 3 | 5min | Baixo |
| Fase 4 | 30min | Médio (revisar __init__.py) |
| Fase 5 | 1h | Médio (revisar variáveis) |
| Fase 6 | 2h | Alto (correções manuais) |
| Fase 7 | 10min | Baixo |
| Fase 8 | 20min | Baixo |
| **Total** | **~4h** | - |

---

## Verificação Final

Após todas as fases:

```bash
cd v2/backend

# 1. Lint completo
black --check .
isort --check .
flake8 .

# 2. Type check
pyright apps/core apps/dat_ingest config

# 3. Testes
pytest apps/ -q

# 4. CI local (se disponível)
make lint
make test
```

---

## Rollback

Se algo der errado:

```bash
# Reverter todas as mudanças de formatação
git checkout main -- v2/backend/

# Ou reverter commit específico
git revert <commit-hash>
```

---

## Referências

- [Black Documentation](https://black.readthedocs.io/)
- [isort Documentation](https://pycqa.github.io/isort/)
- [Flake8 Documentation](https://flake8.pycqa.org/)
- CI Workflow: `.github/workflows/ci.yaml`
- Pyright Config: `v2/backend/pyproject.toml`

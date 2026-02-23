# Plano: Ferramentas de Análise de Código (Local, Custo $0)

**Status**: 📋 Planejado
**Criado**: 2026-02-04
**Objetivo**: Configurar SonarQube + Ruff + Flake8 + Pylint + Bandit para análise local com output JSON otimizado para Claude

---

## 1. Visão Geral

### 1.1 Problema

Atualmente, para encontrar problemas no código, Claude precisa ler arquivos inteiros, consumindo muitos tokens (~50-100k por análise completa).

### 1.2 Solução Proposta

Usar ferramentas de análise estática que geram JSON com lista cirúrgica de issues:

```
Ferramentas geram JSON → Claude lê apenas a lista (~2-5k tokens) → Fix cirúrgico
```

**Economia estimada: ~95% de tokens**

### 1.3 Escopo

| Ferramenta | Propósito | Execução |
|------------|-----------|----------|
| **SonarQube Community** | Dashboard + histórico + Quality Gates | Docker local |
| **Ruff** | Linting ultra-rápido (Rust) | CLI local |
| **Flake8** | Style checker clássico | CLI local |
| **Pylint** | Análise completa | CLI local |
| **Bandit** | Vulnerabilidades de segurança | CLI local |

**Tudo roda 100% local, sem custos de cloud.**

---

## 2. Arquitetura

### 2.1 Estrutura de Arquivos a Criar

```
v2/
├── infra/
│   └── docker-compose.sonarqube.yml    # SonarQube + PostgreSQL
├── backend/
│   ├── sonar-project.properties        # Config do scanner
│   └── pyproject.toml                  # +Ruff, Pylint, Bandit configs
├── scripts/
│   └── analyze_code.py                 # Script unificado JSON
├── out_analysis/                       # Outputs (gitignored)
│   ├── .gitignore
│   ├── issues.json                     # Output unificado
│   ├── ruff.json
│   ├── flake8.json
│   ├── pylint.json
│   └── bandit.json
├── requirements-analysis.txt           # Dependências
├── docs/
│   └── GUIDE_CODE_ANALYSIS.md          # Documentação
└── Makefile                            # +targets de análise
```

### 2.2 Fluxo de Uso

```
┌─────────────────────────────────────────────────────────────────┐
│                     FLUXO DE ANÁLISE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Desenvolvedor roda:                                         │
│     $ make analyze                                              │
│                                                                 │
│  2. Script executa ferramentas em paralelo:                     │
│     ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│     │   Ruff   │  │  Flake8  │  │  Pylint  │  │  Bandit  │     │
│     └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘     │
│          │             │             │             │            │
│          └─────────────┴──────┬──────┴─────────────┘            │
│                               ▼                                 │
│                    ┌───────────────────┐                        │
│                    │   issues.json     │                        │
│                    │   (lista única)   │                        │
│                    └─────────┬─────────┘                        │
│                              │                                  │
│  3. Passa para Claude:       ▼                                  │
│     "Corrija os issues em out_analysis/issues.json"             │
│                              │                                  │
│  4. Claude:                  ▼                                  │
│     - Lê lista (~2k tokens)                                     │
│     - Read apenas linhas específicas                            │
│     - Edit cirúrgico                                            │
│     - Commit + PR                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Especificações Técnicas

### 3.1 SonarQube Community Edition

**docker-compose.sonarqube.yml**:
```yaml
services:
  sonarqube:
    image: sonarqube:10-community
    container_name: sonarqube
    depends_on:
      - sonar_db
    environment:
      SONAR_JDBC_URL: jdbc:postgresql://sonar_db:5432/sonarqube
      SONAR_JDBC_USERNAME: sonar
      SONAR_JDBC_PASSWORD: sonar
    ports:
      - "9000:9000"
    volumes:
      - sonarqube_data:/opt/sonarqube/data
      - sonarqube_extensions:/opt/sonarqube/extensions
      - sonarqube_logs:/opt/sonarqube/logs
    networks:
      - sonar_net

  sonar_db:
    image: postgres:15-alpine
    container_name: sonar_db
    environment:
      POSTGRES_USER: sonar
      POSTGRES_PASSWORD: sonar
      POSTGRES_DB: sonarqube
    volumes:
      - sonar_postgresql:/var/lib/postgresql/data
    networks:
      - sonar_net

volumes:
  sonarqube_data:
  sonarqube_extensions:
  sonarqube_logs:
  sonar_postgresql:

networks:
  sonar_net:
    driver: bridge
```

**Requisitos de sistema**:
- Docker Desktop
- 4GB RAM disponível
- Porta 9000 livre

**Primeiro acesso**:
- URL: http://localhost:9000
- Login: admin / admin (mudar na primeira vez)
- Gerar token: My Account → Security → Generate Token

### 3.2 Configuração Ruff (pyproject.toml)

```toml
[tool.ruff]
line-length = 120
target-version = "py312"

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # Pyflakes
    "I",      # isort
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "UP",     # pyupgrade
    "S",      # flake8-bandit (security)
    "SIM",    # flake8-simplify
    "RUF",    # Ruff-specific rules
]
ignore = [
    "E501",   # line too long (handled by formatter)
    "E203",   # whitespace before ':'
    "S101",   # assert used (ok in tests)
    "S105",   # hardcoded password (false positives)
    "S106",   # hardcoded password (false positives)
]

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]
"conftest.py" = ["F401", "F811"]
"**/tests/**/*.py" = ["F401", "F811", "F841", "S101"]
"**/migrations/**/*.py" = ["E501", "F401"]

[tool.ruff.lint.isort]
known-first-party = ["apps", "config"]
known-third-party = ["django", "rest_framework"]
```

### 3.3 Configuração Pylint (pyproject.toml)

```toml
[tool.pylint.main]
py-version = "3.12"
load-plugins = ["pylint_django"]
django-settings-module = "config.settings"
ignore = ["migrations", "__pycache__", ".venv"]

[tool.pylint.messages_control]
disable = [
    "C0114",  # missing-module-docstring
    "C0115",  # missing-class-docstring
    "C0116",  # missing-function-docstring
    "R0903",  # too-few-public-methods
    "R0913",  # too-many-arguments
    "W0511",  # fixme/todo comments
]

[tool.pylint.format]
max-line-length = 120
```

### 3.4 Configuração Bandit (pyproject.toml)

```toml
[tool.bandit]
exclude_dirs = ["tests", "migrations", ".venv", "__pycache__"]
skips = ["B101", "B105", "B106"]  # assert, hardcoded passwords (false positives)
```

### 3.5 Script de Análise Unificado

**scripts/analyze_code.py** - Funcionalidades:

1. **Executa todas as ferramentas** (ou uma específica com `--tool`)
2. **Parse de outputs JSON** de cada ferramenta
3. **Unifica em formato padrão**:
   ```json
   {
     "summary": {
       "total_issues": 42,
       "by_tool": {"ruff": 30, "bandit": 12},
       "by_severity": {"error": 10, "warning": 32},
       "top_files": {"apps/core/views.py": 8},
       "timestamp": "2026-02-04T10:30:00"
     },
     "issues": [
       {
         "tool": "ruff",
         "file": "apps/core/views.py",
         "line": 42,
         "code": "F401",
         "message": "Unused import 'os'",
         "severity": "warning",
         "fix_available": true
       }
     ]
   }
   ```
4. **Modo summary** (`--summary`) para apenas estatísticas

### 3.6 Makefile Targets

```makefile
# Code Analysis (Local - JSON output para Claude)
analyze:              # Todas as ferramentas
analyze-ruff:         # Apenas Ruff (ultra-rápido)
analyze-flake8:       # Apenas Flake8
analyze-pylint:       # Apenas Pylint
analyze-bandit:       # Apenas Bandit (security)
analyze-summary:      # Apenas resumo estatístico

# SonarQube (self-hosted)
sonar-up:             # Iniciar SonarQube
sonar-down:           # Parar SonarQube
sonar-scan:           # Executar scanner
```

### 3.7 Dependências (requirements-analysis.txt)

```
# Linters
ruff>=0.4.0
flake8>=7.0.0
flake8-json
pylint>=3.0.0
pylint-django>=2.5.0

# Security
bandit>=1.7.0

# Formatters (já configurados)
black>=24.0.0
isort>=5.13.0
```

---

## 4. Fases de Implementação

### Fase 1: Infraestrutura Base
**Estimativa**: ~30 min

| # | Tarefa | Arquivo |
|---|--------|---------|
| 1.1 | Criar docker-compose.sonarqube.yml | `v2/infra/` |
| 1.2 | Criar sonar-project.properties | `v2/backend/` |
| 1.3 | Criar requirements-analysis.txt | `v2/` |
| 1.4 | Criar diretório out_analysis/ com .gitignore | `v2/` |

### Fase 2: Configurações das Ferramentas
**Estimativa**: ~20 min

| # | Tarefa | Arquivo |
|---|--------|---------|
| 2.1 | Adicionar config Ruff ao pyproject.toml | `v2/backend/pyproject.toml` |
| 2.2 | Adicionar config Pylint ao pyproject.toml | `v2/backend/pyproject.toml` |
| 2.3 | Adicionar config Bandit ao pyproject.toml | `v2/backend/pyproject.toml` |
| 2.4 | Adicionar config Coverage ao pyproject.toml | `v2/backend/pyproject.toml` |

### Fase 3: Script de Análise
**Estimativa**: ~45 min

| # | Tarefa | Arquivo |
|---|--------|---------|
| 3.1 | Criar analyze_code.py com parsers JSON | `v2/scripts/` |
| 3.2 | Implementar parse para Ruff | `v2/scripts/analyze_code.py` |
| 3.3 | Implementar parse para Flake8 | `v2/scripts/analyze_code.py` |
| 3.4 | Implementar parse para Pylint | `v2/scripts/analyze_code.py` |
| 3.5 | Implementar parse para Bandit | `v2/scripts/analyze_code.py` |
| 3.6 | Implementar geração de summary | `v2/scripts/analyze_code.py` |
| 3.7 | Testar script manualmente | - |

### Fase 4: Integração Makefile
**Estimativa**: ~15 min

| # | Tarefa | Arquivo |
|---|--------|---------|
| 4.1 | Adicionar targets de análise | `v2/Makefile` |
| 4.2 | Adicionar targets SonarQube | `v2/Makefile` |
| 4.3 | Atualizar .PHONY | `v2/Makefile` |
| 4.4 | Atualizar help | `v2/Makefile` |

### Fase 5: Documentação e Testes
**Estimativa**: ~20 min

| # | Tarefa | Arquivo |
|---|--------|---------|
| 5.1 | Criar GUIDE_CODE_ANALYSIS.md | `v2/docs/` |
| 5.2 | Testar make analyze completo | - |
| 5.3 | Testar make sonar-up/down | - |
| 5.4 | Validar output JSON para Claude | - |

---

## 5. Comparativo de Ferramentas

| Ferramenta | Velocidade | Profundidade | Uso Recomendado |
|------------|------------|--------------|-----------------|
| **Ruff** | ⚡⚡⚡⚡⚡ | ⭐⭐⭐ | Sempre, antes de commits |
| **Flake8** | ⚡⚡⚡⚡ | ⭐⭐⭐ | CI, validação de estilo |
| **Pylint** | ⚡⚡ | ⭐⭐⭐⭐⭐ | Análise profunda ocasional |
| **Bandit** | ⚡⚡⚡⚡ | ⭐⭐⭐⭐ (security) | Antes de PRs importantes |
| **SonarQube** | ⚡⚡ | ⭐⭐⭐⭐⭐ | Dashboard semanal |

---

## 6. Workflow com Claude

### 6.1 Uso Básico

```bash
# 1. Rodar análise
make analyze

# 2. Verificar resumo
cat out_analysis/issues.json | jq '.summary'

# 3. Passar para Claude
"Claude, corrija os issues em out_analysis/issues.json.
 Para cada issue, faça Read da linha específica, Edit cirúrgico.
 Ao final, commit com mensagem descritiva."
```

### 6.2 Workflow Automatizado

```bash
# Análise + Fix + Commit + PR (tudo em um comando futuro)
make analyze-fix  # (possível extensão futura)
```

### 6.3 Consumo de Tokens

| Cenário | Tokens Estimados |
|---------|------------------|
| Ler todo o backend | ~80.000 |
| Ler issues.json (50 issues) | ~2.000 |
| Read de 50 linhas específicas | ~3.000 |
| **Total otimizado** | **~5.000** |
| **Economia** | **~94%** |

---

## 7. Checklist de Validação

### Pré-Implementação
- [ ] Docker Desktop instalado e rodando
- [ ] Python 3.12 disponível
- [ ] Porta 9000 livre para SonarQube

### Pós-Implementação
- [ ] `pip install -r requirements-analysis.txt` funciona
- [ ] `make analyze-ruff` gera JSON válido
- [ ] `make analyze-flake8` gera JSON válido
- [ ] `make analyze-pylint` gera JSON válido
- [ ] `make analyze-bandit` gera JSON válido
- [ ] `make analyze` unifica todos os outputs
- [ ] `make sonar-up` inicia SonarQube em http://localhost:9000
- [ ] `make sonar-down` para SonarQube
- [ ] Output JSON é parseável por Claude
- [ ] Documentação está completa

---

## 8. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| SonarQube consome muita RAM | Média | Baixo | Usar apenas quando necessário, `make sonar-down` após uso |
| Pylint muito lento | Alta | Baixo | Usar `--tool ruff` para análises rápidas |
| Conflito de porta 9000 | Baixa | Médio | Configurar porta alternativa no docker-compose |
| False positives em Bandit | Média | Baixo | Configurar skips no pyproject.toml |

---

## 9. Extensões Futuras (Fora do Escopo Atual)

1. **Pre-commit hooks** - Rodar Ruff automaticamente antes de commits
2. **CI Integration** - Quality Gates bloqueando PRs
3. **VS Code Extension** - Integração com editor
4. **Auto-fix** - `make analyze-fix` que roda Claude automaticamente
5. **Métricas históricas** - Dashboard de evolução da qualidade

---

## 10. Referências

- [SonarQube Community](https://www.sonarsource.com/products/sonarqube/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Flake8 Documentation](https://flake8.pycqa.org/)
- [Pylint Documentation](https://pylint.readthedocs.io/)
- [Bandit Documentation](https://bandit.readthedocs.io/)

---

## Aprovação

| Papel | Nome | Data | Status |
|-------|------|------|--------|
| Autor | Claude | 2026-02-04 | ✅ |
| Revisor | - | - | ⏳ Pendente |
| Aprovador | - | - | ⏳ Pendente |

---

**Próximo passo**: Após aprovação, executar `/implement_plan PLAN_code_analysis_tools.md`

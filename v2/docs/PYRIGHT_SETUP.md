# ⚙️ Pyright Setup & Troubleshooting

**Projeto**: Aprender Sistema v2
**Type Checker**: Pyright 1.1.382 (`v2/backend/requirements-dev.txt:42`)
**Python**: 3.12 (`v2/backend/pyproject.toml:11`; CI em `.github/actions/setup-python-deps/action.yml:12`)
**Última Atualização**: 24 de julho de 2026 — revisão contra a config real

---

## 🚀 Instalação

### 1. Instalar Dependências

```bash
cd v2/backend
pip install -r requirements-dev.txt
```

**Pacotes instalados** (versões conforme `v2/backend/requirements-dev.txt:42-47`):
- `pyright==1.1.382` - Type checker
- `django-types==0.24.0` - Type stubs Django
- `djangorestframework-types==0.9.0` - Type stubs DRF
- `types-requests==2.32.0.20240914` - Type stubs requests
- `types-redis==4.6.0.20240903` - Type stubs Redis
- `celery-types==0.22.0` - Type stubs Celery

> Fonte de verdade das versões é o `requirements-dev.txt`. Se este doc divergir, o arquivo vence.

### 2. Verificar Instalação

```bash
cd v2/backend
pyright --version
```

**Output esperado**: `pyright 1.1.382`

---

## 🔧 Configuração

### pyproject.toml

Configuração principal em `v2/backend/pyproject.toml`:

```toml
[tool.pyright]
typeCheckingMode = "strict"                              # pyproject.toml:8
pythonVersion = "3.12"                                   # pyproject.toml:11
venvPath = "."                                           # pyproject.toml:14
include = ["apps/core", "apps/dev_tools", "config"]      # pyproject.toml:21-25
exclude = [                                              # pyproject.toml:28-34
    "**/__pycache__", "**/migrations",
    "**/.venv", "**/venv", "**/node_modules",
]
stubPath = "typings"                                     # pyproject.toml:37
```

**Arquivos incluídos**:
- `apps/core/` — services, models, views, serializers, tasks
- `apps/dev_tools/` — commands de desenvolvimento (ex.: `seed_rbac`)
- `config/` — settings, URLs

**Arquivos excluídos**: `**/migrations/`, `**/__pycache__`, `**/.venv`, `**/venv`, `**/node_modules`.

> ⚠️ **Corrigido em 2026-07-24**: a app **`apps/dat_ingest` não existe** — foi removida junto com o
> ETL legado. `v2/backend/apps/` contém apenas `core/` e `dev_tools/`. Toda referência a
> `dat_ingest` neste documento foi substituída.
>
> ⚠️ **`**/tests` NÃO está em `exclude`** (`pyproject.toml:28-34`). Os testes não são analisados
> porque também não estão em `include` — não porque estejam explicitamente excluídos.

### Type Stubs Customizados

Type stubs em `v2/backend/typings/` (`stubPath`, `pyproject.toml:37`):

```
typings/
├── rest_framework/
│   └── __init__.pyi       # ModelSerializer[T], ViewSet[T]
└── django_filters/
    ├── __init__.pyi
    └── rest_framework/
        └── __init__.pyi
```

*(Não existe `typings/django/` — Django é tipado pelo pacote `django-types`.)*

**Por que stubs customizados?**
- Django/DRF têm tipagem complexa
- Stubs simplificam uso de Generics
- Melhora autocomplete no VS Code

---

## ▶️ Uso

### Rodar Pyright Localmente

```bash
cd v2/backend

# Verificar todos os arquivos incluídos
pyright

# Verificar diretórios específicos
pyright apps/core/services

# Verificar arquivo específico
pyright apps/core/services/availability_service.py

# Output em JSON
pyright --outputjson > pyright-report.json
```

### Rodar no CI

O CI roda automaticamente em cada push/PR:

```yaml
# .github/workflows/ci.yaml — job "[required] backend typecheck (pyright)" (ci.yaml:380)
- name: Type check with Pyright
  run: |
    cd v2/backend
    pyright apps/core config        # ci.yaml:396
```

> ✅ **Atualizado em 2026-07-24**: pyright é hoje um **gate obrigatório e bloqueante**.
> O step em `.github/workflows/ci.yaml:393-396` **não tem** `continue-on-error`, e o job se chama
> `[required] backend typecheck (pyright)` (`ci.yaml:380`). O marco "PR #8" já foi entregue.

---

## 🔍 VS Code Integration (Pylance)

### Instalação

1. Instalar extensão **Pylance** (oficial Microsoft)
2. Configurar workspace settings:

```json
// .vscode/settings.json
{
    "python.analysis.typeCheckingMode": "strict",
    "python.analysis.diagnosticMode": "workspace",
    "python.analysis.autoImportCompletions": true,
    "python.analysis.inlayHints.variableTypes": true,
    "python.analysis.inlayHints.functionReturnTypes": true,
    "python.languageServer": "Pylance",
    "[python]": {
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.organizeImports": true
        }
    }
}
```

### Features

- **Autocomplete inteligente**: Ctrl + Espaço
- **Inline errors**: Sublinhado vermelho/amarelo
- **Hover info**: Mostra tipos ao passar o mouse
- **Go to definition**: Ctrl + Clique
- **Refactoring**: F2 (renomear símbolo)

---

## 🐛 Troubleshooting

### Erro: "Cannot find module 'django'"

**Causa**: Pyright não encontra Django instalado.

**Solução**:
```bash
# 1. Verificar venv ativo
which python  # Deve apontar para .venv/bin/python

# 2. Reinstalar dependências
pip install -r requirements.txt

# 3. Verificar pyproject.toml
cat pyproject.toml | grep venvPath
# Deve ter: venvPath = "."
```

### Erro: "Module has no attribute 'objects'"

**Causa**: Django models não estão sendo reconhecidos.

**Solução**:
```bash
# 1. Verificar django-types instalado
pip list | grep django-types

# 2. Se não estiver, instalar
pip install django-types==0.24.0

# 3. Recarregar VS Code
# Ctrl + Shift + P -> "Reload Window"
```

### Erro: "reportGeneralTypeIssues" em QuerySets

**Causa**: Django QuerySet usa "magic methods" que Pyright não entende.

**Solução**: Já relaxado em `pyproject.toml`:
```toml
[tool.pyright]
reportGeneralTypeIssues = "warning"  # Não bloqueia
```

**Se persistir**: Adicione `# type: ignore` na linha:
```python
queryset = Solicitacao.objects.filter(status="pendente")  # type: ignore[misc]
```

### Erro: "Cannot resolve import"

**Causa**: Pyright não encontra módulos em `apps/`.

**Solução**: Verificar `extraPaths` em `pyproject.toml`:
```toml
[tool.pyright.executionEnvironments]
[[tool.pyright.executionEnvironments]]
extraPaths = ["apps", "config"]
```

### Muitos Erros (centenas)

**Normal!** Em `strict mode`, Pyright é bem rigoroso.

**Estratégia**:
1. ✅ PR #1: Aceitar baseline (erros existentes)
2. ✅ PRs #2-#8: Corrigir gradualmente (8 PRs, ~144h)
3. ✅ Após PR #8: Código crítico 100% tipado

**Ver também**: [TYPE_HINTS_GUIDE.md](./TYPE_HINTS_GUIDE.md).
*(O `TYPE_HINTS_REFERENCE_FULL.md` citado até 2026-07-24 nunca existiu no repositório.)*

---

## 📊 Comandos Úteis

### Gerar Relatório JSON

```bash
cd v2/backend
pyright --outputjson > pyright-report.json
```

**Estrutura**:
```json
{
  "version": "1.1.382",
  "time": "...",
  "generalDiagnostics": [
    {
      "file": "apps/core/services/availability_service.py",
      "severity": "error",
      "message": "...",
      "range": { "start": { "line": 42, "character": 10 }, ... }
    }
  ],
  "summary": {
    "filesAnalyzed": 65,
    "errorCount": 124,
    "warningCount": 89,
    "informationCount": 5,
    "timeInSec": 3.2
  }
}
```

### Contar Erros por Severidade

```bash
cd v2/backend
pyright --outputjson | python -c "
import json, sys
data = json.load(sys.stdin)
summary = data['summary']
print(f\"Errors: {summary['errorCount']}\")
print(f\"Warnings: {summary['warningCount']}\")
print(f\"Files: {summary['filesAnalyzed']}\")
"
```

### Verificar Apenas Services

```bash
cd v2/backend
pyright apps/core/services/ apps/dev_tools/
```

---

## 🎯 Baseline (Estado Atual)

**Baseline criado em**: 11/11/2025

```bash
cd v2/backend
pyright --outputjson > pyright-baseline.json
```

**Erros esperados**: ~200-400 (normal para projeto sem type hints)

**Após 8 PRs**: 0 erros em código crítico (65 arquivos, ~12,000 linhas)

**Timeline**: 3.6 semanas (144h)

---

## 🔄 Integração com CI/CD

### GitHub Actions

```yaml
# .github/workflows/ci.yaml — job "[required] backend typecheck (pyright)" (ci.yaml:380)
- name: Type check with Pyright
  run: |
    cd v2/backend
    pyright apps/core config        # ci.yaml:396
```

**Estado em 2026-07-24**: gate **bloqueante**. Não há `continue-on-error` no step
(`.github/workflows/ci.yaml:393-396`) — pyright reprovando reprova o PR.

### Pre-commit Hook (Futuro)

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pyright
        name: pyright
        entry: pyright
        language: system
        types: [python]
        pass_filenames: false
        always_run: true
```

---

## 📚 Recursos

### Documentação Oficial
- [Pyright Documentation](https://github.com/microsoft/pyright)
- [Pylance Extension](https://marketplace.visualstudio.com/items?itemName=ms-python.vscode-pylance)
- [django-types](https://github.com/sbdchd/django-types)

### Interno
- [`TYPE_HINTS_GUIDE.md`](./TYPE_HINTS_GUIDE.md) - Guia para desenvolvedores
- `.claude/skills/django-patterns/SKILL.md` (skill local) - Padrões Django

---

## 🆘 Suporte

**Problemas comuns?** Consulte FAQ acima.

**Dúvidas?** Pergunte no Slack (#dev-type-hints) ou abra issue no GitHub.

**Bugs no Pyright?** Reporte em: https://github.com/microsoft/pyright/issues

---

**Happy type checking! 🐍✨**

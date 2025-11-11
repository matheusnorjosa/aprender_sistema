# Type Hints Baseline — Aprender Sistema v2

**Data**: 11 de Novembro de 2025
**Branch**: `feat/typehints-setup`
**PR**: #1
**Python**: 3.12.12
**Pyright**: 1.1.382 (strict mode)

---

## 📊 Estado Inicial

### Arquivos do Projeto

```
Total: 186 arquivos Python (excl. migrations, __pycache__)

Distribuição:
├── Services:     24 arquivos (~7,192 linhas)
├── Models:       5 arquivos (1,017+ linhas)
├── Serializers:  1+ arquivos (562+ linhas)
├── Views:        21 arquivos (981+ linhas)
├── Tasks:        1+ arquivos (489 linhas)
├── Tests:        82 arquivos
└── Commands:     27 arquivos
```

### Cobertura Atual de Type Hints

**Estimativa**: ~16% (30/186 arquivos com type hints parciais)

**Arquivos com type hints parciais**:
- `apps/core/services/availability_service.py` - Dataclasses com tipos
- `apps/core/services/gcal_sync_service.py` - Alguns métodos tipados
- Alguns métodos isolados em outros arquivos

**Arquivos sem type hints**:
- Maioria dos models (métodos personalizados)
- Maioria dos serializers (validate methods)
- Maioria das views (action methods)
- Todos os tasks (Celery)
- Todos os management commands

---

## 🎯 Meta (Pós-PR #8)

**Cobertura**: 100% em código crítico (65 arquivos = 35% do projeto)

**Arquivos incluídos**:
- ✅ 24 services (~7,192 linhas)
- ✅ 5 models (1,017+ linhas)
- ✅ Serializers (562+ linhas)
- ✅ 21 views (981+ linhas)
- ✅ Tasks (489 linhas)
- ✅ 27 management commands
- ⏸️ Tests (fixtures apenas - 4 arquivos)

**Total**: ~12,000+ linhas de código crítico

---

## 🔍 Pyright Baseline (Erros Esperados)

### Como Gerar Baseline

```bash
cd v2/backend

# Instalar dependências
pip install -r requirements-dev.txt

# Rodar Pyright
pyright apps/core apps/dat_ingest config --outputjson > pyright-baseline.json

# Ver resumo
cat pyright-baseline.json | python -c "
import json, sys
data = json.load(sys.stdin)
summary = data['summary']
print(f\"Files: {summary['filesAnalyzed']}\")
print(f\"Errors: {summary['errorCount']}\")
print(f\"Warnings: {summary['warningCount']}\")
"
```

### Erros Esperados (Estimativa)

**Em strict mode, esperamos:**
- ❌ 200-400 erros (tipo não anotado, Any implícito, etc.)
- ⚠️ 100-200 warnings (imports, unused variables, etc.)

**Tipos comuns de erros**:
1. **Missing type annotations** (~40%)
   ```python
   def processar(dados):  # Missing parameter type
       return dados.upper()  # Missing return type
   ```

2. **Implicit Any** (~30%)
   ```python
   def handle(self, *args, **kwargs):  # args/kwargs sem tipo
       pass
   ```

3. **QuerySet magic methods** (~15%)
   ```python
   queryset = Model.objects.filter(...)  # Pyright não infere tipo
   ```

4. **Django decorators** (~10%)
   ```python
   @action(detail=True)  # Decorator não tipado
   def custom_action(self, request):
       pass
   ```

5. **Outros** (~5%)
   - Optional access sem verificação
   - Retorno incompatível
   - Variáveis não inicializadas

---

## 📈 Progresso Esperado

### Após Cada PR

| PR | Arquivos Tipados | Erros Restantes | % Completo |
|----|------------------|-----------------|------------|
| Baseline | 0/65 | ~300 | 0% |
| #1 | 0/65 | ~300 | 0% (setup) |
| #2 | 24/65 | ~180 | 37% |
| #3 | 29/65 | ~150 | 45% |
| #4 | 30+/65 | ~100 | 50% |
| #5 | 51/65 | ~50 | 78% |
| #6 | 52+/65 | ~30 | 80% |
| #7 | 56/65 | ~20 | 86% |
| #8 | 65/65 | 0 | 100% ✅ |

### Timeline

```
Semana 1 (40h)          Semana 2 (40h)          Semana 3 (40h)          Semana 4 (24h)
┌──────────────┐        ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│ PR#1: Setup  │───────>│ PR#3: Models │───────>│ PR#5: Views  │───────>│ PR#7: Tests  │
│ PR#2: Servic │        │ PR#4: Serial │        │ PR#6: Tasks  │        │ PR#8: Polish │
└──────────────┘        └──────────────┘        └──────────────┘        └──────────────┘
   [0%]                    [45%]                   [80%]                   [100%]
```

**Data Estimada de Conclusão**: 2025-12-08

---

## 🚫 Arquivos Excluídos (Não Serão Tipados)

### Migrations (Geradas Automaticamente)

```
**/migrations/**/*.py
```

**Razão**: Arquivos gerados pelo Django, não devem ser editados manualmente.

### Tests (Menos Crítico)

```
**/tests/test_*.py
```

**Razão**: Tests são menos críticos para type checking. Apenas **fixtures** e **helpers** serão tipados (PR #7).

**Exceção**: `conftest.py`, `factories.py`, `utils.py` (fixtures reutilizáveis)

### Outros

```
**/__pycache__/**
**/node_modules/**
**/.venv/**
```

---

## 📝 Notas

### Por Que Strict Mode?

**Strict mode** é o mais rigoroso, mas garante máxima qualidade:
- Detecta erros sutis antes de rodar
- Força boas práticas (tipos explícitos)
- Melhora autocomplete (Pylance)

**Trade-off**: Mais erros iniciais, mas código final mais robusto.

### Por Que 35% do Projeto?

**Cobertura focada em código crítico**:
- ✅ Lógica de negócio (services)
- ✅ Modelos de dados (models)
- ✅ APIs públicas (views, serializers)
- ✅ Background tasks (Celery)
- ⏸️ Tests (menos crítico)

**Resultado**: Máximo benefício com esforço otimizado.

### Continue-on-error no CI

```yaml
- name: Type check with Pyright
  continue-on-error: true  # Não bloqueia CI
```

**Razão**: Durante PRs #1-#7, teremos erros conhecidos (baseline). CI não deve bloquear.

**Após PR #8**: Remover `continue-on-error` (strict enforcement).

---

## 🔗 Documentação

- [`TYPE_HINTS_GUIDE.md`](../docs/TYPE_HINTS_GUIDE.md) - Guia do desenvolvedor
- [`PYRIGHT_SETUP.md`](../docs/PYRIGHT_SETUP.md) - Setup e troubleshooting
- [`TYPE_HINTS_REFERENCE_FULL.md`](../../TYPE_HINTS_REFERENCE_FULL.md) - Referência completa (1500 linhas)
- [`.claude/CLAUDE.md`](../../.claude/CLAUDE.md) - Guia geral do projeto

---

**Criado em**: 11/11/2025
**Autor**: Claude Code
**Status**: Baseline documentada, aguardando implementação dos 8 PRs
